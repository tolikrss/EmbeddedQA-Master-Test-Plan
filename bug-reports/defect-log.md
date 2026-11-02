# Defect Log: усі дефекти курсу (35)

Severity в W1 було в шкалі Critical / High / Medium / Low, у W2 і далі — Critical / Major / Medium / Minor. Для зведення **High = Major, Low = Minor**.
Кожен дефект відтворено щонайменше 2 рази (W4), здебільшого 3/3 або 5/5. Повні bug reports — у джерельних test sheets (див. [Evidence Index](../evidence-index.md)); вісім release-blocking розписано в [bug-reports.md](bug-reports.md).
Нумерація W7 відповідає здачі завдання W7; у цьому репозиторії ті самі 4 дефекти незалежно відтворено набором `pytest/w7_network`.

## Зведення

| Severity | W1 Gate | W2 Debounce | W3 UART | W4 I2C | W5 Recovery | W6 JSON CLI | W7 Network | **Разом** |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Critical | 2 | 1 | 2 | 1 | 4 | 1 | 2 | **13** |
| ↳ з них Blocker (R01–R04) | 2 | 0 | 0 | 1 | 4 | 1 | 0 | **8** |
| Major (High) | 2 | 2 | 4 | 0 | 4 | 2 | 2 | **16** |
| Medium | 2 | 0 | 1 | 0 | 0 | 0 | 0 | **3** |
| Minor (Low) | 1 | 0 | 1 | 0 | 1 | 0 | 0 | **3** |
| **Разом** | 7 | 3 | 8 | 1 | 9 | 3 | 4 | **35** |

## Перелік

