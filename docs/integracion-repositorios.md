# Integración de repositorios conservados — Etapa 0 (propuesta)

Fecha: 12-oct-2026. Estado: **aprobada por el usuario el 12-oct**. Las etapas 1 y 2 están implementadas (`docs/flujo-ordenes-opciones.md`): `ccxt`, exportación a `hftbacktest`, importación de exportaciones de OpenBB y TradingView, y Heston propio. La etapa 3 está pendiente. Cripto: Bitso con BTC, ETH, SOL y XRP en MXN.

Método:
- Se inventariaron las 103 carpetas de `C:\Users\MIKE\Desktop\Repos`.
- En los repositorios con relación financiera se leyeron la licencia, el README, los manifiestos (`pyproject.toml`,
  `package.json`, `Cargo.toml`, `go.mod`) y la fecha del último commit.
- No se instaló, ejecutó ni copió código de ninguno.

## Conclusión principal

**Ningún repositorio conservado trae datos autorizados de libro de órdenes, operaciones ni cadenas de opciones de la BMV
o de EE. UU.** Son motores (backtesting, ejecución, conectores) o aplicaciones completas. Los datos tienen que venir de un
proveedor:

| Necesidad | Fuente real disponible hoy | Costo | Nota |
|---|---|---|---|
| OHLCV diario de EE. UU. | Alpaca (barras), Tiingo (EOD) | Gratis con las claves que ya tienes | La terminal hoy **guarda solo el cierre**: hay que guardar apertura, máximo y mínimo |
| OHLCV intradía de EE. UU. | Alpaca (barras de minutos; IEX en vivo, SIP histórico con 15 min de retraso) | Gratis | Se rotula feed y retraso |
| OHLCV BMV | EODHD (diario, 20 peticiones/día) | Gratis limitado | Intradía BMV: solo con contrato |
| Operaciones (cinta) EE. UU. | Alpaca trades IEX | Gratis | IEX ≈ 2–3 % del volumen consolidado: **no es la cinta completa** |
| Mejor bid/ask EE. UU. | Alpaca quotes IEX | Gratis | Solo el primer nivel de IEX; **sin profundidad** |
| Libro con profundidad | Sin fuente gratuita autorizada para acciones | De pago (p. ej. Databento, Polygon/Massive) | Requiere contrato |
| Cadena de opciones EE. UU. | Alpaca Options (feed «indicative», gratis, diferido; trae IV y griegas) | Gratis con las claves actuales, **por confirmar con una consulta mínima** | OPRA en tiempo real requiere suscripción |
| Libro y cinta de cripto (fuera del Reto) | API pública de exchanges vía `ccxt` (MIT) | Gratis, con límites de cada exchange | Datos reales y autorizados, pero no son instrumentos del Reto |
| Opciones y libro BMV / MexDer | Ninguna gratuita | Contrato con MexDer o un distribuidor | — |

## 1. Matriz de repositorios

Nota sobre licencias: `actinver-terminal` está en GitHub. **No se copia código GPL/AGPL/LGPL dentro del repositorio**, por
las obligaciones que trae distribuirlo. Esos proyectos se usan como herramientas externas: el proceso del usuario genera
un CSV o JSON que la terminal importa. El código MIT, BSD o Apache solo entra como dependencia declarada y opcional,
nunca copiado.

