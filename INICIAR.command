#!/usr/bin/env bash
#
# Anonimizador Judicial Chile — arranque en macOS.
#
# Haga doble clic en este archivo desde el Finder. La primera vez preparará el
# entorno, lo que puede tardar algunos minutos; las siguientes será inmediato.
#
# Si macOS advierte que el archivo proviene de un desarrollador no
# identificado, haga clic derecho sobre él y elija «Abrir». Es la advertencia
# habitual para cualquier archivo descargado de internet.

set -euo pipefail

# Al abrirse con doble clic, la carpeta de trabajo es la de inicio del usuario,
# no la de la aplicación. Sin esta línea no encontraría sus propios archivos.
cd "$(dirname "$0")"

VERSION_MINIMA="3.11"

echo "Anonimizador Judicial Chile"
echo "Procesamiento local. Nada de lo que abra saldrá de este equipo."
echo

# --- Buscar un intérprete de Python adecuado ------------------------------
# macOS trae Python 3.9, que no alcanza. Se prueban primero las versiones
# instaladas por Homebrew o desde python.org.
encontrar_python() {
  for candidato in python3.13 python3.12 python3.11 python3; do
    if command -v "$candidato" >/dev/null 2>&1; then
      if "$candidato" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
        echo "$candidato"
        return 0
      fi
    fi
  done
  return 1
}

if ! PYTHON=$(encontrar_python); then
  echo "No se encontró Python $VERSION_MINIMA o superior en este equipo."
  echo
  echo "macOS incluye una versión más antigua que no alcanza. Instale una"
  echo "actual por cualquiera de estas dos vías:"
  echo
  echo "  1. Descárguela de https://www.python.org/downloads/macos/"
  echo "     (elija la última versión y ejecute el instalador)."
  echo
  echo "  2. Si usa Homebrew:  brew install python@3.12"
  echo
  echo "Después vuelva a hacer doble clic en este archivo."
  echo
  read -r -p "Presione Intro para cerrar."
  exit 1
fi

echo "Python encontrado: $($PYTHON --version)"

# --- Preparar el entorno la primera vez -----------------------------------
if [ ! -d ".venv" ]; then
  echo
  echo "Primera ejecución: preparando el entorno. Esto puede tardar unos minutos."
  "$PYTHON" -m venv .venv
  ./.venv/bin/python -m pip install --quiet --upgrade pip
  ./.venv/bin/python -m pip install --quiet -r requirements.txt
  echo "Entorno preparado."
fi

echo
echo "Abriendo la aplicación en el navegador…"
echo "Para cerrarla, presione Control+C en esta ventana."
echo

./.venv/bin/python scripts/run_dev.py "$@"
