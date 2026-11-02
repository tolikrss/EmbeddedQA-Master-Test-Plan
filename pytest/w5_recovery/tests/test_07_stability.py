"""Repeated recovery / stability: a long random mix of every fault type."""
import random

import pytest

from helpers import READY_MS, RECOVERIES, resets_since


@pytest.mark.req("R1", "R4", "R5", "R6")
@pytest.mark.parametrize("seed", [11, 22])
def test_REC01_mixed_fault_storm_x20(dut, seed, record_property):
    """TC-REC-01: 20 random faults (WDT, brown-out, power cut, interrupted save, deep sleep) with random activity
    in between -> every time ACTIVE within 5 s, relay OFF after emergency resets, no boot loop, CLI works."""
    rnd = random.Random(seed)
    history = []
    for i in range(20):
        for _ in range(rnd.randint(0, 3)):
            c = rnd.choice(["relay on", "relay off", "save", "sensor", "status"])
            dut.send(c)
            dut.wait(rnd.uniform(20, 200))
        kind = rnd.choice(list(RECOVERIES))
        RECOVERIES[kind](dut)
        st = dut.status()
        history.append((kind, st["reset_reason"], st["counter"], dut.relay()))
    boot_idx = dut.current_boot().idx
    dut.wait(10000)
    record_property("history_kind_reason_counter_relay", history)
    problems = []
    if resets_since(dut, boot_idx):
        problems.append("device keeps resetting after the fault storm")
    unsafe = [h for h in history if h[0] in ("wdt", "brownout") and h[3] == 1]
    if unsafe:
        problems.append(f"relay ON after {len(unsafe)} emergency resets: {unsafe}")
    counters = [h[2] for h in history]
    jumps = [(a, b) for a, b in zip(counters, counters[1:]) if b < a or b - a > 10]
    if jumps:
        problems.append(f"persistent counter jumped/rolled back {len(jumps)}x: {jumps}")
    assert not problems, " | ".join(problems)
