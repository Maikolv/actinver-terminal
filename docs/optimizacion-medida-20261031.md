# Optimización medida de Mesa — 31-oct-2026

Mandato vigente: ninguna operación, siquiera demo. Servidor de prueba solo local con motor, bot y sincronizador deshabilitados, sin .env; sockets externos rechazados. Se usó copia SQLite fija fuera del repositorio; nunca se alteró la estrategia, sus parámetros ni el backtest. No se activó DLL, adaptador, puente, cuenta ni notificación.

## Método y alcance

Windows 11 26200, AMD Ryzen 7 3700U, 8 procesadores lógicos, 5.89 GiB RAM utilizable; Python 3.12.14, Node 24.19.0, FastAPI 0.143.3, Uvicorn 0.54.0, pandas 3.0.6. Google Chrome for Testing 143.0.7499.4, headless shell build 1200. Tres procesos nuevos por fase, navegador/contexto nuevos, viewport 1440×1000, misma configuración y copia de datos de 248385536 bytes. Huella en evidencia/dataset.json. No se purgó caché del sistema: «frío» significa proceso nuevo, no disco frío. Cifras de arranque no acreditan causalidad del parche; no se optimizaron importaciones. Otras aplicaciones de Windows continuaron abiertas, por lo que hay ruido y presión de memoria.

Cada repetición: disponibilidad HTTP del servidor, apertura Mesa y espera del selector, 15 GET estado, 15 GET universo, recarga, apertura de Velas, movimiento, 60 s en espera. Primer panel útil significa interfaz/catalogo local utilizable, **no primera cotización actual**. El widget externo fue bloqueado igual en ambas fases. Las llamadas de medición hechas por APIRequestContext no cuentan en el tráfico CDP de la página. Bytes son encodedDataLength de CDP (incluye cabeceras, puede reflejar caché); no son consumo de red facturado. CPU se expresa en segundos consumidos; tiempo de tareas CDP es una aproximación de actividad, no CPU del proceso renderer. RSS servidor es working set instantáneo, no pico.

Memoria completa de pestaña: suplemento pareado (tres antes/después), navegadores separados, solo Mesa y sin iframe abierto; suma RSS de renderers propios identificados por SystemInfo CDP. El frontend anterior se sirvió desde los archivos de línea base conservados, sin restaurar archivos de trabajo. El endpoint completo conservó su implementación. No comparar RSS como ahorro estable ni sumar shared working sets como memoria privada.

## Resultados: mediana / p95

P95 por rango más cercano. Arranque/UI/espera tienen n=3 por fase (p95 equivale al máximo y no es una estimación robusta poblacional). Endpoints n=45 por fase.

| Medida | Antes: mediana / p95 | Después: mediana / p95 |
|---|---:|---:|
| Arranque de proceso (ms) | 30991.63 / 33154.62 | 15826.66 / 16261.83 |
| Selector utilizable / primer panel local (ms) | 5077.57 / 5212.10 | 490.15 / 638.15 |
| Recarga tibia de Mesa (ms) | 618.23 / 863.02 | 191.89 / 229.63 |
| Reordenar panel (ms) | 101.41 / 121.96 | 47.80 / 54.15 |
| RSS servidor (MiB) | 40.89 / 41.48 | 31.31 / 41.45 |
| Heap JS pestaña (MiB) | 2.67 / 2.67 | 2.99 / 2.99 |
| CPU servidor en espera (s CPU / ventana 60 s) | 0.11 / 0.12 | 0.11 / 0.11 |
| Tiempo de tareas pestaña en espera (s / 60 s) | 0.11 / 0.13 | 0.07 / 0.11 |
| Solicitudes de página durante espera 60 s | 0.00 / 0.00 | 0.00 / 0.00 |
| Bytes CDP durante espera 60 s | 0.00 / 0.00 | 0.00 / 0.00 |
| Solicitudes de página en recorrido completo | 21.00 / 21.00 | 21.00 / 21.00 |
| Bytes CDP en recorrido completo | 76276.00 / 76276.00 | 70552.00 / 70552.00 |
| /api/estado completo (ms, 45 muestras/fase) | 48.52 / 605.86 | 33.03 / 2034.11 |
| /api/universo completo (ms, 45 muestras/fase) | 450.23 / 669.69 | 286.18 / 412.07 |
| RSS renderer, Mesa cerrada (MiB, 3 pares) | 82.24 / 83.22 | 92.26 / 93.23 |

Catálogo ligero nuevo `/api/universo?solo_catalogo=true`: **61.00 / 79.91 ms** (mediana / p95, 45 muestras posteriores). No es equivalente a la respuesta con precios: deliberadamente lleva precios/proveedor nulos y conserva la identidad/cobertura. El endpoint sin parámetro sigue calculando cotizaciones; sus variaciones no se atribuyen a una caché nueva.

## Cambios pequeños y motivo

