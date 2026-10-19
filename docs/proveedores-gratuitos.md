# Proveedores con acceso gratuito y herramientas visibles en la terminal

Revisión general: **16-oct-2026**; alternativas para Skylit revisadas **18-oct-2026**, con la documentación oficial enlazada en cada fila. Cuando una página no permite confirmar
una condición, la celda lo dice. Ningún plan se contrató ni se creó ninguna cuenta para esta revisión. Los
conectores marcados «implementado» ya existían en la terminal y se reutilizan.

## 1. Proveedores

Leyenda de acceso:
- **Gratis permanente:** plan sin costo y sin fecha de fin.
- **Crédito único:** saldo de prueba que se agota.
- **Software gratis / datos de pago:** la herramienta no cobra, pero los datos sí.

| Proveedor (doc oficial) | Acceso | Instrumentos y moneda | Velas y temporalidades | Historia | Tiempo real o retraso | Ticks, agresor, Level 2 | Opciones, OI, griegas | Límites | Registro / tarjeta | Licencia de uso | Terminal | Quantower |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [Alpaca Market Data](https://docs.alpaca.markets/docs/about-market-data-api) | Gratis permanente (Basic) | Acciones y ETF de EE. UU., USD; cripto | 1 min a 1 día | Desde 2016 | IEX en tiempo real; SIP histórico solo con más de 15 min (la terminal pide ≥ 16 min) | Operaciones SIP sin lado del agresor; bid/ask de IEX en 1 nivel; sin Level 2 | Feed «indicative» derivado de OPRA y diferido, con condición de operación (`c`). Las griegas e IV vienen en el snapshot, pero no siempre ([doc de cadena](https://docs.alpaca.markets/reference/optionchain)). El OI no está en datos de mercado: aparece en el endpoint de contratos de la API de trading ([doc](https://docs.alpaca.markets/docs/options-trading-overview)) | 200/min; 30 símbolos de acciones y 200 cotizaciones de opciones por WebSocket | Cuenta Alpaca (gratis), sin tarjeta | Plan gratuito para uso personal, sin redistribución (así lo registra la terminal); la página no detalla derechos de pantalla | **Implementado** (velas, cinta, bid/ask, cadena) | Conector «Alpaca: Stocks» ([lista](https://www.quantower.com/connections)) |
| [Bitso](https://docs.bitso.com/bitso-api/docs/general-concepts) vía ccxt | Gratis permanente (API pública) | Cripto en MXN | Velas de la API pública | No confirmada en la doc | Tiempo real (API pública) | Operaciones con lado; libro con profundidad | No aplica | 60 por minuto por IP en la API pública; si se excede, bloqueo de 1 min y luego de 24 h | Ninguno para datos públicos | Términos de Bitso; no revisados para redistribución | **Implementado** (libro, cinta, velas) | No figura en la lista de Quantower |
| [FRED](https://fred.stlouisfed.org/docs/api/fred/) | Gratis permanente | Series macro y tasas | Diaria o menor frecuencia | Larga, según la serie | Publicación oficial (no intradía) | No | No | La página consultada no da cifra | Clave gratuita | [Términos de uso](https://fred.stlouisfed.org/legal/#api) | **Implementado** | No aplica |
| [Banxico SIE](https://www.banxico.org.mx/SieAPIRest/service/v1/) | Gratis (token) | FIX USD/MXN y series de Banxico | Diaria | Larga | Publicación oficial | No | No | La página dice que hay límites, sin cifras | Token gratuito | Términos de Banxico | **Implementado** | No aplica |
| [Tiingo](https://www.tiingo.com/about/pricing) | Gratis permanente (Starter) | EE. UU., USD | Diaria (el IEX intradía del plan gratis no se pudo confirmar) | Más de 30 años | Cierres | No | No | 50 por hora, 1,000 por día, 500 símbolos al mes, 1 GB | Cuenta, sin tarjeta | **Solo uso interno y personal**: no se puede mostrar a terceros | **Implementado** | No figura |
| [EODHD](https://eodhd.com/pricing) | Gratis (sandbox) | La BMV la confirmó la propia terminal; la página no lista bolsas | Diaria | 1 año | Cierres; cotización con 15 min de retraso | No | No | 20 por día (más 500 de bienvenida una sola vez) | Cuenta | Términos de EODHD | **Implementado** (BMV) | No figura |
| [Alpha Vantage](https://www.alphavantage.co/premium/) | Gratis permanente | EE. UU. y otros | Diaria (lo premium no está detallado) | Según la función | Para tiempo real o 15 min exige trámite de «data entitlement» | No | Sin confirmar en el plan gratis | 25 por día | Clave gratuita | Términos de Alpha Vantage | **Implementado** (estados financieros) | Conector «Alpha Vantage» |
| [Twelve Data](https://twelvedata.com/pricing) | Gratis permanente (Basic) | EE. UU., forex y cripto; **BMV fuera de Basic**, salvo símbolo de prueba | Intradía y diaria | Sin confirmar | Anuncia tiempo real para acciones y ETF de EE. UU. | No | No | 8 créditos por minuto, 800 por día; WebSocket de prueba | Cuenta | Uso personal, interno y no comercial; Basic indica uso interno sin visualización | Especificación ya existe (`config/proveedores/twelvedata_bmv.json`), **sin activar** | No figura |
| [Massive (antes Polygon)](https://massive.com/pricing) | Gratis permanente (Stocks Basic) | EE. UU., USD | Agregados de 1 minuto | 2 años | **Solo cierre del día** | Sin operaciones ni cotizaciones | No se pudo confirmar | 5 por minuto | Cuenta | Términos de Massive | No implementado: no agrega nada a Alpaca | Conector «Polygon.io» |
| [Finnhub](https://finnhub.io/pricing) | Gratis, condiciones sin confirmar | EE. UU., cobertura gratuita sin confirmar | — | — | Sin confirmar | — | — | **Cupo gratuito sin confirmar**; techo general de 30 llamadas/s y HTTP 429 por exceso (extracto oficial; §7) | Cuenta | Sin confirmar | No implementado | No figura |
| [Databento](https://databento.com/pricing) | Crédito único de USD 125 (vence a los 6 meses; histórico o primer mes de suscripción) | CME, OPRA, Nasdaq TotalView y otros | Ticks y barras | Amplia | Tiempo real **solo de pago** (desde USD 199 al mes) | Ticks con lado del agresor y libro completo (MBO/MBP) | OPRA histórico con el crédito | Por consumo | Cuenta; tarjeta no confirmada | Licencia por dataset | No implementado (el crédito es un gasto: lo decide usted) | No figura |
| Quantower | Software gratuito; los datos de cada conector se pagan aparte | — | — | — | Depende del conector | dxFeed, Rithmic, IB y Tradier dan profundidad u opciones **con su propia suscripción** | — | — | — | — | No aplica: Quantower es otra aplicación y no lee la base de la terminal | — |

Notas:
- Que la terminal pueda usar una API no significa que Quantower tenga un conector compatible. De las fuentes
  implementadas, solo Alpaca y Alpha Vantage aparecen en su lista.
- Acceder gratis a un precio no da licencia para mostrarlo o redistribuirlo. Tiingo lo prohíbe expresamente; la
  terminal escucha solo en 127.0.0.1 y es de uso personal.
- Entre las fuentes revisadas no se verificó una alternativa gratuita permanente que complete todos los campos
  de Skylit; ver §8. Esto no es una afirmación exhaustiva sobre todos los proveedores del mercado.

## 2. Matriz por herramienta

| Herramienta | Datos mínimos | Cálculo | Con lo gratuito hoy |
|---|---|---|---|
| Velas con SMA/EMA, MACD, estocástico y SAR | OHLCV | Medias, MACD 12/26/9, estocástico 14/3/3, SAR 0.02–0.2; valor nulo mientras calienta | **Sí**: EE. UU. (Alpaca SIP, ≥ 15 min), cripto (Bitso), BMV diaria (EODHD) o CSV |
| Perfil de volumen | Operaciones con precio y tamaño | Volumen por nivel de precio, POC y área de valor del 70 % (VAH/VAL) | **Sí, implementado en Order Flow** con la cinta guardada: SIP diferida (EE. UU.) o Bitso (cripto) |
| TPO / Market Profile | Barras de 30 min por sesión | Periodos de 30 min por sesión y nivel, con zona horaria explícita | **Implementado en Order Flow** sobre barras guardadas; sin barras suficientes devuelve nulo, sin interpolación |
| DOM y mapa de calor de liquidez | Libro por niveles en el tiempo | Instantáneas sin interpolar | **Solo cripto** (Bitso). En EE. UU., IEX da 1 nivel; la profundidad es de pago |
| Footprint y delta acumulado | Operaciones con **lado del agresor** | Volumen por precio y lado; delta = compras − ventas | **Solo cripto**. El SIP no trae el lado; con OHLCV no se puede reconstruir |
| Option Flow (cinta y filtro de Skylit) | Cinta de opciones con NBBO del instante, condición, patas, OI con fecha, spot | Ver el filtro de Skylit en `docs/mejoras-intradia-permutaciones.md` | **Parcial, implementado**: cinta indicativa de Alpaca guardada con condición y filtro sobre ella o CSV. NBBO histórico del instante, patas y OI siguen «no evaluable» si faltan; la interfaz indica que el filtro completo no se aplicó |
| GEX | Gamma, OI, multiplicador, spot y moneda de una misma referencia | gamma × OI × multiplicador × S² × 0.01 | **Condicionado a datos compatibles**: contratos Paper autorizado aporta OI de cierre previo fechado y tamaño si disponibles (ver §4). Acceso mínimo comprobado; no certifica gamma/spot ni cobertura. CSV autorizado sigue disponible |

Otras distinciones:
- El volumen no sustituye al interés abierto.
- El mapa de calor de liquidez (libro) no es GEX (exposición de contratos).

## 3. Combinación gratuita mínima

Una sola terminal, con paneles vinculados por símbolo (Velas, Order Flow y Option Flow conservan el instrumento). Cada
panel muestra fuente, retraso, horario y calentamiento, y avisa cuando faltan datos:

1. **Alpaca Basic** (implementado):
   - velas e indicadores de EE. UU. con ≥ 15 min de retraso;
   - cinta SIP diferida sin lado;
   - bid/ask de IEX;
   - cadena de opciones indicativa (IV y griegas cuando vienen);
   - cinta de opciones indicativa diferida (≥ 15 min), con condición y procedencia, para evaluación parcial de Skylit.
2. **Bitso por ccxt** (implementado): libro, cinta con lado, footprint y mapa de calor reales, solo de cripto en MXN.
3. **EODHD, Banxico y FRED** (implementados): cierres de la BMV, FIX y tasas.
4. **Importación de CSV autorizados** para lo que no da ninguna fuente gratuita: libro y cinta de EE. UU., opciones con
   datos faltantes para GEX, cinta de opciones con NBBO (filtro de Skylit) y opciones de MexDer.
5. **Contratos Alpaca Paper** (implementado, apagado por defecto): OI fechado y multiplicador; una consulta mínima exitosa. No mueve dinero ni completa NBBO/patas.

Lo que exige proveedor de pago o archivo con licencia:
- Profundidad de EE. UU. (Level 2): Databento, dxFeed u otro distribuidor.
- OPRA en tiempo real con OI.
- Cualquier dato en tiempo real de la BMV o de MexDer.

## 4. Conectores y configuración

Se amplió el adaptador Alpaca existente con la cinta histórica de opciones de Market Data
(`GET /v1beta1/options/trades`), caché, límites y procedencia. No se conectaron Finnhub ni Twelve Data.

**Autorización recibida (18-oct-2026):** se permite consultar exclusivamente
`GET https://paper-api.alpaca.markets/v2/options/contracts`, solo metadatos, sin órdenes, cuentas,
posiciones ni suscripciones de pago. La integración está implementada y queda desactivada por defecto.
El 18-oct se hizo una consulta mínima de un contrato y una página: **éxito**. Esto confirma acceso a esa
consulta, no cobertura completa de OI, gamma o spot. El endpoint pertenece a la API de trading,
pero la consulta no compra contratos. OI fechado y multiplicador pueden completar entradas de GEX si son
compatibles con los demás datos; no completan el NBBO histórico ni todas las patas.

Guía, paso a paso (claves solo en `.env`, nunca en el código):
1. `ALPACA_API_KEY_ID` y `ALPACA_API_SECRET_KEY`: cuenta gratuita de Alpaca, en «API Keys».
2. `FRED_API_KEY`: cuenta en fred.stlouisfed.org, en «API Keys».
3. `BANXICO_TOKEN`: solicítelo en el portal del SIE de Banxico.
4. `EODHD_API_KEY`, `TIINGO_API_KEY`, `ALPHAVANTAGE_API_KEY` y `EIA_API_KEY`: registro gratuito de cada proveedor.
5. Bitso no requiere clave. Para apagarlo: `[flujo.cripto] activo = false` en `config/local.toml`.
6. Reinicie la terminal y revise **Más → Datos** y el estado de cada panel.

Contratos Paper usa `ALPACA_PAPER_API_KEY_ID` y `ALPACA_PAPER_API_SECRET_KEY`, sin fallback del
adaptador a las claves de mercado. La comprobación autorizada usó explícitamente el par existente contra
Paper; tras su éxito se conservó ese mismo par bajo los nombres Paper en `.env` local ignorado, sin
cambiar valores ni crear claves. El interruptor no cambió. Para habilitar consultas manuales añada
`contratos_oi = true` dentro de `[flujo.alpaca]` en `config/local.toml` y reinicie. Actualice primero
metadatos y después cadena: no se completan snapshots anteriores con información conocida después.

## 5. Disponibilidad real comprobada (16-oct-2026)

Registro de la verificación real anterior del 16-oct-2026: una consulta mínima por fuente, solo resultado sin claves.
Esta ampliación se valida con un cliente HTTP falso, sin red ni claves; **no se repitieron consultas reales**
y estos resultados previos no prueban por sí solos la nueva ingestión de cinta.

| Fuente | Resultado |
|---|---|
| Alpaca, barras diarias SIP (MU) | HTTP 200, 8 barras |
| Alpaca, operaciones de opciones (MU 20-nov-26 C250) | HTTP 200, campos `t, x, p, s, c` (con condición; sin NBBO ni patas) |
| Alpaca, snapshot de opciones indicativo (MU) | HTTP 200; ese contrato vino sin `greeks` ni `impliedVolatility` |
| Bitso, ticker público | HTTP 200 |
| FRED (DGS3MO) | HTTP 200 |
| Banxico SIE (FIX) | HTTP 200 |
| EODHD (BMV) | Métricas de la terminal: éxito el 16-oct |
| Alpha Vantage y EIA | Consulta de la terminal «ok» el 16-oct |

## 6. Pendiente

- Contratos Paper: acceso mínimo verificado; el interruptor sigue apagado por defecto. Cada cadena necesita
  metadatos compatibles y gamma/spot reales para que GEX sea calculable (§4).
- No se verificó una alternativa gratuita permanente completa entre las fuentes revisadas (§8). Según la decisión
  del usuario, Skylit se mantiene parcial; un archivo autorizado con todos los campos faltantes permitiría completarlo.
- TPO / Market Profile y POC/VAH/VAL están implementados; su disponibilidad por instrumento depende de barras u operaciones guardadas suficientes.
- Finnhub: límites gratuitos pendientes de confirmación oficial legible; Twelve Data Basic no cubre la BMV general (ver §7). Ambos continúan desconectados.
- Databento (USD 125 de crédito histórico) y cualquier proveedor de pago: decisión suya.


## 7. Revisión documental oficial de Finnhub y Twelve Data (16-oct-2026)

- **Finnhub:** se consultaron [precios](https://finnhub.io/pricing) y
  [límites de la API](https://finnhub.io/docs/api/rate-limit). En esta revisión ambas páginas
  devolvieron contenido sin texto legible al lector web. Por ello **no se pudieron confirmar
  con documentación oficial los límites del plan gratuito**. Las cifras de 60 llamadas/minuto
  y 50 símbolos WebSocket que aparecen en terceros no se elevan a dato verificado ni se usan
  para configurar un conector. La búsqueda restringida al dominio oficial sí recuperó en el
  extracto indexado de [Country List / Rate Limits](https://www.finnhub.io/docs/api/country)
  un **techo general adicional de 30 llamadas/segundo** para todos los planes y respuesta
  **HTTP 429** al exceder límites. Es evidencia del extracto oficial indexado, no de una
  lectura completa de la página (que sigue sin texto legible), y **no confirma el cupo
  específico gratuito por minuto ni los símbolos WebSocket**. No se hizo ninguna petición autenticada.
- **Twelve Data Basic:** la [tarifa oficial](https://twelvedata.com/pricing) publica
  **8 créditos API/minuto, 800/día y 8 créditos WebSocket de prueba**; los créditos dependen
  del peso del endpoint y del número de símbolos. El [catálogo filtrado por Basic](https://twelvedata.com/exchanges?level=basic)
  enumera EE. UU., forex y cripto. La [ficha oficial de la BMV (XMEX)](https://twelvedata.com/exchanges/XMEX)
  indica **Pro+** para particulares, **Venture+** para empresas y datos **EOD (cierre)**.
  Por tanto, **Basic no incluye la cobertura general de la BMV**. La ficha ofrece GMEXICOB
  como símbolo de prueba; esa excepción no equivale a acceso al mercado completo.
  No se activó el proveedor ni se comprobó el acceso de ninguna cuenta mediante API.

## 8. Alternativas gratuitas para completar Skylit (18-oct-2026)

Revisión de documentación pública oficial, sin cuentas nuevas, credenciales, APIs autenticadas, compras ni
consumo de créditos. Se necesita NBBO del instante e identificación de patas por operación, además de los
otros campos del filtro. Una cadena actual o una vela no reconstruyen esos datos.

| Fuente | Oferta y condición documentada | Límite para completar Skylit |
|---|---|---|
| [Alpaca Basic / planes](https://docs.alpaca.markets/us/docs/about-market-data-api), [fuentes históricas](https://docs.alpaca.markets/us/docs/historical-option-data) y [condiciones](https://docs.alpaca.markets/us/docs/market-data-faq) | Basic gratuito, 200 peticiones históricas/min; excluye los últimos 15 min. OPRA en tiempo real es de pago. `indicative` retrasa operaciones y modifica cotizaciones. Las condiciones distinguen algunas operaciones Single Leg y Multi Leg. | Quote indicativa modificada no prueba NBBO exacto. La condición aporta información parcial, sin identificar siempre todas las patas; `I`/`S` no bastan. La guía específica de histórico indica que OPRA está disponible solo para usuarios suscritos; la exclusión de los últimos 15 min de la tabla Basic no demuestra acceso OPRA gratuito. No se cambia de feed ni se comprueba el permiso de la cuenta. |
| [Tradier Market Data](https://docs.tradier.com/docs/market-data), [Time & Sales](https://docs.tradier.com/reference/brokerage-api-markets-get-timesales) e [histórico](https://docs.tradier.com/docs/historical-data) | Sandbox retrasa acciones/opciones 15 min, sin griegas y **sin ticks**. Histórico descrito como quotes es OHLCV diario; no hay histórico de opciones expiradas. Tiempo real requiere cuenta Brokerage. | Sandbox no aporta la cinta de ticks necesaria. Las páginas no documentan NBBO histórico y todas las patas enlazados por print gratis permanentemente. No se crea cuenta ni se conecta Tradier. |
| [Cboe Delayed Quotes](https://www.cboe.com/delayed_quotes/) y [DataShop Option Trades](https://datashop.cboe.com/option-trades) | Delayed Quotes excedió el tamaño del lector: no se verificó desde ella una descarga ni derechos de automatización. DataShop vende histórico y suscripción diaria; Option Trades describe NBBO por operación y ofrece muestra. | Cadena diferida o muestra no prueban cinta histórica gratuita permanente con patas. No se compra ni se extrae el portal; no se obtuvo precio para un universo/período concreto. |
| [Databento: créditos y facturación](https://databento.com/docs/faqs/usage-pricing-and-data-credits) | USD 125 de bienvenida por equipo, una sola vez, vence a los 6 meses; válido para histórico o primer mes de suscripción. Histórico facturado por bytes. | **Crédito finito, no plan gratuito permanente**. No se confirma que cubra el universo/período ni la asociación de patas requerida. No se registra cuenta ni se consume saldo. |

**Conclusión limitada a estas fuentes:** hay datos gratuitos útiles, pero no se verificó una alternativa gratuita
permanente que complete todos los campos de Skylit. No se verificó una licencia gratuita de automatización o redistribución que amplíe los accesos descritos; las muestras y los créditos no equivalen a esa licencia. Se conserva el filtro parcial con faltantes visibles, como
indicó el usuario. Contratos Paper puede aportar OI y multiplicador, sin eliminar otros faltantes ni realizar
transacciones reales. Esta revisión no demuestra que no exista solución en ningún otro proveedor.
