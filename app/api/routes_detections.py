"""Alta, modificación y baja de detecciones."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    DetectionPatchRequest,
    ManualDetectionRequest,
    SearchAndAnonymizeRequest,
)
from app.models.store import store
from app.services.detections import (
    add_bulk_detection,
    add_manual_detection,
    remove_detection,
    update_detection,
)

router = APIRouter(prefix="/api/detecciones", tags=["detecciones"])


def _obtener_estado(session_id: str):
    estado = store.get(session_id)
    if not estado:
        raise HTTPException(404, "La sesión expiró. Vuelva a cargar el documento.")
    return estado


@router.post("/manual")
async def agregar_manual(peticion: ManualDetectionRequest):
    """Agrega un dato marcado a mano sobre la vista previa."""
    estado = _obtener_estado(peticion.session_id)
    if not estado.doc_text:
        raise HTTPException(400, "No hay ningún documento cargado.")
    try:
        deteccion = add_manual_detection(
            estado, peticion.cat, peticion.start, peticion.end, peticion.original
        )
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    store.save(estado)
    return {"deteccion": deteccion, "detecciones": estado.detections}


@router.post("/buscar-y-anonimizar")
async def buscar_y_anonimizar(peticion: SearchAndAnonymizeRequest):
    """Anonimiza todas las coincidencias que encontró el buscador."""
    estado = _obtener_estado(peticion.session_id)
    if not estado.doc_text:
        raise HTTPException(400, "No hay ningún documento cargado.")
    try:
        deteccion = add_bulk_detection(
            estado,
            peticion.cat,
            peticion.original,
            peticion.positions,
            peticion.placeholder,
        )
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    store.save(estado)
    return {"deteccion": deteccion, "detecciones": estado.detections}


@router.patch("/{detection_id}")
async def modificar_deteccion(detection_id: int, peticion: DetectionPatchRequest):
    estado = _obtener_estado(peticion.session_id)
    try:
        deteccion = update_detection(
            estado,
            detection_id,
            cat=peticion.cat,
            placeholder=peticion.placeholder,
            enabled=peticion.enabled,
        )
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    store.save(estado)
    return {
        "deteccion": deteccion,
        "detecciones": estado.detections,
        "grupos": estado.clusters,
    }


@router.delete("/{detection_id}")
async def eliminar_deteccion(detection_id: int, session_id: str):
    estado = _obtener_estado(session_id)
    try:
        remove_detection(estado, detection_id)
    except ValueError as error:
        raise HTTPException(404, str(error)) from error
    store.save(estado)
    return {"detecciones": estado.detections, "grupos": estado.clusters}
