# Bug Reports: release-blocking defects

Тут детально описано 9 дефектів, які визначають release decision: по одному або два на кожен критичний ризик. Повний перелік усіх 35 дефектів курсу — у [defect-log.md](defect-log.md).

Severity: **Blocker** — Critical-дефект у ризиках безпеки актуатора R01–R04 без обхідного шляху; **Critical** — небезпечний стан актуатора, втрата контролю чи критичних даних без обхідного шляху; **Major** — функцію порушено, є наслідки для даних чи ресурсу, але без прямої загрози безпеці; **Minor** — індикація, діагностика.

---

## MTP-BUG-01: LIMIT_OPEN ігнорується в OPENING, і таймаут 10 с в OPENING не спрацьовує

| Поле | Значення |
|---|---|
| Source | W1 BUG-01 + BUG-02 |
| Requirement | Smart Gate R3, R10 |
| Risk | R01 (🟥 9) |
| Build / Env | Smart_Gate_Controller_Buggy_QA_Training_1, Arduino Uno, Wokwi |
| Preconditions | Симуляція запущена; стан CLOSED; обидва реле OFF |
| Steps | 1. Натиснути OPEN (кнопка або Serial `O`). 2. Переконатися: `STATE: CLOSED -> OPENING`, OPEN relay ON. 3. Натиснути LIMIT OPEN на 80–600 мс або утримувати 2 с. 4. Не натискати нічого ще 16 с. |
| Expected | Крок 3: OPEN relay OFF, стан OPEN. Якщо лімітер не спрацював — на 10 с ERROR, обидва реле OFF, ERROR LED, buzzer |
| Actual | Стан лишається OPENING, OPEN relay ON і під час, і після натискання лімітера; Serial безперервно друкує `OPEN LIMIT DETECTED`. Через 10.3 / 11.3 / 16 с — той самий OPENING, реле ON, ERROR LED OFF, buzzer мовчить. Контроль: у CLOSING таймаут спрацьовує рівно на 10.0 с |
| Impact | Привід тисне за кінцеве положення **без обмеження в часі**: єдиних двох захистів (лімітер і таймаут) немає саме в напрямку відкриття |
| Severity | **Critical (Blocker)** |
| Reproducibility | 5/5 |
| Evidence | E01 (TC-03, TC-13, TC-14), E02 |
| Regression after fix | T-01, T-02 (OPENING і CLOSING, 9.9 / 10.0 / >10 с), T-04, T-31 |

---

## MTP-BUG-02: реле знову вмикається ≈340 мс після Task WDT reset

| Поле | Значення |
|---|---|
| Source | W5 BUG-02 (також BUG-03 brown-out, W6 BUG-03 RESET) |
| Requirement | Recovery: після аварійного reset актуатор у безпечному стані (OFF) |
| Risk | R02 (🟥 9) |
| Build / Env | embedded_qa_wokwi_lab homework_buggy (sha256 `b4c58c49…`), host-модель ESP32, pytest |
| Preconditions | Пристрій після POWERON, relay OFF |
| Steps | 1. `relay on` (реле ON, стан збережено в NVS). 2. `hang`. 3. Дочекатися Task WDT reset. 4. Спостерігати GPIO5 і `status` після boot |
| Expected | Reset ≤ 5 с, reason TASK_WDT; після boot relay OFF, доки користувач не ввімкне його знову |
| Actual | Reset через 4008 мс, reason TASK_WDT — коректно. Але `GPIO pin=5 level=1` @4967.9 мс, тобто ≈340 мс після reset @4619.0 мс; `status` → `"relay":true` |
| Impact | Будь-яке зависання прошивки закінчується **самовільним увімкненням реле** без участі людини. Те саме після brown-out (≈338 мс) і в 5–6 з 20 змішаних аварійних reset |
| Severity | **Critical (Blocker)** |
| Reproducibility | 3/3 прогони; 10/10 циклів у WDT05 |
| Evidence | E17, E18, E19, E26, E27 |
| Regression after fix | T-06…T-10, T-11 (fail-safe не має ламати відновлення збереженого стану при нормальному reboot) |

