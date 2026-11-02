// Host-side hardware model for the ESP32 lab firmware.
//
// Channels (all owned by the pytest harness):
//   stdin  -> UART0 RX (Serial.read / Serial.available), 256-byte RX FIFO
//   stdout <- UART0 TX (everything the firmware prints)
//   stderr <- "@HW ..." hardware trace: GPIO edges, resets, sleep entry, NVS commits
//   fd $HAL_CTRL_FD -> hardware/fault-injection commands from the harness
//
// Time: one "world" millisecond == 1/HAL_SCALE real milliseconds, measured on
// CLOCK_MONOTONIC from HAL_T0_NS (spawn time chosen by the harness), so the
// harness can timestamp serial lines on the same clock.
//
// A reset or deep sleep ends this process (exit 10 / 11); the harness starts a new
// process with the proper reset reason / wake-up cause. NVS lives in a file, so
// it survives resets exactly like flash does. Each NVS entry write is atomic
// (tmp file + rename), like a real NVS entry; power can be cut between entries.
#include "Arduino.h"
#include "DHTesp.h"
#include "Preferences.h"
#include "esp_sleep.h"
#include "esp_system.h"
#include "esp_task_wdt.h"

#include <atomic>
#include <csignal>
#include <cstdarg>
#include <deque>
#include <fstream>
#include <map>
#include <mutex>
#include <sstream>
#include <thread>
#include <time.h>
#include <unistd.h>
#include <vector>

void setup();
void loop();

