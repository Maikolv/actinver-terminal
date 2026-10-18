# Prompt maestro: Quantower, investigación y práctica

Copia el texto de la siguiente sección en Claude Code desde un proyecto de trabajo. Esta entrega no activa operaciones reales. La estrategia es una hipótesis que debe competir con referencias y sobrevivir validación; no se ha demostrado alfa.

## Prompt listo para usar

Actúa como ingeniero cuantitativo y docente de microestructura. Trabaja en Windows con Quantower y C#, usando exclusivamente las API disponibles en la versión instalada. Primero verifica versión, conexión, instrumentos, licencias y SDK reales; nunca inventes métodos ni resultados. Produce un sistema que opere automáticamente en SIMULADOR y un material de práctica. Para un futuro modo real prepara una integración separada y deshabilitada, que requiera configuración y activación explícita posteriores; no la actives en esta tarea.

### Contexto local que debes inspeccionar

- Terminal: `C:/Users/MIKE/Desktop/Repos/actinver-terminal`. Lee CLAUDE.md, mandato vigente, documentación de flujo, investigación, backtesting, riesgo y mejoras intradía. Usa el grafo de codebase-memory y verifica su cobertura; si está desactualizado consulta los archivos precisos.
- Repositorios: `C:/Users/MIKE/Desktop/Repos`. Inventaría URL remota, commit, licencia, entorno e integración real de hftbacktest, nautilus_trader, vectorbt, backtrader, skfolio, Heston-Calibration, orderbook, OpenBB, ccxt y demás candidatos pertinentes. Tener una carpeta no significa que esté instalado ni que su licencia permita copiarlo. No ejecutes todos ni integres todos: justifica cada dependencia.
- No leas ni exportes `.env`, credenciales, bases de cartera o documentos privados para ilustrar ejemplos. Usa fixtures sintéticos rotulados y exportaciones autorizadas.
- La terminal de Actinver informa y simula; no le añadas un canal de órdenes al portal del Reto. El bot de futuros será un proyecto separado.
- Revisa el informe de Instagram de esta entrega. Distingue afirmaciones del autor, criterios transcritos, errores de transcripción y mejoras propias. Si faltan las imágenes adjuntas, decláralo y deja un apartado para incorporarlas; no inventes su contenido.

### Proveedores gratuitos y herramientas visibles en la misma terminal

Investiga y presenta una lista actualizada de proveedores con acceso gratuito utilizable desde Actinver-terminal. Consulta documentación oficial vigente, cita enlaces y fecha de revisión, y distingue plan gratuito permanente, prueba temporal, acceso institucional y software gratuito que requiere datos de pago. Examina primero los conectores y proveedores ya implementados en la terminal para reutilizarlos. Como candidatos de investigación, revisa Alpaca, Alpha Vantage, exchanges accesibles mediante ccxt, FRED, Banxico y alternativas pertinentes; no presupongas su gratuidad, cobertura o autorización de uso actual.

Entrega una tabla con: proveedor; enlace oficial; instrumentos/bolsas y moneda; velas y temporalidades; profundidad histórica; tiempo real o retraso exacto; ticks, lado del agresor y Level 2; opciones, OI y griegas; límites de peticiones; registro/tarjeta requeridos; licencia de uso y visualización; compatibilidad con Actinver-terminal y Quantower; funciones que permite y funciones que no cubre. Señala dónde la documentación no permite confirmar una condición.

Incluye una matriz por herramienta: velas con SMA/EMA, MACD, estocástico y SAR; perfil de volumen; TPO/Market Profile; DOM y heatmap de liquidez; footprint y delta acumulado; Option Flow; GEX. Explica los datos mínimos y el cálculo de cada una. Velas OHLCV no reconstruyen el footprint ni el agresor; una cadena de opciones no sustituye el tape; volumen no sustituye OI; el heatmap de liquidez no es GEX. No declares un feed completo gratuito de CME/OPRA sin verificar derechos y cobertura. Distingue acceso gratuito a precios de una licencia para mostrarlos o redistribuirlos.

Propón una combinación gratuita mínima para visualizar las herramientas posibles dentro de la misma Actinver-terminal, con paneles vinculados por símbolo, metadatos de fuente/retraso, horarios, calentamiento y mensajes claros cuando falten datos. Indica cuáles requieren un proveedor de pago o importación de archivos autorizados y por qué. No uses datos ficticios como sustituto en modo real. Una API utilizable por la terminal no implica que Quantower tenga un conector compatible.

