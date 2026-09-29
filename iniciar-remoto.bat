@echo off
rem Actinver Terminal con acceso remoto PRIVADO (Tailscale Serve). Requiere Tailscale instalado y con sesion iniciada.
rem Ver docs\acceso-remoto.md. La terminal sigue escuchando solo en 127.0.0.1; Tailscale la publica solo en SU red.
setlocal
cd /d "%~dp0"
where tailscale >nul 2>nul
if errorlevel 1 (
  echo No se encontro Tailscale. Instalelo con:  winget install tailscale.tailscale
  echo inicie sesion y vuelva a ejecutar este archivo.
  exit /b 1
)
where uv >nul 2>nul || (echo No se encontro "uv". Instalelo con:  winget install astral-sh.uv & exit /b 1)
uv sync --quiet || exit /b 1
rem Publica el puerto 8765 dentro de su red Tailscale (HTTPS). NO usa Funnel: nada queda abierto a Internet.
tailscale serve --bg 8765 || exit /b 1
echo.
echo Direccion para su celular o laptop (con Tailscale y la misma cuenta):
for /f "usebackq delims=" %%u in (`uv run python -c "import json,subprocess; d=json.loads(subprocess.run(['tailscale','status','--json'],capture_output=True,text=True).stdout); print('https://'+d['Self']['DNSName'].rstrip('.'))"`) do set URL=%%u
echo   %URL%
echo Agregue el nombre (sin https://) a TERMINAL_HOSTS_REMOTOS en .env si aun no esta.
echo.
uv run terminal iniciar --sin-navegador
