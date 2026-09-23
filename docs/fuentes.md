# Fuentes de datos: tipo, retraso, límites, credenciales y condiciones

Mediciones del 2026-09-23 (hora de México) en este PC. «Retraso medido» = antigüedad del dato más reciente al consultarlo; «latencia» = tiempo de respuesta HTTP.

## Precios y tipo de cambio

| Fuente | Dato | Tipo | Retraso medido / esperado | Límite configurado | Credencial | Condiciones | Estado |
|---|---|---|---|---|---|---|---|
| **Banxico SIE** (SF43718) | USD/MXN FIX | Cierre diario (FIX ~12:00 CDMX) | Mismo día hábil | 200/día | Token gratuito `BANXICO_TOKEN` | API oficial; respetar límites del SIE | Implementado; **requiere token** (fuente primaria de FX cuando existe) |
| **FRED** (DEXMXUS) | USD/MXN mediodía NY | Cierre diario | **2–3 sesiones**: el 23-sep el último dato era del 18-sep; latencia 0.55 s | 50/día | No | Datos públicos; citar FRED | **Funcionando** (respaldo de FX) |
| **Tiingo EOD** | Cierre, ajustado, dividendos, splits de EE. UU. (SIC y ETF) | Cierre | Mismo día tras el cierre de NYSE | 45/h, 900/día | `TIINGO_API_KEY` (gratuita) | Uso personal; sin redistribución | Implementado; **requiere clave** |
| **Alpaca Market Data** (solo datos) | Barras diarias de EE. UU. (crudas y ajustadas) y **último precio en vivo de IEX** por WebSocket | Cierre (histórico SIP con 15 min de retraso) + **tiempo real IEX** (hasta 30 símbolos) | Histórico: mismo día; en vivo: segundos (IEX ≈ 2–3 % del volumen de EE. UU., el precio sigue al consolidado) | 5 000/día (plan: 200/min); 1 conexión WebSocket | `ALPACA_API_KEY_ID` + `ALPACA_API_SECRET_KEY` (cuenta gratuita; claves de Paper Trading) | Plan gratuito de datos; la terminal solo llama `data.alpaca.markets` y `stream.data.alpaca.markets`, nunca la API de operaciones | Implementado; **requiere claves**. Protocolo verificado el 23-sep (respuesta `connected` y rechazo 402 con clave falsa) |
| **Barchart OnDemand** | Históricos EE. UU. | Cierre | Según contrato | 400/día | `BARCHART_API_KEY` | Licencia de pago; el sitio prohíbe extracción automatizada | Implementado; **requiere contrato** |
| **EODHD** | Cierres de la BMV (`.MX`) | Cierre | Mismo día tras el cierre de la BMV | 18/día (plan gratis 20) | `EODHD_API_KEY` | Según plan | Implementado; **requiere clave** |
| **CSV del usuario** | Precios, NAV de fondos, operaciones, universo del simulador | Cierre / NAV | El del archivo | 1 MB, 5 000 filas | No | Datos obtenidos legítimamente por el usuario | Funcionando |

## Contexto (no precios)

| URL / fuente | Uso en la terminal | Vía | Retraso / latencia medidos | Límite | Credencial | Estado |
|---|---|---|---|---|---|---|
| **forexfactory.com** | Calendario macro USD/MXN (Fed, NFP, CPI, Banxico) → alerta «evento de alto impacto próximo» | Feed de exportación semanal `nfs.faireconomy.media/ff_calendar_thisweek.json` (el que enlaza su sitio) | Calendario de la semana en curso; 80 eventos obtenidos; latencia 0.23 s | 2/h (se consulta ≤ 1/h) | No | **Funcionando** |
| **seekingalpha.com/market-news** | Titulares por emisora de EE. UU. en cartera → impacto y sentimiento (léxico o LLM local) → alerta de noticia | RSS público `seekingalpha.com/api/sa/combined/<TICKER>.xml` (no bloqueado en `robots.txt`); solo titular y enlace | Titular más reciente de ~1 h de antigüedad; latencia 0.55 s | 60/h (≤ 1 por emisora cada 30 min) | No | **Funcionando** |
| **insiderfinance.io/insider-trades** | Señal de insiders | Producto de suscripción sin API pública → se usa la fuente oficial **SEC EDGAR (Formulario 4)** | Formulario 4: hasta 2 días hábiles tras la operación (regla SEC) | 1 000/día, ≤ 10/s | `SEC_USER_AGENT` (nombre + correo de contacto que exige la SEC) | SEC implementado; **requiere configuración**; InsiderFinance **requiere suscripción** |
| **es.tradingview.com** | Gráfica y análisis técnico por activo (`BMV:`, `NASDAQ:`, `NYSE:`, `AMEX:`) | **Widget oficial embebible** en una página aislada `/grafica/<id>` con CSP propia; el MCP `tradingviewmcp` solo para confirmación visual manual | Datos y retraso los define TradingView (según la bolsa y su plan) | — | No (widget) | **Funcionando** (widget carga en Chrome; ver `docs/evidencia/grafica-tradingview.png`) |
| **dukascopy.com** (CFD) | Ayuda contextual: qué es un CFD; **CFD y apalancamiento fuera de las carteras** | Enlace en «Ayuda» | — | — | — | Implementado (enlace) |
| **barchart.com** | Históricos/técnicos | **Barchart OnDemand API** (adaptador `Barchart`) | Según contrato | 400/día | `BARCHART_API_KEY` | **Requiere contrato** |

