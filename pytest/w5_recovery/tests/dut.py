"""Black-box driver for the ESP32 IoT controller running on the host hardware model.

What a test can see / do here is what a bench gives you:
  * UART0 (send CLI lines, read every printed line, timestamped);
  * GPIO levels of the relay (GPIO5) and LED (GPIO2) - like a logic analyzer / the Wokwi relay part;
  * power state (on / deep sleep / off) - like a power profiler (PPK2) on the supply rail;
  * the button and the DHT22 (press with bounce, disconnect, out-of-range values);
  * fault injection: brown-out, full power cut, power cut between NVS (flash) writes,
    flash bit-flip while the device is off.

All times are in "device world" milliseconds. The model runs HAL_SCALE times faster than
real time, and deep sleep / power-off periods are fast-forwarded, so a 30 s sleep costs ~0 s.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

RELAY_PIN = 5
LED_PIN = 2

RESET_CODES = {"POWERON": 1, "SW": 3, "PANIC": 4, "INT_WDT": 5, "TASK_WDT": 6, "WDT": 7,
               "DEEPSLEEP": 8, "BROWNOUT": 9}
WAKE_TIMER, WAKE_EXT0 = 4, 2

_HW_RE = re.compile(r"^@HW (\S+) (.*)$")


@dataclass
class Event:
    t: float          # world ms
    kind: str         # TX / RX / HW / SYS
    text: str
    boot: int         # index of the boot (process) this belongs to


@dataclass
class Boot:
    idx: int
    t: float                      # world ms when the chip came out of reset
    reason: str                   # POWERON / SW / TASK_WDT / BROWNOUT / DEEPSLEEP / ...
    wake_cause: int = 0
    end_t: float | None = None    # world ms of reset / sleep entry
    end_kind: str | None = None   # RESET / SLEEP / OFF
    end_reason: str | None = None
    gpio: dict = field(default_factory=dict)


class DeviceTimeout(AssertionError):
    pass


class Device:
    def __init__(self, fw: Path, workdir: Path, scale: float = 10.0, name: str = "dut"):
        self.fw = Path(fw)
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.nvs = self.workdir / "nvs.db"
        self.scale = scale
        self.name = name
        self._cv = threading.Condition()
        self.events: list[Event] = []
        self.boots: list[Boot] = []
        self._mono_ref = time.monotonic_ns()
        self._skip_ms = 0.0
        self._proc: subprocess.Popen | None = None
        self._ctrl_w: int | None = None
        self._stop = False
        self.auto_restart = True
        self.power_off_ms = 500.0       # how long supply stays off on an injected power cut
        self.btn_level = 1
        self.dht = "ok 24.5 45"
        self.state = "OFF"              # OFF / RUN / SLEEP

    # ------------------------------------------------------------------ clock
    def now(self) -> float:
        with self._cv:
            return (time.monotonic_ns() - self._mono_ref) / 1e6 * self.scale + self._skip_ms

    def _fast_forward(self, ms: float):
        with self._cv:
            self._skip_ms += ms

    def wait(self, ms: float):
        """Let `ms` of device time pass."""
        end = self.now() + ms
        while self.now() < end:
            time.sleep(min(0.002, max(0.0, (end - self.now()) / self.scale / 1000)))

    # ------------------------------------------------------------------ logging
    def _ev(self, kind: str, text: str, t: float | None = None):
        with self._cv:
            e = Event(self.now() if t is None else t, kind, text, len(self.boots) - 1)
            self.events.append(e)
            self._cv.notify_all()
            return e

    def mark(self) -> int:
        with self._cv:
            return len(self.events)

    def dump_log(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._cv:
            evs = sorted(self.events, key=lambda e: e.t)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# firmware={self.fw.name} scale={self.scale} (times = device world ms)\n")
            for e in evs:
                if e.kind == "HW" and (" PINMODE " in f" {e.text} " or e.text.startswith("PINMODE")):
                    continue
                f.write(f"[{e.t:11.1f}] b{e.boot:<2} {e.kind:<3} {e.text}\n")

    # ------------------------------------------------------------------ power
    def power_on(self, fresh_flash: bool = False, reason: str = "POWERON", wake_cause: int = 0):
        if fresh_flash and self.nvs.exists():
            self.nvs.unlink()
        self._spawn(reason, wake_cause)

    def _spawn(self, reason: str, wake_cause: int = 0):
        r, w = os.pipe()
        t0 = time.monotonic_ns()
        boot_t = self.now()
        env = dict(os.environ, HAL_SCALE=str(self.scale), HAL_T0_NS=str(t0),
                   HAL_RESET_REASON=str(RESET_CODES[reason]), HAL_WAKE_CAUSE=str(wake_cause),
                   HAL_NVS_FILE=str(self.nvs), HAL_CTRL_FD=str(r), HAL_BTN=str(self.btn_level),
                   HAL_DHT=self.dht)
        # world time of the process start (the model measures millis() from t0 as well)
        boot_t = (t0 - self._mono_ref) / 1e6 * self.scale + self._skip_ms
        proc = subprocess.Popen([str(self.fw)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, pass_fds=(r,), env=env, bufsize=0)
        os.close(r)
        with self._cv:
            b = Boot(len(self.boots), boot_t, reason, wake_cause)
            self.boots.append(b)
            self._proc, self._ctrl_w, self.state = proc, w, "RUN"
        self._ev("SYS", f"CHIP RESET RELEASED reason={reason} wake_cause={wake_cause}", boot_t)
        out_t = threading.Thread(target=self._read_uart, args=(proc, b), daemon=True)
        err_t = threading.Thread(target=self._read_hw, args=(proc, b), daemon=True)
        out_t.start(); err_t.start()
        threading.Thread(target=self._supervise, args=(proc, b, out_t, err_t, w), daemon=True).start()

    def _read_uart(self, proc, b: Boot):
        for raw in proc.stdout:
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            self._ev("RX", line)

    def _read_hw(self, proc, b: Boot):
        for raw in proc.stderr:
            line = raw.decode("utf-8", "replace").rstrip("\n")
            m = _HW_RE.match(line)
            if not m:
                self._ev("SYS", "stderr: " + line)
                continue
            t = b.t + float(m.group(1))
            text = m.group(2)
            if text.startswith("GPIO "):
                g = dict(kv.split("=") for kv in text.split()[1:])
                with self._cv:
                    b.gpio[int(g["pin"])] = int(g["level"])
            self._ev("HW", text, t)

    def _supervise(self, proc, b: Boot, out_t, err_t, ctrl_w):
        rc = proc.wait()
        auto = self.auto_restart
        out_t.join(); err_t.join()
        try:
            os.close(ctrl_w)
        except OSError:
            pass
        with self._cv:
            last = [e for e in self.events if e.boot == b.idx and e.kind == "HW"]
            stopping = self._stop
        reset_ev = next((e for e in reversed(last) if e.text.startswith("RESET ")), None)
        sleep_ev = next((e for e in reversed(last) if e.text.startswith("DEEP_SLEEP ")), None)
        with self._cv:
            b.gpio = {k: 0 for k in b.gpio}  # outputs released by reset / power loss
        if stopping:
            b.end_kind, b.end_t = "OFF", self.now()
            self.state = "OFF"
            return
        if rc == 10 and reset_ev:
            reason = re.search(r"reason=(\S+)", reset_ev.text).group(1)
            b.end_kind, b.end_t, b.end_reason = "RESET", reset_ev.t, reason
            if not auto:
                self._ev("SYS", "POWER OFF (held off by test)")
                self.state = "OFF"
                return
            if reason == "POWERON":
                self._ev("SYS", f"POWER OFF for {self.power_off_ms:.0f} ms")
                self.state = "OFF"
                self._fast_forward(self.power_off_ms)
            self._spawn(reason)
        elif rc == 11 and sleep_ev:
            kv = dict(x.split("=") for x in sleep_ev.text.split()[1:])
            timer_us = int(kv["timer_us"])
            b.end_kind, b.end_t, b.end_reason = "SLEEP", sleep_ev.t, f"timer_us={timer_us}"
            self.state = "SLEEP"
            if int(kv["ext0_pin"]) >= 0 and int(kv["btn_level_now"]) == int(kv["ext0_level"]):
                self._ev("SYS", "ext0 wake-up level already present -> immediate wake")
                self._spawn("DEEPSLEEP", WAKE_EXT0)
            elif timer_us >= 0:
                # fast-forward the sleep: the supply-current trace would show this gap
                wake_at = sleep_ev.t + timer_us / 1000.0
                self._fast_forward(max(0.0, wake_at - self.now()))
                self._spawn("DEEPSLEEP", WAKE_TIMER)
            else:
                self._ev("SYS", "deep sleep with no wake-up source: device will never wake")
        else:
            b.end_kind, b.end_t, b.end_reason = "RESET", self.now(), f"host_exit_{rc}"
            self._ev("SYS", f"model process ended unexpectedly rc={rc} -> treated as PANIC reset")
            if auto:
                self._spawn("PANIC")

    def shutdown(self):
        with self._cv:
            self._stop = True
            p = self._proc
        if p and p.poll() is None:
            p.kill()
            p.wait()
        time.sleep(0.02)

    # ------------------------------------------------------------------ I/O
    def send(self, line: str | bytes, eol: bytes = b"\n"):
        data = line if isinstance(line, bytes) else line.encode()
        with self._cv:
            p = self._proc
        self._ev("TX", repr(data + eol)[2:-1] if isinstance(line, bytes) else line)
        if p is None or p.poll() is not None or self.state != "RUN":
            self._ev("SYS", "TX dropped: device not running")
            return
        try:
            p.stdin.write(data + eol)
            p.stdin.flush()
        except (BrokenPipeError, OSError):
            self._ev("SYS", "TX dropped: device reset during transmission")

    def hw(self, cmd: str):
        with self._cv:
            w = self._ctrl_w
        self._ev("SYS", f"INJECT {cmd}")
        try:
            os.write(w, (cmd + "\n").encode())
        except (OSError, TypeError):
            self._ev("SYS", f"INJECT {cmd} dropped: device not running")

    def wait_for(self, pattern: str, since: int = 0, timeout: float = 3000, kind: str = "RX",
                 boot: int | None = None) -> Event:
        rx = re.compile(pattern)
        end = self.now() + timeout
        i = since
        while True:
            with self._cv:
                while i < len(self.events):
                    e = self.events[i]
                    i += 1
                    if e.kind == kind and rx.search(e.text) and (boot is None or e.boot == boot):
                        return e
            if self.now() > end:
                raise DeviceTimeout(f"no {kind} matching /{pattern}/ within {timeout:.0f} ms")
            time.sleep(0.001)

    def lines(self, since: int = 0, kind: str = "RX", until: int | None = None) -> list[Event]:
        with self._cv:
            return [e for e in self.events[since:until] if e.kind == kind]

    def cmd(self, line: str, expect: str | None = None, timeout: float = 2000) -> Event | None:
        m = self.mark()
        self.send(line)
        if expect:
            return self.wait_for(expect, since=m, timeout=timeout)
        return None

    def status(self, timeout: float = 2000) -> dict:
        e = self.cmd("status", r"^\{.*\}\s*$", timeout)
        return json.loads(e.text)

    # ------------------------------------------------------------------ boots / power
    @property
    def boot_count(self) -> int:
        with self._cv:
            return len(self.boots)

    def current_boot(self) -> Boot:
        with self._cv:
            return self.boots[-1]

    def wait_boot(self, after: int, timeout: float = 10000) -> Boot:
        """Wait until boot number `after` (index) exists, i.e. the chip came out of reset again."""
        end = self.now() + timeout
        while self.now() < end:
            with self._cv:
                if len(self.boots) > after:
                    return self.boots[after]
            time.sleep(0.001)
        raise DeviceTimeout(f"device did not come out of reset within {timeout:.0f} ms")

    def wait_ready(self, timeout: float = 5000) -> dict:
        """R1: after start the device prints the reset reason and answers `status` with state ACTIVE."""
        b = self.current_boot()
        m = 0
        self.wait_for(r"\[BOOT\]", since=m, timeout=timeout, boot=b.idx)
        end = self.now() + timeout
        last_err = None
        while self.now() < end:
            try:
                st = self.status(timeout=800)
                if st.get("state") == "ACTIVE":
                    return st
            except DeviceTimeout as ex:
                last_err = ex
        raise DeviceTimeout(f"device not ACTIVE within {timeout:.0f} ms ({last_err})")

    def relay(self) -> int:
        with self._cv:
            return self.current_boot().gpio.get(RELAY_PIN, 0) if self.state == "RUN" else 0

    def led(self) -> int:
        with self._cv:
            return self.current_boot().gpio.get(LED_PIN, 0) if self.state == "RUN" else 0

    def power_cycle(self, off_ms: float = 500):
        self.power_off_ms = off_ms
        n = self.boot_count
        self.hw("POWERCUT")
        return self.wait_boot(n)

    def brownout(self):
        n = self.boot_count
        self.hw("BROWNOUT")
        return self.wait_boot(n)

    def power_off(self):
        """Cut power and keep it off (for flash manipulation)."""
        self.auto_restart = False
        self.hw("POWERCUT")
        end = self.now() + 3000
        while self.state != "OFF" and self.now() < end:
            time.sleep(0.001)
        self.auto_restart = True

    # ------------------------------------------------------------------ peripherals
    def press_button(self, hold_ms: float = 200, bounce: bool = True, release_bounce: bool = True):
        seq = []
        if bounce:  # typical 2-5 ms contact chatter
            seq += [(0, 0.8), (1, 0.6), (0, 1.2), (1, 0.4)]
        seq.append((0, hold_ms))
        if release_bounce:
            seq += [(1, 0.7), (0, 0.5), (1, 0.9), (0, 0.3)]
        seq.append((1, 60))
        m = self.mark()
        self.hw("BTNSEQ " + ",".join(f"{l}:{d}" for l, d in seq))
        self.wait_for("BTNSEQ_DONE", since=m, kind="HW", timeout=hold_ms + 3000)

    def set_dht(self, mode: str):
        """Change the sensor condition and wait until it is physically in effect."""
        self.dht = mode
        m = self.mark()
        self.hw("DHT " + mode)
        self.wait_for(r"^DHT mode=", since=m, kind="HW", timeout=1000)

    # ------------------------------------------------------------------ flash
    def read_flash(self) -> dict[str, tuple[str, str]]:
        out = {}
        if self.nvs.exists():
            for line in self.nvs.read_text().splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    out[parts[0]] = (parts[1], parts[2] if len(parts) > 2 else "")
        return out

    def flip_flash_bits(self, byte_index: int = 0, mask: int = 0x01) -> list[str]:
        """Flip bits in every stored value (device must be OFF). Models flash bit rot."""
        assert self.state == "OFF"
        lines, touched = [], []
        for line in self.nvs.read_text().splitlines():
            k, t, h = (line.split() + [""])[:3]
            if h:
                b = bytearray.fromhex(h)
                i = min(byte_index, len(b) - 1)
                b[i] ^= mask
                h = b.hex()
                touched.append(k)
            lines.append(f"{k} {t} {h}")
        self.nvs.write_text("\n".join(lines) + "\n")
        self._ev("SYS", f"FLASH bit-flip mask=0x{mask:02x} at byte {byte_index} of entries {touched}")
        return touched
