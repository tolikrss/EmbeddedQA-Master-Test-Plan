#pragma once
#include <stdint.h>
struct TempAndHumidity { float temperature; float humidity; };
class DHTesp {
 public:
  enum DHT_MODEL_t { AUTO_DETECT, DHT11, DHT22, AM2302, RHT03 };
  enum DHT_ERROR_t { ERROR_NONE = 0, ERROR_TIMEOUT, ERROR_CHECKSUM };
  void setup(uint8_t pin, DHT_MODEL_t model = AUTO_DETECT);
  TempAndHumidity getTempAndHumidity();
  float getTemperature();
  float getHumidity();
  DHT_ERROR_t getStatus() { return status_; }
  const char* getStatusString();
  int getMinimumSamplingPeriod() { return 2000; }
 private:
  DHT_ERROR_t status_ = ERROR_NONE;
  uint8_t pin_ = 0;
};
