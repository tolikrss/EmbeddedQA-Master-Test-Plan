#pragma once
#include <stdint.h>
#include "esp_system.h"
typedef enum {
  GPIO_NUM_0 = 0, GPIO_NUM_2 = 2, GPIO_NUM_4 = 4, GPIO_NUM_5 = 5, GPIO_NUM_15 = 15,
  GPIO_NUM_25 = 25, GPIO_NUM_26 = 26, GPIO_NUM_27 = 27, GPIO_NUM_32 = 32, GPIO_NUM_33 = 33
} gpio_num_t;
typedef enum {
  ESP_SLEEP_WAKEUP_UNDEFINED = 0, ESP_SLEEP_WAKEUP_ALL, ESP_SLEEP_WAKEUP_EXT0,
  ESP_SLEEP_WAKEUP_EXT1, ESP_SLEEP_WAKEUP_TIMER, ESP_SLEEP_WAKEUP_TOUCHPAD,
  ESP_SLEEP_WAKEUP_ULP, ESP_SLEEP_WAKEUP_GPIO, ESP_SLEEP_WAKEUP_UART
} esp_sleep_wakeup_cause_t;
esp_err_t esp_sleep_enable_timer_wakeup(uint64_t time_in_us);
esp_err_t esp_sleep_enable_ext0_wakeup(gpio_num_t gpio_num, int level);
esp_sleep_wakeup_cause_t esp_sleep_get_wakeup_cause(void);
[[noreturn]] void esp_deep_sleep_start(void);
