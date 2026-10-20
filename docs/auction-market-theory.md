# Auction Market Theory · implementación local

Revisión: 19 de octubre de 2026. AMT organiza hipótesis de aceptación, rechazo y búsqueda de valor; no demuestra por sí misma una ventaja estadística.

## Qué funciona

| Proyecto | Entrega | Alcance comprobable |
|---|---|---|
| Actinver-terminal | Order Flow → Auction Market Theory | Tabla por sesión, rejilla configurable, POC TPO observado, VAH/VAL previos, IB, cobertura y contexto |
| API existente | `/api/flujo/perfiles?simbolo=…&paso_precio=0.25` | Campo `subasta`; sólo lectura; errores 422 para rejilla inválida |
| futuros-lab | `futuros_lab/amt.py`, `amt_replay.py` | Mismo cálculo Python; CSV o ejemplo sintético reproducible; no órdenes |
| Quantower | `AmtObservador` y `PerfilSubasta` | Perfil TPO de ticks recibidos, métricas POC/VAH/VAL; compilación sin errores/advertencias contra DLL instalada; DLL propia instalada; no iniciado ni validado con feed en la plataforma |
| TradingView | `tradingview/actinver_amt.pine` | Indicador Pine v6 para niveles previos introducidos manualmente, IB y alertas al cierre; compilado, añadido al gráfico y guardado en TradingView como «Actinver AMT - Contexto RTH v1»; pendiente validar señales con niveles reales de futuros |

Se conservan los cálculos de volumen y delta existentes. No se reemplazan por TPO ni se asigna volumen de una vela a precios inventados. El observador Quantower no es un bot de ejecución. La terminal tampoco se convierte en canal de órdenes.

## Convención reproducible

- Sesión de referencia: RTH 09:30–16:00, `America/New_York`; cripto conserva 00:00–24:00 de la zona ya configurada por la terminal. No es un perfil Globex. Las sesiones nocturnas necesitan otro adaptador.
- Python: OHLC de barras cerradas de 1, 5 o 15 minutos; una marca por cubeta fija y bloque de 30 minutos. No interpolar rangos. Es una **cota inferior de TPO**, no Market Profile completo de ticks.
- Quantower: una marca por precio efectivamente recibido y bloque de 30 minutos. El perfil empieza al arrancar; siempre se identifica como parcial. No reconstruye ticks ausentes.
- Rejilla anclada en cero; paso configurable en terminal. 0.25 es la rejilla de investigación inicial para MES/ES/MNQ/NQ; para otros instrumentos hay que elegir y contrastar el paso. No equivale a verificar el tick contractual.
- POC: cubeta con más TPO; en empate, la inferior. Su valor mostrado es el centro de la cubeta, por lo que puede no ser un precio negociable. VA: expansión contigua desde POC hasta cubrir al menos 70%; incluye ambos vecinos en empate y atraviesa huecos con peso cero. No coincide necesariamente con algoritmos de otros proveedores.
- IB: máximo/mínimo de la primera hora, publicado sólo si se observaron todas sus barras cerradas. Una referencia previa requiere todas las barras esperadas y cierre de sesión pasado. Una sesión parcial intermedia invalida el arrastre de referencia.
- Aceptación: dos cierres consecutivos y sin hueco temporal fuera del valor previo. Rechazo: última barra explora fuera y cierra dentro; si barre ambos extremos se etiqueta aparte. Rotación: cierre dentro sin barrido. Fuera sin confirmación: exploración.
- Disponibilidad: descartar barras abiertas, futuras o publicadas después del corte. El perfil de hoy es descriptivo; la clasificación usa exclusivamente el valor previo congelado. No usar el perfil final de hoy para justificar una entrada anterior.
- No están implementados un clasificador completo de tipos de día, single prints auténticos, poor highs/lows ni calendario de festivos/cierres anticipados. No se infieren de cuatro precios por vela.

## Usarlo

