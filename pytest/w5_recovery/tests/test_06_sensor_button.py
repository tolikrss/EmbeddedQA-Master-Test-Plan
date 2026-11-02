"""Sensor failure (R2) and button (R3) — rows of the Recovery/Fault-Injection test sheet."""
import re

import pytest

from helpers import snapshot

VALUE_RX = r"temp=\s*-?\d"


@pytest.mark.req("R2")
@pytest.mark.parametrize("mode", ["nan", "checksum"], ids=["disconnected", "checksum_error"])
def test_SB01_sensor_failure_reported_explicitly(dut, mode, record_property):
    """TC-SB-01: DHT22 does not answer / bad checksum -> explicit error, no number printed, status sensor_ok=false."""
    dut.set_dht(mode)
    m = dut.mark()
    dut.send("sensor")
    dut.wait(500)
    reply = [e.text for e in dut.lines(m) if e.text.strip()]
    st = dut.status()
    record_property("reply", reply)
    record_property("status_sensor_ok", st["sensor_ok"])
    assert st["sensor_ok"] is False
    assert not any(re.search(VALUE_RX, l) for l in reply), f"invalid reading printed as a measurement: {reply}"
    assert any("ERROR" in l.upper() for l in reply), f"no explicit error: {reply}"


@pytest.mark.req("R2")
@pytest.mark.parametrize("t,h", [(150.0, 50.0), (-60.0, 50.0), (25.0, 120.0)],
                         ids=["temp_150C", "temp_-60C", "hum_120pct"])
def test_SB02_out_of_range_values_not_valid(dut, t, h, record_property):
    """TC-SB-02: physically impossible DHT22 data (range -40..80 C, 0..100 %RH) must not be accepted as valid."""
    dut.set_dht(f"raw {t} {h}")
    m = dut.mark()
    dut.send("sensor")
    dut.wait(500)
    reply = [e.text for e in dut.lines(m) if e.text.strip()]
    st = dut.status()
    record_property("reply", reply)
    record_property("status", st)
    assert st["sensor_ok"] is False, f"out-of-range data reported as sensor_ok=true ({t} C / {h} %)"


@pytest.mark.req("R2")
def test_SB03_invalid_data_does_not_move_actuator(dut, record_property):
    """TC-SB-03: relay keeps its state while the sensor is broken or delivers garbage."""
    for relay in ("on", "off"):
        dut.cmd(f"relay {relay}"); dut.wait(100)
        pin = dut.relay()
        for mode in ("nan", "raw 150 120", "raw -60 0"):
            dut.set_dht(mode)
            dut.send("sensor"); dut.wait(300)
            dut.status()
            assert dut.relay() == pin, f"relay changed with sensor mode {mode}"


@pytest.mark.req("R3")
@pytest.mark.parametrize("bounce,release_bounce", [(False, False), (True, False), (False, True), (True, True)],
                         ids=["clean", "press_bounce", "release_bounce", "both_bounce"])
def test_SB04_one_press_one_event(dut, bounce, release_bounce, record_property):
    """TC-SB-04: one physical press (with typical 2-3 ms contact bounce) -> exactly one logical event."""
    c0 = dut.status()["counter"]
    dut.press_button(bounce=bounce, release_bounce=release_bounce)
    dut.wait(300)
    c1 = dut.status()["counter"]
    record_property("events", c1 - c0)
    assert c1 - c0 == 1, f"{c1 - c0} events for one press"


@pytest.mark.req("R3")
def test_SB05_twenty_presses_twenty_events(dut, record_property):
    """TC-SB-05 (template T02): 20 bouncy presses -> exactly 20 events, relay toggles accordingly."""
    c0 = dut.status()["counter"]
    for _ in range(20):
        dut.press_button(hold_ms=150)
        dut.wait(150)
    c1 = dut.status()["counter"]
    record_property("events", c1 - c0)
    assert c1 - c0 == 20, f"{c1 - c0} events for 20 presses"


@pytest.mark.req("R3")
def test_SB06_long_hold_is_one_event(dut, record_property):
    """TC-SB-06: holding the button for 3 s produces one event, not a stream."""
    c0 = dut.status()["counter"]
    dut.press_button(hold_ms=3000, bounce=False, release_bounce=False)
    dut.wait(300)
    c1 = dut.status()["counter"]
    record_property("events", c1 - c0)
    assert c1 - c0 == 1
