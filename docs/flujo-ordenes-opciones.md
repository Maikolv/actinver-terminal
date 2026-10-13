# Velas, Order Flow y Option Flow (etapa 1)

Paquete `terminal/flujo/` (12-oct-2026). Solo lectura, análisis y simulación: **ninguna ruta envía órdenes** (lo
comprueba `tests/test_seguridad.py::test_no_existen_rutas_de_ordenes_reales`).

## Cómo usarlo

1. Abre la terminal (`launcher\ActinverTerminal.exe` o `uv run terminal iniciar`) y ve a **Más**.
2. **Velas**:
   - elige el instrumento, el intervalo (1 min a 1 día) y el rango;
   - pulsa **Actualizar desde proveedor**;
   - activa SMA 20, Bollinger o VWAP.

   Al pasar el puntero sobre una vela ves su OHLCV, la fuente y el retraso.
3. **Order Flow**:
   - elige un instrumento y pulsa **Actualizar libro** y **Actualizar operaciones**;
   - el panel muestra el libro por niveles, la profundidad, el desequilibrio, la cinta, el delta de volumen (si hay
     lado) y el perfil de volumen.
4. **Option Flow**:
   - elige un subyacente del SIC y pulsa **Actualizar cadena desde proveedor**;
   - filtra por vencimiento, tipo, strike, volumen, interés abierto o |delta|;
   - la regla de volumen inusual se configura en el mismo panel;
   - el botón **Al modelo** lleva un contrato al panel Black-Scholes-Merton.
5. **Mercado** (mapa de calor):
   - ventana de 1, 5 o 20 sesiones;
   - filtros por mercado, clase, sector y proveedor;
   - al seleccionar una celda se abre su ficha (método, cierres usados, fuente, captura, rezago y calidad), con enlace
     a sus velas.

Atajos de la barra de comandos: `/VEL`, `/OF`, `/OPC` y `/MER`.

Las consultas se hacen solo cuando pulsas un botón. No hay procesos en segundo plano. Hay un límite por símbolo:
- 60 s para velas;
- 30 s para operaciones;
- 5 s para el libro;
- 120 s para opciones.

## Fuentes y calidad

| Panel | Fuente | Qué entrega | Retraso | Limitación |
|---|---|---|---|---|
| Velas SIC | Alpaca, consolidado SIP | OHLCV ajustado por splits, de 1 min a 1 día | **≥ 15 min** (se pide así para usar el plan gratuito) | Precio de origen en USD, no el del SIC en MXN |
| Velas cripto | Exchange público (Bitso por omisión) | OHLCV | La última vela puede estar en formación | Fuera del Reto |
| Libro SIC | Alpaca IEX | **Solo el mejor bid/ask de IEX** (1 nivel) | Medido con la hora de la cotización | IEX ≈ 2–3 % del volumen; no es profundidad |
| Libro cripto | Exchange público vía ccxt | Hasta 50 niveles por lado | Medido con la marca de tiempo del exchange | — |
| Cinta SIC | Alpaca SIP histórico | Operaciones | ≥ 15 min | **Sin lado del agresor**: no hay delta |
| Cinta cripto | Exchange público | Operaciones con lado del agresor | Medido | — |
| Opciones | Alpaca, feed «indicative» de OPRA | Bid/ask, último, volumen diario, IV y griegas cuando las trae | Diferido (~15 min) | **Sin interés abierto**; si falta la IV se calcula (origen «calculado») |
| Todo | CSV importado por ti | Lo que tengas derecho a usar | El que declares | La terminal no verifica la fuente |

Cada dato se guarda con su procedencia completa: fuente, licencia, mercado, feed, calidad (`proveedor`, `importado`,
`calculado` o `sintetico`), retraso, nota, hora de captura y `disponible_desde`. Esta última permite reproducir lo que
se sabía en una fecha. En modo real nunca aparecen datos sintéticos, y los paneles **no simulan** flujo cuando falta
una fuente.

## Cálculos (todos descriptivos)

| Cálculo | Definición |
|---|---|
| SMA 20 | Media simple de 20 cierres |
| RSI 14 | **Wilder**: promedio simple inicial y después suavizado `(n−1)/n`, el mismo de TradingView |
| Bollinger | Media de 20 ± 2 desviaciones poblacionales |
| VWAP | Anclado a la primera barra del rango, con precio típico (H+L+C)/3 |
| Desequilibrio del libro | (Σ tamaño bid − Σ tamaño ask) / total, sobre los niveles mostrados |
| Delta de volumen | Σ compras − Σ ventas del agresor. Solo si el proveedor informa el lado de **todas** las operaciones; nunca se infiere |
| Perfil de volumen | Volumen por cubeta de precio (24 cubetas en el rango observado) |
| IV calculada | BSM europeo sobre el punto medio bid/ask, con la tasa FRED DGS2 más reciente (o 4 % declarado) y sin dividendos. Las opciones de EE. UU. son americanas |
| Volumen inusual | Volumen ≥ mínimo y, con interés abierto, volumen/interés abierto ≥ razón; sin interés abierto, volumen ≥ percentil de la cadena. **Regla descriptiva, no recomendación** |
| Mapa de calor | Cierre más reciente / cierre de N sesiones antes − 1, ajustado solo por splits y con la prioridad única de fuentes |