1. En terminal, abrir **Order Flow**, elegir instrumento y rejilla. Importar barras con licencia desde **Velas** si faltan. La tabla no inventa niveles cuando no hay datos.
2. Revisar cobertura y fecha de referencia antes de interpretar un estado. El origen de los datos se conserva en el panel. Un estado descriptivo no es permiso de entrada.
3. Quantower: abrir **TPO Chart**, perfil diario, bloques de 30 minutos, paso fijo y misma sesión. Mostrar valor e IB de 60 minutos; mantener el perfil de volumen diferenciado. Para el observador, se instaló la DLL propia independiente `ActinverAMT.Quantower.dll` bajo `C:\Quantower\Settings\Scripts\Strategies\ActinverAMT`. No se reemplazaron DLL del proveedor ni el adaptador anterior. La compilación y la copia instalada tienen SHA-256 `65A0690CF801F3839550B3FF30623F5DAF35DCA43B619D56425178FBA0A71178`. Seleccionar `Actinver · AMT observador` en Strategies manager con contrato de vencimiento concreto; no requiere cuenta ni coloca órdenes. Comprobar el perfil contra ticks/replay autorizados. Se instaló el archivo, pero no se arrancó ni se conectó a ningún feed en esta entrega.
4. TradingView: copiar el Pine al editor y compilar. Utilizar velas temporales normales de 1/5/15 minutos, sesión RTH y datos del contrato correcto. Introducir VAH/VAL/POC de la sesión anterior completa; indicar su fecha de cierre y la ventana de validez de la sesión actual. Ceros, fechas o límites inválidos desactivan el contexto. Renovar niveles cada sesión. No usar datos del contrato continuo para enviar órdenes.
5. Crear alertas **al cierre** si se desea. El JSON tiene el esquema del receptor informativo existente `/webhook/tradingview`, pero éste sólo acepta instrumentos de su catálogo: **los futuros CME no están habilitados en ese receptor**. Para futuros, usar inicialmente notificaciones de TradingView; un receptor separado de futuros requiere implementación y pruebas. No desactivar la validación del catálogo para forzar compatibilidad. Una alerta no genera una orden ni garantiza entrega. No exponer credenciales en Pine, repositorios, capturas o URLs.

## Reproducir sin cuentas

En `C:\Users\MIKE\Desktop\Repos\futuros-lab`:

```powershell
# El .venv de futuros-lab apunta a un intérprete eliminado; se usa el entorno local funcional de la terminal.
& ..\actinver-terminal\.venv\Scripts\python.exe -m futuros_lab.amt_replay --demo --hasta 2026-10-16T21:00:00Z
& ..\actinver-terminal\.venv\Scripts\python.exe -m futuros_lab.amt_replay --csv datos.csv --paso .25 --hasta 2026-10-19T16:00:00Z --salida contexto.json
& .\_tools\dotnet\dotnet.exe build .\quantower\ActinverAMT.Quantower\ActinverAMT.Quantower.csproj --no-restore
& .\_tools\dotnet\dotnet.exe run --project .\quantower\FuturosLab.Pruebas\FuturosLab.Pruebas.csproj --no-restore
```

CSV mínimo: `inicio,intervalo,apertura,maximo,minimo,cierre`. Fechas ISO con zona, intervalo `1Min`, `5Min` o `15Min`; `disponible_desde` opcional. No mezclar contratos, ajustes de rollover o proveedores. La procedencia de un CSV externo sigue requiriendo verificación humana.

## Lucid: reglas verificadas y puntos que faltan

Lucid permite automatización bajo sus reglas; eso no valida este sistema. Quantower figura como plataforma Rithmic, mientras TradingView aparece bajo CQG. Confirmar la conexión contratada. En Flex 50K se publican MLL de 2,000 USD y hasta 4 minis/40 micros; funded está sujeto al scaling EOD. No convertir el nominal 50K en presupuesto de pérdida.

