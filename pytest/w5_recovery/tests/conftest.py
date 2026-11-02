import json
import re
import subprocess
from pathlib import Path

import pytest

from dut import Device

ROOT = Path(__file__).resolve().parent.parent


def pytest_addoption(parser):
    parser.addoption("--fw", default="buggy", choices=["demo", "buggy"],
                     help="firmware build under test (demo = reference, buggy = homework)")
    parser.addoption("--run-tag", default="run1", help="sub-folder for this run's results/logs")
    parser.addoption("--scale", default=10.0, type=float,
                     help="time acceleration of the hardware model (device ms per real ms)")


def pytest_configure(config):
    config.addinivalue_line("markers", "req(id): requirement covered by the test")
    if not (ROOT / "build" / f"fw_{config.getoption('--fw')}").exists():
        subprocess.run([str(ROOT / "build.sh")], check=True)


@pytest.fixture(scope="session")
def fw_name(request):
    return request.config.getoption("--fw")


@pytest.fixture(scope="session")
def results_dir(request, fw_name):
    d = ROOT / "results" / fw_name / request.config.getoption("--run-tag")
    (d / "logs").mkdir(parents=True, exist_ok=True)
    return d


def _safe(nodeid: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.\-\[\]]+", "_", nodeid.split("::", 1)[-1])[:150]


@pytest.fixture
def dut(request, fw_name, results_dir, tmp_path):
    """Fresh device: erased flash, power-on, waits until ACTIVE (R1)."""
    d = Device(ROOT / "build" / f"fw_{fw_name}", tmp_path, scale=request.config.getoption("--scale"))
    request.node.dut = d
    d.power_on(fresh_flash=True)
    d.wait_ready()
    yield d
    d.shutdown()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when != "call" and not (rep.when == "setup" and rep.failed):
        return
    d = getattr(item, "dut", None)
    res_dir = ROOT / "results" / item.config.getoption("--fw") / item.config.getoption("--run-tag")
    (res_dir / "logs").mkdir(parents=True, exist_ok=True)
    log_path = res_dir / "logs" / (_safe(item.nodeid) + ".log")
    if d is not None:
        d.dump_log(log_path)
    props = dict(item.user_properties)
    entry = {
        "nodeid": item.nodeid,
        "outcome": rep.outcome,
        "duration_s": round(rep.duration, 3),
        "props": props,
        "log": str(log_path.relative_to(ROOT)) if d is not None else None,
        "message": (rep.longrepr.reprcrash.message if rep.failed and hasattr(rep.longrepr, "reprcrash") else None),
    }
    with open(res_dir / "results.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    if d is not None:
        rep.sections.append(("device log", f"{log_path.relative_to(ROOT)}"))


def pytest_sessionstart(session):
    import shutil
    res = ROOT / "results" / session.config.getoption("--fw") / session.config.getoption("--run-tag")
    if res.exists():
        shutil.rmtree(res)
    (res / "logs").mkdir(parents=True, exist_ok=True)
