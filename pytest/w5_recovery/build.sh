#!/usr/bin/env bash
# Builds the UNMODIFIED Wokwi sketches against the host hardware model.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build
for fw in demo buggy; do
  src=firmware/$fw/sketch.ino
  # Arduino IDE auto-generates prototypes; we let g++ see the sketch as-is via a wrapper unit.
  printf '#include <Arduino.h>\n#include "../%s"\n' "$src" > build/${fw}_unit.cpp
  g++ -std=gnu++17 -O0 -g -Wall -Wno-unused-variable -Ihal build/${fw}_unit.cpp hal/hal.cpp -o build/fw_$fw -lpthread
  echo "built build/fw_$fw  (sketch sha256 $(sha256sum $src | cut -c1-12))"
done
