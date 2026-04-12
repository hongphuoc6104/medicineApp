#!/bin/bash
# ============================================
# MedicineApp Dev Startup Script
# Khởi động stack dev ổn định cho Android thật qua USB + adb reverse.
# PostgreSQL chạy bằng Docker, còn Node API và Python AI chạy local.
# Usage: bash dev.sh
# ============================================

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOBILE_ENV="$PROJECT_DIR/mobile/.env"
VENV_DIR="$PROJECT_DIR/venv"
VENV_PY="$VENV_DIR/bin/python"
NODE_PORT=3001
PYTHON_PORT=8000
DEVICE_ID="${ANDROID_DEVICE_ID:-}"

fail() {
  echo ""
  echo "❌ $1" >&2
  exit 1
}

print_port_debug() {
  local port="$1"
  echo "🔎 Listener details for :${port}"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true
  elif command -v fuser >/dev/null 2>&1; then
    fuser -v "${port}/tcp" 2>/dev/null || true
  elif command -v ss >/dev/null 2>&1; then
    ss -ltnp "sport = :${port}" 2>/dev/null || true
  else
    echo "(No lsof/fuser/ss available to inspect listeners)"
  fi

  if command -v docker >/dev/null 2>&1; then
    local docker_port_hit
    docker_port_hit="$(docker ps --format '{{.Names}} {{.Ports}}' | grep ":${port}->" || true)"
    if [[ -n "$docker_port_hit" ]]; then
      echo "🐳 Docker containers publishing :${port}:"
      echo "$docker_port_hit"
    fi
  fi
}

assert_local_python_ready() {
  if [[ ! -d "$VENV_DIR" ]]; then
    fail "Missing venv at $VENV_DIR. Recreate it first: python3.12 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
  fi

  if [[ ! -x "$VENV_PY" ]]; then
    fail "Missing interpreter at $VENV_PY. Recreate venv and reinstall dependencies before running dev.sh"
  fi

  local py_version
  py_version="$($VENV_PY -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  local py_major py_minor
  py_major="${py_version%%.*}"
  py_minor="${py_version##*.}"

  if [[ "$py_major" -ne 3 || "$py_minor" -lt 10 ]]; then
    fail "Unsupported Python at $VENV_PY (found $py_version, require >=3.10)"
  fi

  if [[ "$py_version" != "3.12" ]]; then
    echo "⚠️  Using Python $py_version in venv (recommended: 3.12)."
  fi

  if ! "$VENV_PY" -c 'import fastapi, uvicorn' >/dev/null 2>&1; then
    fail "venv is present but missing FastAPI/Uvicorn. Run: source venv/bin/activate && pip install -r requirements.txt"
  fi
}

assert_python_port_free() {
  if ! "$VENV_PY" - "$PYTHON_PORT" <<'PY'
import socket
import sys

port = int(sys.argv[1])
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    sock.bind(("127.0.0.1", port))
except OSError:
    sys.exit(1)
finally:
    sock.close()
PY
  then
    echo ""
    echo "❌ Port ${PYTHON_PORT} is already in use."
    echo "This script refuses to continue to avoid silently using the wrong scan runtime."
    echo "Stop the listener on :${PYTHON_PORT}, then run: bash dev.sh"
    print_port_debug "$PYTHON_PORT"
    exit 1
  fi
}

wait_for_health() {
  local url="$1"
  local retries="$2"
  local sleep_sec="$3"
  local i

  for i in $(seq 1 "$retries"); do
    if curl -sf "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$sleep_sec"
  done

  return 1
}

verify_python_runtime_health() {
  local health_url="http://127.0.0.1:${PYTHON_PORT}/api/health"
  local health_json

  health_json="$(curl -sf "$health_url")" || fail "Python AI started but health endpoint is unavailable at $health_url"

  if ! HEALTH_JSON="$health_json" "$VENV_PY" - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["HEALTH_JSON"])
runtime = payload.get("runtime")
scan_runtime = payload.get("scan_runtime") or {}

if not isinstance(runtime, dict):
    print("Health response missing 'runtime' block.")
    sys.exit(1)

if runtime.get("inside_docker"):
    print("Runtime mismatch: inside_docker=true (expected local host runtime).")
    sys.exit(1)

if not runtime.get("using_expected_venv"):
    print(
        "Runtime mismatch: python_executable="
        f"{runtime.get('python_executable')} is not from expected venv "
        f"{runtime.get('expected_venv')}"
    )
    sys.exit(1)

if not payload.get("ai_ready"):
    print("AI runtime is up but ai_ready=false; scan may fall back to mock mode.")
    last_error = scan_runtime.get("pipeline_last_error")
    if last_error:
        print(f"pipeline_last_error: {last_error}")
    sys.exit(1)

print("✅ Python runtime verified (local venv + ai_ready=true)")
PY
  then
    fail "Python AI health is reachable but runtime check failed. See details above."
  fi
}

