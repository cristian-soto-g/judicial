"""Lectura de archivos de texto plano.

Módulo propio de esta obra derivada: la aplicación original no admitía texto
plano. La detección de codificación es deliberadamente conservadora — se
prueban las codificaciones habituales en documentos chilenos y, como último
recurso, se decodifica con reemplazo antes que rechazar el archivo.
"""
from __future__ import annotations

CODIFICACIONES = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


def extract_txt(data: bytes) -> str:
    """Devuelve el texto del archivo, probando codificaciones habituales."""
    if not data.strip():
        raise ValueError("El archivo de texto está vacío.")

    for codificacion in CODIFICACIONES:
        try:
            texto = data.decode(codificacion)
        except (UnicodeDecodeError, LookupError):
            continue
        return _normalizar(texto)

    # Ninguna codificación funcionó de forma limpia: se decodifica con
    # reemplazo para no perder el documento completo por unos pocos bytes.
    return _normalizar(data.decode("utf-8", errors="replace"))


def _normalizar(texto: str) -> str:
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    texto = texto.replace("\x00", "")
    resultado = texto.strip()
    if not resultado:
        raise ValueError("El archivo de texto no contiene contenido legible.")
    return resultado
