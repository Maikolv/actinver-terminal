# Proveedores de datos: cobertura, licencia y latencia

Resumen operativo. El detalle está en [proveedores.md](proveedores.md) (configuración), [source-matrix.md](source-matrix.md) y [sources/](sources/).

Cada registro guarda:

- instrumento, mercado y serie;
- moneda y precio o contenido;
- proveedor;
- `event_time`, `available_at` e `ingested_at`;
- latencia medida;
- estado de calidad: `REAL_TIME`, `DELAYED`, `EOD`, `STALE` o `UNKNOWN`.

La licencia de cada fuente está en la tabla `licencias_fuente` y en su ficha.

| Proveedor (clase) | Datos | Cobertura verificada | Licencia / acceso | Latencia observada | Estado 24-sep-2026 |
|---|---|---|---|---|---|
| `BmvLicensedProvider` | Cotizaciones BMV local y SIC en MXN | Ninguna | Contrato con Grupo BMV o un distribuidor autorizado | — | **Pendiente: contrato, documentación, `BMV_API_KEY`, `BMV_URL_BASE`** |
| `ForeignMarketLicensedProvider` | Bolsa de origen (USD u otra moneda); nunca la serie SIC | Ninguna | Contrato con un proveedor de la bolsa de origen | — | **Pendiente: `EXT_ESPECIFICACION`, `EXT_API_KEY`, `EXT_URL_BASE`** |
| `LsegProvider`, `IceProvider` | Cotizaciones con derechos BMV | Ninguna | Suscripción | — | Pendiente |
| SiBolsa (Grupo BMV) | Plataforma de consulta web/app de Grupo BMV (mercados, SIC, MexDer, Valmer) | — | Suscripción para lectura humana; su pantalla no se extrae. Acceso programático = Web Services de Grupo BMV → `BmvLicensedProvider` | — | Sin contrato: copiar precios a CSV de precios con `fuente=SiBolsa` |
| `InfoselProvider` (Infosel HUB / APIs financieras) | Último hecho y mejores posturas BMV y BIVA en tiempo real, histórico e intradía | Ninguna | Contrato de APIs Infosel (infosel.com/apis) | — | **Conector listo** (Market API v3, `GET /api/v3/instruments/last`, claves `1/12576/0/<emisora><serie>` BMV y `1/12609/0/…` SIC, `Authorization: Bearer <JWT>`). Pendiente: `INFOSEL_API_KEY` y `INFOSEL_URL_BASE` del contrato. Es la vía para tiempo real BMV |
| `EdimexProvider` (Edimex / EDI Financial) | Emisoras, fondos, históricos | Ninguna | Sitio de consulta sin API abierta; acceso programático solo contratado | — | Pendiente; mientras tanto, sus exportaciones se importan como CSV de precios con `fuente=Edimex` |
| Calificaciones de Seeking Alpha (CSV) | Quant, autores y Wall Street (1–5) y notas por factor | Emisoras de EE. UU. | Exportación de la cuenta del participante | Fecha de la exportación | **Importador listo**; se muestran en el Ranking, no entran al optimizador |
| `EodhdBmvProvider` | Cierre diario BMV local | Ninguna | Plan gratuito (20/día) | EOD | Pendiente: `EODHD_API_KEY` |
| `ManualOrCsvProvider` | Precios y NAV copiados del portal | Lo que el participante capture | Datos propios | EOD | **Funciona** |
| Seeking Alpha RSS | Titulares fechados, autor, tipo (noticia / análisis / transcripción), otras emisoras mencionadas | Emisoras de EE. UU. en cartera o en la propuesta (hasta 25) | RSS público; solo titular y enlace | Verificado 29-sep: 30 notas distintas de MRNA | **Funciona**: se identifica por `guid` y se descartan notas que no mencionan la emisora |
| Notas de Seeking Alpha (CSV) | Tesis del participante con URL y fecha | — | Propias | Disponibles al importarse | **Funciona** |
| InsiderFinance (CSV) | Operaciones de insiders con fechas de operación y divulgación | EE. UU.; NO CUBRE BMV | Exportación del plan, si existe | — | Importador listo |
| SEC EDGAR (Form 4) | Fuente primaria de insiders | EE. UU. | API oficial; exige `SEC_USER_AGENT` | Hasta 2 días hábiles (regla SEC) | Pendiente: `SEC_USER_AGENT` |
| Forex Factory | Calendario semanal: consenso, previo, revisiones | Semana en curso | Feed de exportación público | Respuesta 0.62 s | **Funciona**; versiones guardadas |
| TradingView webhook | Eventos de alertas del usuario | Según su plan | Webhooks propios | `UNKNOWN` por diseño | Listo; pendiente de túnel y secreto |
| FRED | Tipo de cambio (respaldo) e índices para investigación | — | API oficial con `FRED_API_KEY` | 2–3 sesiones de rezago | CSV público bloquea el User-Agent de la terminal → **pendiente: `FRED_API_KEY`** |
| Banxico SIE | Tipo de cambio FIX | — | Token gratuito | Mismo día | Pendiente: `BANXICO_TOKEN` |
| Barchart OnDemand | Históricos | BMV/SIC no confirmadas | Contrato | — | Pendiente de contrato |

