# Prompt para Claude: TradingView para Nasdaq y S&P 500

Copia el prompt completo en Claude Code con acceso al navegador o a TradingView Desktop. Preparado el 17 de octubre de 2026; las funciones y condiciones deben verificarse nuevamente al ejecutarlo. Esta entrega es un prompt, no una configuración ya aplicada.

## Prompt listo para usar

Actúa como especialista en TradingView, futuros CME, microestructura y configuración de Windows. Configura localmente mi entorno para analizar y practicar futuros Nasdaq-100 y S&P 500 con la mejor configuración que permitan mi equipo, plan, datos y conexión existentes. Explica en español sencillo. No prometas una configuración universal perfecta ni rentabilidad.

Tienes autorización para inspeccionar el entorno pertinente y realizar cambios reversibles de configuración. Usa los plugins y skills pertinentes que estén realmente disponibles; lee sus instrucciones. Conserva las configuraciones anteriores y registra cómo restaurarlas. No compres planes, cambies contratos, aceptes condiciones, guardes contraseñas en archivos ni actives operaciones en cuentas de evaluación, financiadas o reales. Deja la ejecución exclusivamente en Paper Trading de TradingView. Si hace falta iniciar sesión o resolver autenticación, indícame el paso exacto sin solicitar mis secretos.

### 1. Inspección y compatibilidad

- Detecta TradingView web/Desktop, versión, sistema, pantallas, resolución, plan contratado, límites efectivos de gráficos, indicadores, alertas e historial. No instales extensiones ni optimizadores innecesarios.
- Lee las instrucciones del proyecto y estos recursos locales: `C:/Users/MIKE/Desktop/Repos/actinver-terminal`, `C:/Users/MIKE/Desktop/Repos/futuros-lab` y los entregables en `C:/Users/MIKE/Documents/Codex/2026-10-16/tienes-total-facultad-sobre-mi-pc-2/outputs`. En particular: `prompt-quantower-claude.md`, `prompt-claude-lucid-flex50k.md`, `lucid-reglas-50k-2026-10-17.md`, `guia-lucid-desde-cero.md` y `practica-orderflow.html`. Inspecciona las instrucciones y cambios existentes antes de reutilizar `tradingview/` o `docs/tradingview-puente.md`; conserva el trabajo ajeno. Usa codebase-memory para explorar estructura cuando corresponda y comprueba su cobertura.
- Identifica el tipo de conexión de mi cuenta Lucid Flex 50K. La documentación consultada lista TradingView con CQG/Tradovate y Quantower con Rithmic. Verifica la oferta vigente y mi cuenta concreta: no supongas que unas credenciales Rithmic sirven en TradingView ni migres la cuenta automáticamente.
- Entrega una tabla: función solicitada, disponible hoy, requisito, coste o límite, alternativa y estado verificado. Si no puedes operar la interfaz, completa los archivos y una guía exacta, y distingue lo preparado de lo aplicado.

### 2. Datos, contratos y proveedores

- Prepara una lista de seguimiento con ES, MES, NQ y MNQ de CME. Selecciona los vencimientos concretos con liquidez y operabilidad verificadas; registra símbolo completo, vencimiento y conexión. Usa continuos como ES1!/NQ1! para contexto y documenta rollover y ajuste histórico. No asumas que el continuo analizado identifica el contrato de ejecución.
- Verifica especificaciones CME vigentes. Referencia inicial: tick de 0.25 puntos; ES USD50/punto y USD12.50/tick; MES USD5/punto y USD1.25/tick; NQ USD20/punto y USD5/tick; MNQ USD2/punto y USD0.50/tick. Calcula tamaño y riesgo con las especificaciones confirmadas.
- Identifica retrasos, permisos CME, calidad, horario y diferencias entre feed de gráficos y broker. Comprueba si mis permisos del broker pueden verificarse en TradingView para evitar un doble pago; no presupongas que una cuenta de prop firm reúne los requisitos.
- Presenta proveedores gratuitos o con modalidad gratuita que puedan alimentar herramientas dentro de Actinver-terminal, separando acciones, futuros, opciones y macroeconomía. Verifica fuente oficial, cobertura, retraso, profundidad, límites, licencia, API y uso permitido. Distingue software gratuito de datos gratuitos y prueba gratuita. No presentes Yahoo/yfinance, proxies ni datos diferidos como feed apto para ejecutar futuros intradía. Un proveedor externo no puede insertarse arbitrariamente en el feed nativo de TradingView.
- Si falta un dato necesario, deja el panel marcado como no disponible; no fabriques order flow, gamma ni cotizaciones.

