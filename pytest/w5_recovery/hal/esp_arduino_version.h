#pragma once
// Model of Arduino-ESP32 core 3.0.x (ESP-IDF 5.1), as used by current Wokwi templates.
#define ESP_ARDUINO_VERSION_MAJOR 3
#define ESP_ARDUINO_VERSION_MINOR 0
#define ESP_ARDUINO_VERSION_PATCH 7
#define ESP_ARDUINO_VERSION_VAL(major, minor, patch) ((major << 16) | (minor << 8) | (patch))
#define ESP_ARDUINO_VERSION ESP_ARDUINO_VERSION_VAL(3, 0, 7)
