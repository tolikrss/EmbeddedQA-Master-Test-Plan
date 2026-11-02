"""4. Data persistence / integrity — R6: after an interrupted save only the old or the new complete state may remain,
corrupted state must be detected. Flash = ESP32 NVS (the device has no EEPROM; RTC memory is not used for state)."""
import pytest

from dut import RELAY_PIN
from helpers import CORRUPT_RX, READY_MS, boot_rx, gpio_high_during_boot, snapshot


def _state(st, d):
    return (st["counter"], bool(st["relay"]), d.relay())


@pytest.mark.req("R6")
@pytest.mark.parametrize("how", ["power_cycle", "reboot_cmd", "deep_sleep"])
def test_DI01_saved_state_survives_restart(dut, how, record_property):
    """TC-DI-01: counter saved with `save` is restored after a clean power cycle / `reboot` / deep sleep."""
    for _ in range(4):
        dut.press_button(bounce=False, release_bounce=False)
    dut.cmd("save"); dut.wait(300)
    before = snapshot(dut)
    n = dut.boot_count
    if how == "power_cycle":
        dut.power_cycle(off_ms=2000)
    elif how == "reboot_cmd":
        dut.send("reboot"); dut.wait_boot(n)
    else:
        dut.send("sleep 2"); dut.wait_boot(n, timeout=8000)
    after = dut.wait_ready(READY_MS)
    record_property("before", before)
    record_property("after", after)
    allowed = {before["counter"]} | ({before["counter"] + 1} if how == "deep_sleep" else set())
    assert after["counter"] in allowed, f"counter {before['counter']} -> {after['counter']}"


@pytest.mark.req("R6")
def test_DI02_powerloss_leaves_old_or_new_valid_state(dut, record_property):
    """TC-DI-02 (lab `powerloss`): state after the interrupted save is the old one or one complete new one
    (at most one more event than before) — never a value that no operation produced."""
    for _ in range(3):
        dut.press_button(bounce=False, release_bounce=False)
    dut.cmd("save"); dut.wait(300)
    old = dut.status()
    n = dut.boot_count
    dut.send("powerloss")
    dut.wait_boot(n, timeout=5000)
    new = dut.wait_ready(READY_MS)
    record_property("counter_before", old["counter"])
    record_property("counter_after", new["counter"])
    assert new["counter"] in (old["counter"], old["counter"] + 1), (
        f"counter {old['counter']} -> {new['counter']}: neither old nor a complete new state")


@pytest.mark.req("R6")
def test_DI03_interrupted_save_is_detected(dut, record_property):
    """TC-DI-03: after `powerloss` the boot log reports that an interrupted/incomplete save was found and handled."""
    dut.cmd("save"); dut.wait(300)
    n = dut.boot_count
    dut.send("powerloss")
    new = dut.wait_boot(n, timeout=5000)
    dut.wait_ready(READY_MS)
    rx = boot_rx(dut, new.idx)
    hits = [l for l in rx if any(k in l.upper() for k in ("RECOVER", "INTERRUPT", "PENDING", "CORRUPT", "INVALID", "ROLLBACK"))]
    record_property("recovery_lines", hits)
    assert hits, "no diagnostic about the interrupted save in the boot log"


@pytest.mark.req("R6")
@pytest.mark.parametrize("commits_before_cut", [0, 1, 2])
@pytest.mark.parametrize("op", ["relay on", "relay off"])
def test_DI04_power_cut_between_flash_writes(dut, op, commits_before_cut, record_property):
    """TC-DI-04: supply cut after K flash (NVS) entry writes of a state update -> after power-on the state is
    exactly the old one or exactly the new one (counter and relay must belong to the same version)."""
    pre = "relay off" if op == "relay on" else "relay on"
    # learn what one state update looks like (counter delta) on this build
    dut.cmd(pre); dut.wait(200)
    c0 = dut.status()["counter"]
    dut.cmd(op); dut.wait(200)
    delta = dut.status()["counter"] - c0
    dut.cmd(pre); dut.wait(300)
    old = dut.status()
    old_v = (old["counter"], bool(old["relay"]))
    new_v = (old["counter"] + delta, op == "relay on")
    n = dut.boot_count
    dut.hw(f"NVSCUT {commits_before_cut} POWERON")
    dut.send(op)
    try:
        dut.wait_boot(n, timeout=1500)
        cut = True
    except AssertionError:
        cut = False  # update needed fewer flash writes than K: nothing was interrupted
        dut.hw("NVSCUT -1 POWERON")
        dut.power_cycle(off_ms=500)
    after = dut.wait_ready(READY_MS)
    got = (after["counter"], bool(after["relay"]))
    record_property("cut_happened", cut)
    record_property("old", old_v)
    record_property("new", new_v)
    record_property("after_power_on", got)
    assert got in (old_v, new_v), f"mixed state after power cut: got {got}, allowed old {old_v} or new {new_v}"


@pytest.mark.req("R6", "R5")
@pytest.mark.parametrize("flip", [(0, 0x01), (0, 0x80)], ids=["bit0", "bit7"])
@pytest.mark.parametrize("saved_relay", ["off", "on"])
def test_DI05_corrupted_flash_is_detected(dut, saved_relay, flip, record_property):
    """TC-DI-05: a bit flip in the stored state (device off) must be detected at boot, and corrupted data must not
    switch the actuator ON."""
    dut.cmd(f"relay {saved_relay}"); dut.cmd("save"); dut.wait(300)
    before = snapshot(dut)
    dut.power_off()
    touched = dut.flip_flash_bits(*flip)
    dut.power_on()
    after = dut.wait_ready(READY_MS)
    rx = boot_rx(dut, dut.current_boot().idx)
    diag = [l for l in rx if __import__("re").search(CORRUPT_RX, l)]
    record_property("entries_flipped", len(touched))
    record_property("before", (before["counter"], before["relay"]))
    record_property("after", (after["counter"], after["relay"], dut.relay()))
    record_property("diagnostic", diag)
    if saved_relay == "off":
        assert dut.relay() == 0, "corrupted flash switched the relay ON (saved state was OFF)"
    assert diag, f"corruption not reported; device silently loaded counter={after['counter']} relay={after['relay']}"


@pytest.mark.req("R6", "R1")
def test_DI06_blank_flash_defaults(dut, record_property):
    """TC-DI-06: first boot with erased flash -> safe defaults (counter 0, relay OFF), ACTIVE, no reset loop."""
    st = dut.status()
    dut.wait(5000)
    record_property("status", st)
    assert st["counter"] == 0 and st["relay"] is False and dut.relay() == 0
    assert dut.boot_count == 1


@pytest.mark.req("R6")
def test_DI07_repeated_powerloss_x5(dut, record_property):
    """TC-DI-07: 5 interrupted saves in a row: each time the state stays old-or-new, never drifts."""
    seq = [dut.status()["counter"]]
    for i in range(5):
        dut.press_button(bounce=False, release_bounce=False)
        dut.cmd("save"); dut.wait(200)
        before = dut.status()["counter"]
        n = dut.boot_count
        dut.send("powerloss")
        dut.wait_boot(n, timeout=5000)
        after = dut.wait_ready(READY_MS)["counter"]
        seq.append((before, after))
    record_property("before_after", seq[1:])
    bad = [(b, a) for b, a in seq[1:] if a not in (b, b + 1)]
    assert not bad, f"{len(bad)}/5 interrupted saves left an invalid counter: {bad}"