### 3. Espacio de trabajo claro

Crea y guarda un diseño “Futuros Nasdaq y S&P — Práctica”, con copia de seguridad del anterior. Adáptalo a mi plan: si no admite varios gráficos, crea plantillas individuales y un procedimiento rápido para alternar.

- Contexto: diario y 60 minutos; estructura intradía: 15/5 minutos; ejecución simulada: 1 minuto cuando sea útil. Sincroniza símbolo, cursor y dibujos únicamente cuando sea apropiado. No mezcles dibujos de ES con NQ.
- Usa velas estándar para decisiones y backtests. Separa cualquier Heikin Ashi, Renko u otra transformación de las hipótesis de ejecución.
- Define sesiones RTH/ETH expresamente. Identifica zona del exchange y conversión a Ciudad de México con cambios estacionales. Muestra apertura, máximos/mínimos previos y overnight, VWAP de sesión y volumen. Distingue calendario CME del horario obligatorio de cierre de Lucid.
- Plantilla principal ligera: precio, volumen, VWAP y EMA20/50 como valores iniciales para evaluar, sin afirmar que generan alfa. Plantillas opcionales: SMA200, MACD12/26/9, estocástico14/3/3 y SAR parabólico con parámetros visibles. No satures el gráfico ni optimices parámetros mirando el periodo de prueba.
- Configura colores legibles, escalas, tamaño de letra, favoritos y botones frecuentes. Evita atajos que permitan enviar órdenes por accidente.

### 4. Order flow, perfil, delta, opciones y gamma

- Verifica disponibilidad real de Volume Profile, TPO/Market Profile, footprint, delta y CVD según plan e instrumento. Distingue perfil de volumen y distribución de tiempo; marca POC/VAH/VAL y metodología de sesión.
- La documentación consultada del footprint de TradingView clasifica volumen comprador/vendedor según dirección del precio intrabar. Explica su cálculo vigente, cobertura histórica y limitaciones; no lo presentes como clasificación inequívoca de operaciones agresoras a bid/ask del exchange. Revisa también la metodología del CVD elegido.
- Para DOM, verifica broker compatible y sus permisos de profundidad. Los datos de nivel 2 del DOM proceden de la conexión del broker; no asumas que pagar datos gráficos desbloquea profundidad. Separa liquidez publicada, cancelaciones y volumen ejecutado.
- Para absorción e imbalance, formula observaciones e hipótesis comprobables. Una divergencia de delta o pared de liquidez no basta por sí sola para entrar.
- Verifica si existen opciones, option flow y GEX utilizables con fuentes autorizadas. Explica origen, retraso, supuestos de signo del inventario de dealers, unidades y diferencias entre opciones SPX/SPY/QQQ y futuros ES/NQ. No traslades strikes como niveles idénticos sin conversión justificada.
- Si TradingView no cubre una función, propón mantenerla en Quantower, Bookmap o Actinver-terminal, indicando conexión y coste verificados. No afirmes equivalencia entre un heatmap de liquidez y un heatmap GEX.

### 5. Práctica y controles de riesgo

Configura una cuenta virtual Paper Trading identificada claramente, con USD50,000 como capital de práctica si la interfaz lo permite. Esto no reproduce automáticamente las reglas Lucid. Mantén desconectada la ejecución de Lucid durante las pruebas.

