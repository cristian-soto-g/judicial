"""Exportación a texto plano.

Módulo propio de esta obra derivada: la aplicación original no exportaba texto
plano. Es el formato más seguro para trasladar el contenido a otra herramienta,
porque no arrastra metadatos ni contenido oculto del documento de origen.
"""
from __future__ import annotations


def build_txt_bytes(texto: str) -> bytes:
    contenido = (texto or "").replace("\r\n", "\n").strip()
    return (contenido + "\n").encode("utf-8")
