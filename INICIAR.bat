@echo off
REM Anonimizador Judicial Chile - arranque en Windows.
REM Haga doble clic en este archivo. La primera vez preparara el entorno.

cd /d "%~dp0"
chcp 65001 >nul

echo Anonimizador Judicial Chile
echo Procesamiento local. Nada de lo que abra saldra de este equipo.
echo.

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>nul
if errorlevel 1 (
  echo No se encontro Python 3.11 o superior en este equipo.
  echo.
  echo Instalelo desde https://www.python.org/downloads/windows/
  echo Al ejecutar el instalador, marque la casilla "Add Python to PATH".
  echo.
  echo Despues vuelva a hacer doble clic en este archivo.
  echo.
  pause
  exit /b 1
)

if not exist ".venv" (
  echo Primera ejecucion: preparando el entorno. Puede tardar unos minutos.
  python -m venv .venv
  .venv\Scripts\python -m pip install --quiet --upgrade pip
  .venv\Scripts\python -m pip install --quiet -r requirements.txt
  echo Entorno preparado.
)

echo.
echo Abriendo la aplicacion en el navegador...
echo Para cerrarla, presione Control+C en esta ventana.
echo.

.venv\Scripts\python scripts\run_dev.py %*
pause
