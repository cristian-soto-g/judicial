"""Utilidades compartidas por los exportadores.

Basado en las utilidades del Anonimizador Judicial de IALAB — Facultad de
Derecho, UBA (Apache 2.0), con adecuación del lenguaje.
"""
from __future__ import annotations

from app.anonymize.apply import anonymize_text
from app.export.docx_format import FORMATO_POR_DEFECTO, FormatoDocumento
from app.models.schemas import ExportDocumentRequest, ExportFormatOptions, SessionState
from app.services.analyze import prune_detections


def formato_desde_opciones(opciones: ExportFormatOptions | None) -> FormatoDocumento:
    if not opciones:
        return FORMATO_POR_DEFECTO
    return FormatoDocumento(
        font_name=opciones.font_name,
        font_size_pt=opciones.font_size_pt,
        line_spacing=opciones.line_spacing,
        margin_cm=opciones.margin_cm,
        margin_top_bottom_cm=opciones.margin_top_bottom_cm,
        alignment=opciones.alignment,
    )


def resolver_texto_exportacion(
    state: SessionState, request: ExportDocumentRequest
) -> str:
    """Devuelve el texto a exportar: el editado por el usuario o el anonimizado."""
    if request.text is not None:
        return request.text
    detecciones = prune_detections(state.detections, state.doc_text)
    return anonymize_text(state.doc_text, detecciones)


def texto_a_parrafos(texto: str) -> list[str]:
    """Divide el texto en párrafos para la exportación."""
    from app.extraction.pdf_cleanup import merge_lines_to_paragraphs

    normalizado = merge_lines_to_paragraphs(texto.replace("\r\n", "\n"))
    parrafos = [p.strip() for p in normalizado.split("\n\n") if p.strip()]
    if parrafos:
        return parrafos
    lineas = [linea.strip() for linea in texto.split("\n") if linea.strip()]
    return lineas or [texto.strip() or "(documento sin contenido)"]
