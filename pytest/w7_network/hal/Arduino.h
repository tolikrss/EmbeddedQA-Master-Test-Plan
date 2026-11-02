// Host model of the Arduino-ESP32 API surface used by the lab firmware.
// Purpose: run the UNMODIFIED sketch.ino on Linux so a pytest harness can
// test it as a black box (serial in/out + GPIO + power/fault injection).
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include <string>

typedef uint8_t byte;
typedef bool boolean;

#define HIGH 1
#define LOW 0
#define INPUT 0x01
#define OUTPUT 0x03
#define INPUT_PULLUP 0x05
#define INPUT_PULLDOWN 0x09

void pinMode(uint8_t pin, uint8_t mode);
void digitalWrite(uint8_t pin, uint8_t val);
int digitalRead(uint8_t pin);
unsigned long millis();
unsigned long micros();
void delay(uint32_t ms);
void delayMicroseconds(uint32_t us);
void yield();

class String {
 public:
  String() {}
  String(const char* s) : s_(s ? s : "") {}
  String(const std::string& s) : s_(s) {}
  String(char c) : s_(1, c) {}
  String(int v) : s_(std::to_string(v)) {}
  String(unsigned v) : s_(std::to_string(v)) {}
  String(long v) : s_(std::to_string(v)) {}
  String(unsigned long v) : s_(std::to_string(v)) {}
  unsigned int length() const { return (unsigned)s_.size(); }
  const char* c_str() const { return s_.c_str(); }
  void trim() {
    size_t b = 0, e = s_.size();
    while (b < e && isspace((unsigned char)s_[b])) b++;
    while (e > b && isspace((unsigned char)s_[e - 1])) e--;
    s_ = s_.substr(b, e - b);
  }
  bool startsWith(const String& p) const { return s_.compare(0, p.s_.size(), p.s_) == 0 && s_.size() >= p.s_.size(); }
  bool endsWith(const String& p) const { return s_.size() >= p.s_.size() && s_.compare(s_.size() - p.s_.size(), p.s_.size(), p.s_) == 0; }
  int indexOf(char c, unsigned from = 0) const { auto p = s_.find(c, from); return p == std::string::npos ? -1 : (int)p; }
  int indexOf(const String& t, unsigned from = 0) const { auto p = s_.find(t.s_, from); return p == std::string::npos ? -1 : (int)p; }
  String substring(unsigned from) const { return from >= s_.size() ? String() : String(s_.substr(from)); }
  String substring(unsigned from, unsigned to) const {
    if (from > to) { unsigned t = from; from = to; to = t; }
    if (from >= s_.size()) return String();
    if (to > s_.size()) to = (unsigned)s_.size();
    return String(s_.substr(from, to - from));
  }
  long toInt() const { return atol(s_.c_str()); }   // Arduino semantics: atol
  float toFloat() const { return (float)atof(s_.c_str()); }
  void toLowerCase() { for (auto& c : s_) c = (char)tolower((unsigned char)c); }
  void toUpperCase() { for (auto& c : s_) c = (char)toupper((unsigned char)c); }
  bool equals(const String& o) const { return s_ == o.s_; }
  bool equalsIgnoreCase(const String& o) const { return strcasecmp(s_.c_str(), o.s_.c_str()) == 0; }
  bool isEmpty() const { return s_.empty(); }
  char charAt(unsigned i) const { return i < s_.size() ? s_[i] : 0; }
  char operator[](unsigned i) const { return charAt(i); }
  void reserve(unsigned n) { s_.reserve(n); }
  String& operator+=(const String& o) { s_ += o.s_; return *this; }
  String& operator+=(const char* o) { s_ += o; return *this; }
  String& operator+=(char c) { s_ += c; return *this; }
  bool concat(char c) { s_ += c; return true; }
  bool concat(const String& o) { s_ += o.s_; return true; }
  friend String operator+(const String& a, const String& b) { return String(a.s_ + b.s_); }
  friend String operator+(const String& a, const char* b) { return String(a.s_ + b); }
  friend String operator+(const char* a, const String& b) { return String(std::string(a) + b.s_); }
  bool operator==(const String& o) const { return s_ == o.s_; }
  bool operator==(const char* o) const { return s_ == o; }
  bool operator!=(const String& o) const { return s_ != o.s_; }
  bool operator!=(const char* o) const { return s_ != o; }
 private:
  std::string s_;
};

class Print {
 public:
  virtual size_t write(const uint8_t* b, size_t n) = 0;
  size_t write(uint8_t c) { return write(&c, 1); }
  size_t print(const char* s) { return write((const uint8_t*)s, strlen(s)); }
  size_t print(const String& s) { return print(s.c_str()); }
  size_t print(char c) { return write((uint8_t)c); }
  size_t print(int v) { return printf("%d", v); }
  size_t print(unsigned v) { return printf("%u", v); }
  size_t print(long v) { return printf("%ld", v); }
  size_t print(unsigned long v) { return printf("%lu", v); }
  size_t print(double v, int digits = 2) { return printf("%.*f", digits, v); }
  size_t println() { return print("\r\n"); }
  template <typename T> size_t println(T v) { size_t n = print(v); return n + println(); }
  size_t println(double v, int digits) { size_t n = print(v, digits); return n + println(); }
  size_t printf(const char* fmt, ...) __attribute__((format(printf, 2, 3)));
};

class HardwareSerial : public Print {
 public:
  void begin(unsigned long baud) { (void)baud; }
  int available();
  int read();
  int peek();
  String readStringUntil(char term);
  String readString();
  void setTimeout(unsigned long ms) { timeout_ = ms; }
  unsigned long timeout_ = 1000;
  void flush() {}
  size_t write(const uint8_t* b, size_t n) override;
  using Print::write;
  operator bool() const { return true; }
};
extern HardwareSerial Serial;

class EspClass {
 public:
  uint32_t getFreeHeap();
  [[noreturn]] void restart();
  uint32_t getCpuFreqMHz() { return 240; }
};
extern EspClass ESP;

// Arduino-ESP32 helpers (std::min/max as in arduino-esp32 3.x, constrain macro)
#include <algorithm>
using std::min;
using std::max;
#define constrain(amt, low, high) ((amt) < (low) ? (low) : ((amt) > (high) ? (high) : (amt)))
long random(long howbig);
long random(long howsmall, long howbig);
void randomSeed(unsigned long seed);
