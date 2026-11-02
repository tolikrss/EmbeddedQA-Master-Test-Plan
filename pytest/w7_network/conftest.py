import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from node import Node  # noqa: E402


def pytest_addoption(parser):
    parser.addoption("--fw", default="buggy", choices=["buggy", "demo"])
    parser.addoption("--out", default="results/run")
    parser.addoption("--scale", default="10")


@pytest.fixture
def dut(request):
    cfg = request.config
    out = os.path.join(ROOT, cfg.getoption("--out"), "logs")
    os.makedirs(out, exist_ok=True)
    name = re.sub(r"[^\w\-\[\]=.]", "_", request.node.name)
    n = Node(os.path.join(ROOT, f"node_{cfg.getoption('--fw')}"), float(cfg.getoption("--scale")),
             os.path.join(out, name + ".log"))
    n.note(f"test {request.node.nodeid} fw={cfg.getoption('--fw')}")
    request.node._dut = n
    yield n
    n.close()


@pytest.fixture
def record(request):
    def _r(k, v):
        request.node.user_properties.append((k, json.dumps(v) if not isinstance(v, str) else v))
        d = getattr(request.node, "_dut", None)
        if d:
            d.note(f"MEASURED {k} = {v}")
    return _r


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    rep = (yield).get_result()
    if rep.when == "call":
        out = os.path.join(ROOT, item.config.getoption("--out"))
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "results.jsonl"), "a") as f:
            f.write(json.dumps({"test": item.nodeid.split("::")[-1], "outcome": rep.outcome,
                                "measured": dict(item.user_properties),
                                "message": str(rep.longrepr.reprcrash.message) if rep.failed else ""},
                               ensure_ascii=False) + "\n")
