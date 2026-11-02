# Webinar 5: нефункціональне тестування (Sleep / Watchdog / Brown-out / Persistence)

Автоматизований black-box набір pytest для навчального ESP32 IoT Controller (`embedded_qa_wokwi_lab`).
Автор: Лахно А. Г., 02.11.2026.

## Як це працює
`firmware/{demo,buggy}/sketch.ino` — **незмінні** скетчі з лабораторної (sha256 у `build.sh` output).
Вони компілюються під host-модель ESP32 (`hal/`), яка відтворює Arduino-ESP32 3.0 API:

| Що моделюється | Як тест це бачить / як впливає |
|---|---|
| UART0 115200 8N1, RX-буфер 256 B | надсилає CLI-рядки, читає кожен рядок з міткою часу |
| GPIO5 (relay), GPIO2 (LED) | рівні як на логічному аналізаторі |
| Deep sleep + timer / ext0 wake-up | живлення: момент засинання і виходу з reset (як PPK2) |
| Task WDT (timeout, panic → reset) | reset reason `TASK_WDT`, лог `task_wdt` |
| NVS (Preferences) у файлі, атомарний запис запису | обрив живлення після K-го запису, bit-flip при вимкненому пристрої |
| Brown-out / power cut | reset у будь-який момент з причиною `BROWNOUT` / `POWERON` |
| Кнопка з дребезгом, DHT22 (відключення, checksum, значення поза діапазоном) | — |

Час пристрою прискорено ×10 (`--scale`), а сон і вимкнення живлення «перемотуються», тож 60-секундний сон займає мілісекунди.

## Запуск
```bash
pip install pytest pytest-html pytest-timeout
./run_all.sh                       # build + DEMO x1 + BUGGY x3 + results/summary.md
python3 -m pytest --fw buggy       # один прогін
python3 -m pytest --fw demo -k WDT # вибірково
```
Потрібні g++ (C++17) і Linux.

## Структура тестів (124 кейси, 32 функції)
| Файл | Пункт завдання | Що перевіряє |
|---|---|---|
| `test_01_sleep_wake.py` | 1 | SW01 тривалість сну ±15 % для N=1…60; SW02 працездатність після wake; SW03 дані; SW04 10 циклів |
| `test_02_watchdog.py` | 2 | WDT01 reset ≤5 с; WDT02 reset reason; WDT03 relay OFF; WDT04 без boot loop; WDT05 ×10; WDT06 без хибних reset |
| `test_03_brownout.py` | 3 | BO01 причина reset і цілість даних; BO02 relay OFF; BO03 brown-out під час boot; BO04 10 випадкових |
| `test_04_data_integrity.py` | 4 | DI01 restart; DI02/03/07 `powerloss`; DI04 обрив між записами flash; DI05 bit-flip; DI06 чиста flash |
| `test_05_negative_after_recovery.py` | 5 | NEG01 9 некоректних вводів × 5 типів відновлення; NEG02 шум на UART при старті; NEG03 `sleep` з поганим аргументом; NEG04 сенсор |
| `test_06_sensor_button.py` | рядки test sheet | SB01–03 DHT22 (R2), SB04–06 кнопка (R3) |
| `test_07_stability.py` | repeated recovery | REC01 20 змішаних збоїв |

Пункт 6 (параметризація) — `pytest.mark.parametrize` у 17 функціях.

## Результати (`results/`)
- `buggy/run1..3/` і `demo/run1/`: `report.html`, `junit.xml` (з виміряними значеннями в properties), `results.jsonl`, `logs/<test>.log` — повний лог кожного тесту (TX/RX/HW/SYS із часом пристрою).
- `summary.md` / `summary.json` — зведення і відтворюваність.

BUGGY: 78 PASS / 46 FAIL (кожен FAIL — 3/3). DEMO: 121 PASS / 3 FAIL (SB02, та сама прогалина R2 в еталоні).

## Обмеження
Це не заміна Wokwi чи плати: brown-out — це миттєвий reset без аналогової просадки, обрив запису відбувається між записами NVS, heap не моделюється. Що ще треба перевірити на залізі — див. Release Decision у test sheet.
