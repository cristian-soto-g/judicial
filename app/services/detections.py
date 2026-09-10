"""Alta, modificación y baja manual de detecciones.

Basado en el servicio de detecciones del Anonimizador Judicial de IALAB —
Facultad de Derecho, UBA (Apache 2.0). Modificado: mensajes y categorías
adecuados a este proyecto, y búsqueda de ocurrencias insensible a acentos, que
en documentos chilenos importa porque conviven "Muñoz" y "Munoz".
"""
from __future__ import annotations

import re

from app.anonymize.placeholders import make_placeholder
from app.models.schemas import Detection, Mention, Position, SessionState
from app.resolution.normalize import strip_accents


def _siguiente_id_mencion(state: SessionState) -> str:
    return f"m_manual_{len(state.mentions)}"


def _siguiente_id_deteccion(state: SessionState) -> int:
    return max((d.id for d in state.detections), default=-1) + 1


def _contador_categoria(state: SessionState, cat: str) -> int:
    return sum(1 for d in state.detections if d.cat == cat) + 1


def _buscar_ocurrencias(texto: str, superficie: str) -> list[Position]:
    """Busca todas las apariciones del texto, sin distinguir acentos ni mayúsculas."""
    objetivo = superficie.strip()
    if not objetivo:
        return []

    texto_plano = strip_accents(texto).lower()
    objetivo_plano = strip_accents(objetivo).lower()

    posiciones: list[Position] = []
    for coincidencia in re.finditer(re.escape(objetivo_plano), texto_plano):
        inicio, fin = coincidencia.start(), coincidencia.end()
        posiciones.append(Position(start=inicio, end=fin, raw=texto[inicio:fin]))
    return posiciones


def _detectar_existente(state: SessionState, cat: str, superficie: str) -> Detection | None:
    clave = f"{cat}||{superficie.strip().lower()}"
    return next(
        (
            d
            for d in state.detections
            if f"{d.cat}||{d.original.strip().lower()}" == clave
        ),
        None,
    )


def _agregar_posiciones(destino: Detection, posiciones: list[Position]) -> None:
    existentes = {(p.start, p.end) for p in destino.positions}
    for posicion in posiciones:
        if (posicion.start, posicion.end) not in existentes:
            destino.positions.append(posicion)
            existentes.add((posicion.start, posicion.end))


def add_manual_detection(
    state: SessionState,
    cat: str,
    start: int,
    end: int,
    original: str | None = None,
) -> Detection:
    """Agrega una detección a partir de un fragmento seleccionado a mano."""
    texto = state.doc_text
    if start < 0 or end > len(texto) or end <= start:
        raise ValueError("El rango de texto seleccionado no es válido.")

    superficie = (original or texto[start:end]).strip()
    if len(superficie) < 2:
        raise ValueError("La selección es demasiado corta para anonimizar.")

    from app.detection.filters import is_valid_manual_detection

    if not is_valid_manual_detection(cat, superficie, texto, start):
        raise ValueError(
            "La selección no parece un dato personal. Seleccione un nombre, un "
            "RUT, un domicilio u otro dato concreto, y no una frase completa."
        )

    fragmento = texto[start:end].strip()
    if fragmento and fragmento.lower() != superficie.lower():
        superficie = fragmento

    posiciones = _buscar_ocurrencias(texto, superficie)
    if not posiciones:
        posiciones = [Position(start=start, end=end, raw=texto[start:end])]

    mencion = Mention(
        id=_siguiente_id_mencion(state),
        cat=cat,  # type: ignore[arg-type]
        surface=superficie,
        start=posiciones[0].start,
        end=posiciones[0].end,
        norm=superficie.lower(),
        source_layer="manual",
    )
    state.mentions.append(mencion)

    existente = _detectar_existente(state, cat, superficie)
    if existente:
        _agregar_posiciones(existente, posiciones)
        existente.mention_ids.append(mencion.id)
        return existente

    deteccion = Detection(
        id=_siguiente_id_deteccion(state),
        cat=cat,  # type: ignore[arg-type]
        original=superficie,
        placeholder=make_placeholder(
            cat, superficie, _contador_categoria(state, cat), state.label_mode
        ),
        enabled=True,
        positions=posiciones,
        mention_ids=[mencion.id],
        user_added=True,
        fuente="manual",
    )
    state.detections.append(deteccion)
    return deteccion


