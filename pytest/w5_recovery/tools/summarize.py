"""Aggregate results/<fw>/run*/results.jsonl -> results/summary.json + summary.md (pass/fail per test, reproducibility)."""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
out = {}
md = ["# Test summary\n"]
for fw_dir in sorted((ROOT / "results").glob("*")):
    if not fw_dir.is_dir():
        continue
    runs = sorted(fw_dir.glob("run*/results.jsonl"))
    per = defaultdict(list)
    props = {}
    for r in runs:
        for line in r.read_text().splitlines():
            e = json.loads(line)
            per[e["nodeid"]].append(e["outcome"])
            if e["nodeid"] not in props or (e["outcome"] == "failed" and props[e["nodeid"]]["outcome"] != "failed"):
                props[e["nodeid"]] = e
    total = len(per)
    failed = {k: v for k, v in per.items() if "failed" in v}
    out[fw_dir.name] = {"runs": len(runs), "tests": total, "failed": len(failed),
                        "passed": total - len(failed),
                        "tests_detail": {k: {"outcomes": v, "props": props[k]["props"], "message": props[k]["message"],
                                             "log": props[k]["log"]} for k, v in per.items()}}
    md.append(f"## {fw_dir.name}: {total} tests x {len(runs)} run(s) -> {total - len(failed)} passed, {len(failed)} failed\n")
    for k, v in sorted(failed.items()):
        md.append(f"- {k.split('::')[-1]}  fail {v.count('failed')}/{len(v)} — {props[k]['message']}")
    md.append("")
(ROOT / "results" / "summary.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
(ROOT / "results" / "summary.md").write_text("\n".join(md))
print("\n".join(md[:3] + [l for l in md if l.startswith("## ")]))
