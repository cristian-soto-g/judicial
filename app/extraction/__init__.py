"""Lectura de documentos: texto plano, Word y PDF con capa de texto."""
from app.extraction.docx import extract_docx
from app.extraction.pdf import extract_pdf
from app.extraction.txt import extract_txt
from app.extraction.reader import ResultadoExtraccion, extraer_documento

__all__ = [
    "ResultadoExtraccion",
    "extraer_documento",
    "extract_docx",
    "extract_pdf",
    "extract_txt",
]
