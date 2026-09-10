"""Limpieza del texto extraído de un PDF.

Basado en el módulo de limpieza del Anonimizador Judicial de IALAB — Facultad
de Derecho, UBA (Apache 2.0). Modificado: se agregaron los patrones de pie de
página habituales en resoluciones chilenas y el descarte de las líneas de
firma electrónica avanzada, que la Oficina Judicial Virtual estampa al pie de
cada documento y que no aportan contenido al análisis.
"""
from __future__ import annotations

import re

# Pie de página del tipo "1 | Página", incluso con las letras separadas por el
# extractor de PDF.
_PIE_PAGINA_RE = re.compile(
    r"^\s*\d+\s*\|\s*(?:P\s*)?[áaÁA]?\s*(?:g\s*)?(?:i\s*)?(?:n\s*)?(?:a\s*)?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Encabezados con letras separadas ("P á g i n a").
_PALABRA_ESPACIADA_RE = re.compile(
    r"\b((?:[A-Za-zÁÉÍÓÚÑáéíóúñ]\s){2,}[A-Za-zÁÉÍÓÚÑáéíóúñ])\b"
)

# Línea que contiene solo el número de página.
_NUMERO_PAGINA_SOLO_RE = re.compile(r"^\s*\d{1,4}\s*$", re.MULTILINE)

# Sello de firma electrónica del Poder Judicial. Se elimina porque es texto
# repetido en cada página y arrastra códigos que el motor confundiría con
# números de causa.
_FIRMA_ELECTRONICA_RE = re.compile(
    r"^.*(?:"
    r"firma(?:do)?\s+electr[óo]nicamente|"
    r"firma\s+electr[óo]nica\s+avanzada|"
    r"c[óo]digo\s+de\s+verificaci[óo]n|"
    r"verifique\s+(?:la\s+)?(?:validez|autenticidad)|"
    r"documento\s+firmado\s+digitalmente|"
    r"este\s+documento\s+(?:tiene|posee)\s+firma"
    r").*$",
    re.IGNORECASE | re.MULTILINE,
)


def _colapsar_letras_espaciadas(coincidencia: re.Match[str]) -> str:
    return re.sub(r"\s+", "", coincidencia.group(1))


def clean_pdf_text(texto: str) -> str:
    """Quita el ruido de paginación y normaliza los saltos de línea."""
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    texto = _PALABRA_ESPACIADA_RE.sub(_colapsar_letras_espaciadas, texto)
    texto = _FIRMA_ELECTRONICA_RE.sub("", texto)
    texto = _PIE_PAGINA_RE.sub("", texto)
    texto = _NUMERO_PAGINA_SOLO_RE.sub("", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def merge_lines_to_paragraphs(texto: str) -> str:
    """Une en párrafos las líneas que el PDF cortó por razones de maquetado."""
    lineas = [linea.strip() for linea in texto.split("\n") if linea.strip()]
    parrafos: list[str] = []
    actual = ""

    for linea in lineas:
        if not actual:
            actual = linea
            continue
        if _linea_continua(actual, linea):
            actual = f"{actual} {linea}"
        else:
            parrafos.append(actual.strip())
            actual = linea

    if actual:
        parrafos.append(actual.strip())

    return "\n\n".join(parrafos)


def _linea_continua(anterior: str, siguiente: str) -> bool:
    """Heurística: determina si la línea siguiente pertenece al mismo párrafo."""
    if re.match(r"^[\d\-•·–—]\s", siguiente):
        return False
    if anterior.endswith("-"):
        return True
    if anterior.rstrip().endswith((",", ";", ":")):
        return True
    if anterior.rstrip()[-1] not in ".!?":
        if siguiente[0].islower() or siguiente[0] in "([\"'":
            return True
    return False
