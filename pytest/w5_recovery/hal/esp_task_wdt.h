#pragma once
#include <stdint.h>
#include <stdbool.h>
#include "esp_system.h"
typedef struct { uint32_t timeout_ms; uint32_t idle_core_mask; bool trigger_panic; } esp_task_wdt_config_t;
typedef void* TaskHandle_t;
#ifndef portNUM_PROCESSORS
#define portNUM_PROCESSORS 2
#endif
esp_err_t esp_task_wdt_init(const esp_task_wdt_config_t* config);
esp_err_t esp_task_wdt_reconfigure(const esp_task_wdt_config_t* config);
esp_err_t esp_task_wdt_init(uint32_t timeout_s, bool panic);  // IDF4 / core 2.x
esp_err_t esp_task_wdt_deinit(void);
esp_err_t esp_task_wdt_add(TaskHandle_t task);
esp_err_t esp_task_wdt_delete(TaskHandle_t task);
esp_err_t esp_task_wdt_reset(void);
