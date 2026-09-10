"""Operaciones sobre los grupos de identidad.

Basado en el servicio de grupos del Anonimizador Judicial de IALAB — Facultad
de Derecho, UBA (Apache 2.0). Modificado: los estados pasaron a nombrarse en
español y se simplificó la numeración de las etiquetas al confirmar un grupo.
"""
from __future__ import annotations

from app.anonymize.placeholders import make_placeholder
from app.models.schemas import Cluster, Detection, Mention, Position, SessionState


def _superficies(state: SessionState, mention_ids: set[str]) -> list[str]:
    superficies: list[str] = []
    for mencion in state.mentions:
        if mencion.id in mention_ids:
            valor = mencion.surface.strip()
            if valor and valor not in superficies:
                superficies.append(valor)
    return superficies


def _menciones_de_detecciones(
    state: SessionState, detection_ids: list[int]
) -> set[str]:
    ids: set[str] = set()
    for detection_id in detection_ids:
        deteccion = next((d for d in state.detections if d.id == detection_id), None)
        if not deteccion:
            continue
        ids.update(deteccion.mention_ids)
        normalizada = deteccion.original.strip().lower()
        for mencion in state.mentions:
            if mencion.surface.strip().lower() == normalizada:
                ids.add(mencion.id)
                continue
            for posicion in deteccion.positions:
                if mencion.start == posicion.start and mencion.end == posicion.end:
                    ids.add(mencion.id)
    return ids


def _asegurar_menciones(state: SessionState, deteccion: Detection) -> set[str]:
    """Crea menciones para una detección que no las tenga (alta manual)."""
    ids = _menciones_de_detecciones(state, [deteccion.id])
    if ids:
        deteccion.mention_ids = list(ids)
        return ids

    nuevas: set[str] = set()
    posiciones = deteccion.positions or [Position(start=0, end=len(deteccion.original))]
    for indice, posicion in enumerate(posiciones):
        mention_id = f"m_manual_{deteccion.id}_{indice}_{len(state.mentions)}"
        superficie = (posicion.raw or deteccion.original).strip()
        state.mentions.append(
            Mention(
                id=mention_id,
                cat=deteccion.cat,
                surface=superficie,
                start=posicion.start,
                end=posicion.end,
                norm=superficie.lower(),
                source_layer="manual",
            )
        )
        nuevas.add(mention_id)

    deteccion.mention_ids = list(nuevas)
    return nuevas


def _sincronizar(state: SessionState, grupo: Cluster) -> None:
    """Propaga la etiqueta del grupo a todas sus detecciones."""
    superficies = {s.strip().lower() for s in grupo.surfaces}
    etiqueta = grupo.placeholder or grupo.canonical_label
    if not etiqueta:
        return
    for deteccion in state.detections:
        pertenece = deteccion.original.strip().lower() in superficies or any(
            mention_id in grupo.mention_ids for mention_id in deteccion.mention_ids
        )
        if pertenece:
            deteccion.cluster_id = grupo.cluster_id
            if grupo.status == "confirmado":
                deteccion.placeholder = etiqueta
                deteccion.enabled = True


def _reconstruir(state: SessionState, grupo: Cluster) -> None:
    grupo.mention_ids = list(dict.fromkeys(grupo.mention_ids))
    grupo.surfaces = _superficies(state, set(grupo.mention_ids))


def create_cluster_from_detections(
    state: SessionState, detection_ids: list[int], cat: str | None = None
) -> Cluster | None:
    """Crea un grupo nuevo a partir de las detecciones indicadas."""
    ids: set[str] = set()
    for detection_id in detection_ids:
        deteccion = next((d for d in state.detections if d.id == detection_id), None)
        if deteccion:
            ids.update(_asegurar_menciones(state, deteccion))
    if not ids:
        return None

    primera = next(
        (d for d in state.detections if d.id == detection_ids[0]), None
    )
    grupo = Cluster(
        cluster_id=f"manual_{len(state.clusters)}",
        cat=cat or (primera.cat if primera else "PERSONA"),  # type: ignore[arg-type]
        mention_ids=list(ids),
        surfaces=_superficies(state, ids),
        confidence="media",
        status="sugerido",
        reasons=["manual"],
    )
    state.clusters.append(grupo)
    _sincronizar(state, grupo)
    return grupo


def add_detections_to_cluster(
    state: SessionState, cluster_id: str, detection_ids: list[int]
) -> Cluster | None:
    grupo = next((c for c in state.clusters if c.cluster_id == cluster_id), None)
    if not grupo:
        return None

    nuevas: set[str] = set()
    for detection_id in detection_ids:
        deteccion = next((d for d in state.detections if d.id == detection_id), None)
        if deteccion:
            nuevas.update(_asegurar_menciones(state, deteccion))
    if not nuevas:
        return None

    for mention_id in nuevas:
        if mention_id not in grupo.mention_ids:
            grupo.mention_ids.append(mention_id)

    _reconstruir(state, grupo)
    _sincronizar(state, grupo)
    return grupo


