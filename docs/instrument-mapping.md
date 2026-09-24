# Correspondencia de instrumentos: Actinver, BMV, SIC y mercado extranjero

La tabla completa por instrumento está en [instrument-matrix.md](instrument-matrix.md). Se regenera con `uv run terminal cobertura`; la tabla de datos es `correspondencia_simbolos`.

## Reglas

| Objeto | Identificador | MIC | Moneda | Fuente de precio válida |
|---|---|---|---|---|
| Acción local | `BMV:AMX` (serie `AMX B`) | XMEX | MXN | BMV licenciada, EODHD (EOD) o captura del portal |
| Listado SIC | `SIC:AAPL` (serie `AAPL *`) | XMEX | MXN | **Solo** la serie SIC de la BMV |
| Acción de origen | `NASDAQ:AAPL` | XNAS | USD | Proveedor de la bolsa de origen: referencia, **no** precio SIC |
| ADR de una emisora mexicana | Ticker en EE. UU. (p. ej. un ADR de AMX) | XNYS | USD | No sustituye a `BMV:AMX` |
| Fondo Actinver | `FONDO:ACTIGOB` | — | MXN | NAV importado |
| CFD o criptoactivo | `AAPL CFD`, `BTC/USDT` | — | — | **Rechazado** (`clasificacion.py`) |

**No hay sustituciones automáticas:**

- `normalizar_simbolo` separa los mercados.
- Un disparador de SQLite rechaza una cotización SIC o BMV que no venga en MXN.
- Sin precio confiable se muestra «SIN PRECIO CONFIABLE» y se congela esa parte de la valuación, con advertencia.
- No se usa como sustituto un ADR, un CFD, el precio de EE. UU. convertido con tipo de cambio ni el último cierre obsoleto.

**ISIN:** no está disponible en las fuentes actuales. Se llenará con el catálogo del simulador o con un proveedor licenciado.

**Catálogo del simulador:** pendiente de importar (semana del 28 sep al 2 oct), con el tipo `universo`. Mientras tanto, todos los instrumentos aparecen como «pendiente: catálogo del simulador no importado».
