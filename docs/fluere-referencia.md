# Referencia funcional: Fluere

Se examinó la página pública de [Fluere](https://capitalfluere.com/) con `rea` mediante una sesión aislada de Chrome DevTools Protocol. La captura registró el árbol visible y de accesibilidad; no incluyó módulos de pago ni el funcionamiento interno del producto. Las funciones descritas en la página son afirmaciones públicas del proveedor, no funciones verificadas dentro de su terminal.

## Incorporado a actinver-terminal

- Una barra de comandos abre secciones con códigos cortos y localiza un símbolo del universo local por coincidencia exacta. `Ctrl+K` enfoca la barra. Si la clave no es única o no tiene gráfica, se informa sin navegar a otro instrumento.
- El panel **Modelos** calcula un precio teórico de opción europea con Black-Scholes-Merton, dividendos continuos y griegas. Una prima introducida manualmente permite estimar volatilidad implícita por bisección. La respuesta indica unidades y límites.
- En **Mercado** se añadió un mapa de calor de variación entre los dos últimos cierres locales por instrumento, con fuente, fecha y acceso a cierres históricos. Muestra media móvil de 20 sesiones y RSI de 14 sesiones calculados con historia anterior. Las velas se abren en el widget oficial gratuito de TradingView ya integrado, con sus propios indicadores y condiciones de retraso.

Estas funciones se implementaron con código propio y datos existentes de la terminal. No se copiaron recursos ni código de Fluere.

## Relevancia futura

El sitio presenta investigación por símbolo, gráficos, filtrado, riesgo, pruebas históricas y herramientas de opciones como una superficie integrada. Para un futuro proyecto de Order Flow y Option Flow, la siguiente capacidad útil sería **normalizar datos trazables de proveedores autorizados**: símbolo, contrato, mercado, instante, zona horaria, bid/ask, tamaño, volumen, interés abierto, origen y retraso. Después se podrían añadir pruebas históricas sin sesgo temporal y controles de riesgo antes de automatizar órdenes. La página pública no demuestra calidad, latencia ni licencia de esos datos; ninguna señal operativa se derivó de ella.

## Alcance y límites

El modelo actual usa solo hipótesis manuales. No consulta cadenas de opciones, no observa flujo de órdenes ni ejecuta operaciones. Black-Scholes-Merton europeo puede no representar el ejercicio anticipado ni la liquidez de contratos reales. Los símbolos de la barra solo se buscan en el universo ya registrado.
La base local conserva cierres y volumen, pero no OHLC completo verificado. Por eso el mapa local no fabrica velas ni representa operaciones intradía. Los datos de las velas proceden del widget externo de TradingView y pueden diferir de las referencias del simulador.
Referencia de integración del widget gratuito: https://www.tradingview.com/widget-docs/widgets/charts/advanced-chart/ . La disponibilidad y el retraso dependen del mercado mostrado por TradingView.

Fuente de observación: `work/rea-fluere-observation.json` del expediente de Codex del 12 de octubre de 2026. La captura indica `policy_filtered` porque se limitaron los orígenes permitidos a `capitalfluere.com`.
