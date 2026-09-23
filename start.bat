@echo off
rem Actinver Terminal: instala dependencias (primera vez) y abre la terminal en http://127.0.0.1:8765
rem Uso:  start.bat          -> datos reales (con las claves de .env; sin claves, solo tipo de cambio)
rem       start.bat demo     -> datos SINTÉTICOS etiquetados, base separada en data\demo
setlocal
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo No se encontro "uv". Instalelo con:  winget install astral-sh.uv
  echo y vuelva a ejecutar start.bat
  exit /b 1
)
uv sync --quiet || exit /b 1
if /i "%~1"=="demo" (
  uv run terminal demo
) else (
  uv run terminal iniciar
)