Implementa los conectores gratuitos pertinentes dentro de la arquitectura existente, con caché, límites de uso, validación, manejo de errores y pruebas mínimas; conserva las claves fuera del código y detalla las que deba configurar el usuario. No compres planes ni crees cuentas en esta tarea. Termina con una guía de configuración paso a paso, una matriz de disponibilidad real comprobada y un inventario de lo pendiente; no afirmes que una integración funciona sin probarla.

### 1. Configuración verificable de Quantower

Construye un workspace «Futuros — laboratorio» y documenta paso a paso cómo reproducirlo, sin comprar suscripciones ni conectar dinero real. Si Quantower no está instalado o no hay datos/licencia suficiente, entrega instrucciones precisas y el estado pendiente.

Contratos outright que debes verificar contra CME y metadatos del proveedor:

| Raíz | Mercado | USD/punto | Tick | USD/tick |
|---|---|---:|---:|---:|
| MES | Micro E-mini S&P 500 | 5 | 0.25 | 1.25 |
| ES | E-mini S&P 500 | 50 | 0.25 | 12.50 |
| MNQ | Micro E-mini Nasdaq-100 | 2 | 0.25 | 0.50 |
| NQ | E-mini Nasdaq-100 | 20 | 0.25 | 5.00 |

Selecciona contrato negociable con vencimiento concreto, conexión y cuenta de simulación correctos. No uses el continuo para enviar órdenes. Verifica horario, feriados, vencimiento y rollover; usa IANA `America/New_York`, `America/Chicago` y `America/Mexico_City`, con DST. No fijes una conversión horaria anual. Margen no equivale a pérdida máxima ni al presupuesto de riesgo.

Paneles vinculados por símbolo: velas 1/5/15 min, footprint bid×ask, volumen por precio y delta, cumulative delta con reinicio de sesión, TPO/Market Profile de sesión y previo, DOM/Time & Sales, lista de posiciones/órdenes y métricas de riesgo. Distingue POC de tiempo (TPO) del POC de volumen. Marca VAH/VAL con porcentaje y algoritmo explícitos, initial balance, VWAP y extremos previos. No confundas una orden visible en DOM con una transacción ejecutada.

Para futuros, el feed debe permitir ticks de operaciones y bid/ask y, si se usa profundidad, Level 2 histórico/en vivo apropiado. Para Option Flow se necesita tape de opciones con condiciones, timestamp, quotes NBBO y permisos; una cadena o volumen diario no revela agresor, apertura/cierre ni propósito. GEX requiere cadena, OI con fecha de publicación, gamma/modelo, spot o futuro de referencia, multiplicador, expiración y divisa. No supongas que una licencia de futuros incluye OPRA, SPX o todas las opciones.

Si usas SPX/SPY para ES o NDX/QQQ para NQ como contexto, documenta escalas, basis, horarios y desfases. No compares strikes directamente ni trasplantes el GEX de un ETF a un futuro como si fueran la misma exposición. Para opciones sobre futuros valida la definición de gamma, unidades y modelo; no apliques sin revisión una fórmula de opciones sobre acciones. OI suele reflejar una publicación posterior al cierre, no un conteo intradía de posiciones nuevas. Calls+ y puts− es una convención; no conocemos la posición de los dealers.

### 2. Hipótesis operacional y falsable

Registra por adelantado dos modelos alternativos y una versión base sin filtros de opciones:

**A. Rechazo de subasta fallida:** precio barre un extremo/VAH/VAL previo y vuelve al área; exige señal cuantificable de absorción (volumen agresor elevado y avance de precio limitado), divergencia entre precio y delta definida con ventanas pasadas y confirmación por cierre de la barra. Entrada simulada en el siguiente evento disponible, nunca en el cierre ya conocido. Stop detrás del extremo más un buffer de ticks; objetivo basado en VWAP/POC o R predefinido, sin usar un POC futuro. Probar largos y cortos como variantes contabilizadas.

**B. Aceptación y continuación:** cierre fuera del área de valor/initial balance, permanencia mínima y retesteo con volumen/delta favorables. Define de forma mecánica aceptación, retesteo, volumen relativo y expiración de señal. Stop por invalidación del retesteo; objetivo y salida temporal predefinidos.

