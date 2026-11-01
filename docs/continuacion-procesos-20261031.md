# Continuación de procesos — 31-oct-2026

Se terminó primero la continuación de Mesa descrita en `cierre-pendientes-reels-20261031.md`. Esta etapa tiene snapshot, diff y hashes separados en `procesos-20261031-evidencia/`: no incluye cambios anteriores de app.py, cobertura_secciones.py, app.js, navegación, referencias, reels o TradingView. Se conservó la corrección previa de reportes._seccion_motor y estado_motor; no se reescribieron. Sin commit ni push.

## 1. Respaldo de precios

`actualizar_precios` admite ahora inyectar el reloj. Solo cuando una posición de nivel 0 recibe cero barras y la sesión correspondiente al corte solicitado cerró, continúa con el siguiente proveedor configurado que soporta el instrumento. Ese respaldo se limita a una fuente, aunque devuelva cero o falle; los límites siguen consumiéndose en el adaptador existente. Para reparar el cierre se pide desde la última sesión esperada, no cinco años de historia. No se cambia ORDEN_PRECIOS ni se reasigna un instrumento.

Se conserva `intentos_precio` como último intento para la cola. Como su clave primaria es solo instrumento_id, no podía guardar ambos intentos: la nueva tabla `intentos_precio_historial` conserva fuente, fecha y cantidad de barras de cada intento. Es una creación aditiva dentro de db.inicializar, probada en bases temporales; **no se migró ni escribió la base original durante el trabajo**. Las filas de precios mantienen la fecha, proveedor real y tipo entregados; obtenido_en sigue siendo hora de ingesta, no fecha de publicación inventada.

Regresiones con httpx.MockTransport y adaptadores Tiingo/Alpaca reales: cero barras tras cierre recupera AMD; durante mercado abierto y fuera de cartera no lo intenta; cupo agotado no emite HTTP; cero o error del respaldo no busca un tercero. El request de Alpaca se dirige exclusivamente al dominio de datos, nunca a operaciones.

## 2. Propuesta de proveedores, no aplicada

Ver `propuesta-proveedores-sic-20261031.md`, CSV y JSON de solo lectura. 143 SIC activos con soporte declarado e historia Alpaca observada; 97 al 30-oct, 45 al 29-oct y uno al 14-oct. FSLR carece de cierre del 30-oct entre Tiingo/Alpaca en la foto medida. No se inventó ese precio. La corrida del 30-oct ya recuperó 98 registros con Alpaca tras límite de Tiingo: no se atribuye esa recuperación histórica a este parche.

Tiingo tiene configurado 45/h y 900/día; Alpaca 5000/día. El limitador existente no tiene ventana de minuto: la propuesta exige incorporar una antes de volcar todo el universo a Alpaca. El costo estimado mínimo por ronda completa es 286 solicitudes (raw/ajustada), más páginas y reintentos, no una medida real de tráfico. La línea `activo = false` de Tiingo está íntegramente comentada en un archivo que no se carga; sería global, no solo SIC. No se modificó config/local.toml ni ninguna cuota ni se consultaron claves.

## 3. Hora inyectada

La cola usa el día del reloj inyectado para su reserva de siete días y la ingesta lo pasa a ultima_sesion_cerrada. Reportes propaga su hora al resumen del Reto, motor, ventana de alertas, pronóstico y movimientos públicos; las alertas futuras quedan fuera de la ventana. La corrección anterior que evita KeyError sin ultimo_ciclo se conserva. Pruebas parametrizadas con viernes abierto y cerrado ejercitan estado_motor y los tres reportes.

El alcance es la selección temporal de estas rutas. No se afirma que generar un reporte histórico reconstruya las propuestas y la cartera que existían ese día: esas funciones siguen leyendo el estado guardado actual. Los timestamps de registro de ingesta reflejan cuándo se hizo la descarga, independientemente del corte de estudio.

## 4. Texto de plan, nunca enviado

