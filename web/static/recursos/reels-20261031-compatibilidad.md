# Uso en Quantower y TradingView — investigación exclusivamente

La interfaz de OpenTerminal usa React/Next y Express, no TradingPlatform.BusinessLayer ni Pine. Se incorpora su organización al panel nativo de Actinver; no se instala como una DLL de Quantower.

Quantower: reutilice para una futura capa de visualización las funciones puras que ya existen en quantower/FuturosLab.Nucleo/Riesgo.cs y NoiseBands.cs. Esas funciones no equivalen a estrategia conectada. Compare cada resultado con la Mesa mediante vectores compartidos; el deslizamiento en Riesgo.cs está expresado en dinero, mientras que Mesa usa ticks totales (× USD 5 para NQ). No pase un valor sin convertir sus unidades. Nada de Start, órdenes o conectar cuentas.

TradingView: mesa_riesgo_nq.pine dibuja únicamente entrada, SL y TP manuales y tabla de riesgo. Cargar en Pine Editor, compilar y añadir al gráfico solo como indicador informativo, sin crear alertas. Usar NQ/MNQ de futuros; no confundir con CFD/cash. Se guardó como fuente; todavía no está verificado por el compilador remoto. No hay strategy.entry, strategy.exit, alert ni webhook.

Gamma: long gamma con cobertura delta requiere opciones, griegas, IV y costos fechados. GEX aproximado de la terminal no revela inventario real de dealers, no determina por sí solo TP/SL NQ y no demuestra alfa. El cálculo local de riesgo es un escenario manual, nunca señal actual.

Day Trader: sus skills de acciones y Time Machine son referencias de proceso. El bootstrap por franjas no aporta 10,000 observaciones independientes; conserva sesgo de muestra, pérdida por gaps y cambio de régimen. No se instala trader-broker.

Puente futuro solo informativo: contrato con vencimiento, MIC, multiplicador, tick, moneda, tipo de datos, proveedor, evento/disponibilidad/ingesta, latencia, reglas, hora de generación/caducidad, invalidación y costos. Rechazar dato ausente, obsoleto o no permitido; sin precio confiable devolver SIN SEÑAL. No se implementa un nuevo envío Telegram en esta entrega. Se requiere autorización humana posterior antes de cualquier trade, incluso demo.
