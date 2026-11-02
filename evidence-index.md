# Evidence Package Index

**Правило:** evidence має дозволяти іншій людині перевірити висновок QA без мене. Тому для кожного claim вказано не лише файл, а й рядок або значення, яке його доводить.

Позначки середовища: **Wokwi** = прогін у симуляторі Wokwi; **Wokwi + LA** = Wokwi з wokwi-logic-analyzer (VCD); **Host** = незмінена прошивка, скомпільована під host-модель ESP32 Arduino API (див. [pytest/README.md](pytest/README.md)).

## Найсильніші докази (для захисту)

| # | Claim | Risk | Evidence | Чому цього достатньо |
|---|---|---|---|---|
| E17 | Реле знову вмикається ≈340 мс після WDT reset | R02 | [pytest/w5_recovery/evidence/logs/test_WDT03…[cli].log](pytest/w5_recovery/evidence/logs/) рядки `RESET reason=TASK_WDT` @4619.0 → `GPIO pin=5 level=1` @4967.9 | Часова мітка reset і подія GPIO в одному логу; 10/10 у WDT05, 3/3 прогони |
| E20 | Користувач вимкнув реле, обрив живлення між двома записами NVS → пристрій стартує з relay ON | R03 | [pytest/w5_recovery/evidence/logs/test_DI04…[relay_off-1].log](pytest/w5_recovery/evidence/logs/) `TX relay off` → `NVS_COMMIT #7 counter` → `NVS_CUT before write key=qa-lab/relay` → після boot `"relay":true,"counter":4` | Видно, який саме запис не відбувся і який стан відновився |
| E14 | Після першого NACK на I2C прошивка зависає без retry і без логів | R04 | [pulseview/i2c_mpu6050/fig4_buggy_hang_timeline.png](pulseview/i2c_mpu6050/fig4_buggy_hang_timeline.png): last ACK 22.567449 s → єдиний NACK 23.568530 s → шина IDLE до 31.9 s, `Main loop alive` зникає | Protocol trace показує стан шини, а не лише Serial; перехресна перевірка sigrok-cli 1:1 |
| E01 | LIMIT_OPEN ігнорується, OPEN relay лишається ON; таймаут 10 с в OPENING не спрацьовує | R01 | [wokwi/smart_gate/Smart_Gate_Test_Sheet_Lakhno.docx](wokwi/smart_gate/) TC-03, TC-13 (10.3 / 11.3 / 16 с: OPENING, relay ON) проти TC-14 (CLOSING: ERROR рівно на 10.0 с) | Контрольний сценарій у тій самій збірці працює: дефект локалізовано саме в OPENING |
| E36 | 100 повідомлень в офлайні → після NET UP 200 publish лише 8 унікальних ID (93–100); 92 втрачено, `dropped=0` | R06 | [network-stress/buggy/run1/logs/test_MEM02…log](network-stress/buggy/run1/logs/) STATUS `"buffer":100,"capacity":8` і `"duplicates":100` | ID-трасування доводить і втрату, і дублювання; лічильник `dropped` суперечить фактам |
| E37 | Витік heap: −64 B на повідомлення, 1000 повідомлень → −64 000 B; demo 0 B | R11 | [memory-stability-log.md](network-stress/memory-stability-log.md), [test_MEM01…log](network-stress/buggy/run1/logs/test_MEM01_heap_trend_online_stress.log) | Тренд з 11 точок, а не одне значення; контроль на demo тим самим harness; підтверджено другим незалежним harness |
| E33 | Reconnect storm: backoff 500 → 50 мс, ≈360–370 спроб за 20 с | R09 | [network-stress/buggy/run1/logs/test_NET02…log](network-stress/buggy/run1/logs/) `retry=1 backoff_ms=500`, `retry=2 backoff_ms=50` …; еталон: 500/1000/2000/4000/8000, 6 спроб | Контрольний прогін на demo-прошивці з тим самим harness |
| E04 | Шумовий імпульс 5 мс приймається як натискання й запускає ACTION | R05 | [pulseview/gpio_debounce/TC-06_noise_5ms.png](pulseview/gpio_debounce/TC-06_noise_5ms.png) + `.vcd` + `_serial.log` (`LOGICAL EVENT #1 … ACCEPTED` @1008 мс) | Сигнал на піні (VCD) і логічна подія (Serial) зіставлено за часом |
| E09 | 41-символьний рядок у UART → SYSTEM FAULT, reboot, конфігурація скинута; хвіст рядка виконується | R07 | [uart-cli/UART_CLI_Serial_Log.txt](uart-cli/UART_CLI_Serial_Log.txt) §TC-15 (рядок 486+), §TC-18, sweep N = 1…300 | Межа 40/41 знайдена sweep'ом, вміст рядка ролі не грає |

