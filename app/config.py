"""Configuración de la aplicación.

Basado en el módulo homónimo del Anonimizador Judicial de IALAB — Facultad de
Derecho, UBA (Apache 2.0). Modificado: se agregaron los parámetros de
sensibilidad de detección y de reversibilidad, y se desactivaron por defecto
las capas de lenguaje natural, que aquí son opcionales.
"""
from __future__ import annotations

import os
from pathlib import Path

from app.runtime_paths import app_dir, bundle_dir

# --- Servidor -----------------------------------------------------------
# La aplicación se sirve exclusivamente en la interfaz de loopback: no queda
# accesible desde la red local ni desde internet.
HOST = "127.0.0.1"
PORT = 8799
APP_VERSION = "1.0.0"
APP_NAME = "Anonimizador Judicial Chile"

BUNDLE_DIR = bundle_dir()


def _resolve_frontend_dir() -> Path:
    """Resuelve la carpeta del frontend: variable de entorno, disco o paquete."""
    env = os.environ.get("ANON_FRONTEND_DIR", "").strip()
    if env:
        path = Path(env).expanduser().resolve()
        if (path / "index.html").exists():
            return path
    overlay = app_dir() / "frontend"
    if (overlay / "index.html").exists():
        return overlay
    return BUNDLE_DIR / "frontend"


FRONTEND_DIR = _resolve_frontend_dir()

# Recursos de solo lectura (diccionarios de nombres, apellidos y fórmulas).
RESOURCE_DATA_DIR = BUNDLE_DIR / "data"
DATA_DIR = app_dir() / "data"

# --- Límites --------------------------------------------------------------
MAX_UPLOAD_BYTES = 40 * 1024 * 1024  # 40 MB

# --- Resolución de identidades -------------------------------------------
FUZZY_HIGH = 92
FUZZY_MEDIUM = 85
PROXIMITY_CHARS = 200

# --- Capas de lenguaje natural (opcionales) ------------------------------
# Se activan solo si spaCy y su modelo en español están instalados. Su ausencia
# no impide el funcionamiento: la detección determinística opera igual.
ENABLE_SPACY = os.environ.get("ANON_ENABLE_SPACY", "1") not in ("0", "false", "False")

# --- Sensibilidad de la detección ----------------------------------------
# "exhaustiva"  : privilegia no dejar pasar datos personales, a costa de más
#                 falsos positivos. Es el modo por defecto porque un falso
#                 positivo se corrige en la revisión, mientras que un dato no
#                 detectado se publica.
# "equilibrada" : compromiso entre exhaustividad y precisión.
# "precisa"     : minimiza falsos positivos; exige más evidencia por detección.
SENSIBILIDAD_POR_DEFECTO = "exhaustiva"
SENSIBILIDADES = ("exhaustiva", "equilibrada", "precisa")

# --- Reversibilidad -------------------------------------------------------
# Parámetros de derivación de clave para el mapa de correspondencias cifrado.
# scrypt con estos valores exige ~64 MB de memoria por intento, lo que encarece
# de forma considerable un ataque por fuerza bruta sobre la frase de paso.
SCRYPT_N = 2**16
SCRYPT_R = 8
SCRYPT_P = 1
MAPA_EXTENSION = ".anonmap"
MAPA_FORMATO = "anonmap/1"
