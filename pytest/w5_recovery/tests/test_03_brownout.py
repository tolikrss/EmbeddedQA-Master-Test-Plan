"""3. Brown-out / power loss (harness fault injection on the supply): device must come back correctly."""
import random

import pytest

from dut import RELAY_PIN
from helpers import READY_MS, boot_rx, gpio_high_during_boot, resets_since, snapshot

FAULTS = {"BROWNOUT": ("BROWNOUT", "BROWN"), "POWERCUT": ("POWERON", "POWER")}


def _inject(d, fault):
    return d.brownout() if fault == "BROWNOUT" else d.power_cycle(off_ms=1000)


@pytest.mark.req("R1", "R6", "R7")
@pytest.mark.parametrize("activity", ["idle", "relay_on", "sensor_read"])
@pytest.mark.parametrize("fault", list(FAULTS))
def test_BO01_recovers_with_correct_reset_reason(dut, fault, activity, record_property):
    """TC-BO-01: brown-out / power cut while idle or busy -> ACTIVE again, reset reason reported, saved counter intact."""
    for _ in range(2):
        dut.press_button(bounce=False, release_bounce=False)
    dut.cmd("save"); dut.wait(300)
    saved = dut.status()["counter"]
    if activity == "relay_on":
        dut.cmd("relay on", r"RELAY\] ON")
        saved = dut.status()["counter"]
    elif activity == "sensor_read":
        dut.send("sensor")
        dut.wait(2)
    new = _inject(dut, fault)
    st = dut.wait_ready(READY_MS)
    boot_line = next((l for l in boot_rx(dut, new.idx) if "[BOOT]" in l), "")
    record_property("boot_line", boot_line)
    record_property("status", st)
    record_property("counter_saved", saved)
    want = FAULTS[fault][1]
    assert want in boot_line.upper().replace("_", ""), f"boot log reset reason {boot_line!r} does not identify {fault}"
    assert want in st["reset_reason"].upper().replace("_", "")
    assert st["counter"] == saved, f"persistent counter {saved} -> {st['counter']} after {fault}"


@pytest.mark.req("R5", "R6")
@pytest.mark.parametrize("how", ["cli", "button"])
def test_BO02_relay_off_after_brownout(dut, how, record_property):
    """TC-BO-02: relay ON + brown-out -> after the emergency reset the actuator stays OFF (same safety rule as R5)."""
    if how == "cli":
        dut.cmd("relay on", r"RELAY\] ON")
    else:
        dut.press_button(bounce=False, release_bounce=False)
    dut.wait(200)
    assert dut.relay() == 1
    new = dut.brownout()
    st = dut.wait_ready(READY_MS)
    pulses = gpio_high_during_boot(dut, new.idx, RELAY_PIN)
    record_property("relay_pin_after", dut.relay())
    record_property("relay_high_after_reset_ms", [round(t - new.t) for t in pulses])
    assert dut.relay() == 0 and st["relay"] is False, "relay is ON after brown-out reset"
    assert not pulses, "relay driven ON during brown-out recovery boot"


@pytest.mark.req("R1", "R6")
@pytest.mark.parametrize("at_ms", [5, 50, 150, 300, 320, 400])
def test_BO03_brownout_during_boot(dut, at_ms, record_property):
    """TC-BO-03: a second brown-out hits while the device is still booting -> it still ends up ACTIVE, data intact, no loop."""
    dut.cmd("relay on"); dut.cmd("save"); dut.wait(300)
    saved = dut.status()["counter"]
    first = dut.brownout()
    dut.wait(max(0, at_ms - (dut.now() - first.t)))
    second = dut.brownout()
    st = dut.wait_ready(READY_MS)
    dut.wait(5000)
    record_property("second_fault_after_boot_ms", round(second.t - first.t))
    record_property("counter_saved", saved)
    record_property("counter_after", st["counter"])
    assert resets_since(dut, second.idx) == 0, "boot loop after double brown-out"
    assert st["counter"] == saved, f"counter {saved} -> {st['counter']}"
    assert dut.relay() == 0, "relay ON after brown-out recovery"


@pytest.mark.req("R1", "R5", "R6")
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_BO04_random_brownouts_x10(dut, seed, record_property):
    """TC-BO-04: 10 brown-outs at random moments of random activity -> always ACTIVE, relay OFF, counter never goes back."""
    rnd = random.Random(seed)
    counters, relays, plan = [dut.status()["counter"]], [], []
    for _ in range(10):
        cmd = rnd.choice(["status", "sensor", "relay on", "relay off", "save", "button"])
        delay = rnd.uniform(0, 60)
        plan.append((cmd, round(delay, 1)))
        if cmd == "button":
            dut.hw("BTN 0")
        else:
            dut.send(cmd)
        dut.wait(delay)
        dut.brownout()
        dut.btn_level = 1
        st = dut.wait_ready(READY_MS)
        dut.hw("BTN 1")
        counters.append(st["counter"])
        relays.append(dut.relay())
    record_property("plan_cmd_delayms", plan)
    record_property("counters", counters)
    record_property("relay_after", relays)
    assert all(b >= a for a, b in zip(counters, counters[1:])), f"counter went backwards: {counters}"
    assert relays == [0] * 10, f"relay ON after brown-out in {relays.count(1)}/10 recoveries"
