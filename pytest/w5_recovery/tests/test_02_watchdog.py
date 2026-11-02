"""2. Watchdog — R5: `hang` -> WDT reset <= ~5 s, WDT reset reason, device recovers, relay OFF, no boot loop."""
import random

import pytest

from dut import RELAY_PIN
from helpers import (READY_MS, WDT_LIMIT_MS, WDT_MEAS_TOL, boot_rx, gpio_high_during_boot,
                     recover_wdt, resets_since, snapshot)


def _hang(d):
    n = d.boot_count
    hung = d.current_boot()
    m = d.mark()
    d.send("hang")
    t_cmd = d.events[m].t
    new = d.wait_boot(n, timeout=15000)
    return hung, new, hung.end_t - t_cmd


@pytest.mark.req("R5")
def test_WDT01_reset_within_5s(dut, record_property):
    """TC-WDT-01: firmware hang is ended by a reset not later than ~5 s after `hang`."""
    hung, new, dt = _hang(dut)
    record_property("hang_to_reset_ms", round(dt, 1))
    record_property("reset_reason_trace", hung.end_reason)
    assert hung.end_kind == "RESET", "device never reset after hang"
    assert dt <= WDT_LIMIT_MS * WDT_MEAS_TOL, f"reset came {dt:.0f} ms after hang (limit ~{WDT_LIMIT_MS} ms)"


@pytest.mark.req("R5", "R1", "R7")
def test_WDT02_reset_reason_identifies_wdt(dut, record_property):
    """TC-WDT-02: after recovery both the boot log and `status` name a watchdog reset."""
    _, new, _ = _hang(dut)
    st = dut.wait_ready(READY_MS)
    boot_line = next((l for l in boot_rx(dut, new.idx) if "[BOOT]" in l), "")
    record_property("boot_line", boot_line)
    record_property("status_reset_reason", st["reset_reason"])
    assert "WDT" in boot_line.upper(), f"boot log reset reason is not WDT: {boot_line!r}"
    assert "WDT" in st["reset_reason"].upper(), f"status reset_reason is not WDT: {st['reset_reason']!r}"


@pytest.mark.req("R5")
@pytest.mark.parametrize("how", ["cli", "cli_then_save", "button"])
def test_WDT03_relay_off_after_wdt_reset(dut, how, record_property):
    """TC-WDT-03: relay ON before the hang -> after the WDT reset the actuator is OFF (and never pulses ON while booting)."""
    if how == "button":
        dut.press_button(bounce=False, release_bounce=False)
    else:
        dut.cmd("relay on", r"RELAY\] ON")
        if how == "cli_then_save":
            dut.cmd("save")
    dut.wait(200)
    assert dut.relay() == 1, "precondition: relay must be ON"
    _, new, _ = _hang(dut)
    st = dut.wait_ready(READY_MS)
    pulses = gpio_high_during_boot(dut, new.idx, RELAY_PIN)
    record_property("relay_pin_after", dut.relay())
    record_property("status_relay_after", st["relay"])
    record_property("relay_high_events_after_reset_ms", [round(t - new.t) for t in pulses])
    assert dut.relay() == 0, "relay pin is ON after WDT reset (unsafe actuator state)"
    assert st["relay"] is False, "status reports relay ON after WDT reset"
    assert not pulses, f"relay was driven ON {len(pulses)}x during recovery boot"


@pytest.mark.req("R5")
def test_WDT04_no_boot_loop_after_recovery(dut, record_property):
    """TC-WDT-04: after one WDT recovery the device stays up (observe 3 x WDT period) and keeps serving commands."""
    _, new, _ = _hang(dut)
    dut.wait_ready(READY_MS)
    for _ in range(15):
        dut.wait(1000)
        dut.status()
    extra = resets_since(dut, new.idx)
    record_property("extra_resets_in_15s", extra)
    assert extra == 0, f"{extra} additional resets after recovery (boot loop)"


@pytest.mark.req("R5")
def test_WDT05_repeated_hang_recovery_x10(dut, record_property):
    """TC-WDT-05: 10 consecutive hang/recovery cycles: every reset <= 5 s, reason WDT, ACTIVE, relay OFF, counter kept."""
    dut.cmd("relay on"); dut.cmd("save"); dut.wait(200)
    base = dut.status()["counter"]
    dts, counters, relays = [], [], []
    for _ in range(10):
        dut.cmd("relay on")
        dut.wait(100)
        _, new, dt = _hang(dut)
        st = dut.wait_ready(READY_MS)
        dts.append(round(dt))
        counters.append(st["counter"])
        relays.append(dut.relay())
        assert "WDT" in st["reset_reason"].upper()
    record_property("hang_to_reset_ms", dts)
    record_property("counter_after_each", counters)
    record_property("relay_after_each", relays)
    assert max(dts) <= WDT_LIMIT_MS * WDT_MEAS_TOL, f"slowest WDT reset {max(dts)} ms"
    assert min(counters) >= base, f"persistent counter lost: base {base}, seen {counters}"
    assert all(b >= a for a, b in zip(counters, counters[1:])), f"counter went backwards: {counters}"
    assert relays == [0] * 10, f"relay ON after WDT reset in {relays.count(1)}/10 cycles"


@pytest.mark.req("R5")
def test_WDT06_no_false_wdt_reset_in_normal_operation(dut, record_property):
    """TC-WDT-06: 60 s of normal traffic (status/sensor/relay/save/button) never triggers the watchdog."""
    rnd = random.Random(6)
    start_boot = dut.current_boot().idx
    cmds = ["status", "sensor", "relay on", "relay off", "save", "help"]
    t_end = dut.now() + 60000
    n = 0
    while dut.now() < t_end:
        if rnd.random() < 0.15:
            dut.press_button()
        else:
            dut.send(rnd.choice(cmds))
        n += 1
        dut.wait(rnd.uniform(100, 900))
    record_property("commands_sent", n)
    record_property("resets", resets_since(dut, start_boot))
    assert resets_since(dut, start_boot) == 0, "unexpected reset during normal operation"
    assert dut.status()["state"] == "ACTIVE"