### Datos de mercado y conectores
| Repositorio | Capacidad concreta | Licencia | Dependencias | Riesgo | Método de integración | Prioridad | Acción humana |
|---|---|---|---|---|---|---|---|
| `ccxt` | Libro de órdenes, operaciones y OHLCV de cientos de exchanges de cripto (endpoints públicos) | MIT | Paquete `ccxt` (grande) | Cripto fuera del Reto; límites por exchange | **Adaptador opcional** `OrderBookProvider`/`TradesProvider`, apagado por omisión | P2 | Elegir exchange y aceptar sus términos |
| `OpenBB` | Plataforma de datos con muchos proveedores (la mayoría con clave propia) | AGPL-3.0 | Pesadas | AGPL; duplica conectores existentes | **Consultar externamente**: si el usuario la corre, la terminal importa sus exportaciones CSV | P3 | Instalarla y correrla por su cuenta |
| `OpenStock` | App web (Next.js) de seguimiento de mercado (Finnhub) | AGPL-3.0 | Node, MongoDB | AGPL; servicio web completo | **Mantener independiente** | — | — |
| `FinceptTerminal` | Terminal C++/Qt con datos propietarios y ejecución | AGPL-3.0 (edición de pago aparte) | Qt, C++ | Incluye ejecución con bróker; AGPL | **Mantener independiente**; solo referencia de funciones públicas | — | — |
| `tradingviewmcp` | Puente CDP a TradingView Desktop (lectura de gráficas, Pine) | MIT (fork) | Node, TradingView de pago | Requiere suscripción; automatiza una app de escritorio | **Mantener independiente**; el puente oficial (webhook + Pine) ya existe | — | Suscripción a TradingView si se quiere usar |
| `worldmonitor` | Tablero de noticias y geopolítica | AGPL-3.0 | Node | AGPL; muchas fuentes externas | Mantener independiente | — | — |
| `fomo-robinhood-radar` | Lectura de operaciones en cadena (Robinhood Chain) | MIT | Python | Archivado el 6-oct-2026; cripto | Mantener independiente | — | — |
| `polymarket-bot` | Bot de mercados de predicción | Sin licencia | Node | Sin licencia: no se puede reutilizar código | Mantener independiente | — | — |

### Backtesting y simulación
| Repositorio | Capacidad | Licencia | Dependencias | Riesgo | Método | Prioridad | Acción humana |
|---|---|---|---|---|---|---|---|
| `backtrader` | Backtesting por eventos (ya se usó para validar cálculos, D-33) | GPL-3.0 | Python puro | GPL; sin commits desde abr-2023 | **Herramienta externa de verificación** (como hasta hoy), sin dependencia interna | P3 | — |
| `vectorbt` | Backtesting vectorizado muy rápido | Apache-2.0 **+ Commons Clause** | numba, pandas | Commons Clause prohíbe vender; dependencia pesada | Opcional externo; la terminal ya tiene walk-forward propio | P3 | — |
| `hftbacktest` | Backtesting de alta frecuencia con colas y latencias sobre datos L2/L3 | MIT | Rust + Python (`hftbacktest`) | Necesita datos de libro por nivel que no tenemos | **Adaptador futuro** (etapa 4): exportar libro/operaciones normalizados al formato de hftbacktest | P3 | Datos L2 con licencia |
| `nautilus_trader` | Motor de trading/backtesting profesional (Rust/Python) | LGPL-3.0 | Rust, grande | Incluye ejecución en vivo; pesado | **Mantener independiente**; a lo sumo, exportar datos en su formato | — | — |
| `trading-backtest` | Motor Java ligero, salida CSV | MIT | Java/Gradle | Otro lenguaje | Mantener independiente | — | — |

### Estrategias cuantitativas y aprendizaje
| Repositorio | Capacidad | Licencia | Riesgo | Método | Prioridad |
|---|---|---|---|---|---|
| `qlib` (Microsoft) | Plataforma de investigación cuantitativa con ML, alfas y backtest | MIT | Muy pesada; sus datos de ejemplo son de China/EE. UU. | Consultar externamente; importar señales como CSV | P3 |
| `FinRL` | Aprendizaje por refuerzo para carteras | MIT | Sobreajuste alto; pesado | Mantener independiente | — |
| `RD-Agent` | Agentes que generan y prueban factores | MIT | Gasto de LLM; resultados no verificados | Mantener independiente | — |
| `TradingAgents`, `TradingAgents_TauricResearch`, `Vibe-Trading` | Agentes LLM de análisis | Apache-2.0 / MIT | Opiniones de LLM sin validación | Mantener independiente; si acaso, sus notas entran como «investigación manual» | — |
| `Kronos` | Modelo base de series financieras | MIT | Ya evaluado: sin ventaja, 494 MB y 95 min | Ya integrado como experimento (D-41) | — |
| `awesome-quant`, `awesome-systematic-trading`, `paperswithbacktest-awesome-systematic-trading` | Listas de referencias | Varias | Ninguno | Consulta documental | — |

