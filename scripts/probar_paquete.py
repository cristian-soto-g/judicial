"""Prueba de humo sobre el paquete ya construido.

Levanta el ejecutable tal como lo hará el usuario y recorre el flujo completo
contra él: carga de los tres formatos admitidos, análisis, exportación,
generación del mapa cifrado y reversión. Comprueba además que el documento
exportado no conserve ninguno de los datos que debía anonimizar.

Es la verificación que distingue un paquete que arranca de uno que sirve. Un
ejecutable puede iniciarse sin errores y fallar después al leer un PDF porque
una biblioteca quedó fuera del empaquetado.

Uso:
    python scripts/probar_paquete.py
"""
from __future__ import annotations

import io
import json
import platform
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
NOMBRE_PAQUETE = "AnonimizadorJudicialChile"
BASE = "http://127.0.0.1:8799"
FRASE = "frase de paso para la prueba del paquete"

DOCUMENTO = """4° Tribunal de Juicio Oral en lo Penal de Santiago
RIT N° 145-2024 — RUC 2300456789-1

Compareció don Juan Ignacio Pérez Muñoz, cédula de identidad N° 12.345.678-5,
domiciliado en Pasaje Los Aromos 45, comuna de Maipú, teléfono +56 9 8765 4321,
correo juan.perez@correo.cl. Conducía el vehículo patente BBBB12.
"""

DATOS_SENSIBLES = [
    "12.345.678-5",
    "juan.perez@correo.cl",
    "+56 9 8765 4321",
    "BBBB12",
    "145-2024",
    "Pérez",
]


class FalloDePrueba(Exception):
    """Alguna comprobación del paquete no se cumplió."""


# Nombre del archivo con que el usuario abre la aplicación en cada sistema. En
# macOS la extensión importa: el Finder asocia .command con la Terminal y la
# ejecuta al hacer doble clic, mientras que un .sh se abriría en un editor de
# texto sin arrancar nada.
LANZADOR_ESPERADO = {
    "Windows": "INICIAR.bat",
    "Darwin": "INICIAR.command",
    "Linux": "INICIAR.sh",
}


def carpeta_distribucion() -> Path:
    return RAIZ / "dist" / f"{NOMBRE_PAQUETE}-portable"


def comprobar_lanzador() -> None:
    """Verifica que el paquete traiga el lanzador propio de este sistema.

    Es la comprobación que faltaba cuando el paquete de macOS se entregó con un
    INICIAR.sh: el ejecutable funcionaba, pero no había forma de abrirlo con
    doble clic, que es justamente lo que una distribución portable promete.
    """
    esperado = LANZADOR_ESPERADO.get(platform.system(), "INICIAR.sh")
    lanzador = carpeta_distribucion() / esperado

    comprobar(lanzador.exists(), f"el paquete incluye {esperado}")

    presentes = sorted(
        archivo.name
        for archivo in carpeta_distribucion().iterdir()
        if archivo.name.startswith("INICIAR")
    )
    comprobar(
        presentes == [esperado],
        f"no incluye lanzadores de otros sistemas (presentes: {presentes})",
    )

    if platform.system() != "Windows":
        comprobar(
            bool(lanzador.stat().st_mode & 0o111),
            f"{esperado} tiene permiso de ejecución",
        )

    contenido = lanzador.read_text(encoding="utf-8")
    comprobar(
        NOMBRE_PAQUETE in contenido,
        f"{esperado} apunta al ejecutable del paquete",
    )

    instrucciones = (carpeta_distribucion() / "LEEME.txt").read_text(encoding="utf-8")
    comprobar(
        esperado in instrucciones,
        f"las instrucciones nombran {esperado}",
    )


def ruta_ejecutable() -> Path:
    carpeta = RAIZ / "dist" / f"{NOMBRE_PAQUETE}-portable" / NOMBRE_PAQUETE
    nombre = NOMBRE_PAQUETE + (".exe" if platform.system() == "Windows" else "")
    ejecutable = carpeta / nombre
    if not ejecutable.exists():
        raise FalloDePrueba(
            f"No se encontró el ejecutable en {ejecutable}. "
            "Ejecute antes: python scripts/construir_paquete.py"
        )
    return ejecutable


