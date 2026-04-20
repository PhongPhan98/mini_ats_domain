#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/frontend"

START_PORT="${FRONTEND_PORT:-3000}"
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"

port_in_use() {
  lsof -iTCP:"$1" -sTCP:LISTEN -t >/dev/null 2>&1
}

if [[ ! -d "node_modules" ]]; then
  echo "[mini_ats] node_modules missing. Installing..."
  npm install
fi

if [[ ! -f ".env.local" ]]; then
  cp .env.local.example .env.local
  echo "[mini_ats] Created frontend/.env.local from example"
fi

PORT_TO_USE="$START_PORT"
while port_in_use "$PORT_TO_USE"; do
  PORT_TO_USE=$((PORT_TO_USE + 1))
done

if [[ "$PORT_TO_USE" != "$START_PORT" ]]; then
  echo "[mini_ats] Frontend port $START_PORT busy -> using $PORT_TO_USE"
fi

echo "[mini_ats] Starting frontend on http://localhost:$PORT_TO_USE"
NEXT_PUBLIC_API_BASE_URL="$API_BASE_URL" PORT="$PORT_TO_USE" exec npm run dev
