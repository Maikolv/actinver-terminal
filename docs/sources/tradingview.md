# TradingView — https://es.tradingview.com/

- **Finalidad:**
  - Gráficos para revisión humana.
  - Símbolos verificables: `BMV:WALMEX`, y `BMV:AAPL` para el listado SIC en la BMV.
  - Alertas que configura el propio usuario.
- **Modalidad autorizada en la terminal:**
  1. **Widget oficial embebible** en `/grafica/<id>`, con CSP aislada. No se extraen datos del widget.
  2. **Webhook de alertas** (`POST /webhook/tradingview`, `terminal/webhook_tv.py`). Cada evento se autentica con un secreto en el cuerpo y se validan el esquema, el símbolo, la moneda, la hora (≤ 300 s y no futura), los duplicados y los valores atípicos. Se registra la hora de recepción.
- **Qué no es:**
  - El webhook avisa de que ocurrió una alerta. No es una API continua de cotizaciones.
  - Una suscripción visual en tiempo real no autoriza la extracción por scripts.
  - La terminal no usa endpoints internos, cookies ni sesión. `tradingviewmcp` se limita a la convención de símbolos y a la confirmación visual manual.
- **Cobertura real:** depende del plan del usuario en TradingView y de los derechos de la BMV en ese plan. No verificada para este usuario.
- **Latencia:**
  - El precio que llega en el evento se registra como `UNKNOWN`: TradingView no declara en el mensaje el retraso de la BMV, y `{{timenow}}` es la hora de la alerta, no la del evento de mercado.
  - La latencia de entrega del webhook se mide como `hora_recepcion − hora_evento` en `cotizaciones_registro`. Todavía no hay muestras, porque el túnel no está configurado.
- **Condiciones:** términos de uso de TradingView. Cualquier uso automatizado que no sea el widget o los webhooks del propio usuario requiere autorización del proveedor.
- **Sello temporal de esta ficha:** 2026-09-23.
- **Limitaciones:** exponer el webhook requiere un túnel HTTPS público (decisión del usuario) y `TRADINGVIEW_WEBHOOK_HOSTS`.
- **Pruebas:** `tests/test_monitor.py::test_webhook_*`.
