# Proveedores con acceso gratuito y herramientas visibles en la terminal

Revisión: **16-oct-2026**, con la documentación oficial enlazada en cada fila. Cuando una página no permite confirmar
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
| [Twelve Data](https://twelvedata.com/pricing) | Gratis permanente (Basic) | 3 mercados sin nombrar; BMV sin confirmar | Intradía y diaria | Sin confirmar | Anuncia tiempo real para acciones y ETF de EE. UU. | No | No | 8 créditos por minuto, 800 por día; WebSocket de prueba | Cuenta | Términos de Twelve Data | Especificación ya existe (`config/proveedores/twelvedata_bmv.json`), **sin activar** | No figura |
| [Massive (antes Polygon)](https://massive.com/pricing) | Gratis permanente (Stocks Basic) | EE. UU., USD | Agregados de 1 minuto | 2 años | **Solo cierre del día** | Sin operaciones ni cotizaciones | No se pudo confirmar | 5 por minuto | Cuenta | Términos de Massive | No implementado: no agrega nada a Alpaca | Conector «Polygon.io» |
| Finnhub | Gratis | EE. UU. | — | — | **No se pudo confirmar en la página oficial** (60/min y 50 símbolos por WebSocket solo en fuentes de terceros) | — | — | — | Cuenta | — | No implementado | No figura |
| [Databento](https://databento.com/pricing) | Crédito único de USD 125, solo para datos históricos | CME, OPRA, Nasdaq TotalView y otros | Ticks y barras | Amplia | Tiempo real **solo de pago** (desde USD 199 al mes) | Ticks con lado del agresor y libro completo (MBO/MBP) | OPRA histórico con el crédito | Por consumo | Cuenta; tarjeta no confirmada | Licencia por dataset | No implementado (el crédito es un gasto: lo decide usted) | No figura |
| Quantower | Software gratuito; los datos de cada conector se pagan aparte | — | — | — | Depende del conector | dxFeed, Rithmic, IB y Tradier dan profundidad u opciones **con su propia suscripción** | — | — | — | — | No aplica: Quantower es otra aplicación y no lee la base de la terminal | — |

Notas:
- Que la terminal pueda usar una API no significa que Quantower tenga un conector compatible. De las fuentes
  implementadas, solo Alpaca y Alpha Vantage aparecen en su lista.
- Acceder gratis a un precio no da licencia para mostrarlo o redistribuirlo. Tiingo lo prohíbe expresamente; la
  terminal escucha solo en 127.0.0.1 y es de uso personal.
- Ninguna fuente gratuita ofrece un feed completo de CME u OPRA en tiempo real. No hay datos gratuitos de la BMV ni
  de MexDer en tiempo real.

## 2. Matriz por herramienta

| Herramienta | Datos mínimos | Cálculo | Con lo gratuito hoy |
|---|---|---|---|
| Velas con SMA/EMA, MACD, estocástico y SAR | OHLCV | Medias, MACD 12/26/9, estocástico 14/3/3, SAR 0.02–0.2; valor nulo mientras calienta | **Sí**: EE. UU. (Alpaca SIP, ≥ 15 min), cripto (Bitso), BMV diaria (EODHD) o CSV |
| Perfil de volumen | Operaciones con precio y tamaño | Volumen por nivel de precio (POC/VAH/VAL aún no se calculan) | **Sí, implementado en Order Flow** con la cinta guardada: SIP diferida (EE. UU.) o Bitso (cripto) |
| TPO / Market Profile | Barras de 30 min por sesión | Letras por periodo y nivel | Calculable con las barras de Alpaca; **no implementado** |
| DOM y mapa de calor de liquidez | Libro por niveles en el tiempo | Instantáneas sin interpolar | **Solo cripto** (Bitso). En EE. UU., IEX da 1 nivel; la profundidad es de pago |
| Footprint y delta acumulado | Operaciones con **lado del agresor** | Volumen por precio y lado; delta = compras − ventas | **Solo cripto**. El SIP no trae el lado; con OHLCV no se puede reconstruir |
| Option Flow (cinta y filtro de Skylit) | Cinta de opciones con NBBO del instante, condición, patas, OI con fecha, spot | Ver el filtro de Skylit en `docs/mejoras-intradia-permutaciones.md` | **Parcial**: Alpaca trae operaciones indicativas con condición, pero no el NBBO histórico del instante, ni las patas, ni el OI en datos de mercado. Una cadena no sustituye la cinta |
| GEX | Gamma, OI, multiplicador, spot y moneda de una misma referencia | gamma × OI × multiplicador × S² × 0.01 | **No con datos de mercado gratuitos** (sin OI). El endpoint de contratos de Alpaca trae OI y tamaño (ver §4); mientras tanto, solo por CSV |

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
   - cadena de opciones indicativa (IV y griegas cuando vienen).
2. **Bitso por ccxt** (implementado): libro, cinta con lado, footprint y mapa de calor reales, solo de cripto en MXN.
3. **EODHD, Banxico y FRED** (implementados): cierres de la BMV, FIX y tasas.
4. **Importación de CSV autorizados** para lo que no da ninguna fuente gratuita: libro y cinta de EE. UU., opciones con
   interés abierto (GEX), cinta de opciones con NBBO (filtro de Skylit) y opciones de MexDer.

Lo que exige proveedor de pago o archivo con licencia:
- Profundidad de EE. UU. (Level 2): Databento, dxFeed u otro distribuidor.
- OPRA en tiempo real con OI.
- Cualquier dato en tiempo real de la BMV o de MexDer.

## 4. Conectores y configuración

No se agregó ningún conector nuevo en esta entrega. Los gratuitos pertinentes ya estaban implementados, con caché,
límites, validación y manejo de errores.

**Candidato pendiente de su decisión:** OI y multiplicador desde el endpoint de contratos de Alpaca
(`/v2/options/contracts`). Ese endpoint vive en la **API de trading** (cuenta de broker), no en la de datos. Aunque la
consulta sería solo de lectura, usted pidió no abrir conexiones de corretaje sin necesidad concreta, así que no se
implementó ni se probó. Si lo autoriza, permitiría calcular GEX con el OI del cierre previo.

Guía, paso a paso (claves solo en `.env`, nunca en el código):
1. `ALPACA_API_KEY_ID` y `ALPACA_API_SECRET_KEY`: cuenta gratuita de Alpaca, en «API Keys».
2. `FRED_API_KEY`: cuenta en fred.stlouisfed.org, en «API Keys».
3. `BANXICO_TOKEN`: solicítelo en el portal del SIE de Banxico.
4. `EODHD_API_KEY`, `TIINGO_API_KEY`, `ALPHAVANTAGE_API_KEY` y `EIA_API_KEY`: registro gratuito de cada proveedor.
5. Bitso no requiere clave. Para apagarlo: `[flujo.cripto] activo = false` en `config/local.toml`.
6. Reinicie la terminal y revise **Más → Datos** y el estado de cada panel.

## 5. Disponibilidad real comprobada (16-oct-2026)

Una consulta mínima por fuente. Se registró solo el resultado, sin claves.

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

- Decidir si se usa el endpoint de contratos de Alpaca (OI y tamaño) para GEX y el filtro de Skylit (§4).
- El NBBO histórico del instante y las patas de las opciones no vienen en ninguna fuente gratuita verificada. El
  filtro de Skylit solo es completo con un CSV con esos campos.
- TPO / Market Profile y POC/VAH/VAL del perfil de volumen: calculables con datos gratuitos, no implementados.
- Finnhub y Twelve Data: confirmar en su documentación oficial (cobertura de la BMV, límites) antes de conectarlos.
- Databento (USD 125 de crédito histórico) y cualquier proveedor de pago: decisión suya.
