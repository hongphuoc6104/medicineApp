#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="$ROOT_DIR/venv/bin/python"

MODE="quick"
RUN_SCAN_SMOKE=0
IMAGE_PATH=""
RUN_MOBILE=1
RUN_NODE=1
RUN_PYTHON=1

usage() {
  cat <<'EOF'
Usage:
  bash scripts/debug_phase_a_checks.sh [options]

Options:
  --quick            Run focused Phase A checks (default)
  --full             Run broader checks, including full Node suite
  --scan-smoke       Run Python app-path smoke script if available
  --image <path>     Run protected CLI pipeline on one image after checks
  --skip-mobile      Skip Flutter analyze/test
  --skip-node        Skip Node scan/full tests
  --skip-python      Skip Python compile/smoke checks
  --help             Show this help

Examples:
  bash scripts/debug_phase_a_checks.sh --quick
  bash scripts/debug_phase_a_checks.sh --full --scan-smoke
  bash scripts/debug_phase_a_checks.sh --quick --image "data/input/prescription_3/IMG_20260209_180505.jpg"
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --quick)
      MODE="quick"
      shift
      ;;
    --full)
      MODE="full"
      shift
      ;;
    --scan-smoke)
      RUN_SCAN_SMOKE=1
      shift
      ;;
    --image)
      IMAGE_PATH="${2:-}"
      if [[ -z "$IMAGE_PATH" ]]; then
        echo "Missing value for --image" >&2
        exit 1
      fi
      shift 2
      ;;
    --skip-mobile)
      RUN_MOBILE=0
      shift
      ;;
    --skip-node)
      RUN_NODE=0
      shift
      ;;
    --skip-python)
      RUN_PYTHON=0
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

section() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$1"
}

run_in_dir() {
  local dir="$1"
  shift
  (cd "$dir" && "$@")
}

section "Phase A debug checks: $MODE"
section "Workspace summary"
run_in_dir "$ROOT_DIR" git status --short || true

if [[ "$RUN_PYTHON" -eq 1 ]]; then
  if [[ ! -x "$VENV_PY" ]]; then
    echo "Python venv not found at $VENV_PY" >&2
    exit 1
  fi

  section "Python compile checks"
  run_in_dir "$ROOT_DIR" "$VENV_PY" -m py_compile core/pipeline.py server/main.py

  if [[ "$RUN_SCAN_SMOKE" -eq 1 && -f "$ROOT_DIR/scripts/tests/test_phase_a_api_alignment.py" ]]; then
    section "Python scan app-path smoke"
    run_in_dir "$ROOT_DIR" "$VENV_PY" scripts/tests/test_phase_a_api_alignment.py
  fi
fi

if [[ "$RUN_NODE" -eq 1 ]]; then
  if [[ "$MODE" == "quick" ]]; then
    section "Node focused Phase A tests"
    run_in_dir "$ROOT_DIR/server-node" npm test -- tests/unit/scan.service.test.js tests/integration/scan.routes.test.js
  else
    section "Node full test suite"
    run_in_dir "$ROOT_DIR/server-node" npm test
  fi
fi

if [[ "$RUN_MOBILE" -eq 1 ]]; then
  section "Flutter analyze"
  run_in_dir "$ROOT_DIR/mobile" flutter analyze

  section "Flutter test"
  run_in_dir "$ROOT_DIR/mobile" flutter test
fi

if [[ -n "$IMAGE_PATH" ]]; then
  if [[ ! -f "$ROOT_DIR/$IMAGE_PATH" && ! -f "$IMAGE_PATH" ]]; then
    echo "Image not found: $IMAGE_PATH" >&2
    exit 1
  fi
  section "Protected CLI pipeline smoke"
  if [[ -f "$ROOT_DIR/$IMAGE_PATH" ]]; then
    run_in_dir "$ROOT_DIR" "$VENV_PY" scripts/run_pipeline.py --image "$ROOT_DIR/$IMAGE_PATH"
  else
    run_in_dir "$ROOT_DIR" "$VENV_PY" scripts/run_pipeline.py --image "$IMAGE_PATH"
  fi
fi

section "Phase A checks completed successfully"
