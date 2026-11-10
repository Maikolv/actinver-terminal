param([switch]$Quitar)
$ErrorActionPreference = 'Stop'
# Registra (o con -Quitar, elimina) el acceso «Actinver Terminal (arranque)» en la carpeta Inicio del usuario, que
# Windows ejecuta al iniciar sesión. Sin permisos de administrador. Ver scripts\arranque-automatico.ps1.
$inicio = [Environment]::GetFolderPath('Startup')
$lnk = Join-Path $inicio 'Actinver Terminal (arranque).lnk'
if ($Quitar) {
    if (Test-Path -LiteralPath $lnk) { Remove-Item -LiteralPath $lnk -Force }
    Write-Output "Arranque automatico quitado: $lnk"
    exit 0
}
$repo = Split-Path -Parent $PSScriptRoot
$script = Join-Path $PSScriptRoot 'arranque-automatico.ps1'
$shell = New-Object -ComObject WScript.Shell
$acceso = $shell.CreateShortcut($lnk)
$acceso.TargetPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$acceso.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`""
$acceso.WorkingDirectory = $repo
$acceso.WindowStyle = 7  # minimizada
$acceso.IconLocation = (Join-Path $repo 'launcher\actinver-terminal.ico') + ',0'
$acceso.Description = 'Enciende la Terminal Actinver (solo en esta PC) al iniciar sesion.'
$acceso.Save()
Write-Output "Arranque automatico registrado: $lnk"