- Usa inicialmente un microcontrato en ejercicios; verifica que el riesgo del stop más costes cabe en el presupuesto. No uses el saldo nominal de 50K como capital que se puede perder.
- Propón límites conservadores de práctica basados en la distancia al umbral de pérdida vigente y exposición conjunta ES/NQ; presenta los valores como propuesta, no como regla oficial. Incluye comisiones, deslizamiento y pérdidas abiertas.
- Reconsulta reglas Lucid oficiales y distingue evaluación, financiada simulada y real: drawdown, escalamiento, límites, horarios, noticias, automatización, retiros y prácticas prohibidas. Registra fecha y URL; si hay ambigüedad horaria EST/Eastern, resuélvela antes de automatizar conversiones.
- Desactiva operaciones con un clic y activa confirmaciones cuando estén disponibles. Verifica contratos, cuenta y tamaño antes de cada orden virtual. Comprueba stop, objetivo, OCO/brackets, órdenes parciales, cancelación y cierre en Paper Trading; documenta diferencias con la conexión futura.
- Explica qué ocurre al desconectar, dónde reside un stop y cómo verificar una posición cerrada. No simules pruebas de emergencia en cuentas Lucid.

### 6. Pine Script y posible automatización futura

Inspecciona lo existente y reutiliza únicamente lo pertinente y compatible con su licencia. Si necesitas un script, usa la versión vigente de Pine y documentación oficial. Separa indicador, estrategia de backtest y órdenes reales.

- No uses información futura ni valores de marcos superiores todavía no confirmados como si fueran históricos. Documenta repainting, cálculo intrabar, diferencias histórico/tiempo real y alertas al cierre.
- Valida con velas estándar, costes, reglas de ejecución, límites del emulador y periodos separados de desarrollo y prueba. Usa Bar Magnifier sólo si está disponible y explica sus límites. No deduzcas fills de DOM o una cola de ejecución a partir de OHLC.
- Las pruebas de permutación evalúan evidencia frente a una hipótesis nula; no generan alfa. Preserva dependencia temporal mediante bloques cuando corresponda, corrige búsqueda de múltiples variantes y reporta resultados fuera de muestra, costes, drawdown y sensibilidad. Si faltan datos, entrega protocolo sin inventar métricas.
- TradingView no ofrece actualmente ejecución automática nativa de estrategias Pine en la cuenta de brokerage según la documentación consultada: compruébalo de nuevo. Un fill del Strategy Tester es del emulador. Las alertas tampoco son confirmaciones de ejecución del broker.
- Configura únicamente alertas informativas de práctica disponibles en mi plan. Documenta condición, símbolo, sesión, frecuencia, caducidad y recreación tras cambios: una alerta conserva una copia de la configuración al crearla.
- Si planteas un puente futuro por webhook, entrega sólo diseño deshabilitado: autenticación, protección de secretos, validación de cuenta/símbolo/vencimiento/tamaño, caducidad, idempotencia, conciliación, rechazo de duplicados, límites de riesgo y parada. No publiques un servidor ni conectes órdenes como parte de esta configuración.

### 7. Guía sencilla y entregables

Explica como para un principiante: la gráfica es el mapa, el contrato es lo que compras o vendes, el stop limita el riesgo previsto pero no garantiza el precio, y el simulador es el espacio de práctica. Define tick, punto, largo/corto, stop, límite, mercado, margen y rollover con ejemplos de un microcontrato. No conviertas esos ejemplos en señales actuales.

Entrega:
1. Inventario de configuración anterior y copia/restauración disponible.
2. Diseño y plantillas guardados, con capturas que oculten datos privados.
3. Tabla de contratos, sesiones, permisos y herramientas disponibles o pendientes.
4. Comparación de proveedores gratuitos y costes inevitables comprobados.
5. Guía paso a paso adaptada a la interfaz observada y checklist antes/durante/después de practicar.
6. Ejercicios de velas, VWAP, perfil, DOM, delta, ejecución y riesgo, aprovechando el artifact local de práctica. Los ejemplos sintéticos deben indicarlo.
7. Cualquier Pine creado con explicación, limitaciones y resultados realmente obtenidos.
8. Informe final de cambios aplicados, pruebas, pasos pendientes y forma de deshacerlos.

