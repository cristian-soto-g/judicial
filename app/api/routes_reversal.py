"""Reversibilidad: generación del mapa cifrado y restitución del documento.

Rutas propias de esta obra derivada.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.config import MAPA_EXTENSION, MAX_UPLOAD_BYTES
from app.export.docx_export import build_docx_bytes
from app.export.export_utils import texto_a_parrafos
from app.export.http_headers import content_disposition_attachment
from app.export.txt_export import build_txt_bytes
from app.extraction import extraer_documento
from app.models.schemas import MapaRequest, RevertirResponse
from app.models.store import store
from app.reversal.mapping import ErrorMapa, generar_mapa_cifrado, leer_mapa_cifrado, revertir_texto

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reversion", tags=["reversibilidad"])


@router.post("/mapa")
async def descargar_mapa(peticion: MapaRequest):
    """Genera el archivo cifrado que permite deshacer la anonimización."""
    estado = store.get(peticion.session_id)
    if not estado:
        raise HTTPException(404, "La sesión expiró. Vuelva a cargar el documento.")

    try:
        datos = generar_mapa_cifrado(estado, peticion.passphrase, peticion.nota)
    except ErrorMapa as error:
        raise HTTPException(400, str(error)) from error

    return Response(
        content=datos,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": content_disposition_attachment(
                f"{estado.doc_name}{MAPA_EXTENSION}"
            )
        },
    )


@router.post("/revertir", response_model=RevertirResponse)
async def revertir_documento(
    passphrase: str = Form(...),
    mapa: UploadFile = File(...),
    documento: UploadFile | None = File(None),
    texto: str = Form(""),
):
    """Restituye los datos originales de un documento anonimizado.

    Recibe el archivo del mapa, la frase de paso y el documento anonimizado
    (como archivo o como texto pegado). Nada de esto se conserva: la operación
    se resuelve en memoria y la respuesta se devuelve de inmediato.
    """
    contenido_mapa = await mapa.read()
    if not contenido_mapa:
        raise HTTPException(400, "El archivo del mapa está vacío.")
    if len(contenido_mapa) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "El archivo del mapa es demasiado grande.")

    texto_anonimizado = texto.strip()
    nombre = "documento"

    if documento is not None and documento.filename:
        datos = await documento.read()
        if len(datos) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "El documento es demasiado grande.")
        try:
            resultado = extraer_documento(documento.filename, datos)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        texto_anonimizado = resultado.texto
        nombre = documento.filename.rsplit(".", 1)[0]

    if not texto_anonimizado:
        raise HTTPException(
            400,
            "Debe adjuntar el documento anonimizado o pegar su texto para poder "
            "revertirlo.",
        )

    try:
        contenido = leer_mapa_cifrado(contenido_mapa, passphrase)
        restituido, reemplazos, faltantes = revertir_texto(texto_anonimizado, contenido)
    except ErrorMapa as error:
        raise HTTPException(400, str(error)) from error

    return RevertirResponse(
        texto=restituido,
        doc_name=contenido.get("documento") or nombre,
        reemplazos=reemplazos,
        sin_coincidencia=faltantes,
    )


@router.post("/descargar")
async def descargar_revertido(
    formato: str = Form("docx"),
    nombre: str = Form("documento"),
    texto: str = Form(...),
):
    """Entrega el texto restituido como archivo, sin conservarlo en el servidor."""
    if not texto.strip():
        raise HTTPException(400, "No hay texto para descargar.")

    seguro = (nombre or "documento").strip() or "documento"

    if formato == "txt":
        return Response(
            content=build_txt_bytes(texto),
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": content_disposition_attachment(
                    f"{seguro}_restituido.txt"
                )
            },
        )

    return Response(
        content=build_docx_bytes(texto_a_parrafos(texto)),
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": content_disposition_attachment(
                f"{seguro}_restituido.docx"
            )
        },
    )
