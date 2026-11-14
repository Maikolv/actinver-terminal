$ErrorActionPreference = 'Stop'
# Crea (o actualiza) en el Escritorio el acceso «Help Quote Terminal» con el logo de la terminal. Si falta el iniciador,
# lo compila. El iniciador enciende la terminal si no responde y abre http://127.0.0.1:8765 en el navegador.
$repo = Split-Path -Parent $PSScriptRoot
$exe = Join-Path $PSScriptRoot 'ActinverTerminal.exe'
$icono = Join-Path $PSScriptRoot 'actinver-terminal.ico'
if (-not (Test-Path -LiteralPath $exe)) { & (Join-Path $PSScriptRoot 'compilar.ps1') | Out-Null }
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop 'Help Quote Terminal.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $exe
$shortcut.WorkingDirectory = $repo
$shortcut.Description = 'Abre la Terminal Actinver e inicia el servicio local si hace falta.'
$shortcut.IconLocation = "$icono,0"
$shortcut.Save()
Write-Output $shortcutPath
