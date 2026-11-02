"""Webinar 7: IoT network node, black-box tests (network, buffer, duplicates, memory).

Requirements: requirements/device_requirements.md (R1..R8).
Only the UART CLI is used: NET DOWN/UP, SEND, STRESS <N>, BUFFER, STATUS, RESET STATS.
"""
import re

import pytest

PUB = re.compile(r"\[MQTT\] publish id=(\d+)")
RETRY = re.compile(r"\[NET\] retry=(\d+) backoff_ms=(\d+)")
QUEUED = re.compile(r"\[BUFFER\] queued id=(\d+)")


def texts(lines):
    return [l[2] for l in lines if l[1] == "@T"]


def published_ids(lines):
    return [int(m.group(1)) for t in texts(lines) for m in [PUB.search(t)] if m]


def go_offline_and_send(dut, n_send):
    dut.cmd("NET DOWN", 200)
    queued = []
    for _ in range(n_send):
        out = dut.cmd("SEND", 120)
        queued += [int(m.group(1)) for t in texts(out) for m in [QUEUED.search(t)] if m]
    return queued


def go_online(dut, wait_ms=10000):
    i = dut.mark()
    dut.send("NET UP")
    end = dut.wait_for(lambda l: "flush_end" in l[2], timeout_dev_ms=wait_ms, start=i)
    dut.wait_dev(300)
    return dut.since(i), end


# ---------------- R1/R2: connection loss, retry, recovery ----------------

def test_NET01_no_hang_during_outage(dut, record):
    dut.cmd("NET DOWN", 200)
    answered = 0
    for _ in range(5):
        dut.wait_dev(2000)
        s = dut.status()
        answered += s is not None
    record("status_answered_of_5", answered)
    assert answered == 5, "node stopped answering STATUS while network is down"


def test_NET02_backoff_grows_no_reconnect_storm(dut, record):
    """R2: retry must use backoff and must not create a reconnect storm.
    Acceptance: backoff never decreases, every backoff >= first backoff (500 ms),
    and in a 20 s outage there are at most 10 attempts."""
    i = dut.mark()
    dut.send("NET DOWN")
    dut.wait_dev(20000)
    retries = [(int(m.group(1)), int(m.group(2))) for t in texts(dut.since(i)) for m in [RETRY.search(t)] if m]
    backoffs = [b for _, b in retries]
    record("attempts_20s", len(retries))
    record("backoff_seq_first10", backoffs[:10])
    assert retries, "no retry observed"
    assert all(b2 >= b1 for b1, b2 in zip(backoffs, backoffs[1:])), f"backoff decreases: {backoffs[:6]}"
    assert min(backoffs) >= backoffs[0], f"backoff below initial: min={min(backoffs)}"
    assert len(retries) <= 10, f"reconnect storm: {len(retries)} attempts in 20 s"


def test_NET03_recovery_after_net_up(dut, record):
    dut.cmd("NET DOWN", 200)
    dut.wait_dev(6000)
    i = dut.mark()
    dut.send("NET UP")
    ok = dut.wait_for(lambda l: "reconnect=SUCCESS" in l[2], timeout_dev_ms=10000, start=i)
    t_up = dut.since(i)[0][0] if dut.since(i) else None
    record("recovery_ms", round(ok[0] - t_up, 1) if ok and t_up else None)
    s = dut.status()
    record("state_after", s["net"])
    assert ok and s["net"] == "CONNECTED" and s["broker"] is True


# ---------------- R3/R5: offline buffer and flush ----------------

def test_BUF01_offline_messages_are_buffered(dut, record):
    dut.cmd("RESET STATS")
    queued = go_offline_and_send(dut, 5)
    b = texts(dut.cmd("BUFFER"))
    record("queued_ids", queued)
    record("buffer_line", b)
    assert len(queued) == 5 and any("count=5" in t for t in b)


def test_BUF02_buffer_flushed_exactly_once(dut, record):
    dut.cmd("RESET STATS")
    queued = go_offline_and_send(dut, 5)
    lines, end = go_online(dut)
    ids = published_ids(lines)
    s = dut.status()
    record("queued", queued)
    record("published", ids)
    record("status", s)
    assert end, "flush did not finish"
    assert ids == queued, f"flush must publish each buffered id once in FIFO order, got {ids}"
    assert s["duplicates"] == 0 and s["buffer"] == 0


