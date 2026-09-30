@echo off
rem Inicia la Terminal Actinver y comparte solo dentro de la red privada Tailscale.
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\iniciar-remoto.ps1"
if errorlevel 1 (
  echo.
  echo No se pudo activar el acceso remoto. Revise el mensaje anterior.
  pause
  exit /b 1
)
echo.
echo Pulse una tecla para cerrar esta ventana. La terminal seguira funcionando.
pause >nul
