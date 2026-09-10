"""Construcción del mapa de correspondencias y restitución del texto.

Módulo propio de esta obra derivada.

El mapa asocia cada etiqueta del documento anonimizado con el dato original que
reemplazó. Se entrega como archivo separado y cifrado, de modo que el documento
anonimizado pueda compartirse sin arrastrar consigo la información que permite
deshacer la anonimización.

Restricción importante y deliberada: la reversión exige que cada etiqueta
identifique a un solo dato. Los modos de etiquetado genérico ("[NOMBRE]" para
todas las personas) y de iniciales no cumplen esa condición, porque varias
personas comparten una misma etiqueta. En esos casos la aplicación no genera un
mapa parcial que induzca a error, sino que lo rechaza con una explicación.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from app.config import APP_NAME, APP_VERSION, MAPA_FORMATO
from app.models.schemas import ETIQUETAS_CATEGORIA, SessionState
from app.reversal.crypto import ErrorCifrado, cifrar, descifrar

ADVERTENCIA = (
    "Este archivo permite volver a identificar a las personas del documento "
    "anonimizado. Consérvelo cifrado, guárdelo separado del documento y no lo "
    "comparta junto con él."
)


class ErrorMapa(Exception):
    """El mapa de correspondencias no puede construirse o aplicarse."""


def construir_mapa(state: SessionState, nota: str = "") -> dict:
    """Arma el mapa de correspondencias a partir del estado de la sesión."""
    activas = [d for d in state.detections if d.enabled]
    if not activas:
        raise ErrorMapa(
            "No hay datos anonimizados en esta sesión, de modo que no hay nada "
            "que revertir."
        )

    por_etiqueta: dict[str, set[str]] = {}
    for deteccion in activas:
        por_etiqueta.setdefault(deteccion.placeholder, set()).add(deteccion.original)

    ambiguas = sorted(
        etiqueta for etiqueta, originales in por_etiqueta.items() if len(originales) > 1
    )
    if ambiguas:
        muestra = ", ".join(ambiguas[:5])
        raise ErrorMapa(
            "La reversión no es posible con el etiquetado actual: las etiquetas "
            f"{muestra} corresponden a más de un dato distinto. Vuelva a "
            "analizar el documento con el modo de etiquetado «Categorizado», "
            "que numera cada dato por separado, o edite manualmente las "
            "sustituciones repetidas."
        )

    entradas = [
        {
            "etiqueta": deteccion.placeholder,
            "original": deteccion.original,
            "categoria": deteccion.cat,
            "categoria_visible": ETIQUETAS_CATEGORIA.get(deteccion.cat, deteccion.cat),
            "ocurrencias": len(deteccion.positions),
        }
        for deteccion in sorted(activas, key=lambda d: d.placeholder)
    ]

    return {
        "formato": MAPA_FORMATO,
        "aplicacion": f"{APP_NAME} {APP_VERSION}",
        "documento": state.doc_name,
        "creado_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "modo_etiquetado": state.label_mode,
        "nota": nota.strip(),
        "advertencia": ADVERTENCIA,
        "entradas": entradas,
    }


def generar_mapa_cifrado(state: SessionState, passphrase: str, nota: str = "") -> bytes:
    """Devuelve el archivo del mapa, listo para descargar."""
    mapa = construir_mapa(state, nota)
    contenido = json.dumps(mapa, ensure_ascii=False, indent=2).encode("utf-8")

    try:
        sobre = cifrar(contenido, passphrase)
    except ErrorCifrado as error:
        raise ErrorMapa(str(error)) from error

    archivo = {
        "_advertencia": ADVERTENCIA,
        "_documento": state.doc_name,
        "_creado_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "_entradas": len(mapa["entradas"]),
        **sobre,
    }
    return json.dumps(archivo, ensure_ascii=False, indent=2).encode("utf-8")


def leer_mapa_cifrado(contenido: str | bytes, passphrase: str) -> dict:
    """Descifra el archivo del mapa y devuelve su contenido."""
    if isinstance(contenido, bytes):
        contenido = contenido.decode("utf-8", errors="replace")

    try:
        sobre = json.loads(contenido)
    except json.JSONDecodeError as error:
        raise ErrorMapa(
            "El archivo del mapa no se pudo leer. Verifique que sea el archivo "
            "de reversión generado por esta aplicación."
        ) from error

    try:
        datos = descifrar(sobre, passphrase)
    except ErrorCifrado as error:
        raise ErrorMapa(str(error)) from error

    try:
        return json.loads(datos.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ErrorMapa("El contenido del mapa está dañado.") from error


def revertir_texto(texto: str, mapa: dict) -> tuple[str, int, list[str]]:
    """Restituye los datos originales en el texto anonimizado.

    Devuelve el texto restituido, la cantidad de reemplazos aplicados y la
    lista de etiquetas del mapa que no se encontraron en el texto, que es el
    dato que permite advertir al usuario si el documento no corresponde al mapa.
    """
    entradas = mapa.get("entradas") or []
    if not entradas:
        raise ErrorMapa("El mapa no contiene correspondencias.")

    correspondencias = {
        entrada["etiqueta"]: entrada["original"]
        for entrada in entradas
        if entrada.get("etiqueta")
    }

    # Se ordenan de mayor a menor longitud para que "[PERSONA_10]" se reemplace
    # antes que "[PERSONA_1]" y no quede un "0" suelto en el texto.
    etiquetas = sorted(correspondencias, key=len, reverse=True)
    patron = re.compile("|".join(re.escape(etiqueta) for etiqueta in etiquetas))

    reemplazos = 0
    encontradas: set[str] = set()

    def sustituir(coincidencia: re.Match[str]) -> str:
        nonlocal reemplazos
        etiqueta = coincidencia.group(0)
        encontradas.add(etiqueta)
        reemplazos += 1
        return correspondencias[etiqueta]

    resultado = patron.sub(sustituir, texto)
    sin_coincidencia = sorted(set(etiquetas) - encontradas)

    return resultado, reemplazos, sin_coincidencia
