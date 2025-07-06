# Czytnik Logów dla Centrali Satel

Narzędzie wiersza poleceń (CLI) w języku Python do odczytywania i interpretowania logów zdarzeń z central alarmowych Satel (np. z serii INTEGRA) za pośrednictwem modułu ethernetowego ETHM-1 Plus.

## Główne Funkcje

- **Połączenie sieciowe:** Łączy się z centralą przez sieć TCP/IP na porcie integracyjnym (domyślnie 7094).
- **Odczyt dwóch typów logów:** Obsługuje odczyt standardowego dziennika zdarzeń oraz logów Grade 2.
- **Pełna interpretacja zdarzeń:** Tłumaczy techniczne kody zdarzeń na zrozumiałe opisy w języku polskim, wykorzystując wbudowaną bazę kodów.
- **Inteligentna obsługa "Przywrócenia":** Poprawnie interpretuje zdarzenia powrotu do normy (np. "Rozbrojenie" vs "Uzbrojenie").
- **Dekodowanie daty i źródła:** Rekonstruuje pełną datę zdarzenia (wraz z rokiem) i identyfikuje źródło (użytkownik, czujka, manipulator itp.).
- **Brak zewnętrznych zależności:** Skrypt korzysta wyłącznie ze standardowej biblioteki Pythona.

## Instalacja

1.  **Sklonuj repozytorium:**
    ```bash
    git clone <URL_TWOJEGO_REPOZYTORIUM>
    cd satel-log-reader
    ```

2.  **(Zalecane) Stwórz i aktywuj wirtualne środowisko:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Na Windows: venv\Scripts\activate
    ```

3.  **Zainstaluj zależności:**
    (W tym przypadku krok ten nic nie zainstaluje, ale jest to standardowa procedura)
    ```bash
    pip install -r requirements.txt
    ```

## Użycie

Skrypt uruchamia się z terminala, podając jako argument adres IP centrali.

**Składnia polecenia:**
```bash
python satel_logs.py --host <ADRES_IP> [OPCJE]
```

**Argumenty:**
- `--host <ADRES_IP>`: (Wymagany) Adres IP modułu ETHM-1 Plus.
- `--limit <LICZBA>`: (Opcjonalnie) Ogranicza liczbę odczytywanych logów.
- `--both`: (Opcjonalnie) Odczytuje logi standardowe oraz Grade 2.

**Przykłady:**

- **Odczytanie ostatnich 100 zdarzeń ze standardowego logu:**
  ```bash
  python satel_logs.py --host 192.168.1.100 --limit 100
  ```

- **Odczytanie wszystkich zdarzeń z obu logów (standardowego i Grade 2):**
  ```bash
  python satel_logs.py --host 192.168.1.100 --both
  ```

## Pliki w Projekcie

- `satel_logs.py`: Główny, wykonywalny plik skryptu.
- `event_codes.json`: Plik danych zawierający kompletną bazę kodów zdarzeń i ich opisów. Może być łatwo aktualizowany bez modyfikacji głównego skryptu.