## Importar CSV

Las plantillas se descargan en cada panel (`/api/flujo/plantilla/{velas|operaciones|libro|opciones}`). Reglas:
- UTF-8, hasta 5 MB y 50,000 filas;
- encabezados exactos y en orden;
- instantes ISO 8601 **con zona horaria** y no futuros;
- precios > 0;
- libro sin cruzar y OHLC consistente;
- IV como fracción (0.35 = 35 %).

Es todo o nada: una fila inválida rechaza el archivo e indica su número. La fuente y la licencia que declares se guardan
con cada fila.

## Pruebas
- `tests/test_flujo.py`:
  - instantes, OHLC y libro inválidos;
  - RSI de Wilder contra una referencia independiente y el valor publicado (70.46);
  - Bollinger y VWAP;
  - delta solo con lado;
  - regla de volumen inusual;
  - importación todo o nada;
  - sin fuga temporal;
  - adaptadores de Alpaca y cripto con respuestas simuladas (la clave nunca va en la URL);
  - estados vacíos;
  - API protegida con CSRF.
- `tests/test_visualizaciones_mercado.py`: mapa con prioridad única y ventanas.

# Etapa 2: adaptadores de repositorios (12-oct-2026)

Cada adaptador tiene su contrato de entrada y salida, un interruptor en `config/local.toml` (`[flujo.<nombre>] activo`),
manejo de errores sin secretos y pruebas en `tests/test_flujo_etapa2.py`.

| Adaptador | Repositorio de referencia | Método | Entrada → salida | Interruptor | Límite |
|---|---|---|---|---|---|
| Libro y cinta de cripto | `ccxt` (MIT) | Dependencia opcional (grupo `cripto`) | Par → libro, operaciones y velas con procedencia | `[flujo.cripto]` | El del exchange + 5–60 s por símbolo |
| Exportación a `hftbacktest` | `hftbacktest` (MIT) | Formato documentado de eventos (`event_dtype`), sin importar su código | Libro y operaciones guardados → `.npz` con la llave `data` | `[flujo.hftbacktest]` | Bajo demanda |
| Velas de TradingView, OpenBB o Yahoo | `OpenBB` (AGPL: solo sus archivos exportados) y TradingView | Detección de columnas y paso por la validación de la plantilla | CSV exportado → velas «importado» | `[flujo.externos]` | 10 importaciones/min |
| Modelo de Heston | `Heston-Calibration` (sin licencia: solo lectura) | Código propio desde los artículos publicados | Cadena guardada → parámetros, error y avisos | `[flujo.heston]` | 1 calibración cada 30 s por subyacente |

## Heston

- **Pricer:** función característica en la forma de Albrecher et al. (2007), probabilidades P1/P2 de Heston (1993) e
  integración de Gauss-Legendre (256 nodos en [0, 250]); las puts salen por paridad.
- **Verificación:** con σ → 0 y v0 = θ = σ²_BS reproduce Black-Scholes (error < 1e-5). Con una cadena sintética
  recupera los 5 parámetros exactos.
- **Calibración:**
  - mínimos cuadrados con límites sobre ≤ 60 contratos fuera del dinero, de 7 a 180 días, con bid/ask e IV;
  - residuo = (precio modelo − precio medio) / vega BS, que aproxima el error en puntos de volatilidad;
  - tasa FRED DGS2 y sin dividendos.
- **Avisos visibles:**
  - Feller incumplido;
  - parámetros en su límite (posible falta de identificación);
  - error medio mayor a 5 puntos.
- **Resultado real con MU (12-oct):** convergió con 60 contratos y un error medio de 3.7 puntos, pero σ quedó en su
  límite (5) y no cumple Feller. La terminal lo muestra como advertencia: la superficie de MU, con el subyacente de
  cierre y las cotizaciones diferidas, no queda bien descrita por un solo Heston.

## Exportación a `hftbacktest`

Descarga: el botón **Exportar a hftbacktest (.npz)** en Order Flow, o `GET /api/flujo/hftbacktest?simbolo=…`.
- El libro se exporta como `DEPTH_CLEAR` + `DEPTH_SNAPSHOT` por nivel; las operaciones, como `TRADE_EVENT`, con
  `BUY`/`SELL` solo si la fuente informó el lado.
- Marcas en nanosegundos: `exch_ts` es la hora del evento y `local_ts` la hora de captura (≥ `exch_ts`).
- **Limitación:** las instantáneas se capturan al pulsar «Actualizar», así que no forman un libro continuo. Sirven para
  validar el formato o estrategias lentas, no para colas de alta frecuencia. La terminal no ejecuta `hftbacktest`.
