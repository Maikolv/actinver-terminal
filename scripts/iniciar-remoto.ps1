$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot

# Datos de la sesion Tailscale. Si falta algo, devuelve el motivo (texto) en lugar de detener el script:
# la terminal local debe arrancar aunque el acceso remoto no este disponible.
function Get-Remoto {
    if ($env:ACTINVER_SIN_TAILSCALE -eq '1') { return 'se pidio iniciar solo en local (ACTINVER_SIN_TAILSCALE=1).' }
    $ts = (Get-Command tailscale.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source)
    if (-not $ts) {
        $candidate = Join-Path $env:ProgramFiles 'Tailscale\tailscale.exe'
        if (Test-Path -LiteralPath $candidate) { $ts = $candidate }
    }
    if (-not $ts) { return 'Tailscale no esta instalado (tailscale.com/download/windows).' }
    $raw = & $ts status --json 2>$null
    if ($LASTEXITCODE -ne 0) { return 'no se pudo consultar Tailscale; abralo e inicie sesion.' }
    $status = $raw | ConvertFrom-Json
    if ($status.BackendState -ne 'Running') { return 'Tailscale aun no ha iniciado sesion en esta PC.' }
    $hostName = ([string]$status.Self.DNSName).TrimEnd('.').ToLowerInvariant()
    if (-not $hostName.EndsWith('.ts.net')) { return 'Tailscale no proporciono un nombre DNS valido.' }
    $userID = [string]$status.Self.UserID
    $login = [string]$status.User.PSObject.Properties[$userID].Value.LoginName
    if (-not $login -or $login -notmatch '@') { return 'Tailscale no proporciono el usuario de la cuenta.' }
    return @{ ts = $ts; host = $hostName; login = $login }
}

function Test-Terminal($remoto) {
    try {
        $headers = @{}
        if ($remoto) {
            $headers['Host'] = $remoto.host
            $headers['Tailscale-User-Login'] = $remoto.login
        }
        $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8765/api/estado' -Headers $headers -UseBasicParsing -TimeoutSec 3
        return $response.StatusCode -eq 200
    } catch { return $false }
}

# Arranca la terminal como proceso independiente (sigue corriendo al cerrar esta ventana); registros en data\terminal_*.log
function Start-Terminal($remoto) {
    $expected = Join-Path $repo '.venv\Scripts\terminal.exe'
    $running = Get-Process -Name terminal -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $expected }
    foreach ($proc in $running) { Stop-Process -Id $proc.Id -ErrorAction Stop }
    Start-Sleep -Seconds 2
    if (Test-Terminal $null) { throw 'El puerto 8765 lo ocupa otro proceso. No se modifico.' }
    $uv = (Get-Command uv -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source)
    if (-not $uv) { throw 'No se encontro "uv". Instalelo con: winget install astral-sh.uv' }
    & $uv sync --quiet --directory $repo
    New-Item -ItemType Directory -Force -Path (Join-Path $repo 'data') | Out-Null
    Start-Process -FilePath $uv -ArgumentList @('run', 'terminal', 'iniciar', '--sin-navegador') -WorkingDirectory $repo `
        -WindowStyle Hidden -RedirectStandardOutput (Join-Path $repo 'data\terminal_salida.log') `
        -RedirectStandardError (Join-Path $repo 'data\terminal_errores.log') | Out-Null
    for ($i = 0; $i -lt 90; $i++) {
        Start-Sleep -Seconds 1
        if (Test-Terminal $remoto) { return }
    }
    throw 'La terminal no respondio. Revise data\terminal_errores.log.'
}

$remoto = Get-Remoto
if ($remoto -is [string]) {
    # Sin Tailscale: solo acceso local. Nunca se publica por otra via.
    if (-not (Test-Terminal $null)) { Start-Terminal $null }
    Write-Warning "Acceso remoto NO activo: $remoto"
    Write-Output 'La terminal quedo disponible solo en esta PC: http://127.0.0.1:8765/'
    exit 0
}

$envPath = Join-Path $repo '.env'
if (-not (Test-Path -LiteralPath $envPath)) { throw 'No se encontro .env en el proyecto.' }
$lines = [System.Collections.Generic.List[string]]::new()
$lines.AddRange([string[]][System.IO.File]::ReadAllLines($envPath))
foreach ($setting in @(@('TERMINAL_HOSTS_REMOTOS', $remoto.host), @('TERMINAL_USUARIOS_REMOTOS', $remoto.login))) {
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

# Si la terminal no acepta la identidad remota (configuracion nueva), se reinicia solo este proceso
if (-not (Test-Terminal $remoto)) { Start-Terminal $remoto }

$serve = & $remoto.ts serve --bg 8765 2>&1
if ($LASTEXITCODE -ne 0) { throw "Tailscale Serve no pudo iniciarse: $serve" }
Write-Output "Acceso privado activo: https://$($remoto.host)"
Write-Output 'Abra esa direccion en otro dispositivo conectado a la misma red Tailscale.'
