#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="$ROOT_DIR/venv/bin/python"
PYTHON_HEALTH_URL="http://127.0.0.1:8000/api/health"

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

verify_python_runtime_health() {
  local health_json

  if ! health_json="$(curl -sf "$PYTHON_HEALTH_URL")"; then
    echo ""
    echo "❌ Python runtime health check failed: $PYTHON_HEALTH_URL is unreachable."
    echo "Failure mode: local AI runtime is not running (or wrong process bound to :8000)."
    echo "Fix path: start local stack with 'bash dev.sh' and re-run this script."
    exit 1
  fi

  if ! HEALTH_JSON="$health_json" "$VENV_PY" - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["HEALTH_JSON"])
runtime = payload.get("runtime")
scan_runtime = payload.get("scan_runtime") or {}

if not isinstance(runtime, dict):
    print("❌ Health payload missing 'runtime' block.")
    print("Failure mode: Python server is outdated or not the hardened local runtime.")
    sys.exit(1)

if runtime.get("inside_docker"):
    print("❌ Runtime mismatch: inside_docker=true for /api/health on :8000.")
    print("Failure mode: app-path may be hitting container runtime instead of local venv runtime.")
    sys.exit(1)

if not runtime.get("using_expected_venv"):
    print("❌ Runtime mismatch: python executable is not from repo venv.")
    print(f"python_executable={runtime.get('python_executable')}")
    print(f"expected_venv={runtime.get('expected_venv')}")
    print("Failure mode: wrong interpreter can produce scan drift or missing dependencies.")
    sys.exit(1)

if not payload.get("ai_ready"):
    print("❌ ai_ready=false on /api/health.")
    print("Failure mode: API is up but scan runtime is not ready; requests may fall back to mock mode.")
    last_error = scan_runtime.get("pipeline_last_error")
    if last_error:
        print(f"pipeline_last_error={last_error}")
    sys.exit(1)

mode = scan_runtime.get("mode")
print(f"✅ Python runtime health OK (mode={mode})")
PY
  then
    exit 1
  fi
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

  section "Python runtime health checks"
  verify_python_runtime_health

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
