"""Detección determinística de datos personales en documentos chilenos.

Este módulo ocupa el lugar que en el Anonimizador Judicial de IALAB — Facultad
de Derecho, UBA (Apache 2.0) ocupaba la detección argentina. Conserva de aquel
la arquitectura general —un conjunto de detectores por categoría que aportan
menciones a una lista común, con resolución de solapamientos por prioridad—,
pero todas las expresiones regulares y todas las reglas de validación fueron
escritas de nuevo para el ordenamiento chileno.

Dos criterios gobiernan este archivo:

1. Ante la duda, se detecta. Un falso positivo se corrige en la pantalla de
   revisión con un clic; un dato personal no detectado se publica.
2. Cuando el dato viene precedido por una etiqueta ("RUT", "RIT", "teléfono"),
   se marca únicamente el valor y no la etiqueta. El documento anonimizado
   conserva así su legibilidad: se lee "RIT N° [CAUSA_1]" y no "[CAUSA_1]".

Nota sobre el uso de mayúsculas y minúsculas. Varias reglas dependen de la
capitalización para distinguir un nombre propio de una palabra corriente. Por
eso las expresiones no llevan la marca global de insensibilidad a mayúsculas:
esa insensibilidad se aplica solo al rótulo, mediante grupos `(?i:...)`.
Aplicarla a toda la expresión haría que `[A-Z]` calzara también con minúsculas
y el motor tomaría verbos por apellidos.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.detection.dictionaries import (
    PREFIJOS_ORGANIZACION,
    SIGLAS_ORGANIZACION,
    STOPWORDS_FRASE,
    SUFIJOS_ORGANIZACION,
    get_apellidos,
    get_formulas,
    get_nombres,
)
from app.detection.validadores import (
    validar_formato_ruc,
    validar_patente,
    validar_rut,
    validar_telefono,
)
from app.resolution.normalize import normalize_text


@dataclass
class RawItem:
    """Mención en bruto, antes de la deduplicación y del filtrado de calidad."""

    cat: str
    original: str
    start: int
    end: int
    source_layer: str = "regex"
    score: float = 0.8
    etiquetado: bool = False
    razones: list[str] = field(default_factory=list)


def _ci(patron: str) -> str:
    """Envuelve un fragmento para que ignore mayúsculas solo en ese tramo."""
    return f"(?i:{patron})"


# --- Piezas reutilizables -------------------------------------------------

_NUM = _ci(r"(?:N[°ºo]\.?|Nro\.?|N[uú]m(?:ero)?\.?)?") + r"\s*[:\-–]?\s*"
_MAY = "A-ZÁÉÍÓÚÜÑ"
_MIN = "a-záéíóúüñ"
_PALABRA_TITULO = rf"[{_MAY}][{_MIN}]+"
_PALABRA_MAYUSCULA = rf"[{_MAY}]{{2,}}"
# El orden importa: las alternativas se prueban de izquierda a derecha, de
# modo que "del" debe ir antes que "de" o nunca llegaría a coincidir y
# "Constructora del Sur" se leería como "Constructora de".
_PARTICULA = r"(?:del|de|las|los|la|y|da|van|von)\b"

_MESES = (
    r"(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
    r"sep?tiembre|octubre|noviembre|diciembre)"
)

_TRATAMIENTOS = (
    r"(?:Sr\.?|Sra\.?|Srta\.?|Sres\.?|se[nñ]or(?:a|ita)?|don|do[nñ]a|"
    r"Dr\.?|Dra\.?|doctor(?:a)?|Prof\.?|profesor(?:a)?|"
    r"abogad[oa]|Ab\.?|juez|jueza|ministr[oa]|fiscal|defensor(?:a)?|"
    r"perit[oa]|m[eé]dic[oa]|psic[oó]log[oa]|asistente\s+social|"
    r"carabiner[oa]|sargento|cabo|teniente|capit[aá]n|comisari[oa]|"
    r"subcomisari[oa]|inspector(?:a)?|detective|suboficial|funcionari[oa])"
)

_ROLES_PROCESALES = (
    r"(?:imputad[oa]s?|acusad[oa]s?|condenad[oa]s?|sentenciad[oa]s?|"
    r"v[ií]ctimas?|ofendid[oa]s?|denunciante|denunciad[oa]|"
    r"querellante|querellad[oa]|testig[oa]s?|perit[oa]s?|"
    r"demandante|demandad[oa]|solicitante|requerid[oa]|requirente|"
    r"defendid[oa]|representad[oa]|compareciente|declarante|"
    r"recurrente|recurrid[oa]|apelante|adolescente|"
    r"beneficiari[oa]|alimentari[oa]|alimentante)"
)

# Nombre que comienza con iniciales: "J. I. Pérez Muñoz". Aparece sobre todo
# en firmas y en la individualización de peritos y funcionarios. Va primero en
# la alternativa porque, de lo contrario, la expresión capturaría solo los
# apellidos y las iniciales quedarían a la vista en el documento anonimizado.
_NOMBRE_CON_INICIALES = (
    rf"(?:[{_MAY}]\.\s*){{1,3}}"
    rf"{_PALABRA_TITULO}(?:\s+(?:{_PARTICULA}\s+)?{_PALABRA_TITULO}){{0,3}}"
)

# Cualquier forma de nombre propio: con iniciales, en mayúscula inicial o en
# versales.
_NOMBRE = (
    rf"(?:{_NOMBRE_CON_INICIALES}"
    rf"|{_PALABRA_TITULO}(?:\s+(?:{_PARTICULA}\s+)?{_PALABRA_TITULO}){{1,4}}"
    rf"|{_PALABRA_MAYUSCULA}(?:\s+(?:DE|DEL|LA|LAS|LOS|Y)\s+)?"
    rf"(?:\s*{_PALABRA_MAYUSCULA}){{1,4}})"
)


# =========================================================================
# Número de causa (RIT, RUC y ROL)
# =========================================================================

# Identificador con la forma "letra-número-año", que es la usual en Chile
# ("O-1234-2023", "C-567-2022"), y también sin letra ("1234-2023").
_ID_CAUSA = r"(?:[A-Z]\s*-\s*)?\d[\d\.]{0,8}\s*[-–/]\s*(?:19|20)\d{2}"

_RIT_RE = re.compile(_ci(r"\bR\.?\s?I\.?\s?T\.?") + rf"\s*{_NUM}({_ID_CAUSA})")

_RUC_ETIQUETADO_RE = re.compile(
    _ci(r"\bR\.?\s?U\.?\s?C\.?") + rf"\s*{_NUM}" + r"(\d{2}\s*-?\s*\d{8}\s*-\s*[0-9kK])"
)

# RUC sin etiqueta: diez dígitos y verificador. El formato es lo bastante
# característico como para no confundirse con otras cifras del expediente.
_RUC_SUELTO_RE = re.compile(r"\b(\d{10}\s*-\s*[0-9kK])\b")

_ROL_RE = re.compile(
    _ci(r"\b(?:R\.?\s?O\.?\s?L\.?|Rol)")
    + _ci(r"\s*(?:[uú]nico|de\s+ingreso|ingreso(?:\s+corte)?|corte)?")
    + rf"\s*{_NUM}({_ID_CAUSA})"
)

_CAUSA_GENERICA_RE = re.compile(
    _ci(
        r"\b(?:causa|expediente|carpeta\s+investigativa|ingreso\s+corte|"
        r"n[uú]mero\s+de\s+causa)"
    )
    + rf"\s*{_NUM}({_ID_CAUSA})"
)

# Identificador suelto "letra-número-año". Se acepta solo en modo exhaustivo
# porque, sin rótulo, puede coincidir con una referencia normativa.
_ID_CAUSA_SUELTO_RE = re.compile(r"\b([A-Z]\s*-\s*\d{1,6}\s*-\s*(?:19|20)\d{2})\b")


def _detectar_causa(texto: str, exhaustivo: bool) -> list[tuple[int, int, str, bool]]:
    """Devuelve (inicio, fin, valor, etiquetado) para cada número de causa."""
    hallazgos: list[tuple[int, int, str, bool]] = []

    for patron in (_RIT_RE, _RUC_ETIQUETADO_RE, _ROL_RE, _CAUSA_GENERICA_RE):
        for m in patron.finditer(texto):
            hallazgos.append((m.start(1), m.end(1), m.group(1).strip(), True))

    for m in _RUC_SUELTO_RE.finditer(texto):
        if validar_formato_ruc(m.group(1)):
            hallazgos.append((m.start(1), m.end(1), m.group(1).strip(), False))

    if exhaustivo:
        for m in _ID_CAUSA_SUELTO_RE.finditer(texto):
            hallazgos.append((m.start(1), m.end(1), m.group(1).strip(), False))

    return hallazgos


# =========================================================================
# RUT / Cédula de identidad
# =========================================================================

_ETIQUETA_RUT = (
    r"(?:R\.?\s?U\.?\s?T\.?|R\.?\s?U\.?\s?N\.?|"
    r"c[ée]dula(?:\s+(?:nacional\s+)?de\s+identidad)?|C\.?\s?I\.?|"
    r"rol\s+[uú]nico\s+(?:tributario|nacional)|documento\s+de\s+identidad)"
)

_RUT_ETIQUETADO_RE = re.compile(
    _ci(rf"\b{_ETIQUETA_RUT}") + rf"\s*{_NUM}" + r"(\d[\d\.]{5,11}\s*[-–]\s*[0-9kK])\b"
)

# RUT sin etiqueta, con o sin separadores de miles. Se exige que el dígito
# verificador calce, de modo que una cifra cualquiera no se tome por un RUT.
_RUT_SUELTO_RE = re.compile(r"\b(\d{1,3}(?:\.\d{3}){1,2}\s*[-–]\s*[0-9kK])\b")
_RUT_COMPACTO_RE = re.compile(r"\b(\d{7,8}\s*[-–]\s*[0-9kK])\b")


def _detectar_rut(texto: str) -> list[tuple[int, int, str, bool]]:
    hallazgos: list[tuple[int, int, str, bool]] = []

    for m in _RUT_ETIQUETADO_RE.finditer(texto):
        # Con rótulo explícito se acepta aunque el verificador no calce: un RUT
        # mal transcrito sigue identificando a una persona.
        hallazgos.append((m.start(1), m.end(1), m.group(1).strip(), True))

    for patron in (_RUT_SUELTO_RE, _RUT_COMPACTO_RE):
        for m in patron.finditer(texto):
            if validar_rut(m.group(1)):
                hallazgos.append((m.start(1), m.end(1), m.group(1).strip(), False))

    return hallazgos


# =========================================================================
# Correo electrónico
# =========================================================================

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+\s?@\s?[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")


# =========================================================================
# Teléfonos
# =========================================================================

_ETIQUETA_TELEFONO = (
    r"(?:tel[eé]fonos?|fonos?|celulares?|cel\.?|m[oó]vil|"
    r"whats?app|wsp|contacto|n[uú]mero\s+de\s+contacto)"
)

_TELEFONO_INTERNACIONAL_RE = re.compile(
    r"((?:\+\s?56|\(\s?\+?56\s?\))\s*\(?\s*\d{1,2}\s*\)?[\s\.\-]?\d{3,4}[\s\.\-]?\d{4})"
)

_TELEFONO_ETIQUETADO_RE = re.compile(
    _ci(rf"\b{_ETIQUETA_TELEFONO}")
    + rf"\s*{_NUM}"
    + r"((?:\+?\s?56\s*)?\(?\s?\d{1,2}\s?\)?[\s\.\-]?\d{3,4}[\s\.\-]?\d{4})"
)

# Numeración nacional con separadores: 9 8765 4321 / 22 234 5678 / 2 2234 5678
_TELEFONO_NACIONAL_RE = re.compile(
    r"\b(9[\s\.\-]\d{4}[\s\.\-]?\d{4}"
    r"|\(?\d{2}\)?[\s\.\-]\d{3}[\s\.\-]?\d{4}"
    r"|\(?\d\)?[\s\.\-]\d{4}[\s\.\-]?\d{4})\b"
)

# Nueve dígitos seguidos que comienzan con 9: formato frecuente al transcribir
# un celular. Solo se acepta en modo exhaustivo, por su ambigüedad.
_TELEFONO_COMPACTO_RE = re.compile(r"\b(9\d{8})\b")


def _detectar_telefono(texto: str, exhaustivo: bool) -> list[tuple[int, int, str, bool]]:
    hallazgos: list[tuple[int, int, str, bool]] = []

    for patron, etiquetado in (
        (_TELEFONO_INTERNACIONAL_RE, True),
        (_TELEFONO_ETIQUETADO_RE, True),
        (_TELEFONO_NACIONAL_RE, False),
    ):
        for m in patron.finditer(texto):
            if validar_telefono(m.group(1)):
                hallazgos.append((m.start(1), m.end(1), m.group(1).strip(), etiquetado))

    if exhaustivo:
        for m in _TELEFONO_COMPACTO_RE.finditer(texto):
            if validar_telefono(m.group(1)):
                hallazgos.append((m.start(1), m.end(1), m.group(1).strip(), False))

    return hallazgos


# =========================================================================
# Patentes de vehículos
# =========================================================================

_ETIQUETA_PATENTE = (
    r"(?:patente(?:\s+[uú]nica)?|placa(?:\s+patente)?(?:\s+[uú]nica)?|"
    r"P\.?\s?P\.?\s?U\.?|placa\s+de\s+circulaci[oó]n)"
)

_PATENTE_ETIQUETADA_RE = re.compile(
    _ci(rf"\b{_ETIQUETA_PATENTE}")
    + rf"\s*{_NUM}"
    + _ci(r"([A-Z]{2,4}\s*[·•\.\-]?\s*\d{2,4})")
    + r"\b"
)

# Formato vigente sin rótulo: cuatro letras del alfabeto restringido y dos
# dígitos. Es específico y prácticamente no aparece por azar en un escrito.
_PATENTE_ACTUAL_RE = re.compile(r"\b([BCDFGHJKLPRSTVWXYZ]{4}\s*[·•\.\-]?\s*\d{2})\b")

# Cualquier formato separado por punto medio: el signo es distintivo de las
# placas chilenas.
_PATENTE_PUNTO_MEDIO_RE = re.compile(r"\b([A-Z]{2,4}\s*[·•]\s*\d{2,4})\b")


def _detectar_patente(texto: str, preciso: bool = False) -> list[tuple[int, int, str, bool]]:
    hallazgos: list[tuple[int, int, str, bool]] = []

    for m in _PATENTE_ETIQUETADA_RE.finditer(texto):
        if validar_patente(m.group(1), con_etiqueta=True):
            hallazgos.append((m.start(1), m.end(1), m.group(1).strip(), True))

    # En modo preciso solo se admite el formato vigente sin rótulo, que es
    # inequívoco. El separado por punto medio queda fuera porque los formatos
    # antiguos pueden coincidir con siglas y numeraciones del propio escrito.
    patrones = (
        (_PATENTE_ACTUAL_RE,)
        if preciso
        else (_PATENTE_ACTUAL_RE, _PATENTE_PUNTO_MEDIO_RE)
    )
    for patron in patrones:
        for m in patron.finditer(texto):
            if validar_patente(m.group(1)):
                hallazgos.append((m.start(1), m.end(1), m.group(1).strip(), False))

    return hallazgos


# =========================================================================
# Domicilios
# =========================================================================

_VIA = (
    r"(?:calle|avenida|avda\.?|av\.?|pasaje|psje\.?|pje\.?|camino|ruta|"
    r"callej[oó]n|costanera|alameda|carretera|autopista|rotonda|plaza)"
)

_COMPLEMENTO = (
    r"(?:depto\.?|departamento|dpto\.?|of\.?|oficina|casa|block|blk\.?|"
    r"torre|piso|villa|poblaci[oó]n|pobl\.?|condominio|parcela|sitio|lote|"
    r"manzana|mz\.?|km\.?|kil[oó]metro|sector|fundo|loteo|local|"
    r"interior|letra)"
)

# El nombre de una vía chilena empieza con mayúscula o con un número
# ("Pasaje Los Aromos", "Avenida 5 de Abril"). Exigirlo, en lugar de enumerar
# las palabras que no deben seguir, evita el error de descartar direcciones
# reales cuyo nombre comienza por artículo: en Chile son numerosísimas —Los
# Aromos, Las Rosas, El Bosque— y una lista de palabras prohibidas las
# eliminaría todas.
_INICIO_NOMBRE_VIA = rf"[{_MAY}0-9]"
_RESTO_NOMBRE_VIA = rf"[{_MAY}{_MIN}0-9'\.\-]*"

_DOMICILIO_VIA_NUMERO_RE = re.compile(
    _ci(rf"\b{_VIA}")
    + r"\s+"
    + rf"{_INICIO_NOMBRE_VIA}{_RESTO_NOMBRE_VIA}"
    + rf"(?:\s+(?:{_PARTICULA}\s+)?{_INICIO_NOMBRE_VIA}{_RESTO_NOMBRE_VIA}){{0,4}}"
    + r"\s*"
    + _ci(r"(?:N[°ºo]\.?\s*)?")
    + r"\d{1,6}"
    + _ci(rf"(?:\s*,?\s*{_COMPLEMENTO}\s*[\wÁÉÍÓÚÑáéíóúñ°º\-]+){{0,3}}")
    + rf"(?:\s*,\s*(?:{_ci('comuna de')}\s+)?{_PALABRA_TITULO}"
    rf"(?:\s+{_PALABRA_TITULO}){{0,2}})?"
)

_DOMICILIO_NARRATIVO_RE = re.compile(
    _ci(
        r"\b(?:domiciliad[oa]s?|residente|reside|vive|habita|"
        r"con\s+domicilio(?:\s+\w+){0,3}|"
        r"domicilio(?:\s+(?:particular|real|laboral|comercial|convencional))?|"
        r"sit[oa]s?|ubicad[oa]s?)"
        r"\s+en\s+(?:la\s+|el\s+)?"
    )
    + r"(.{6,120}?)"
    + _ci(
        r"(?=(?:,\s*)?(?:y\s+|quien|el\s+cual|donde|seg[uú]n)|[;\.]\s|[;\.]$|\n|$)"
    )
)

_COMUNA_RE = re.compile(
    _ci(r"\bcomuna\s+de")
    + rf"\s+({_PALABRA_TITULO}(?:\s+(?:{_PARTICULA}\s+)?{_PALABRA_TITULO}){{0,3}})\b"
)

_VIA_SUELTA_RE = re.compile(rf"\b{_VIA}\b", re.IGNORECASE)
_COMPLEMENTO_SUELTO_RE = re.compile(rf"\b{_COMPLEMENTO}", re.IGNORECASE)


# Marcas que indican que la dirección terminó y comenzó el relato. La captura
# narrativa es necesariamente laxa —una dirección puede tener comas, números y
# nombres propios—, de modo que el recorte posterior es lo que impide que la
# detección se lleve consigo media oración.
_CORTE_DOMICILIO_RE = re.compile(
    r"\s*,?\s*\b(?:declar\w*|manifest\w*|se[nñ]al\w*|indic\w*|expres\w*|"
    r"refir\w*|refiere|agreg\w*|reconoc\w*|neg[oó]|nieg\w*|solicit\w*|"
    r"sostien\w*|sostuvo|afirm\w*|relat\w*|concurri\w*|se\s+encontr\w*|"
    r"quien|quienes|donde|el\s+cual|la\s+cual|seg[uú]n|conforme|mientras|"
    r"cuando|porque|ya\s+que|que\s)",
    re.IGNORECASE,
)

_LARGO_MAXIMO_DOMICILIO = 110


def _recortar_domicilio(cuerpo: str) -> str:
    """Corta la captura en el punto donde deja de ser una dirección."""
    corte = _CORTE_DOMICILIO_RE.search(cuerpo)
    if corte:
        cuerpo = cuerpo[: corte.start()]

    if len(cuerpo) > _LARGO_MAXIMO_DOMICILIO:
        ultima_coma = cuerpo.rfind(",", 0, _LARGO_MAXIMO_DOMICILIO)
        cuerpo = cuerpo[: ultima_coma if ultima_coma > 10 else _LARGO_MAXIMO_DOMICILIO]

    return cuerpo.strip(" ,.;:")


def _tiene_senal_de_direccion(valor: str) -> bool:
    """Una dirección real trae número, vía o complemento; una frase, no."""
    if re.search(r"\d", valor) and _VIA_SUELTA_RE.search(valor):
        return True
    if _COMPLEMENTO_SUELTO_RE.search(valor):
        return True
    return bool(_VIA_SUELTA_RE.search(valor) and "," in valor)


def _fusionar_tramos(
    texto: str, tramos: list[tuple[int, int, str]]
) -> list[tuple[int, int, str]]:
    """Une tramos contiguos para no partir una dirección en dos detecciones."""
    if not tramos:
        return []
    tramos.sort(key=lambda t: t[0])
    fusionados: list[tuple[int, int, str]] = [tramos[0]]
    for inicio, fin, _ in tramos[1:]:
        anterior_inicio, anterior_fin, _ = fusionados[-1]
        if inicio <= anterior_fin + 2:
            nuevo_fin = max(anterior_fin, fin)
            fusionados[-1] = (
                anterior_inicio,
                nuevo_fin,
                texto[anterior_inicio:nuevo_fin].strip(),
            )
        else:
            fusionados.append((inicio, fin, texto[inicio:fin].strip()))
    return fusionados


def _detectar_domicilio(texto: str, preciso: bool = False) -> list[tuple[int, int, str, bool]]:
    tramos: list[tuple[int, int, str]] = []

    for m in _DOMICILIO_VIA_NUMERO_RE.finditer(texto):
        valor = m.group(0).strip(" ,.;")
        if len(valor) > 6:
            tramos.append((m.start(), m.start() + len(valor), valor))

    for m in _DOMICILIO_NARRATIVO_RE.finditer(texto):
        cuerpo = _recortar_domicilio(m.group(1))
        if len(cuerpo) > 6 and _tiene_senal_de_direccion(cuerpo):
            inicio = m.start(1)
            tramos.append((inicio, inicio + len(cuerpo), cuerpo))

    for m in _COMUNA_RE.finditer(texto):
        tramos.append((m.start(), m.end(), m.group(0).strip()))

    fusionados = _fusionar_tramos(texto, tramos)

    if preciso:
        # Una dirección real trae numeración. Sin ella la captura suele ser el
        # nombre de un lugar, no el domicilio de nadie.
        fusionados = [t for t in fusionados if re.search(r"\d", t[2])]

    return [(i, f, v, True) for i, f, v in fusionados]


# =========================================================================
# Organizaciones
# =========================================================================

# Continuación admisible en el nombre de una organización: palabra con
# mayúscula inicial, versal, partícula, o numeral ordinal. Las minúsculas
# corrientes quedan fuera, que es lo que impide que la expresión se lleve por
# delante el verbo de la oración siguiente. El punto tampoco forma parte del
# vocablo: sin esa exclusión, "Carabineros de Chile. SEXTO:" se leería como un
# solo nombre y la detección invadiría el considerando siguiente.
_ORG_CONTINUACION = (
    rf"(?:{_ci(_PARTICULA)}|{_ci('(?:en|lo|al)')}|"
    rf"[{_MAY}][\w{_MIN}{_MAY}'\-]*|\d+[°ºa-z]*)"
)

# El separador excluye el salto de línea: el nombre de una organización no se
# reparte entre dos párrafos.
_ORG_SEPARADOR = r"[ \t]+"

_ORG_SUFIJO_RE = re.compile(
    rf"\b((?:[{_MAY}][\w{_MIN}{_MAY}&'\-\.]*\s+){{1,6}}{_ci(SUFIJOS_ORGANIZACION)})(?!\w)"
)

_ORG_PREFIJO_RE = re.compile(
    rf"\b({_ci(PREFIJOS_ORGANIZACION)}(?:{_ORG_SEPARADOR}{_ORG_CONTINUACION}){{1,7}})"
)

_ORG_SIGLA_RE = re.compile(
    r"\b(" + "|".join(re.escape(sigla) for sigla in SIGLAS_ORGANIZACION) + r")\b"
)

# Tribunales chilenos con numeral ordinal delante ("4° Tribunal de Juicio Oral
# en lo Penal de Santiago", "8° Juzgado de Garantía de Santiago").
_ORG_TRIBUNAL_ORDINAL_RE = re.compile(
    rf"\b(\d{{1,2}}\s*[°ºa-z]*{_ORG_SEPARADOR}{_ci('(?:Juzgado|Tribunal)')}"
    rf"(?:{_ORG_SEPARADOR}{_ORG_CONTINUACION}){{1,8}})"
)


def _detectar_organizacion(texto: str) -> list[tuple[int, int, str, bool]]:
    hallazgos: list[tuple[int, int, str, bool]] = []
    for patron in (
        _ORG_TRIBUNAL_ORDINAL_RE,
        _ORG_PREFIJO_RE,
        _ORG_SUFIJO_RE,
        _ORG_SIGLA_RE,
    ):
        for m in patron.finditer(texto):
            valor = m.group(1).strip(" ,.;")
            if len(valor) >= 3:
                hallazgos.append((m.start(1), m.start(1) + len(valor), valor, True))
    return hallazgos


# =========================================================================
# Personas
# =========================================================================

_PERSONA_TRATAMIENTO_RE = re.compile(
    _ci(rf"\b{_TRATAMIENTOS}") + rf"\s+({_NOMBRE})"
)

_PERSONA_ROL_RE = re.compile(
    _ci(rf"\b{_ROLES_PROCESALES}")
    + r"\s*[,:\.]?\s*"
    + _ci(rf"(?:{_TRATAMIENTOS}\s+)?")
    + rf"({_NOMBRE})"
)

# Nombre inmediatamente anterior a un RUT o a una cédula. Es la regla más
# valiosa para el control de sesgo: opera por contexto y no por diccionario, de
# modo que reconoce apellidos poco frecuentes con la misma eficacia que los
# habituales.
_PERSONA_ANTES_DE_RUT_RE = re.compile(
    rf"({_NOMBRE})\s*[,;\-–]?\s*" + _ci(rf"(?:{_ETIQUETA_RUT})\s*(?:N[°ºo]\.?)?\s*\d")
)

# Nombre presentado de forma explícita ("de nombre X", "individualizada como X").
_PERSONA_PRESENTACION_RE = re.compile(
    _ci(
        r"\b(?:de\s+nombre|llamad[oa]|individualizad[oa]\s+como|"
        r"identificad[oa]\s+como|responde\s+al\s+nombre\s+de)"
    )
    + rf"\s+({_NOMBRE})"
)

# Notación de encabezado: "APELLIDO PATERNO APELLIDO MATERNO, Nombres".
_PERSONA_APELLIDO_COMA_RE = re.compile(
    rf"\b([{_MAY}][{_MAY}{_MIN}]{{2,}}(?:\s+[{_MAY}][{_MAY}{_MIN}]{{2,}})?),\s+"
    rf"([{_MAY}][{_MAY}{_MIN}]{{2,}}(?:\s+[{_MAY}][{_MAY}{_MIN}]{{2,}}){{0,3}})\b"
)

# Nombre con inicial intermedia: "Juan P. Muñoz", "Juan I. Pérez Muñoz".
_PERSONA_INICIAL_RE = re.compile(
    rf"\b({_PALABRA_TITULO}\s+(?:[{_MAY}]\.\s*){{1,3}}"
    rf"{_PALABRA_TITULO}(?:\s+(?:{_PARTICULA}\s+)?{_PALABRA_TITULO}){{0,2}})\b"
)

# Nombre encabezado por iniciales: "J. I. Pérez Muñoz".
_PERSONA_INICIALES_PREFIJO_RE = re.compile(rf"\b({_NOMBRE_CON_INICIALES})\b")

_PERSONA_CAPITALIZADA_RE = re.compile(
    rf"\b({_PALABRA_TITULO}(?:\s+(?:{_PARTICULA}\s+)?{_PALABRA_TITULO}){{1,4}})\b"
)

_PERSONA_MAYUSCULAS_RE = re.compile(
    rf"\b({_PALABRA_MAYUSCULA}(?:\s+{_PALABRA_MAYUSCULA}){{1,4}})\b"
)

# Apellido aislado tras un rol procesal o un tratamiento ("la víctima Painemal
# declaró", "la señora Painemal ratificó"). En los escritos chilenos es
# frecuentísimo que, una vez individualizada la persona, se la mencione después
# solo por su apellido paterno; sin esta regla esas menciones posteriores
# quedarían sin anonimizar aunque la primera sí lo estuviera.
_PERSONA_APELLIDO_SOLO_RE = re.compile(
    _ci(rf"\b(?:{_ROLES_PROCESALES}|{_TRATAMIENTOS})")
    + _ci(rf"\s+(?:{_TRATAMIENTOS}\s+)?")
    + rf"([{_MAY}][{_MIN}]{{2,}})\b"
)

_CONECTOR_Y_RE = re.compile(r"\s+y\s+", re.IGNORECASE)


def _tiene_ancla_de_diccionario(valor: str) -> bool:
    """Indica si alguna palabra del candidato figura en los catálogos."""
    nombres = get_nombres()
    apellidos = get_apellidos()
    partes = [normalize_text(p) for p in valor.split() if len(p) > 1]
    return any(parte in nombres or parte in apellidos for parte in partes)


def tiene_nombre_y_apellido(valor: str) -> bool:
    """Indica si el candidato trae a la vez un nombre de pila y un apellido."""
    nombres = get_nombres()
    apellidos = get_apellidos()
    partes = [normalize_text(p) for p in valor.split() if len(p) > 1]
    return any(p in nombres for p in partes) and any(p in apellidos for p in partes)


def _tiene_formula_judicial(valor: str) -> bool:
    """Indica si el candidato está compuesto por vocabulario forense."""
    formulas = get_formulas()
    partes = [normalize_text(p) for p in valor.split() if len(p) > 1]
    if not partes:
        return True
    return any(parte in formulas or parte in STOPWORDS_FRASE for parte in partes)


# Verbos de dicción y de decisión con que suelen comenzar los párrafos de un
# escrito. Cuando anteceden a un nombre, la expresión regular los arrastra
# porque también están capitalizados; este recorte los devuelve al texto.
_VERBO_INICIAL_RE = re.compile(
    r"^(?:declar|manifest|se[nñ]al|indic|expres|refier|refir|agreg|reconoc|"
    r"nieg|neg|solicit|sostien|sostuv|afirm|relat|compareci|concurri|ratific|"
    r"depon|depus|dij|expus|a[nñ]ad|acompa[nñ]|aport|present|ratific|"
    r"resolvi|dispus|orden|conden|absolv|dict|consider|tuv|estim|conclu)"
    r"[a-záéíóúñ]*$",
    re.IGNORECASE,
)


def _recortar_encabezado_no_nominal(valor: str) -> str:
    """Quita del inicio las palabras que no pueden formar parte de un nombre.

    Una oración como "Declaró Kavinski Wolodarsky Trewhela" ofrece cuatro
    palabras capitalizadas seguidas, y la primera es un verbo. Sin este
    recorte, el filtro de calidad descartaría la mención entera por parecer
    narrativa y el nombre quedaría sin anonimizar, que es justamente el
    resultado que debe evitarse.
    """
    partes = valor.split()
    nombres, apellidos, formulas = get_nombres(), get_apellidos(), get_formulas()

    while len(partes) > 1:
        primera = normalize_text(partes[0])
        if primera in nombres or primera in apellidos:
            break
        if (
            primera in formulas
            or primera in STOPWORDS_FRASE
            or _VERBO_INICIAL_RE.match(primera)
        ):
            partes = partes[1:]
            continue
        break

    return " ".join(partes)


# Sufijo societario al final de un candidato a nombre de persona. Ocurre en
# razones sociales formadas con el nombre de su titular —"Juan Pérez Muñoz
# Ltda."—: la persona está ahí, pero el sufijo no forma parte de su nombre.
_SUFIJO_SOCIETARIO_FINAL_RE = re.compile(
    r"\s+(?:S\.?\s?A\.?|S\.?\s?p\.?\s?A\.?|Ltda\.?|Limitada|"
    r"E\.?\s?I\.?\s?R\.?\s?L\.?)$",
    re.IGNORECASE,
)


def _recortar_sufijo_societario(valor: str) -> str:
    """Quita el sufijo de sociedad que quede al final de un nombre de persona."""
    recortado = _SUFIJO_SOCIETARIO_FINAL_RE.sub("", valor).strip()
    return recortado if len(recortado.split()) >= 2 else valor


def _recortar_en_conector(valor: str) -> str:
    """Evita unir dos personas distintas: "Ana Soto y Luis Pérez"."""
    partido = _CONECTOR_Y_RE.split(valor, maxsplit=1)
    return partido[0].strip() if len(partido) > 1 else valor


# Tratamientos y roles que preceden al nombre y que el modelo de lenguaje
# suele incluir dentro de la entidad. No son datos personales y conviene
# devolverlos al texto: "La señora [PERSONA_1] ratificó" se lee mejor que
# "La [PERSONA_1] ratificó", y conserva la concordancia de la oración.
_ENCABEZADO_TRATAMIENTO_RE = re.compile(
    _ci(rf"^(?:{_TRATAMIENTOS}|{_ROLES_PROCESALES})\b[\s,\.:]*")
)


def recortar_nombre_de_persona(valor: str) -> tuple[str, int]:
    """Ajusta un nombre capturado y devuelve (nombre, desplazamiento inicial).

    El desplazamiento permite corregir la posición de la mención en el
    documento: sin él, la sustitución quedaría desalineada respecto del texto.
    """
    original = valor
    recortado = valor.strip()
    desplazamiento = original.index(recortado) if recortado in original else 0

    while True:
        coincidencia = _ENCABEZADO_TRATAMIENTO_RE.match(recortado)
        if not coincidencia or coincidencia.end() >= len(recortado):
            break
        desplazamiento += coincidencia.end()
        recortado = recortado[coincidencia.end():]

    previo = recortado
    recortado = _recortar_encabezado_no_nominal(recortado)
    if recortado != previo:
        desplazamiento += previo.index(recortado) if recortado in previo else 0

    recortado = _recortar_sufijo_societario(recortado)
    return recortado.strip(" ,.;:"), desplazamiento


def _detectar_persona(
    texto: str, exhaustivo: bool, preciso: bool = False
) -> list[tuple[int, int, str, bool]]:
    hallazgos: list[tuple[int, int, str, bool]] = []

    def agregar(valor: str, inicio: int, etiquetado: bool) -> None:
        limpio = _recortar_encabezado_no_nominal(valor.strip(" ,.;:"))
        limpio = _recortar_en_conector(limpio)
        limpio = _recortar_sufijo_societario(limpio)
        if len(limpio) < 3:
            return
        desplazamiento = valor.index(limpio) if limpio in valor else 0
        hallazgos.append(
            (inicio + desplazamiento, inicio + desplazamiento + len(limpio), limpio, etiquetado)
        )

    # 1. Reglas de contexto: no dependen del diccionario y son, por eso, las
    #    que igualan la detección entre apellidos frecuentes y poco frecuentes.
    for patron in (
        _PERSONA_ANTES_DE_RUT_RE,
        _PERSONA_TRATAMIENTO_RE,
        _PERSONA_ROL_RE,
        _PERSONA_PRESENTACION_RE,
    ):
        for m in patron.finditer(texto):
            valor = m.group(1)
            if _tiene_formula_judicial(valor) and not _tiene_ancla_de_diccionario(valor):
                continue
            agregar(valor, m.start(1), True)

    for m in _PERSONA_APELLIDO_SOLO_RE.finditer(texto):
        apellido = m.group(1)
        normalizado = normalize_text(apellido)
        if normalizado in get_formulas() or normalizado in STOPWORDS_FRASE:
            continue
        if normalizado in get_apellidos() or normalizado in get_nombres() or exhaustivo:
            agregar(apellido, m.start(1), True)

    # 2. Encabezado "APELLIDOS, Nombres".
    for m in _PERSONA_APELLIDO_COMA_RE.finditer(texto):
        completo = m.group(0)
        if _tiene_formula_judicial(completo):
            continue
        if not _tiene_ancla_de_diccionario(completo):
            continue
        agregar(completo, m.start(), False)

    # 3. Nombre con inicial intermedia o encabezado por iniciales. En el
    #    segundo caso se exige ancla en el catálogo, porque el patrón coincide
    #    también con abreviaturas normativas del tipo "C. Penal".
    for m in _PERSONA_INICIAL_RE.finditer(texto):
        if _tiene_formula_judicial(m.group(1)):
            continue
        agregar(m.group(1), m.start(1), False)

    for m in _PERSONA_INICIALES_PREFIJO_RE.finditer(texto):
        candidato = m.group(1)
        if _tiene_formula_judicial(candidato):
            continue
        if not _tiene_ancla_de_diccionario(candidato):
            continue
        agregar(candidato, m.start(1), False)

    # 4. Secuencias capitalizadas con ancla en el diccionario. Es la única
    #    regla que depende del catálogo, y por eso la que el modo preciso
    #    endurece: exige que el candidato traiga a la vez un nombre de pila y
    #    un apellido conocidos, en lugar de cualquiera de los dos.
    for patron in (_PERSONA_CAPITALIZADA_RE, _PERSONA_MAYUSCULAS_RE):
        for m in patron.finditer(texto):
            candidato = m.group(1)
            if _tiene_formula_judicial(candidato):
                continue
            if preciso:
                if not tiene_nombre_y_apellido(candidato):
                    continue
            elif not _tiene_ancla_de_diccionario(candidato):
                continue
            agregar(candidato, m.start(1), False)

    return hallazgos


# =========================================================================
# Otros datos sensibles
# =========================================================================

_OTRO_PATRONES: tuple[tuple[str, str], ...] = (
    # Número Único de Evidencia: identificador de la cadena de custodia.
    ("nue", _ci(r"\bN\.?\s?U\.?\s?E\.?") + rf"\s*{_NUM}" + r"(\d{4,12})\b"),
    ("pasaporte", _ci(r"\bpasaportes?") + rf"\s*{_NUM}" + r"([A-Z0-9][A-Z0-9\-]{4,14})\b"),
    (
        "serie_cedula",
        _ci(r"\b(?:n[uú]mero\s+de\s+)?serie") + rf"\s*{_NUM}" + r"([A-Z0-9][A-Z0-9\.\-]{4,14})\b",
    ),
    ("imei", _ci(r"\bI\.?\s?M\.?\s?E\.?\s?I\.?") + rf"\s*{_NUM}" + r"(\d{14,16})\b"),
    (
        "cuenta_bancaria",
        _ci(r"\bcuenta\s+(?:corriente|vista|de\s+ahorro|rut|bancaria)")
        + rf"\s*{_NUM}"
        + r"(\d[\d\.\-]{5,20})\b",
    ),
    ("tarjeta", r"\b((?:\d{4}[\s\-]){3}\d{4})\b"),
    (
        "licencia",
        _ci(r"\blicencia\s+de\s+conducir(?:\s+clase\s+[A-E]-?\d?)?")
        + rf"\s*{_NUM}"
        + r"(\d[\d\.\-]{5,15})\b",
    ),
    (
        "ficha_clinica",
        _ci(r"\bficha\s+(?:cl[ií]nica|m[eé]dica)") + rf"\s*{_NUM}" + r"(\d{3,12})\b",
    ),
    (
        "parte_policial",
        _ci(r"\b(?:parte|denuncia)\s+(?:policial|N[°º])?") + rf"\s*{_NUM}" + r"(\d{2,10})\b",
    ),
    ("folio", _ci(r"\bfolios?") + rf"\s*{_NUM}" + r"(\d{3,12})\b"),
    ("ip", r"\b((?:\d{1,3}\.){3}\d{1,3})\b"),
    ("url", r"(https?://[^\s<>\"]{4,200})"),
    ("usuario_red", r"(?<![\w@])(@[A-Za-z0-9_\.]{3,30})\b"),
    (
        "fecha_nacimiento",
        _ci(r"\b(?:nacid[oa]\s+el|fecha\s+de\s+nacimiento)")
        + r"\s*[:,]?\s*"
        + _ci(
            rf"(\d{{1,2}}\s*(?:de\s+{_MESES}\s+de|[/\-\.])\s*\d{{1,4}}"
            r"(?:\s*[/\-\.]\s*\d{2,4})?)"
        ),
    ),
)

_OTRO_COMPILADOS = tuple(
    (nombre, re.compile(patron)) for nombre, patron in _OTRO_PATRONES
)


def _ip_valida(valor: str) -> bool:
    partes = valor.split(".")
    if len(partes) != 4:
        return False
    try:
        return all(0 <= int(parte) <= 255 for parte in partes)
    except ValueError:
        return False


# Patrones de "Otros sensibles" que no llevan rótulo delante y se reconocen
# solo por su forma. Son los más expuestos a coincidir por azar con una cifra
# del escrito, de modo que el modo preciso prescinde de ellos.
_OTRO_SIN_ROTULO = frozenset({"tarjeta", "ip", "usuario_red"})


def _detectar_otro(texto: str, preciso: bool = False) -> list[tuple[int, int, str, bool]]:
    hallazgos: list[tuple[int, int, str, bool]] = []
    for nombre, patron in _OTRO_COMPILADOS:
        if preciso and nombre in _OTRO_SIN_ROTULO:
            continue
        for m in patron.finditer(texto):
            valor = m.group(1).strip()
            if not valor:
                continue
            if nombre == "ip" and not _ip_valida(valor):
                continue
            hallazgos.append((m.start(1), m.start(1) + len(valor), valor, True))
    return hallazgos


# =========================================================================
# Orquestación
# =========================================================================

# Orden de prioridad ante solapamientos. Las categorías con validación
# estructural van primero porque su detección es la más confiable.
PRIORIDAD_CATEGORIAS = (
    "CAUSA",
    "RUT",
    "EMAIL",
    "TELEFONO",
    "PATENTE",
    "OTRO",
    "DOMICILIO",
    "ORGANIZACION",
    "PERSONA",
)


def detect_regex_cl(texto: str, sensibilidad: str = "exhaustiva") -> list[RawItem]:
    """Aplica todos los detectores determinísticos sobre el texto."""
    exhaustivo = sensibilidad == "exhaustiva"
    preciso = sensibilidad == "precisa"

    por_categoria: dict[str, list[tuple[int, int, str, bool]]] = {
        "CAUSA": _detectar_causa(texto, exhaustivo),
        "RUT": _detectar_rut(texto),
        "EMAIL": [
            (m.start(), m.end(), m.group(0).strip(), True)
            for m in _EMAIL_RE.finditer(texto)
        ],
        "TELEFONO": _detectar_telefono(texto, exhaustivo),
        "PATENTE": _detectar_patente(texto, preciso),
        "OTRO": _detectar_otro(texto, preciso),
        "DOMICILIO": _detectar_domicilio(texto, preciso),
        "ORGANIZACION": _detectar_organizacion(texto),
        "PERSONA": _detectar_persona(texto, exhaustivo, preciso),
    }

    items: list[RawItem] = []
    for categoria in PRIORIDAD_CATEGORIAS:
        for inicio, fin, valor, etiquetado in por_categoria.get(categoria, []):
            if fin <= inicio or not valor.strip():
                continue
            items.append(
                RawItem(
                    cat=categoria,
                    original=valor,
                    start=inicio,
                    end=fin,
                    source_layer="regex",
                    score=0.95 if etiquetado else 0.8,
                    etiquetado=etiquetado,
                )
            )

    return items