### Riesgo, escenarios y optimización
| Repositorio | Capacidad | Licencia | Método | Prioridad |
|---|---|---|---|---|
| `skfolio` | Optimización y riesgo (CVaR, HRP, etc.) | BSD-3 | **Ya es dependencia** de la terminal (optimizador) | — |
| `Heston-Calibration` | Calibración del modelo de Heston (notebook) y una cadena SPX de ejemplo | **Sin licencia** | **No reutilizar el código ni el CSV**. Se puede implementar el método desde el artículo publicado (Cui et al., 2017) con código propio | P3 |

### Order Flow, libro y operaciones
| Repositorio | Capacidad | Licencia | Método | Prioridad |
|---|---|---|---|---|
| `orderbook` | Motor de emparejamiento en Go (precio-tiempo) | MIT | Solo referencia conceptual: no es una fuente de datos | — |
| `orderbook-consumer-demo` | Demo en Go sin licencia | Sin licencia | No reutilizar | — |
| `hummingbot` | Bot de *market making* para cripto con conectores | Apache-2.0 | **Mantener independiente**: es un bot de ejecución | — |
| `freqtrade` | Bot de trading de cripto | GPL-3.0 | Mantener independiente (ejecución) | — |
| `astra-quant-agent` | Trading autónomo de cripto en OKX con LLM | AGPL-3.0 | **Mantener independiente**: ejecuta órdenes | — |
| `AutoHedge` | «Fondo de cobertura autónomo» que opera en Solana | MIT | **Mantener independiente**: ejecuta órdenes | — |
| `lumibot` | Biblioteca de trading con brókers (Alpaca, IB…) | GPL-3.0 | **Mantener independiente**: ejecución | — |

### Option Flow, volatilidad y cadenas
No hay repositorio con datos de opciones autorizados. Lo reutilizable:
- `Heston-Calibration` como referencia académica (sin copiar código);
- el panel BSM propio (`terminal/modelos_opciones.py`).

### Visualización y gráficos
| Repositorio | Capacidad | Licencia | Método |
|---|---|---|---|
| `trade-journal` (LuxAlgo) | Diario de operaciones con calendario de P&L | MIT | Referencia de interfaz; mantener independiente (Node, Docker) |
| Widget oficial de TradingView | Velas e indicadores | Términos de TradingView | Ya integrado como enlace externo |
| Gráficos propios | La terminal dibuja SVG sin dependencias | Propio | **Se amplía** para velas, volumen y profundidad |

### Noticias, documentos e investigación
| Repositorio | Capacidad | Licencia | Método |
|---|---|---|---|
| `financial-services` (Anthropic) | Habilidades y agentes para comps, DCF y notas de resultados | Apache-2.0 | Uso desde Claude (fuera de la terminal); sus salidas entran como investigación manual |
| `PaddleOCR` | OCR | Apache-2.0 | No hace falta: la terminal ya usa el OCR de Windows para capturas |
| `pdf-inspector` | Lectura de PDF | MIT | No hace falta: ya se usa `pypdf` |
| `Scrapling`, `firecrawl`, `changedetection.io`, `maxun`, `browser-use`, `camofox-browser` | Extracción web | Varias (AGPL en firecrawl y maxun) | **No integrar**: la extracción choca con los términos de los sitios financieros (mandato § 6.3) |

### Automatización, auditoría y calidad de código
`ast-grep`, `repomix`, `serena`, `codebase-memory-mcp`, `trailofbits-skills`, `testing-handbook`, `strix`, `tdd-guard`,
`spec-kit`, `superpowers` y `gstack` sirven para desarrollar, no para la terminal en ejecución. Quedan como herramientas
de la sesión de desarrollo.

