# 10 · Fuentes de datos y URL candidatas

## Integradas en la terminal

| Fuente | Dato | Tipo | Credencial / costo | Uso permitido | Adaptador |
|---|---|---|---|---|---|
| FRED — DEXMXUS | USD/MXN (compra al mediodía en NY) | Diario, rezago de días | Ninguna | Descarga pública; citar FRED | `Fred` |
| Banxico SIE — SF43718 | Tipo de cambio FIX | Diario | Token gratuito | API oficial con límites | `Banxico` |
| Tiingo EOD | Cierres, cierre ajustado, dividendos y splits de EE. UU. | Cierre | Clave gratuita (uso personal); planes de pago | Uso personal, sin redistribución | `Tiingo` |
| EODHD | Cierres de la BMV (`.MX`) | Cierre | Clave: 20 peticiones/día gratis; pago para más | Según plan | `Eodhd` |
| CSV del usuario | Operaciones, posiciones, cierres, valor liquidativo (NAV) | Cierre / NAV | — | Datos que el usuario obtiene legítimamente | `Archivo` / importador |
| Nasdaq Trader Symbol Directory | Existencia, bolsa, bandera ETF, nombre | Diario | Ninguna | Archivos públicos | `scripts/verificar_universo.py` |
| BMV — Información de emisoras | Claves de emisoras | Descarga pública (XLS) | Ninguna | Botón de descarga del sitio | Ídem |
| actinver.com/<fondo> | Categoría, ISIN, horizonte, liquidez de fondos | Estático | Ninguna | Consulta de páginas públicas permitidas por `robots.txt` (26 páginas, 1 s entre peticiones) | `config/fondos_actinver.csv` |

## Evaluadas y descartadas

| Fuente | Motivo |
|---|---|
| Stooq | La descarga CSV exige resolver un desafío anti-bot (prueba de trabajo). Automatizarlo sería evadir un control. |
| Yahoo Finance (API no oficial) | Respuesta 429 y condiciones que restringen el acceso automatizado. |
| SEC EDGAR JSON | Exige cabecera User-Agent con correo de contacto; no se envió el correo del usuario sin su permiso. Se usó Nasdaq Trader. |

## URL candidatas indicadas en el encargo

| URL | Qué ofrece | Uso que permite | Licencia / API | Uso en la terminal |
|---|---|---|---|---|
| https://es.tradingview.com/ | Gráficos, cotizaciones (tiempo real según suscripción y bolsa), ideas | Consulta personal en su web o app; *widgets* embebibles con atribución. Sus condiciones prohíben extraer datos por medios automatizados y redistribuirlos | Datos licenciados por bolsa; *Charting Library*/datos comerciales bajo contrato | **No integrada** para datos. Uso manual recomendado para confirmación visual (el MCP `tradingviewmcp` sirve para ver el propio gráfico, no para alimentar la terminal). Un *widget* embebido requeriría abrir la CSP a sus dominios: decisión del usuario |
| https://seekingalpha.com/market-news | Noticias y análisis | Lectura con suscripción; prohíbe extracción automatizada | Suscripción; sin API pública oficial | **No integrada**. Consulta manual |
| https://www.forexfactory.com/ | Calendario económico, noticias de divisas | Consulta personal; condiciones restringen extracción | Sin API oficial documentada | **No integrada**. Recomendación: calendario oficial de Banxico/INEGI para eventos de México |
| https://www.insiderfinance.io/insider-trades | Operaciones de *insiders* (derivadas del Formulario 4 de la SEC) | Producto con suscripción | Comercial | **No integrada**. Alternativa oficial y gratuita: SEC EDGAR (Formulario 4) si el usuario decide incluir esa señal |
| https://www.dukascopy.com/swiss/spanish/cfd/what-are-cfds/ | Contenido educativo sobre CFD | Lectura | — | Contexto. CFD y apalancamiento están **fuera** de ambas carteras |
| https://www.barchart.com/ | Cotizaciones, históricos, opciones | Consulta en su web; descargas limitadas a miembros; condiciones prohíben *scraping* | API comercial *Barchart OnDemand* (licencia de pago) | **No integrada**. Alternativa si se contrata: adaptador nuevo con la misma interfaz |

## Tiempo real

Ninguna fuente configurada entrega tiempo real. Para tenerlo genuinamente, el usuario debe decidir:

1. **Qué mercados**: BMV (emisoras locales y SIC) y/o EE. UU.
2. **Proveedor y contrato**: para BMV, distribuidores autorizados de datos de la bolsa (p. ej. Infosel u otros *vendors* licenciados); para EE. UU., proveedores con datos consolidados (SIP) o de una sola bolsa (IEX), p. ej. Tiingo IEX, Polygon/Massive, Alpaca o Databento.
3. **Tipo de licencia de bolsa**: usuario no profesional vs profesional, uso de visualización vs *non-display*; muchas bolsas cobran por usuario.
4. **Costo mensual y límites** (conexiones simultáneas, símbolos).
5. **Aceptar transmisión** (WebSocket) en lugar de consultas periódicas.

La arquitectura está lista: se añade un adaptador con `tipo_dato = "tiempo_real"` (vigencia de 120 s configurable) o `"retrasado"` (20 min) y la interfaz ya los etiqueta. Mientras tanto, todo se presenta como «cierre» con su fecha.