echo "🚀 MedicineApp Dev Startup"
echo "=========================="

[[ -f "$MOBILE_ENV" ]] || fail "Missing mobile env file at $MOBILE_ENV"
[[ -d "$PROJECT_DIR/server-node" ]] || fail "Missing server-node directory at $PROJECT_DIR/server-node"

assert_local_python_ready
assert_python_port_free

# 1. Update mobile/.env to localhost for adb reverse workflow
sed -i "s|API_BASE_URL=.*|API_BASE_URL=http://127.0.0.1:${NODE_PORT}/api|" "$MOBILE_ENV"
echo "✅ Updated $MOBILE_ENV → API_BASE_URL=http://127.0.0.1:${NODE_PORT}/api"

# 2. Start PostgreSQL only via Docker
echo ""
echo "🐳 Starting Docker services (postgres only)..."
docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d postgres
echo "✅ PostgreSQL started"

# 3. Run DB migrations
echo ""
echo "🗄️  Running migrations..."
(cd "$PROJECT_DIR/server-node" && npm run migrate)

# 4. Start Node API locally
echo ""
echo "🧩 Starting Node.js API locally..."
if command -v fuser >/dev/null 2>&1; then
  fuser -k ${NODE_PORT}/tcp 2>/dev/null || true
elif command -v lsof >/dev/null 2>&1; then
  lsof -ti tcp:${NODE_PORT} | xargs -r kill -9 2>/dev/null || true
else
  pkill -f "node --watch src/server.js\|node src/server.js" 2>/dev/null || true
fi
sleep 1
pushd "$PROJECT_DIR/server-node" >/dev/null
nohup node src/server.js > /tmp/medicine-node.log 2>&1 &
NODE_PID=$!
popd >/dev/null
echo "📝 Node logs: /tmp/medicine-node.log (PID: $NODE_PID)"

echo "⏳ Waiting for Node.js to be healthy..."
if ! wait_for_health "http://127.0.0.1:${NODE_PORT}/api/health" 12 2; then
  echo "⚠️ Node.js did not become healthy in time. Last log lines:"
  tail -n 40 /tmp/medicine-node.log || true
  fail "Node.js API failed to start on :${NODE_PORT}"
fi
echo "✅ Node.js API ready at http://127.0.0.1:${NODE_PORT}"

# 5. Start Python AI server (local venv)
echo ""
echo "🤖 Starting Python AI server (local venv)..."
pushd "$PROJECT_DIR" >/dev/null
nohup "$VENV_PY" -m uvicorn server.main:app --host 0.0.0.0 --port ${PYTHON_PORT} > /tmp/python-ai.log 2>&1 &
AI_PID=$!
popd >/dev/null
echo "📝 Python AI logs: /tmp/python-ai.log (PID: $AI_PID)"

echo "⏳ Waiting for Python AI health..."
if ! wait_for_health "http://127.0.0.1:${PYTHON_PORT}/api/health" 20 1; then
  echo "⚠️ Python AI did not become healthy in time. Last log lines:"
  tail -n 60 /tmp/python-ai.log || true
  fail "Python AI server failed to start on :${PYTHON_PORT}"
fi
verify_python_runtime_health

# 6. Setup adb reverse for Android USB debugging
echo ""
echo "📱 Setting up adb reverse..."
ADB_ARGS=()
if [ -n "$DEVICE_ID" ]; then
  ADB_ARGS=(-s "$DEVICE_ID")
fi

if ! command -v adb >/dev/null 2>&1; then
  echo "⚠️  adb not found. Install Android platform-tools to enable USB reverse."
elif adb "${ADB_ARGS[@]}" get-state >/dev/null 2>&1; then
  adb "${ADB_ARGS[@]}" reverse tcp:${NODE_PORT} tcp:${NODE_PORT}
  echo "✅ adb reverse tcp:${NODE_PORT} -> localhost:${NODE_PORT}"
else
  echo "⚠️  No Android device detected via adb. You can still run backend locally."
fi

# 7. Summary
echo ""
echo "============================================"
echo "✅ All services started!"
echo "  PostgreSQL  : localhost:5432 (Docker)"
echo "  Node.js API : http://127.0.0.1:${NODE_PORT} (local, PID: $NODE_PID)"
echo "  Python AI   : http://127.0.0.1:${PYTHON_PORT} (local venv, PID: $AI_PID)"
echo "  Mobile .env : API_BASE_URL=http://127.0.0.1:${NODE_PORT}/api"
echo ""
echo "📱 To run Flutter on phone:"
echo "  cd mobile && flutter run -d <device-id>"
echo "  (works across Wi-Fi changes as long as USB + adb reverse are active)"
echo ""
echo "📋 To stop Python AI:"
echo "  kill $AI_PID"
echo "To stop Node API:"
echo "  kill $NODE_PID"
echo "To stop Docker:"
echo "  docker compose down"
echo "============================================"
