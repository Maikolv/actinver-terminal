# Renombra la carpeta local actinver-terminal -> help-quote-terminal y rehace el arranque automatico.
# Ejecutar con Claude Code, Codex y la terminal CERRADOS (si no, Windows bloquea la carpeta):
#   powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Desktop\Repos\actinver-terminal\scripts\renombrar-carpeta.ps1"
$ErrorActionPreference = 'Stop'
$base = Join-Path $env:USERPROFILE 'Desktop\Repos'
$viejo = Join-Path $base 'actinver-terminal'
$nuevo = Join-Path $base 'help-quote-terminal'
if (-not (Test-Path $viejo)) { throw "No existe $viejo" }
if (Test-Path $nuevo) { throw "Ya existe $nuevo" }

# 1. Detener procesos que usen la carpeta (servidor de la terminal, uv, python).
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*$viejo*" -and $_.ProcessId -ne $PID } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2

# 2. Quitar el acceso directo viejo y renombrar.
$inicio = [Environment]::GetFolderPath('Startup')
Remove-Item -LiteralPath (Join-Path $inicio 'Actinver Terminal (arranque).lnk') -Force -ErrorAction SilentlyContinue
Rename-Item -LiteralPath $viejo -NewName 'help-quote-terminal'

# 3. Copiar la memoria de Claude Code a la ruta nueva del proyecto.
$proy = Join-Path $env:USERPROFILE '.claude\projects'
$mv = Join-Path $proy 'C--Users-MIKE-Desktop-Repos-actinver-terminal\memory'
$mn = Join-Path $proy 'C--Users-MIKE-Desktop-Repos-help-quote-terminal\memory'
if (Test-Path $mv) { New-Item -ItemType Directory -Force $mn | Out-Null; Copy-Item "$mv\*" $mn -Recurse -Force }

# 4. Rehacer el entorno (las rutas de .venv cambian) y el arranque automatico.
Set-Location $nuevo
uv sync
powershell -ExecutionPolicy Bypass -File (Join-Path $nuevo 'scripts\instalar-arranque-automatico.ps1')
Write-Output "Listo: $nuevo"
