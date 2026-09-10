#!/usr/bin/env bash
#
# Anonimizador Judicial Chile — arranque en Linux.
#
# Ejecútelo desde una terminal:  ./INICIAR.sh
# La primera vez preparará el entorno; las siguientes será inmediato.

set -euo pipefail
cd "$(dirname "$0")"

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
  echo "No se encontró Python 3.11 o superior."
  echo "Instálelo con el gestor de paquetes de su distribución. Por ejemplo:"
  echo "  sudo apt install python3.12 python3.12-venv"
  exit 1
fi

echo "Anonimizador Judicial Chile — procesamiento local."
echo "Python encontrado: $($PYTHON --version)"

if [ ! -d ".venv" ]; then
  echo "Primera ejecución: preparando el entorno…"
  "$PYTHON" -m venv .venv
  ./.venv/bin/python -m pip install --quiet --upgrade pip
  ./.venv/bin/python -m pip install --quiet -r requirements.txt
fi

exec ./.venv/bin/python scripts/run_dev.py "$@"
