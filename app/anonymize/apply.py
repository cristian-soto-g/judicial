"""Aplicación de las sustituciones sobre el texto del documento.

Basado en el módulo homónimo del Anonimizador Judicial de IALAB — Facultad de
Derecho, UBA (Apache 2.0). Modificado: se eliminó el modo "solo confirmados",
que en la práctica inducía a exportar documentos con datos sin reemplazar, y se
agregó el control de solapamientos al aplicar los reemplazos.
"""
from __future__ import annotations

from app.models.schemas import Detection


def anonymize_text(texto: str, detections: list[Detection]) -> str:
    """Devuelve el texto con cada dato activo reemplazado por su etiqueta."""
    reemplazos: list[tuple[int, int, str]] = [
        (posicion.start, posicion.end, deteccion.placeholder)
        for deteccion in detections
        if deteccion.enabled
        for posicion in deteccion.positions
    ]
    if not reemplazos:
        return texto

    # Resolución de solapamientos. Importa cuál prevalece: si dos reemplazos se
    # cruzan y se conservara el más breve, el fragmento restante del más
    # extenso quedaría a la vista. Ante "Juan Pérez Muñoz" y "Pérez", debe
    # aplicarse el primero, o el documento conservaría "Juan … Muñoz".
    # Por eso, a igual punto de inicio, se ordena primero el más extenso, y se
    # descarta todo lo que invada un tramo ya tomado.
    reemplazos.sort(key=lambda r: (r[0], -r[1]))

    conservados: list[tuple[int, int, str]] = []
    ultimo_fin = -1
    for inicio, fin, etiqueta in reemplazos:
        if inicio < ultimo_fin:
            continue
        conservados.append((inicio, fin, etiqueta))
        ultimo_fin = fin

    # Se aplica de atrás hacia adelante para que los índices no se desplacen.
    resultado = texto
    for inicio, fin, etiqueta in reversed(conservados):
        resultado = resultado[:inicio] + etiqueta + resultado[fin:]

    return resultado


def build_highlights(detections: list[Detection]) -> list[dict]:
    """Genera los rangos que la interfaz resalta sobre el documento original."""
    rangos = [
        {
            "start": posicion.start,
            "end": posicion.end,
            "cat": deteccion.cat,
            "placeholder": deteccion.placeholder,
            "detection_id": deteccion.id,
            "cluster_id": deteccion.cluster_id,
        }
        for deteccion in detections
        if deteccion.enabled
        for posicion in deteccion.positions
    ]

    rangos.sort(key=lambda r: (r["start"], -r["end"]))

    sin_solapes: list[dict] = []
    ultimo_fin = -1
    for rango in rangos:
        if rango["start"] >= ultimo_fin:
            sin_solapes.append(rango)
            ultimo_fin = rango["end"]

    return sin_solapes
