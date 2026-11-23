# Crea (o con -Quitar elimina) un acceso directo en la carpeta Inicio del usuario que arranca la terminal local
# minimizada al iniciar sesión: solo 127.0.0.1:8765, sin Tailscale. Lo ejecuta el usuario; no cambia ajustes del sistema.
#   powershell -ExecutionPolicy Bypass -File scripts\arranque-al-iniciar-sesion.ps1          -> crear
#   powershell -ExecutionPolicy Bypass -File scripts\arranque-al-iniciar-sesion.ps1 -Quitar  -> quitar
param([switch]$Quitar)
$repo = Split-Path -Parent $PSScriptRoot
$lnk = Join-Path ([Environment]::GetFolderPath("Startup")) "Actinver Terminal (local).lnk"
if ($Quitar) {
    if (Test-Path $lnk) { Remove-Item $lnk; "Acceso directo quitado: $lnk" } else { "No había acceso directo." }
    return
}
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
$s.TargetPath = Join-Path $env:WINDIR "System32\cmd.exe"
$s.Arguments = "/c `"$repo\start.bat`""
$s.WorkingDirectory = $repo
$s.WindowStyle = 7  # minimizada
$s.Description = "Arranca la terminal local en 127.0.0.1:8765 al iniciar sesión (sin Tailscale)"
$s.Save()
"Acceso directo creado: $lnk"
