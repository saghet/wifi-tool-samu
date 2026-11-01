#!/usr/bin/env bash
# Script para iniciar la consola interactiva CLI/TUI de HackingTool
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
else
    PYTHON_BIN="python3"
fi

export PYTHONPATH="$SCRIPT_DIR/src:$PYTHONPATH"
exec "$PYTHON_BIN" -m hackingtool.cli "$@"
