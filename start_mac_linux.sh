#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.11+ is required. Install Python, then run this script again."
  exit 1
fi

python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' || {
  echo "Please install Python 3.11 or newer, then run this script again."
  exit 1
}

if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
fi

.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' EXIT INT TERM

for attempt in $(seq 1 30); do
  if .venv/bin/python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=1)' >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if command -v open >/dev/null 2>&1; then
  open "http://127.0.0.1:8000"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://127.0.0.1:8000" >/dev/null 2>&1 || true
else
  echo "Open http://127.0.0.1:8000 in your browser."
fi

echo "Fieldnote FX is running. Keep this terminal open; press Ctrl+C to stop it."
wait "$server_pid"
