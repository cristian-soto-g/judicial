"""Comprueba que el entorno tenga todo lo necesario para ejecutar la aplicación.

Distingue entre dependencias imprescindibles y opcionales, de modo que la
ausencia de la capa de lenguaje natural no se confunda con una instalación
defectuosa.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

IMPRESCINDIBLES = [
    ("fastapi", "servidor web local"),
    ("uvicorn", "servidor web local"),
    ("pydantic", "validación de datos"),
    ("docx", "lectura y escritura de documentos Word"),
    ("pdfplumber", "lectura de PDF con texto seleccionable"),
    ("reportlab", "exportación a PDF"),
    ("rapidfuzz", "comparación de nombres"),
    ("networkx", "agrupación de identidades"),
    ("cryptography", "cifrado del mapa de reversión"),
]

OPCIONALES = [("spacy", "capa de lenguaje natural (mejora la detección de nombres)")]


def revisar(modulos: list[tuple[str, str]]) -> list[str]:
    faltantes: list[str] = []
    for modulo, proposito in modulos:
        try:
            importlib.import_module(modulo)
            print(f"  [ok]     {modulo:16s} {proposito}")
        except ImportError:
            print(f"  [falta]  {modulo:16s} {proposito}")
            faltantes.append(modulo)
    return faltantes


def main() -> int:
    print("Dependencias imprescindibles:")
    faltantes = revisar(IMPRESCINDIBLES)

    print("\nDependencias opcionales:")
    revisar(OPCIONALES)

    print("\nDiccionarios:")
    from app.detection.dictionaries import get_apellidos, get_formulas, get_nombres

    print(f"  nombres:   {len(get_nombres())} entradas")
    print(f"  apellidos: {len(get_apellidos())} entradas")
    print(f"  fórmulas:  {len(get_formulas())} entradas")

    if faltantes:
        print(
            "\nFaltan dependencias imprescindibles. Instálelas con:\n"
            "  pip install -r requirements.txt"
        )
        return 1

    print("\nEl entorno está listo. Ejecute: python scripts/run_dev.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
