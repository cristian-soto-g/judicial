@echo off
REM Inicia el Anonimizador Judicial Chile en este equipo.
cd /d "%~dp0"

if not exist ".venv" (
  echo Creando el entorno virtual...
  python -m venv .venv
  .venv\Scripts\python -m pip install --quiet --upgrade pip
  .venv\Scripts\python -m pip install --quiet -r requirements.txt
)

.venv\Scripts\python scripts\run_dev.py %*
pause
