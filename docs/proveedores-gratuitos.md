# Proveedores con acceso gratuito y herramientas visibles en la terminal

**Actualización 2-nov-2026:** solo recursos gratuitos. Twelve: clave importada y validada mediante una consulta de estado, sin cotizaciones. XMEX/BMV exige Pro y no se activa. Barchart de contrato y API de Claude también bloqueados por política vigente. [Condiciones, evidencia y controles](politica-proveedores-gratuitos-20261102.md).

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

## 9. Mesa: brechas F1–F6 (1-nov-2026)

Avance operativo posterior: `avance-gratuitos-20261101.md`. SEC ya tiene 100 publicaciones
reales de cuatro emisoras, con XOM actual CIK 2115436. Treasury 30 años tiene 24 observaciones
de la publicación original H.15, sin clave, y fuente fed_h15. No confundir esa cobertura con
verificación de la API FRED ni publicaciones SEC con BPA u hora del anuncio.

Revisión externa posterior: `confirmacion-externa-proveedores-20261101.md`. SP1 aparece
como INPC en publicaciones del propio Banxico, aún sin GET de metadatos actual validado.
XMEX general no se considera incluido en Basic: ficha oficial Pro+/Venture+, EOD y
un símbolo de prueba. Ninguna de estas confirmaciones documentales activa conectores.

Implementación y evidencia: `docs/proveedores-mesa-20261101.md` y
`docs/proveedores-20261101-evidencia/`. Pruebas HTTP simuladas no acreditan acceso real al plan.
No se leyó `.env`. No había credenciales ni identificación SEC en las variables permitidas.
Los tres conectores nuevos están **apagados por defecto**; SIN DATO cuando falta evidencia.

