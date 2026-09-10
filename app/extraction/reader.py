"""Punto único de entrada para la lectura de documentos.

Módulo propio de esta obra derivada. Centraliza la decisión de formato para
que la capa de API no tenga que conocer los detalles de cada extractor, e
incorpora el texto plano, que la aplicación original no admitía.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.extraction.docx import extract_docx
from app.extraction.pdf import extract_pdf_con_aviso
from app.extraction.txt import extract_txt

EXTENSIONES_ADMITIDAS = (".txt", ".docx", ".pdf")


@dataclass(frozen=True)
class ResultadoExtraccion:
    """Texto extraído junto con el aviso que corresponda mostrar al usuario."""

    texto: str
    formato: str
    aviso: str = ""


def extraer_documento(nombre_archivo: str, data: bytes) -> ResultadoExtraccion:
    """Extrae el texto del documento según su extensión."""
    nombre = (nombre_archivo or "").lower().strip()

    if nombre.endswith(".txt"):
        return ResultadoExtraccion(texto=extract_txt(data), formato="txt")

    if nombre.endswith(".docx"):
        return ResultadoExtraccion(texto=extract_docx(data), formato="docx")

    if nombre.endswith(".pdf"):
        texto, aviso = extract_pdf_con_aviso(data)
        return ResultadoExtraccion(texto=texto, formato="pdf", aviso=aviso)

    if nombre.endswith(".doc"):
        raise ValueError(
            "El formato .doc (Word 97-2003) no es compatible. Abra el archivo "
            "en Word y guárdelo como .docx antes de cargarlo."
        )

    raise ValueError(
        "Formato no admitido. Esta aplicación procesa archivos .txt, .docx y "
        "PDF con texto seleccionable."
    )
