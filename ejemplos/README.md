# Archivos de ejemplo

Todos son **ficticios** y sirven para probar la importación («Mi cartera → Importar»); no son cotizaciones reales.

| Archivo | Tipo en «Importar» | Uso |
|---|---|---|
| `operaciones_confirmadas.csv` | transacciones | Operaciones ya ejecutadas en el simulador (comisión 0.10 % + IVA 16 % sobre la comisión) |
| `posiciones_iniciales.csv` | posiciones | Arranque con posiciones existentes |
| `precios_capturados.csv` | precios | Precios o valor liquidativo copiados a mano (proveedor «manual_csv», estado EOD) |
| `catalogo_simulador.csv` | universo | Lista de instrumentos del simulador (restringe el universo y la cobertura) |
| `alerta_tradingview.json` | — | Mensaje para una alerta de TradingView con webhook (ver docs/proveedores.md) |
