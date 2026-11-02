"""Summarize results/<fw>/runN/results.jsonl into Markdown (outcomes, repeatability, measured values)."""
import glob
import json
import os
import sys
from collections import OrderedDict

root = sys.argv[1] if len(sys.argv) > 1 else "results"
print("# W7 network suite: summary\n")
for fw in ("demo", "buggy"):
    runs = sorted(glob.glob(os.path.join(root, fw, "run*", "results.jsonl")))
    if not runs:
        continue
    table = OrderedDict()
    for r in runs:
        for line in open(r, encoding="utf-8"):
            d = json.loads(line)
            t = table.setdefault(d["test"], {"out": [], "measured": d["measured"]})
            t["out"].append(d["outcome"])
    fails = sum(1 for t in table.values() if "failed" in t["out"])
    print(f"## {fw}: {len(table)} tests x {len(runs)} run(s): {len(table) - fails} PASS / {fails} FAIL\n")
    print("| Test | Result | Repro | Key measurements (run1) |\n|---|---|---|---|")
    for name, t in table.items():
        res = "FAIL" if "failed" in t["out"] else "PASS"
        rep = f"{t['out'].count('failed' if res == 'FAIL' else 'passed')}/{len(t['out'])}"
        meas = "; ".join(f"{k}={v}" for k, v in t["measured"].items())
        print(f"| `{name}` | {res} | {rep} | {meas[:220].replace('|', '/')} |")
    print()
