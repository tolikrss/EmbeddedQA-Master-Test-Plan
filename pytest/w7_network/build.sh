#!/usr/bin/env bash
# Builds the UNMODIFIED Webinar 7 sketches against the host model (hal/).
set -euo pipefail
cd "$(dirname "$0")"
for fw in buggy demo; do
  src=firmware/$fw/sketch.ino
  [ -f "$src" ] || { echo "missing $src (copy it from the course package)"; exit 1; }
  cp "$src" build_$fw.cpp
  # -O0 -fno-allocation-dce: at -O1+ GCC may delete a new/delete pair or an unused
  # allocation, which hides heap leaks from the heap model (found when cross-checking
  # against the W7 submission: -O1 showed a flat heap, -O0 shows -64 B per message).
  g++ -std=c++17 -O0 -fno-allocation-dce -w -Ihal -include Arduino.h build_$fw.cpp hal/hal7.cpp -o node_$fw -lpthread
  echo "built node_$fw (sketch sha256 $(sha256sum "$src" | cut -c1-12))"
done
