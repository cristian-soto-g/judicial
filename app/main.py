"""Punto de entrada de la aplicación.

Basado en el punto de entrada del Anonimizador Judicial de IALAB — Facultad de
Derecho, UBA (Apache 2.0). Modificado: se agregaron las rutas de
reversibilidad, las cabeceras que impiden el almacenamiento en caché del
contenido de los documentos y el rechazo de peticiones que no provengan del
propio equipo.
"""
from __future__ import annotations

import logging
import os
import sys
import webbrowser
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.staticfiles import StaticFiles

from app.api import (
    routes_analyze,
    routes_detections,
    routes_entities,
    routes_export,
    routes_reversal,
    routes_upload,
)
from app.config import APP_NAME, APP_VERSION, FRONTEND_DIR, HOST, PORT
from app.models.schemas import CATEGORIAS, ETIQUETAS_CATEGORIA
from app.models.store import store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=APP_NAME,
    description=(
        "Anonimización local de documentos judiciales chilenos. Basado en el "
        "Anonimizador Judicial de IALAB — Facultad de Derecho, UBA."
    ),
    version=APP_VERSION,
)

# Anfitriones admitidos. La aplicación es de uso personal y local: rechazar
# cualquier otro impide que quede expuesta por accidente si el equipo comparte
# la red o si se ejecuta detrás de un reenvío de puertos.
ANFITRIONES_LOCALES = frozenset(
    {
        f"127.0.0.1:{PORT}",
        f"localhost:{PORT}",
        f"[::1]:{PORT}",
        "127.0.0.1",
        "localhost",
    }
)


@app.middleware("http")
async def proteger_y_no_almacenar(request: Request, call_next):
    """Restringe el acceso al propio equipo y evita el almacenamiento en caché."""
    anfitrion = (request.headers.get("host") or "").lower()
    if anfitrion and anfitrion not in ANFITRIONES_LOCALES:
        return JSONResponse(
            status_code=403,
            content={
                "detail": (
                    "Esta aplicación solo admite conexiones desde el propio "
                    "equipo. Ábrala en http://127.0.0.1:"
                    f"{PORT}."
                )
            },
        )

    respuesta = await call_next(request)
    respuesta.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    respuesta.headers["Pragma"] = "no-cache"
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    respuesta.headers["Referrer-Policy"] = "no-referrer"
    return respuesta


app.include_router(routes_upload.router)
app.include_router(routes_analyze.router)
app.include_router(routes_detections.router)
app.include_router(routes_entities.router)
app.include_router(routes_export.router)
app.include_router(routes_reversal.router)


class ArchivosSinCache(StaticFiles):
    async def get_response(self, path: str, scope):  # type: ignore[override]
        respuesta = await super().get_response(path, scope)
        respuesta.headers["Cache-Control"] = "no-cache, must-revalidate"
        return respuesta


if FRONTEND_DIR.exists():
    app.mount("/static", ArchivosSinCache(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def inicio():
    indice: Path = FRONTEND_DIR / "index.html"
    if indice.exists():
        return FileResponse(indice)
    return {"mensaje": f"{APP_NAME} — interfaz no encontrada", "documentacion": "/docs"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    icono = FRONTEND_DIR / "icono.svg"
    if icono.exists():
        return FileResponse(icono, media_type="image/svg+xml")
    return Response(status_code=204)


@app.get("/estado")
async def estado():
    """Diagnóstico de la aplicación y de sus capas de detección."""
    from app.detection.nlp_status import get_nlp_layers_status

    return {
        "estado": "en funcionamiento",
        "aplicacion": APP_NAME,
        "version": APP_VERSION,
        "anfitrion": HOST,
        "puerto": PORT,
        "procesamiento": "local",
        "sesiones_abiertas": store.count(),
        "categorias": [
            {"clave": clave, "nombre": ETIQUETAS_CATEGORIA[clave]}
            for clave in CATEGORIAS
        ],
        "capas_lenguaje_natural": get_nlp_layers_status(),
        "basado_en": {
            "obra": "Anonimizador Judicial",
            "autor": "IALAB — Facultad de Derecho, Universidad de Buenos Aires",
            "licencia": "Apache 2.0",
        },
    }


def run_server(abrir_navegador: bool = True) -> None:
    """Levanta el servidor local y abre el navegador."""
    import uvicorn

    # En un ejecutable empaquetado sin consola, la salida estándar puede no
    # existir y uvicorn falla al consultarla.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")

    url = f"http://{HOST}:{PORT}"
    logger.info("%s %s", APP_NAME, APP_VERSION)
    logger.info("Procesamiento local. Abra %s en su navegador.", url)

    if abrir_navegador:
        try:
            webbrowser.open(url)
        except Exception:  # pragma: no cover - depende del entorno gráfico
            logger.info("No se pudo abrir el navegador automáticamente.")

    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    run_server()