def add_bulk_detection(
    state: SessionState,
    cat: str,
    original: str,
    positions: list[Position],
    placeholder: str | None = None,
) -> Detection:
    """Crea o extiende una detección con posiciones ya calculadas por el buscador.

    A diferencia de la selección con el cursor, aquí no se aplica el filtro de
    validez: quien escribe un término en el buscador y pide anonimizarlo ya
    manifestó su intención de manera inequívoca.
    """
    texto = state.doc_text
    superficie = original.strip()
    if len(superficie) < 2:
        raise ValueError("El texto que desea anonimizar es demasiado corto.")
    if not positions:
        raise ValueError("No se recibieron coincidencias para anonimizar.")

    vistas: set[tuple[int, int]] = set()
    limpias: list[Position] = []
    for posicion in positions:
        if posicion.start < 0 or posicion.end > len(texto) or posicion.end <= posicion.start:
            raise ValueError(
                f"Rango de texto inválido: {posicion.start}-{posicion.end}."
            )
        clave = (posicion.start, posicion.end)
        if clave in vistas:
            continue
        vistas.add(clave)
        limpias.append(
            Position(
                start=posicion.start,
                end=posicion.end,
                raw=texto[posicion.start : posicion.end],
            )
        )

    mencion = Mention(
        id=_siguiente_id_mencion(state),
        cat=cat,  # type: ignore[arg-type]
        surface=superficie,
        start=limpias[0].start,
        end=limpias[0].end,
        norm=superficie.lower(),
        source_layer="manual",
    )
    state.mentions.append(mencion)

    etiqueta_limpia: str | None = None
    if placeholder is not None:
        etiqueta_limpia = placeholder.strip()
        if not etiqueta_limpia:
            raise ValueError("La sustitución no puede quedar vacía.")

    existente = _detectar_existente(state, cat, superficie)
    if existente:
        _agregar_posiciones(existente, limpias)
        existente.mention_ids.append(mencion.id)
        if etiqueta_limpia:
            existente.placeholder = etiqueta_limpia
            existente.manual_placeholder = True
        return existente

    deteccion = Detection(
        id=_siguiente_id_deteccion(state),
        cat=cat,  # type: ignore[arg-type]
        original=superficie,
        placeholder=etiqueta_limpia
        or make_placeholder(
            cat, superficie, _contador_categoria(state, cat), state.label_mode
        ),
        enabled=True,
        positions=limpias,
        mention_ids=[mencion.id],
        manual_placeholder=bool(etiqueta_limpia),
        user_added=True,
        fuente="manual",
    )
    state.detections.append(deteccion)
    return deteccion


def update_detection(
    state: SessionState,
    detection_id: int,
    cat: str | None = None,
    placeholder: str | None = None,
    enabled: bool | None = None,
) -> Detection:
    """Modifica el tipo, la sustitución o el estado de una detección."""
    deteccion = next((d for d in state.detections if d.id == detection_id), None)
    if not deteccion:
        raise ValueError("No se encontró la detección indicada.")

    if cat and cat != deteccion.cat:
        deteccion.cat = cat  # type: ignore[assignment]
        deteccion.cluster_id = None
        for mention_id in deteccion.mention_ids:
            mencion = next((m for m in state.mentions if m.id == mention_id), None)
            if mencion:
                mencion.cat = cat  # type: ignore[assignment]
        if placeholder is None or not deteccion.manual_placeholder:
            deteccion.placeholder = make_placeholder(
                cat, deteccion.original, _contador_categoria(state, cat), state.label_mode
            )
            deteccion.manual_placeholder = False

    if placeholder is not None:
        limpia = placeholder.strip()
        if not limpia:
            raise ValueError("La sustitución no puede quedar vacía.")
        deteccion.placeholder = limpia
        deteccion.manual_placeholder = True

    if enabled is not None:
        deteccion.enabled = enabled

    return deteccion


def remove_detection(state: SessionState, detection_id: int) -> None:
    """Elimina una detección y sus menciones asociadas."""
    deteccion = next((d for d in state.detections if d.id == detection_id), None)
    if not deteccion:
        raise ValueError("No se encontró la detección indicada.")

    ids_mencion = set(deteccion.mention_ids)
    state.mentions = [m for m in state.mentions if m.id not in ids_mencion]
    state.detections = [d for d in state.detections if d.id != detection_id]

    for grupo in state.clusters:
        if deteccion.cluster_id and grupo.cluster_id == deteccion.cluster_id:
            grupo.surfaces = [
                s
                for s in grupo.surfaces
                if s.strip().lower() != deteccion.original.strip().lower()
            ]
            grupo.mention_ids = [
                mid for mid in grupo.mention_ids if mid not in ids_mencion
            ]
