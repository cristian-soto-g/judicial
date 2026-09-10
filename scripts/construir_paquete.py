"""Construye la distribución portable de la aplicación.

Ejecuta PyInstaller sobre `anonimizador.spec` y arma junto al ejecutable los
archivos que el usuario necesita: el lanzador, las instrucciones y los avisos
de licencia.

Uso:
    python scripts/construir_paquete.py
    python scripts/construir_paquete.py --sufijo v1.0.0-Windows-x64

El resultado queda en `dist/`. En Windows produce el paquete que se publica;
en Linux o macOS produce el equivalente para esa plataforma, lo que permite
verificar el empaquetado sin depender de un equipo Windows.
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app.config import APP_NAME, APP_VERSION  # noqa: E402

NOMBRE_PAQUETE = "AnonimizadorJudicialChile"

INSTRUCCIONES = """\
{app} {version}
Anonimización local de documentos judiciales chilenos.

CÓMO ABRIRLA
------------
Haga doble clic en INICIAR.bat (Windows) o ejecute ./INICIAR.sh (macOS y Linux).

Se abrirá una ventana con el estado de la aplicación y, enseguida, su navegador
en la dirección http://127.0.0.1:8799

Para cerrarla, presione Control+C en esa ventana o ciérrela. Al hacerlo se
descarta de la memoria el documento que estuviera procesando.

NO REQUIERE INSTALACIÓN
-----------------------
Esta carpeta es autónoma. No instala nada en el equipo, no requiere permisos de
administrador y no necesita que Python esté instalado. Puede moverla o copiarla
donde quiera, incluso a una unidad extraíble.

Para desinstalarla, borre la carpeta.

PRIVACIDAD
----------
El procesamiento ocurre por completo en este equipo. La aplicación no realiza
llamadas a servicios externos y rechaza las peticiones que no provengan del
propio equipo. Puede desconectar la red y seguirá funcionando igual.

Las sesiones viven solo en memoria: el texto del documento no se escribe en
disco y se pierde al cerrar la aplicación.

LÍMITES
-------
No incluye reconocimiento óptico de caracteres, de modo que un PDF escaneado
será rechazado. La detección automática no es completa: revise siempre el
resultado antes de compartir un documento.

Este paquete no incluye la capa opcional de reconocimiento de entidades por
modelo de lenguaje, porque ese modelo se distribuye bajo licencia GPL-3.0.
La detección determinística funciona sin ella. Para incorporarla, ejecute la
aplicación desde el código fuente.

ORIGEN Y LICENCIA
-----------------
Basada en el Anonimizador Judicial de IALAB — Laboratorio de Innovación e
Inteligencia Artificial, Facultad de Derecho, Universidad de Buenos Aires,
distribuido bajo licencia Apache 2.0. Esta obra derivada la adapta al
ordenamiento chileno y no está afiliada a IALAB ni cuenta con su patrocinio.

Véanse los archivos LICENSE y NOTICE incluidos en esta carpeta.