namespace {

constexpr int EXIT_RESET = 10;
constexpr int EXIT_SLEEP = 11;

double g_scale = 10.0;
int64_t g_t0_ns = 0;
esp_reset_reason_t g_reset_reason = ESP_RST_POWERON;
esp_sleep_wakeup_cause_t g_wake_cause = ESP_SLEEP_WAKEUP_UNDEFINED;
std::string g_nvs_file = "nvs.db";
int g_ctrl_fd = -1;

int64_t mono_ns() {
  timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (int64_t)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}
double now_ms() { return (double)(mono_ns() - g_t0_ns) / 1e6 * g_scale; }

void sleep_until_ms(double target) {
  for (;;) {
    double left = target - now_ms();
    if (left <= 0) return;
    double real_ns = left / g_scale * 1e6;
    timespec ts{(time_t)(real_ns / 1e9), (long)fmod(real_ns, 1e9)};
    nanosleep(&ts, nullptr);
  }
}

std::mutex g_trace_mu;
void hw(const char* fmt, ...) {
  char body[512];
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(body, sizeof body, fmt, ap);
  va_end(ap);
  char line[600];
  int n = snprintf(line, sizeof line, "@HW %.3f %s\n", now_ms(), body);
  std::lock_guard<std::mutex> lk(g_trace_mu);
  (void)!write(2, line, n);
}

const char* reason_name(esp_reset_reason_t r) {
  switch (r) {
    case ESP_RST_POWERON: return "POWERON";
    case ESP_RST_EXT: return "EXT";
    case ESP_RST_SW: return "SW";
    case ESP_RST_PANIC: return "PANIC";
    case ESP_RST_INT_WDT: return "INT_WDT";
    case ESP_RST_TASK_WDT: return "TASK_WDT";
    case ESP_RST_WDT: return "WDT";
    case ESP_RST_DEEPSLEEP: return "DEEPSLEEP";
    case ESP_RST_BROWNOUT: return "BROWNOUT";
    default: return "UNKNOWN";
  }
}

[[noreturn]] void chip_reset(esp_reset_reason_t why, const char* detail) {
  hw("RESET reason=%s detail=%s", reason_name(why), detail);
  _exit(EXIT_RESET);
}

void uart_tx(const char* s, size_t n) {
  while (n) {
    ssize_t w = write(1, s, n);
    if (w <= 0) return;
    s += w;
    n -= (size_t)w;
  }
}
void uart_txs(const char* s) { uart_tx(s, strlen(s)); }

// ---------------- GPIO ----------------
std::mutex g_gpio_mu;
uint8_t g_mode[40] = {0};
uint8_t g_out[40] = {0};
uint8_t g_ext[40];  // level driven by the outside world (button etc.); 0xFF = floating

// ---------------- UART RX ----------------
std::mutex g_rx_mu;
std::deque<uint8_t> g_rx;
constexpr size_t RX_FIFO = 256;

// ---------------- DHT22 model ----------------
std::mutex g_dht_mu;
std::string g_dht_mode = "ok";
float g_dht_t = 24.5f, g_dht_h = 45.0f;

// ---------------- WDT model ----------------
std::atomic<bool> g_wdt_inited{false}, g_wdt_subscribed{false}, g_wdt_panic{true};
std::atomic<uint32_t> g_wdt_timeout_ms{5000};
std::atomic<double> g_wdt_last_feed{0};
std::atomic<bool> g_wdt_thread_started{false};

void wdt_thread() {
  double last_report = -1;
  for (;;) {
    timespec ts{0, 200000};  // 0.2 ms real
    nanosleep(&ts, nullptr);
    if (!g_wdt_inited || !g_wdt_subscribed) continue;
    double t = now_ms();
    if (t - g_wdt_last_feed.load() > (double)g_wdt_timeout_ms.load()) {
      if (last_report >= 0 && t - last_report < g_wdt_timeout_ms) continue;
      last_report = t;
      char b[256];
      unsigned long ms = (unsigned long)t;
      snprintf(b, sizeof b,
               "E (%lu) task_wdt: Task watchdog got triggered. The following tasks/users did not reset the watchdog in time:\r\n"
               "E (%lu) task_wdt:  - loopTask (CPU 1)\r\n", ms, ms);
      uart_txs(b);
      hw("WDT_TIMEOUT since_feed_ms=%.1f", t - g_wdt_last_feed.load());
      if (g_wdt_panic) {
        uart_txs("\r\nabort() was called at PC 0x400d4f2b on core 0\r\n\r\nRebooting...\r\n");
        chip_reset(ESP_RST_TASK_WDT, "task_wdt_panic");
      }
    }
  }
}
void start_wdt_thread() {
  bool exp = false;
  if (g_wdt_thread_started.compare_exchange_strong(exp, true)) std::thread(wdt_thread).detach();
}

// ---------------- NVS model ----------------
struct Entry { std::string type; std::vector<uint8_t> data; };
std::mutex g_nvs_mu;
std::map<std::string, Entry> g_nvs;
bool g_nvs_loaded = false;
std::atomic<long> g_nvs_cut_after{-1};  // -1 = disarmed; N = allow N more commits, then cut power
std::atomic<int> g_nvs_cut_reason{ESP_RST_BROWNOUT};
long g_nvs_commits = 0;

std::string hex(const std::vector<uint8_t>& d) {
  static const char* H = "0123456789abcdef";
  std::string s;
  for (uint8_t b : d) { s += H[b >> 4]; s += H[b & 15]; }
  return s;
}
std::vector<uint8_t> unhex(const std::string& s) {
  std::vector<uint8_t> d;
  for (size_t i = 0; i + 1 < s.size(); i += 2) d.push_back((uint8_t)strtoul(s.substr(i, 2).c_str(), nullptr, 16));
  return d;
}
void nvs_load() {
  if (g_nvs_loaded) return;
  g_nvs_loaded = true;
  std::ifstream f(g_nvs_file);
  std::string line;
  while (std::getline(f, line)) {
    std::istringstream is(line);
    std::string k, t, h;
    if (is >> k >> t) { is >> h; g_nvs[k] = Entry{t, unhex(h)}; }
  }
}
void nvs_flush_file() {
  std::string tmp = g_nvs_file + ".tmp";
  {
    std::ofstream f(tmp, std::ios::trunc);
    for (auto& kv : g_nvs) f << kv.first << ' ' << kv.second.type << ' ' << hex(kv.second.data) << '\n';
  }
  rename(tmp.c_str(), g_nvs_file.c_str());  // atomic: an NVS entry is either old or new
}
// Every entry write/erase goes through here: this is where power can be cut.
void nvs_commit(const std::string& key, const char* op) {
  long c = g_nvs_cut_after.load();
  if (c == 0) {
    hw("NVS_CUT before %s key=%s (commits_done=%ld)", op, key.c_str(), g_nvs_commits);
    chip_reset((esp_reset_reason_t)g_nvs_cut_reason.load(), "power_cut_during_nvs_write");
  }
  nvs_flush_file();
  g_nvs_commits++;
  hw("NVS_COMMIT #%ld %s key=%s", g_nvs_commits, op, key.c_str());
  if (c > 0) g_nvs_cut_after = c - 1;
}

// ---------------- control channel ----------------
void apply_btn(int level) {
  std::lock_guard<std::mutex> lk(g_gpio_mu);
  g_ext[4] = (uint8_t)level;
}
void ctrl_thread() {
  FILE* f = fdopen(g_ctrl_fd, "r");
  if (!f) return;
  char buf[4096];
  while (fgets(buf, sizeof buf, f)) {
    std::istringstream is(buf);
    std::string cmd;
    is >> cmd;
    if (cmd == "BTN") {
      int l; is >> l; apply_btn(l); hw("BTN level=%d", l);
    } else if (cmd == "BTNSEQ") {  // BTNSEQ level:world_ms,level:world_ms,...
      std::string seq; is >> seq;
      std::stringstream ss(seq);
      std::string item;
      while (std::getline(ss, item, ',')) {
        int l = atoi(item.substr(0, item.find(':')).c_str());
        double d = atof(item.substr(item.find(':') + 1).c_str());
        apply_btn(l);
        hw("BTN level=%d", l);
        sleep_until_ms(now_ms() + d);
      }
      hw("BTNSEQ_DONE");
    } else if (cmd == "DHT") {
      std::lock_guard<std::mutex> lk(g_dht_mu);
      is >> g_dht_mode;
      if (g_dht_mode == "ok" || g_dht_mode == "raw") is >> g_dht_t >> g_dht_h;
      hw("DHT mode=%s t=%.1f h=%.1f", g_dht_mode.c_str(), g_dht_t, g_dht_h);
    } else if (cmd == "BROWNOUT") {
      uart_txs("\r\nBrownout detector was triggered\r\n\r\n");
      chip_reset(ESP_RST_BROWNOUT, "injected_brownout");
    } else if (cmd == "POWERCUT") {
      chip_reset(ESP_RST_POWERON, "injected_power_cycle");
    } else if (cmd == "NVSCUT") {  // NVSCUT <commits_allowed> <BROWNOUT|POWERON>
      long n; std::string why;
      is >> n >> why;
      g_nvs_cut_reason = (why == "POWERON") ? ESP_RST_POWERON : ESP_RST_BROWNOUT;
      g_nvs_cut_after = n;
      hw("NVSCUT armed allow=%ld reason=%s", n, why.c_str());
    } else if (cmd == "PING") {
      hw("PONG");
    }
  }
}

// UART RX paced at 115200 8N1 (10 bits per byte -> 0.0868 ms per byte, device time):
// the harness may write a whole line at once, the firmware sees it arrive byte by byte.
std::mutex g_rxp_mu;
std::deque<uint8_t> g_rx_wire;
void rx_reader_thread() {
  uint8_t b[512];
  for (;;) {
    ssize_t n = read(0, b, sizeof b);
    if (n <= 0) { timespec ts{0, 5000000}; nanosleep(&ts, nullptr); continue; }
    std::lock_guard<std::mutex> lk(g_rxp_mu);
    g_rx_wire.insert(g_rx_wire.end(), b, b + n);
  }
}
void rx_thread() {
  const double byte_ms = 10.0 * 1000.0 / 115200.0;
  double t_next = now_ms();
  for (;;) {
    timespec ts{0, 100000};
    nanosleep(&ts, nullptr);
    double t = now_ms();
    std::lock_guard<std::mutex> lk(g_rxp_mu);
    if (g_rx_wire.empty()) { t_next = t; continue; }
    std::lock_guard<std::mutex> lk2(g_rx_mu);
    while (!g_rx_wire.empty() && t_next <= t) {
      uint8_t c = g_rx_wire.front();
      g_rx_wire.pop_front();
      t_next += byte_ms;
      if (g_rx.size() >= RX_FIFO) { hw("UART_RX_OVERFLOW"); continue; }
      g_rx.push_back(c);
    }
  }
}

void on_fatal(int sig) {
  char b[160];
  snprintf(b, sizeof b, "\r\nGuru Meditation Error: Core  1 panic'ed (host signal %d)\r\n\r\nRebooting...\r\n", sig);
  uart_txs(b);
  chip_reset(ESP_RST_PANIC, "cpu_exception");
}

}  // namespace

