# Acciones requeridas del usuario

Actualizado: 12-oct-2026. Cada acción indica si **puede automatizarse** (la terminal ya lo hace o lo hará), si
**requiere tu intervención** (sin costo) o si **requiere contrato o proveedor de pago**.

## 1. Prioridad alta

| Acción | Tipo | Detalle |
|---|---|---|
| Capturas del portal del Reto (resumen + tabla de acciones), idealmente entre 2:00 y 2:30 p.m. | Requiere tu intervención | El reglamento prohíbe automatizar el portal. Al registrar una captura, la terminal descarga los cierres del día |
| Revisar y aprobar la etapa 2 (adaptadores de repositorios) | Requiere tu intervención | `docs/integracion-repositorios.md` |
| Decidir si quieres profundidad de libro o opciones en tiempo real de EE. UU. | Requiere contrato o proveedor de pago | Ver la sección 3 |

## 2. Credenciales y cuentas

Solo nombres de variables en `.env`; los valores nunca se comparten ni se suben.

| Variable | Servicio | Costo | Estado al 12-oct | Qué activa |
|---|---|---|---|---|
| `ALPACA_API_KEY_ID`, `ALPACA_API_SECRET_KEY` | Alpaca Market Data | Gratis | Configuradas y verificadas | Velas SIP, cinta SIP, bid/ask IEX, opciones (feed indicativo), flujo en vivo IEX |
| `TIINGO_API_KEY` | Tiingo | Gratis | Configurada | Cierres de EE. UU. |
| `EODHD_API_KEY` | EODHD | Gratis (20/día) | Configurada | Cierres de la BMV |
| `BANXICO_TOKEN` | Banxico SIE | Gratis | Configurada | FIX USD/MXN |
| `FRED_API_KEY` | FRED | Gratis | Configurada y verificada | Tasas y macro; tasa para la IV calculada |
| `EIA_API_KEY` | EIA | Gratis | Configurada y verificada | WTI, Brent e inventarios |
| `ALPHAVANTAGE_API_KEY` | Alpha Vantage | Gratis (25/día) | Configurada y verificada | Estados financieros anuales |
| `COINGECKO_DEMO_API_KEY` | CoinGecko Demo | Gratis | **Falta** (opcional) | Referencia BTC/ETH |
| `SEC_USER_AGENT` | SEC EDGAR | Gratis | Configurada | Form 4 y 13F |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Telegram | Gratis | Configuradas | Plan y alertas |
| `FINVIZ_AUTH_TOKEN` | Finviz Elite | **De pago** | No configurada | Precios EE. UU. en lote |
| — (sin clave) | Bitso, vía ccxt | Gratis, API pública | Activo | Libro, cinta y velas de cripto (fuera del Reto) |

## 3. Licencias o suscripciones para Order Flow y Option Flow

| Dato | ¿Gratis? | Opción | Tipo |
|---|---|---|---|
| Libro con profundidad de acciones de EE. UU. | No | Proveedor de datos de nivel 2 (p. ej. Databento o Polygon/Massive) | Requiere contrato o proveedor de pago |
| Cinta consolidada en tiempo real con lado del agresor | No (el lado casi nunca se publica) | Proveedor de nivel 2 o 3 | Requiere contrato o proveedor de pago |
| Opciones OPRA en tiempo real e interés abierto | No | Suscripción de datos de opciones (Alpaca de pago u otro) | Requiere contrato o proveedor de pago |
| Libro, operaciones y opciones de la BMV o MexDer | No | Contrato con Grupo BMV, MexDer o un distribuidor | Requiere contrato o proveedor de pago |
| Libro y cinta de cripto | **Sí** | Bitso (activo) u otro exchange de ccxt | Puede automatizarse (ya activo) |
| Velas OHLCV de EE. UU. con ≥ 15 min de retraso | **Sí** | Alpaca (activo) | Puede automatizarse (ya activo) |
| Opciones de EE. UU. diferidas | **Sí** | Alpaca, feed indicativo (activo) | Puede automatizarse (ya activo) |

## 4. Archivos CSV que puedes importar

Las plantillas están en cada panel o en `/api/flujo/plantilla/{tipo}`. Solo datos que tengas derecho a usar:

| CSV | Para qué | De dónde podrías exportarlo |
|---|---|---|
| `velas` | Velas de la BMV o de cualquier mercado sin proveedor | Tu bróker o una plataforma con licencia que permita exportar |
| `operaciones` | Cinta de un instrumento | Tu proveedor de datos con licencia |
| `libro` | Instantáneas del libro por nivel | Tu proveedor de datos con licencia |
| `opciones` | Cadenas de MexDer u otras | Tu bróker o proveedor |
| Investigación (`Más → Investigación`) | Notas y valores de ROIC.ai, Quartr, SpotGamma, etc. | Sus exportaciones, adaptadas a la plantilla |
| PDF de la pestaña Acciones del simulador | Precios BMV del día | `uv run terminal precios-portal <pdf>` |

## 5. Pasos para iniciar cada módulo localmente

```bash
uv sync
uv run terminal iniciar
uv run pytest -q
uv run terminal robustez
uv run python scripts/historia_externa.py verificar
```

- `uv sync` instala el entorno, con `ccxt` incluido en el grupo `cripto`.
- `uv run terminal iniciar` levanta la terminal en http://127.0.0.1:8765; también arranca con `launcher\ActinverTerminal.exe`.
- `uv run pytest -q` corre todas las pruebas.
- `uv run terminal robustez` corre el protocolo de robustez (15–20 min).
- `scripts/historia_externa.py verificar` revisa la historia externa (Excel).

En la interfaz: **Más → Velas / Order Flow / Option Flow / Riesgo / Seguimiento / Backtesting / Mercado / Investigación / Modelos**.

Para apagar un adaptador, edita `config/local.toml`:
- `[flujo.alpaca] activo = false`
- `[flujo.cripto] activo = false`
- `[finviz] activo = false`

## 6. Decisiones antes de activar cada integración

| Integración | Decisión |
|---|---|
| Cripto (ccxt) | **Tomada (12-oct)**: activo con Bitso y BTC, ETH, SOL y XRP en MXN. Puedes cambiar de exchange o pares en `[flujo.cripto]` |
| Finviz Elite | Contratarlo o no (USD 39.50/mes) |
| Profundidad, cinta u opciones en tiempo real | Elegir proveedor y aceptar su costo y licencia |
| Etapa 2 | **Aprobada e implementada (12-oct)**: exportación a `hftbacktest`, importación de velas de OpenBB y TradingView, Heston propio. Para usar `hftbacktest` u `OpenBB`, instálalos tú, fuera de la terminal |
| `qlib`, `FinRL`, `backtrader` | Siguen como herramientas externas: si las corres, importa sus resultados como investigación manual |

## 7. Datos sin licencia confirmada o no disponibles gratuitamente

- La cadena SPX de `Heston-Calibration` (`spx_chain_raw.csv`): sin licencia, no se usa.
- Cualquier dato extraído de páginas web (Yahoo, Investing, TradingView): sus términos lo prohíben y no se extrae.
- Interés abierto de opciones de EE. UU. (no viene en el feed gratuito).
- Lado del agresor en acciones de EE. UU. (no viene en SIP ni en IEX).
- Todo dato en tiempo real de la BMV y de MexDer.
