#!/usr/bin/env bash
# Start the OpenCode leg backend exactly as it runs live.
#
# Why this script exists (audit SH-1): the app reads .env from the CODE
# location now, but the server still has to be started with the right
# environment — PYTHONPATH pointing at app/backend and the sqlite DATABASE_URL
# override (the .env ships a postgresql+asyncpg URL with no driver/server
# behind it). Starting uvicorn from a random directory used to silently
# lose the NVIDIA key; this script pins everything in one place.
#
# Usage:
#   ./start-backend.sh            # port 8002, smoke DB, flow automation on
#   PORT=8002 DATABASE_URL=sqlite+aiosqlite:///./micro_drama.db ./start-backend.sh
#
# Env overrides:
#   PORT (default 8002), HOST (default 127.0.0.1),
#   DATABASE_URL (default sqlite+aiosqlite:///./micro_drama_smoke.db),
#   FLOW_AUTOMATION_ENABLED (default 1).
set -euo pipefail

# Always run from the leg root (this script's directory), whatever the
# caller's CWD is.
cd "$(dirname "$0")"

export PYTHONPATH="$PWD/app/backend"
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./micro_drama_smoke.db}"
export FLOW_AUTOMATION_ENABLED="${FLOW_AUTOMATION_ENABLED:-1}"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8002}"

echo "opencode backend: http://$HOST:$PORT (DATABASE_URL=$DATABASE_URL)"
exec "$PWD/app/backend/venv/bin/python" -m uvicorn app.main:app \
    --host "$HOST" --port "$PORT"
