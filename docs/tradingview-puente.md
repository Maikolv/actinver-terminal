# Puente TradingView (vía oficial: alertas por webhook)

**Decisión:** TradingView entra a la terminal solo por su mecanismo oficial, las alertas con webhook que
`terminal/webhook_tv.py` ya recibe (fila R5 de `docs/03-plan-implementacion.md`). El repo hermano
`tradingviewmcp` (`C:\Users\MIKE\Desktop\Repos\tradingviewmcp`) se usa **solo como herramienta de desarrollo** para
escribir, validar e instalar el indicador Pine y las alertas. **No** se usa para leer precios, OHLCV ni valores de
indicadores de la interfaz (`quote_get`, `data_get_*`): eso automatizaría la UI de TradingView, no es una fuente
oficial y no alimenta la valuación.

## Piezas

| Pieza | Ruta |
|---|---|
| Indicador Pine con dos `alertcondition` (cruce al alza / a la baja de un nivel) | `tradingview/actinver_cruce_nivel.pine` |
| Receptor del webhook (valida secreto, símbolo, moneda, hora, duplicados) | `terminal/webhook_tv.py` |
| Prueba de que el mensaje del Pine lo acepta el receptor | `tests/test_tradingview_pine.py` |

## Flujo

1. `uv run terminal webhook-secreto` genera `TRADINGVIEW_WEBHOOK_SECRETO` en `.env` (ver `docs/proveedores.md`).
2. Validar el Pine sin abrir TradingView (compilación oficial del servidor):
   ```bash
   cd C:\Users\MIKE\Desktop\Repos\tradingviewmcp
   node src/cli/index.js pine check --file C:\Users\MIKE\Desktop\Repos\actinver-terminal\tradingview\actinver_cruce_nivel.pine
   ```
3. Instalarlo en el gráfico (TradingView abierto con `node src/cli/index.js launch`): con las herramientas MCP
   `pine_set_source` → `pine_smart_compile` → `pine_save`, o pegando el archivo en el editor Pine.
4. Crear la alerta en TradingView sobre el indicador y, en el mensaje, reemplazar `<SECRETO>` por el valor de
   `TRADINGVIEW_WEBHOOK_SECRETO`. El secreto **nunca** se guarda en el `.pine`, ni en el repo ni en los registros.
5. URL de la alerta: un túnel HTTPS propio hacia `http://127.0.0.1:8765/webhook/tradingview`
   (`TRADINGVIEW_WEBHOOK_HOSTS`, ver `docs/proveedores.md`). Exponer la terminal es decisión del usuario.

## Límites

- Un evento de alerta es un aviso («el precio cruzó X»), no una cotización en tiempo real: se registra con latencia
  `UNKNOWN` (`timenow` es la hora de la alerta, no la del dato de mercado).
- Con `BMV_DLY` TradingView entrega datos retrasados; la alerta hereda ese retraso.
- Las alertas de TradingView requieren un plan que permita webhooks; eso lo contrata y verifica el usuario.
- El MCP de TradingView controla la cuenta de TradingView del usuario desde su PC. Úsalo solo con su autorización
  y sin exponerlo a la red.
