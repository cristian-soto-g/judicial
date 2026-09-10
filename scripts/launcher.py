"""Punto de entrada del paquete ejecutable.

PyInstaller toma este archivo como raíz del programa. Se mantiene deliberadamente
mínimo: todo lo demás vive en el paquete `app`, de modo que el ejecutable y la
ejecución desde el código fuente compartan exactamente el mismo comportamiento.
"""
from __future__ import annotations

import sys
from pathlib import Path

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Importaciones que el análisis estático de PyInstaller debe alcanzar. Varias
# de ellas ocurren dentro de funciones en el código de la aplicación, y sin
# esta referencia explícita podrían quedar fuera del paquete.
from app import main as _main  # noqa: E402
from app.detection import filters as _filters  # noqa: E402,F401
from app.detection import nlp_status as _nlp_status  # noqa: E402,F401
from app.detection import validadores as _validadores  # noqa: E402,F401
from app.export import csv_export as _csv  # noqa: E402,F401
from app.export import docx_export as _docx  # noqa: E402,F401
from app.export import pdf_export as _pdf  # noqa: E402,F401
from app.export import txt_export as _txt  # noqa: E402,F401
from app.extraction import reader as _reader  # noqa: E402,F401
from app.reversal import crypto as _crypto  # noqa: E402,F401
from app.reversal import mapping as _mapping  # noqa: E402,F401
from app.services import analysis_cancel as _cancel  # noqa: E402,F401
from app.services import clusters as _clusters  # noqa: E402,F401
from app.services import detections as _detections  # noqa: E402,F401


def main() -> int:
    return _main.run_server(abrir_navegador="--sin-abrir" not in sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
