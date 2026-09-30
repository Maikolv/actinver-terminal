$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$ts = (Get-Command tailscale.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source)
if (-not $ts) {
    $candidate = Join-Path $env:ProgramFiles 'Tailscale\tailscale.exe'
    if (Test-Path -LiteralPath $candidate) { $ts = $candidate }
}
if (-not $ts) { throw 'Tailscale no esta instalado. Descarguelo del sitio oficial tailscale.com/download/windows.' }

$raw = & $ts status --json
if ($LASTEXITCODE -ne 0) { throw 'No se pudo consultar Tailscale. Abra Tailscale e inicie sesion.' }
$status = $raw | ConvertFrom-Json
if ($status.BackendState -ne 'Running') { throw 'Tailscale aun no ha iniciado sesion en esta PC.' }
$hostName = ([string]$status.Self.DNSName).TrimEnd('.').ToLowerInvariant()
if (-not $hostName.EndsWith('.ts.net')) { throw 'Tailscale no proporciono un nombre DNS valido.' }
$userID = [string]$status.Self.UserID
$profile = $status.User.PSObject.Properties[$userID].Value
$login = [string]$profile.LoginName
if (-not $login -or $login -notmatch '@') { throw 'Tailscale no proporciono el usuario de la cuenta para limitar el acceso.' }

$envPath = Join-Path $repo '.env'
if (-not (Test-Path -LiteralPath $envPath)) { throw 'No se encontro .env en el proyecto.' }
$lines = [System.Collections.Generic.List[string]]::new()
$lines.AddRange([string[]][System.IO.File]::ReadAllLines($envPath))
foreach ($setting in @(@('TERMINAL_HOSTS_REMOTOS', $hostName), @('TERMINAL_USUARIOS_REMOTOS', $login))) {
    $key = $setting[0]
    $value = $setting[1]
    $found = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match ('^' + [regex]::Escape($key) + '=')) {
            $lines[$i] = "$key=$value"
            $found = $true
            break
        }
    }
    if (-not $found) { $lines.Add("$key=$value") }
}
$newEnv = [string]::Join("`r`n", $lines) + "`r`n"
$oldEnv = [System.IO.File]::ReadAllText($envPath)
if ($newEnv -ne $oldEnv) {
    [System.IO.File]::WriteAllText($envPath, $newEnv, [System.Text.UTF8Encoding]::new($false))
}

function Test-Terminal([bool]$remoteHost) {
    try {
        $headers = @{}
        if ($remoteHost) {
            $headers['Host'] = $hostName
            $headers['Tailscale-User-Login'] = $login
        }
        $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8765/api/estado' -Headers $headers -UseBasicParsing -TimeoutSec 3
        return $response.StatusCode -eq 200
    } catch { return $false }
}

if (-not (Test-Terminal $true)) {
    $expected = Join-Path $repo '.venv\Scripts\terminal.exe'
    $running = Get-Process -Name terminal -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $expected }
    foreach ($proc in $running) { Stop-Process -Id $proc.Id -ErrorAction Stop }
    Start-Sleep -Seconds 2
    if (Test-Terminal $false) { throw 'El puerto 8765 lo ocupa otro proceso. No se modifico.' }
    Start-Process -FilePath 'cmd.exe' -ArgumentList @('/c', 'start.bat') -WorkingDirectory $repo -WindowStyle Hidden | Out-Null
    $ready = $false
    for ($i = 0; $i -lt 45; $i++) {
        Start-Sleep -Seconds 1
        if (Test-Terminal $true) { $ready = $true; break }
    }
    if (-not $ready) { throw 'La terminal no respondio con la configuracion remota. Revise start.bat.' }
}

$serve = & $ts serve --bg 8765 2>&1
if ($LASTEXITCODE -ne 0) { throw "Tailscale Serve no pudo iniciarse: $serve" }
Write-Output "Acceso privado activo: https://$hostName"
Write-Output 'Abra esa direccion en otro dispositivo conectado a la misma red Tailscale.'