Código fuente: https://github.com/cristian-soto-g/judicial
"""

# El contenido del archivo .bat se mantiene en ASCII puro. cmd.exe interpreta
# el archivo con la codificacion vigente antes de ejecutar chcp, de modo que un
# acento en las primeras lineas se leeria mal.
LANZADOR_BAT = """\
@echo off
REM {app} - arranque en Windows.
cd /d "%~dp0"
chcp 65001 >nul
"{nombre}\\{nombre}.exe" %*
if errorlevel 1 pause
"""

LANZADOR_SH = """\
#!/usr/bin/env bash
# {app} — arranque en macOS y Linux.
set -euo pipefail
cd "$(dirname "$0")"
exec "./{nombre}/{nombre}" "$@"
"""


def _ejecutar(comando: list[str]) -> None:
    print(f"  $ {' '.join(comando)}")
    subprocess.run(comando, check=True, cwd=RAIZ)


def limpiar() -> None:
    for carpeta in ("build", "dist"):
        ruta = RAIZ / carpeta
        if ruta.exists():
            shutil.rmtree(ruta)
            print(f"  se eliminó {carpeta}/")


def construir() -> Path:
    print("Construyendo el ejecutable…")
    _ejecutar(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            str(RAIZ / "anonimizador.spec"),
            "--noconfirm",
            "--clean",
            "--log-level",
            "WARN",
        ]
    )

    destino = RAIZ / "dist" / NOMBRE_PAQUETE
    if not destino.exists():
        raise SystemExit("PyInstaller no produjo la carpeta esperada en dist/.")
    return destino


def armar_distribucion(carpeta_exe: Path) -> Path:
    """Coloca el ejecutable y sus acompañantes en la carpeta final."""
    distribucion = RAIZ / "dist" / f"{NOMBRE_PAQUETE}-portable"
    if distribucion.exists():
        shutil.rmtree(distribucion)
    distribucion.mkdir(parents=True)

    shutil.move(str(carpeta_exe), str(distribucion / NOMBRE_PAQUETE))

    (distribucion / "LEEME.txt").write_text(
        INSTRUCCIONES.format(app=APP_NAME, version=APP_VERSION), encoding="utf-8"
    )
    for archivo in ("LICENSE", "NOTICE"):
        shutil.copy2(RAIZ / archivo, distribucion / archivo)

    (distribucion / "INICIAR.bat").write_text(
        LANZADOR_BAT.format(app=APP_NAME, nombre=NOMBRE_PAQUETE),
        encoding="utf-8",
        newline="\r\n",
    )
    lanzador_sh = distribucion / "INICIAR.sh"
    lanzador_sh.write_text(
        LANZADOR_SH.format(app=APP_NAME, nombre=NOMBRE_PAQUETE), encoding="utf-8"
    )
    lanzador_sh.chmod(0o755)

    return distribucion


def comprimir(distribucion: Path, sufijo: str) -> Path:
    base = RAIZ / "dist" / f"{NOMBRE_PAQUETE}-{sufijo}"
    print(f"Comprimiendo en {base.name}.zip…")
    archivo = shutil.make_archive(
        str(base), "zip", root_dir=distribucion.parent, base_dir=distribucion.name
    )
    return Path(archivo)


def _sufijo_por_defecto() -> str:
    sistemas = {"Windows": "Windows", "Darwin": "macOS", "Linux": "Linux"}
    sistema = sistemas.get(platform.system(), platform.system())
    arquitectura = "x64" if platform.machine().lower() in ("amd64", "x86_64") else platform.machine()
    return f"v{APP_VERSION}-{sistema}-{arquitectura}"


def main() -> int:
    analizador = argparse.ArgumentParser(description="Construye el paquete portable.")
    analizador.add_argument(
        "--sufijo",
        default=os.environ.get("ANON_SUFIJO_PAQUETE") or _sufijo_por_defecto(),
        help="Sufijo del archivo comprimido resultante.",
    )
    analizador.add_argument(
        "--sin-comprimir",
        action="store_true",
        help="Deja la carpeta armada sin generar el archivo comprimido.",
    )
    argumentos = analizador.parse_args()

    print(f"{APP_NAME} {APP_VERSION} — construcción del paquete portable")
    print(f"Plataforma: {platform.system()} {platform.machine()}")
    print()

    limpiar()
    carpeta_exe = construir()
    distribucion = armar_distribucion(carpeta_exe)

    tamano = sum(f.stat().st_size for f in distribucion.rglob("*") if f.is_file())
    print(f"\nCarpeta armada: {distribucion.relative_to(RAIZ)} ({tamano / 1e6:.1f} MB)")

    if argumentos.sin_comprimir:
        return 0

    comprimido = comprimir(distribucion, argumentos.sufijo)
    print(
        f"Paquete listo: {comprimido.relative_to(RAIZ)} "
        f"({comprimido.stat().st_size / 1e6:.1f} MB)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
