# -*- mode: python ; coding: utf-8 -*-
"""Especificación de empaquetado para PyInstaller.

Construye una distribución en carpeta (no un único archivo). La diferencia
importa para una herramienta que trata datos sensibles: el formato de archivo
único se descomprime entero en la carpeta temporal del sistema cada vez que se
ejecuta, dejando allí una copia completa del programa. La distribución en
carpeta no escribe nada fuera de donde el usuario la puso.

El modelo de lenguaje de spaCy no se incluye deliberadamente. Se distribuye
bajo licencia GPL-3.0, y empaquetarlo junto al resto sometería toda la
distribución a esa licencia. La capa que lo usa es opcional por diseño: la
detección determinística funciona sin ella. Quien quiera esa capa puede
instalarla por separado desde el código fuente.

Uso:  pyinstaller anonimizador.spec --noconfirm
"""
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

RAIZ = Path(SPECPATH)
NOMBRE = "AnonimizadorJudicialChile"

_ruta_icono = RAIZ / "frontend" / "icono.ico"
_icono_windows = (
    str(_ruta_icono) if sys.platform == "win32" and _ruta_icono.exists() else None
)

datos = [
    (str(RAIZ / "frontend"), "frontend"),
    (str(RAIZ / "data" / "dictionaries"), "data/dictionaries"),
]

# Archivos de datos que estas bibliotecas leen del disco en tiempo de
# ejecución. El análisis de importaciones no los alcanza, porque no son
# módulos: python-docx necesita sus plantillas XML para abrir un documento,
# reportlab sus tipografías para escribir un PDF, y pdfminer sus tablas de
# codificación para interpretarlo. Sin ellos el paquete arranca sin errores y
# falla recién al procesar el primer archivo del usuario.
for _paquete in ("docx", "reportlab", "pdfminer", "pdfplumber"):
    datos += collect_data_files(_paquete)

# reportlab incluye entre sus datos una tipografía de demostración bajo
# licencia GPL que la aplicación no utiliza. Se excluye para que la
# distribución quede compuesta solo por componentes de licencia permisiva.
datos = [
    (origen, destino)
    for origen, destino in datos
    if "DarkGarden" not in Path(origen).name
]

# Marcador que fuerza la creación de docx/parts/ en el paquete. La razón está
# explicada en el propio archivo; en resumen, python-docx busca sus plantillas
# por una ruta que atraviesa ese directorio, y sin él la lectura de documentos
# Word falla en el paquete aunque las plantillas estén presentes.
datos.append(
    (str(RAIZ / "scripts" / "empaquetado" / "marcador_docx_parts.txt"), "docx/parts")
)

# Uvicorn resuelve estos módulos en tiempo de ejecución, de modo que el
# análisis estático no los alcanza.
importaciones_ocultas = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
]

# Toda la aplicación, para que ninguna importación diferida quede fuera.
importaciones_ocultas += collect_submodules("app")

analisis = Analysis(
    [str(RAIZ / "scripts" / "launcher.py")],
    pathex=[str(RAIZ)],
    binaries=[],
    datas=datos,
    hiddenimports=importaciones_ocultas,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Dependencias de desarrollo y de la capa opcional, que no forman
        # parte de la distribución.
        "pytest",
        "httpx",
        "spacy",
        "thinc",
        "tkinter",
        "matplotlib",
        "IPython",
        # pdfplumber declara estas bibliotecas para su modo de inspección
        # visual, que dibuja las páginas como imágenes. La aplicación solo
        # extrae texto y nunca lo usa; entre las dos suman unos cincuenta
        # megabytes. Pillow, en cambio, no puede excluirse: reportlab lo
        # importa al cargarse, de modo que sin él no habría exportación a PDF.
        # La prueba de humo es la que permite distinguir un caso del otro.
        "numpy",
        "pypdfium2",
        "pypdfium2_raw",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analisis.pure)

ejecutable = EXE(
    pyz,
    analisis.scripts,
    [],
    exclude_binaries=True,
    name=NOMBRE,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # Con consola: la ventana muestra el estado de la aplicación y es el modo
    # de cerrarla. Sin ella, el usuario no tendría señal alguna durante los
    # segundos que tarda en levantar, ni forma evidente de detenerla.
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # El icono se aplica solo en Windows. macOS espera el formato .icns, y
    # entregarle un .ico haría fallar la construcción en ese sistema.
    icon=_icono_windows,
)

coleccion = COLLECT(
    ejecutable,
    analisis.binaries,
    analisis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=NOMBRE,
)
