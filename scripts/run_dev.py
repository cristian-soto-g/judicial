"""Levanta la aplicación en modo de desarrollo.

Uso:
    python scripts/run_dev.py            abre el navegador automáticamente
    python scripts/run_dev.py --sin-abrir  no abre el navegador
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import run_server  # noqa: E402

if __name__ == "__main__":
    run_server(abrir_navegador="--sin-abrir" not in sys.argv)
