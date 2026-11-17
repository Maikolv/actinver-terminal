# Auction Market Theory · implementación local

Revisión: 19 de octubre de 2026. AMT organiza hipótesis de aceptación, rechazo y búsqueda de valor; no demuestra por sí misma una ventaja estadística.

## Qué funciona

| Proyecto | Entrega | Alcance comprobable |
|---|---|---|
| Actinver-terminal | Order Flow → Auction Market Theory | Tabla por sesión, rejilla configurable, POC TPO observado, VAH/VAL previos, IB, cobertura y contexto |
| API existente | `/api/flujo/perfiles?simbolo=…&paso_precio=0.25` | Campo `subasta`; sólo lectura; errores 422 para rejilla inválida |
| Módulo de la terminal | `terminal/flujo/subasta.py` y `tests/test_subasta.py` | Mismo cálculo que ve la interfaz; reproducible con CSV propio o barras de prueba; no órdenes |
| TradingView | `tradingview/actinver_amt.pine` | Indicador Pine v6 para niveles previos introducidos manualmente, IB y alertas al cierre; compilado, añadido al gráfico y guardado en TradingView como «Actinver AMT - Contexto RTH v1»; pendiente validar señales con niveles reales de futuros |

Se conservan los cálculos de volumen y delta existentes. No se reemplazan por TPO ni se asigna volumen de una vela a precios inventados. La terminal tampoco se convierte en canal de órdenes.

## Equivalencias en la terminal

| Herramienta típica de una plataforma de futuros | Dónde está en Actinver Terminal |
|---|---|
| Gráfico TPO / Market Profile | Order Flow › TPO (letras por bloque de 30 min, POC, VA, IB) |
| Perfil de volumen (POC, VAH, VAL) | Order Flow › Perfil de volumen |
| Footprint / clusters bid × ask | Order Flow › Footprint (Bid × Ask, volumen, delta) |
| DOM / libro de órdenes | Order Flow › Libro (mejor bid/ask IEX; libro completo por CSV con licencia) |
| Time & sales | Order Flow › Operaciones (cinta) |
| Delta acumulado | Order Flow › Delta |
| Indicadores técnicos | Velas (SMA, EMA, Bollinger, VWAP, MACD, estocástico, SAR, RSI) |
| Calculadora de riesgo por contrato | Mesa › Plan de riesgo NQ (escenarios listos) |
| Alertas | Alertas (escritorio y Telegram) y receptor `/webhook/tradingview` |
| Backtest y optimización | Backtesting, Robustez y Laboratorio sin conexión (Datos y fuentes) |
| Espacio de trabajo con paneles | Mesa de investigación (paleta Ctrl+K, disposiciones guardadas) |

Ninguna de estas secciones envía órdenes.

## Convención reproducible

- Sesión de referencia: RTH 09:30–16:00, `America/New_York`; cripto conserva 00:00–24:00 de la zona ya configurada por la terminal. No es un perfil Globex. Las sesiones nocturnas necesitan otro adaptador.
- Python: OHLC de barras cerradas de 1, 5 o 15 minutos; una marca por cubeta fija y bloque de 30 minutos. No interpolar rangos. Es una **cota inferior de TPO**, no Market Profile completo de ticks.
- Rejilla anclada en cero; paso configurable en terminal. 0.25 es la rejilla de investigación inicial para MES/ES/MNQ/NQ; para otros instrumentos hay que elegir y contrastar el paso. No equivale a verificar el tick contractual.
- POC: cubeta con más TPO; en empate, la inferior. Su valor mostrado es el centro de la cubeta, por lo que puede no ser un precio negociable. VA: expansión contigua desde POC hasta cubrir al menos 70%; incluye ambos vecinos en empate y atraviesa huecos con peso cero. No coincide necesariamente con algoritmos de otros proveedores.
- IB: máximo/mínimo de la primera hora, publicado sólo si se observaron todas sus barras cerradas. Una referencia previa requiere todas las barras esperadas y cierre de sesión pasado. Una sesión parcial intermedia invalida el arrastre de referencia.
- Aceptación: dos cierres consecutivos y sin hueco temporal fuera del valor previo. Rechazo: última barra explora fuera y cierra dentro; si barre ambos extremos se etiqueta aparte. Rotación: cierre dentro sin barrido. Fuera sin confirmación: exploración.
- Disponibilidad: descartar barras abiertas, futuras o publicadas después del corte. El perfil de hoy es descriptivo; la clasificación usa exclusivamente el valor previo congelado. No usar el perfil final de hoy para justificar una entrada anterior.
- No están implementados un clasificador completo de tipos de día, single prints auténticos, poor highs/lows ni calendario de festivos/cierres anticipados. No se infieren de cuatro precios por vela.