---

## MTP-BUG-03: обрив живлення між двома записами NVS відновлює змішаний стан (relay ON після `relay off`)

| Поле | Значення |
|---|---|
| Source | W5 BUG-04 (також BUG-05, BUG-06) |
| Requirement | Persistence: після обриву запису має бути старий або новий цілісний стан |
| Risk | R03 (🟥 9) |
| Build / Env | homework_buggy W5, host-модель з інжекцією обриву після K-го commit NVS |
| Preconditions | Стан (counter=3, relay=ON) збережено |
| Steps | 1. `relay off`. 2. Обірвати живлення після 1-го commit цієї операції (counter записано, relay ще ні; вікно ≈26 мс). 3. Увімкнути живлення. 4. `status` |
| Expected | (3, ON) — старий стан, або (4, OFF) — новий |
| Actual | `NVS_COMMIT #7 key=counter` → `NVS_CUT before write key=relay` → після boot `"relay":true,"counter":4`, тобто змішаний стан. Користувач вимкнув реле, а після перебою живлення воно знову ON |
| Impact | Неатомарний запис критичного стану. Разом із BUG-06 (bit-flip у flash не виявляється, relay OFF → ON) пристрій не має механізму перевірки цілісності даних |
| Severity | **Critical (Blocker)** |
| Reproducibility | 3/3 (детерміновано для K = 1) |
| Evidence | E20, E21, E22 |
| Regression after fix | T-11…T-14 |

---

## MTP-BUG-04: після першого I2C NACK прошивка тихо зависає (без retry, без ERROR, без heartbeat)

| Поле | Значення |
|---|---|
| Source | W4 BUG-I2C-01 |
| Requirement | I2C: retry кожні ≈250 мс ×3 → ERROR + FALLBACK → recovery після відновлення пристрою; main loop не блокується |
| Risk | R04 (🟥 9) |
| Build / Env | Wokwi I2C BUGGY v2, ESP32 DevKit-C v4 + MPU6050 0x68, wokwi-logic-analyzer (D0 SDA, D1 SCL) |
| Preconditions | Нормальні читання з ACK; heartbeat `[SYSTEM] Main loop alive` у Serial |
| Steps | 1. Записати VCD. 2. Увімкнути FAULT switch (адреса → 0x69). 3. Спостерігати шину й Serial ≥ 8 с. 4. Вимкнути FAULT, спостерігати ≥ 18 с |
| Expected | Як на NORMAL-збірці (E11, E12): 3 спроби з інтервалом ≈250 мс, `[ERROR]` + `[FALLBACK]` через ≈500 мс, heartbeat не переривається, `[RECOVERY]` після зняття збою |
| Actual | Last ACK 22.567449 с → **єдиний** NACK 23.568530 с → шина IDLE (SDA = SCL = HIGH) до кінця capture 31.9 с. Жодного retry, `[WARN]`, `[ERROR]`; heartbeat зникає. Після FAULT OFF відновлення немає (18.4 с спостереження) |
| Impact | Це не lock-up шини, а блокуюче очікування у firmware без timeout. Вузол перестає реагувати на все, включно зі STOP. В інтегрованій системі WDT перезапустить вузол → MTP-BUG-02 → реле ON |
| Severity | **Critical (Blocker)** |
| Reproducibility | 2/2 (fault 1.0 с і 1.6 с) |
| Evidence | E14, E15; еталон — E11, E12, E13 |
| Regression after fix | T-15…T-17, T-40 |

---

## MTP-BUG-05 (новий, W7): переповнення офлайн-буфера — ємність перевищено, старі повідомлення втрачено мовчки, `dropped` = 0

