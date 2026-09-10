"""Exportación de la tabla de equivalencias.

Basado en el exportador CSV del Anonimizador Judicial de IALAB — Facultad de
Derecho, UBA (Apache 2.0). Modificado: se agregó la advertencia sobre el
carácter sensible del archivo y las columnas usan los nombres visibles de las
categorías chilenas.

Advertencia de protección de datos: esta tabla contiene los datos originales en
claro. A diferencia del mapa de reversión, no está cifrada, de modo que solo
debe usarse para el control interno del trabajo y nunca compartirse junto con
el documento anonimizado.
"""
from __future__ import annotations

import csv
import io

from app.models.schemas import ETIQUETAS_CATEGORIA, Detection

# Caracteres con que las planillas de cálculo interpretan que una celda es una
# fórmula. Anteponer un apóstrofo evita que un dato del documento se ejecute al
# abrir el archivo.
_PREFIJOS_FORMULA = ("=", "+", "-", "@")


def _neutralizar(valor: str) -> str:
    if valor and valor[0] in _PREFIJOS_FORMULA:
        return "'" + valor
    return valor


def build_csv_bytes(detections: list[Detection]) -> bytes:
    filas = [
        ["Tipo", "Dato original", "Sustitución", "Ocurrencias", "Activa", "Grupo"]
    ]
    for deteccion in detections:
        filas.append(
            [
                _neutralizar(ETIQUETAS_CATEGORIA.get(deteccion.cat, deteccion.cat)),
                _neutralizar(deteccion.original),
                _neutralizar(deteccion.placeholder),
                str(len(deteccion.positions)),
                "Sí" if deteccion.enabled else "No",
                _neutralizar(deteccion.cluster_id or ""),
            ]
        )

    buffer = io.StringIO()
    # El punto y coma es el separador que esperan las planillas configuradas en
    # español, que es el caso habitual en Chile.
    csv.writer(buffer, delimiter=";").writerows(filas)
    return ("﻿" + buffer.getvalue()).encode("utf-8")
