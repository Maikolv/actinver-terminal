# Matriz de fuentes: seis sitios web y la BMV

Cada fila resume su ficha en [`docs/sources/`](sources/). «Conectada» significa que la terminal hace llamadas reales y autorizadas **hoy**, sin credenciales pendientes.

| Fuente | Papel | Modalidad autorizada | Cobertura real | Latencia medida | Licencia / condiciones | Estado |
|---|---|---|---|---|---|---|
| [BMV](sources/bmv.md) | **Autoridad de precio** del mercado local y del SIC en MXN | Producto licenciado (`BmvLicensedProvider`) | Ninguna verificada | Ninguna | Contrato de datos de mercado | **PENDIENTE DE LICENCIA** |
| [TradingView](sources/tradingview.md) | Gráficos, símbolos y alertas del usuario | Widget oficial + webhook de alertas | Según el plan del usuario (no verificada) | Webhook: sin muestras (`UNKNOWN` por diseño) | Términos de TradingView | Widget **conectado**; webhook implementado y **pendiente de túnel y secreto** |
| [Seeking Alpha](sources/seekingalpha.md) | Investigación y noticias de valores **extranjeros** | RSS público por emisora | Emisoras de EE. UU. (SIC) | 0.23 s de respuesta; titular con 13.2 h (24-sep 02:14 UTC) | Uso personal de titular y enlace; sin licencia de datos | **Conectado** (contexto, no precios) |
| [Forex Factory](sources/forexfactory.md) | Calendario macro | Feed de exportación semanal enlazado por el sitio | Semana en curso; sin dato efectivo | 0.62 s; 80 eventos (24-sep 02:14 UTC) | Sin API documentada | **Conectado** (contexto) |
| [InsiderFinance](sources/insiderfinance.md) | Descubrimiento de operaciones de insiders | Lectura humana; datos de SEC EDGAR (Form 4) | EE. UU.; **NO CUBRE BMV** | SEC: hasta 2 días hábiles (regla SEC) | Suscripción; la SEC exige un User-Agent | SEC **pendiente de `SEC_USER_AGENT`**; InsiderFinance sin uso automático |
| [Dukascopy](sources/dukascopy.md) | Educación sobre CFD y control de clasificación | Enlace + `clasificacion.py` | No es feed bursátil | — | — | **Usado** (control activo) |
| [Barchart](sources/barchart.md) | Históricos e indicadores complementarios | Barchart OnDemand (de pago) | BMV y SIC **no confirmadas** | — | El sitio prohíbe la extracción automatizada | **PENDIENTE DE CONTRATO** |

## Autoridad de precios por mercado

| Mercado | Precio de referencia | Proveedor hoy | Qué se muestra si falta |
|---|---|---|---|
| BMV local (MXN) | BMV licenciada; se coteja con el simulador | Ninguno verificado. Alternativas: EODHD (EOD, clave) o captura manual | SIN PRECIO CONFIABLE |
| SIC (MXN) | Serie SIC de la BMV | Ninguno verificado | SIN PRECIO CONFIABLE, con la referencia de origen **aparte** |
| Origen extranjero (USD) | Proveedor contratado de la bolsa de origen | Alpaca IEX y Tiingo (con claves; hoy sin claves) | «Referencia externa», nunca como precio BMV |
| Fondos Actinver | Valor liquidativo (NAV) | Captura o CSV | SIN PRECIO CONFIABLE |
| Tipo de cambio | Banxico FIX (prioritario) o FRED | FRED **conectado** (2–3 sesiones de rezago) | Tipo de cambio no vigente → se suspende la valuación en USD |

La matriz por instrumento (símbolo Actinver, emisor, serie, ISIN, MIC, moneda, símbolo BMV, símbolo de origen, proveedor, latencia, último dato y causa de la discrepancia) está en [instrument-matrix.md](instrument-matrix.md). Se regenera con `uv run terminal cobertura`.

**Otras fuentes evaluadas:** OpenBB (el único proveedor con `xmex` es Intrinio, de pago), public-apis (ninguna fuente con licencia BMV verificable), worldmonitor (contexto sin integración). Detalle en [repository-adoption-matrix.md](repository-adoption-matrix.md).
