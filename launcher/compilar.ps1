$ErrorActionPreference = 'Stop'
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64/v4.0.30319/csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) {
    throw 'No se encontro el compilador de .NET Framework en Windows.'
}
$source = Join-Path $PSScriptRoot 'ActinverTerminal.cs'
$output = Join-Path $PSScriptRoot 'ActinverTerminal.exe'
& $compiler '/nologo' '/target:winexe' "/out:$output" '/reference:System.dll' '/reference:System.Windows.Forms.dll' $source
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $output)) {
    throw 'No se pudo crear ActinverTerminal.exe.'
}
Write-Output $output