## Повний індекс

### W1: Smart Gate Controller (Wokwi, Arduino Uno)
| ID | Related | Type | Description | File |
|---|---|---|---|---|
| E01 | R01, R08, R12 | Test sheet + Serial observations | 29 TC (21 PASS / 7 FAIL / 1 BLOCKED), 7 bug reports, кожен 5/5 | [Smart_Gate_Test_Sheet_Lakhno.docx](wokwi/smart_gate/Smart_Gate_Test_Sheet_Lakhno.docx) |
| E02 | R01, R08, R12 | Bug log | Таблиця BUG-01…07 з кроками й evidence | [Smart_Gate_Bug_Log.xlsx](bug-reports/Smart_Gate_Bug_Log.xlsx) |
| E03 | R01 | Test cases + Input-State-Output model | Тест-кейси й модель станів | [Smart_Gate_Test_Cases.xlsx](wokwi/smart_gate/Smart_Gate_Test_Cases.xlsx) |

### W2: GPIO debounce (Host, ESP32)
| ID | Related | Type | Description | File |
|---|---|---|---|---|
| E04 | R05 | VCD + PNG + Serial | TC-06 шум 5 мс прийнято як натискання | [TC-06_noise_5ms.*](pulseview/gpio_debounce/) |
| E05 | R05 | VCD + PNG + Serial | TC-03 heavy bounce → 4 logical events | [TC-03_heavy_bounce.*](pulseview/gpio_debounce/) |
| E06 | R05 | VCD + PNG + Serial | TC-07 шум під час critical operation перезапускає операцію | [TC-07_noise_critical.*](pulseview/gpio_debounce/) |
| E07 | R05 | VCD + PNG + Serial | TC-02 short bounce → 1 event (PASS, контроль) | [TC-02_short_bounce.*](pulseview/gpio_debounce/) |
| E08 | R05 | Test sheet | 7 TC × 5 прогонів, 10 фізичних дій → 17 logical events | [Debounce_Test_Sheet_Test_Log_Lakhno.pdf](pulseview/gpio_debounce/Debounce_Test_Sheet_Test_Log_Lakhno.pdf) |

### W3: UART CLI (Host, ESP32; 105 прогонів під ASan/UBSan без помилок пам'яті)
| ID | Related | Type | Description | File |
|---|---|---|---|---|
| E09 | R07 | Serial transcript | 26 TC з часовими мітками, sweep довжини, додатки A–C | [UART_CLI_Serial_Log.txt](uart-cli/UART_CLI_Serial_Log.txt) |
| E10 | R07 | Test report + QA conclusion | Таблиця виконання, BVA, 8 bug reports | [UART_CLI_Test_Report.docx](uart-cli/UART_CLI_Test_Report.docx), [UART_CLI_QA_Conclusion.docx](uart-cli/UART_CLI_QA_Conclusion.docx) |

