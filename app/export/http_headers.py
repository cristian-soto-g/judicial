"""Cabeceras HTTP para las descargas.

Basado en el módulo homónimo del Anonimizador Judicial de IALAB — Facultad de
Derecho, UBA (Apache 2.0), con adecuación del lenguaje.
"""
from __future__ import annotations

from urllib.parse import quote


def content_disposition_attachment(nombre_archivo: str) -> str:
    """Cabecera de descarga compatible con nombres en ASCII y en UTF-8."""
    seguro = nombre_archivo.replace('"', "'").replace("\r", "").replace("\n", "")
    ascii_puro = seguro.encode("ascii", "ignore").decode().strip() or "documento"
    codificado = quote(seguro, safe="")
    return f'attachment; filename="{ascii_puro}"; filename*=UTF-8\'\'{codificado}'
