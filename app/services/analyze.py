"""Servicio de análisis completo de un documento.

Basado en el servicio de análisis del Anonimizador Judicial de IALAB —
Facultad de Derecho, UBA (Apache 2.0). Modificado: las categorías por defecto
son las nueve chilenas, se transporta el nivel de sensibilidad hasta el motor y
las estadísticas incluyen el desglose por categoría con sus nombres visibles.
"""
from __future__ import annotations

import logging
import time

from app.detection.pipeline import run_detection
from app.models.schemas import (
    CATEGORIAS,
    AnalyzeResponse,
    Detection,
    SessionState,
)
from app.resolution.cluster import build_clusters, mentions_to_detections
from app.services.analysis_cancel import check_cancel, clear_cancel

logger = logging.getLogger(__name__)

CATEGORIAS_POR_DEFECTO = list(CATEGORIAS)


def _absorber_menciones_parciales(detections: list[Detection]) -> list[Detection]:
    """Funde en el nombre completo las menciones que solo traen el apellido.

    Un mismo escrito individualiza a la persona una vez —"Ana María Painemal
    Quilaqueo"— y después la nombra solo por su apellido. Ambas menciones deben
    quedar cubiertas por una única sustitución: si se conservaran como
    detecciones separadas, el documento anonimizado usaría dos seudónimos para
    la misma persona y su lectura induciría a error.

    La operación traslada las posiciones de la mención breve a la extensa, en
    lugar de descartarlas. Descartarlas —que es lo que hacía la aplicación en
    que este trabajo se basa— dejaba esas apariciones sin reemplazar en el
    documento final, que es precisamente el error que no puede cometerse al
    tratar información sensible.
    """
    personas = [d for d in detections if d.cat == "PERSONA"]
    otras = [d for d in detections if d.cat != "PERSONA"]

    # De la más extensa a la más breve: cada mención se ofrece a la primera
    # detección que la contenga.
    personas.sort(key=lambda d: len(d.original), reverse=True)

    conservadas: list[Detection] = []
    for deteccion in personas:
        actual = deteccion.original.strip().lower()

        contenedora = next(
            (
                previa
                for previa in conservadas
                if not deteccion.user_added
                and len(actual) >= 4
                and actual != previa.original.strip().lower()
                and _es_subcadena_de_palabras(actual, previa.original.strip().lower())
            ),
            None,
        )

        if contenedora is None:
            conservadas.append(deteccion)
            continue

        existentes = {(p.start, p.end) for p in contenedora.positions}
        for posicion in deteccion.positions:
            if (posicion.start, posicion.end) not in existentes:
                contenedora.positions.append(posicion)
                existentes.add((posicion.start, posicion.end))
        contenedora.mention_ids.extend(deteccion.mention_ids)

    return otras + conservadas


def _es_subcadena_de_palabras(breve: str, extensa: str) -> bool:
    """Comprueba que todas las palabras de la forma breve estén en la extensa."""
    palabras_breves = breve.split()
    palabras_extensas = set(extensa.split())
    return bool(palabras_breves) and all(
        palabra in palabras_extensas for palabra in palabras_breves
    )


def prune_detections(detections: list[Detection], texto: str) -> list[Detection]:
    """Vuelve a aplicar los filtros y renumera las detecciones."""
    from app.detection.filters import is_valid_detection

    depuradas: list[Detection] = []
    for deteccion in detections:
        if deteccion.user_added:
            depuradas.append(deteccion)
            continue
        inicio = deteccion.positions[0].start if deteccion.positions else 0
        if is_valid_detection(deteccion.cat, deteccion.original, texto, inicio, True):
            depuradas.append(deteccion)

    depuradas = _absorber_menciones_parciales(depuradas)
    depuradas.sort(key=lambda d: (d.positions[0].start if d.positions else 0))
    for indice, deteccion in enumerate(depuradas):
        deteccion.id = indice
    return depuradas


def run_full_analysis(state: SessionState) -> AnalyzeResponse:
    """Ejecuta la detección, la agrupación y la asignación de etiquetas."""
    clear_cancel(state.session_id)
    categorias = state.enabled_categories or CATEGORIAS_POR_DEFECTO

    inicio = time.perf_counter()
    mentions = run_detection(
        state.doc_text,
        enabled_categories=list(categorias),
        sensibilidad=state.sensibilidad,
        session_id=state.session_id,
    )
    tras_deteccion = time.perf_counter()

    check_cancel(state.session_id)
    state.mentions = mentions

    clusters = build_clusters(mentions, state.doc_text)
    tras_agrupacion = time.perf_counter()
    check_cancel(state.session_id)
    state.clusters = clusters

    detections = mentions_to_detections(mentions, state.label_mode, clusters)
    detections = prune_detections(detections, state.doc_text)
    state.detections = detections

    logger.info(
        "Análisis de %s: detección %.2fs (%d menciones), agrupación %.2fs "
        "(%d grupos), total %.2fs",
        state.doc_name or state.session_id,
        tras_deteccion - inicio,
        len(mentions),
        tras_agrupacion - tras_deteccion,
        len(clusters),
        tras_agrupacion - inicio,
    )

    estadisticas: dict[str, int] = {categoria: 0 for categoria in CATEGORIAS}
    for deteccion in detections:
        if deteccion.enabled and deteccion.cat in estadisticas:
            estadisticas[deteccion.cat] += 1
    estadisticas["TOTAL"] = len(detections)
    estadisticas["OCURRENCIAS"] = sum(len(d.positions) for d in detections if d.enabled)

    return AnalyzeResponse(
        session_id=state.session_id,
        detections=detections,
        clusters=clusters,
        stats=estadisticas,
    )