Comprueba que el diseño persiste al reabrir, que los símbolos y vencimientos coinciden, que los datos muestran su estado real, que no hay cuenta operativa habilitada y que los ejercicios virtuales funcionan. No declares completado un paso que sólo describiste. Guarda entregables en una carpeta identificable y presenta sus rutas completas. No modifiques Actinver-terminal ni publiques cambios de código por el mero hecho de configurar TradingView.

### Fuentes oficiales iniciales: revalidar al ejecutar

- Lucid, plataformas: https://support.lucidtrading.com/en/articles/11404614-lucid-trading-supported-platforms
- TradingView, permisos del broker: https://www.tradingview.com/support/solutions/43000479666-how-can-i-get-real-time-data-from-exchanges-that-i-have-already-purchased-with-my-broker/
- TradingView, Paper Trading: https://www.tradingview.com/support/solutions/43000516466-paper-trading-main-functionality/
- TradingView, footprint: https://www.tradingview.com/support/solutions/43000726164-volume-footprint-charts-a-complete-guide/
- TradingView, nivel 2: https://www.tradingview.com/support/solutions/43000480004-how-do-i-get-level-2-data/
- TradingView, automatización Pine: https://www.tradingview.com/support/solutions/43000481026-how-to-autotrade-using-pine-script-strategies/
- Pine, estrategias: https://www.tradingview.com/pine-script-docs/concepts/strategies/
- Pine, alertas: https://www.tradingview.com/pine-script-docs/concepts/alerts/
- TradingView, continuos ajustados: https://www.tradingview.com/support/solutions/43000685266-how-can-i-enable-backadjustment-for-continuous-futures/


## Incorporación del TikTok: oficina de inversión (19-oct-2026)

Lee `docs/oficina-inversion-pixel.md` y `config/oficina-pixel-repos.json` de Actinver-terminal. Inspecciona los clones PixelFund-AI, pixel-hedge-fund y company-pixel-office bajo `C:/Users/MIKE/Desktop/Repos`. La oficina original de sólo lectura está en `/static/recursos/oficina-inversion.html`; sus seis roles son reglas descriptivas y puede preparar un prompt de análisis manual para Claude. No son agentes autónomos ni un fondo rentable demostrado. No copies assets/código sin verificar licencia. No reutilices las rutas de órdenes de Bybit, BloFin o Polymarket; no son conectores CME ni sirven por sí solas para ES/MES/NQ/MNQ.

Reutiliza el contexto, checklist y fórmulas compatibles en Pine, manteniendo la oficina y el comité fuera de Pine. No inventes acceso HTTP a localhost. Las alertas de TradingView no son un canal bidireccional para el comité; no abras túneles ni actives webhook/órdenes. Conserva el trabajo existente en tradingview/ y docs/tradingview-puente.md; valida sesiones, rollover, bar-close y restricciones del plan antes de proponer cambios. La publicación del indicador y la configuración de cuenta no constan aplicadas en esta entrega.


## Reel DepEDXbRMRF — laboratorio offline (19-oct-2026)

Inspecciona `laboratorios/reel-bots/` y `config/repositorios-reel-bots.json` en Actinver-terminal. El ejemplo probado usa backtesting.py 0.6.5 en entorno separado; CSV validado, costes por lado, spread fijo, tamaño 1 y SMA20/50. No demuestra alfa ni modela márgenes o rollover de futuros. Freqtrade/vectorbt/Nautilus son clones previos; backtesting.py y LEAN son nuevos. No arranques ni instales los cinco motores por defecto. Revisa AGPL/GPL/LGPL y la condición Commons Clause de vectorbt antes de reutilizar o distribuir.
El archivo `laboratorios/reel-bots/sma_referencia.pine` es un indicador de comparación, sin órdenes ni alertas. Compílalo en Pine Editor antes de darlo por operativo; no se verificó allí en esta entrega. Compara barras cerradas y no equipares sus marcas con fills del backtest. Pine no ejecuta estos repos Python/Rust ni HTTP arbitrario a localhost. No contrates ni conectes TradersPost: la mención del reel no demuestra elegibilidad de mi cuenta. LEAN/Nautilus no muestran Tradovate en las listas oficiales consultadas; verifica versión, adaptadores y reglas actuales antes de cualquier diseño de puente.