### W4: I2C protocol analysis (Wokwi + LA, MPU6050 0x68)
| ID | Related | Type | Description | File |
|---|---|---|---|---|
| E11 | R04 | Protocol timeline | NORMAL: last ACK 52.000172 s → NACK 53.000265 s → retry 250 мс → ERROR+FALLBACK → recovery 71.000177 s без reboot | [fig1_normal_fault_timeline.png](pulseview/i2c_mpu6050/fig1_normal_fault_timeline.png) |
| E12 | R04 | Retry cycle | 18 циклів × 3 спроби = 54 NACK, інтервал ≈250 мс | [fig2_normal_retry_cycle.png](pulseview/i2c_mpu6050/fig2_normal_retry_cycle.png) |
| E13 | R04 | Waveform | ACK vs NACK на SDA/SCL | [fig3_waveform_ack_vs_nack.png](pulseview/i2c_mpu6050/fig3_waveform_ack_vs_nack.png) |
| E14 | R04 | Protocol timeline | BUGGY: тихе зависання після першого NACK (2/2) | [fig4_buggy_hang_timeline.png](pulseview/i2c_mpu6050/fig4_buggy_hang_timeline.png) |
| E15 | R04 | Analysis sheet | Таблиці транзакцій, таймінги, bug report | [Protocol_Analysis_Sheet_Webinar_4_Lakhno.docx](pulseview/i2c_mpu6050/Protocol_Analysis_Sheet_Webinar_4_Lakhno.docx) |

### W5: Recovery / fault injection (Host, pytest, 124 кейси × 3 прогони)
| ID | Related | Type | Description | File |
|---|---|---|---|---|
| E16 | R02 | Reset log | PASS: hang → WDT reset за 4008 мс, reason TASK_WDT | [test_WDT01_reset_within_5s.log](pytest/w5_recovery/evidence/logs/test_WDT01_reset_within_5s.log) |
| E17 | R02 | Reset log + GPIO | FAIL: relay ON ≈340 мс після WDT reset | [test_WDT03_relay_off_after_wdt_reset[cli].log](pytest/w5_recovery/evidence/logs/) |
| E18 | R02 | Reset log ×10 | FAIL: relay ON у 10/10 циклах hang → reset | [test_WDT05_repeated_hang_recovery_x10.log](pytest/w5_recovery/evidence/logs/test_WDT05_repeated_hang_recovery_x10.log) |
| E19 | R02 | Reset log | FAIL: relay ON ≈338 мс після brown-out | [test_BO02_relay_off_after_brownout[cli].log](pytest/w5_recovery/evidence/logs/) |
| E20 | R03 | Before/after NVS log | FAIL: змішаний стан (4, ON) після `relay off` і обриву між записами | [test_DI04_power_cut_between_flash_writes[relay_off-1].log](pytest/w5_recovery/evidence/logs/) |
| E21 | R03 | Before/after | FAIL: bit-flip у flash не виявлено, relay OFF → ON | [test_DI05_corrupted_flash_is_detected[off-bit0].log](pytest/w5_recovery/evidence/logs/) |
| E22 | R03 | Before/after ×5 | FAIL: `powerloss` дає counter +100 (2→102 … 410→510) | [test_DI07_repeated_powerloss_x5.log](pytest/w5_recovery/evidence/logs/test_DI07_repeated_powerloss_x5.log), [test_DI02…log](pytest/w5_recovery/evidence/logs/test_DI02_powerloss_leaves_old_or_new_valid_state.log) |
| E23 | R13 | Timing | FAIL: `sleep 5` → сон 500 мс | [test_SW01_wakeup_time_within_15pct[5].log](pytest/w5_recovery/evidence/logs/) |
| E24 | R10 | Serial | FAIL: відключений DHT22 → `temp=0.0C humidity=0.0%` | [test_SB01…[disconnected].log](pytest/w5_recovery/evidence/logs/) |
| E25 | R05 | Counter | FAIL: 20 натискань → 38 подій | [test_SB05_twenty_presses_twenty_events.log](pytest/w5_recovery/evidence/logs/test_SB05_twenty_presses_twenty_events.log) |
| E26 | R02 | Fault storm ×20 | FAIL: relay ON після 6 із 20 змішаних аварійних reset | [test_REC01_mixed_fault_storm_x20[11].log](pytest/w5_recovery/evidence/logs/) |
| E27 | R02, R03, R13 | Pytest report | Зведення 3 прогонів (78/46, усі FAIL 3/3), demo-контроль 121/124 | [summary.md](pytest/w5_recovery/evidence/summary.md), [summary.json](pytest/w5_recovery/evidence/summary.json), [junit_buggy_run1.xml](pytest/w5_recovery/evidence/junit_buggy_run1.xml), [junit_demo_run1.xml](pytest/w5_recovery/evidence/junit_demo_run1.xml) |
| E28 | R02, R03 | Test sheet | Recovery / Fault Injection Test Sheet | [Recovery_Fault_Injection_Test_Sheet_Webinar_5_Lakhno.docx](pytest/w5_recovery/evidence/Recovery_Fault_Injection_Test_Sheet_Webinar_5_Lakhno.docx) |

