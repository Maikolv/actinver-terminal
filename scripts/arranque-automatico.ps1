$ErrorActionPreference = 'Stop'
# Arranque automático al iniciar sesión en Windows (9-nov-2026: la terminal estuvo apagada del 6 al 9-nov y no hubo
# descargas, plan del día ni avisos). Usa el mismo iniciador del acceso directo, SOLO en esta PC (127.0.0.1): no publica
# por Tailscale. Si la terminal ya responde, no hace nada. Registros en data\terminal_*.log.
$env:ACTINVER_SIN_TAILSCALE = '1'
& (Join-Path $PSScriptRoot 'iniciar-remoto.ps1')
