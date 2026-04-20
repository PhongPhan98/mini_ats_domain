#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BACKEND_PORT="${BACKEND_PORT:-8000}"
AUTO_KILL="${MINI_ATS_AUTO_KILL:-0}"

port_in_use() {
  lsof -iTCP:"$1" -sTCP:LISTEN -t >/dev/null 2>&1
}

if [[ ! -d ".venv" ]]; then
  echo "[mini_ats] .venv not found. Create it first:"
  echo "python3 -m venv .venv && source .venv/bin/activate && pip install -r backend/requirements.txt"
  exit 1
fi

source .venv/bin/activate

if [[ ! -f "backend/.env" ]]; then
  cp backend/.env.example backend/.env
  echo "[mini_ats] Created backend/.env from example. Please edit OPENAI_API_KEY + DATABASE_URL"
fi

if port_in_use "$BACKEND_PORT"; then
  if [[ "$AUTO_KILL" == "1" ]]; then
    echo "[mini_ats] Port $BACKEND_PORT is busy -> killing existing listener"
    lsof -iTCP:"$BACKEND_PORT" -sTCP:LISTEN -t | xargs -r kill -9
    sleep 1
  else
    echo "[mini_ats] Backend port $BACKEND_PORT is already in use."
    echo "Set MINI_ATS_AUTO_KILL=1 to auto-kill or run with BACKEND_PORT=<port>."
    exit 1
  fi
fi

echo "[mini_ats] Starting backend on http://localhost:$BACKEND_PORT"
exec uvicorn app.main:app --reload --port "$BACKEND_PORT" --app-dir backend
