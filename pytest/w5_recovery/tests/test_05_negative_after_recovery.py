"""5. Negative tests after recovery: wrong / unexpected input right after every kind of reset."""
import re

import pytest

from helpers import ERROR_RX, READY_MS, RECOVERIES, resets_since

BAD_INPUT = {
    "unknown_word": "foo",
    "relay_bad_arg": "relay maybe",
    "relay_no_arg": "relay",
    "upper_case": "STATUS",
    "save_extra_arg": "save extra",
    "hang_extra_arg": "hang now",
    "binary_garbage": b"\x01\x7f\xc3\x28\xff",
    "overlong_300": "x" * 300,
    "empty_line": "",
}
EXPECT_ERROR = {"unknown_word", "relay_bad_arg", "relay_no_arg", "upper_case", "save_extra_arg",
                "hang_extra_arg", "binary_garbage"}


def _prepare(d):
    """Known state before the fault: relay ON, a couple of events, saved."""
    d.press_button(bounce=False, release_bounce=False)
    d.cmd("save"); d.wait(200)


@pytest.mark.req("R1", "R7")
@pytest.mark.parametrize("bad", list(BAD_INPUT))
@pytest.mark.parametrize("recovery", list(RECOVERIES))
def test_NEG01_invalid_command_after_recovery(dut, recovery, bad, record_property):
    """TC-NEG-01: after <recovery>, an invalid command must not reset the device, change relay/counter,
    or block the CLI; a malformed command must be answered with an explicit error."""
    _prepare(dut)
    RECOVERIES[recovery](dut)
    before = dut.status()
    pin_before = dut.relay()
    boot_idx = dut.current_boot().idx
    m = dut.mark()
    dut.send(BAD_INPUT[bad])
    dut.wait(1500)
    reply = [e.text for e in dut.lines(m) if e.text.strip()]
    after = dut.status()
    record_property("reply", reply[:3])
    record_property("before", (before["counter"], before["relay"], pin_before))
    record_property("after", (after["counter"], after["relay"], dut.relay()))
    assert resets_since(dut, boot_idx) == 0, "invalid input caused a reset"
    assert (after["counter"], after["relay"], dut.relay()) == (before["counter"], before["relay"], pin_before), \
        "invalid input changed device state"
    if bad in EXPECT_ERROR:
        assert any(re.search(ERROR_RX, l) for l in reply), f"no error diagnostic for {BAD_INPUT[bad]!r}: {reply}"


@pytest.mark.req("R1")
@pytest.mark.parametrize("recovery", ["wdt", "brownout", "power_cycle"])
def test_NEG02_garbage_on_uart_while_booting(dut, recovery, record_property):
    """TC-NEG-02: noise on UART during the boot after a fault -> device still becomes ACTIVE, nothing is executed."""
    dut.cmd("relay off"); dut.cmd("save"); dut.wait(200)
    c0 = dut.status()["counter"]
    n = dut.boot_count
    if recovery == "wdt":
        dut.send("hang")
    elif recovery == "brownout":
        dut.hw("BROWNOUT")
    else:
        dut.power_off_ms = 500
        dut.hw("POWERCUT")
    b = dut.wait_boot(n, timeout=15000)
    for chunk in (b"\x00\xff\xfe", b"relay o", b"\r\n\x1b[A", b"zzzz\n"):
        dut.wait(40)
        dut.send(chunk, eol=b"")
    st = dut.wait_ready(READY_MS)
    dut.wait(3000)
    record_property("status", st)
    assert resets_since(dut, b.idx) == 0
    assert dut.relay() == 0 and st["relay"] is False, "boot-time noise switched the relay"
    assert st["counter"] == c0


@pytest.mark.req("R4")
@pytest.mark.parametrize("arg", ["abc", "-5", "0", "99999999", "5abc", ""])
def test_NEG03_sleep_with_invalid_argument_after_wdt(dut, arg, record_property):
    """TC-NEG-03: `sleep <bad>` after a WDT recovery must never leave the device asleep for ever / unusable.
    Requirement R4 does not define limits, so the check is robustness: awake and ACTIVE within 70 s."""
    RECOVERIES["wdt"](dut)
    c0 = dut.status()["counter"]
    n = dut.boot_count
    m = dut.mark()
    dut.send(f"sleep {arg}".strip())
    dut.wait(500)
    went_to_sleep = dut.current_boot().end_kind == "SLEEP" or dut.boot_count > n
    if went_to_sleep:
        dut.wait_boot(n, timeout=70000)
    st = dut.wait_ready(READY_MS)
    reply = [e.text for e in dut.lines(m) if e.kind == "RX" and e.boot == n - 1 and e.text.strip()]
    sleeper = dut.boots[n - 1]
    record_property("reply", reply[:3])
    record_property("slept_ms", round(dut.boots[n].t - sleeper.end_t) if went_to_sleep else 0)
    assert st["state"] == "ACTIVE"
    assert c0 <= st["counter"] <= c0 + 1


@pytest.mark.req("R2")
@pytest.mark.parametrize("recovery", list(RECOVERIES))
def test_NEG04_sensor_disconnected_after_recovery(dut, recovery, record_property):
    """TC-NEG-04: DHT22 unplugged after <recovery> -> explicit sensor error, no fake value, relay unchanged."""
    RECOVERIES[recovery](dut)
    pin0 = dut.relay()
    dut.set_dht("nan")
    m = dut.mark()
    dut.send("sensor")
    dut.wait(500)
    reply = [e.text for e in dut.lines(m) if e.text.strip()]
    st = dut.status()
    record_property("reply", reply)
    record_property("sensor_ok", st["sensor_ok"])
    assert st["sensor_ok"] is False
    assert dut.relay() == pin0
    assert any("ERROR" in l.upper() for l in reply), f"no explicit sensor error: {reply}"
    assert not any(re.search(r"temp=\s*-?\d", l) for l in reply), f"invalid reading reported as a value: {reply}"
