"""Shared steps: ways to knock the device down and bring it back, plus common checks."""
import re

from dut import Device

WDT_LIMIT_MS = 5000          # R5: WDT reset "not later than ~5 s"
WDT_MEAS_TOL = 1.05          # measurement tolerance on top of the limit (serial/trace latency)
READY_MS = 5000              # device must be ACTIVE again within this time after reset
ERROR_RX = r"(?i)(error|unknown|invalid|unsupported)"
CORRUPT_RX = r"(?i)(corrupt|invalid|crc|integrity|no valid state|checksum|defaults)"


def snapshot(d: Device) -> dict:
    st = d.status()
    st["relay_pin"] = d.relay()
    return st


def recover_wdt(d: Device):
    n = d.boot_count
    d.send("hang")
    b = d.wait_boot(n, timeout=15000)
    d.wait_ready(READY_MS)
    return b


def recover_brownout(d: Device):
    b = d.brownout()
    d.wait_ready(READY_MS)
    return b


def recover_power_cycle(d: Device):
    b = d.power_cycle(off_ms=1000)
    d.wait_ready(READY_MS)
    return b


def recover_powerloss_cmd(d: Device):
    n = d.boot_count
    d.send("powerloss")
    b = d.wait_boot(n, timeout=5000)
    d.wait_ready(READY_MS)
    return b


def recover_deep_sleep(d: Device, seconds: int = 2):
    n = d.boot_count
    d.send(f"sleep {seconds}")
    b = d.wait_boot(n, timeout=seconds * 2000 + 5000)
    d.wait_ready(READY_MS)
    return b


RECOVERIES = {
    "wdt": recover_wdt,
    "brownout": recover_brownout,
    "power_cycle": recover_power_cycle,
    "powerloss_cmd": recover_powerloss_cmd,
    "deep_sleep": recover_deep_sleep,
}


def boot_rx(d: Device, boot_idx: int) -> list[str]:
    return [e.text for e in d.events if e.kind == "RX" and e.boot == boot_idx]


def gpio_high_during_boot(d: Device, boot_idx: int, pin: int) -> list[float]:
    return [e.t for e in d.events
            if e.kind == "HW" and e.boot == boot_idx and re.match(rf"GPIO pin={pin} level=1", e.text)]


def resets_since(d: Device, boot_idx: int) -> int:
    return d.boot_count - 1 - boot_idx