# ---------------- R4: boundary of buffer capacity ----------------

@pytest.mark.parametrize("n", [7, 8, 9, 12])
def test_BUF03_capacity_boundary_counters(dut, record, n):
    dut.cmd("RESET STATS")
    go_offline_and_send(dut, n)
    s = dut.status()
    exp_count, exp_drop = min(n, 8), max(0, n - 8)
    record("sent_offline", n)
    record("buffer", s["buffer"])
    record("dropped", s["dropped"])
    assert s["capacity"] == 8
    assert s["buffer"] == exp_count, f"occupancy {s['buffer']} for capacity 8"
    assert s["dropped"] == exp_drop, f"dropped counter {s['dropped']}, expected {exp_drop}"


@pytest.mark.parametrize("n", [8, 9, 12])
def test_BUF04_drop_oldest_keeps_newest_in_order(dut, record, n):
    dut.cmd("RESET STATS")
    queued = go_offline_and_send(dut, n)
    lines, _ = go_online(dut)
    ids = published_ids(lines)
    expected = queued[-8:]
    lost_silently = sorted(set(queued) - set(ids))
    record("queued", queued)
    record("published", ids)
    record("lost_ids", lost_silently)
    assert ids == expected, f"expected newest 8 in FIFO order {expected}, got {ids}"


# ---------------- R6: duplicates across reconnects ----------------

def test_DUP01_no_duplicate_ids_over_5_flaps(dut, record):
    dut.cmd("RESET STATS")
    all_ids = []
    for _ in range(5):
        go_offline_and_send(dut, 3)
        lines, _ = go_online(dut)
        all_ids += published_ids(lines)
    s = dut.status()
    dups = len(all_ids) - len(set(all_ids))
    record("published_total", len(all_ids))
    record("unique_ids", len(set(all_ids)))
    record("status_duplicates", s["duplicates"])
    assert dups == 0, f"{dups} duplicate publications of the same id"


# ---------------- R7: memory stability ----------------

def test_MEM01_heap_trend_online_stress(dut, record):
    heaps = [dut.status()["heap"]]
    for _ in range(10):
        i = dut.mark()
        dut.send("STRESS 100")
        dut.wait_for(lambda l: "[STRESS] end" in l[2], timeout_dev_ms=5000, start=i)
        dut.wait_dev(200)
        heaps.append(dut.status()["heap"])
    record("heap_series", heaps)
    record("delta_bytes", heaps[-1] - heaps[0])
    record("bytes_per_message", round((heaps[0] - heaps[-1]) / 1000.0, 1))
    assert heaps[-1] >= heaps[0] - 1024, f"systematic heap drop: {heaps[0]} -> {heaps[-1]} over 1000 messages"


def test_MEM02_heap_and_buffer_offline_stress(dut, record):
    heaps, occ = [dut.status()["heap"]], []
    for _ in range(5):
        dut.cmd("NET DOWN", 200)
        i = dut.mark()
        dut.send("STRESS 100")
        dut.wait_for(lambda l: "[STRESS] end" in l[2], timeout_dev_ms=5000, start=i)
        dut.wait_dev(200)
        s = dut.status()
        occ.append(s["buffer"])
        go_online(dut)
        heaps.append(dut.status()["heap"])
    record("heap_series", heaps)
    record("buffer_occupancy_offline", occ)
    assert max(occ) <= 8, f"buffer occupancy {max(occ)} exceeds capacity 8"
    assert heaps[-1] >= heaps[0] - 1024, f"systematic heap drop: {heaps[0]} -> {heaps[-1]}"


# ---------------- R8: observability ----------------

def test_OBS01_status_has_required_fields(dut, record):
    s = dut.status()
    need = {"net", "buffer", "capacity", "sent", "dropped", "duplicates", "reconnect_attempts", "heap"}
    record("fields", sorted(s))
    assert need <= set(s)


@pytest.mark.parametrize("bad", ["HELP", "stress 5", "NET", "NET SIDEWAYS", "STATUSX"])
def test_NEG01_unknown_command_rejected_without_side_effects(dut, record, bad):
    before = dut.status()
    out = texts(dut.cmd(bad))
    after = dut.status()
    record("response", out)
    assert any("ERROR" in t for t in out)
    for k in ("net", "buffer", "sent", "dropped"):
        assert before[k] == after[k], f"{k} changed after invalid command"
