# uart-cli/

W3 UART CLI: boundary і stress-тести сервісного інтерфейсу (ризик R07).

| | |
|---|---|
| Збірка | UART CLI HOMEWORK DEVICE v2.0, ESP32 DevKit v1, 115200 8N1, LF |
| Виконано | 26 тест-кейсів × 5 прогонів (3 пакетом, 2 посимвольно): 14 PASS / 12 FAIL; ще 105 прогонів під ASan / UBSan без помилок пам'яті |
| Техніки | BVA (speed, timeout, int32), sweep довжини рядка 1…300 + 400 / 1000 / 5000, negative (unknown, empty, спецсимволи, Unicode), stress (burst 100 команд, 500 випадкових байтів), state / sequence |
| Дефекти | 8: 2 Critical, 4 Major, 1 Medium, 1 Minor |

| Файл | Що в ньому |
|---|---|
| [UART_CLI_Serial_Log.txt](UART_CLI_Serial_Log.txt) | Повний transcript TX / RX з часовими мітками для кожного TC, sweep довжини, додатки A–C |
| [UART_CLI_Test_Report.docx](UART_CLI_Test_Report.docx) | Таблиця виконання, boundary / length analysis, 8 bug reports |
| [UART_CLI_QA_Conclusion.docx](UART_CLI_QA_Conclusion.docx) | QA conclusion практики |

**Ключова межа:** 40 символів — OK, 41 — `*** SYSTEM FAULT *** input line boundary failure` + reboot, і хвіст рядка виконується як команда (§TC-15, TC-18 у transcript). Термінатор не рахується; вміст рядка ролі не грає. Bug report — [MTP-BUG-08](../bug-reports/bug-reports.md#mtp-bug-08-рядок-із-41-символу-в-uart-cli-перезавантажує-пристрій-а-хвіст-рядка-виконується-як-команда).
