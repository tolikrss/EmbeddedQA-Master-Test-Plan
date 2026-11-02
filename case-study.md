# Embedded QA Case Study: Smart IoT Safety Controller

> Фінальний репорт: проблема → ризик → дизайн тестів → виконання → докази → знахідки → висновок.
> Детальний план — [master-test-plan.md](master-test-plan.md).

## Problem

ESP32-контролер керує приводом воріт і передає телеметрію. Команді треба вирішити, **чи можна ставити прошивку на пілотний об'єкт, де вона керуватиме реальним приводом.**
Тому для QA питання не «скільки тестів зелених», а «чи може реле опинитися під напругою без команди, і чи дізнаємося ми про збій».

## System Under Test

| | |
|---|---|
| Плата | ESP32 DevKit v1 (ESP32-WROOM-32); DevKit-C v4 для I2C; Arduino Uno — прототип логіки воріт |
| Сенсори | DHT22, MPU6050 (I2C 0x68), кінцеві датчики LIMIT_OPEN / LIMIT_CLOSE |
| Виконавчі елементи | OPEN / CLOSE relay, реле навантаження, LED, ERROR LED, buzzer |
| Інтерфейси | GPIO + переривання, UART 115200, I2C ≈100 kHz, Wi-Fi / MQTT |
| Firmware | 7 підсистем-збірок (версії і sha256 — [master-test-plan.md §1.2](master-test-plan.md#12-версії-firmware-release-candidate)) |
| Безпечний стан | Обидва реле OFF |

Входи (кнопки, лімітери, датчики, UART, мережа) → firmware (debounce, машина станів, CLI, I2C-драйвер, NVS, WDT, мережевий стан) → виходи (реле, LED / buzzer, Serial, MQTT). Схема — [docs/system-overview.md](docs/system-overview.md).

## Risks

**Ризик = Ймовірність × Вплив** (шкала 3 × 3). Шість ризиків мають максимальний бал 9 і визначають реліз:

| Risk | Failure mode → Impact | Ризик |
|---|---|:-:|
| R01 | Реле не зупиняється на лімітері / по таймауту → привід тисне без обмеження | 🟥 9 |
| R02 | Реле вмикається після аварійного reset → несанкціонований рух | 🟥 9 |
| R03 | Перебій живлення під час збереження → хибний стан реле після старту | 🟥 9 |
| R04 | Один NACK на I2C → тихе зависання, STOP не обробляється | 🟥 9 |
| R06 | Офлайн-телеметрія губиться / дублюється, і цього не видно | 🟥 9 |
| R11 | Витік heap на кожне повідомлення → reset через години роботи | 🟥 9 |

Ще 7 ризиків (шум на входах, лімітери, reconnect storm, сон, CLI, датчики, індикація) і перегляд «до / після тестування» — [docs/risk-matrix.md](docs/risk-matrix.md).
Найважливіший перегляд: R11 спершу був Низьким (3), а за evidence став Високим (9).

## Test Strategy

Кожен тест обґрунтований ризиком, який він перевіряє. Рівень і середовище обрано за тим, де дефект можна **довести**:

| Ризик | Рівень | Метод | Середовище | Чому саме так |
|---|---|---|---|---|
| R01 | System black-box | State transition + timing boundary 9.9 / 10.0 / >10 с в обох напрямках | Wokwi | Таймаут — межа в часі; CLOSING як контроль локалізує дефект |
| R02 | Fault injection | hang, brown-out у будь-який момент, ×10, ×20 | Python + pytest | Потрібні точна мітка reset і стан GPIO в ту саму мілісекунду |
| R03 | Fault injection | Обрив після K-го запису NVS, bit-flip | Python + pytest | У вікно ≈26 мс між записами руками не влучити |
| R04 | Component / interface + fault injection | VCD + декодер + fault switch, NORMAL проти BUGGY | Logic analyzer + PulseView / sigrok | Лише trace шини відрізняє lock-up шини від зависання прошивки |
| R06 | Network | ID-трасування кожного publish, BVA ємності 7 / 8 / 9 / 12 | MQTT / network (емуляція) + pytest | Лічильники брешуть, довіряти можна лише ID |
| R11 | Non-functional / reliability | Heap trend 10 і 5 ітерацій, контроль на еталоні | pytest | Одне значення heap нічого не доводить |

**Автоматизація** — там, де перевірки повторювані й детерміновані: 124 (W5) + 62 (W6) + 21 (W7) pytest-кейсів, кожен набір має контроль на еталонній прошивці й 3 прогони. W1 — ручні сценарії в Wokwi; для debounce уже є Wokwi CI scenarios ([wokwi/debounce_scenarios](wokwi/debounce_scenarios/)).

**Regression:** дим-тест (boot + CLI + sensor + MQTT) на кожну збірку; критичний (control + data integrity + recovery) на кожну зміну критичних підсистем; повний (functional + protocol + power + network + stress) перед релізом — [master-test-plan.md §6.3](master-test-plan.md#63-regression-strategy).
Повна матриця: 40 рядків — [docs/test-matrix.md](docs/test-matrix.md).

## Test Environment

| Середовище | Для чого використано | Чого не доводить |
|---|---|---|
| Wokwi | Машина станів воріт (W1), I2C-стенд (W4) | Електрику, дребезг реальних контактів |
| Serial / CLI | Усі практики: команди, `status`, reset reason, логи з часовими мітками | Те, що не виводиться в Serial |
| Logic analyzer + PulseView / sigrok | I2C-транзакції (W4), імпульси на GPIO (W2) | Фронти, ємність, підтяжки |
| Python + pytest + host-модель ESP32 | W2, W3, W5, W6, W7: незмінений `sketch.ino` на моделі Arduino-ESP32 API, fault injection, ASan / UBSan | Аналоговий brown-out, Wi-Fi стек, фрагментацію heap ESP-IDF |
| MQTT / network (емуляція) | `NET DOWN/UP`, буфер, дублікати, backoff (W7) | Реальний брокер, RSSI, TLS |
| Real hardware | **Не використано** → T-38…T-40 і residual risks | — |

## Test Scenarios

Шість найпоказовіших сценаріїв (з 271):

1. **Лімітер в OPENING** (R01). OPEN → LIMIT_OPEN → реле має вимкнутися. Фактично реле ON, і таймаут 10 с теж не спрацьовує (у CLOSING — рівно 10.0 с).
2. **hang → WDT → relay** (R02). WDT спрацьовує за 4008 мс (PASS), але через ≈340 мс після reset реле знову ON — 10 разів із 10.
3. **Обрив між двома записами NVS** (R03). `relay off` → записано counter, relay ще ні → після старту `(4, ON)`.
4. **NACK на I2C** (R04). Еталон: 3 retry по 250 мс → ERROR + FALLBACK → recovery. Buggy: один NACK і тиша на шині до кінця capture.
5. **12 повідомлень в офлайн-буфер на 8** (R06). `count=12/8`, `dropped=0`, ID 1–4 зникли, решта опубліковані двічі.
6. **10 × STRESS 100** (R11). Heap 286 847 → 222 847 B, рівно −64 B на повідомлення; еталон — 0 B.

Fault injection, використаний у сценаріях: hang, brown-out (зокрема під час boot), обрив запису flash, bit-flip, NACK, відмова DHT22, `NET DOWN` / 5 флапів, шум 1–8 мс на входах, 41…5000 символів і 500 випадкових байтів у UART.

## Findings

**35 дефектів:** 13 Critical (8 із них — Blocker у ризиках безпеки), 16 Major, 3 Medium, 3 Minor — [bug-reports/defect-log.md](bug-reports/defect-log.md). 9 release-blocking описано повністю, з Expected / Actual — [bug-reports/bug-reports.md](bug-reports/bug-reports.md).

Головне — не кількість, а патерн: **happy path працює всюди, ламається перехід через межу.** Межа часу (таймаут лише в одному напрямку), межа reset (стан реле після boot), межа запису (між двома commit), межа протоколу (перший NACK), межа ємності (9-те повідомлення), межа довжини (41-й символ).

Дефекти **з'єднуються в ланцюги:** I2C hang (R04) з WDT стане reset, а reset (R02) увімкне реле. Витік heap (R11) через ≈12 год закінчиться тим самим. Окремо жоден тест цього не покаже, тому інтеграційний тест T-40 — умова виходу.

## Evidence

44 позиції — [evidence-index.md](evidence-index.md). Кожен claim прив'язано до рядка лога, часової мітки чи значення, щоб інша людина могла перевірити висновок.

| Тип | Де |
|---|---|
| Serial-логи з часовими мітками | [uart-cli/](uart-cli/), [pytest/w5_recovery/evidence/logs/](pytest/w5_recovery/evidence/logs/), [network-stress/](network-stress/) |
| PulseView / VCD traces і графіки сигналів | [pulseview/](pulseview/) |
| Wokwi: test sheets і CI-сценарії | [wokwi/](wokwi/) |
| Pytest-звіти, JUnit XML, 3 прогони + еталон | [pytest/](pytest/) |
| Memory stability log, CSV, графіки | [network-stress/](network-stress/) |
| Bug reports | [bug-reports/](bug-reports/) |
| Test summary | [docs/test-summary.md](docs/test-summary.md) |

## Conclusion

**NO-GO** — [docs/release-decision.md](docs/release-decision.md).
Підстава — не 67.2 % PASS, а відкриті Critical-дефекти в усіх чотирьох ризиках безпеки актуатора, тиха втрата даних і витік пам'яті, що веде до reset. Усі відтворюються детерміновано й не мають експлуатаційного обхідного шляху. Умови переходу до GO WITH RISKS сформульовано вимірювано.

**Обмеження.** Реального заліза не було. Wokwi й host-модель не доводять аналоговий brown-out, дребезг реальних контактів і EMI, Wi-Fi стек, фрагментацію heap ESP-IDF. Підсистеми тестувалися окремими збірками. Усе це — residual risks з конкретними тестами для плати (T-38…T-40).

### What I learned / decisions made

- **Ризик спершу, тест потім.** Матриця ризиків вирішила, що тестувати глибше, а що — якщо лишиться час (R12 індикація).
- **Перевіряти треба і PASS.** Перший прогін W7 показав рівний heap, бо модель, зібрана з `-O1`, не бачила алокацію: її прибрав компілятор. Звірка з другим harness знайшла цю сліпу зону; після `-O0 -fno-allocation-dce` витік відтворився 3/3, а еталон лишився рівним.
- **Еталон як контроль.** Кожен автоматизований набір спочатку проходить на еталонній прошивці: так FAIL не можна списати на harness.
- **Рішення — за наслідком, а не за pass rate.** Тому NO-GO при 67 % PASS і було б NO-GO при 98 %.

### What I would improve next

1. Wokwi CI scenarios для Smart Gate, щоб R01 був в автоматичному regression.
2. Один спільний HAL і `conftest` для всіх наборів замість трьох окремих host-моделей.
3. Інтеграційна збірка і T-40: I2C hang з увімкненим WDT і перевіркою реле.
4. Реальна плата: T-39 (brown-out на БЖ), T-38 (soak 24 год), осцилограми кнопок.
5. CI (GitHub Actions) з дим-тестом на кожен push і публікацією JUnit.
