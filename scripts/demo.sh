#!/usr/bin/env bash
# Starts the backend against the demo database and vault (never the real ones).
# Usage (from the repo root): ./scripts/demo.sh [--reset] [PORT]
set -u
cd "$(dirname "$0")/../backend"

RESET=""
PORT=8000
for arg in "$@"; do
  if [ "$arg" = "--reset" ]; then RESET="--reset"; else PORT="$arg"; fi
done

source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
export DATABASE_URL="sqlite:///./${DEMO_DATABASE:-demo.db}"
export OBSIDIAN_VAULT_PATH="${TEMP:-/tmp}/kairos-demo-vault"
export TELEGRAM_BOT_TOKEN="" TELEGRAM_ALLOWED_USER_ID="" MAX_ACTIVE_PROJECTS=3
mkdir -p "$OBSIDIAN_VAULT_PATH"

alembic upgrade head
# Without --reset, an already-seeded database is refused on purpose and kept as is
python scripts/seed_demo.py $RESET
exec uvicorn app.main:app --reload --port "$PORT"
