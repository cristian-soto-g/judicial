"""Filtros de calidad posteriores a la detección.

Basado en los filtros del Anonimizador Judicial de IALAB — Facultad de
Derecho, UBA (Apache 2.0). Modificado: las reglas fueron reescritas para las
nueve categorías chilenas y para el lenguaje forense chileno.

Estos filtros descartan detecciones que, pese a calzar con un patrón, casi con
certeza no son datos personales: frases narrativas capturadas como nombres,
citas normativas confundidas con patentes, cifras de dinero tomadas por
identificadores. El umbral se fija de manera deliberadamente permisiva: se
descarta solo aquello que es claramente ruido, porque la revisión humana puede
quitar un falso positivo, pero no puede recuperar lo que el motor nunca marcó.
"""
from __future__ import annotations

import re

from app.detection.dictionaries import (
    STOPWORDS_FRASE,
    get_apellidos,
    get_formulas,
    get_nombres,
)
from app.detection.regex_cl import RawItem
from app.detection.validadores import validar_patente, validar_telefono
from app.resolution.normalize import normalize_text

# --- Personas -------------------------------------------------------------

_VERBOS_NARRATIVOS_RE = re.compile(
    r"\b(?:que|manifiesta|manifest[oó]|declara|declar[oó]|se[nñ]ala|se[nñ]al[oó]|"
    r"indica|indic[oó]|expresa|expres[oó]|refiere|refiri[oó]|sostiene|sostuvo|"
    r"agrega|agreg[oó]|reconoce|reconoci[oó]|niega|neg[oó]|solicita|solicit[oó]|"
    r"resuelve|resolvi[oó]|dispone|dispuso|ordena|orden[oó]|acredita|acredit[oó]|"
    r"fue|era|hab[ií]a|pudo|debe|deber[aá]|corresponde|procede)\b",
    re.IGNORECASE,
)

_CITA_PROCESAL_RE = re.compile(r"\b(?:c/|s/|v/|vs\.?|contra)\b", re.IGNORECASE)

# Palabras administrativas capitalizadas que el detector de personas confunde
# con apellidos cuando aparecen junto a uno.
_ADMINISTRATIVAS = frozenset(
    {
        "publico", "publica", "publicos", "publicas", "privado", "privada",
        "nacional", "nacionales", "regional", "regionales", "municipal",
        "municipales", "provincial", "estatal", "general", "generales",
        "especial", "especiales", "comun", "comunes", "civil", "penal",
        "laboral", "familia", "oral", "garantia", "suprema", "apelaciones",
        "primero", "segundo", "tercero", "cuarto", "quinto", "sexto",
        "septimo", "octavo", "noveno", "decimo", "norte", "sur", "oriente",
        "poniente", "centro", "chile", "chilena", "chileno", "santiago",
    }
)


