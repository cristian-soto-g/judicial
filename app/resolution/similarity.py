"""Similitud textual y reglas de identidad entre menciones.

Basado en el módulo de similitud del Anonimizador Judicial de IALAB — Facultad
de Derecho, UBA (Apache 2.0). Modificado: las reglas de apellido compartido
contemplan el uso chileno de dos apellidos, y el enlace por identificador
compartido opera sobre el RUT en lugar del DNI y el CUIT argentinos.

Precaución relevante: compartir apellido no basta para unificar dos menciones.
En un expediente es habitual que aparezcan varios miembros de una misma
familia; unificarlos produciría una anonimización incorrecta que además
confundiría a quien lea el documento.
"""
from __future__ import annotations

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover - respaldo si falta la biblioteca
    fuzz = None

from app.config import FUZZY_HIGH, FUZZY_MEDIUM, PROXIMITY_CHARS
from app.models.schemas import Mention
from app.resolution.normalize import (
    get_initials,
    get_surnames,
    normalize_mention,
    tokenize_name,
)


def fuzzy_score(a: str, b: str) -> float:
    """Similitud entre dos cadenas, en una escala de 0 a 100."""
    if fuzz is not None:
        return float(fuzz.token_sort_ratio(a, b))
    from difflib import SequenceMatcher

    return float(SequenceMatcher(None, a, b).ratio() * 100)


def _es_inicial(token: str) -> bool:
    return len(token.replace(".", "").strip()) <= 2


def shared_surname(tokens_a: list[str], tokens_b: list[str]) -> bool:
    apellidos_a = get_surnames(tokens_a)
    apellidos_b = get_surnames(tokens_b)
    return bool(apellidos_a & apellidos_b)


def initials_match(tokens_a: list[str], tokens_b: list[str]) -> bool:
    """Compara "J. Pérez" con "Juan Pérez" exigiendo apellido en común."""
    if not tokens_a or not tokens_b:
        return False
    if not shared_surname(tokens_a, tokens_b):
        return False

    iniciales_a = get_initials(tokens_a)
    iniciales_b = get_initials(tokens_b)
    if not iniciales_a or not iniciales_b:
        return False

    if any(_es_inicial(t) for t in tokens_a) or any(_es_inicial(t) for t in tokens_b):
        return (
            iniciales_a[0] == iniciales_b[0]
            or iniciales_a in iniciales_b
            or iniciales_b in iniciales_a
        )

    if tokens_a[0] != tokens_b[0]:
        return False

    corta, larga = (
        (iniciales_a, iniciales_b)
        if len(iniciales_a) <= len(iniciales_b)
        else (iniciales_b, iniciales_a)
    )
    return larga.startswith(corta)


def apellido_aislado(tokens_a: list[str], tokens_b: list[str]) -> bool:
    """Indica si una mención es un apellido suelto contenido en la otra."""
    conjunto_a, conjunto_b = set(tokens_a), set(tokens_b)
    if len(conjunto_a) != 1 and len(conjunto_b) != 1:
        return False
    if not (conjunto_a < conjunto_b or conjunto_b < conjunto_a):
        return False
    return shared_surname(tokens_a, tokens_b)


def nombre_abreviado(tokens_a: list[str], tokens_b: list[str]) -> bool:
    """Indica si un nombre es una forma abreviada del otro.

    En Chile la individualización completa lleva uno o dos nombres de pila más
    los apellidos paterno y materno, pero el mismo escrito alterna después con
    formas más breves: "Juan Ignacio Pérez Muñoz" y luego "Juan Pérez Muñoz".
    La similitud textual no resuelve bien ese caso —omitir un nombre de pila
    baja el puntaje por debajo de cualquier umbral razonable—, de modo que se
    aplica una regla estructural: una forma es abreviatura de la otra cuando
    sus palabras están contenidas en las de la otra, comparten apellido y
    coinciden en al menos dos palabras.
    """
    conjunto_a, conjunto_b = set(tokens_a), set(tokens_b)
    if conjunto_a == conjunto_b:
        return False
    if not (conjunto_a <= conjunto_b or conjunto_b <= conjunto_a):
        return False
    if not shared_surname(tokens_a, tokens_b):
        return False
    return len(conjunto_a & conjunto_b) >= 2


