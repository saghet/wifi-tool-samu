#!/usr/bin/env bash
# Script inteligente para iniciar o abrir la interfaz web de HackingTool
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

URL="http://127.0.0.1:8000"

# Comprobar si el servidor ya está corriendo en el puerto 8000
if curl -s --max-time 1 "$URL/api/system" >/dev/null 2>&1; then
    echo "[*] HackingTool Web ya está en ejecución. Abriendo en el navegador..."
    xdg-open "$URL" >/dev/null 2>&1 || sensible-browser "$URL" >/dev/null 2>&1 || true
    exit 0
fi

# Detectar intérprete Python adecuado (.venv o sistema)
if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
else
    PYTHON_BIN="python3"
fi

echo "========================================================"
echo "  Iniciando HackingTool Web Interface..."
echo "  URL: $URL"
echo "========================================================"

exec "$PYTHON_BIN" "$SCRIPT_DIR/run_web.py" "$@"