**Costos estimados:**

- Hoy: $0.
- Datos BMV: según contrato.
- EODHD: plan de pago si hacen falta más de 20 consultas al día.
- Túnel para el webhook: gratuito (Cloudflare Quick Tunnel).


## Seeking Alpha: qué exigiría una integración automática adicional

La suscripción personal (Premium o Pro) **no** da acceso a una API. Las calificaciones Quant, las notas por factor y los artículos Premium no se extraen de forma automática: se importan desde una exportación que hace el participante (CSV, tipo `calificaciones_sa`). Para automatizarlas haría falta un **acuerdo de licencia de datos con Seeking Alpha** que especifique:

- **Datos:** calificaciones Quant, de autores y de Wall Street con su fecha de cálculo; notas por factor (valuación, crecimiento, rentabilidad, momentum y revisiones); histórico fechado para validar sin sesgo de anticipación.
- **Permisos:** uso programático personal no comercial, almacenamiento local, cantidad de consultas por día y tiempo de conservación.
- **Técnico:** URL base, autenticación, formato de símbolo y un ejemplo de respuesta, para escribir la especificación como con Infosel.

Mientras no exista esa licencia, las calificaciones importadas son contexto fechado en el Ranking y no entran al optimizador.


## Cobertura de precios (revisión del 29-sep-2026)

| Fuente | Qué cubre | Tipo y retraso | Acceso | Estado |
|---|---|---|---|---|
| EODHD (`eodhd`, plan gratuito) | 41 de 44 emisoras BMV del universo con el código exacto (verificado contra `exchange-symbol-list/MX`) | Cierre diario (EOD); un año de historia | `EODHD_API_KEY`; 20 consultas/día | **Funciona.** Se corrigió `PE&OLES`, que se pedía como «PEOLES». Recupera 6 emisoras nuevas por día. Con el cupo gratuito solo ~18 se actualizan a diario. |
| Twelve Data (`twelvedata`) | 37 de 44 (lista pública `/stocks?exchange=BMV`, símbolo por símbolo en `config/proveedores/twelvedata_bmv.json`). Sin cobertura: CEMEX CPO, FEMSA UBD, KOF UBL, LASITE B-1, MEGA CPO, SMARTRC, TERRA 13 | **EOD**: su lista de mercados indica para México «EOD» y plan **Pro** | `TWELVEDATA_API_KEY` de plan Pro | Preparado; inactivo sin clave |
| Hoja oficial de fondos Actinver (`actinver_pdf`) | 22 de 23 fondos (serie B en MXN); JPMRVUS publica solo B-1 | NAV del día hábil anterior («precios de valuación al …») | PDF público de actinver.com (`robots.txt` no restringe `/documents/`); se descarga como máximo cada 3 h hasta tener la valuación | **Funciona**; guarda la huella SHA-256 y copia en `data/fuentes/actinver/` |
| Infosel Market API v3 (`infosel`) | BMV y SIC | Tiempo real o retrasado, según el contrato (se mide la latencia) | Contrato de APIs, URL de producción y token JWT | Conector listo; faltan contrato y credenciales |
| Grupo BMV INTRA | Tiempo real de Capitales, Dinero y Derivados, consolidado BMV/BIVA y SIC | Tiempo real (multicast); retrasado en algunos índices | Contrato de licencia de información para casas de bolsa, vendors e instituciones; infraestructura multicast o Web Services; tarifas 2025-2026 (marketdatasales@grupobmv.com.mx) | No es un producto para una persona. Para uso individual, un distribuidor como Infosel |

**Prioridad para una misma fecha** (`mercado.PRIORIDAD_FUENTE`), de mayor a menor: contratos BMV (INTRA, Infosel, LSEG, ICE, Edimex) → EODHD → Twelve Data → hoja de Actinver → referencias de la bolsa de origen (Tiingo, Alpaca) → captura manual → cotización en vivo del día. Entre fechas distintas siempre gana la más reciente.
