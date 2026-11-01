#!/usr/bin/env python3
"""Launcher for the HackingTool Web Interface."""
import argparse
import os
import sys
import webbrowser
from pathlib import Path

# Ensure src/ is on sys.path
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def check_and_bootstrap():
    """Ensure required packages are available, or re-exec inside .venv if present."""
    venv_python = BASE_DIR / ".venv" / "bin" / "python"
    if venv_python.exists() and sys.executable != str(venv_python):
        # If running from system python and .venv is ready, re-exec inside .venv
        try:
            import fastapi  # type: ignore
            import uvicorn  # type: ignore
        except ImportError:
            print(f"[*] Re-executing launcher using project virtualenv: {venv_python}")
            os.execv(str(venv_python), [str(venv_python)] + sys.argv)


def main():
    parser = argparse.ArgumentParser(
        description="Lanzador de la interfaz web interactiva de HackingTool"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host IP to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on code change")
    args = parser.parse_args()

    check_and_bootstrap()

    try:
        import uvicorn
    except ImportError:
        print("[!] Error: 'uvicorn' o 'fastapi' no están instalados.")
        print("[*] Ejecuta: .venv/bin/pip install -r requirements.txt o pip install fastapi uvicorn websockets")
        sys.exit(1)

    url = f"http://{args.host}:{args.port}"
    print("=" * 65)
    print("  🛡  HACKINGTOOL WEB SUITE & CONTROL CENTER")
    print(f"  🌐  Servidor activo en: {url}")
    print("  ⚡  Terminal en tiempo real y asistente IA habilitados")
    print("=" * 65)

    if not args.no_browser and args.host in ("127.0.0.1", "localhost", "0.0.0.0"):
        import threading
        import time

        def open_tab():
            time.sleep(1.2)
            webbrowser.open_new_tab(url)

        threading.Thread(target=open_tab, daemon=True).start()

    from hackingtool.web.server import app

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