| Поле | Значення |
|---|---|
| Source | W7 BUG-02 |
| Requirement | W7 R4: capacity 8, policy DROP_OLDEST, drop видно в counter/log; R3, R8 |
| Risk | R06 (🟥 9) |
| Build / Env | webinar_7 homework_buggy (sha256 `d953e339…`), host-модель ESP32, pytest; контроль — demo_firmware |
| Preconditions | `RESET STATS`; стан CONNECTED |
| Steps | 1. `NET DOWN`. 2. `SEND` ×12. 3. `BUFFER`, `STATUS`. 4. `NET UP`. 5. Зібрати ID усіх `[MQTT] publish` |
| Expected | Після 9-го SEND: `overflow policy=DROP_OLDEST dropped_total=1` … ; `BUFFER count=8 capacity=8 dropped=4`; після NET UP опубліковано 8 найновіших (5…12) по одному разу, у порядку |
| Actual | `overflow policy=DROP_OLDEST dropped_total=0`, далі `queued id=12 count=12/8`; `BUFFER count=12 capacity=8 dropped=0`. Flush: `9,9,10,10,11,11,12,12,5,5,6,6,…,12,12` (24 publish). ID 1–4 зникли без сліду. Офлайн `STRESS 100`: `"buffer":100,"capacity":8`, після NET UP 200 publish лише 8 унікальних ID (93–100), `dropped=0` |
| Impact | **Тиха втрата даних**: 92 зі 100 повідомлень зникають, а лічильник каже, що втрат немає. Оператор не може виявити втрату навіть з діагностики. Межа знайдена BVA: 8 — OK, 9 — FAIL |
| Severity | **Critical** (втрата даних без можливості виявлення + неправдива діагностика) |
| Reproducibility | 3/3 прогони; для N = 9, 12, 100 |
| Evidence | E35, E36, E38; ASan/UBSan без помилок пам'яті в моделі — `asan_overflow_scenario_C.txt` |
| Regression after fix | T-18…T-22; demo: `count=8 dropped=4`, publish 5…12 |

---

## MTP-BUG-06 (новий, W7): кожне буферизоване повідомлення публікується двічі після reconnect

| Поле | Значення |
|---|---|
| Source | W7 BUG-01 |
| Requirement | W7 R6: один message ID не публікується успішно більше одного разу; R5 |
| Risk | R06 (🟥 9) |
| Build / Env | як MTP-BUG-05 |
| Preconditions | `RESET STATS`, CONNECTED |
| Steps | 1. `NET DOWN`. 2. `SEND` ×5 (у черзі ID 1…5). 3. `NET UP`. 4. `STATUS` |
| Expected | publish 1, 2, 3, 4, 5 по одному разу; `sent=5`, `duplicates=0` |
| Actual | `flush_start count=5` → `publish id=1` ×2, `id=2` ×2 … `id=5` ×2 → `flush_end`; `STATUS: "sent":10,"duplicates":5`. За 5 флапів по 3 повідомлення: 30 publish, 15 унікальних |
| Impact | Подвійна обробка телеметрії на бекенді (подвійний облік подій, хибні тренди); вдвічі більше трафіку після кожного відновлення |
| Severity | Major |
| Reproducibility | 3/3 |
| Evidence | E34, E39, E38 |
| Regression after fix | T-19, T-21 |

---

## MTP-BUG-07 (новий, W7): reconnect storm — backoff зменшується з 500 до 50 мс

| Поле | Значення |
|---|---|
| Source | W7 BUG-03 |
| Requirement | W7 R2: retry з backoff, без reconnect storm |
| Risk | R09 (🟧 6) |
| Build / Env | як MTP-BUG-05 |
| Preconditions | CONNECTED |
| Steps | 1. `NET DOWN`. 2. Спостерігати `[NET] retry=… backoff_ms=…` 20 с. 3. `STATUS` |
| Expected | Backoff не спадає (еталон: 500 → 1000 → 2000 → 4000 → 8000 → 8000), ≤ 10 спроб за 20 с |
| Actual | `retry=1 backoff_ms=500`, `retry=2 backoff_ms=50`, далі весь час 50 мс; ≈360–370 спроб за 20 с (≈18/с). Вузол не зависає й відновлюється після NET UP (PASS) |
| Impact | У реальній мережі — навантаження на брокер і точку доступу, ризик бану клієнта брокером, зайве споживання енергії; при масовому відключенні всі вузли синхронно «штурмують» брокер |
| Severity | Major |
| Reproducibility | 3/3 |
| Evidence | E33, E38 |
| Regression after fix | T-32 |

