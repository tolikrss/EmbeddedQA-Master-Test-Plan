# wokwi/

Симуляція в Wokwi: де вона використана, що доводить і як відтворити.
Схеми й прошивки — з курсових пакетів (тут не публікуються); нижче описано, що в них є, щоб було зрозуміло, що саме тестувалося.

## smart_gate/ — W1 Smart Gate Controller (ризики R01, R08, R12)

| | |
|---|---|
| Пакет | `Smart_Gate_Controller_Buggy_QA_Training` (`diagram.json` + `sketch.ino`), Arduino Uno |
| Входи | кнопки OPEN (клавіша `o`), CLOSE (`c`), STOP (`s`); лімітери LIMIT_OPEN (`u`), LIMIT_CLOSE (`d`); Serial `O / C / S / R` |
| Виходи | relay OPEN, relay CLOSE, LED OPEN / CLOSE / ERROR, buzzer, Serial-діагностика |
| Виконано | 29 тест-кейсів: 21 PASS / 7 FAIL / 1 BLOCKED, кожен FAIL — 5/5 |
| Техніки | State transition, equivalence, timing boundary (9.9 / 10.0 / >10 с), negative, combination (обидва лімітери), output verification (таблиця R15) |

| Файл | Що в ньому |
|---|---|
| [Smart_Gate_Test_Sheet_Lakhno.docx](smart_gate/Smart_Gate_Test_Sheet_Lakhno.docx) | Hardware Test Sheet: execution log з фактичними спостереженнями, 7 bug reports |
| [Smart_Gate_Test_Cases.xlsx](smart_gate/Smart_Gate_Test_Cases.xlsx) | Тест-кейси, модель Input → State → Output |
| [../bug-reports/Smart_Gate_Bug_Log.xlsx](../bug-reports/Smart_Gate_Bug_Log.xlsx) | Bug log BUG-01…07 |

Ключовий доказ (R01): TC-03 — LIMIT_OPEN в OPENING ігнорується, реле ON; TC-13 — через 10.3 / 11.3 / 16 с OPENING без ERROR. Контроль у тій самій збірці: TC-14 — CLOSING переходить у ERROR рівно на 10.0 с.

## debounce_scenarios/ — W2, Wokwi CI scenarios (ризик R05)

Автоматичні сценарії для `wokwi-cli`, які відтворюють дефекти debounce без ручного натискання:

```bash
wokwi-cli --scenario tc06_noise_5ms.yaml --timeout 15000 .
```

| Сценарій | Що перевіряє | Очікувано | Факт на buggy (host-модель, ті самі стимули) |
|---|---|---|---|
| `tc01_normal_press.yaml` | Звичайне натискання | 1 подія | PASS |
| `tc03_heavy_bounce.yaml` | Сильний брязкіт | 1 подія | FAIL: 4 події |
| `tc04_long_press.yaml` | Довге утримання | 1 подія | PASS |
| `tc05_rapid_presses.yaml` | Швидкі натискання | 1 подія на натиск | PASS |
| `tc06_noise_5ms.yaml` | Імпульс шуму 5 мс | 0 подій | FAIL: подія прийнята |
| `tc07_noise_critical.yaml` | Шум під час critical operation | Операція не перезапускається | FAIL |
| `bonus_boundary.yaml` | Межа фільтра | Поріг 30 мс | FAIL: фактичний поріг ≈1 мс |

Для `tc06` і `tc07` успішне завершення `wait-serial: 'LOGICAL EVENT #…'` означає, що дефект відтворено.

**Як отримано факт.** У цьому циклі сценарії через `wokwi-cli` не запускалися: GUI і CLI Wokwi в середовищі виконання були недоступні. Ті самі стимули (брязкіт 10–100 переходів за ~1 мс, імпульси шуму) подавалися на незмінену прошивку в host-моделі ESP32, кожен сценарій ×5. YAML-файли — готовий спосіб повторити перевірку в Wokwi CI; це перший крок до автоматизації R05 у CI. Сигнали й логи тих самих прогонів — [../pulseview/gpio_debounce/](../pulseview/gpio_debounce/).

## Чого Wokwi не доводить

Симуляція підтверджує логіку, але не всі фізичні ефекти: таймінги реальних контактів, шум, поведінку живлення, реальні умови інтерфейсів. Тому для R01 / R05 на реальній платі ще потрібні осцилограми кнопок і лімітерів (residual risk RR-03).
