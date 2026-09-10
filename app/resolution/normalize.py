"""Normalización de menciones para comparar variantes de un mismo dato.

Basado en el módulo de normalización del Anonimizador Judicial de IALAB —
Facultad de Derecho, UBA (Apache 2.0). Modificado: los tratamientos y roles
procesales que se recortan son los del proceso chileno, y la identificación de
apellidos contempla el orden habitual en Chile, donde la persona se
individualiza con dos apellidos (paterno y materno).
"""
from __future__ import annotations

import re
import unicodedata

# Tratamientos de cortesía y roles procesales que preceden al nombre y que no
# forman parte de él.
TRATAMIENTOS = re.compile(
    r"^(?:el|la|los|las)\s+"
    r"|(?:sr\.?|sra\.?|srta\.?|don|do[nñ]a|se[nñ]or(?:a|ita)?|"
    r"dr\.?|dra\.?|do[cn]tor(?:a)?|abogad[oa]|"
    r"juez|jueza|ministr[oa]|fiscal|defensor(?:a)?|perit[oa]|"
    r"funcionari[oa]|carabiner[oa]|sargento|cabo|teniente|capit[aá]n|"
    r"comisari[oa]|subcomisari[oa]|inspector(?:a)?|detective)\s+"
    r"|(?:imputad[oa]|acusad[oa]|condenad[oa]|sentenciad[oa]|"
    r"v[ií]ctima|ofendid[oa]|denunciante|querellante|querellad[oa]|"
    r"testig[oa]|demandante|demandad[oa]|solicitante|"
    r"ni[nñ][oa]|adolescente|menor)\s+",
    re.IGNORECASE,
)

_PARTICULAS = {"de", "del", "la", "las", "los", "y", "i", "da", "dos", "van", "von"}


def strip_accents(texto: str) -> str:
    """Quita los diacríticos, para que Muñoz y Munoz se comparen como iguales."""
    return "".join(
        c
        for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def normalize_text(texto: str) -> str:
    """Minúsculas, sin acentos y con los espacios colapsados."""
    resultado = texto.lower().strip()
    resultado = strip_accents(resultado)
    return re.sub(r"\s+", " ", resultado)


def normalize_mention(surface: str) -> str:
    """Normaliza una mención quitando tratamientos, roles y puntuación."""
    resultado = normalize_text(surface)
    resultado = TRATAMIENTOS.sub("", resultado).strip()
    return re.sub(r"[\.,]", "", resultado)


def tokenize_name(texto: str) -> list[str]:
    """Divide un nombre en palabras significativas, sin partículas."""
    return [p for p in re.split(r"\s+", texto) if p and p not in _PARTICULAS]


def get_initials(tokens: list[str]) -> str:
    return "".join(t[0] for t in tokens if t)


def get_surnames(tokens: list[str]) -> set[str]:
    """Devuelve los tokens que probablemente son apellidos.

    En Chile la individualización habitual es "nombre(s) + apellido paterno +
    apellido materno", de modo que los apellidos ocupan las dos últimas
    posiciones. En los encabezados judiciales, en cambio, aparece la notación
    invertida "APELLIDO, Nombre". Se contemplan ambas: primero se consulta el
    diccionario y, si no hay coincidencia, se toman los extremos como
    candidatos, lo que permite emparejar variantes aun con apellidos ausentes
    del catálogo.
    """
    if len(tokens) <= 1:
        return set(tokens)

    try:
        from app.detection.dictionaries import get_apellidos

        apellidos = get_apellidos()
    except Exception:  # pragma: no cover - el diccionario es opcional
        apellidos = set()

    coincidencias = {t for t in tokens if t in apellidos}
    if coincidencias:
        return coincidencias

    if len(tokens) >= 3:
        # Nombre + dos apellidos: los dos últimos tokens.
        return {tokens[-2], tokens[-1], tokens[0]}
    return {tokens[0], tokens[-1]}
