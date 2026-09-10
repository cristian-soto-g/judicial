"""Validadores determinísticos de identificadores chilenos.

Módulo propio de esta obra derivada. Reemplaza la validación de CUIT y DNI
argentinos de la aplicación original por la de los identificadores chilenos.

La validación estructural cumple aquí un papel de control de calidad: permite
distinguir un RUT real de una cifra cualquiera con formato parecido, lo que
reduce los falsos positivos sin sacrificar detección.
"""
from __future__ import annotations

import re

# --- RUT / Cédula de identidad -------------------------------------------

_SERIE_RUT = (2, 3, 4, 5, 6, 7)


def calcular_dv(cuerpo: str | int) -> str:
    """Calcula el dígito verificador de un RUT según el algoritmo módulo 11."""
    digitos = re.sub(r"\D", "", str(cuerpo))
    if not digitos:
        raise ValueError("El cuerpo del RUT no contiene dígitos.")

    suma = 0
    for posicion, digito in enumerate(reversed(digitos)):
        suma += int(digito) * _SERIE_RUT[posicion % len(_SERIE_RUT)]

    resto = 11 - (suma % 11)
    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)


def normalizar_rut(rut: str) -> str:
    """Devuelve el RUT sin puntos, sin guion y con el verificador en mayúscula."""
    limpio = re.sub(r"[^0-9kK]", "", rut or "")
    return limpio.upper()


def validar_rut(rut: str) -> bool:
    """Indica si el RUT es estructuralmente válido y su verificador coincide."""
    limpio = normalizar_rut(rut)
    if len(limpio) < 7 or len(limpio) > 9:
        return False

    cuerpo, dv = limpio[:-1], limpio[-1]
    if not cuerpo.isdigit():
        return False
    if int(cuerpo) < 1_000_000:
        # Los RUT vigentes de personas naturales superan holgadamente el millón.
        # Exigirlo evita que cifras cortas del texto se tomen por identificadores.
        return False

    try:
        return calcular_dv(cuerpo) == dv
    except ValueError:
        return False


def formatear_rut(rut: str) -> str:
    """Devuelve el RUT en el formato habitual 12.345.678-9."""
    limpio = normalizar_rut(rut)
    if len(limpio) < 2:
        return rut
    cuerpo, dv = limpio[:-1], limpio[-1]
    partes: list[str] = []
    while len(cuerpo) > 3:
        partes.insert(0, cuerpo[-3:])
        cuerpo = cuerpo[:-3]
    if cuerpo:
        partes.insert(0, cuerpo)
    return f"{'.'.join(partes)}-{dv}"


# --- Rol Único de Causa (RUC) --------------------------------------------

_RUC_RE = re.compile(r"^(\d{2})[-\s]*(\d{8})[-\s]*([0-9kK])$")


def validar_formato_ruc(ruc: str) -> bool:
    """Verifica la estructura de un RUC: dos dígitos de año, ocho de serie y verificador.

    Deliberadamente no se comprueba el dígito verificador. El algoritmo con que
    el Ministerio Público lo calcula no está publicado de manera oficial y
    verificable, y rechazar un RUC legítimo por una suposición equivocada
    dejaría un dato identificatorio sin anonimizar. Ante la duda, se prefiere
    detectar de más y que la revisión humana descarte.
    """
    limpio = re.sub(r"[^0-9kK\-\s]", "", ruc or "").strip()
    coincidencia = _RUC_RE.match(limpio)
    if not coincidencia:
        return False

    anio = int(coincidencia.group(1))
    # El RUC comenzó a usarse con la reforma procesal penal, en el año 2000.
    return 0 <= anio <= 99


# --- Patentes de vehículos ------------------------------------------------

# Las patentes chilenas emitidas desde 2007 usan un alfabeto restringido: se
# excluyen las vocales y las letras M, N y Q para evitar confusiones de lectura.
LETRAS_PATENTE = "BCDFGHJKLPRSTVWXYZ"

_PATENTE_AUTO_ACTUAL = re.compile(
    rf"^[{LETRAS_PATENTE}]{{4}}\d{{2}}$", re.IGNORECASE
)
_PATENTE_MOTO_ACTUAL = re.compile(
    rf"^[{LETRAS_PATENTE}]{{3}}\d{{2}}$", re.IGNORECASE
)
_PATENTE_ANTIGUA = re.compile(r"^[A-Z]{2}\d{4}$", re.IGNORECASE)
_PATENTE_LAXA = re.compile(r"^[A-Z]{2,4}\d{2,4}$", re.IGNORECASE)


def compactar_patente(valor: str) -> str:
    """Quita separadores (punto medio, guion, punto y espacios) y normaliza."""
    return re.sub(r"[\s\.\-·•]", "", valor or "").upper()


def validar_patente(valor: str, con_etiqueta: bool = False) -> bool:
    """Valida una patente chilena.

    Cuando el texto trae una etiqueta explícita ("patente", "placa patente",
    "PPU") se acepta un patrón más amplio, porque la etiqueta ya aporta la
    evidencia que de otro modo debería aportar el formato.
    """
    compacta = compactar_patente(valor)
    if not compacta:
        return False

    if _PATENTE_AUTO_ACTUAL.match(compacta) or _PATENTE_MOTO_ACTUAL.match(compacta):
        return True

    if con_etiqueta:
        return bool(_PATENTE_LAXA.match(compacta))

    return bool(_PATENTE_ANTIGUA.match(compacta))


# --- Teléfonos ------------------------------------------------------------

# Primer dígito de la numeración nacional: 9 para móviles y 2 a 7 para la red
# fija y los servicios de valor agregado.
_PRIMEROS_DIGITOS_VALIDOS = frozenset("234567 9".replace(" ", ""))


def digitos_telefono(valor: str) -> str:
    """Devuelve solo los dígitos del teléfono, descartando el prefijo 56."""
    digitos = re.sub(r"\D", "", valor or "")
    if digitos.startswith("56") and len(digitos) == 11:
        return digitos[2:]
    if digitos.startswith("056") and len(digitos) == 12:
        return digitos[3:]
    return digitos


def validar_telefono(valor: str) -> bool:
    """Valida un teléfono chileno de nueve dígitos, con o sin prefijo país."""
    nacional = digitos_telefono(valor)
    if len(nacional) != 9:
        return False
    if nacional[0] not in _PRIMEROS_DIGITOS_VALIDOS:
        return False
    # Un número compuesto por un solo dígito repetido casi siempre es un dato
    # de relleno o un error de digitación, no un teléfono real.
    return len(set(nacional)) > 2


def es_movil(valor: str) -> bool:
    nacional = digitos_telefono(valor)
    return len(nacional) == 9 and nacional.startswith("9")
