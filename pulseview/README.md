# pulseview/

Докази з логічного аналізатора: що відбувається на шині й на піні, а не лише що прошивка пише в Serial.

## i2c_mpu6050/ — W4 I2C protocol analysis (ризик R04)

| | |
|---|---|
| Стенд | Wokwi, ESP32 DevKit-C v4 + MPU6050 (0x68), I2C ≈100.6 kHz (SDA GPIO21, SCL GPIO22) |
| Захоплення | wokwi-logic-analyzer: D0 = SDA, D1 = SCL, VCD (timescale 1 ns) |
| Декодування | Власний I2C-декодер + перехресна перевірка `sigrok-cli -P i2c` (той самий libsigrokdecode, що в PulseView), збіг 1:1 |
| Fault injection | FAULT switch (GPIO27) → адреса 0x69 → NACK |

| Файл | Що показує | Ключові значення |
|---|---|---|
| [fig1_normal_fault_timeline.png](i2c_mpu6050/fig1_normal_fault_timeline.png) | NORMAL: від останнього ACK до recovery | last ACK 52.000172 с → NACK 53.000265 с → retry 53.250058 / 53.500058 с → ERROR + FALLBACK → ACK 71.000177 с без reboot |
| [fig2_normal_retry_cycle.png](i2c_mpu6050/fig2_normal_retry_cycle.png) | NORMAL: цикл retry | 18 циклів × 3 спроби = 54 NACK, інтервал ≈250 мс, heartbeat не переривається |
| [fig3_waveform_ack_vs_nack.png](i2c_mpu6050/fig3_waveform_ack_vs_nack.png) | Хвильова форма ACK проти NACK | 9-й такт SCL: SDA LOW (ACK) / HIGH (NACK) |
| [fig4_buggy_hang_timeline.png](i2c_mpu6050/fig4_buggy_hang_timeline.png) | **BUGGY: зависання** | last ACK 22.567449 с → **єдиний** NACK 23.568530 с → шина IDLE до 31.9 с, heartbeat зникає, recovery немає (2/2) |
| [Protocol_Analysis_Sheet_Webinar_4_Lakhno.docx](i2c_mpu6050/Protocol_Analysis_Sheet_Webinar_4_Lakhno.docx) | Таблиці транзакцій, таймінги, bug report | Нормальне читання: S 0x68 W ACK · 0x41 · Sr 0x68 R · 0xEF 0x5C → 24.00 °C, 651.6 мкс |

**Висновок з trace:** шина після NACK вільна (SDA = SCL = HIGH), отже це не lock-up шини, а блокуюче очікування у firmware без timeout. Без trace цього не відрізнити: в обох випадках у Serial просто тиша.
Вихідні `.vcd` W4 у пакет не потрапили. Графіки й аналіз побудовано з них під час практики (див. Analysis Sheet).

## gpio_debounce/ — W2 GPIO debounce (ризик R05)

Для кожного сценарію є три файли: `.vcd` (сигнал на GPIO18, відкривається в PulseView: *File → Import → Value Change Dump*), `.png` (той самий сигнал з позначеними логічними подіями) і `_serial.log` (Serial з часовими мітками).

| Сценарій | Результат | Що видно |
|---|---|---|
| [TC-02 short bounce](gpio_debounce/TC-02_short_bounce.png) | PASS (контроль) | Брязкіт ≈1 мс → 1 логічна подія |
| [TC-03 heavy bounce](gpio_debounce/TC-03_heavy_bounce.png) | FAIL | Сегменти по 2 мс → 4 логічні події |
| [TC-06 noise 5 ms](gpio_debounce/TC-06_noise_5ms.png) | FAIL | Імпульс шуму 5 мс → `LOGICAL EVENT #1 … ACCEPTED` @1008 мс |
| [TC-07 noise during critical op](gpio_debounce/TC-07_noise_critical.png) | FAIL | Шум перезапускає операцію: 2.0 → 3.4 с |

Звіт: [Debounce_Test_Sheet_Test_Log_Lakhno.pdf](gpio_debounce/Debounce_Test_Sheet_Test_Log_Lakhno.pdf) — 7 TC × 5 прогонів, 10 фізичних дій дали 17 логічних подій.
