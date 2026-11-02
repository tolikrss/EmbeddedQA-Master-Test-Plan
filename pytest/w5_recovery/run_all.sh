#!/usr/bin/env bash
# Builds both firmwares and runs the whole non-functional suite.
#   ./run_all.sh            -> demo x1, buggy x3 (reproducibility)
#   REPEAT=5 ./run_all.sh   -> buggy x5
set -uo pipefail
cd "$(dirname "$0")"
./build.sh
REPEAT=${REPEAT:-3}
python3 -m pytest --fw demo --run-tag run1 --junitxml=results/demo/run1/junit.xml \
  --html=results/demo/run1/report.html --self-contained-html -q | tee results_demo_run1.txt | tail -3
for i in $(seq 1 "$REPEAT"); do
  python3 -m pytest --fw buggy --run-tag run$i --junitxml=results/buggy/run$i/junit.xml \
    --html=results/buggy/run$i/report.html --self-contained-html -q | tee results_buggy_run$i.txt | tail -3
done
python3 tools/summarize.py