def proximity(m1: Mention, m2: Mention, texto: str) -> bool:
    """Indica si dos menciones están lo bastante cerca en el documento."""
    if m1.cat != "PERSONA" or m2.cat != "PERSONA":
        return False
    if abs(m1.start - m2.start) <= PROXIMITY_CHARS:
        return True
    inicio_parrafo = texto.rfind("\n", 0, min(m1.start, m2.start))
    fin_parrafo = texto.find("\n", max(m1.end, m2.end))
    if fin_parrafo == -1:
        fin_parrafo = len(texto)
    return m1.start >= inicio_parrafo and m2.start <= fin_parrafo


def link_personas_near_identifier(
    mentions: list[Mention],
) -> list[tuple[str, str, float, str]]:
    """Enlaza personas que aparecen junto al mismo RUT.

    Se exige, además de la cercanía, que las menciones sean compatibles entre
    sí. Dos personas distintas pueden figurar cerca de un mismo RUT —el
    imputado y su abogado, por ejemplo— y unificarlas sería un error grave.
    """
    aristas: list[tuple[str, str, float, str]] = []
    identificadores = [m for m in mentions if m.cat == "RUT"]
    personas = [m for m in mentions if m.cat == "PERSONA"]

    for identificador in identificadores:
        cercanas = [
            p
            for p in personas
            if abs(identificador.start - p.start) <= PROXIMITY_CHARS
        ]
        for indice, p1 in enumerate(cercanas):
            for p2 in cercanas[indice + 1 :]:
                n1 = normalize_mention(p1.surface)
                n2 = normalize_mention(p2.surface)
                t1 = tokenize_name(n1)
                t2 = tokenize_name(n2)
                if initials_match(t1, t2) or fuzzy_score(n1, n2) >= FUZZY_HIGH:
                    aristas.append((p1.id, p2.id, 0.95, "identificador_compartido"))

    return aristas


def compute_edge(m1: Mention, m2: Mention, texto: str) -> tuple[float, str, str] | None:
    """Determina si dos menciones corresponden al mismo dato."""
    if m1.cat != m2.cat:
        return None

    n1 = normalize_mention(m1.surface)
    n2 = normalize_mention(m2.surface)
    if n1 == n2:
        return (1.0, "alta", "identica")

    puntaje = fuzzy_score(n1, n2)
    t1 = tokenize_name(n1)
    t2 = tokenize_name(n2)

    if m1.cat == "PERSONA":
        if initials_match(t1, t2):
            return (0.93, "alta", "iniciales")

        # Mención por apellido solo frente al nombre completo. La coincidencia
        # se propone, no se impone: dos familiares comparten apellido, de modo
        # que la confirmación queda en manos de quien revisa.
        if apellido_aislado(t1, t2):
            return (0.84, "media", "apellido_solo")

        if nombre_abreviado(t1, t2):
            compartidas = len(set(t1) & set(t2))
            # Con tres palabras en común —dos apellidos y un nombre de pila— la
            # coincidencia es prácticamente segura. Con solo dos conviene que la
            # revisión humana lo confirme: dos hermanos comparten ambos
            # apellidos y difieren únicamente en el nombre de pila.
            if compartidas >= 3:
                return (0.9, "alta", "nombre_abreviado")
            return (0.86, "media", "nombre_abreviado")

        if shared_surname(t1, t2) and puntaje >= FUZZY_MEDIUM:
            confianza = "alta" if puntaje >= FUZZY_HIGH else "media"
            return (max(puntaje, 88) / 100, confianza, "apellido_comun")

        if proximity(m1, m2, texto) and shared_surname(t1, t2) and puntaje >= FUZZY_HIGH:
            return (puntaje / 100, "media", "proximidad")

        return None

    if puntaje >= FUZZY_HIGH:
        return (puntaje / 100, "alta", "similitud_alta")
    if puntaje >= FUZZY_MEDIUM:
        return (puntaje / 100, "baja", "similitud_media")

    return None
