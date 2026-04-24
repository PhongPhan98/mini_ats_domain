#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-candidates}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-mini_ats}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$MODE" in
  candidates) SQL_FILE="$SCRIPT_DIR/reset-candidates.sql" ;;
  jobs) SQL_FILE="$SCRIPT_DIR/reset-jobs.sql" ;;
  all) SQL_FILE="$SCRIPT_DIR/reset-all.sql" ;;
  *)
    echo "Usage: $0 [candidates|jobs|all]"
    exit 1
    ;;
esac

echo "Reset mode: $MODE"
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SQL_FILE"
echo "Done."
