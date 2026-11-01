# Cierre acotado de pendientes de Mesa — 31-oct-2026

Se conservaron los cambios anteriores y los dos anexos de Claude. No se reescribieron fuentes de ingesta ni modelos. Snapshot de fuentes y Git previo, diff y hashes finales en `auditoria-reels-20261031-evidencia/cierre-pendientes/`. codebase-memory devolvió Transport closed; fallback acotado de fuentes/pruebas, sin cobertura global atribuida al grafo.

Resueltos R31-12,13,14,16,18. R31-17 y19 parciales; R31-02 compilado en servidor, visual pendiente. Decisión MNQ: etiqueta solo NQ en Mesa y aclaración en Pine; no se modifica semántica, vectores, multiplicadores ni C#. Se conservan 23 tipos. Cambiar instrumento conserva abiertos los paneles, cancela preflight anterior y reemplaza el marco por uno del símbolo nuevo. Sin dato o sin catálogo nunca presupone una cotización. Un 200 significa documento disponible, no datos fiables.

## Aislamiento: resultado real, no solo prueba bloqueada

La prueba con sandbox `allow-scripts allow-popups allow-popups-to-escape-sandbox` produjo gráfica vacía y errores de cookies/Locks API. Quitar no-referrer no lo reparó; retirar sandbox, manteniendo no-referrer, mostró la gráfica NVDA. Calendario mostró eventos incluso con sandbox, aunque la corrida final registra avisos de proveedor. Se conserva sandbox únicamente allí y no-referrer en todos. Mapa no acreditó contenido útil ni con el control; no se considera resuelto. El aislamiento completo de los demás marcos requiere diseño separado y no se finge resuelto añadiendo allow-same-origin sobre el mismo origen. CSP global intacta. Ver tres capturas comparativas, `proveedores-sandbox.json` y `proveedores-final.json`; públicos, sin sesión ni envío de POST de telemetría.

## Resultados reproducidos

- `node --test tests/*.test.mjs`: 31 aprobadas.
- Python Actinver: referencias, cobertura, inventario, seguridad, TradingView: 28 aprobadas; una advertencia Starlette.
- Suite futuros-lab: 164 aprobadas con socket externo bloqueado y loopback permitido. Primera corrida con bloqueo de TODAS las conexiones: 162 pasaron y dos fallaron por sus servidores HTTP temporales locales; no eran fallas de estrategia. Se permitió únicamente loopback y se repitió completa. Telegram es FakeAvisador en esas pruebas: no hay mensajes externos.
- Runner .NET Release puro: salida 0, TODO COINCIDE; 510 escenarios válidos NQ/MNQ, cero diferencias. No se desplegó ninguna DLL de Quantower.
- Pine actual: pine_check (core.check instalado en tradingviewmcp), Guest, cero errores y cero advertencias. SHA y fecha en pine-check.json. No se arrancó MCP, conexión CDP, broker ni puente. Tres copias exigidas sincronizadas, también copia de entregables.
- Navegador Chromium 143 aislado: 390/768/1440, claro/oscuro; seis casos y recorrido de ida/vuelta. Sin errores JS locales, sin desbordamiento. HTTP404, red caída y fondo sin cobertura muestran SIN DATO sin iframe. Prueba pública separada con errores de proveedor registrados explícitamente.

## Comprobación visual Pine pendiente

1. Abrir personalmente un gráfico NQZ2026 en TradingView, sin conectar broker. Comprobar que es futuro NQ de CME, no CFD.
2. Pine Editor: pegar el archivo actual `tradingview/mesa_riesgo_nq.pine`, guardar como indicador privado y añadir al gráfico; no publicar, no crear alertas ni estrategia.
3. Escenario manual hipotético: entrada 20000, stop19990, R2, presupuesto100, comisión/slip0. NQ: TP20020, riesgo200 USD, cero contratos. No son cotizaciones actuales.
4. Corto: entrada20000, stop20010: TP19980. Leer advertencia de gap en tabla.
5. Repetir en futuro MNQZ2026: riesgo20 USD y cinco contratos con presupuesto100. La Mesa sigue expresamente solo NQ.
6. Guardar captura, símbolo, SHA del archivo y mensajes del editor. La compilación remota no sustituye esa comprobación.

Candados false/false/false; sin diario real disponible; incidentes no auditados, sin ventaja demostrada. Ninguna orden, tampoco demo; sin Telegram, credenciales, compra, commit ni push. Servidor aislado de prueba debe cerrarse al finalizar.
