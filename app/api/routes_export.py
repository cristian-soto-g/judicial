"""Exportación del documento anonimizado."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.anonymize.apply import anonymize_text
from app.export.csv_export import build_csv_bytes
from app.export.docx_export import build_docx_bytes
from app.export.export_utils import (
    formato_desde_opciones,
    resolver_texto_exportacion,
    texto_a_parrafos,
)
from app.export.http_headers import content_disposition_attachment
from app.export.pdf_export import build_pdf_bytes
from app.export.txt_export import build_txt_bytes
from app.models.schemas import (
    AnonymizedPreviewResponse,
    ExportDocumentRequest,
    ExportRequest,
)
from app.models.store import store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/exportar", tags=["exportación"])

TIPO_DOCX = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def _obtener_estado_para_exportar(session_id: str):
    """Comprueba que el documento ya se haya analizado.

    Lo que se exige es el análisis, no que haya detecciones. Un documento sin
    datos personales es un resultado legítimo y debe poder exportarse: negarlo
    obligaría a inventar una detección para destrabar la exportación.
    """
    estado = store.get(session_id)
    if not estado:
        raise HTTPException(404, "La sesión expiró. Vuelva a cargar el documento.")
    if not estado.analizado:
        raise HTTPException(
            400, "Analice el documento antes de exportarlo."
        )
    return estado


@router.post("/vista-previa", response_model=AnonymizedPreviewResponse)
async def previsualizar(peticion: ExportRequest):
    """Texto anonimizado tal como quedará al exportar.

    Se aplican las detecciones de la sesión sin filtrarlas de nuevo: lo que
    muestra la tabla de revisión es exactamente lo que se reemplaza.
    """
    estado = _obtener_estado_para_exportar(peticion.session_id)
    return AnonymizedPreviewResponse(
        session_id=estado.session_id,
        doc_name=estado.doc_name,
        text=anonymize_text(estado.doc_text, estado.detections),
    )


@router.post("/docx")
async def exportar_docx(peticion: ExportDocumentRequest):
    estado = _obtener_estado_para_exportar(peticion.session_id)
    try:
        texto = resolver_texto_exportacion(estado, peticion)
        datos = build_docx_bytes(
            texto_a_parrafos(texto), formato_desde_opciones(peticion.format)
        )
    except Exception as error:
        logger.exception("Error al generar el documento Word")
        raise HTTPException(500, f"No se pudo generar el Word: {error}") from error

    return Response(
        content=datos,
        media_type=TIPO_DOCX,
        headers={
            "Content-Disposition": content_disposition_attachment(
                f"{estado.doc_name}_anonimizado.docx"
            )
        },
    )


@router.post("/pdf")
async def exportar_pdf(peticion: ExportDocumentRequest):
    estado = _obtener_estado_para_exportar(peticion.session_id)
    try:
        texto = resolver_texto_exportacion(estado, peticion)
        datos = build_pdf_bytes(
            texto_a_parrafos(texto), formato_desde_opciones(peticion.format)
        )
    except Exception as error:
        logger.exception("Error al generar el PDF")
        raise HTTPException(500, f"No se pudo generar el PDF: {error}") from error

    return Response(
        content=datos,
        media_type="application/pdf",
        headers={
            "Content-Disposition": content_disposition_attachment(
                f"{estado.doc_name}_anonimizado.pdf"
            )
        },
    )


@router.post("/txt")
async def exportar_txt(peticion: ExportDocumentRequest):
    estado = _obtener_estado_para_exportar(peticion.session_id)
    texto = resolver_texto_exportacion(estado, peticion)
    return Response(
        content=build_txt_bytes(texto),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": content_disposition_attachment(
                f"{estado.doc_name}_anonimizado.txt"
            )
        },
    )


@router.post("/csv")
async def exportar_csv(peticion: ExportRequest):
    """Tabla de equivalencias. Contiene los datos originales sin cifrar."""
    estado = _obtener_estado_para_exportar(peticion.session_id)
    return Response(
        content=build_csv_bytes(estado.detections),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": content_disposition_attachment(
                f"{estado.doc_name}_equivalencias.csv"
            )
        },
    )
