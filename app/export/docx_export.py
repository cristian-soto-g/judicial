"""Exportación a documento Word.

Basado en el exportador del Anonimizador Judicial de IALAB — Facultad de
Derecho, UBA (Apache 2.0), con adecuación del formato y del lenguaje.
"""
from __future__ import annotations

import io

from docx import Document

from app.export.docx_format import (
    FORMATO_POR_DEFECTO,
    FormatoDocumento,
    agregar_parrafo,
    aplicar_formato,
)


def build_docx_bytes(
    parrafos: list[str], formato: FormatoDocumento = FORMATO_POR_DEFECTO
) -> bytes:
    documento = Document()
    aplicar_formato(documento, formato)

    for texto in parrafos or ["(documento sin contenido)"]:
        agregar_parrafo(documento, texto, formato)

    buffer = io.BytesIO()
    documento.save(buffer)
    buffer.seek(0)
    return buffer.read()
