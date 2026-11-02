#!/usr/bin/env bash
# DEMO x1 (control) + BUGGY x3 (repeatability). Results go to results/<fw>/runN/.
set -uo pipefail
cd "$(dirname "$0")"
./build.sh
rm -rf results
for spec in demo:1 buggy:1 buggy:2 buggy:3; do
  fw=${spec%%:*}; r=${spec##*:}; out=results/$fw/run$r
  mkdir -p "$out"
  python3 -m pytest --fw=$fw --out=$out -q -rf --junitxml=$out/junit.xml tests > $out/pytest_output.txt 2>&1
  echo "$fw run$r: $(tail -1 $out/pytest_output.txt)"
done
python3 tools/summarize.py results > results/summary.md
