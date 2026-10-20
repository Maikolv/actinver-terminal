# Auditoría: qué falta para que la terminal funcione en su totalidad — 20-oct-2026

Cada punto distingue **lo que ya funciona**, **lo que falta** y **quién lo resuelve**: el usuario (ajustes del equipo,
cuentas o pagos, que no se hacen sin su decisión) o el código. Datos medidos hoy salvo indicación.

## 1. Operación diaria (prioridad alta)

| Tema | Estado | Qué hacer | Quién |
|---|---|---|---|
| Terminal encendida | Estuvo apagada del 20-oct a las 00:54 hasta las 14:50: la PC se suspendió a las 03:54 y despertó a las 11:11 sin reabrir la terminal. Sin terminal no hay descargas, ni avisos de pérdida, ni plan actualizado | (a) Configurar la energía de Windows para no suspender en horario de mercado (07:00–15:30). (b) Opcional: abrir `launcher\ActinverTerminal.exe` al iniciar sesión (carpeta Inicio o Programador de tareas) | **Usuario** (son ajustes del sistema) |
| Una sola terminal | La otra sesión levanta servidores de prueba (puertos 8766–8771). Si tienen el motor encendido, compiten por la única conexión en vivo de Alpaca y por la base | Usar solo el puerto 8765 para operar. Los servidores de prueba deben arrancar con `TERMINAL_SIN_MOTOR=1` | Usuario y sesiones de desarrollo |
| Captura del portal | Funciona: 14 capturas confirmadas. Desde hoy, una captura tomada después de las 14:00 también sirve de cierre BMV de respaldo | Capturar después del cierre (14:00–14:30) y, si se opera, después de cada operación | Usuario |
| Plan por Telegram | Funciona («enviada»). Correo sin SMTP | Opcional: configurar SMTP en `.env` | Usuario |
| Avisos de pérdida | Funcionan solo con la terminal encendida y el mercado abierto | Ver el primer punto | — |

## 2. Datos

| Tema | Estado | Qué falta | Quién |
|---|---|---|---|
| Cierres BMV | EODHD gratis: 20 consultas al día (la terminal usa 18; el cupo se renueva a medianoche UTC, 18:00 CDMX). **28 de 46 emisoras BMV activas no tienen precio de los últimos 7 días.** Tus posiciones BMV ya tienen respaldo con el precio del portal | (a) Importar el PDF de la pestaña Acciones del simulador con `uv run terminal precios-portal <pdf>` (gratis, cubre todo el catálogo ese día). (b) EODHD de pago (USD 19.99 al mes) | Usuario (a: acción manual; b: decisión de pago) |
| SIC y ETF | Tiingo (cierres) y Alpaca IEX en vivo, hasta 30 símbolos, con reconexiones frecuentes (12 el 19-oct) | Una sola terminal con el motor encendido | Usuario y sesiones |
| Fondos | NAV oficiales con 16 sesiones de historia: el ranking los marca «historia corta» y las propuestas los ponderan con poca evidencia | Se resuelve solo con el tiempo, o importando historia autorizada de los fondos | — |
| Tipo de cambio | Banxico FIX al día | Nada | — |
| Tiempo real BMV | No existe fuente gratuita | Proveedor de pago | Usuario (decisión) |
| Opciones con OI y cinta completa (GEX, Skylit) | Parcial: contratos Paper de Alpaca (OI del cierre previo) apagados por omisión; sin NBBO histórico ni patas | Proveedor OPRA de pago, o dejarlo como herramienta educativa | Usuario (decisión) |

## 3. Funciones que dependen de credenciales opcionales

| Función | Estado | Para activarla |
|---|---|---|
| Asistente con redacción propia (Claude) | Responde con fragmentos de la documentación: no hay `ANTHROPIC_API_KEY` | Clave de Anthropic (de pago por uso) **o** Ollama local gratuito (`OLLAMA_URL`) |
| CoinGecko (referencia cripto) | Sin clave | `COINGECKO_DEMO_API_KEY` (gratis, opcional) |
| Finviz Elite | Apagado | De pago (USD 39.50 al mes) |
| Monitor en la nube (Cloudflare) | URL y secreto configurados. Hoy hubo «sin_conexion» y un «database is locked» al sincronizar, cuando otra escritura usaba la base al mismo tiempo | Revisar que el relevo avise si la terminal se cae (era el objetivo del monitor) |

## 4. Calidad del software

- Integración continua en GitHub: las últimas 3 corridas en verde.
- Suite local: ≈ 650 pruebas. Los fallos del 18-oct del trabajo de otra sesión ya quedaron integrados.
- Pendiente de código: `database is locked` esporádico cuando dos procesos escriben a la vez (la terminal y un script
  manual). Mitigación: reintentar la sincronización con la nube en vez de registrar el error.

## 5. Modelo y decisiones

- Ningún modelo tiene ventaja demostrada frente a repartir en partes iguales (V1, pronóstico, Kronos, TSM). La
  terminal informa; las decisiones de compra y venta son del usuario.
- Decisiones abiertas: la referencia del plan frente a 1/N, las 9 propuestas de revisión del mandato y las fuentes de
  pago.

## 6. Hecho hoy

- Respaldo del cierre BMV con la captura del portal (`portal.cierres_desde_captura`, proveedor `actinver_portal`,
  prioridad 13, por debajo de EODHD). Se aplicó a las capturas guardadas: 29 cierres; ALPEK y GMEXICO al 19 y 20-oct.
  El plan dejó de usar precios del 16-oct. 3 pruebas nuevas.
- La terminal se reinició a las 14:50.
