"""Análisis del documento y ciclo de vida de la sesión."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import AnalyzeRequest, AnalyzeResponse, CancelRequest
from app.models.store import store
from app.services.analysis_cancel import AnalysisCancelledError, request_cancel
from app.services.analyze import run_full_analysis

router = APIRouter(prefix="/api", tags=["análisis"])


@router.post("/analizar", response_model=AnalyzeResponse)
async def analizar_documento(peticion: AnalyzeRequest):
    """Ejecuta la detección sobre el documento cargado."""
    estado = store.get(peticion.session_id)
    if not estado:
        raise HTTPException(404, "La sesión expiró. Vuelva a cargar el documento.")
    if not estado.doc_text:
        raise HTTPException(400, "No hay ningún documento cargado.")

    estado.label_mode = peticion.label_mode
    estado.sensibilidad = peticion.sensibilidad
    if peticion.enabled_categories is not None:
        estado.enabled_categories = peticion.enabled_categories

    try:
        resultado = run_full_analysis(estado)
    except AnalysisCancelledError as error:
        raise HTTPException(409, "El análisis fue interrumpido.") from error

    store.save(estado)
    return resultado


@router.post("/analizar/cancelar")
async def cancelar_analisis(peticion: CancelRequest):
    estado = store.get(peticion.session_id)
    if not estado:
        raise HTTPException(404, "La sesión expiró.")
    request_cancel(peticion.session_id)
    return {"cancelado": True, "session_id": peticion.session_id}


@router.get("/sesion/{session_id}")
async def obtener_sesion(session_id: str):
    estado = store.get(session_id)
    if not estado:
        raise HTTPException(404, "La sesión expiró.")
    return {
        "session_id": estado.session_id,
        "doc_name": estado.doc_name,
        "caracteres": len(estado.doc_text),
        "detecciones": len(estado.detections),
        "grupos": len(estado.clusters),
        "aviso": estado.aviso_extraccion,
    }


@router.delete("/sesion/{session_id}")
async def cerrar_sesion(session_id: str):
    """Descarta la sesión y con ella el texto del documento en memoria."""
    store.delete(session_id)
    return {"cerrada": True, "session_id": session_id}
