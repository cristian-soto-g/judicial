"""Orquestación de las capas de detección.

Basado en el orquestador del Anonimizador Judicial de IALAB — Facultad de
Derecho, UBA (Apache 2.0). Modificado: la capa determinística es ahora la
chilena, la capa de lenguaje natural pasó a ser opcional y la resolución de
solapamientos respeta el orden de prioridad entre categorías en lugar del
simple orden de aparición.
"""
from __future__ import annotations

import logging

from app.config import ENABLE_SPACY
from app.detection.filters import apply_quality_filters
from app.detection.regex_cl import PRIORIDAD_CATEGORIAS, RawItem, detect_regex_cl
from app.models.schemas import Mention

logger = logging.getLogger(__name__)

_ORDEN_PRIORIDAD = {categoria: i for i, categoria in enumerate(PRIORIDAD_CATEGORIAS)}


def raw_to_mentions(items: list[RawItem]) -> list[Mention]:
    """Convierte las menciones en bruto al modelo de datos de la aplicación."""
    return [
        Mention(
            id=f"m{indice}",
            cat=item.cat,  # type: ignore[arg-type]
            surface=item.original,
            start=item.start,
            end=item.end,
            norm=item.original.strip().lower(),
            source_layer=item.source_layer,
        )
        for indice, item in enumerate(items)
    ]


def _resolver_solapamientos(items: list[RawItem]) -> list[RawItem]:
    """Ante dos detecciones superpuestas, conserva la más confiable.

    El criterio es, en orden: la categoría de mayor prioridad, luego la que
    tenga contexto explícito, y por último la de mayor extensión. Así, un RUT
    dentro de una frase capturada como domicilio prevalece sobre el domicilio,
    y un nombre con tratamiento prevalece sobre una coincidencia casual.
    """
    ordenados = sorted(
        items,
        key=lambda it: (
            _ORDEN_PRIORIDAD.get(it.cat, 99),
            0 if it.etiquetado else 1,
            -(it.end - it.start),
            it.start,
        ),
    )

    conservados: list[RawItem] = []
    ocupados: list[tuple[int, int]] = []

    for item in ordenados:
        if any(item.start < fin and inicio < item.end for inicio, fin in ocupados):
            continue
        conservados.append(item)
        ocupados.append((item.start, item.end))

    conservados.sort(key=lambda it: it.start)
    return conservados


def run_detection(
    texto: str,
    enabled_categories: list[str] | None = None,
    sensibilidad: str = "exhaustiva",
    session_id: str | None = None,
) -> list[Mention]:
    """Ejecuta todas las capas y devuelve las menciones finales."""
    from app.services.analysis_cancel import check_cancel

    check_cancel(session_id)
    items = detect_regex_cl(texto, sensibilidad=sensibilidad)
    logger.debug("Capa determinística: %d menciones", len(items))

    if ENABLE_SPACY:
        check_cancel(session_id)
        try:
            from app.detection.spacy_layer import detect_spacy

            items_spacy = detect_spacy(texto)
            items.extend(items_spacy)
            logger.debug("Capa de lenguaje natural: %d menciones", len(items_spacy))
        except Exception as error:
            logger.info("Capa de lenguaje natural no disponible: %s", error)

    check_cancel(session_id)
    items = apply_quality_filters(items, texto)

    # El orden de estas dos operaciones no es indiferente. Las categorías que
    # el usuario desactivó deben descartarse ANTES de resolver los
    # solapamientos, nunca después: si una mención descartada participara de la
    # resolución, podría desplazar a otra que sí interesa y esta última se
    # perdería sin dejar rastro. Es un fallo de privacidad, no de precisión.
    # Ejemplo concreto: en "la empresa Juan Pérez Muñoz Ltda." la organización
    # abarca al nombre y tiene prioridad sobre él; con la categoría de
    # organizaciones desactivada, resolver primero eliminaría el nombre de la
    # persona junto con la organización que lo contenía.
    if enabled_categories is not None:
        permitidas = set(enabled_categories)
        items = [item for item in items if item.cat in permitidas]

    items = _resolver_solapamientos(items)

    return raw_to_mentions(items)