// ================= Arduino API =================
HardwareSerial Serial;
EspClass ESP;

size_t HardwareSerial::write(const uint8_t* b, size_t n) { uart_tx((const char*)b, n); return n; }
int HardwareSerial::available() { std::lock_guard<std::mutex> lk(g_rx_mu); return (int)g_rx.size(); }
int HardwareSerial::read() {
  std::lock_guard<std::mutex> lk(g_rx_mu);
  if (g_rx.empty()) return -1;
  int c = g_rx.front(); g_rx.pop_front(); return c;
}
int HardwareSerial::peek() { std::lock_guard<std::mutex> lk(g_rx_mu); return g_rx.empty() ? -1 : g_rx.front(); }

size_t Print::printf(const char* fmt, ...) {
  char buf[512];
  va_list ap;
  va_start(ap, fmt);
  int n = vsnprintf(buf, sizeof buf, fmt, ap);
  va_end(ap);
  if (n < 0) return 0;
  if (n >= (int)sizeof buf) n = sizeof buf - 1;
  return write((const uint8_t*)buf, (size_t)n);
}

uint32_t EspClass::getFreeHeap() { return 298412; }  // not modelled: constant
void EspClass::restart() { esp_restart(); }

void pinMode(uint8_t pin, uint8_t mode) {
  if (pin >= 40) return;
  std::lock_guard<std::mutex> lk(g_gpio_mu);
  g_mode[pin] = mode;
  hw("PINMODE pin=%u mode=%u", pin, mode);
}
void digitalWrite(uint8_t pin, uint8_t val) {
  if (pin >= 40) return;
  bool changed;
  {
    std::lock_guard<std::mutex> lk(g_gpio_mu);
    changed = g_out[pin] != (val ? 1 : 0);
    g_out[pin] = val ? 1 : 0;
  }
  if (changed && g_mode[pin] == OUTPUT) hw("GPIO pin=%u level=%u", pin, val ? 1 : 0);
}
int digitalRead(uint8_t pin) {
  if (pin >= 40) return 0;
  std::lock_guard<std::mutex> lk(g_gpio_mu);
  if (g_mode[pin] == OUTPUT) return g_out[pin];
  if (g_ext[pin] != 0xFF) return g_ext[pin];
  return g_mode[pin] == INPUT_PULLUP ? 1 : 0;
}
unsigned long millis() { return (unsigned long)(uint32_t)now_ms(); }
unsigned long micros() { return (unsigned long)(uint32_t)(now_ms() * 1000.0); }
void delay(uint32_t ms) { sleep_until_ms(now_ms() + ms); }
void delayMicroseconds(uint32_t us) { sleep_until_ms(now_ms() + us / 1000.0); }
void yield() {}

