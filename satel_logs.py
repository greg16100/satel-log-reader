import socket
import argparse
import struct
import json
import time
import os
from datetime import datetime

# --- Konfiguracja ---
PORT = 7094
READ_EVENT_CMD = 0x8C
EVENT_CODES_FILE = "event_codes.json"  # Nazwa pliku z kodami

# Tłumaczenie typów źródeł
SOURCE_TYPES = {
    0: "System", 1: "Urządzenie", 2: "Użytkownik", 3: "Użytkownik", 4: "Urządzenie",
    6: "Użytkownik", 9: "Użytkownik", 30: "Dane IP", 31: "Dane IP"
}

# --- Funkcje pomocnicze ---
def load_event_codes(filename):
    """Wczytuje definicje kodów zdarzeń z pliku JSON."""
    if not os.path.isfile(filename):
        print(f"BŁĄD: Plik z kodami zdarzeń '{filename}' nie został znaleziony.")
        return None
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"BŁĄD: Plik '{filename}' zawiera błąd składni JSON.")
        return None

def encode_frame(cmd, data_bytes):
    def rotate_left(val): return ((val << 1) & 0xFFFF) | ((val >> 15) & 0x01)
    def calculate_crc(data):
        crc = 0x147A
        for b in data: crc = (rotate_left(crc) ^ 0xFFFF) + ((rotate_left(crc) ^ 0xFFFF) >> 8) + b
        return crc
    payload = [cmd] + data_bytes; crc = calculate_crc(payload); frame = [0xFE, 0xFE]
    for b in payload + [crc >> 8, crc & 0xFF]:
        if b == 0xFE: frame.extend([0xFE, 0xF0])
        else: frame.append(b)
    frame += [0xFE, 0x0D]
    return bytes(frame)

def decode_event_record(data):
    if len(data) != 8: return None
    try:
        b1, b2, b3, b4, b5, b6, b7, b8 = struct.unpack('BBBBBBBB', data)
        year_marker = (b1 >> 6) & 0x03; z_flag = (b1 >> 5) & 0x01
        day = b2 & 0x1F; month = (b3 >> 4) & 0x0F
        hour_min = ((b3 & 0x0F) << 8) | b4; hour, minute = divmod(hour_min, 60)
        restore = (b5 >> 2) & 0x01; code = ((b5 & 0x03) << 8) | b6; source = b7
        partition = (b5 >> 3) & 0x1F
        
        current_year = datetime.now().year
        year = current_year - (current_year % 4) + year_marker
        try:
            event_dt = datetime(year, month, day, hour, minute)
            if event_dt > datetime.now(): year -= 4
        except ValueError: year = current_year
        
        return {"date": f"{year}-{month:02}-{day:02}", "time": f"{hour:02}:{minute:02}", "code_raw": code, "source": source, "partition": partition, "restore": restore, "z": z_flag}
    except (struct.error, IndexError): return None

def get_device_name(source_number):
    if 1 <= source_number <= 128: return f"Czujka {source_number}"
    if 193 <= source_number <= 200: return f"Manipulator (adres {source_number - 193})"
    if 201 == source_number: return "DLOADX na RS-232"
    special_sources = {241: "Admin", 255: "Serwis"}
    return special_sources.get(source_number, f"Urządzenie {source_number}")

# --- Główna funkcja programu ---
def main():
    parser = argparse.ArgumentParser(description="Odczyt logów zdarzeń z centrali alarmowej SATEL.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--host", required=True, help="Adres IP centrali")
    parser.add_argument("--limit", type=int, default=0, help="Maksymalna liczba logów do odczytu (0 = bez limitu)")
    parser.add_argument("--both", action="store_true", help="Odczytaj logi standardowe oraz Grade 2")
    args = parser.parse_args()

    event_codes = load_event_codes(EVENT_CODES_FILE)
    if event_codes is None:
        return # Zakończ, jeśli nie udało się wczytać kodów

    log_types_to_read = []
    if args.both:
        log_types_to_read.append({'name': 'standardowych', 'index': [0xFF, 0xFF, 0xFF], 'is_grade2': False})
        log_types_to_read.append({'name': 'Grade 2', 'index': [0x00, 0xFF, 0xFF], 'is_grade2': True})
    else:
        log_types_to_read.append({'name': 'standardowych', 'index': [0xFF, 0xFF, 0xFF], 'is_grade2': False})
    
    all_events = []
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(5)
        try: s.connect((args.host, PORT))
        except (socket.timeout, ConnectionRefusedError, OSError) as e: print(f"Błąd połączenia: {e}"); return
        
        for log_type in log_types_to_read:
            print(f"\nŁączenie z centralą i pobieranie logów {log_type['name']}...")
            current_index = log_type['index']
            while True:
                if args.limit > 0 and len(all_events) >= args.limit: break
                try:
                    frame = encode_frame(READ_EVENT_CMD, current_index)
                    s.sendall(frame); time.sleep(0.05)
                    response = s.recv(2048)
                    idx = response.find(b'\x8C')
                    if idx == -1 or idx + 15 > len(response): break
                    
                    event_payload = response[idx + 1:idx + 9]
                    record = decode_event_record(event_payload)
                    
                    end_of_log = (log_type['is_grade2'] and event_payload[0] == 0) or \
                                 (not log_type['is_grade2'] and (not record or record['z'] == 0))
                    
                    if end_of_log: break
                    if record: all_events.append(record)
                    current_index = list(response[idx + 9:idx + 12])
                except socket.timeout: print("Przekroczono czas oczekiwania na odpowiedź."); break
            if args.limit > 0 and len(all_events) >= args.limit: break

    if not all_events: print("Nie znaleziono żadnych zdarzeń."); return

    print("\n--- Zdarzenia ---")
    for i, event in enumerate(all_events):
        code = event['code_raw']
        event_info = event_codes.get(str(code)) # Klucze w JSON są stringami
        
        description = f"[Nieznany kod: {code:04X}]"
        source_details = f"Źródło {event['source']}"

        if event_info:
            description = event_info.get('restore_desc') if event['restore'] == 1 and 'restore_desc' in event_info else event_info.get('desc', description)
            source_kind = event_info.get('kind', -1)
            source_type_str = SOURCE_TYPES.get(source_kind, "Źródło")

            if source_type_str == "Użytkownik":
                source_details = f"Użytkownik {event['source']}"
            elif source_type_str == "Urządzenie": source_details = get_device_name(event['source'])
            elif source_type_str == "Dane IP": source_details = f"Dane IP (P: {event['partition']}, S: {event['source']})"
            else: source_details = f"{source_type_str} {event['source']}"
        
        print(f"{i+1:2d}. {event['date']} {event['time']} | {description:<45} | {source_details}")

if __name__ == "__main__":
    main()