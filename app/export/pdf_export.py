"""Exportación a PDF.

Basado en el exportador del Anonimizador Judicial de IALAB — Facultad de
Derecho, UBA (Apache 2.0), con adecuación del formato y del lenguaje.
"""
from __future__ import annotations

import io
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate

from app.export.docx_format import FORMATO_POR_DEFECTO, FormatoDocumento

_ALINEACIONES = {
    "left": TA_LEFT,
    "justify": TA_JUSTIFY,
    "center": TA_CENTER,
    "right": TA_RIGHT,
}

_TIPOGRAFIAS = {
    "Times New Roman": "Times-Roman",
    "Arial": "Helvetica",
    "Calibri": "Helvetica",
}


def _estilo(formato: FormatoDocumento) -> ParagraphStyle:
    return ParagraphStyle(
        name="CuerpoAnonimizado",
        fontName=_TIPOGRAFIAS.get(formato.font_name, "Times-Roman"),
        fontSize=formato.font_size_pt,
        leading=formato.font_size_pt * formato.line_spacing,
        alignment=_ALINEACIONES.get(formato.alignment, TA_JUSTIFY),
        spaceAfter=formato.space_after_pt,
    )


def build_pdf_bytes(
    parrafos: list[str], formato: FormatoDocumento | None = None
) -> bytes:
    formato = formato or FORMATO_POR_DEFECTO
    estilo = _estilo(formato)
    buffer = io.BytesIO()

    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=formato.margin_cm * cm,
        rightMargin=formato.margin_cm * cm,
        topMargin=formato.margin_top_bottom_cm * cm,
        bottomMargin=formato.margin_top_bottom_cm * cm,
    )

    contenido: list[Paragraph] = []
    for crudo in parrafos:
        texto = crudo.strip()
        if not texto:
            continue
        contenido.append(Paragraph(escape(texto).replace("\n", "<br/>"), estilo))

    if not contenido:
        contenido.append(Paragraph(escape("(documento sin contenido)"), estilo))

    documento.build(contenido)
    buffer.seek(0)
    return buffer.read()