// ================= ESP-IDF =================
esp_reset_reason_t esp_reset_reason(void) { return g_reset_reason; }
void esp_restart(void) { chip_reset(ESP_RST_SW, "esp_restart"); }

static int64_t g_sleep_timer_us = -1;
static int g_ext0_pin = -1, g_ext0_level = -1;
esp_err_t esp_sleep_enable_timer_wakeup(uint64_t us) { g_sleep_timer_us = (int64_t)us; hw("SLEEP_CFG timer_us=%llu", (unsigned long long)us); return ESP_OK; }
esp_err_t esp_sleep_enable_ext0_wakeup(gpio_num_t pin, int level) { g_ext0_pin = pin; g_ext0_level = level; hw("SLEEP_CFG ext0 pin=%d level=%d", (int)pin, level); return ESP_OK; }
esp_sleep_wakeup_cause_t esp_sleep_get_wakeup_cause(void) { return g_wake_cause; }
void esp_deep_sleep_start(void) {
  int btn;
  { std::lock_guard<std::mutex> lk(g_gpio_mu); btn = g_ext[4] == 0xFF ? 1 : g_ext[4]; }
  hw("DEEP_SLEEP timer_us=%lld ext0_pin=%d ext0_level=%d btn_level_now=%d", (long long)g_sleep_timer_us, g_ext0_pin, g_ext0_level, btn);
  _exit(EXIT_SLEEP);
}

