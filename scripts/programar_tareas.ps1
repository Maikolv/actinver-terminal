# Registra cinco tareas programadas de Windows para el usuario actual (no requiere administrador).
# Revíselo antes de ejecutarlo:  powershell -ExecutionPolicy Bypass -File scripts\programar_tareas.ps1
# Para quitarlas:  Unregister-ScheduledTask -TaskName "Terminal portafolios - *" -Confirm:$false

$raiz = Split-Path -Parent $PSScriptRoot
$uv = (Get-Command uv -ErrorAction Stop).Source

$actualizar = New-ScheduledTaskAction -Execute $uv -Argument "run terminal actualizar" -WorkingDirectory $raiz
$disparo1 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 17:45
Register-ScheduledTask -TaskName "Terminal portafolios - actualizar" -Action $actualizar -Trigger $disparo1 `
    -Description "Actualiza tipo de cambio y cierres (respeta límites de proveedores)" -Force | Out-Null

$respaldo = New-ScheduledTaskAction -Execute $uv -Argument "run terminal respaldar" -WorkingDirectory $raiz
$disparo2 = New-ScheduledTaskTrigger -Daily -At 22:00
Register-ScheduledTask -TaskName "Terminal portafolios - respaldo" -Action $respaldo -Trigger $disparo2 `
    -Description "Respaldo verificado de data/terminal.db (conserva 14)" -Force | Out-Null

# Reportes (hora local del PC: se asume zona de Ciudad de México). Lun-Vie 08:00 y 15:15; semanal los sábados 09:00.
$lv = @("Monday","Tuesday","Wednesday","Thursday","Friday")
foreach ($r in @(@("preapertura", "08:00", $lv), @("cierre", "15:15", $lv), @("semanal", "09:00", @("Saturday")))) {
    $accion = New-ScheduledTaskAction -Execute $uv -Argument "run terminal reporte $($r[0])" -WorkingDirectory $raiz
    $disparo = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $r[2] -At $r[1]
    Register-ScheduledTask -TaskName "Terminal portafolios - reporte $($r[0])" -Action $accion -Trigger $disparo `
        -Description "Genera data/reportes/AAAA-MM-DD_$($r[0]).md" -Force | Out-Null
}

Write-Output "Tareas registradas. Revíselas en el Programador de tareas."