- El selector deja de calcular precios del universo. La línea base medía ese trabajo innecesario y la carga hasta selector; no se añade dependencia ni caché de precios.
- Reordenar reutiliza tarjetas y `moveBefore` cuando está disponible; mantiene el contexto del iframe. Cerrar o quitar elimina el marco. Navegadores sin `moveBefore` conservan tarjeta/disposición mediante `insertBefore`, pero pueden recargar el marco: pendiente comprobar allí.
- Aviso de panel duplicado; búsqueda por clave/nombre con Ctrl/Cmd+K y Escape. No se añaden paneles duplicados ni cambia el catálogo de 23 tipos.
- GET simultáneos sin opciones se deduplican hasta resolverse, con liberación también en error. No persisten una respuesta ni sustituyen una fresca por una vieja. POST y peticiones con opciones no se agrupan. Timeout de 15 s solo en estado/universo; no se limita una simulación costosa con ese plazo.
- Ranking y consulta periódica de actualización SEC no consultan con `document.hidden`; estado ya suspendía su polling y el flujo de velas cerraba al ocultar. No se aumentan cuotas ni reintentos de proveedor.

No hubo tráfico de espera de Mesa ni antes ni después con proveedores bloqueados. No se inventa ahorro allí. El número de iframes después de mover pasó de 0 a 1 porque antes el fallo cerraba el panel: conservarlo puede usar más memoria y es el comportamiento solicitado.

## Fuentes y recursos

Ver [proveedores gratuitos](proveedores-gratuitos-20261031.md) y [equivalencias completas de los 15 tipos upstream](openterminal-equivalencias-20261031.md). Verificación documental oficial separada de disponibilidad real. No se hizo una prueba autenticada de feeds ni se atribuyó frescura a HTTP 200. FRED oficial API y CSV público son vías distintas; Yahoo/Nasdaq/TradingView scanner no se convierten en APIs oficiales por aparecer en OpenTerminal. No se clonó ni instaló nada.

No se introduce fallback de precios. La ingesta existente conserva fecha/proveedor/obtenido_en en sus objetos; no se inventan available_at/event_time/ingested_at que la fuente no entrega. Normalizar todos esos campos en la ingesta existente y respetar Retry-After de cada proveedor requieren trabajo separado: el adaptador base existente tiene timeout de 30 s, consume cuota por intento y backoff 2/4 s, pero no interpreta Retry-After. No se ejercitó red para probar cuotas.

## Pruebas y evidencia

- 22 pruebas Node: deduplicación real con fetch controlado (concurrencia, errores, POST), suspensión de Ranking oculto, aritmética y referencia exacta, catálogo, guías y navegación.
- 19 pruebas Python: catálogo sin consultar precios, respuesta normal preservada, cobertura y seguridad. Advertencia de deprecación Starlette, sin fallos.
- Cuatro recorridos Chromium: claro/oscuro × 390/1440, Ctrl+K/Escape, sin desbordamiento ni errores JS, disposición persistente, identidad del iframe y cero recargas al mover, liberación al cerrar. `ui.json` y capturas.
- estado_demo.py de solo lectura: resultado en `estado-demo.json`; ausencia de diario no acredita cero incidentes ni ventaja.
- codebase-memory: list_projects y check_index_coverage devolvieron Transport closed. Fallback acotado: rg/lectura de app.py, app.js, mesa.mjs/html, mercado.py, adaptadores/base.py, config/db, inventarios y catálogo upstream. No se afirma cobertura del grafo.

Comandos usados desde el workspace: `node work/perf31.cjs antes`, `node work/perf31.cjs despues`, `node work/perf31_mem.cjs`, `node work/perf31_ui.cjs`; servidor aislado `work/perf31_server.py`. Copias revisables del instrumental en esta carpeta de evidencia. Pruebas desde Actinver: `node --test tests/consultas_deduplicadas.test.mjs tests/mesa.test.mjs tests/mesa_paridad.test.mjs tests/mesa_catalogo_auditoria.test.mjs tests/riesgo_nq_referencia.test.mjs tests/navegacion.test.mjs tests/guias.test.mjs`; `.venv/Scripts/python.exe -m pytest tests/test_universo_catalogo.py tests/test_cobertura_secciones.py tests/test_seguridad.py -q`.

## Pendientes preservados

R31-16 queda resuelto para el Chromium comprobado. No se cierran R31-02 visual Pine, R31-06/19 cobertura/frescura, R31-09 licencias, R31-17 aislamiento de marcos, R31-18 cobertura Mesa, ni investigación estadística por medir rendimiento. Pine cuenta ahora con evidencia de compilación en servidor de TradingView aportada por Claude; aquí no se volvió a compilar ni se probó en gráfico. NoiseBands.cs y PlanManualNQ.cs son funciones puras existentes, no estrategia activada.

Esta medición no cubre todas las pestañas, proveedor real cargado ni motor activo, excluidos para mantener las condiciones offline. No representa consumo con CME/DOM. No demuestra alfa ni autoriza operar.

## Lectura crítica de las cifras

El p95 de /api/estado fue peor después (2034 ms frente a 606 ms); las 45 observaciones incluyen la primera carga, no solo tibias. Ese endpoint no recibió optimización de servidor. El RSS renderer de la muestra pareada aumentó (mediana 82.24 a 92.26 MiB); no se demostró ahorro de memoria. Debe repetirse con seguimiento de memoria privada/picos y ventanas más largas antes de atribuir la variación al parche. La mejora comprobada principal es evitar precios para el selector y conservar los marcos. El arranque sigue siendo el mayor tiempo absoluto; investigar su perfil de importaciones queda pendiente, sin mover costo ocultamente a la primera consulta.