| ID | API oficial y dato | Estado y autenticación | Cupo y disponibilidad | Límites y pendientes |
|---|---|---|---|---|
| F2 | [FRED DGS30](https://fred.stlouisfed.org/series/DGS30) y [publicación original H.15](https://www.federalreserve.gov/releases/h15/): Treasury 30 años, diario, porcentaje | API FRED añadida, acceso con clave aún sin verificar. Vía independiente gratuita: XML H.15 + cruce DDP/FRED oficiales; 24 observaciones reales, fuente fed_h15 | H.15: dos GET de publicaciones + dos HEAD de tamaño, sin cuenta ni clave. Último periodo 29-oct-2026, conocido desde importación el 1-nov. Sin polling nuevo | No es respuesta API FRED ni cotización vigente; fuente original, unidad/plazo/identidad, huellas y disponibilidad conservadas; no sustituye periodos más recientes por más antiguos |
| F3 | [Banxico SIE](https://www.banxico.org.mx/SieAPIRest/service/v1/): tasa objetivo | SF61745 citado en documentación oficial; **no confirmado por GET de metadatos**: HTTP 400 sin token. BANXICO_TOKEN, cabecera Bmx-Token | Política local, no cuota oficial acreditada: 20/día y 8/min; catálogo y datos, una petición cada uno; sin reintentos, Retry-After persistente | Verifica título/identidad antes de pedir datos. Disponible desde descarga, nunca desde periodo histórico; apagado |
| F6 | [Banxico SIE](https://www.banxico.org.mx/SieAPIRest/service/v1/): bono M 10 años | Mismo conector/credencial que F3; **ID no confirmado**, no adivinado | Comparte cupos de F3; publicación histórica, no rendimiento vigente | Exige título bono M/tasa fija y 10 años; rechaza UDIBONOS u otro plazo. Falta catálogo y GET oficial; SIN DATO |
| F4 | [Banxico SIE](https://www.banxico.org.mx/SieAPIRest/service/v1/): INPC, índice mensual | Ruta optativa con BANXICO_TOKEN; **ID no confirmado**. SP1 dio HTTP 400 sin token; no se configura. No requiere credencial nueva INEGI | Comparte cupos de F3; periodo mensual separado del conocimiento | Exige título completo del índice; variación no sustituye nivel. Apagado hasta identificar serie en catálogo y confirmar por API; no se solicita token |
| F1a | [SEC submissions](https://www.sec.gov/search-filings/edgar-application-programming-interfaces): publicación de 8-K/8-K-A Item 2.02 | Verificados MU/723125, NVDA/1045810, AMD/2488 y XOM/2115436; 100 publicaciones reales. ClienteSEC con contacto Git existente usado solo en memoria, sin .env ni clave API | Seis GET reales: cuatro iniciales, catálogo oficial y XOM actual. CIK histórico 34088 rechazado; fuentes automáticas siguen apagadas. Cupo local 5/min y 20/día | Aceptación EDGAR no prueba hora del anuncio ni BPA. Estimación/reportado/revisión/reacción sin fuente permanecen SIN DATO |
| F1b | [Alpha Vantage EARNINGS_CALENDAR](https://www.alphavantage.co/documentation/#earnings-calendar): fecha prevista, estimación BPA y moneda | ALPHAVANTAGE_API_KEY; apagado, plan_verificado=false. **Cero consultas reales**; inclusión en plan gratuito no acreditada | Techo local 25/día compartido con alpha_vantage; calendario 1/min, CSV de 3 meses, actualización diaria | Guarda conocimiento y todas las revisiones; excluye previsión posterior al anuncio. No entrega por sí solo BPA realizado/revisión/hora. Prueba autenticada única pendiente |
| F5 | [Twelve Data XMEX](https://twelvedata.com/exchanges/XMEX), [precios](https://twelvedata.com/pricing): cierres BMV | Diagnóstico manual de una petición a símbolo verificado con TWELVEDATA_API_KEY. **Cero consultas reales**; no se modifica cola/configuración productiva | Basic anunciado 8 créditos/min y 800/día; diagnóstico conserva menor cupo local de 700/día y 8/min; EOD | Ficha XMEX indica Pro+/Venture+ y GMEXICOB de prueba. Una excepción no prueba cobertura gratuita general ni nivel de la cuenta. Sin acceso acreditado no se activa respaldo |

La documentación es evidencia del contrato y condiciones anunciadas, no de los permisos de una cuenta.
Ninguna fuente de esta tabla sustituye ticks/DOM CME; gratis no implica licencia de redistribución.

### Actualización operativa posterior del 1-nov-2026

Esta actualización reemplaza los estados de acceso pendientes de la tabla anterior,
sin borrar la evidencia histórica. El usuario autorizó el cargador habitual de claves
solo en memoria y ocho consultas gratuitas; se consumieron las ocho. No se activan fuentes.

| ID | Evidencia real | Límite que permanece |
|---|---|---|
| F2 | FRED DGS30: un GET HTTP 200, 23 observaciones guardadas | Publicación histórica, no cotización actual; H.15 conserva identidad separada |
| F3 | SIE SF61745: catálogo y datos HTTP 200, 24 observaciones | Tasa objetivo publicada; conocimiento desde captura |
| F6 | SIE SF30057: catálogo y datos HTTP 200, 21 observaciones | Rendimiento promedio mensual a 10 años, nunca diario/vigente |
| F4 | SIE SP1: catálogo HTTP 200, índice general nacional mensual confirmado por ID, título legado y cifra Indices | Datos todavía no descargados. Se corrigió el validador con pruebas; no se inventaron observaciones |
| F1b | EARNINGS_CALENDAR: un GET HTTP 200, tres estimaciones guardadas | BPA reportado EARNINGS no consultado aún; código y revisiones observadas solo probados offline |

Evidencia saneada: `proveedores-20261101-evidencia/gratis-verificacion-autorizada-20261101.json`
y `sie-sp1-catalogo-20261101.json`. Detalle y siguientes verificaciones:
`avance-gratuitos-20261101.md`. Se mantienen los cupos locales existentes; la respuesta
HTTP 200 no acredita redistribución, datos en tiempo real ni permisos perpetuos del plan.

### Seis consultas adicionales autorizadas y realizadas (1-nov-2026, 12:55–12:58 CDMX)

Evidencia: `proveedores-20261101-evidencia/gratis-seis-adicionales-20261101.json`.
El mismo cargador habitual se usó únicamente en memoria, sin mostrar ni copiar claves.
Un contador impuso un máximo total de seis GET, sin reintentos ni redirecciones;
las consultas Alpha se separaron más de 60 segundos y respetaron el cupo local compartido.

- **F4 / SP1:** metadatos y datos HTTP 200; 24 índices mensuales guardados, de octubre
  de 2024 a septiembre de 2026. Unidad índice, no porcentaje ni inflación interanual
  calculada. Se confirmó nuevamente el título legado y la identidad antes de guardar.
- **F1 / EARNINGS:** cuatro GET HTTP 200; ocho BPA reportados por cada MU, NVDA, AMD y
  XOM (32 en total). Primeras capturas locales, no necesariamente el valor original del
  anuncio. La API no informó moneda ni base contable en el contrato recibido: se muestran
  como no informadas, sin asumir USD ni calcular sorpresa.
- El campo `reportTime` aporta una ventana pre/post-market, no una hora exacta.
  Se conserva y presenta la procedencia Alpha por separado. La reacción permanece SIN DATO.
- No se observaron revisiones entre capturas: revisión SIN DATO, sin fabricar una
  reformulación. El registro conserva cambios futuros observados con su conocimiento real.

No se habilitaron conectores automáticos ni se modificaron precios, modelos o estrategias.
Estas respuestas puntuales no prueban derechos de redistribución ni disponibilidad perpetua.

### Variación histórica diaria con datos existentes

El contrato admite ventana pre/post-market. Cuando EARNINGS.reportTime la declara en
una observación API, el calendario puede mostrar variación descriptiva con los dos
cierres consecutivos XNYS correspondientes, en USD y de una sola fuente, conocidos
al corte y con la sesión final ya cerrada. No exige inventar hora exacta ni usar
aceptación SEC. Se rechazan barras sintéticas, retrasadas, futuras o de monedas/fuentes
mezcladas y no se rellena una sesión ausente con otra posterior. No aísla splits,
dividendos ni causalidad; no es una señal de trading. Se verificaron 32 variaciones
offline sin nuevas consultas: `variacion-diaria-auditoria-20261101.json` en la carpeta
de evidencia. La hora exacta y revisiones no observadas siguen SIN DATO.

### F5: diagnóstico autorizado sin credencial disponible

Se intentó preparar la comprobación única para BMV:ALPEK. El cargador habitual no
aportó TWELVEDATA_API_KEY: **0 llamadas HTTP**, sin dato guardado ni activación.
`twelve-unico-diagnostico-20261101.json` registra ese resultado saneado. No se acredita
rechazo de Basic ni acceso de cuenta. El permiso de una llamada sigue sin consumirse;
no se crea una cuenta ni se solicita una clave nueva. La cobertura documental de XMEX
y la futura respuesta autenticada son evidencias diferentes, que no se sustituyen.

### Respaldo mensual FRED/BLS — verificación adicional

Tres consultas autorizadas, tres HTTP 200: UNRATE, PAYEMS y CPIAUCSL. Se guardaron
81 observaciones, incluido CPI_YOY calculado con el mismo mes del año previo de la
misma captura. Fuente fred_macro, conocimiento desde descarga, no vintage histórico.
Identidad/unidades oficiales: https://fred.stlouisfed.org/series/UNRATE,
https://fred.stlouisfed.org/series/PAYEMS y https://fred.stlouisfed.org/series/CPIAUCSL.
Evidencia: fred-macro-respaldo-20261101.json y macro-respaldo-lectura-20261101.json.
No requiere cuenta/clave nuevas: usa FRED existente. No se habilita por defecto ni
se añade a los conectores automáticos. La Mesa conserva BLS para meses iguales o más
recientes y etiqueta FRED al usarlo; no sustituye una publicación fresca por otra vieja.

La base habitual ya tenía BLS para septiembre: el respaldo no reemplazó sus datos.
La petición pública BLS sin clave recibió HTTP 200 pero no confirmó el contrato
completo; no se guardó ese intento ni se presenta como validación. No se evade un
bloqueo ni se convierte una respuesta HTTP en cobertura acreditada.

### Alternativas para el faltante BMV: resultado de revisión oficial

| Proveedor | Acceso gratuito documentado | Cobertura BMV verificada en esta revisión | Acción |
|---|---|---|---|
| EODHD | 20 llamadas/día, 20/min y un año de historia en https://eodhd.com/pricing y https://eodhd.com/financial-apis/api-limits | Conector existente; su cuota no cubre por sí sola un refresco ilimitado | Reutilizar sin ampliar límites; no es una API nueva |
| Twelve Data | Basic; XMEX https://twelvedata.com/exchanges/XMEX muestra Pro+/Venture+, EOD y un símbolo de prueba | Cuenta sin comprobar: no hay clave disponible; diagnóstico autorizado hizo 0 llamadas | Configuración manual de una clave existente si el usuario dispone de ella. No comprar ni crear cuenta automáticamente |
| Marketstack | https://marketstack.com/pricing anuncia 100 consultas/mes, un año EOD, HTTPS y uso no comercial | No confirmada: información de exchanges no equivale a precios de XMEX en Free | No se implementa como proveedor BMV confirmado ni se activa. FAQ indexada menciona 1000, pero tarifa y FAQ abierta indican 100: no usar el límite mayor |
| DataBursatil | No confirmada en fuente oficial accesible | Sitio oficial https://databursatil.com respondió 403 al lector | No eludirlo ni usar comentarios de terceros como licencia; verificación manual pendiente |

Marketstack cuenta por símbolo, no solo por petición HTTP, según https://marketstack.com/faq.
No se recomienda abrir otra cuenta como solución BMV sin confirmar primero mercado,
permiso del plan y cuota. Nada de esta tabla sustituye ticks/DOM CME ni acredita datos
en tiempo real, redistribución libre o una estrategia operativa.
# Comprobación adicional BLS sin clave — 1-nov-2026

Comprobación posterior del cliente ya implementado: `BLS.consultar`, sin credencial y con SQLite en memoria, completó una petición para 2024–2026. Resultado válido: 32 CPI, 32 desempleo, 33 empleo y 20 variaciones CPI interanuales; periodos 2024-01 a 2026-09. No se igualan artificialmente coberturas ni se cuentan M13 como meses. `proveedores-20261101-evidencia/bls-conector-real-20261101.json` registra el alcance y el consumo temporal de una petición. Código existente sin cambios; no se activó el conector ni se importaron observaciones a la base habitual. No acredita vintages históricos o el instante de publicación.

Una petición oficial POST a `https://api.bls.gov/publicAPI/v2/timeseries/data/`, sin credenciales ni carga de entorno, confirmó REQUEST_SUCCEEDED y 63 observaciones mensuales (21 por CUSR0000SA0, LNS14000000 y CES0000000001) para 2025–2026. No se importaron datos ni se activaron conectores. Es cobertura macro estadounidense, sin profundidad de mercado; no sustituye tick/DOM CME ni acredita vintage o publicación exacta. La prueba no mide el cupo ni verifica otras ventanas. Evidencia: `proveedores-20261101-evidencia/bls-sin-clave-revision-20261101.json`; firma oficial: https://www.bls.gov/developers/api_signature_v2.htm. Se conserva el intento anterior HTTP 200 no confirmado como historial.


### Finviz Elite

La exportación que usa este conector corresponde a Elite y se excluye de la política gratuita. El monitor bloquea la actualización antes de la petición aunque exista un token configurado. La búsqueda de llamadas en terminal/ y tools/ encontró una sola ruta de producción, que pasa por ese bloqueo. Seis pruebas de test_finviz.py aprobadas con datos locales y HTTP simulado.

### EODHD diferido y cierres

El plan gratuito declara 20 llamadas diarias para uso personal sin tarjeta. El conector diferido comparte contador y pausa Retry-After con cierres. La regresión conjunta dio 74 aprobadas y una advertencia (pytest-cupo-eodhd-integrado.txt). El 3 de noviembre de 2026 se verificó el formato de la respuesta de AAPL.US con la clave pública demo, con marca de evento 13:54 UTC. Esa prueba no acredita acceso ni retraso efectivo para BMV. [Documentación oficial](https://eodhd.com/financial-apis/live-ohlcv-stocks-api).

### Calendario económico del BLS

Consulta manual gratuita de fechas de empleo e inflación de EE. UU., sin credenciales. La descarga oficial devolvió HTTP 403 para bls.ics desde esta PC. Mesa enlaza al calendario oficial incluso si la API local falla (Chromium aislado con HTTP 503 simulado). Esta alternativa cubre publicaciones del BLS. [Calendario oficial](https://www.bls.gov/schedule/).

### Calendario de publicaciones BEA

Fuente pública sin clave ni facturación. Mesa muestra una copia fechada, en UTC, de los próximos siete días. Las fechas pueden cambiar y se mantienen separadas de cifras publicadas y modelos. Para refrescar la copia ejecuta `uv run python tools/actualizar_calendario_bea.py` desde el repositorio. Si la descarga falla, se conserva el último corte. [Calendario oficial](https://www.bea.gov/news/schedule/icalendar).

### SMARTRC 14: precios de valuación y cierres negociados

La ficha pública de Actinver identifica SMARTRC 14 y publica un precio teórico fechado. El reporte diario describe rendimientos calculados con precios de valuación. Ambos sirven como referencia documental del fondo; no acreditan una serie de cierres negociados ni volumen. La oferta de Grupo BMV de Hechos Diarios y Precios de Cierre Mensual es de pago con tarjeta. El cuadro CF103 de Banxico ofrece indicadores de bolsa, no el histórico de esa emisión. Se conserva SIN DATO en Velas hasta verificar una serie autorizada de cierres para la clave exacta.

- Ficha del fondo: https://portal.actinver.com/es/smartrc
- Reporte de valuación: https://actinver.com/documents/d/actinver/reporte-diario
- Productos de Grupo BMV: https://sibolsa.com/es/Grupo_BMV/Publicaciones_en_linea
- Cuadro CF103: https://www.banxico.org.mx/SieInternet/consultarDirectorioInternetAction.do?accion=consultarCuadro&idCuadro=CF103

**Vía local si ya se dispone de un archivo autorizado.** El importador existente admite
la plantilla de precios con `fecha,instrumento_id,precio,moneda,tipo_dato`.
Para cierres negociados de la serie 14, use `BMV:SMARTRC`, `MXN` y `cierre`;
revise la previsualización antes de confirmar. El importador guarda el origen como
`archivo` y puede reemplazar filas coincidentes de ese origen, por lo que conviene
conservar aparte el documento de procedencia. Este formato aporta cierres fechados,
sin OHLC intradía ni volumen. El precio teórico de la ficha no debe importarse como cierre.

### Pausas de proveedores y regresión integrada

Los clientes de contexto que heredan `ContextoAPI.json` pasan por `Adaptador._get`.
BLS usa POST de lectura y registra `Retry-After` para HTTP 429 y 503. Comprueba
la pausa antes de consumir cuota. La regresión integrada de BEA y BLS terminó
con 915 aprobadas y una advertencia con el motor apagado. El cotejo de las rutas
GET/POST directas en `terminal/adaptadores` y `terminal/centro_conectores.py`
no equivale a verificar todos los clientes de `terminal/` ni la vigencia de sus datos.

### Hora de distribución del comunicado de resultados de Micron

MU, cuarto trimestre fiscal 2026, periodo terminado el 3 de septiembre. El comunicado emitido por Micron y distribuido por GlobeNewswire registra el 30 de septiembre de 2026 a las 16:01 ET (20:01 UTC), con precisión de minuto. Es la hora de distribución por ese canal, distinta del registro en SEC y de la conferencia. Evidencia para TP01-01, sin extrapolar a otros trimestres, emisoras o revisiones. Todavía no se ingiere como dato de Mesa.

https://www.globenewswire.com/news-release/2026/09/30/3372366/0/en/micron-technology-inc-reports-record-fiscal-fourth-quarter-and-full-year-2026-results.html
