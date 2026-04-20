#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
export MINI_ATS_AUTO_KILL="${MINI_ATS_AUTO_KILL:-1}"

cleanup() {
  echo "[mini_ats] Stopping all services..."
  [[ -n "${BACKEND_PID:-}" ]] && kill "$BACKEND_PID" >/dev/null 2>&1 || true
  [[ -n "${FRONTEND_PID:-}" ]] && kill "$FRONTEND_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

if ! lsof -iTCP:5432 -sTCP:LISTEN -t >/dev/null 2>&1; then
  if command -v docker >/dev/null 2>&1; then
    echo "[mini_ats] PostgreSQL not listening on 5432 -> trying docker compose up -d db"
    docker compose up -d db || echo "[mini_ats] WARNING: couldn't start db via docker. Start DB manually."
  else
    echo "[mini_ats] WARNING: PostgreSQL not running on :5432 and docker not found."
  fi
fi

BACKEND_PORT="$BACKEND_PORT" ./scripts/run_backend.sh &
BACKEND_PID=$!

sleep 3
if ! kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
  echo "[mini_ats] Backend failed to start. Check logs above."
  exit 1
fi

API_BASE_URL="http://localhost:$BACKEND_PORT" FRONTEND_PORT="$FRONTEND_PORT" ./scripts/run_frontend.sh &
FRONTEND_PID=$!

sleep 3
if ! kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
  echo "[mini_ats] Frontend failed to start. Check logs above."
  exit 1
fi

echo "[mini_ats] Backend PID: $BACKEND_PID"
echo "[mini_ats] Frontend PID: $FRONTEND_PID"
echo "[mini_ats] Backend URL: http://localhost:$BACKEND_PORT"
echo "[mini_ats] Frontend URL: http://localhost:$FRONTEND_PORT (auto-shifts if busy)"
echo "[mini_ats] Press Ctrl+C to stop all"

wait