`texto_plan` acepta el reloj opcional y lo transmite. `mensaje_simple` nombra cada emisora atrasada con fecha ISO respecto del calendario de su referencia; sin fecha válida lo declara. No generaliza el atraso a toda la cartera por una sola posición ni aplica el cierre mexicano a una referencia estadounidense todavía en sesión. La interfaz de construir conserva precios_al para consumidores anteriores; la generación actual usa la lista por emisora. La prueba del 2-nov a las 20:30 UTC reproduce México cerrado y NY abierto sin cambiar el reloj del PC. Todos los mensajes son texto local de prueba; no se arrancó BotTelegram ni se enviaron avisos.

## 5. GEX condicionado

No se aplicó el filtro adicional de strikes. En la fecha local de este trabajo (31-oct) aún no ha ocurrido la comprobación posterior al lunes 2-nov. Se conservan DIAS_CADENA=60, la regla de 60 s, la anti-fuga y la corrección de ventana ya existentes. No se disparó tarea ni adquisición GEX. La modificación ±30 % solo procede si, tras la observación autorizada futura, MU sigue por debajo de 50 % y se dispone de spot; requiere entonces su prueba específica.

## Verificación y límites

- Suite completa: **738 aprobadas, cero fallas**, una advertencia de deprecación Starlette, **466.93 s (7 min 46 s)**. Log completo en evidencia. Se ejecutó sobre fixtures temporales, sin .env y con sockets externos bloqueados; loopback solo para pruebas HTTP locales.
- Durante esa corrida se añadieron tres casos finales de texto/fecha inválida. La selección posterior `test_procesos_20261031.py test_mensaje_simple.py test_bot_telegram.py` pasó **32 pruebas**, incluidas esas tres y la corrección final del aviso por mercado. No se atribuyen esos tres casos a la recolección inicial de 738 ni se suman duplicados.
- `node --test tests/*.test.mjs`: **31 aprobadas**.
- `npm --prefix cloud-alerts test`: **19 aprobadas** con servicios simulados, sin publicar worker ni enviar mensajes.
- Ya había entorno y dependencias suficientes; no se ejecutó uv sync ni se cambió lockfile/dependencias para estas correcciones.
- codebase-memory list_projects y check_index_coverage: Transport closed. Se documenta fallback con rg y lectura en ingesta, adaptadores/base/proveedores, reportes, servicios, mensaje_simple, bot, db y sus pruebas. No se declara cobertura estructural completa del grafo.

No se hicieron descargas de precios ni se consumieron cuotas reales; el comportamiento live del fallback no está verificado. La disponibilidad SIP de la cuenta y su cuota externa siguen sin verificarse. No se leyó ni imprimió .env ni se automatizó Actinver. Ningún servidor de revisión de esta continuación quedó abierto. Adaptador/live/fondeada false; sin diario real disponible, incidentes no auditados y sin ventaja demostrada. No hubo trades, tampoco demo, órdenes ni activación de brokers/puentes/estrategias.

## Archivos de implementación y hashes

- `terminal/ingesta.py` — SHA256 `cb21d43a9b83500eff7936296feaecbe48f7d8bfbbca4352108f0ede6879e80c`
- `terminal/db.py` — SHA256 `cf31bcf17f599119481ede13ac7127b2411aff6d425694ea0b1c504c2d9aa25b`
- `terminal/reportes.py` — SHA256 `163147c7bc4203ba6c30b4759f4a1118d5f73c488a323dfd17a3c9d35499fb9b`
- `terminal/bot_telegram.py` — SHA256 `e145f0cbca74a6798bda0790b864c088c0d9c954d47dfb217750bd279bc61cd8`
- `terminal/mensaje_simple.py` — SHA256 `9be1c1c81c2848abe1c06ee3ffaaaa1e2ba4c55778ac20496e69e017ba7ab059`
- `tests/test_procesos_20261031.py` — SHA256 `73e694e6e7a083dbbf163b1a996477bfc9a2031b85cbf2a2fe4b695f793080d6`
- `config/propuesta-proveedores-20261031.toml` — SHA256 `f1077c4ad04df4728732cd9663116605345d7b4a0f41bc9c1e860f913dae8763`