def confirm_cluster(state: SessionState, cluster_id: str) -> Cluster | None:
    """Confirma un grupo: todas sus variantes pasan a compartir una etiqueta."""
    grupo = next((c for c in state.clusters if c.cluster_id == cluster_id), None)
    if not grupo:
        return None

    _reconstruir(state, grupo)
    grupo.status = "confirmado"

    if not grupo.placeholder:
        confirmados = sum(
            1
            for c in state.clusters
            if c.cat == grupo.cat and c.status == "confirmado"
        )
        grupo.placeholder = make_placeholder(
            grupo.cat,
            grupo.surfaces[0] if grupo.surfaces else "",
            confirmados,
            state.label_mode,
        )
    grupo.canonical_label = grupo.placeholder
    _sincronizar(state, grupo)
    return grupo


def split_cluster(
    state: SessionState, cluster_id: str, mention_ids: list[str]
) -> list[Cluster]:
    """Separa del grupo las menciones indicadas, que pasan a un grupo propio."""
    grupo = next((c for c in state.clusters if c.cluster_id == cluster_id), None)
    if not grupo:
        return []

    conservadas = [mid for mid in grupo.mention_ids if mid not in mention_ids]
    nuevos: list[Cluster] = []

    if conservadas:
        grupo.mention_ids = conservadas
        _reconstruir(state, grupo)
        grupo.status = "sugerido"
        grupo.placeholder = None
        grupo.canonical_label = None

    if mention_ids:
        nuevo = Cluster(
            cluster_id=f"{cluster_id}_sep_{len(state.clusters)}",
            cat=grupo.cat,
            mention_ids=list(mention_ids),
            surfaces=_superficies(state, set(mention_ids)),
            confidence=grupo.confidence,
            status="sugerido",
            reasons=["separado"],
        )
        state.clusters.append(nuevo)
        nuevos.append(nuevo)

    return nuevos


def remove_surface_from_cluster(
    state: SessionState, cluster_id: str, surface: str
) -> list[Cluster]:
    """Saca una variante del grupo y la deja como grupo aparte.

    Es la corrección natural cuando la agrupación unió por error a dos personas
    que comparten apellido, situación frecuente en causas de familia.
    """
    grupo = next((c for c in state.clusters if c.cluster_id == cluster_id), None)
    if not grupo:
        return []

    objetivo = surface.strip().lower()
    a_mover = [
        m.id
        for m in state.mentions
        if m.id in grupo.mention_ids and m.surface.strip().lower() == objetivo
    ]
    if not a_mover:
        return []

    for deteccion in state.detections:
        if (
            deteccion.cluster_id == cluster_id
            and deteccion.original.strip().lower() == objetivo
        ):
            deteccion.cluster_id = None

    return split_cluster(state, cluster_id, a_mover)


def absorb_cluster_into(
    state: SessionState, target_id: str, source_id: str
) -> Cluster | None:
    """Funde un grupo dentro de otro, conservando la identidad del destino."""
    if target_id == source_id:
        return None

    destino = next((c for c in state.clusters if c.cluster_id == target_id), None)
    origen = next((c for c in state.clusters if c.cluster_id == source_id), None)
    if not destino or not origen:
        return None

    for mention_id in origen.mention_ids:
        if mention_id not in destino.mention_ids:
            destino.mention_ids.append(mention_id)

    for deteccion in state.detections:
        if deteccion.cluster_id == source_id:
            deteccion.cluster_id = target_id

    state.clusters = [c for c in state.clusters if c.cluster_id != source_id]
    _reconstruir(state, destino)
    _sincronizar(state, destino)
    return destino


def merge_clusters(state: SessionState, cluster_ids: list[str]) -> Cluster | None:
    """Combina dos o más grupos en uno nuevo."""
    a_combinar = [c for c in state.clusters if c.cluster_id in cluster_ids]
    if len(a_combinar) < 2:
        return None

    menciones: list[str] = []
    superficies: list[str] = []
    razones: list[str] = []
    for grupo in a_combinar:
        menciones.extend(grupo.mention_ids)
        superficies.extend(grupo.surfaces)
        razones.extend(grupo.reasons)

    combinado = Cluster(
        cluster_id=f"combinado_{len(state.clusters)}",
        cat=a_combinar[0].cat,
        mention_ids=list(dict.fromkeys(menciones)),
        surfaces=list(dict.fromkeys(superficies)),
        confidence="media",
        status="sugerido",
        reasons=sorted(set(razones)),
    )

    state.clusters = [c for c in state.clusters if c.cluster_id not in cluster_ids]
    state.clusters.append(combinado)
    _sincronizar(state, combinado)
    return combinado
