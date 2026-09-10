"""Lectura de PDF con capa de texto, sin reconocimiento óptico.

Basado en el extractor de PDF del Anonimizador Judicial de IALAB — Facultad de
Derecho, UBA (Apache 2.0). Modificado: la función informa explícitamente
cuántas páginas quedaron fuera por carecer de texto seleccionable. Ese aviso es
deliberado: un PDF escaneado que se procesara en silencio produciría un
documento en apariencia anonimizado pero en realidad intacto, que es el peor
resultado posible cuando se trabaja con información sensible.
"""
from __future__ import annotations

import io
import logging

import pdfplumber

from app.extraction.pdf_cleanup import clean_pdf_text, merge_lines_to_paragraphs

logger = logging.getLogger(__name__)

MINIMO_CARACTERES = 15


def extract_pdf_con_aviso(data: bytes) -> tuple[str, str]:
    """Extrae la capa de texto del PDF y devuelve (texto, aviso)."""
    partes: list[str] = []
    paginas_sin_texto = 0

    with pdfplumber.open(io.BytesIO(data)) as documento:
        total_paginas = len(documento.pages)
        for pagina in documento.pages:
            texto_pagina = (pagina.extract_text() or "").strip()
            if not texto_pagina:
                paginas_sin_texto += 1
                continue
            limpio = clean_pdf_text(texto_pagina)
            partes.append(merge_lines_to_paragraphs(limpio))

    texto = "\n\n".join(parte for parte in partes if parte).strip()

    if not texto:
        raise ValueError(
            "Este PDF no tiene texto seleccionable: probablemente sea un "
            "escaneo. Esta aplicación no incluye reconocimiento óptico de "
            "caracteres, de modo que no puede procesarlo. Utilice el documento "
            "en Word (.docx) o un PDF exportado con capa de texto."
        )

    if len(texto) < MINIMO_CARACTERES:
        raise ValueError(
            "El PDF contiene muy poco texto seleccionable. Verifique que no se "
            "trate de un escaneo o de un archivo dañado."
        )

    aviso = ""
    if paginas_sin_texto:
        logger.info(
            "PDF mixto: %d de %d páginas sin texto seleccionable.",
            paginas_sin_texto,
            total_paginas,
        )
        aviso = (
            f"Atención: {paginas_sin_texto} de {total_paginas} páginas de este "
            "PDF no tienen texto seleccionable y quedaron fuera del análisis. "
            "Si esas páginas contienen datos personales, no serán anonimizadas. "
            "Revíselas por separado antes de compartir el documento."
        )

    return texto, aviso


def extract_pdf(data: bytes) -> str:
    """Variante que descarta el aviso; se conserva por comodidad en pruebas."""
    texto, _ = extract_pdf_con_aviso(data)
    return texto
