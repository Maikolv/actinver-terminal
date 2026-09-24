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
| `EodhdBmvProvider` | Cierre diario BMV local | Ninguna | Plan gratuito (20/día) | EOD | Pendiente: `EODHD_API_KEY` |
| `ManualOrCsvProvider` | Precios y NAV copiados del portal | Lo que el participante capture | Datos propios | EOD | **Funciona** |
| Seeking Alpha RSS | Titulares, autor, tipo de contenido | Emisoras de EE. UU. | RSS público; lectura humana del texto | Respuesta 0.23 s; titular con ~13 h | **Funciona** (contexto, no precios) |
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
