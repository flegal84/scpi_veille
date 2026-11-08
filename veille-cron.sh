#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi
mkdir -p logs
echo "=== $(date -Is) : début veille SCPI ===" >> logs/veille-cron.log
./.venv/bin/python scpi.py "$@" >> logs/veille-cron.log 2>&1
echo "=== $(date -Is) : fin veille SCPI ===" >> logs/veille-cron.log