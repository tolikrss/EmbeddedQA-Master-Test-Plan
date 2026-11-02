"""1. Sleep / Wake — R4: ACTIVE -> SLEEP -> WAKE, wake-up timing ±15 %, device usable, data intact."""
import pytest

from helpers import READY_MS, boot_rx, snapshot

TOL = 0.15


def _sleep_and_measure(d, seconds):
    n = d.boot_count
    sleeper = d.current_boot()
    m = d.mark()
    d.send(f"sleep {seconds}")
    t_cmd = d.events[m].t
    wake = d.wait_boot(n, timeout=seconds * 1000 * (1 + TOL) * 2 + 5000)
    assert sleeper.end_kind == "SLEEP", f"device did not enter deep sleep (ended by {sleeper.end_kind} {sleeper.end_reason})"
    slept_ms = wake.t - sleeper.end_t          # supply-current view: sleep entry -> chip running again
    first_rx_after = d.wait_for(r".", since=m, boot=wake.idx, timeout=2000)
    last_rx_before = [e for e in d.events[m:] if e.kind == "RX" and e.boot == sleeper.idx]
    gap_ms = first_rx_after.t - (last_rx_before[-1].t if last_rx_before else t_cmd)
    return sleeper, wake, slept_ms, gap_ms, t_cmd


@pytest.mark.req("R4")
@pytest.mark.parametrize("seconds", [1, 2, 5, 10, 30, 60])
def test_SW01_wakeup_time_within_15pct(dut, seconds, record_property):
    """TC-SW-01: `sleep N` -> deep sleep lasts N s ±15 % (measured on the power trace)."""
    _, wake, slept_ms, gap_ms, _ = _sleep_and_measure(dut, seconds)
    lo, hi = seconds * 1000 * (1 - TOL), seconds * 1000 * (1 + TOL)
    record_property("requested_ms", seconds * 1000)
    record_property("measured_sleep_ms", round(slept_ms, 1))
    record_property("serial_silence_ms", round(gap_ms, 1))
    record_property("error_pct", round((slept_ms / (seconds * 1000) - 1) * 100, 1))
    assert lo <= slept_ms <= hi, (
        f"deep sleep lasted {slept_ms:.0f} ms, expected {lo:.0f}..{hi:.0f} ms for `sleep {seconds}`")


@pytest.mark.req("R4", "R1", "R7")
def test_SW02_device_functional_after_wake(dut, record_property):
    """TC-SW-02: after wake-up: reset reason = deep sleep, wake cause logged, ACTIVE, CLI/relay/sensor/button work."""
    _, wake, _, _, _ = _sleep_and_measure(dut, 5)
    st = dut.wait_ready(READY_MS)
    rx = boot_rx(dut, wake.idx)
    record_property("boot_line", next((l for l in rx if "[BOOT]" in l), None))
    record_property("status_after_wake", st)
    assert any("[BOOT]" in l and "DEEP" in l.upper() for l in rx), "boot log does not name deep-sleep wake-up as reset reason"
    assert any("WAKE" in l.upper() for l in rx), "wake-up cause not reported"
    assert "DEEP" in st["reset_reason"].upper()
    dut.cmd("relay on", r"RELAY\] ON")
    dut.wait(100)
    assert dut.relay() == 1, "relay does not switch ON after wake-up"
    dut.cmd("relay off", r"RELAY\] OFF")
    dut.wait(100)
    assert dut.relay() == 0, "relay does not switch OFF after wake-up"
    dut.cmd("sensor", r"\[SENSOR\]")
    c0 = dut.status()["counter"]
    dut.press_button(bounce=False, release_bounce=False)
    dut.wait(200)
    assert dut.status()["counter"] == c0 + 1, "button not handled after wake-up"


@pytest.mark.req("R4", "R6")
def test_SW03_persistent_data_intact_after_wake(dut, record_property):
    """TC-SW-03: saved counter survives deep sleep (no loss, no corruption; the sleep command itself may count as +1 event)."""
    for _ in range(3):
        dut.press_button(bounce=False, release_bounce=False)
    dut.cmd("save")
    dut.wait(300)
    before = snapshot(dut)
    _sleep_and_measure(dut, 5)
    after = dut.wait_ready(READY_MS)
    record_property("counter_before", before["counter"])
    record_property("counter_after", after["counter"])
    assert before["counter"] <= after["counter"] <= before["counter"] + 1, (
        f"counter {before['counter']} -> {after['counter']} across deep sleep")


@pytest.mark.req("R4")
def test_SW04_repeated_sleep_wake_cycles(dut, record_property):
    """TC-SW-04: 10 x `sleep 2` — every wake-up in tolerance, device ACTIVE each time, counter monotonic."""
    times, counters = [], [dut.status()["counter"]]
    for _ in range(10):
        _, _, slept_ms, _, _ = _sleep_and_measure(dut, 2)
        times.append(round(slept_ms))
        counters.append(dut.wait_ready(READY_MS)["counter"])
    record_property("sleep_ms_per_cycle", times)
    record_property("counter_per_cycle", counters)
    bad = [t for t in times if not (1700 <= t <= 2300)]
    assert not bad, f"{len(bad)}/10 wake-ups outside 1700..2300 ms: {times}"
    assert all(b - a in (0, 1) for a, b in zip(counters, counters[1:])), f"counter not monotonic/consistent: {counters}"