| ID | Source | Risk | Severity | Суть | Repro | MTP report |
|---|---|---|---|---|---|---|
| W1-01 | Smart Gate R3 | R01 | Critical | LIMIT_OPEN в OPENING ігнорується: OPEN relay ON, стан OPEN недосяжний | 5/5 | MTP-BUG-01 |
| W1-02 | Smart Gate R10 | R01 | Critical | Таймаут 10 с не спрацьовує в OPENING (у CLOSING — 10.0 с) | 5/5 | MTP-BUG-01 |
| W1-03 | Smart Gate R11 | R08 | Major | Обидва лімітники: лише WARNING, без ERROR; в OPENING реле ON | 5/5 | |
| W1-04 | Smart Gate R15 | R12 | Medium | У STOPPED світиться OPEN LED | 5/5 | |
| W1-05 | Smart Gate R13/R12 | R01 | Major | STOP скидає ERROR → STOPPED без RESET | 5/5 | |
| W1-06 | Smart Gate R6/R4 | R12, R01 | Medium | STOP у CLOSED → STOPPED, далі CLOSE вмикає CLOSE relay при зачинених воротах | 5/5 | |
| W1-07 | Smart Gate R14 | R12 | Minor | Кожна Serial-команда з LF дає хибне `UNKNOWN COMMAND` | 5/5 | |
| W2-01 | Debounce | R05 | Critical | Шумовий імпульс 5 мс (будь-який > 1 мс) приймається як натискання + ACTION; фактичний поріг ≈1 мс замість 30 мс | 5/5 | |
| W2-02 | Debounce | R05 | Major | Heavy bounce → 4 logical events; брязкіт 8 мс → 2; розрив контакту 2 мс при утриманні → 2 | 5/5 | |
| W2-03 | Debounce | R05 | Major | Шум під час critical operation дає зайві ACTION і перезапускає операцію (2.0 → 3.4 с) | 5/5 | |
| W3-01 | UART REQ-10/11/12/16 | R07 | Critical | Рядок ≥ 41 символу → SYSTEM FAULT, reboot, конфігурацію скинуто | 5/5 | MTP-BUG-08 |
| W3-02 | UART REQ-12/09/07 | R07 | Major | Хвіст після 41-го символу виконується як нова команда | 5/5 | MTP-BUG-08 |
| W3-03 | UART REQ-15/12/16 | R07 | Major | Після 400+ символів пакетом наступний `status` → ERROR | 5/5 | |
| W3-04 | UART REQ-13/14/16 | R07 | Critical | `set` у стані CONFIG=DIRTY → SYSTEM FAULT і reboot | 5/5 | |
| W3-05 | UART REQ-02/03 | R07 | Major | `set speed 256` → OK: speed=255 (обрізання замість ERROR) | 5/5 | |
| W3-06 | UART REQ-04/05 | R07 | Major | `set timeout 0` (−0, 00) приймається | 5/5 | |
| W3-07 | UART REQ-08/07 | R07 | Medium | Рядок лише зі спецсимволів або non-ASCII → `OK` | 5/5 | |
| W3-08 | UART REQ-06 | R07 | Minor | `STATUS`/`Status` виконуються, інші команди case-sensitive | 5/5 | |
| W4-01 | I2C retry/fallback | R04 | Critical | Після першого NACK тихе зависання: без retry, без ERROR, heartbeat зникає, немає recovery | 2/2 | MTP-BUG-04 |
| W5-01 | Sleep | R13 | Major | `sleep N` → сон N/10 (5 с → 0.5 с), лог пише `timer=5 s` | 3/3 | |
| W5-02 | WDT recovery | R02 | Critical | Relay знову ON через ≈340 мс після WDT reset (10/10) | 3/3 | MTP-BUG-02 |
| W5-03 | Brown-out recovery | R02 | Critical | Relay ON після brown-out reset | 3/3 | MTP-BUG-02 |
| W5-04 | NVS integrity | R03 | Critical | Обрив живлення між 2 записами NVS → змішаний стан | 3/3 | MTP-BUG-03 |
| W5-05 | NVS integrity | R03 | Major | `powerloss`: counter +100 (4 → 104), без діагностики | 3/3 (5/5 у циклі) | MTP-BUG-03 |
| W5-06 | NVS integrity | R03 | Critical | Bit-flip у flash не виявляється; relay OFF → ON | 3/3 | MTP-BUG-03 |
| W5-07 | Sensor | R10 | Major | Відмова DHT22 → `temp=0.0C humidity=0.0%` без ERROR | 3/3 | |
| W5-08 | Button | R05 | Major | Брязкіт при відпусканні → 2 події (20 натискань → 34–38) | 3/3 | |
| W5-09 | Sensor | R10 | Minor | Значення DHT22 поза діапазоном приймаються (є і в demo) | 3/3 | |
| W6-01 | JSON CLI Req 5 | R07 | Major | `SET PWM 100` → INVALID_VALUE | 3/3 | |
| W6-02 | JSON CLI Req 3 | R10, R07 | Major | `GET TEMP` → JSON без `}` | 3/3 | |
| W6-03 | JSON CLI Req 7 | R02 | Critical | `RESET` → `reset:true`, але STATUS (true,255) / (true,2) / (true,127) / (true,252) | 3/3 | MTP-BUG-02 (споріднений) |
| W7-01 | Network R6, R5 | R06 | Major | Кожне буферизоване повідомлення публікується двічі | 3/3 | MTP-BUG-06 |
| W7-02 | Network R4, R3, R8 | R06 | Critical | Буфер > ємності (9…100 / 8), найстаріші губляться мовчки, `dropped=0`, порядок flush порушено | 3/3 | MTP-BUG-05 |
| W7-03 | Network R2 | R09 | Major | Reconnect storm: backoff 500 → 50 мс, ≈360–370 спроб / 20 с | 3/3 | MTP-BUG-07 |
| W7-04 | Network R7 | R11 | Critical | Витік heap на кожне повідомлення (SEND / STRESS, онлайн і офлайн): −64 B у моделі, 1000 повідомлень → −64 000 B, не повертається; demo 0 B | 3/3 | MTP-BUG-09 |

## Спостереження, які не оформлено як дефекти (питання до вимог)

- W1: мала `o` приймається як OPEN; команда з кнопки фіксується при відпусканні; реверс без паузи (вимоги не задають паузу).
- W2: чи межа 30 мс включна; чи має валідне натискання під час critical operation перезапускати операцію.
- W5: `sleep` з некоректним аргументом мовчки обрізається до 1…60 с; relay відновлюється в ON після POWER_ON / SW reset (в обох збірках — потрібне рішення продукту: «пам'ятати стан» чи «fail-safe OFF»).
- W6: одиниці `STATUS.pwm` (0..255 проти 0..100) вимогами не задано.
- W7: `STRESS abc` / `STRESS 0` виконуються як `STRESS 1` (constrain), а не ERROR — в обох збірках.
