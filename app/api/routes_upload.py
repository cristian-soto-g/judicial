"""Carga de documentos."""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import MAX_UPLOAD_BYTES
from app.extraction import extraer_documento
from app.models.schemas import UploadResponse
from app.models.store import store

router = APIRouter(prefix="/api", tags=["carga"])


@router.post("/cargar", response_model=UploadResponse)
async def cargar_documento(file: UploadFile = File(...)):
    """Lee el documento y abre una sesión de trabajo en memoria."""
    if not file.filename:
        raise HTTPException(400, "Debe indicar un archivo.")

    datos = await file.read()
    if not datos:
        raise HTTPException(400, "El archivo está vacío.")

    if len(datos) > MAX_UPLOAD_BYTES:
        limite = MAX_UPLOAD_BYTES // (1024 * 1024)
        raise HTTPException(
            413,
            f"El archivo supera el límite de {limite} MB. Divídalo o reduzca su "
            "tamaño antes de cargarlo.",
        )

    try:
        resultado = extraer_documento(file.filename, datos)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except Exception as error:
        raise HTTPException(500, f"No se pudo leer el archivo: {error}") from error

    session_id = store.create()
    estado = store.get(session_id)
    assert estado is not None

    estado.doc_name = file.filename.rsplit(".", 1)[0]
    estado.doc_text = resultado.texto
    estado.doc_paragraphs = [p for p in resultado.texto.split("\n\n") if p.strip()]
    estado.aviso_extraccion = resultado.aviso
    store.save(estado)

    return UploadResponse(
        session_id=session_id,
        doc_name=estado.doc_name,
        char_count=len(resultado.texto),
        paragraph_count=len(estado.doc_paragraphs),
        aviso=resultado.aviso,
    )