def _parece_narrativa(surface: str) -> bool:
    """Indica si el texto capturado es una frase y no un nombre."""
    valor = surface.strip()
    if len(valor) > 60:
        return True
    palabras = valor.split()
    if len(palabras) >= 7:
        return True
    if len(palabras) >= 3 and _VERBOS_NARRATIVOS_RE.search(valor):
        return True
    if re.search(r"\bque\b", valor, re.IGNORECASE):
        return True
    normalizadas = [normalize_text(p) for p in palabras]
    formulas = get_formulas()
    if not normalizadas:
        return True
    coincidencias = sum(1 for p in normalizadas if p in formulas or p in STOPWORDS_FRASE)
    return coincidencias >= max(1, len(normalizadas) // 2 + 1)


def _es_persona_valida(
    surface: str, etiquetado: bool = False, del_modelo: bool = False
) -> bool:
    valor = surface.strip()
    if len(valor) < 3:
        return False
    if _parece_narrativa(valor):
        return False
    if _CITA_PROCESAL_RE.search(valor):
        return False

    normalizado = normalize_text(valor)
    if normalizado in get_formulas() or normalizado in STOPWORDS_FRASE:
        return False

    palabras = [p for p in valor.split() if len(p) > 1]
    if not palabras:
        return False

    normalizadas = [normalize_text(p) for p in palabras]
    tiene_nombre = any(p in get_nombres() for p in normalizadas)
    tiene_apellido = any(p in get_apellidos() for p in normalizadas)

    # Una palabra administrativa sin un nombre de pila que la ancle indica que
    # se capturó la denominación de un órgano, no a una persona.
    if any(p in _ADMINISTRATIVAS for p in normalizadas) and not tiene_nombre:
        return False

    # Con contexto explícito —tratamiento, rol procesal o RUT contiguo— se
    # acepta sin exigir diccionario. Esta excepción es la que permite detectar
    # apellidos poco frecuentes en la misma medida que los habituales.
    #
    # Lo mismo vale para lo que aporta el modelo de lenguaje: su clasificación
    # es la evidencia. Volver a exigirle diccionario anularía justamente
    # aquello para lo que sirve la capa, que es reconocer los nombres que las
    # reglas y el catálogo no alcanzan.
    if etiquetado or del_modelo:
        return len(palabras) <= 6

    if len(palabras) == 1:
        return normalizadas[0] in get_nombres() or normalizadas[0] in get_apellidos()

    if len(palabras) > 6:
        return False

    return tiene_nombre or tiene_apellido


# --- Número de causa ------------------------------------------------------

_CAUSA_ANIO_RE = re.compile(r"(?:19|20)\d{2}")


def _es_causa_valida(surface: str) -> bool:
    valor = surface.strip()
    if not re.search(r"\d", valor):
        return False
    # Un número de causa siempre trae el año de ingreso o el verificador del RUC.
    if _CAUSA_ANIO_RE.search(valor):
        return True
    return bool(re.search(r"\d{10}\s*-\s*[0-9kK]", valor))


# --- Domicilios -----------------------------------------------------------

_VIA_O_COMPLEMENTO_RE = re.compile(
    r"\b(?:calle|avenida|avda\.?|av\.?|pasaje|psje\.?|pje\.?|camino|ruta|"
    r"callej[oó]n|costanera|alameda|carretera|autopista|plaza|"
    r"depto\.?|departamento|dpto\.?|of\.?|oficina|casa|block|torre|piso|"
    r"villa|poblaci[oó]n|condominio|parcela|sitio|lote|manzana|km\.?|"
    r"sector|fundo|loteo|comuna)\b",
    re.IGNORECASE,
)

_DOMICILIO_RUIDO = (
    "territorio nacional",
    "situacion de calle",
    "situación de calle",
    "en el marco",
    "vía pública",
    "via publica",
    "la vía",
)


_VVERBO_RE = re.compile(
    r"\b(?:que|se\s+encuentra|manifiesta|declara|consta|habr[ií]a)\b",
    re.IGNORECASE,
)


def _es_domicilio_valido(surface: str) -> bool:
    valor = surface.strip()
    if len(valor) < 6:
        return False
    bajo = valor.lower()
    if any(ruido in bajo for ruido in _DOMICILIO_RUIDO):
        return False
    if _VVERBO_RE.search(valor) and len(valor.split()) > 6:
        return False
    if not _VIA_O_COMPLEMENTO_RE.search(valor):
        return False
    # Una dirección real tiene número, o bien una comuna o complemento.
    return bool(re.search(r"\d", valor)) or "comuna" in bajo or "," in valor



# --- Organizaciones -------------------------------------------------------

_ORG_INICIO_RE = re.compile(
    r"^(?:juzgado|tribunal|corte|fiscal[ií]a|defensor[ií]a|ministerio|"
    r"municipalidad|ilustre|gobernaci[oó]n|delegaci[oó]n|intendencia|seremi|"
    r"servicio|instituto|direcci[oó]n|superintendencia|subsecretar[ií]a|"
    r"contralor[ií]a|consejo|comisi[oó]n|carabineros|polic[ií]a|gendarmer[ií]a|"
    r"ej[eé]rcito|armada|registro|tesorer[ií]a|aduana|hospital|cl[ií]nica|"
    r"consultorio|cesfam|sapu|centro|universidad|liceo|colegio|escuela|"
    r"jard[ií]n|banco|caja|isapre|mutual|sociedad|empresa|comercial|"
    r"constructora|inmobiliaria|consultora|distribuidora|importadora|"
    r"exportadora|transportes|servicios|agr[ií]cola|compa[nñ][ií]a|"
    r"corporaci[oó]n|fundaci[oó]n|cooperativa|sindicato|junta|club|\d)",
    re.IGNORECASE,
)

_ORG_SUFIJO_FINAL_RE = re.compile(
    r"(?:s\.?\s?a\.?|s\.?p\.?a\.?|ltda\.?|limitada|e\.?i\.?r\.?l\.?|"
    r"cooperativa|corporaci[oó]n|fundaci[oó]n|a\.?\s?g\.?)$",
    re.IGNORECASE,
)

_ORG_COLA_NARRATIVA_RE = re.compile(
    r"\b(?:quien|quienes|cual|cuales|cuyo|cuya|que\s+|se\s+\w+[óo]\b|"
    r"resolvi[oó]|dispuso|orden[oó]|se[nñ]al[oó]|declar[oó]|conden[oó]|"
    r"absolvi[oó]|dict[oó]|resuelve|dispone)\b",
    re.IGNORECASE,
)

_ORG_ABREVIATURA_FINAL_RE = re.compile(r"\b(?:n[°ºo]|nro|art|inc|de|del|la|el|y)\s*\.?\s*$", re.IGNORECASE)


def _es_organizacion_valida(surface: str, del_modelo: bool = False) -> bool:
    valor = surface.strip()
    if len(valor) < 3:
        return False
    if len(valor) > 90 or len(valor.split()) > 12:
        return False
    if _ORG_COLA_NARRATIVA_RE.search(valor):
        return False
    if _ORG_ABREVIATURA_FINAL_RE.search(valor):
        return False
    if valor.isupper() and len(valor) <= 8:
        # Sigla institucional.
        return True
    if del_modelo:
        # El modelo reconoce razones sociales que ninguna regla prevé
        # —"Codelco", "Falabella"—: exigirles el encabezado institucional o el
        # sufijo societario las descartaría a todas.
        return valor[0].isupper()
    return bool(_ORG_INICIO_RE.match(valor) or _ORG_SUFIJO_FINAL_RE.search(valor))


# --- Otros datos sensibles ------------------------------------------------

_CONTEXTO_DINERO_RE = re.compile(
    r"(?:\$|pesos|monto|suma|capital|indemnizaci[oó]n|honorarios|multa\s+de|"
    r"unidades\s+tributarias|U\.?T\.?M\.?|U\.?F\.?|avalu[oó]|precio)",
    re.IGNORECASE,
)


def _es_otro_valido(surface: str, texto: str, inicio: int) -> bool:
    valor = surface.strip()
    if len(valor) < 3:
        return False
    if valor.startswith("http") or valor.startswith("@"):
        return True
    if not re.search(r"\d", valor):
        return False
    # Una cifra en contexto monetario no es un identificador.
    contexto = texto[max(0, inicio - 60) : inicio]
    if _CONTEXTO_DINERO_RE.search(contexto):
        return False
    return True


# --- API unificada --------------------------------------------------------


def is_valid_detection(
    cat: str,
    surface: str,
    texto: str = "",
    inicio: int = 0,
    etiquetado: bool = False,
    procedencia: str = "regla",
) -> bool:
    """Decide si una detección se conserva. Punto único de verdad del filtrado.

    `procedencia` distingue lo que produjo la mención. Las reglas y el modelo
    de lenguaje aportan evidencias de naturaleza distinta, y aplicarles el
    mismo criterio deja sin efecto a uno de los dos: un nombre que el modelo
    reconoce es, por lo general, el que el catálogo no contiene.
    """
    valor = surface.strip()
    if not valor or len(valor) < 2:
        return False

    del_modelo = procedencia == "modelo"

    if cat == "PERSONA":
        return _es_persona_valida(valor, etiquetado, del_modelo)
    if cat == "CAUSA":
        return _es_causa_valida(valor)
    if cat == "DOMICILIO":
        return _es_domicilio_valido(valor)
    if cat == "ORGANIZACION":
        return _es_organizacion_valida(valor, del_modelo)
    if cat == "TELEFONO":
        return validar_telefono(valor)
    if cat == "PATENTE":
        return validar_patente(valor, con_etiqueta=etiquetado)
    if cat == "OTRO":
        return _es_otro_valido(valor, texto, inicio)
    # RUT y EMAIL ya vienen validados por el detector.
    return True


def is_valid_manual_detection(
    cat: str, surface: str, texto: str = "", inicio: int = 0
) -> bool:
    """Validación relajada para el texto que la persona marca a mano.

    Cuando alguien selecciona un fragmento y pide anonimizarlo, ya expresó su
    intención: el filtro solo evita los errores evidentes, como haber
    seleccionado un párrafo completo por accidente.
    """
    valor = surface.strip()
    if len(valor) < 2:
        return False
    if len(valor) > 200:
        return False
    if cat == "PERSONA":
        return not _CITA_PROCESAL_RE.search(valor)
    if cat in ("RUT", "EMAIL", "CAUSA", "ORGANIZACION", "DOMICILIO", "OTRO"):
        return True
    return is_valid_detection(cat, valor, texto, inicio, etiquetado=True)


def apply_quality_filters(items: list[RawItem], texto: str) -> list[RawItem]:
    """Aplica los filtros a una lista de menciones en bruto."""
    return [
        item
        for item in items
        if is_valid_detection(item.cat, item.original, texto, item.start, item.etiquetado)
    ]