### Deben permanecer independientes (no financieros o servicios propios)
`AdGuardHome`, `vaultwarden`, `syncthing`, `pocketbase`, `supabase`, `paperless-ngx`, `LibreChat`, `dify`, `ollama`,
`whisper`, `mem0`, `crewAI`, `trigger.dev`, `cline`, `cua`, `agents`, `skills`, `yt-dlp`, carpetas de respaldo (`_respaldos`,
`_cdio_*`, `_librechat-local`, `_ov_check`, `*-local`, `*-run`, `modelos_locales`) y el resto de herramientas generales.

## 2. Recomendación por repositorio

| Recomendación | Repositorios |
|---|---|
| **Integrar como dependencia opcional** | `ccxt` (adaptador de libro y cinta de cripto, apagado por omisión) |
| **Adaptar por exportación de formato** | `hftbacktest` (exportar libro y operaciones normalizados, cuando existan datos L2) |
| **Consultar externamente (importar sus CSV)** | `OpenBB`, `qlib`, `backtrader` (verificación), `vectorbt` |
| **Implementar con código propio desde fuentes publicadas** | Calibración de Heston (artículo), VWAP, Bollinger, perfil de volumen, delta de volumen |
| **Mantener independiente** | Todo motor que ejecute órdenes (`freqtrade`, `hummingbot`, `nautilus_trader`, `lumibot`, `AutoHedge`, `astra-quant-agent`), apps completas (`OpenStock`, `FinceptTerminal`, `trade-journal`, `worldmonitor`), los repositorios sin licencia y los no financieros |

## 3. Arquitectura propuesta

```
terminal/flujo/                     (paquete nuevo, solo lectura y simulación)
  contratos.py   dataclasses: BarraOHLCV, NivelLibro, Operacion, ContratoOpcion, Procedencia
                 Procedencia = fuente, licencia, mercado, zona horaria, hora del evento,
                 hora de captura, retraso medido, calidad ('proveedor'|'importado'|'calculado'|'sintetico')
  proveedores.py Protocolos: MarketDataProvider (OHLCV), OrderBookProvider, TradesProvider,
                 OptionsChainProvider, ResearchProvider (envuelve al centro de investigación)
  almacen.py     tablas versionadas (migración nueva):
                   barras_ohlcv(instrumento, inicio, intervalo, o,h,l,c,v, fuente, tipo, hora_captura, ...)
                   libro_niveles(instantanea_id, lado, nivel, precio, tamano)  + libro_instantaneas(...)
                   operaciones(simbolo, mercado, instante, precio, tamano, lado|NULL, fuente, ...)
                   opciones_cotizaciones(subyacente, vencimiento, strike, tipo, bid, ask, ultimo,
                                         volumen, interes_abierto, iv, delta.., origen_iv, fuente, ...)
                 todas con disponible_desde (sin fuga temporal) y huella para revisiones
  importar_csv.py validación estricta por tipo (encabezados exactos, instantes con zona horaria,
                 bid ≤ ask, precios > 0, sin futuros, ≤ 5 MB), todo o nada, origen = 'importado'
  adaptadores/   alpaca_barras.py, alpaca_opciones.py (opcional), ccxt_libro.py (opcional, apagado)
  calculos.py    VWAP, Bollinger, delta de volumen, desequilibrio, perfil de volumen,
                 curva y superficie de IV, regla descriptiva de volumen inusual (configurable)
```

API local nueva, solo con GET, salvo la importación:
- `/api/flujo/ohlcv`, `/api/flujo/libro`, `/api/flujo/operaciones` y `/api/flujo/opciones`;
- `/api/flujo/estado`: proveedor, licencia, retraso y última captura;
- `POST /api/flujo/importar/{tipo}`, con CSRF, límite de tasa y tamaño máximo.

Vistas nuevas en «Más»:
- **Velas**: selector de instrumento, mercado, rango e intervalo; volumen; SMA, RSI, VWAP y Bollinger opcionales;
  tooltip con OHLCV, fecha, zona, fuente y retraso.