### W6: Pytest automation, JSON CLI (Host, pyserial/pty)
| ID | Related | Type | Description | File |
|---|---|---|---|---|
| E29 | R02, R07, R10 | Pytest output + JUnit + serial trace | buggy: 53 PASS / 9 FAIL | [pytest_homework_buggy.txt](pytest/w6_json_cli/pytest_homework_buggy.txt), [junit_homework_buggy.xml](pytest/w6_json_cli/junit_homework_buggy.xml), [serial_trace_homework_buggy.log](pytest/w6_json_cli/serial_trace_homework_buggy.log) |
| E30 | (harness) | Control run | demo: 62/62 PASS | [pytest_demo_firmware.txt](pytest/w6_json_cli/pytest_demo_firmware.txt) |
| E31 | (repeatability) | 3 прогони | однаковий набір FAIL 3/3 | [repeatability_buggy.txt](pytest/w6_json_cli/repeatability_buggy.txt) |
| E32 | — | Test sheet | Execution log, FAIL classification, bug reports | [Webinar6_Pytest_Test_Sheet_Lakhno.docx](pytest/w6_json_cli/Webinar6_Pytest_Test_Sheet_Lakhno.docx); код: [github.com/tolikrss/Webinar6_Pytest](https://github.com/tolikrss/Webinar6_Pytest) |

### W7: Network / offline buffer / memory (Host, pytest, 21 кейс × 3 прогони + demo)
| ID | Related | Type | Description | File |
|---|---|---|---|---|
| E33 | R09 | Network log | FAIL: backoff 500 → 50 мс, ≈360–370 спроб / 20 с | [test_NET02…log](network-stress/buggy/run1/logs/test_NET02_backoff_grows_no_reconnect_storm.log) |
| E34 | R06 | Message IDs | FAIL: SEND×5 офлайн → publish 1,1,2,2,…,5,5; `duplicates=5` | [test_BUF02…log](network-stress/buggy/run1/logs/test_BUF02_buffer_flushed_exactly_once.log) |
| E35 | R06 | Message IDs + counters | FAIL: 12 офлайн → `count=12/8`, `dropped=0`, ID 1–4 втрачено, порядок 9–12, 5–12, кожен двічі | [test_BUF04…[12].log](network-stress/buggy/run1/logs/) |
| E36 | R06, R11 | IDs + heap | FAIL: 100 офлайн → 8 унікальних ID, `buffer=100`; heap −6400 B за кожні 100 | [test_MEM02…log](network-stress/buggy/run1/logs/test_MEM02_heap_and_buffer_offline_stress.log) |
| E37 | R11 | Memory metrics | FAIL: heap 286847 → 222847 B за 1000 повідомлень (−64 B / повідомлення); demo 286847 B в усіх точках | [memory-stability-log.md](network-stress/memory-stability-log.md), [test_MEM01…log](network-stress/buggy/run1/logs/test_MEM01_heap_trend_online_stress.log) |
| E38 | R06, R09, R11 | Pytest report | buggy 11 PASS / 10 FAIL ×3 прогони, усі FAIL 3/3; demo 21/21 | [summary.md](network-stress/summary.md), JUnit: [buggy/run1](network-stress/buggy/run1/junit.xml), [run2](network-stress/buggy/run2/junit.xml), [run3](network-stress/buggy/run3/junit.xml), [demo](network-stress/demo/run1/junit.xml) |
| E39 | R06 | Message IDs | FAIL: 5 флапів → 30 publish, 15 унікальних ID | [test_DUP01…log](network-stress/buggy/run1/logs/test_DUP01_no_duplicate_ids_over_5_flaps.log) |

### Додано у фінальному пакеті: графіки, CSV, Wokwi-сценарії, підсумок
| ID | Related | Type | Description | File |
|---|---|---|---|---|
| E40 | R11 | Memory chart + CSV | Free heap по ітераціях: buggy 280.1 → 217.6 KB, еталон рівний | [charts/heap_trend.png](network-stress/charts/heap_trend.png), [heap_trend.csv](network-stress/heap_trend.csv) |
| E41 | R09 | Network chart + CSV | Накопичені спроби reconnect за 20 с: 369 проти 6 | [charts/reconnect_attempts.png](network-stress/charts/reconnect_attempts.png), [network_stress.csv](network-stress/network_stress.csv) |
| E42 | R06 | Message IDs CSV | Черга / опубліковані / втрачені ID для кожного сценарію буфера, buggy і еталон | [message_ids.csv](network-stress/message_ids.csv) |
| E43 | R05 | Wokwi project scenarios | 7 Wokwi CI сценаріїв для відтворення дефектів debounce без ручного натискання (факт отримано на host-моделі тими самими стимулами; запуск через `wokwi-cli` — наступний крок) | [wokwi/debounce_scenarios/](wokwi/debounce_scenarios/) |
| E44 | усі | Test summary | Total / passed / failed / blocked / pass rate за підсистемами + контроль на еталоні | [docs/test-summary.md](docs/test-summary.md) |

## Evidence за типами (як у курсі)

| Тип | Що є в пакеті | ID |
|---|---|---|
| Screenshot / графік | PNG сигналів debounce, timeline I2C, графіки heap і reconnect | E04–E07, E11–E14, E40, E41 |
| Serial log | Transcript UART CLI, Serial з часовими мітками W2 / W5 / W7 | E09, E16–E26, E33–E36, E39 |
| PulseView / VCD trace | VCD debounce (відкривається в PulseView), I2C-traces і декодування | E04–E07, E11–E15 |
| Wokwi project | Test sheet і тест-кейси Smart Gate, Wokwi CI сценарії | E01–E03, E43 |
| Pytest report | pytest output, JUnit XML за 3 прогони, контроль на еталоні | E27, E29–E31, E38 |
| Memory stability log | Лог за шаблоном курсу + графік + CSV | E37, E40 |
| Bug report | 9 release-blocking, defect log (35) | [bug-reports/](bug-reports/) |
| Test summary | Підсумок виконання | E44 |

## Як відрізнялися дефекти прошивки від проблем harness

1. **Контрольний прогін на еталонній прошивці** тим самим harness: W5 demo 121/124 (3 FAIL — та сама прогалина вимог R2 в еталоні), W6 demo 62/62, W7 demo 21/21. Якщо harness помиляється, він помиляється і на demo.
2. **Повторюваність:** кожен FAIL перевірено 3/3 (W5, W6, W7) або 5/5 (W1, W2, W3).
3. **Санітайзери:** W3 — 105 прогонів під ASan/UBSan без помилок пам'яті; W7 — сценарій переповнення буфера під ASan/UBSan без помилок ([asan_overflow_scenario_C.txt](network-stress/asan_overflow_scenario_C.txt)). Отже reboot і втрата даних формує логіка прошивки, а не пошкодження пам'яті в моделі.
4. **Незалежний декодер:** W4 — власний I2C-декодер звірено з sigrok-cli (той самий libsigrokdecode, що в PulseView), збіг 1:1.
5. **Другий незалежний harness:** результати W7 звірено з набором, зданим у завданні W7. Збіглися 3 дефекти, а четвертий (витік heap) мій перший прогін пропустив: модель збиралася з `-O1`, і GCC прибирав алокацію. Після перезбирання з `-O0 -fno-allocation-dce` витік відтворився 3/3, а demo лишився рівним. Це приклад того, що PASS теж потребує перевірки середовища.
