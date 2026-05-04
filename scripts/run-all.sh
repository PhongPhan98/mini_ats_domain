#!/usr/bin/env bash
set -euo pipefail
# clear automation event log before startup (best effort)
curl -sS -X POST http://127.0.0.1:8000/api/automation/events/clear >/dev/null 2>&1 || true
for f in scripts/*.sh; do
  [[ "$f" == "scripts/run-all.sh" ]] && continue
  echo "==> running $f"
  bash "$f"
done