def _peticion(ruta: str, datos=None, cabeceras=None, metodo=None):
    peticion = urllib.request.Request(
        BASE + ruta,
        data=datos,
        headers={"Host": "127.0.0.1:8799", **(cabeceras or {})},
        method=metodo,
    )
    try:
        with urllib.request.urlopen(peticion, timeout=60) as respuesta:
            return respuesta.read(), dict(respuesta.headers)
    except urllib.error.HTTPError as error:
        # El cuerpo de la respuesta trae el motivo real del fallo. Sin él, un
        # error de empaquetado se presenta como un escueto "500" y no hay por
        # dónde empezar a buscar.
        detalle = error.read().decode("utf-8", errors="replace")[:600]
        raise FalloDePrueba(f"{ruta} respondió {error.code}: {detalle}") from error


def _json(ruta: str, cuerpo=None, metodo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    cabeceras = {"Content-Type": "application/json"} if cuerpo is not None else {}
    contenido, _ = _peticion(ruta, datos, cabeceras, metodo)
    return json.loads(contenido)


def _formulario(ruta: str, campos: dict[str, str], archivos: dict[str, tuple[str, bytes]]):
    frontera = "----AnonimizadorPrueba"
    partes: list[bytes] = []
    for nombre, valor in campos.items():
        partes.append(
            f'--{frontera}\r\nContent-Disposition: form-data; name="{nombre}"\r\n\r\n'
            f"{valor}\r\n".encode()
        )
    for nombre, (archivo, contenido) in archivos.items():
        partes.append(
            f'--{frontera}\r\nContent-Disposition: form-data; name="{nombre}"; '
            f'filename="{archivo}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()
        )
        partes.append(contenido + b"\r\n")
    partes.append(f"--{frontera}--\r\n".encode())

    contenido, _ = _peticion(
        ruta,
        b"".join(partes),
        {"Content-Type": f"multipart/form-data; boundary={frontera}"},
    )
    return json.loads(contenido)


def esperar_aplicacion(proceso: subprocess.Popen, segundos: int = 90) -> None:
    limite = time.time() + segundos
    while time.time() < limite:
        if proceso.poll() is not None:
            salida = (proceso.stdout.read() if proceso.stdout else b"") or b""
            raise FalloDePrueba(
                "El ejecutable terminó antes de responder:\n"
                + salida.decode("utf-8", errors="replace")[-3000:]
            )
        try:
            _peticion("/estado")
            return
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
            time.sleep(1)
    raise FalloDePrueba(f"La aplicación no respondió en {segundos} segundos.")


def documento_docx() -> bytes:
    from docx import Document

    documento = Document()
    for parrafo in DOCUMENTO.split("\n\n"):
        documento.add_paragraph(parrafo.strip())
    memoria = io.BytesIO()
    documento.save(memoria)
    return memoria.getvalue()


def documento_pdf() -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    memoria = io.BytesIO()
    lienzo = canvas.Canvas(memoria, pagesize=A4)
    alto = 800
    for linea in DOCUMENTO.split("\n"):
        lienzo.drawString(50, alto, linea[:95])
        alto -= 15
    lienzo.save()
    return memoria.getvalue()


def comprobar(condicion: bool, mensaje: str) -> None:
    if not condicion:
        raise FalloDePrueba(mensaje)
    print(f"    [ok] {mensaje}")


def probar_formato(nombre: str, contenido: bytes) -> str:
    carga = _formulario("/api/cargar", {}, {"file": (nombre, contenido)})
    comprobar(carga["char_count"] > 0, f"{nombre}: se leyó el documento")

    sesion = carga["session_id"]
    analisis = _json(
        "/api/analizar",
        {"session_id": sesion, "label_mode": "cat", "sensibilidad": "exhaustiva"},
    )
    comprobar(
        analisis["stats"]["TOTAL"] >= 8,
        f"{nombre}: se detectaron {analisis['stats']['TOTAL']} datos",
    )

    categorias = {d["cat"] for d in analisis["detections"]}
    comprobar(
        {"PERSONA", "RUT", "CAUSA", "EMAIL", "TELEFONO", "PATENTE"} <= categorias,
        f"{nombre}: están presentes todas las categorías esperadas",
    )
    return sesion


def main() -> int:
    try:
        ejecutable = ruta_ejecutable()
    except FalloDePrueba as fallo:
        print(f"FALLO: {fallo}", file=sys.stderr)
        return 1

    print(f"Probando el paquete: {ejecutable.relative_to(RAIZ)}")
    print(f"Plataforma: {platform.system()} {platform.machine()}\n")

    print("  Archivos del paquete:")
    try:
        comprobar_lanzador()
    except FalloDePrueba as fallo:
        print(f"\nFALLO: {fallo}", file=sys.stderr)
        return 1
    print()

    proceso = subprocess.Popen(
        [str(ejecutable), "--sin-abrir"],
        cwd=str(ejecutable.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    try:
        print("  Esperando que la aplicación responda…")
        esperar_aplicacion(proceso)

        estado = _json("/estado")
        comprobar(estado["estado"] == "en funcionamiento", "la aplicación está activa")
        comprobar(len(estado["categorias"]) == 9, "se ofrecen las nueve categorías")
        comprobar(
            estado["capas_lenguaje_natural"]["spacy"]["disponible"] is False,
            "la capa opcional de lenguaje natural no viene incluida, como se documenta",
        )

        print("\n  Texto plano:")
        sesion = probar_formato("causa.txt", DOCUMENTO.encode("utf-8"))

        print("\n  Documento Word:")
        probar_formato("causa.docx", documento_docx())

        print("\n  PDF con capa de texto:")
        probar_formato("causa.pdf", documento_pdf())

        print("\n  Exportación:")
        for formato, firma in (("docx", b"PK"), ("pdf", b"%PDF"), ("txt", b"")):
            contenido, _ = _peticion(
                f"/api/exportar/{formato}",
                json.dumps({"session_id": sesion}).encode(),
                {"Content-Type": "application/json"},
            )
            comprobar(
                contenido.startswith(firma) and len(contenido) > 100,
                f"se generó el archivo {formato}",
            )

        texto_exportado, _ = _peticion(
            "/api/exportar/txt",
            json.dumps({"session_id": sesion}).encode(),
            {"Content-Type": "application/json"},
        )
        exportado = texto_exportado.decode("utf-8")
        fugas = [dato for dato in DATOS_SENSIBLES if dato in exportado]
        comprobar(not fugas, f"el documento exportado no conserva datos personales")

        print("\n  Reversibilidad:")
        mapa, _ = _peticion(
            "/api/reversion/mapa",
            json.dumps({"session_id": sesion, "passphrase": FRASE}).encode(),
            {"Content-Type": "application/json"},
        )
        comprobar(b"12.345.678-5" not in mapa, "el mapa se descargó cifrado")

        reversion = _formulario(
            "/api/reversion/revertir",
            {"passphrase": FRASE, "texto": exportado},
            {"mapa": ("causa.anonmap", mapa)},
        )
        comprobar(
            "12.345.678-5" in reversion["texto"] and not reversion["sin_coincidencia"],
            "la reversión restituyó el documento",
        )

        print("\nEl paquete funciona correctamente.")
        return 0

    except FalloDePrueba as fallo:
        print(f"\nFALLO: {fallo}", file=sys.stderr)
        return 1
    finally:
        proceso.terminate()
        try:
            proceso.wait(timeout=15)
        except subprocess.TimeoutExpired:  # pragma: no cover
            proceso.kill()


if __name__ == "__main__":
    raise SystemExit(main())
