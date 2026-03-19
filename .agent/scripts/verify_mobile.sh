#!/usr/bin/env bash
set -euo pipefail

echo "[mobile] flutter analyze"
flutter analyze

echo "[mobile] flutter test"
flutter test