Gamma estimada y Option Flow son filtros de contexto experimentales, no confirmaciones infalibles. Evalúa por ablación si añaden información frente al modelo base; no presumas que gamma positiva implica reversión ni que prima de calls implica compra alcista. Si faltan datos, reporta «filtro no evaluado»; no sustituyas datos inventados ni finjas ejecutar la estrategia completa.

Todos los umbrales —ventanas, ratio de imbalance, volumen relativo, expiración, stop y objetivo— deben existir en una configuración con unidades, rangos, versión e hipótesis. Un primer conjunto sólo sirve para investigación, no es óptimo conocido. No optimices contra el holdout.

### 3. Riesgo para SIMULACIÓN

Solicita capital, moneda, pérdida máxima diaria, riesgo por idea, comisiones por lado, margen, horario permitido y tolerancia a drawdown. Si faltan, usa un perfil de práctica claramente ilustrativo: riesgo por idea 0.25%, pérdida diaria 1%, máximo 3 intentos, una exposición correlacionada ES/NQ a la vez, sin martingala ni promediar pérdidas. Estos parámetros no han sido calibrados para el usuario.

Calcula contratos = floor(presupuesto_por_idea / (distancia_stop_en_puntos × valor_punto + costos_ida_vuelta + deslizamiento_estimado)), sujeto además al límite de margen disponible y riesgo agregado. Redondea el stop al tick; si el resultado es cero, NO operar. No estreches artificialmente el stop para poder comprar un mini. Un stop no garantiza precio de salida en gaps o desconexión.

Pérdida diaria incluye P&L realizado, no realizado y costos desde el inicio de sesión configurado; no se reinicia al reiniciar el bot. Limita pérdidas, exposición y cantidad en un motor independiente de la señal. Inhibe nuevas entradas ante feed retrasado, timestamps fuera de orden, secuencias perdidas, spreads excesivos, horario no permitido, volatilidad fuera del rango registrado o evento macro definido. Explica por separado cómo manejar una posición ya abierta y sus órdenes protectoras. No cancelar protección por perder la conexión. Evita eventos de alto impacto en la primera validación con una ventana explícita predefinida.

### 4. Arquitectura y pruebas

Implementa núcleo determinista de señales y riesgo separado del adaptador C# de Quantower. Verifica las firmas contra `TradingPlatform.BusinessLayer.dll` instalada y documentación oficial. Si no hay SDK, entrega un núcleo comprobable y adaptador marcado «no compilado», sin reportarlo como funcional.

Estados: Desconectado → Calentamiento → Listo → EntradaPendiente → Posición → SalidaPendiente → Pausa/Error. Incluye identificador idempotente por intención, reconciliación de órdenes y posiciones, fills parciales, rechazos, cancelaciones, reinicio y reconexión; no reenviar una orden sólo por timeout. Verifica soporte nativo de brackets/OCO y órdenes stop por conexión; no lo presupongas. Registra decisiones, datos disponibles al instante, costos y versiones sin secretos.

Crea pruebas de stop/target en misma barra con resolución conservadora o tick real; latencia, slippage, fills limit no garantizados, rollover, DST, tick size, pérdidas simultáneas ES/NQ, órdenes duplicadas y desconexiones. No uses cada fill como observación estadísticamente independiente.

Separa entrenamiento, validación cronológica, walk-forward con purga/embargo y holdout final intacto. Usa como unidad sesiones o bloques definidos por dependencia. Compara con no operar, exposición equivalente y versiones simples. Reporta exceso neto, drawdown, turnover, pérdidas extremas y sensibilidad a costos. El laboratorio de la terminal ofrece signo por bloques con supuesto de simetría y Holm; no es idéntico a barajar precios y reejecutar todo el modelo. Si necesitas una permutación de precios como variante de investigación, implementa otra prueba que reconstruya series OHLC coherentes bajo una nula explícita y vuelva a ejecutar señal y ejecución completas, preservando sesiones y dependencia según diseño. Contabiliza todas las variantes exploradas.

El criterio de éxito no es «ganar un backtest»: exige evidencia fuera de muestra, robustez a costos/latencia, comparación justa y paper trading con reconciliación sin incidencias. Si falla, informa «sin ventaja demostrada».

