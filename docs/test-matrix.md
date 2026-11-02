# Final Test Matrix

Один рядок = ланцюжок **Risk → Level → Test → Environment → Expected → Evidence → Regression → Status**. Кожен тест обґрунтований ризиком, який він перевіряє; Score — рівень ризику за [Risk Matrix](risk-matrix.md) (3 × 3).
Статус наведено для навчальних `buggy`-збірок. Evidence ID розшифровано в [Evidence Index](../evidence-index.md).

Середовища: **Wokwi**, **Wokwi+LA** (logic analyzer, VCD), **Host** (незмінена прошивка на host-моделі ESP32 + Python/pytest), **HW** (реальна плата — не виконувалось).
Regression (рівні з [Master Test Plan §6.3](../master-test-plan.md#63-regression-strategy)): **Smoke** — дим-тест на кожну збірку (boot + basic CLI + sensor + MQTT); **Crit** — критичний regression (control + data integrity + recovery); **Full** — повний regression перед релізом (functional + protocol + power + network + stress). Тест рівня Smoke входить і в Crit, а Crit — у Full.

## 🟥 Високі ризики (score 7–9)

| ID | Risk | Score | Level | Test / Method | Type / technique | Env | Expected | Evidence | Regression | Status |
|---|---|:-:|---|---|---|---|---|---|---|---|
| T-01 | R01 | 9 | System | OPENING + LIMIT_OPEN (80–600 мс натиск, утримання 2 с) | State transition | Wokwi | OPEN, OPEN relay OFF, CLOSE relay OFF | E01 TC-03 | Crit | **FAIL** BUG-01 |
| T-02 | R01 | 9 | System | Рух без лімітера: 9.9 / 10.0 / 10.3 / 11.3 / 16 с, OPENING і CLOSING | Timing boundary | Wokwi | ERROR на 10 с, реле OFF, ERROR LED, buzzer | E01 TC-13, TC-14 | Crit | **FAIL** OPENING (BUG-02); PASS CLOSING (10.0 с) |
| T-03 | R01 | 9 | System | STOP в OPENING / CLOSING | State transition | Wokwi | STOPPED, обидва реле OFF одразу | E01 TC-06, TC-07 | Crit | PASS (реле); індикація → T-34 |
| T-04 | R01 | 9 | System | Монітор реле в 45+ сценаріях, реверс OPEN↔CLOSE під час руху | Combination, output verification | Wokwi | Ніколи OPEN+CLOSE одночасно | E01 TC-10, TC-11, TC-12 | Crit | PASS (0 випадків) |
| T-05 | R01 | 9 | System | ERROR: OPEN, CLOSE, STOP; вихід лише через RESET | State transition, negative | Wokwi | Рух не стартує; ERROR тримається до RESET | E01 TC-16, 17, 26 | Crit | **FAIL** STOP скидає ERROR (BUG-05) |
| T-06 | R02 | 9 | Recovery | `hang` → Task WDT, reason, відсутність boot loop, 0 хибних reset | Fault injection | Host | Reset ≤ 5 с, TASK_WDT | E16, E27 | Crit | PASS (4008 мс) |
| T-07 | R02 | 9 | Recovery | Реле після WDT reset (×1 і ×10 циклів) | Fault injection, output verification | Host | Relay OFF після будь-якого аварійного reset | E17, E18 | Crit | **FAIL** relay ON ≈340 мс після reset, 10/10 |
| T-08 | R02 | 9 | Recovery | Brown-out у робочому режимі, під час boot (5…400 мс) і 10 випадкових | Fault injection, timing | Host | Relay OFF, коректний reset reason | E19, E27 | Crit | **FAIL** relay ON; reset reason PASS |
| T-09 | R02 | 9 | Interface | `RESET` з 5 станів → STATUS | State transition, automation | Host | relay false, pwm 0 | E29 | Crit | **FAIL** W6 BUG-03 (true,255)… |
| T-10 | R02 | 9 | Recovery | 20 змішаних аварійних reset (WDT, brown-out, power, sleep) | Stress, fault injection | Host | Relay OFF після кожного | E26 | Crit | **FAIL** 5–6 із 20 |
| T-11 | R03 | 9 | Recovery | Обрив живлення після K-го запису NVS (K = 0, 1, 2) | Fault injection, boundary | Host | Старий або новий стан, не змішаний | E20 | Crit | **FAIL** K=1: (4, ON) після `relay off` |
| T-12 | R03 | 9 | Recovery | Bit-flip у записах NVS при вимкненому живленні | Fault injection | Host | Пошкодження виявлено, безпечні дефолти | E21 | Crit | **FAIL** relay OFF → ON без діагностики |
| T-13 | R03 | 9 | Recovery | `powerloss` ×5 | Fault injection, repeat | Host | Counter = старе або старе+1 | E22 | Crit | **FAIL** +100 щоразу |
| T-14 | R03 | 9 | Recovery | Збережений стан після reboot / power cycle / deep sleep; чиста flash | Positive control | Host | Стан відновлено, дефолти коректні | E27 (DI01, DI06, SW03) | Smoke + Crit | PASS |
| T-15 | R04 | 9 | Protocol | Нормальна транзакція MPU6050 0x68, 100 kHz | Protocol trace | Wokwi+LA | S-addr-W-ACK-reg-Sr-R-data-NACK-P, валідне значення | E15 | Crit | PASS (24.00 °C, 651.6 мкс) |
| T-16 | R04 | 9 | Recovery | NACK (FAULT → 0x69) на NORMAL-збірці | Fault injection, timing | Wokwi+LA | Retry ≈250 мс ×3, ERROR+FALLBACK, heartbeat живий, recovery без reboot | E11, E12, E13 | Crit | PASS (еталон поведінки) |
| T-17 | R04 | 9 | Recovery | Той самий NACK на BUGGY-збірці | Fault injection | Wokwi+LA | Те саме, що T-16 | E14 | Crit | **FAIL** зависання після 1-го NACK, 2/2 |
| T-18 | R06 | 9 | Network | `NET DOWN` → SEND ×5 → BUFFER | Equivalence (valid partition) | Host | count = 5, ID 1…5 у черзі | E38 | Smoke + Crit | PASS |
| T-19 | R06 | 9 | Network | Flush після `NET UP` | ID tracing | Host | Кожен ID рівно один раз, FIFO, `duplicates=0` | E34 | Crit | **FAIL** кожен ID двічі |
| T-20 | R06 | 9 | Network | Ємність буфера: 7 / 8 / 9 / 12 офлайн-повідомлень | BVA (cap−1, cap, cap+1, cap+4) | Host | occupancy ≤ 8, `dropped = N−8`, лишаються 8 найновіших у порядку | E35, E38 | Crit | **FAIL** на 9 і 12: count 9/8, 12/8, `dropped=0`, ID 1–4 втрачено |
| T-21 | R06 | 9 | Network | 5 флапів × 3 повідомлення | Repeat, ID tracing | Host | Немає повторних ID | E39 | Crit | **FAIL** 30 publish / 15 унікальних |
| T-22 | R06, R11 | 9 | Network | Офлайн `STRESS 100` ×5 | Stress | Host | occupancy ≤ 8, heap стабільний | E36, E37 | Crit | **FAIL** occupancy 100; heap −6400 B за кожні 100 |
| T-37 | R11 | 9 | System | 10 × `STRESS 100` онлайн, heap trend; контроль на demo | Reliability, memory trend | Host | Δheap ≥ −1 KB за 1000 повідомлень | E37 | Crit | **FAIL** −64 000 B (−64 B / повідомлення); demo 0 B |

## 🟧 Середні ризики (score 4–6)

| ID | Risk | Score | Level | Test / Method | Type / technique | Env | Expected | Evidence | Regression | Status |
|---|---|:-:|---|---|---|---|---|---|---|---|
| T-23 | R05 | 6 | Interface | Normal press, short bounce, long press, rapid presses | Equivalence | Host | 1 подія на натиск | E07, E08 | Full | PASS |
| T-24 | R05 | 6 | Interface | Heavy bounce, noise 5 мс, noise під час critical op | Negative, timing | Host | Шум < 30 мс відкинуто, 1 подія | E04, E05, E06 | Full | **FAIL** W2 BUG-01…03 |
| T-25 | R05 | 6 | System | 20 натискань з брязкотом при відпусканні; довге утримання | Repeat, equivalence | Host | 20 подій; утримання = 1 | E25 | Full | **FAIL** 34–38 подій; утримання PASS |
| T-26 | R05 | 6 | System | Одне натискання / утримання кнопки 3 с (Smart Gate R16) | Equivalence | Wokwi | 1 команда, без потоку | E01 TC-23, TC-24 | Full | PASS |
| T-27 | R07 | 4 | Interface | `set speed` / `set timeout` на межах: −1, 0, 1, 255, 256, 257; 0, 1, 60, 61 | BVA | Host | Поза діапазоном → ERROR, конфіг без змін | E09, E10 | Full | **FAIL** 256 → 255, timeout 0 приймається |
| T-28 | R07 | 4 | Interface | Довжина рядка: sweep 1…300, 40/41/42, 400, 1000, 5000 | BVA (input length), stress | Host | > 40 → `ERROR: command too long`, без reboot | E09 | Full | **FAIL** 41 → SYSTEM FAULT, хвіст виконується |
| T-29 | R07 | 4 | Interface | Unknown, empty, спецсимволи, Unicode, burst 100 валідних, garbage | Negative, stress | Host | ERROR на некоректне; burst без втрат | E09, E10 | Full | Частково: burst PASS; спецсимволи → OK (FAIL) |
| T-30 | R07, R10 | 4 | Interface | JSON CLI: одна команда = один валідний JSON; 12 некоректних вводів | Automation, negative | Host | Валідний JSON, ERROR + код, стан без змін | E29, E31 | Smoke | **FAIL** GET TEMP без `}`; negative PASS |
| T-31 | R08 | 6 | System | LIMIT_OPEN + LIMIT_CLOSE одночасно в CLOSED / OPENING / CLOSING | Combination | Wokwi | ERROR, реле OFF, ERROR LED | E01 TC-15 | Crit | **FAIL** лише WARNING, реле ON в OPENING |
| T-32 | R09 | 6 | Network | `NET DOWN` 20 с: відповідь на STATUS, послідовність backoff, к-сть спроб; `NET UP` | Timing, fault injection | Host | Немає hang; backoff зростає; ≤ 10 спроб; recovery | E33, E38 | Full | **FAIL** storm 360+ спроб; no-hang і recovery PASS |
| T-33 | R13 | 6 | Recovery | `sleep N`, N = 1, 2, 5, 10, 30, 60; 10 циклів | Timing boundary | Host | Сон N ± 15 % | E23 | Full | **FAIL** сон N/10 |
| T-34 | R10 | 4 | Interface | DHT22 відключено / checksum / −60 °C / 120 % | Negative, BVA | Host | Явна помилка, без «0.0» | E24, E29 | Full | **FAIL** |

## 🟩 Низькі ризики та тести, заплановані на реальне залізо

| ID | Risk | Score | Level | Test / Method | Type / technique | Env | Expected | Evidence | Regression | Status |
|---|---|:-:|---|---|---|---|---|---|---|---|
| T-35 | R12 | 3 | System | LED/реле в кожному стані за таблицею R15 | Output verification | Wokwi | Відповідність таблиці | E01 TC-20…22, TC-25 | Full | **FAIL** OPEN LED у STOPPED |
| T-36 | R12 | 3 | Interface | Невідома Serial-команда; команда з LF | Negative | Wokwi | Діагностика лише на невідоме | E01 TC-19, TC-28 | Full | **FAIL** хибне UNKNOWN на LF |
| T-38 | R11 | 9 | System | Soak 24 год, флапи кожні 5 хв, heap + largest free block (після fix W7 BUG-04) | Reliability | HW | Стабільний тренд, немає фрагментації | — | Full (HW) | **NOT RUN** (немає плати) |
| T-39 | R02, R03 | 9 | Recovery | Реальний brown-out (регульоване живлення, поріг BOD) | Fault injection | HW | Relay OFF, reason BROWNOUT | — | Full (HW) | **NOT RUN** |
| T-40 | R04 → R02 | 9 | Integration | I2C hang у прошивці з увімкненим WDT → стан реле після reset | Integration, fault injection | HW / інтегрована збірка | Relay OFF після WDT | — | Full (HW) | **NOT RUN** (немає інтегрованої збірки) |

## Покриття

| Risk | Score | Тестів | FAIL | Є evidence | Висновок |
|---|:-:|:-:|:-:|:-:|---|
| R01 | 🟥 9 | 5 | 3 | так | блокує реліз |
| R02 | 🟥 9 | 5 (+1 HW) | 4 | так | блокує реліз |
| R03 | 🟥 9 | 4 (+1 HW) | 3 | так | блокує реліз |
| R04 | 🟥 9 | 3 (+1 HW) | 1 | так | блокує реліз (еталонну поведінку доведено на NORMAL) |
| R06 | 🟥 9 | 5 | 4 | так | блокує реліз |
| R11 | 🟥 9 | 2 (+1 HW) | 2 | так | блокує реліз (витік → reset → R02) |
| R05 | 🟧 6 | 4 | 2 | так | fix до релізу (фантомні команди) |
| R08 | 🟧 6 | 1 | 1 | так | fix до релізу |
| R09 | 🟧 6 | 1 | 1 | так | fix до релізу або прийнятий ризик для пілоту |
| R13 | 🟧 6 | 1 | 1 | так | fix до релізу або прийнятий ризик для пілоту |
| R07 | 🟧 4 | 4 | 4 | так | fix до релізу (reboot від вводу) |
| R10 | 🟧 4 | 2 | 2 | так | fix до релізу |
| R12 | 🟩 3 | 2 | 2 | так | можна після пілоту |

Кожен ризик має щонайменше один тест і evidence. Неперевірені на залізі пункти (T-38…T-40) винесено в residual risks, а не «закрито» симуляцією.
