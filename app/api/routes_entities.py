"""Gestión de los grupos de identidad."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.anonymize.apply import anonymize_text, build_highlights
from app.models.schemas import (
    AssignClusterRequest,
    ClusterAbsorbRequest,
    ClusterAddDetectionsRequest,
    ClusterCreateRequest,
    ClusterMergeRequest,
    ClusterRemoveSurfaceRequest,
    ClusterSplitRequest,
    ClusterUpdateRequest,
    ConfirmResponse,
)
from app.models.store import store
from app.services.clusters import (
    absorb_cluster_into,
    add_detections_to_cluster,
    confirm_cluster,
    create_cluster_from_detections,
    merge_clusters,
    remove_surface_from_cluster,
    split_cluster,
)

router = APIRouter(prefix="/api", tags=["grupos"])


def _obtener_estado(session_id: str):
    estado = store.get(session_id)
    if not estado:
        raise HTTPException(404, "La sesión expiró. Vuelva a cargar el documento.")
    return estado


@router.get("/grupos")
async def listar_grupos(session_id: str):
    estado = _obtener_estado(session_id)
    return {"grupos": estado.clusters, "detecciones": estado.detections}


@router.post("/grupos/crear")
async def crear_grupo(session_id: str, cuerpo: ClusterCreateRequest):
    estado = _obtener_estado(session_id)
    grupo = create_cluster_from_detections(estado, cuerpo.detection_ids, cuerpo.cat)
    if not grupo:
        raise HTTPException(400, "No se pudo crear el grupo con esas detecciones.")
    store.save(estado)
    return {"grupo": grupo, "grupos": estado.clusters, "detecciones": estado.detections}


@router.post("/grupos/combinar")
async def combinar_grupos(session_id: str, cuerpo: ClusterMergeRequest):
    estado = _obtener_estado(session_id)
    combinado = merge_clusters(estado, cuerpo.cluster_ids)
    if not combinado:
        raise HTTPException(400, "Debe indicar al menos dos grupos para combinar.")
    store.save(estado)
    return {"grupo": combinado, "grupos": estado.clusters}


@router.post("/grupos/asignar")
async def asignar_a_grupo(cuerpo: AssignClusterRequest):
    """Mueve una detección a un grupo existente o crea uno nuevo para ella."""
    estado = _obtener_estado(cuerpo.session_id)

    if cuerpo.cluster_id == "__nuevo__":
        grupo = create_cluster_from_detections(estado, [cuerpo.detection_id])
    else:
        grupo = add_detections_to_cluster(
            estado, cuerpo.cluster_id, [cuerpo.detection_id]
        )

    if not grupo:
        raise HTTPException(400, "No fue posible asignar la detección a ese grupo.")

    store.save(estado)
    return {"grupo": grupo, "grupos": estado.clusters, "detecciones": estado.detections}


@router.post("/grupos/{cluster_id}/confirmar", response_model=ConfirmResponse)
async def confirmar_grupo(cluster_id: str, session_id: str):
    estado = _obtener_estado(session_id)
    grupo = confirm_cluster(estado, cluster_id)
    if not grupo:
        raise HTTPException(404, "No se encontró el grupo indicado.")
    store.save(estado)
    return ConfirmResponse(cluster=grupo, detections=estado.detections)


@router.post("/grupos/{cluster_id}/separar")
async def separar_grupo(cluster_id: str, session_id: str, cuerpo: ClusterSplitRequest):
    estado = _obtener_estado(session_id)
    nuevos = split_cluster(estado, cluster_id, cuerpo.mention_ids)
    store.save(estado)
    return {"grupos": estado.clusters, "nuevos": nuevos}


@router.post("/grupos/{cluster_id}/quitar-variante")
async def quitar_variante(
    cluster_id: str, session_id: str, cuerpo: ClusterRemoveSurfaceRequest
):
    estado = _obtener_estado(session_id)
    if not remove_surface_from_cluster(estado, cluster_id, cuerpo.surface):
        raise HTTPException(400, "No se pudo quitar esa variante del grupo.")
    store.save(estado)
    return {"grupos": estado.clusters, "detecciones": estado.detections}


@router.post("/grupos/{cluster_id}/absorber")
async def absorber_grupo(
    cluster_id: str, session_id: str, cuerpo: ClusterAbsorbRequest
):
    estado = _obtener_estado(session_id)
    grupo = absorb_cluster_into(estado, cluster_id, cuerpo.source_cluster_id)
    if not grupo:
        raise HTTPException(400, "No fue posible unir los grupos indicados.")
    store.save(estado)
    return {"grupo": grupo, "grupos": estado.clusters, "detecciones": estado.detections}


@router.post("/grupos/{cluster_id}/agregar")
async def agregar_a_grupo(
    cluster_id: str, session_id: str, cuerpo: ClusterAddDetectionsRequest
):
    estado = _obtener_estado(session_id)
    grupo = add_detections_to_cluster(estado, cluster_id, cuerpo.detection_ids)
    if not grupo:
        raise HTTPException(404, "No se encontró el grupo o la detección indicada.")
    store.save(estado)
    return {"grupo": grupo, "grupos": estado.clusters, "detecciones": estado.detections}


@router.patch("/grupos/{cluster_id}")
async def actualizar_grupo(
    cluster_id: str, session_id: str, cuerpo: ClusterUpdateRequest
):
    estado = _obtener_estado(session_id)
    grupo = next((c for c in estado.clusters if c.cluster_id == cluster_id), None)
    if not grupo:
        raise HTTPException(404, "No se encontró el grupo indicado.")

    if cuerpo.placeholder:
        grupo.placeholder = cuerpo.placeholder
        if grupo.status == "confirmado":
            for deteccion in estado.detections:
                if deteccion.cluster_id == cluster_id:
                    deteccion.placeholder = cuerpo.placeholder
    if cuerpo.canonical_label:
        grupo.canonical_label = cuerpo.canonical_label

    store.save(estado)
    return {"grupo": grupo}


@router.get("/vista-previa")
async def vista_previa(session_id: str, modo: str = "original"):
    """Devuelve el texto original o el anonimizado, con los rangos resaltados."""
    estado = _obtener_estado(session_id)
    texto = (
        anonymize_text(estado.doc_text, estado.detections)
        if modo == "anonimizado"
        else estado.doc_text
    )
    return {
        "texto": texto,
        "resaltados": build_highlights(estado.detections),
        "modo": modo,
    }