### 5. Guía y Artifact educativo

Entrega `GUIA.md`: vocabulario, contratos/ticks, conexión simulada, preparación de sesión, lectura de footprint/TPO/GEX, definición de setups, dimensionamiento, registro y revisión. Incluye una progresión: conceptos → replay sin órdenes → replay con órdenes simuladas → simulación forward. Para cada etapa define ejercicios y criterio de dominio, no una promesa de empezar en real en cierta fecha.

Genera además un Artifact autocontenido HTML/JavaScript o React listo para pegar en Claude Artifacts, en español y sin API/broker. Debe contener:

1. Footprint interactivo con datos SINTÉTICOS, volumen bid/ask, delta por nivel y acumulado; enseñar que delta = compras agresoras − ventas agresoras y que no equivale al delta de opciones.
2. Comparador TPO/volumen con POC/VAH/VAL y explicación del algoritmo.
3. GEX de ejemplo con OI, gamma, multiplicador y spot editables, unidades correctas y selector absoluta/convención; rotular que no muestra posición real del dealer.
4. Casos de decisión largos/cortos/no operar con respuesta justificada, sin información del desenlace antes de responder. Distribución de resultados fija y revelada después; no ligar premio a la decisión para fingir rentabilidad.
5. Calculadora de riesgo MES/MNQ/ES/NQ con costos y validación de entradas; permitir cero contratos.
6. Cuestionario y bitácora local exportable, reinicio claro y sin enviar datos por red. Manejar almacenamiento deshabilitado.

Valida en escritorio y móvil, teclado y contraste; comprueba cálculos con ejemplos manuales. Separa «Artifact local generado» de «publicado en una cuenta de Claude»: no afirmes publicación si no ocurrió. Al terminar entrega archivos, comandos de reproducción, pruebas, dependencias y pendientes reales.

## Fuentes oficiales para verificar antes de ejecutar

- [Quantower Algo y SDK](https://help.quantower.com/quantower/quantower-algo), [API](https://api.quantower.com/).
- [Trading Simulator](https://help.quantower.com/quantower/trading-panels/trading-simulator), [Market Replay](https://help.quantower.com/quantower/trading-panels/market-replay), [backtest](https://help.quantower.com/quantower/quantower-algo/backtest-and-optimize).
- [Volume Analysis](https://help.quantower.com/quantower/analytics-panels/chart/volume-analysis-tools), [TPO](https://help.quantower.com/quantower/analytics-panels/tpo-chart).
- [CME MES](https://www.cmegroup.com/markets/equities/sp/micro-e-mini-sandp-500.contractSpecs.html), [CME MNQ](https://www.cmegroup.com/markets/equities/nasdaq/micro-e-mini-nasdaq-100.contractSpecs.html), [Micro E-mini FAQ](https://www.cmegroup.com/articles/faqs/micro-e-mini-equity-index-futures-frequently-asked-questions.html), [E-mini FAQ](https://www.cmegroup.com/trading/equity-index/eminifaq.html).



## Ampliación: PDF y capturas recibidos

Lee `recursos-adjuntos.md`. Los cuatro PDF de Ana Jiménez / Actinver Acelera respaldan las fórmulas ya implementadas, con precisiones de notación para SAR, EMA e histograma MACD. Foto3 muestra dos paneles ES/MNQ de5min con footprint/perfil; Foto4 muestra lecturas volumen y delta. No se deben copiar valores de la captura como cotizaciones actuales.

El Artifact incorpora módulos6–8: replay sintético de DOM/heatmap, cálculo de indicadores y ruta de Bookmap, Matt Owen, cbrackn, Jigsaw y Andrea Cimi. Respetar el estado de verificación de cada referencia: títulos y conteos de una captura no equivalen a transcripción completa. Añadir una pared, cancelarla y ejecutar una operación son eventos distintos; el heatmap de liquidez no es GEX.

En Quantower configura perfiles de5min y estadísticas de volumen/delta sólo si el feed suministra esos datos. Footprint#1 volumen y Footprint#2 delta describen la captura; no constituyen una regla de entrada validada. Relaciona cada decisión con datos point-in-time, costos y riesgo. La captura de precios Foto2 carece de fecha/moneda/listado confirmados y no alimenta cotizaciones ni posiciones de la terminal.
