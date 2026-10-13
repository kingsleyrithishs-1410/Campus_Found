#!/usr/bin/env bash
# campusfound - one-click start for macOS / Linux. Needs Python 3.10+.
set -e
cd "$(dirname "$0")"

PY=python3
command -v $PY >/dev/null 2>&1 || PY=python
if ! command -v $PY >/dev/null 2>&1; then
  echo "Python 3.10+ is required: https://www.python.org/downloads/"
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "Setting up for the first time. This takes a minute..."
  $PY -m venv .venv
fi

.venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements.txt
exec .venv/bin/python run.py "$@"
