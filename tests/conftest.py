"""Configuración común de las pruebas."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.schemas import SessionState  # noqa: E402
from app.services.analyze import run_full_analysis  # noqa: E402


@pytest.fixture
def analizar():
    """Analiza un texto y devuelve el estado junto con el resultado."""

    def _analizar(texto: str, **opciones):
        estado = SessionState(
            session_id="prueba",
            doc_text=texto,
            doc_name="prueba",
            **opciones,
        )
        return estado, run_full_analysis(estado)

    return _analizar


@pytest.fixture
def detectar(analizar):
    """Devuelve un diccionario categoría -> lista de textos detectados."""

    def _detectar(texto: str, **opciones):
        _, resultado = analizar(texto, **opciones)
        por_categoria: dict[str, list[str]] = {}
        for deteccion in resultado.detections:
            por_categoria.setdefault(deteccion.cat, []).append(deteccion.original)
        return por_categoria

    return _detectar
