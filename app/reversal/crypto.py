"""Cifrado del mapa de correspondencias.

Módulo propio de esta obra derivada: la aplicación original no contemplaba
reversibilidad.

Justificación del diseño. El mapa que permite deshacer la anonimización es, por
definición, el archivo más sensible de todo el flujo: concentra la totalidad de
los datos personales del documento junto con la clave para reubicarlos en él.
Por eso no se guarda nunca en claro y la frase de paso no se conserva en
ninguna parte —ni en memoria más allá de la operación, ni en disco, ni en la
sesión—. La consecuencia es deliberada y debe advertirse al usuario: si pierde
la frase de paso, la reversión es imposible.

Esquema criptográfico:

  * Derivación de clave: scrypt (N=2^16, r=8, p=1), que exige alrededor de
    64 MB de memoria por intento y encarece de manera sustantiva un ataque por
    fuerza bruta sobre la frase de paso.
  * Cifrado: AES-256 en modo GCM, que aporta confidencialidad y autenticación:
    un archivo alterado no se descifra, falla de manera explícita.
  * Los parámetros públicos (versión, sal, algoritmo) viajan como datos
    autenticados adicionales, de modo que tampoco pueden manipularse.
"""
from __future__ import annotations

import base64
import json
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from app.config import MAPA_FORMATO, SCRYPT_N, SCRYPT_P, SCRYPT_R

LONGITUD_SAL = 16
LONGITUD_NONCE = 12
LONGITUD_CLAVE = 32
LARGO_MINIMO_FRASE = 12


class ErrorCifrado(Exception):
    """Falla al cifrar o descifrar el mapa de correspondencias."""


def _b64(datos: bytes) -> str:
    return base64.b64encode(datos).decode("ascii")


def _de_b64(texto: str) -> bytes:
    return base64.b64decode(texto.encode("ascii"))


def _derivar_clave(passphrase: str, sal: bytes) -> bytes:
    kdf = Scrypt(salt=sal, length=LONGITUD_CLAVE, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P)
    return kdf.derive(passphrase.encode("utf-8"))


def validar_frase(passphrase: str) -> None:
    """Rechaza frases de paso demasiado cortas para proteger el mapa."""
    if not passphrase or len(passphrase) < LARGO_MINIMO_FRASE:
        raise ErrorCifrado(
            f"La frase de paso debe tener al menos {LARGO_MINIMO_FRASE} "
            "caracteres. Se recomienda una frase larga y memorable antes que "
            "una contraseña corta y compleja."
        )


def cifrar(datos: bytes, passphrase: str) -> dict:
    """Cifra el contenido y devuelve el sobre con sus parámetros públicos."""
    validar_frase(passphrase)

    sal = os.urandom(LONGITUD_SAL)
    nonce = os.urandom(LONGITUD_NONCE)
    clave = _derivar_clave(passphrase, sal)

    cabecera = {
        "formato": MAPA_FORMATO,
        "cifrado": "AES-256-GCM",
        "derivacion": "scrypt",
        "scrypt_n": SCRYPT_N,
        "scrypt_r": SCRYPT_R,
        "scrypt_p": SCRYPT_P,
        "sal": _b64(sal),
        "nonce": _b64(nonce),
    }
    autenticados = json.dumps(cabecera, sort_keys=True).encode("utf-8")

    try:
        contenido = AESGCM(clave).encrypt(nonce, datos, autenticados)
    except Exception as error:  # pragma: no cover - falla del entorno
        raise ErrorCifrado(f"No se pudo cifrar el mapa: {error}") from error

    return {**cabecera, "contenido": _b64(contenido)}


def descifrar(sobre: dict, passphrase: str) -> bytes:
    """Descifra el sobre y verifica su integridad."""
    if not isinstance(sobre, dict):
        raise ErrorCifrado("El archivo del mapa no tiene el formato esperado.")

    if sobre.get("formato") != MAPA_FORMATO:
        raise ErrorCifrado(
            "El archivo no corresponde a un mapa de reversión de esta "
            "aplicación, o fue generado con una versión incompatible."
        )

    try:
        sal = _de_b64(sobre["sal"])
        nonce = _de_b64(sobre["nonce"])
        contenido = _de_b64(sobre["contenido"])
        parametros = {
            "n": int(sobre.get("scrypt_n", SCRYPT_N)),
            "r": int(sobre.get("scrypt_r", SCRYPT_R)),
            "p": int(sobre.get("scrypt_p", SCRYPT_P)),
        }
    except (KeyError, ValueError, TypeError) as error:
        raise ErrorCifrado("El archivo del mapa está incompleto o dañado.") from error

    cabecera = {
        clave: sobre[clave]
        for clave in (
            "formato",
            "cifrado",
            "derivacion",
            "scrypt_n",
            "scrypt_r",
            "scrypt_p",
            "sal",
            "nonce",
        )
        if clave in sobre
    }
    autenticados = json.dumps(cabecera, sort_keys=True).encode("utf-8")

    kdf = Scrypt(
        salt=sal,
        length=LONGITUD_CLAVE,
        n=parametros["n"],
        r=parametros["r"],
        p=parametros["p"],
    )
    clave = kdf.derive(passphrase.encode("utf-8"))

    try:
        return AESGCM(clave).decrypt(nonce, contenido, autenticados)
    except InvalidTag as error:
        raise ErrorCifrado(
            "No fue posible descifrar el mapa. La frase de paso es incorrecta o "
            "el archivo fue alterado. Recuerde que la frase no se guarda en "
            "ninguna parte: si la perdió, la reversión no es posible."
        ) from error
