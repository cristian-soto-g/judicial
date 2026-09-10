#!/usr/bin/env bash
# Inicia el Anonimizador Judicial Chile en este equipo.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Creando el entorno virtual…"
  python3 -m venv .venv
  ./.venv/bin/pip install --quiet --upgrade pip
  ./.venv/bin/pip install --quiet -r requirements.txt
fi

exec ./.venv/bin/python scripts/run_dev.py "$@"
