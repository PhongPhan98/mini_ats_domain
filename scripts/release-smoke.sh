#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-http://127.0.0.1:8000}"

echo "[1/4] health"
curl -fsS "$BASE/health" && echo

echo "[2/4] ai status"
curl -fsS "$BASE/api/system/ai-status" && echo

echo "[3/4] public job endpoint (example slug)"
curl -sS "$BASE/api/public/jobs/frontend-dev" || true

echo "[4/4] done"
echo "Run UI smoke manually for auth/upload/pipeline/jobs/interviews/public-apply/activity."
