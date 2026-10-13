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
