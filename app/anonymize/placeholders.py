"""Generación de las etiquetas que reemplazan a cada dato.

Basado en el módulo de sustituciones del Anonimizador Judicial de IALAB —
Facultad de Derecho, UBA (Apache 2.0). Modificado: las etiquetas corresponden a
las nueve categorías chilenas y el modo de iniciales contempla los sufijos
societarios chilenos.
"""
from __future__ import annotations

from app.models.schemas import Detection, Mention, Position

# Etiqueta genérica por categoría, sin numerar.
ETIQUETAS_GENERICAS: dict[str, str] = {
    "PERSONA": "[NOMBRE]",
    "RUT": "[RUT]",
    "ORGANIZACION": "[ORGANIZACIÓN]",
    "EMAIL": "[CORREO]",
    "TELEFONO": "[TELÉFONO]",
    "DOMICILIO": "[DOMICILIO]",
    "PATENTE": "[PATENTE]",
    "OTRO": "[DATO]",
    "CAUSA": "[CAUSA]",
}

# Raíz de la etiqueta numerada por categoría.
RAICES_CATEGORIZADAS: dict[str, str] = {
    "PERSONA": "PERSONA",
    "RUT": "RUT",
    "ORGANIZACION": "ORGANIZACION",
    "EMAIL": "CORREO",
    "TELEFONO": "TELEFONO",
    "DOMICILIO": "DOMICILIO",
    "PATENTE": "PATENTE",
    "OTRO": "DATO",
    "CAUSA": "CAUSA",
}

_PARTICULAS_INICIALES = {
    "de", "del", "la", "las", "los", "y", "e", "i",
    "s.a.", "spa", "ltda.", "ltda", "limitada", "e.i.r.l.", "eirl",
}


def make_placeholder(cat: str, original: str, indice: int, modo: str) -> str:
    """Devuelve la etiqueta con que se reemplazará el dato."""
    if modo == "gen":
        return ETIQUETAS_GENERICAS.get(cat, "[DATO]")

    if modo == "ini" and cat in ("PERSONA", "ORGANIZACION"):
        partes = [
            parte
            for parte in original.split()
            if parte.lower() not in _PARTICULAS_INICIALES and len(parte) > 1
        ]
        if partes:
            return "".join(parte[0].upper() + "." for parte in partes)
        return ETIQUETAS_GENERICAS.get(cat, "[DATO]")

    raiz = RAICES_CATEGORIZADAS.get(cat, "DATO")
    return f"[{raiz}_{indice}]"


def build_detections_from_mentions(
    mentions: list[Mention], modo: str
) -> list[Detection]:
    """Agrupa las menciones idénticas en una detección por dato distinto."""
    grupos: dict[str, dict] = {}
    for mencion in mentions:
        clave = f"{mencion.cat}||{mencion.surface.strip().lower()}"
        if clave not in grupos:
            grupos[clave] = {
                "cat": mencion.cat,
                "original": mencion.surface.strip(),
                "positions": [],
                "mention_ids": [],
                "fuente": mencion.source_layer,
            }
        grupos[clave]["positions"].append(
            Position(start=mencion.start, end=mencion.end, raw=mencion.surface)
        )
        grupos[clave]["mention_ids"].append(mencion.id)

    contadores: dict[str, int] = {}
    detecciones: list[Detection] = []

    for identificador, grupo in enumerate(grupos.values()):
        categoria = grupo["cat"]
        contadores[categoria] = contadores.get(categoria, 0) + 1
        detecciones.append(
            Detection(
                id=identificador,
                cat=categoria,
                original=grupo["original"],
                placeholder=make_placeholder(
                    categoria, grupo["original"], contadores[categoria], modo
                ),
                enabled=True,
                positions=grupo["positions"],
                mention_ids=grupo["mention_ids"],
                fuente=grupo["fuente"],
            )
        )

    return detecciones
