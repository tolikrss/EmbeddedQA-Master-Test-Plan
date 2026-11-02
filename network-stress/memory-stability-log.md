# Memory Stability Log: W7 IoT node

Джерело: `STATUS` після кожної ітерації в тестах [`test_MEM01_heap_trend_online_stress`](buggy/run1/logs/test_MEM01_heap_trend_online_stress.log) і [`test_MEM02_heap_and_buffer_offline_stress`](buggy/run1/logs/test_MEM02_heap_and_buffer_offline_stress.log), прогін buggy/run1. Прогони 2 і 3 дали ті самі значення. Контроль — [demo/run1](demo/run1/logs/).
Збірка моделі: `-O0 -fno-allocation-dce` (див. «Як цей витік спершу пропустили» нижче).

## A. Online stress: 10 × `STRESS 100` (homework_buggy)

| Iteration | Action | Network state | Buffer | Sent | Dropped | Duplicates | Free heap, B | Δ від baseline | Notes |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 0 | Baseline | CONNECTED | 0 | 0 | 0 | 0 | 286847 | 0 | 287057 одразу після boot, далі 286847 (−210 B одноразово, так само в demo) |
| 1 | STRESS 100 | CONNECTED | 0 | 100 | 0 | 0 | 280447 | −6400 | |
| 2 | STRESS 100 | CONNECTED | 0 | 200 | 0 | 0 | 274047 | −12800 | |
| 3 | STRESS 100 | CONNECTED | 0 | 300 | 0 | 0 | 267647 | −19200 | |
| 4 | STRESS 100 | CONNECTED | 0 | 400 | 0 | 0 | 261247 | −25600 | |
| 5 | STRESS 100 | CONNECTED | 0 | 500 | 0 | 0 | 254847 | −32000 | |
| 6 | STRESS 100 | CONNECTED | 0 | 600 | 0 | 0 | 248447 | −38400 | |
| 7 | STRESS 100 | CONNECTED | 0 | 700 | 0 | 0 | 242047 | −44800 | |
| 8 | STRESS 100 | CONNECTED | 0 | 800 | 0 | 0 | 235647 | −51200 | |
| 9 | STRESS 100 | CONNECTED | 0 | 900 | 0 | 0 | 229247 | −57600 | |
| 10 | STRESS 100 | CONNECTED | 0 | 1000 | 0 | 0 | 222847 | **−64000** | −64 B на повідомлення, лінійно, без повернення |

**demo_firmware, той самий сценарій:** 286847 B в усіх 11 точках (Δ = 0).

## B. Offline stress: 5 × (`NET DOWN` → `STRESS 100` → `NET UP`) (homework_buggy)

| Iteration | Action | Network state | Buffer | Sent | Dropped | Duplicates | Free heap, B | Notes |
|---:|---|---|---:|---:|---:|---:|---:|---|
| 0 | Baseline | CONNECTED | 0 | 0 | 0 | 0 | 286847 | |
| 1 | offline STRESS 100 | BACKOFF | **100** | 0 | **0** | 0 | 280447 | −6400 B вже під час створення повідомлень; ємність 8, occupancy 100 |
| 1 | NET UP | CONNECTED | 0 | 200 | 0 | **100** | 280447 | 200 publish = 8 унікальних ID (93–100) × 25; flush пам'ять не повертає |
| 2 | offline / NET UP | BACKOFF → CONNECTED | 100 → 0 | 400 | 0 | 200 | 274047 | |
| 3 | offline / NET UP | BACKOFF → CONNECTED | 100 → 0 | 600 | 0 | 300 | 267647 | |
| 4 | offline / NET UP | BACKOFF → CONNECTED | 100 → 0 | 800 | 0 | 400 | 261247 | |
| 5 | offline / NET UP | BACKOFF → CONNECTED | 100 → 0 | 1000 | 0 | 500 | 254847 | −32000 B за 500 повідомлень |

**demo_firmware:** buffer 8 (не 100), heap 286847 B в усіх точках.

## Висновок

- **Heap: FAIL.** Систематичне незворотне падіння −64 B на кожне створене повідомлення, онлайн і офлайн, 3/3 прогони. Еталон із тим самим harness стабільний, тож витік — у прошивці (W7 BUG-04, [MTP-BUG-09](../bug-reports/bug-reports.md#mtp-bug-09-новий-w7-витік-heap-на-кожне-повідомлення)).
- **Прогноз:** ≈286 KB / 64 B ≈ 4 500 повідомлень до вичерпання heap у моделі. При телеметрії раз на 10 с це ≈12 год. На реальному ESP32 падіння настане раніше: Wi-Fi/MQTT-стеку потрібен вільний heap, а найбільший вільний блок через фрагментацію менший за загальний обсяг.
- **Дані:** окремо від витоку буфер «вміщує» 100 записів при ємності 8. 92 з кожних 100 повідомлень втрачено, а 8 решти опубліковано по 25 разів, і все це при `dropped=0` (W7 BUG-02, BUG-01).

## Як цей витік спершу пропустили

Перший прогін цього набору зібрав модель з `-O1` і показав рівний heap (286847 B у всіх точках) — тобто хибний PASS. Під час звірки з набором, зданим у завданні W7, де витік було знайдено, з'ясувалося: на `-O1` GCC має право прибрати пару `new`/`delete` чи невикористану алокацію, і модель обліку heap її не бачить. Після перезбирання з `-O0 -fno-allocation-dce` buggy-збірка показує витік, а demo лишається рівною.
Урок для стратегії: **PASS теж потребує перевірки середовища**, і тут вона знайшла сліпу зону harness. Прапорці збірки зафіксовано в [`pytest/w7_network/build.sh`](../pytest/w7_network/build.sh).

## Обмеження цього evidence

Host-модель рахує лише динамічні алокації прошивки (`operator new/delete`, включно з `String`). Розмір витоку на повідомлення залежить від того, як модель рахує накладні витрати алокатора (64 B тут, 72 B у наборі здачі W7). Модель **не відтворює** фрагментацію heap, алокації Wi-Fi/lwIP/MQTT-стеку ESP-IDF і стек задач FreeRTOS, а тривалість прогону — секунди, а не доби. Після виправлення потрібен soak на платі: 24 год, флапи мережі кожні 5 хв, `ESP.getFreeHeap()` і `heap_caps_get_largest_free_block()` раз на хвилину (T-38 у [Test Matrix](../docs/test-matrix.md)).
