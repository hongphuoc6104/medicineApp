#!/bin/bash
# ============================================
# MedicineApp Dev Startup Script
# Tự động detect IP LAN, update .env, bật services
# Usage: bash dev.sh
# ============================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOBILE_ENV="$PROJECT_DIR/mobile/.env"
VENV="$PROJECT_DIR/venv/bin/activate"

echo "🚀 MedicineApp Dev Startup"
echo "=========================="

# 1. Detect IP LAN
IP=$(ip addr show | grep "inet " | grep -v "127\." | grep -v "172\." | awk '{print $2}' | cut -d/ -f1 | head -1)
if [ -z "$IP" ]; then
  IP=$(hostname -I | awk '{print $1}')
fi
echo "📡 IP LAN: $IP"

# 2. Update mobile/.env
sed -i "s|API_BASE_URL=.*|API_BASE_URL=http://$IP:3000/api|" "$MOBILE_ENV"
echo "✅ Updated $MOBILE_ENV → API_BASE_URL=http://$IP:3000/api"

# 3. Start PostgreSQL + Node.js via Docker Compose (không có python-ai)
echo ""
echo "🐳 Starting Docker services (postgres + node-api)..."
cd "$PROJECT_DIR"
docker compose up -d postgres node-api
echo "✅ Docker services started"

# 4. Chờ Node.js healthy
echo "⏳ Waiting for Node.js to be healthy..."
for i in $(seq 1 12); do
  if curl -sf http://localhost:3000/api/health > /dev/null 2>&1; then
    echo "✅ Node.js API ready at http://localhost:3000"
    break
  fi
  sleep 5
done

# 5. Run DB migrations & seed nếu chưa có
echo ""
echo "🗄️  Running migrations..."
cd "$PROJECT_DIR/server-node" && npm run migrate 2>&1 | tail -3

# 6. Start Python AI server (local venv)
echo ""
echo "🤖 Starting Python AI server (local venv)..."
source "$VENV"
cd "$PROJECT_DIR"
# Kill any existing python AI server
pkill -f "uvicorn server.main:app" 2>/dev/null || true
sleep 1
# Start in background
nohup uvicorn server.main:app --host 0.0.0.0 --port 8000 > /tmp/python-ai.log 2>&1 &
AI_PID=$!
echo "📝 Python AI logs: /tmp/python-ai.log (PID: $AI_PID)"

# 7. Summary
echo ""
echo "============================================"
echo "✅ All services started!"
echo "  PostgreSQL  : localhost:5432 (Docker)"
echo "  Node.js API : http://localhost:3000 (Docker)"
echo "  Python AI   : http://localhost:8000 (local venv, PID: $AI_PID)"
echo "  Mobile .env : API_BASE_URL=http://$IP:3000/api"
echo ""
echo "📱 To run Flutter on phone:"
echo "  cd mobile && flutter run -d 633d8a200720"
echo ""
echo "📋 To stop Python AI:"
echo "  kill $AI_PID"
echo "To stop Docker:"
echo "  docker compose down"
echo "============================================"
