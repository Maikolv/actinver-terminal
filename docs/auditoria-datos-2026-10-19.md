# Auditoría: «no se ven los datos en la terminal» — 19-oct-2026, 23:40

## Hallazgos

| # | Causa | Evidencia | Estado |
|---|---|---|---|
| 1 | **La terminal principal (127.0.0.1:8765) no estaba corriendo** | Ningún proceso escuchaba en 8765. El registro (`data/logs/terminal.log`) termina a las 14:09 sin traza de error: el proceso se cerró desde fuera (reinicio de otra sesión, cierre de la ventana o del equipo), no por una falla | **Resuelto**: se arrancó con el lanzador y responde |
| 2 | Dos servidores de verificación de otra sesión en los puertos **8770 (modo demo)** y **8771 (modo real con base vacía: tipo de cambio «sin datos»)** | Línea de comandos `uvicorn terminal.app:app --port 8770/8771`, iniciados a las 22:59 y 23:00 | No se tocaron (son de otra sesión). Si abres esos puertos verás datos sintéticos o nada |
| 3 | El texto «null» aparecía en Mercado (mapa de calor) y en Reto y perfil | Nodos de texto «null» en `#mercado-visualizaciones`, `#mercado-contenido` y `#reto-contenido` | **Corregido**: `limpiar()` ignora `null` y `false`, y el mapa de calor usa `limpiar()` |
| 4 | El flujo en vivo de Alpaca se reconectó unas 12 veces durante el día | `terminal.log`: `reconexión 1…12 (ErrorFlujo, ConnectionClosedError, TimeoutError, gaierror)` | Sin cambio. El plan gratuito permite **una** conexión WebSocket por clave: si otro servidor con el motor encendido usa la misma clave, se desconectan entre sí. Probable, no comprobado. La red también falló a las 11:05 (`gaierror`) |

## Comprobado

- Base `data/terminal.db`: `PRAGMA quick_check` = ok; 370,850 precios hasta el 2026-10-19; última captura del 19-oct a las 14:30 ($917,413.67).
- Con la terminal arrancada, las 24 pestañas cargaron contenido en el navegador, sin errores de JavaScript ni esqueletos de carga pendientes.

## Recomendación

Abre siempre la terminal con el lanzador (`launcher\ActinverTerminal.exe`), que usa el puerto 8765 y tus datos reales. Si una página no muestra datos, revisa primero que la dirección sea `127.0.0.1:8765` o `localhost:8765`.
