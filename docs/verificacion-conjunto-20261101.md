# Verificación del conjunto actual — 1-nov-2026

## Resultado posterior a las correcciones de Excel

`uv run --offline --frozen pytest tests` terminó con **859 aprobadas, cero fallidas, una advertencia, 1097.18 s (18:17), salida 0**. Evidencia: `proveedores-20261101-evidencia/excel-conjunto-final-20261101.txt`. Se desactivaron carga de entorno, configuración local y motor; BLAS/OMP/MKL a un hilo. La advertencia es BlockingPortal de Starlette/AnyIO. Esta ejecución valida el código posterior de Excel; las 858 de abajo pertenecen a la fase anterior. No se repiten Node y worker por cambios exclusivos de Python/Excel y documentación: sus resultados previos de 52 y 19 conservan ese alcance. No es una medición de rendimiento ni evidencia de ventaja financiera.

## Ejecución completa observada

`uv run --offline --frozen python docs/proveedores-20261101-evidencia/pruebas_sin_red.py tests -q` terminó con **856 aprobadas, 1 fallida, 1 advertencia**, 833.24 s, **salida 1**. Registro íntegro: `proveedores-20261101-evidencia/continuacion-final-pytest-20261101.txt`.

La falla fue `tests/test_seguridad.py::test_sin_secretos_en_archivos_versionados`: PermissionError al intentar leer el archivo de propietario `~$plantilla-sintetico-despues.xlsx`, creado y bloqueado por Excel durante la revisión visual. No se interpreta ese fallo como una búsqueda de secretos completada ni como evidencia de un secreto encontrado.

## Corrección acotada

`.gitignore` excluye ahora únicamente los temporales de propietario Office `~$*.xlsx`, `~$*.docx` y `~$*.pptx`. No se eliminó ni cerró a la fuerza ningún documento. No se omiten archivos fuente, no se captura PermissionError de forma general y no se modifican los patrones de secretos.

Se añadió una regresión que comprueba que Git ignora esos tres tipos de temporal. Los archivos ya versionados no desaparecen del inventario por una regla de ignore; el escáner sigue leyendo el conjunto versionado y los archivos nuevos no ignorados.

La selección de seguridad posterior se sigue en `proveedores-20261101-evidencia/seguridad-office-20261101.txt`. Su resultado se agrega cuando se observa la salida terminal; no se suma a las 856 anteriores para inventar una suite completa aprobada.

**Resultado de seguridad observado:** 16 aprobadas, 1 advertencia, 59.50 s, salida 0. Incluye el escáner completo de secretos y la regresión del ignore. Se inició una segunda suite completa después de esta corrección, en `proveedores-20261101-evidencia/continuacion-final-pytest-corregida-20261101.txt`; queda en seguimiento hasta observar su salida terminal.

**Worker posterior:** `npm --prefix cloud-alerts test`, 19 aprobadas, 0 fallidas, 1197.9954 ms, salida 0. Evidencia: `proveedores-20261101-evidencia/continuacion-worker-20261101.txt`. Servicios simulados; sin despliegue ni envío externo.

**Candados posteriores:** ejecución de solo lectura de `futuros-lab/scripts/estado_demo.py`: modo PAPER; adaptador, live y fondeada false; diario real no disponible, incidentes no auditados, aprobación false y sin ventaja demostrada. Los contadores de sesiones/trades no acreditan evidencia forward ni ausencia de incidentes. No se inició ninguna estrategia.

## Alcance y estado

## Resultado final de la repetición completa

El proceso terminó con **858 aprobadas, 0 fallidas, 1 advertencia**, **929.36 s (15 min 29 s)**, **salida 0**. Registro íntegro: `proveedores-20261101-evidencia/continuacion-final-pytest-corregida-20261101.txt`. Incluye la nueva regresión del ignore de Office. Se mantiene el registro previo de 856 aprobadas/1 falla; no se sustituyó ni sumó a esta ejecución.

La selección Node más reciente pasó 52 pruebas; la regresión posterior de dimensiones también pasó en Chromium con el script permanente `tests/navegador/mesa-disposiciones.cjs` (390/1440). Worker: 19 aprobadas. Estas son tres suites distintas, no una suma de evidencia financiera.

Los archivos Python no cambiaron durante esta repetición; las correcciones de interfaz posteriores se comprobaron con Node y Chromium. No se declara rendimiento mejorado por la duración de pruebas: ambas corridas compartieron el PC con otros procesos y no son un benchmark controlado.

Sin red externa, .env, motor, brokers o estrategias. Se usaron fixtures temporales. La advertencia corresponde a la API de BlockingPortal de Starlette/AnyIO. La revisión posterior de código JS tiene su resultado independiente (52 Node); no se confunde con la recolección de Python.

No se declara terminado el objetivo ni cerrados los pendientes externos. Sin trades, commit ni push.
