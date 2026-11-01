# Propuesta NO aplicada: prioridad de proveedores SIC

Medición de solo lectura, base local original, 31-oct-2026. No se leyó .env, no se consultaron APIs, no se descargaron precios ni se inició el motor. CSV y JSON verificables en `procesos-20261031-evidencia/`.

## Cobertura observada, distinta de promesa de cobertura

143 SIC activos: los 143 satisfacen el predicado actual Alpaca.soporta (USD y listado_referencia no vacío) y los 143 tienen barras Alpaca guardadas. No se considera que soporte declarado garantice cotización actual.

Última fecha Alpaca: 97 instrumentos al 30-oct, 45 al 29-oct y uno al 14-oct. Tiingo: 45 al 30-oct, siete al 29-oct y 91 al 28-oct. Sin cierre del 30-oct en ninguna de ambas fuentes: SIC:FSLR. No se inventa ese cierre.

En la corrida registrada del 30-oct 20:09:42 UTC, Tiingo guardó 26 registros y registró 98 omitidos por límite; Alpaca guardó 98, sin omisiones por límite. El fallback por proveedor ya agotado existía; el cambio de esta entrega cubre el caso diferente: respuesta exitosa con cero barras en una posición después del cierre.

## Límites configurados y costo estimado

Tiingo: 45 consultas/hora y 900/día. Alpaca: 5000/día, feed_historico SIP. Son límites de config/ actuales, no suscripciones nuevas. Datos oficiales de Basic describen 200 consultas/min; el limitador actual del adaptador solo lleva ventanas de hora/día, **no minuto**. No suponer que 5000/día permite una ráfaga sin límite.

Alpaca pide barras raw y ajustadas cuando hay datos: al menos dos solicitudes por instrumento. 143 actualizaciones con una página por ajuste implican 286 solicitudes (más paginación y reintentos); no es una medición de tráfico ni un costo fijo garantizado. En seis rondas diarias serían 1716 solicitudes antes de otras cargas, por debajo de 5000 solo si ese resto también cabe. Revisar el contador real y reservar margen para cartera/otras consultas; no tratar el saldo registrado como cuota siempre disponible.

## Reasignación propuesta

1. Mantener cartera primero y el respaldo acotado implementado. No descargar historia completa para reparar un cierre.
2. Para SIC, priorizar Alpaca después de comparar continuidad, ajustes/splits y etiqueta de feed con la historia existente, sin presentar IEX como consolidado.
3. Exigir limitación por minuto por solicitudes reales, incluyendo paginación y reintentos, antes de mover automáticamente todo el universo. Propuesta conservadora: máximo 90 solicitudes/min y tope diario configurado, con margen para otras rutas. No está implementada ni activada.
4. La prioridad actual ORDEN_PRECIOS está en código y no tiene asignación por instrumento en config/. Desactivar Tiingo en su sección es una sola línea válida, pero cambia TODOS sus instrumentos elegibles (también ETF), no solo SIC. Por eso la alternativa está enteramente comentada en `config/propuesta-proveedores-20261031.toml` y no se carga. Para reasignación exclusivamente SIC se necesitaría una opción explícita y su prueba; no se inventó una clave de configuración que no existe.

No se aplicó ninguna reasignación, se mantuvieron cuotas y fuentes actuales. No se hizo solicitud de credenciales ni prueba de cuenta. La validez de cierres faltantes, SIP disponible para la cuenta y cuota externa actual siguen sin verificarse con red.