esp_err_t esp_task_wdt_init(const esp_task_wdt_config_t* c) {
  if (g_wdt_inited) return ESP_ERR_INVALID_STATE;
  g_wdt_timeout_ms = c->timeout_ms;
  g_wdt_panic = c->trigger_panic;
  g_wdt_last_feed = now_ms();
  g_wdt_inited = true;
  hw("WDT_INIT timeout_ms=%u panic=%d", c->timeout_ms, (int)c->trigger_panic);
  start_wdt_thread();
  return ESP_OK;
}
esp_err_t esp_task_wdt_reconfigure(const esp_task_wdt_config_t* c) {
  g_wdt_timeout_ms = c->timeout_ms; g_wdt_panic = c->trigger_panic; g_wdt_last_feed = now_ms();
  hw("WDT_RECONFIG timeout_ms=%u panic=%d", c->timeout_ms, (int)c->trigger_panic);
  return ESP_OK;
}
esp_err_t esp_task_wdt_init(uint32_t timeout_s, bool panic) {
  esp_task_wdt_config_t c{timeout_s * 1000, 0, panic};
  return esp_task_wdt_init(&c);
}
esp_err_t esp_task_wdt_deinit(void) { g_wdt_inited = false; g_wdt_subscribed = false; return ESP_OK; }
esp_err_t esp_task_wdt_add(TaskHandle_t) {
  if (!g_wdt_inited) return ESP_ERR_INVALID_STATE;
  g_wdt_last_feed = now_ms(); g_wdt_subscribed = true; hw("WDT_ADD loopTask"); return ESP_OK;
}
esp_err_t esp_task_wdt_delete(TaskHandle_t) { g_wdt_subscribed = false; return ESP_OK; }
esp_err_t esp_task_wdt_reset(void) { g_wdt_last_feed = now_ms(); return ESP_OK; }

// ================= DHTesp =================
void DHTesp::setup(uint8_t pin, DHT_MODEL_t) { pin_ = pin; }
TempAndHumidity DHTesp::getTempAndHumidity() {
  std::lock_guard<std::mutex> lk(g_dht_mu);
  if (g_dht_mode == "nan") { status_ = ERROR_TIMEOUT; return {NAN, NAN}; }   // sensor disconnected
  if (g_dht_mode == "checksum") { status_ = ERROR_CHECKSUM; return {NAN, NAN}; }
  status_ = ERROR_NONE;
  return {g_dht_t, g_dht_h};  // "ok" or "raw" (raw = arbitrary, possibly out-of-range values)
}
float DHTesp::getTemperature() { return getTempAndHumidity().temperature; }
float DHTesp::getHumidity() { return getTempAndHumidity().humidity; }
const char* DHTesp::getStatusString() { return status_ == ERROR_NONE ? "OK" : status_ == ERROR_TIMEOUT ? "TIMEOUT" : "CHECKSUM"; }

