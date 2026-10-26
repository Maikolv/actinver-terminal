# Auditoría 25-oct-2026 y prompt de mejoras

Medido hoy (domingo, mercados cerrados) sobre `main` con la terminal real en `127.0.0.1:8765`.

## Hecho en esta sesión

- **Velas en movimiento dentro de la terminal.** El widget oficial de TradingView ya existía, pero solo se abría desde la
  ficha del mapa de Mercado, en otra pestaña y con velas diarias. Ahora aparece en **Mercado y flujo → Velas** al elegir un
  instrumento con símbolo en TradingView, con selector de 1 min, 5 min, 15 min, 1 h o diario. La página `/grafica/{id}`
  acepta `?intervalo=` (lista cerrada) y solo el mismo origen puede enmarcarla (`frame-ancestors 'self'`,
  `X-Frame-Options: SAMEORIGIN`). Comprobado en el navegador: MU (NASDAQ) con velas de 1 min de Cboe One. Prueba nueva:
  `tests/test_grafica_vivo.py`.
- **Versión correcta.** `terminal.__version__` decía 0.1.0 y sellaba así los backtests y las evaluaciones; ahora sale de
  `pyproject.toml` (0.31.0).

## Qué muestra y qué no el widget de TradingView

| Mercado | Dato que ve | Nota |
|---|---|---|
| Acciones y ETF de EE. UU. (SIC) | Cotización gratuita de Cboe One, en USD | No es el consolidado completo; el Reto valúa en MXN con el precio del SIC |
| BMV | Con el retraso que indique TradingView (sin suscripción de datos) | No hay tiempo real BMV gratuito |
| Fondos | Sin gráfica | Solo NAV diario |

Los datos van del navegador a TradingView; la terminal no los guarda ni los usa en cálculos.

## Hallazgos (mayor impacto primero)

1. **Motor automático sin ciclo guardado desde el 21-oct 00:49 UTC.** `/api/estado.motor.ultimo_ciclo` no cambió aunque
   la terminal funcionó el 23-oct. Hoy (25-oct) estaba apagada otra vez; tras arrancarla, el ciclo terminó en 817 s
   (344 datos nuevos). El estado solo se guarda al final del ciclo, así que una terminal que se cierra o una PC que se
   suspende en esos ≈ 14 min no deja registro.
2. **Los registros se borran en cada arranque.** `scripts/iniciar-remoto.ps1` redirige la salida a
   `data/terminal_{salida,errores}.log` sobrescribiendo; tras un reinicio no hay rastro de fallos del motor ni del
   `database is locked` de la sincronización con la nube.
3. **Vigencia:** 182 instrumentos vigentes, 29 vencidos, 2 retrasados y 1 sin datos (de 214 activos). EODHD gratuito
   (20 consultas al día) no alcanza para toda la BMV.
4. **Estado de proveedores viejo:** FRED muestra como última corrida un error de red del 24-sep. El tipo de cambio sale
   bien de Banxico, pero el panel confunde.
5. **Velas propias de la terminal:** gráfica SVG estática, se actualiza a mano y usa SIP con ≥ 15 min de retraso. El
   flujo IEX en vivo (`terminal/tiempo_real.py`) ya recibe precios, pero no actualiza la última vela.
6. **Concentración:** MU pesa 46 % de la cartera (límite del Reto: 50 %). Es un dato de riesgo, no una orden.
7. **Documentación:** en `CLAUDE.md`, la brecha 3 aún dice «última captura del 16-oct», y el encabezado de «Estado
   comprobado» sigue fechado el 18-oct.

## Decisiones del usuario (no se hacen sin su aprobación)

- Energía de Windows para no suspender entre 07:00 y 15:30, o abrir la terminal al iniciar sesión (ajuste del sistema).
- Fuentes de pago: EODHD (cierres BMV completos) o un proveedor de tiempo real BMV.
- Suscripción de datos en TradingView, si se quisiera BMV sin retraso en el widget (es de TradingView, no de la terminal).

## Prompt para la siguiente sesión

```text
Trabaja en C:\Users\MIKE\Desktop\Repos\actinver-terminal (Actinver Terminal, Reto Actinver 2026). Lee CLAUDE.md y
docs/auditoria-2026-10-25.md. Respeta el mandato v2: sin órdenes reales, secretos solo en .env, solo 127.0.0.1, no
presentes datos retrasados como tiempo real, no automatices el portal del Reto, no contrates nada y no incluyas en tus
commits el trabajo sin commitear de otras sesiones (TradingView, reels, NQ).

Resuelve, en este orden, con una prueba por cambio y la suite completa al final:
1. Motor: averigua por qué /api/estado.motor.ultimo_ciclo no avanza desde el 21-oct. Guarda en la base el inicio de
   cada ciclo (no solo el final) y muestra en la cabecera «motor sin ciclo desde …» si pasan más de 2 h con el mercado
   abierto.
2. Registros: que iniciar-remoto.ps1 no sobrescriba los logs; rota a data/logs/ con fecha y conserva 14 días.
3. Sincronización con la nube: reintenta con espera cuando SQLite responda «database is locked» en vez de registrar un
   error.
4. Proveedores: en el panel, no muestres como estado actual un error de un proveedor que no corre desde hace más de
   7 días; márcalo «sin uso reciente».
5. Velas propias: cuando el flujo IEX en vivo esté activo, actualiza la última vela del intervalo elegido con los
   precios que llegan (SSE desde el servidor, sin escribir velas falsas en la base), con la etiqueta «IEX en vivo,
   volumen parcial». Si no hay flujo, deja la gráfica como está.
6. Cobertura BMV: prioriza en la cuota diaria de EODHD las emisoras con posición abierta o en una propuesta activa, y
   muestra cuántas quedaron sin cierre.
7. Corrige CLAUDE.md (brecha 3 y fecha de «Estado comprobado»).
Al terminar, actualiza CHANGELOG.md y docs/historial-estado.md con métricas (pruebas, vigencia, ciclos del motor).
```
