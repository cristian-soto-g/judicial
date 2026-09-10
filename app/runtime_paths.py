"""Rutas de ejecución: desarrollo frente a ejecutable empaquetado.

Basado en el módulo homónimo del Anonimizador Judicial de IALAB — Facultad de
Derecho, UBA (Apache 2.0). Modificado: el nombre del modelo de lenguaje pasó a
ser una constante configurable y la carpeta de datos persistentes se resuelve
en el directorio del usuario.
"""
from __future__ import annotations

import sys
from pathlib import Path

SPACY_MODEL_NAME = "es_core_news_md"


def is_frozen() -> bool:
    """Indica si la aplicación corre como ejecutable empaquetado."""
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """Carpeta de la aplicación (datos persistentes del usuario)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def bundle_dir() -> Path:
    """Carpeta de recursos embebidos (frontend, diccionarios)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", app_dir()))
    return Path(__file__).resolve().parent.parent


def spacy_model_dir() -> Path | None:
    """Ruta al modelo de lenguaje empaquetado, si existe."""
    for base in (app_dir(), bundle_dir()):
        candidate = base / "models" / SPACY_MODEL_NAME
        if (candidate / "meta.json").exists() and (candidate / "config.cfg").exists():
            return candidate
    return None
