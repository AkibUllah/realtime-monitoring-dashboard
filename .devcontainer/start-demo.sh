#!/usr/bin/env bash
# Codespaces demo: the collector API on :8000 and the Vite dev server on :5173 (which proxies
# /api and /ws to the API), both in the background so the forwarded ports work right away.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p backend/data
(cd backend && nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/api.log 2>&1 &)
(cd frontend && nohup npm run dev -- --host 0.0.0.0 > /tmp/vite.log 2>&1 &)
echo "Dashboard on port 5173, API docs on port 8000."