Complementarias: Nasdaq Trader Symbol Directory y descarga pública de emisoras de la BMV (verificación del universo, `scripts/verificar_universo.py`); fichas públicas de fondos y trackers de actinver.com (`config/fondos_actinver.csv`); bases oficiales del Reto (`config/reto.yaml`).

## Descartadas

| Fuente | Motivo |
|---|---|
| Stooq | La descarga exige resolver un desafío anti-bot: automatizarlo sería evadir un control. |
| Yahoo Finance (API no oficial) | HTTP 429 y condiciones que restringen el acceso automatizado. |
| Extraer páginas de TradingView, Barchart, Seeking Alpha o InsiderFinance | Sus condiciones lo prohíben; se usan widget, RSS, API oficial o la fuente primaria (SEC). |

## Tiempo real

**Ninguna fuente gratuita y autorizada entrega tiempo real de las emisoras locales de la BMV.** El simulador del Reto usa la transmisión de la BMV, pero no ofrece API pública. Las emisoras locales se trabajan con cierres diarios y lo indica cada dato (tipo «cierre», fecha, retraso en horas).

**Emisoras del SIC y ETF (implementado, gratis):** con claves de Alpaca la terminal abre un WebSocket IEX durante el horario de NYSE, recibe cada operación de hasta 30 símbolos (prioridad: posiciones, propuestas vigentes, referencia S&P 500) y guarda el último precio cada 15 s como dato `tiempo_real` (vigente ≤ 120 s; con el mercado cerrado se evalúa como cierre). El precio en MXN = precio en vivo × tipo de cambio más reciente (Banxico FIX o FRED): el tipo de cambio **no** es intradía, así que la conversión puede diferir del simulador en lo que se mueva el peso durante el día. Las propuestas y alertas se recalculan con precios en vivo cada 5 min o antes si algún símbolo se mueve ≥ 1 % (mínimo 2 min entre cálculos). Si el WebSocket falla tres veces seguidas se consulta el último precio por REST cada minuto (etiquetado «retrasado»). El cierre oficial sustituye las cotizaciones en vivo del día.

Opciones para tener tiempo real genuino (decisión del usuario):

1. **Proveedor de datos de la BMV con licencia** (distribuidores autorizados como Infosel u otros *vendors*): costo mensual y contrato de datos de bolsa (usuario no profesional vs profesional).
2. **EE. UU. (emisoras del SIC y ETF)**: planes de pago con datos consolidados o de una bolsa (Tiingo IEX, Polygon/Massive, Alpaca, Databento). Útil como referencia, pero el simulador opera en MXN en la BMV.
3. **Su propia sesión del simulador**: automatizar la lectura de la página del Reto requeriría su autorización explícita **y** que las bases lo permitan; el reglamento (§11) solo reconoce órdenes capturadas desde el navegador y el Comité puede descalificar por uso indebido. No se implementa.
4. **Lectura manual**: TradingView (widget o app) para seguimiento intradía; la terminal recalcula con los cierres.

La arquitectura está lista para cualquiera de estas: un adaptador nuevo con `tipo_dato = "tiempo_real"` (vigencia 120 s) o `"retrasado"` (20 min) y consulta por *streaming* (WebSocket) con reconexión.
