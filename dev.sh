#!/bin/bash
# ============================================
# MedicineApp Dev Startup Script
# Khởi động stack dev ổn định cho Android thật qua USB + adb reverse.
# PostgreSQL chạy bằng Docker, còn Node API và Python AI chạy local.
# Usage: bash dev.sh
# ============================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOBILE_ENV="$PROJECT_DIR/mobile/.env"
VENV="$PROJECT_DIR/venv/bin/activate"
NODE_PORT=3001
PYTHON_PORT=8000
DEVICE_ID="${ANDROID_DEVICE_ID:-}"

echo "🚀 MedicineApp Dev Startup"
echo "=========================="

# 1. Update mobile/.env to localhost for adb reverse workflow
sed -i "s|API_BASE_URL=.*|API_BASE_URL=http://127.0.0.1:${NODE_PORT}/api|" "$MOBILE_ENV"
echo "✅ Updated $MOBILE_ENV → API_BASE_URL=http://127.0.0.1:${NODE_PORT}/api"

# 2. Start PostgreSQL only via Docker
echo ""
echo "🐳 Starting Docker services (postgres only)..."
cd "$PROJECT_DIR"
docker compose up -d postgres
echo "✅ PostgreSQL started"

# 3. Run DB migrations
echo ""
echo "🗄️  Running migrations..."
cd "$PROJECT_DIR/server-node" && npm run migrate 2>&1 | tail -3

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
nohup node src/server.js > /tmp/medicine-node.log 2>&1 &
NODE_PID=$!
echo "📝 Node logs: /tmp/medicine-node.log (PID: $NODE_PID)"

echo "⏳ Waiting for Node.js to be healthy..."
for i in $(seq 1 12); do
  if curl -sf http://127.0.0.1:${NODE_PORT}/api/health > /dev/null 2>&1; then
    echo "✅ Node.js API ready at http://127.0.0.1:${NODE_PORT}"
    break
  fi
  sleep 2
done

# 5. Start Python AI server (local venv)
echo ""
echo "🤖 Starting Python AI server (local venv)..."
source "$VENV"
cd "$PROJECT_DIR"
# Kill any existing python AI server
pkill -f "uvicorn server.main:app" 2>/dev/null || true
sleep 1
# Start in background
nohup uvicorn server.main:app --host 0.0.0.0 --port ${PYTHON_PORT} > /tmp/python-ai.log 2>&1 &
AI_PID=$!
echo "📝 Python AI logs: /tmp/python-ai.log (PID: $AI_PID)"

# 6. Setup adb reverse for Android USB debugging
echo ""
echo "📱 Setting up adb reverse..."
ADB_ARGS=()
if [ -n "$DEVICE_ID" ]; then
  ADB_ARGS=(-s "$DEVICE_ID")
fi

if adb "${ADB_ARGS[@]}" get-state >/dev/null 2>&1; then
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
