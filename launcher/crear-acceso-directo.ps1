$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$exe = Join-Path $PSScriptRoot 'ActinverTerminal.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw 'Compile primero el iniciador con launcher/compilar.ps1.' }
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop 'Actinver Terminal.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $exe
$shortcut.WorkingDirectory = $repo
$shortcut.Description = 'Abre la Terminal Actinver e inicia el servicio local si hace falta.'
$shortcut.IconLocation = "$env:WINDIR\System32\shell32.dll,14"
$shortcut.Save()
Write-Output $shortcutPath