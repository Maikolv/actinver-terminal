# Memoria del proyecto

Contexto duradero para cualquier persona o agente que retome el trabajo: hechos no evidentes, decisiones y lecciones. Lo que ya registran el código, git o [decisiones.md](decisiones.md) no se repite aquí. Sin secretos ni datos personales: las credenciales y los hosts privados viven solo en `.env`.

## Contexto

- Proyecto personal para el **Reto Actinver 2026**; competencia del 5-oct al 13-nov-2026. Repositorio privado en GitHub.
- La terminal corre como **proceso independiente**: `uv run terminal iniciar --sin-navegador`, con registros en `data/terminal_*.log` y `data/logs/terminal.log`. Las vistas previas de herramientas de desarrollo pueden detenerse solas; si el acceso remoto da 502, la terminal no está corriendo.
- Hay **varias sesiones de trabajo en paralelo** sobre el mismo repositorio. Antes de editar, revisar `git status` y el contenido actual de los archivos.

## Fuentes de verdad

| Tema | Fuente |
|---|---|
| Reglas | Bases oficiales (URL en [RULES.md](RULES.md)); no usar las de 2025 |
| Instrumentos operables | Capturas del simulador del usuario («Datos Actinver.pdf», 22-sep-2026) → `config/pdf_transcripcion.csv` |
| Saldo real | Solo la captura que el usuario copia del portal. El millón local es un registro, no un saldo |
| Precios de fondos | Hoja diaria oficial de Actinver en PDF (fecha de valuación dentro del documento) |
| Tipo de cambio | FIX de Banxico; FRED como respaldo |

## Lecciones aprendidas (errores que no deben volver)

1. **Splits y dividendos**: «sin dividendos» no significa «sin ajustar». Un cierre crudo convierte un split en un salto ficticio (FUBO +994 %). Durante el Reto se usa `ajustados="splits"`.
2. **Saltos únicos reales** (FUBO +245 % por fusión, 6-ene-2025; MRNA +175 %, 19-ago-2026, con volumen 45× el normal) no se repiten: no deben extrapolarse a medias ni a escenarios.
3. **Cabeceras HTTP solo en ASCII**: httpx rechaza «ú», y el error tiraba el ciclo completo. Cada fuente se aísla con `try/except` para que un fallo no detenga precios ni propuestas.
4. **Fechas sin hora**: una fecha sola no es medianoche UTC; usar la hora de cierre de la sesión (`cotizaciones.hora_cierre`).
5. **Nombres de EODHD**: Peñoles es `PE&OLES`; conservar `&` y `-` y codificarlos en la URL.
6. **Cupos**: el plan gratuito de EODHD (20 consultas por día) se agota con actualizaciones. Hay una reserva de 6 para emisoras nunca cargadas y, si se agota un proveedor, se pasa al siguiente.
7. **Hoja de fondos**: un pie de página pegado («ACTIG+2 -Morningstar») asignaba precios al fondo equivocado. Solo se acepta fondo y serie exactos; si hay ambigüedad, no se asigna.
8. **Envíos**: un plan solo cuenta como entregado si Telegram confirma. Un fallo se reintenta cada 10 minutos.
9. **Universo del simulador vacío = sin restricción**: antes de proponer durante el Reto, verificar que `universo_simulador` tenga filas.
10. **Horario**: `exchange_calendars` fija la BMV en 08:30–15:00; el Reto (y la BMV) operan 07:30–14:00 hasta el 2-nov. Usar siempre `vigencia.apertura_sesion` / `cierre_sesion` / `mercado_abierto`, nunca `session_open/close` directo.
11. **Optimismo dentro de muestra**: la volatilidad de pesos optimizados en su propia muestra subestima el riesgo (16.6 % frente a 42.5 % fuera de muestra). Los escenarios usan la menos optimista de ambas.
12. **Selección por puntuación**: «Máxima puntuación» elige con la primera mitad de la validación; su total puede quedar debajo de «Ajuste» y puede rendir menos que 1/N. No es un error de código.
14. **Reiniciar el servidor por el puerto, no por el nombre**: `uv run terminal iniciar` deja un `python.exe -m terminal iniciar` escuchando en 8765; detener solo `terminal.exe` lo deja vivo con el código viejo (y el lanzador cree que ya está encendido). Detener el proceso dueño del puerto 8765 y verificar la hora de inicio.
13. **Respaldos**: no existía ninguno hasta el 30-sep; ahora el motor hace uno verificado al día en `data/respaldos`.

## Decisiones vigentes (resumen)

- Tres lentes (rendimiento, ajuste, máxima puntuación) × dos universos. El plan del día usa la propuesta principal mejor puntuada; las variantes nacionales y extranjeras son informativas.
- Banda de no-rebalanceo de 2 pp. Boletas limitadas del día con ±0.2 % sobre el precio confiable. Referencia condicional con ±2 %.
- El plan del día sale en cuanto hay cierres de la última sesión, con respaldo a las 07:00. Admite hasta 2 correcciones antes de la apertura.
- Alertas «posible movimiento» silenciadas de 21:00 a 07:00; se incluyen en el plan.
- Chatbot: Claude si hay `ANTHROPIC_API_KEY`; si no, Ollama local; si no, ficha de datos. Máximo 20 por hora.

## Estado de integraciones (30-sep-2026)

| Integración | Estado |
|---|---|
| Tiingo, EODHD (gratuito), Banxico, hoja de fondos Actinver, RSS de Seeking Alpha, Telegram, Tailscale | Activos |
| FRED | Respaldo; timeout el 24-sep |
| Infosel, BMV/SiBolsa, Edimex, Twelve Data, Alpaca, Barchart, LSEG, ICE | Pendientes de contrato o clave; no simular que están activos |
| Correo, Claude | Sin configurar |

## Situación de la cuenta

Sin captura del portal al 30-sep-2026: **saldo no conciliado**. La competencia reinicia el saldo el 5-oct, así que hará falta una captura nueva ese día.