// ================= Preferences (NVS) =================
static std::string K(const std::string& ns, const char* key) { return ns + "/" + key; }
bool Preferences::begin(const char* name, bool ro, const char*) {
  std::lock_guard<std::mutex> lk(g_nvs_mu);
  nvs_load(); ns_ = name; ro_ = ro; started_ = true; return true;
}
void Preferences::end() { started_ = false; }
bool Preferences::clear() {
  std::lock_guard<std::mutex> lk(g_nvs_mu);
  if (!started_ || ro_) return false;
  for (auto it = g_nvs.begin(); it != g_nvs.end();) it = it->first.rfind(ns_ + "/", 0) == 0 ? g_nvs.erase(it) : std::next(it);
  nvs_commit(ns_ + "/*", "erase_all");
  return true;
}
bool Preferences::remove(const char* key) {
  std::lock_guard<std::mutex> lk(g_nvs_mu);
  if (!started_ || ro_) return false;
  auto it = g_nvs.find(K(ns_, key));
  if (it == g_nvs.end()) return false;
  g_nvs.erase(it);
  nvs_commit(K(ns_, key), "erase");
  return true;
}
bool Preferences::isKey(const char* key) { std::lock_guard<std::mutex> lk(g_nvs_mu); return g_nvs.count(K(ns_, key)) > 0; }

static size_t put_raw(const std::string& ns, bool started, bool ro, const char* key, const char* type, const void* v, size_t n) {
  std::lock_guard<std::mutex> lk(g_nvs_mu);
  if (!started || ro) return 0;
  std::vector<uint8_t> d((const uint8_t*)v, (const uint8_t*)v + n);
  std::string k = K(ns, key);
  // NB: real NVS still writes a new entry even if the value is unchanged? (it skips identical values)
  auto it = g_nvs.find(k);
  if (it != g_nvs.end() && it->second.type == type && it->second.data == d) return n;
  Entry old;
  bool had = it != g_nvs.end();
  if (had) old = it->second;
  g_nvs[k] = Entry{type, d};
  long c = g_nvs_cut_after.load();
  if (c == 0) {  // power dies before this entry is committed -> restore old entry in RAM is irrelevant, process ends
    if (had) g_nvs[k] = old; else g_nvs.erase(k);
  }
  nvs_commit(k, "write");
  return n;
}
static bool get_raw(const std::string& ns, const char* key, const char* type, void* out, size_t n) {
  std::lock_guard<std::mutex> lk(g_nvs_mu);
  auto it = g_nvs.find(K(ns, key));
  if (it == g_nvs.end() || it->second.type != type || it->second.data.size() != n) return false;
  memcpy(out, it->second.data.data(), n);
  return true;
}
size_t Preferences::putBool(const char* k, bool v) { uint8_t b = v; return put_raw(ns_, started_, ro_, k, "u8", &b, 1); }
size_t Preferences::putUChar(const char* k, uint8_t v) { return put_raw(ns_, started_, ro_, k, "u8", &v, 1); }
size_t Preferences::putUShort(const char* k, uint16_t v) { return put_raw(ns_, started_, ro_, k, "u16", &v, 2); }
size_t Preferences::putInt(const char* k, int32_t v) { return put_raw(ns_, started_, ro_, k, "i32", &v, 4); }
size_t Preferences::putUInt(const char* k, uint32_t v) { return put_raw(ns_, started_, ro_, k, "u32", &v, 4); }
size_t Preferences::putULong64(const char* k, uint64_t v) { return put_raw(ns_, started_, ro_, k, "u64", &v, 8); }
size_t Preferences::putString(const char* k, const char* v) { return put_raw(ns_, started_, ro_, k, "str", v, strlen(v)); }
size_t Preferences::putBytes(const char* k, const void* v, size_t n) { return put_raw(ns_, started_, ro_, k, "blob", v, n); }
bool Preferences::getBool(const char* k, bool d) { uint8_t b; return get_raw(ns_, k, "u8", &b, 1) ? b != 0 : d; }
uint8_t Preferences::getUChar(const char* k, uint8_t d) { uint8_t b; return get_raw(ns_, k, "u8", &b, 1) ? b : d; }
uint16_t Preferences::getUShort(const char* k, uint16_t d) { uint16_t b; return get_raw(ns_, k, "u16", &b, 2) ? b : d; }
int32_t Preferences::getInt(const char* k, int32_t d) { int32_t b; return get_raw(ns_, k, "i32", &b, 4) ? b : d; }
uint32_t Preferences::getUInt(const char* k, uint32_t d) { uint32_t b; return get_raw(ns_, k, "u32", &b, 4) ? b : d; }
uint64_t Preferences::getULong64(const char* k, uint64_t d) { uint64_t b; return get_raw(ns_, k, "u64", &b, 8) ? b : d; }
String Preferences::getString(const char* k, const String& d) {
  std::lock_guard<std::mutex> lk(g_nvs_mu);
  auto it = g_nvs.find(K(ns_, k));
  if (it == g_nvs.end() || it->second.type != "str") return d;
  return String(std::string(it->second.data.begin(), it->second.data.end()));
}
size_t Preferences::getBytesLength(const char* k) {
  std::lock_guard<std::mutex> lk(g_nvs_mu);
  auto it = g_nvs.find(K(ns_, k));
  return (it == g_nvs.end() || it->second.type != "blob") ? 0 : it->second.data.size();
}
size_t Preferences::getBytes(const char* k, void* buf, size_t maxLen) {
  std::lock_guard<std::mutex> lk(g_nvs_mu);
  auto it = g_nvs.find(K(ns_, k));
  if (it == g_nvs.end() || it->second.type != "blob") return 0;
  size_t n = it->second.data.size();
  if (n > maxLen) return 0;  // real Preferences: "not enough space" -> 0
  memcpy(buf, it->second.data.data(), n);
  return n;
}

