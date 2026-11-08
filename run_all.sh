#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${FLOWAWARE_PYTHON:-.venv/bin/python}"
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$PWD/.cache/matplotlib}"
"$PYTHON" -m pytest -q
"$PYTHON" -m flowaware.experiments "$@"