---

## MTP-BUG-08: рядок із 41+ символу в UART CLI перезавантажує пристрій, а хвіст рядка виконується як команда

| Поле | Значення |
|---|---|
| Source | W3 BUG-01 + BUG-02 |
| Requirement | UART CLI REQ-10/11/12/16: рядок > 40 символів → `ERROR: command too long`, без reboot; відкинути весь рядок |
| Risk | R07 (🟧 4) |
| Build / Env | UART CLI HOMEWORK DEVICE v2.0, ESP32 DevKit v1, host-модель, 115200 8N1, LF |
| Preconditions | `set speed 50` → `save` (SPEED=50, SAVED) |
| Steps | 1. Надіслати одним рядком 41 × `A` + `set speed 0` + LF. 2. Дочекатися банера. 3. `status` |
| Expected | `ERROR: command too long`; жодна частина рядка не виконується; SPEED = 50 |
| Actual | `*** SYSTEM FAULT *** input line boundary failure`, rst:0xc (SW_CPU_RESET), reboot ≈250 мс, LED гасне, незбережені налаштування втрачено; далі хвіст виконується: `OK: speed=0`, `status: SPEED=0, DIRTY` |
| Impact | Сервісний інтерфейс дає змогу перезавантажити пристрій і змінити конфігурацію одним рядком; будь-яке сміття на лінії (≥ 41 байт без LF) = reboot. Межа 40/41 знайдена sweep'ом 1…300 |
| Severity | **Critical** |
| Reproducibility | 5/5; кожне N = 41…300 |
| Evidence | E09 (§TC-15, TC-16, TC-18, TC-24), E10 |
| Regression after fix | T-28, T-29, T-27 |

---

## MTP-BUG-09 (новий, W7): витік heap на кожне повідомлення

| Поле | Значення |
|---|---|
| Source | W7 BUG-04 |
| Requirement | W7 R7: при повторних SEND / STRESS free heap не демонструє систематичного незворотного падіння |
| Risk | R11 (🟥 9) |
| Build / Env | webinar_7 homework_buggy (sha256 `d953e339…`), host-модель, збірка `-O0 -fno-allocation-dce`; контроль — demo_firmware |
| Preconditions | CONNECTED, `STATUS` → heap 286847 B |
| Steps | 1. `STATUS`. 2. `STRESS 100`. 3. `STATUS`. 4. Повторити кроки 2–3 ще 9 разів. 5. Окремо: 5 × (`NET DOWN` → `STRESS 100` → `NET UP`) |
| Expected | Heap коливається, але не падає систематично; після серії повертається до базового рівня (допуск 1 KB) |
| Actual | Онлайн: 286847 → 280447 → 274047 → … → 222847 B, рівно −6400 B на кожні 100 повідомлень (−64 B / повідомлення), пам'ять не повертається. Офлайн — так само, витік на момент створення повідомлення. Demo з тим самим harness: 286847 B у всіх 11 точках |
| Impact | Вичерпання heap ≈ за 4 500 повідомлень (≈12 год при телеметрії раз на 10 с), далі падіння і reset. Після reset реле вмикається (MTP-BUG-02), тож витік у мережевому коді закінчується несанкціонованим рухом |
| Severity | **Critical** |
| Reproducibility | 3/3 прогони, лінійно в кожній ітерації |
| Evidence | E37 ([Memory Stability Log](../network-stress/memory-stability-log.md)), E36, E38 |
| Notes | Перший прогін на збірці моделі `-O1` показав рівний heap: GCC прибрав алокацію, і модель її не побачила. Розбіжність виявлено перехресною перевіркою з окремим harness здачі W7 (там −72 B / повідомлення через інший облік накладних витрат алокатора). Після `-O0 -fno-allocation-dce` обидва harness показують витік, а demo — ні. Висновок: дефект прошивки, а сліпа зона була в тестовому середовищі |
| Regression after fix | T-37, T-22; soak T-38 на платі з `heap_caps_get_largest_free_block()` |
