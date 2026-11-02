# pytest/

Автотести на Python / pytest. Вони тестують незмінені прошивки як black box: через UART і спостережуваний стан GPIO.

**Що автоматизовано і чому:** лише перевірки, які повторювані й детерміновані, а вручну їх не виконати. Це fault injection у точну мілісекунду (вікно між двома записами NVS ≈26 мс), повтори ×10 / ×20, ID-трасування сотень повідомлень, межі CLI.
**Що не автоматизовано:** W1 Smart Gate (ручні сценарії в Wokwi GUI; наступний крок — Wokwi CI, як [для debounce](../wokwi/debounce_scenarios/)) і W4 (аналіз VCD — напівавтоматично власним декодером).

| Папка | Підсистема | Кейсів | Buggy (3 прогони) | Контроль на еталоні | Ризики |
|---|---|---:|---|---|---|
| [w5_recovery/](w5_recovery/) | Sleep / WDT / brown-out / NVS / сенсор / кнопка | 124 | 78 PASS / 46 FAIL, усі FAIL 3/3 | 121 / 124 (3 FAIL — прогалина вимог в еталоні) | R02, R03, R05, R10, R13 |
| [w6_json_cli/](w6_json_cli/) | Serial JSON CLI | 62 | 53 PASS / 9 FAIL, 3/3 | 62 / 62 | R02, R07, R10 |
| [w7_network/](w7_network/) | Network: backoff, офлайн-буфер, дублікати, heap | 21 | 11 PASS / 10 FAIL, 3/3 | 21 / 21 | R06, R09, R11 |

- Результати W5 (summary, JUnit, ключові логи): [w5_recovery/evidence/](w5_recovery/evidence/).
- W6: результати й test sheet — [w6_json_cli/](w6_json_cli/); код тестів — окремий репозиторій [tolikrss/Webinar6_Pytest](https://github.com/tolikrss/Webinar6_Pytest).
- Результати W7 (3 прогони + еталон, логи, CSV, графіки): [../network-stress/](../network-stress/).

## Як це працює

`sketch.ino` компілюється g++ разом із host-моделлю Arduino-ESP32 API (`hal/`): UART 115200 з RX FIFO 256 B, GPIO, millis / delay з прискореним часом, Task WDT, NVS у файлі, deep sleep, brown-out як reset, DHT22, облік heap. Python-драйвер надсилає CLI-рядки й читає кожен рядок відповіді з часовою міткою пристрою. Тест бачить лише те, що бачив би тестувальник із Serial Monitor і логічним аналізатором.

W7 збирається з `-O0 -fno-allocation-dce`: на `-O1` GCC може прибрати алокацію, і облік heap її не побачить. Так перший прогін пропустив витік W7 BUG-04.

Чого модель **не** відтворює: аналогову просадку живлення, Wi-Fi / lwIP стек, фрагментацію heap ESP-IDF, радіо — див. Out of scope у [Master Test Plan](../master-test-plan.md#22-out-of-scope-свідомо-і-чому).

## Як FAIL відрізняється від проблеми harness

Test logic → environment → communication → requirement → firmware:
1. Той самий набір проходить на еталонній прошивці — отже, логіка тесту й середовище коректні.
2. ASan / UBSan без помилок — модель не псує пам'ять.
3. Кожен FAIL — 3/3 прогони.
4. Неоднозначні вимоги винесено як питання, а не як дефекти.

## Запуск (Linux, g++ C++17, Python 3.10+)

Прошивки курсу тут не публікуються. Покладіть `sketch.ino` з курсового пакета в `firmware/<buggy|demo>/`.

```bash
pip install pytest pytest-html pytest-timeout   # W7 потребує лише pytest

cd pytest/w7_network
cp <course>/webinar_7_iot_network_testing/homework_buggy/sketch.ino firmware/buggy/
cp <course>/webinar_7_iot_network_testing/demo_firmware/sketch.ino  firmware/demo/
./run_all.sh                                       # build + demo ×1 + buggy ×3 + results/summary.md
python3 -m pytest --fw=buggy --out=results/adhoc tests -k BUF   # вибірково

cd ../w5_recovery
cp <course>/embedded_qa_wokwi_lab/homework_buggy/sketch.ino firmware/buggy/
cp <course>/embedded_qa_wokwi_lab/demo/sketch.ino          firmware/demo/
./run_all.sh
```

## Набір W7 (`w7_network/tests/test_network.py`)

| Test | Вимога W7 | Що перевіряє | Техніка |
|---|---|---|---|
| NET01 | R1, R2 | Вузол відповідає на STATUS під час 10 с офлайну | Fault injection |
| NET02 | R2 | Backoff не спадає, ≥ початкового, ≤ 10 спроб / 20 с | Timing |
| NET03 | R5 | `NET UP` → CONNECTED, broker true | Recovery |
| BUF01 | R3 | 5 офлайн-SEND потрапляють у буфер | Equivalence |
| BUF02 | R5, R6 | Flush: кожен ID рівно раз, FIFO, `duplicates=0` | ID tracing |
| BUF03 ×4 | R4 | N = 7 / 8 / 9 / 12: occupancy ≤ 8, `dropped = N − 8` | BVA |
| BUF04 ×3 | R4 | N = 8 / 9 / 12: опубліковано 8 найновіших у порядку | BVA, ID tracing |
| DUP01 | R6 | 5 флапів × 3 повідомлення без повторних ID | Repeat |
| MEM01 | R7 | Heap після 10 × `STRESS 100` онлайн (Δ ≥ −1 KB) | Memory trend |
| MEM02 | R4, R7 | 5 × офлайн `STRESS 100`: occupancy ≤ 8 і heap | Stress |
| OBS01 | R8 | STATUS містить усі поля | Observability |
| NEG01 ×5 | — | Невідомі команди → ERROR, стан без змін | Negative |
