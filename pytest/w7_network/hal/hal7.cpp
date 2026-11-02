// Host model of the Arduino-ESP32 API surface used by the Webinar 7 IoT node.
// Runs the UNMODIFIED sketch.ino on Linux as a black box:
//   stdin  -> UART0 RX (Serial.available / read / readStringUntil)
//   stdout <- UART0 TX, one line per output line: "@T <device_ms> <text>"
//            GPIO changes:                         "@HW <device_ms> GPIO<n>=<v>"
// Time: device ms run HAL_SCALE times faster than wall clock (default x5).
// Heap: ESP.getFreeHeap() = HEAP_TOTAL - live bytes allocated via operator new
//       (all dynamic allocations of the firmware, incl. String) - a fixed
//       baseline. This models leaks/fragmentation-free growth only.
#include "Arduino.h"
#include "DHTesp.h"
#include <atomic>
#include <chrono>
#include <deque>
#include <mutex>
#include <new>
#include <stdarg.h>
#include <thread>
#include <unistd.h>

void setup();
void loop();

HardwareSerial Serial;
EspClass ESP;

static double g_scale = 5.0;
static std::chrono::steady_clock::time_point g_t0;
static std::mutex g_rx_mu;
static std::deque<uint8_t> g_rx;
static std::atomic<bool> g_eof{false};
static std::string g_txline;
static std::mutex g_out_mu;

// ---------------- heap model ----------------
static std::atomic<long long> g_live{0};
static const long long HEAP_TOTAL = 327680;   // ESP32 DRAM heap region (approx.)
static const long long HEAP_BASELINE = 40000; // WiFi/RTOS/static use at boot
struct Hdr { size_t n; size_t pad; };
void* operator new(size_t n) {
  Hdr* h = (Hdr*)malloc(sizeof(Hdr) + n);
  if (!h) throw std::bad_alloc();
  h->n = n; g_live += (long long)n;
  return h + 1;
}
void* operator new[](size_t n) { return operator new(n); }
void operator delete(void* p) noexcept {
  if (!p) return;
  Hdr* h = (Hdr*)p - 1; g_live -= (long long)h->n; free(h);
}
void operator delete[](void* p) noexcept { operator delete(p); }
void operator delete(void* p, size_t) noexcept { operator delete(p); }
void operator delete[](void* p, size_t) noexcept { operator delete(p); }

uint32_t EspClass::getFreeHeap() {
  long long f = HEAP_TOTAL - HEAP_BASELINE - g_live.load();
  return f < 0 ? 0 : (uint32_t)f;
}
void EspClass::restart() { fflush(stdout); _exit(3); }

// ---------------- time ----------------
static double now_ms() {
  auto d = std::chrono::steady_clock::now() - g_t0;
  return std::chrono::duration<double, std::milli>(d).count() * g_scale;
}
unsigned long millis() { return (unsigned long)(uint32_t)now_ms(); }
unsigned long micros() { return (unsigned long)(uint32_t)(now_ms() * 1000.0); }
void delay(uint32_t ms) { std::this_thread::sleep_for(std::chrono::microseconds((long long)(ms * 1000.0 / g_scale))); }
void delayMicroseconds(uint32_t us) { std::this_thread::sleep_for(std::chrono::microseconds((long long)(us / g_scale))); }
void yield() {}

// ---------------- GPIO ----------------
static int g_pin[64];
void pinMode(uint8_t, uint8_t) {}
void digitalWrite(uint8_t pin, uint8_t val) {
  if (pin < 64 && g_pin[pin] != val) {
    g_pin[pin] = val;
    std::lock_guard<std::mutex> lk(g_out_mu);
    fprintf(stdout, "@HW %.1f GPIO%u=%u\n", now_ms(), pin, val);
    fflush(stdout);
  }
}
int digitalRead(uint8_t pin) { return pin < 64 ? g_pin[pin] : 0; }

// ---------------- UART ----------------
size_t HardwareSerial::write(const uint8_t* b, size_t n) {
  std::lock_guard<std::mutex> lk(g_out_mu);
  for (size_t i = 0; i < n; i++) {
    char c = (char)b[i];
    if (c == '\r') continue;
    if (c == '\n') {
      fprintf(stdout, "@T %.1f %s\n", now_ms(), g_txline.c_str());
      fflush(stdout);
      g_txline.clear();
    } else g_txline += c;
  }
  return n;
}
size_t Print::printf(const char* fmt, ...) {
  char buf[1024];
  va_list ap; va_start(ap, fmt);
  int n = vsnprintf(buf, sizeof buf, fmt, ap);
  va_end(ap);
  if (n < 0) return 0;
  if (n >= (int)sizeof buf) n = sizeof buf - 1;
  return write((const uint8_t*)buf, (size_t)n);
}
int HardwareSerial::available() { std::lock_guard<std::mutex> lk(g_rx_mu); return (int)g_rx.size(); }
int HardwareSerial::read() {
  std::lock_guard<std::mutex> lk(g_rx_mu);
  if (g_rx.empty()) return -1;
  int c = g_rx.front(); g_rx.pop_front(); return c;
}
int HardwareSerial::peek() { std::lock_guard<std::mutex> lk(g_rx_mu); return g_rx.empty() ? -1 : g_rx.front(); }
String HardwareSerial::readStringUntil(char term) {
  std::string s;
  double start = now_ms();
  while (now_ms() - start < (double)timeout_) {
    int c = read();
    if (c < 0) { std::this_thread::sleep_for(std::chrono::microseconds(200)); continue; }
    if ((char)c == term) break;
    s += (char)c;
    start = now_ms();
  }
  return String(s);
}
String HardwareSerial::readString() { return readStringUntil('\0'); }

// ---------------- DHT22 ----------------
void DHTesp::setup(uint8_t pin, DHT_MODEL_t) { pin_ = pin; }
TempAndHumidity DHTesp::getTempAndHumidity() { status_ = ERROR_NONE; return {24.5f, 45.0f}; }
float DHTesp::getTemperature() { return 24.5f; }
float DHTesp::getHumidity() { return 45.0f; }
const char* DHTesp::getStatusString() { return "OK"; }

// ---------------- main ----------------
static void rx_thread() {
  uint8_t b[256];
  for (;;) {
    ssize_t n = ::read(0, b, sizeof b);
    if (n <= 0) { g_eof = true; return; }
    std::lock_guard<std::mutex> lk(g_rx_mu);
    for (ssize_t i = 0; i < n; i++) if (g_rx.size() < 256) g_rx.push_back(b[i]);  // 256 B FIFO
  }
}

int main() {
  if (const char* s = getenv("HAL_SCALE")) g_scale = atof(s);
  setvbuf(stdout, nullptr, _IOFBF, 1 << 16);
  g_t0 = std::chrono::steady_clock::now();
  std::thread(rx_thread).detach();
  setup();
  for (;;) {
    loop();
    if (g_eof) {
      // drain pending input then stop
      if (Serial.available() == 0) { fflush(stdout); _exit(0); }
    }
    std::this_thread::sleep_for(std::chrono::microseconds(50));
  }
}
long random(long howbig) { return howbig <= 0 ? 0 : (long)(rand() % howbig); }
long random(long a, long b) { return b <= a ? a : a + random(b - a); }
void randomSeed(unsigned long s) { srand((unsigned)s); }