// ================= entry point =================
int main() {
  memset(g_ext, 0xFF, sizeof g_ext);
  g_ext[4] = 1;  // button released (pulled up / open)
  if (const char* s = getenv("HAL_SCALE")) g_scale = atof(s);
  if (const char* s = getenv("HAL_T0_NS")) g_t0_ns = atoll(s); else g_t0_ns = mono_ns();
  if (const char* s = getenv("HAL_RESET_REASON")) g_reset_reason = (esp_reset_reason_t)atoi(s);
  if (const char* s = getenv("HAL_WAKE_CAUSE")) g_wake_cause = (esp_sleep_wakeup_cause_t)atoi(s);
  if (const char* s = getenv("HAL_NVS_FILE")) g_nvs_file = s;
  if (const char* s = getenv("HAL_CTRL_FD")) g_ctrl_fd = atoi(s);
  if (const char* s = getenv("HAL_BTN")) g_ext[4] = (uint8_t)atoi(s);
  if (const char* s = getenv("HAL_DHT")) {
    std::istringstream is(s);
    is >> g_dht_mode >> g_dht_t >> g_dht_h;
  }
  for (int sig : {SIGSEGV, SIGBUS, SIGFPE, SIGILL, SIGABRT}) signal(sig, on_fatal);
  hw("BOOT reset_reason=%s wake_cause=%d", reason_name(g_reset_reason), (int)g_wake_cause);
  std::thread(rx_reader_thread).detach();
  std::thread(rx_thread).detach();
  if (g_ctrl_fd >= 0) std::thread(ctrl_thread).detach();
  // ROM bootloader banner, like a real ESP32 on UART0
  char banner[128];
  unsigned rom = 0x1; const char* romn = "POWERON_RESET";
  switch (g_reset_reason) {
    case ESP_RST_SW: rom = 0xc; romn = "SW_CPU_RESET"; break;
    case ESP_RST_PANIC: rom = 0xc; romn = "SW_CPU_RESET"; break;
    case ESP_RST_TASK_WDT: case ESP_RST_INT_WDT: rom = 0x7; romn = "TG0WDT_SYS_RESET"; break;
    case ESP_RST_DEEPSLEEP: rom = 0x5; romn = "DEEPSLEEP_RESET"; break;
    case ESP_RST_BROWNOUT: rom = 0xf; romn = "RTCWDT_BROWN_OUT_RESET"; break;
    default: break;
  }
  snprintf(banner, sizeof banner, "ets Jul 29 2019 12:21:46\r\n\r\nrst:0x%x (%s),boot:0x13 (SPI_FAST_FLASH_BOOT)\r\n", rom, romn);
  uart_txs(banner);
  setup();
  for (;;) loop();
}
