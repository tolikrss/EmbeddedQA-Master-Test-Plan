# Wokwi scenarios для повторення тестів

Покладіть файл поруч із `diagram.json` і запустіть через Wokwi CLI:

```
wokwi-cli --scenario tc06_noise_5ms.yaml --timeout 15000 .
```

Сценарії використовують лише кроки `set-control`, `delay`, `wait-serial`, як і `scenario.yaml` з курсу.
Для `tc06` і `tc07` успішне завершення `wait-serial: 'LOGICAL EVENT #…'` означає, що дефект відтворено.
Вручну те саме видно в GUI: коротко натисніть клавішу **N** (кнопка NOISE без брязкоту). Будь-яке натискання довше ~1 мс дає LOGICAL EVENT.