## Usarlo

1. En terminal, abrir **Order Flow**, elegir instrumento y rejilla. Importar barras con licencia desde **Velas** si faltan. La tabla no inventa niveles cuando no hay datos.
2. Revisar cobertura y fecha de referencia antes de interpretar un estado. El origen de los datos se conserva en el panel. Un estado descriptivo no es permiso de entrada.
3. En la misma terminal: **Order Flow** muestra el perfil TPO por letras (bloques de 30 minutos), el perfil de volumen con POC/VAH/VAL, el footprint bid × ask y el delta; **Velas** añade VWAP, medias y osciladores sobre las mismas barras; **Mesa › Investigación de futuros** reúne gráfica, calendario, Order Flow, opciones, el plan de riesgo NQ y la robustez en una sola vista.
4. TradingView: copiar el Pine al editor y compilar. Utilizar velas temporales normales de 1/5/15 minutos, sesión RTH y datos del contrato correcto. Introducir VAH/VAL/POC de la sesión anterior completa; indicar su fecha de cierre y la ventana de validez de la sesión actual. Ceros, fechas o límites inválidos desactivan el contexto. Renovar niveles cada sesión. No usar datos del contrato continuo para enviar órdenes.
5. Crear alertas **al cierre** si se desea. El JSON tiene el esquema del receptor informativo existente `/webhook/tradingview`, pero éste sólo acepta instrumentos de su catálogo: **los futuros CME no están habilitados en ese receptor**. Para futuros, usar inicialmente notificaciones de TradingView; un receptor separado de futuros requiere implementación y pruebas. No desactivar la validación del catálogo para forzar compatibilidad. Una alerta no genera una orden ni garantiza entrega. No exponer credenciales en Pine, repositorios, capturas o URLs.

## Reproducir sin cuentas

Todo dentro de Actinver Terminal, sin cuentas ni plataformas externas:

1. **Velas › Importar CSV** con barras de 1, 5 o 15 minutos que tenga derecho a usar.
2. **Order Flow** con ese instrumento y la rejilla deseada: la tabla AMT, el TPO y el perfil se calculan solos.
3. Por API local, la misma lectura: `GET /api/flujo/perfiles?simbolo=…&intervalo=5Min&paso_precio=0.25` (campo `subasta`).
4. Pruebas del cálculo: `uv run pytest tests/test_subasta.py tests/test_perfiles_sesion.py`.

CSV mínimo: `inicio,intervalo,apertura,maximo,minimo,cierre`. Fechas ISO con zona, intervalo `1Min`, `5Min` o `15Min`; `disponible_desde` opcional. No mezclar contratos, ajustes de rollover o proveedores. La procedencia de un CSV externo sigue requiriendo verificación humana.

## Recursos primarios consultados

- [TradingView TPO](https://www.tradingview.com/support/solutions/43000713306-time-price-opportunity-tpo-indicator/): referencia visual y alertas de perfiles completados.
- [Pine alertas](https://www.tradingview.com/pine-script-docs/concepts/alerts/): condiciones y configuración del usuario.
- [Pine datos/footprint](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/): existe `request.footprint`, restringido a planes compatibles; categoriza volumen mediante acción intrabar, no asumir agresor de bolsa. No se requiere para este Pine básico.
- [CME ES](https://www.cmegroup.com/markets/equities/sp/e-mini-sandp500.contractSpecs.html), [NQ](https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.contractSpecs.html), [micro E-mini](https://www.cmegroup.com/markets/equities/micro-emini-equity.html): contrastar metadatos y contratos en fuente oficial.

Una estrella de GitHub no certifica utilidad, licencia ni funcionamiento. Los repositorios se reutilizan por capacidad concreta, sin instalar todos los motores a la vez.

## Evidencia de esta entrega

- 72 pruebas Python de terminal (AMT, perfiles, flujo e intradía): pasan.
- 3 pruebas de navegación: pasan. Interfaz comprobada con un fixture sintético aislado; sin desbordamiento horizontal a 390 px.
- Pine: compilado, cargado y guardado en la cuenta existente de TradingView; sin alertas activadas. Prueba negativa observada con niveles cero/timeframe diario: «NO EVALUAR». No se afirma validación de señales ni de ejecución sobre datos de futuros.

El ejemplo de interfaz emplea un instrumento del catálogo y precios inventados explícitamente etiquetados; no añade un feed CME a la terminal.