- **Order Flow**: libro, profundidad, cinta, delta, perfil de volumen y estado «sin fuente autorizada».
- **Option Flow**: cadena por vencimiento y strike, filtros, curva y superficie de IV, regla de volumen inusual y
  enlace al panel BSM.

El **mapa de calor** se amplía con:
- filtros por sector, clase, proveedor y ventana (1, 5 y 20 sesiones);
- escala de color accesible (azul–naranja, apta para daltónicos);
- ajuste por splits y prioridad única de proveedores, con lo que se cierran los hallazgos de la auditoría;
- detalle al seleccionar una celda y navegación a la ficha del instrumento.

Reglas que se mantienen:
- nada inventa OHLC, libro, operaciones ni cadenas;
- sin datos, el panel dice «sin fuente autorizada» y explica cómo importarlos;
- los datos sintéticos solo existen en modo demo y llevan su etiqueta.

## 4. Archivos que se modificarán (etapa 1)

| Archivo | Cambio |
|---|---|
| `terminal/flujo/*` (nuevo) | Contratos, almacén, importación, cálculos y adaptadores |
| `terminal/migraciones.py` | Migración nueva con las tablas de arriba |
| `terminal/ingesta.py`, `terminal/adaptadores/*` | Guardar apertura, máximo y mínimo cuando el proveedor los entrega (Alpaca y Tiingo ya los traen) |
| `terminal/visualizaciones.py` | Precio ajustado por splits, prioridad única y ventanas de 1, 5 y 20 sesiones |
| `terminal/app.py` | Rutas `/api/flujo/*` |
| `terminal/seguridad.py` | Límites de tasa de las rutas nuevas |
| `web/index.html`, `web/static/app.js`, `web/static/app.css` | Vistas de velas, Order Flow y Option Flow, y mejoras del mapa |
| `tests/test_flujo_*.py` (nuevos) | Contratos, importación, cálculos, API y estados vacíos |
| `docs/flujo-ordenes-opciones.md`, `docs/acciones-requeridas-usuario.md` | Uso local y acciones del usuario |

## 5. Riesgos

| Tipo | Riesgo | Mitigación |
|---|---|---|
| Licencia | Copiar código GPL/AGPL/LGPL a un repositorio publicado en GitHub | No se copia; solo se usan como herramientas externas o se escribe código propio |
| Licencia | Repositorios sin licencia (`Heston-Calibration`, `polymarket-bot`, `orderbook-consumer-demo`) | No se reutiliza su código ni sus datos |
| Licencia de datos | Redistribuir datos de Alpaca, Tiingo u OPRA | Los datos viven solo en `data/` (fuera de Git) y no se publican |
| Interpretación | Mostrar la cinta IEX como si fuera el mercado completo | Rótulo fijo «IEX ≈ 2–3 % del volumen; no es la cinta consolidada» |
| Interpretación | Volumen inusual leído como señal | Rótulo «regla descriptiva configurable; no es recomendación» |
| Seguridad | CSV manipulado (instantes falsos, precios absurdos) | Validación estricta, todo o nada, auditoría |
| Seguridad | Dependencia `ccxt` grande | Grupo opcional en `pyproject`; apagada por omisión |
| Operación | Servicios persistentes | Ninguno nuevo: todo corre dentro del proceso de la terminal |
| Ejecución | Órdenes reales | Ninguna ruta nueva escribe en brókeres; se añade una prueba que lo verifica |

## 6. Acciones que solo puede hacer el usuario

1. Aprobar esta propuesta (o recortarla) antes de la etapa 1.
2. Decidir si se activa el adaptador de cripto (`ccxt`) y con qué exchange, aceptando sus términos.
3. Confirmar el uso del feed «indicative» de opciones de Alpaca con tus claves actuales. Se verifica con una consulta
   mínima.
4. Si quieres libro con profundidad u opciones en tiempo real de EE. UU., o de la BMV o MexDer: contratar un proveedor.
   Es una decisión de pago.
5. Exportar e importar por CSV los datos que tengas con licencia propia (por ejemplo, de TradingView o de tu bróker).