La página de personalización contempla DLL on/off y consistencia de evaluación 40% estándar o 50% add-on. La configuración local deja desconocida la variante del usuario. No se permite asumir un límite más favorable. El horario público escribe EST; reconfirmar semántica y calendario de cierres especiales antes de automatizar una cuenta. HFT está prohibido y microscalping tiene restricciones; no retrasar salidas de protección para maquillar duraciones.

El prompt entregado establece una implementación verificable en PAPER y una lista de bloqueos reales. No se activa ninguna cuenta Lucid ni se prometen ganancias. Faltan datos CME autorizados, variante de cuenta, conexión, calendario, pruebas de ejecución y evidencia fuera de muestra.

## Recursos primarios consultados

- [Quantower TPO](https://help.quantower.com/quantower/analytics-panels/tpo-chart): sesiones, bloques, VA e IB.
- [Quantower operaciones](https://help.quantower.com/quantower/quantower-algo/trading-operations): solicitudes, resultados y órdenes protectoras.
- [Quantower tipos de órdenes](https://help.quantower.com/quantower/trading-panels/order-entry/order-types): soporte dependiente del conector; confirmar brackets/OCO server-side reales.
- [Quantower Backtest & Optimize](https://help.quantower.com/quantower/quantower-algo/backtest-and-optimize): replay, comisiones y validación.
- [TradingView TPO](https://www.tradingview.com/support/solutions/43000713306-time-price-opportunity-tpo-indicator/): referencia visual y alertas de perfiles completados.
- [Pine alertas](https://www.tradingview.com/pine-script-docs/concepts/alerts/): condiciones y configuración del usuario.
- [Pine datos/footprint](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/): existe `request.footprint`, restringido a planes compatibles; categoriza volumen mediante acción intrabar, no asumir agresor de bolsa. No se requiere para este Pine básico.
- [Lucid automatización](https://support.lucidtrading.com/en/articles/11404728-other-trading-activities), [plataformas](https://support.lucidtrading.com/en/articles/11404614-lucid-trading-supported-platforms), [personalización](https://support.lucidtrading.com/en/articles/16226050-lucidflex-customization).
- [Lucid drawdown](https://support.lucidtrading.com/en/articles/12945815-lucidflex-drawdown), [scaling](https://support.lucidtrading.com/en/articles/12945808-lucidflex-scaling-plan), [horarios](https://support.lucidtrading.com/en/articles/11404729-allowed-trading-times).
- [Lucid HFT](https://support.lucidtrading.com/en/articles/11404736-prohibited-high-frequency-trading), [microscalping](https://support.lucidtrading.com/en/articles/11404742-prohibited-microscalping).
- [CME ES](https://www.cmegroup.com/markets/equities/sp/e-mini-sandp500.contractSpecs.html), [NQ](https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.contractSpecs.html), [micro E-mini](https://www.cmegroup.com/markets/equities/micro-emini-equity.html): contrastar metadatos y contratos en fuente oficial.

Inventario local con procedencias: `config/amt-recursos-locales.json`. Una estrella de GitHub no certifica utilidad, licencia ni funcionamiento. Los repositorios se reutilizan por capacidad concreta, sin instalar todos los motores a la vez.

## Evidencia de esta entrega

- 72 pruebas Python de terminal (AMT, perfiles, flujo e intradía): pasan.
- 37 pruebas del laboratorio de futuros: pasan usando el entorno funcional de la terminal.
- 26 vectores C# de contratos/riesgo/guardas/AMT: coinciden.
- 3 pruebas de navegación: pasan. Interfaz comprobada con un fixture sintético aislado; sin desbordamiento horizontal a 390 px.
- Observador independiente Quantower: compilado con 0 errores y 0 advertencias e instalado, sin ejecución en la plataforma.
- Pine: compilado, cargado y guardado en la cuenta existente de TradingView; sin alertas activadas. Prueba negativa observada con niveles cero/timeframe diario: «NO EVALUAR». No se afirma validación de señales ni de ejecución sobre datos de futuros.

El ejemplo de interfaz emplea un instrumento del catálogo y precios inventados explícitamente etiquetados; no añade un feed CME a la terminal.
