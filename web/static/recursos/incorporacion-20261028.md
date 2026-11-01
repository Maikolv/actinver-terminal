# Integración de los tres reels: investigación y herramientas

El acceso público /p/ inicialmente devolvió login. Después funcionó /reel/.../embed/captioned/, y la sesión abierta de Chrome permitió comprobar los posts de plugins y TradingView. Se descargaron los tres videos y se revisaron sus fotogramas y transcripciones. El intento de navegación posterior en Chrome agotó el tiempo; no se afirma que todos los posts se verificaron visualmente en el navegador. Esta versión sustituye el estado pendiente anterior.

## 1. De-dVXJofx6 — fuentes de investigación IA

faadhiljabbar agrupa personas por investigación IA, acciones IA, inversión IA, LLM, desarrollo e infraestructura. No menciona un repositorio ni ofrece una estrategia reproducible. La aportación a Actinver es una agenda editorial para el cuaderno de investigación:

| Área | Nombres observados en el video |
|---|---|
| Investigación | Andrej Karpathy, Demis Hassabis, Yann LeCun |
| Acciones IA | Justin Banks, Zephyr, Serenity |
| Inversión IA | Marc Andreessen, Cathie Wood, Chamath Palihapitiya |
| LLM | Sebastian Raschka, Simon Willison, Hamel Husain |
| Desarrollo | Harrison Chase, Boris Cherny, Alexander Wang |
| Infraestructura | SemiAnalysis, Jukan, Jim Fan |

Son los nombres mostrados por el autor, no una recomendación financiera ni una verificación de las opiniones de esas cuentas. No se siguieron cuentas automáticamente. Para incorporar una idea al cuaderno: guardar URL original y fecha, afirmación, evidencia primaria, instrumento afectado, horizonte, dato que la refutaría y estado de comprobación. Contrastar opiniones con documentos de la empresa, proveedor o paper; no trasladarlas al score de NQ como alfa.

En Quantower/TradingView esta información sirve como contexto de investigación externo; no es un feed de precios, orderflow ni una condición automática de entrada.

## 2. De9mZYXCGeB — 30 plugins de Claude

El video recomienda expresamente elegir una fila según la tarea y una herramienta de esa fila, no instalar todo. El catálogo de nombres está en plugins-observados.json. Las cifras de estrellas cambian y no se usan como evidencia de calidad.

Se reutilizan capacidades ya presentes: Matt Pocock Skills para aclarar requisitos, codebase-memory para localizar código con cobertura comprobada, skills de diseño para armonía visual y Humanizer para documentación. No se descargaron 30 homónimos ni se activaron hooks globales. Los nombres sin URL exacta no se atribuyen a un autor de GitHub por adivinación. La metodología aplicable queda en el prompt de optimización: una tarea, contexto mínimo, cambio medido, prueba y comparación.

Estas herramientas ayudan a desarrollar los tres proyectos, pero no son indicadores nativos de Quantower ni librerías importables de Pine.

## 3. De-jrR2x-g0 — pipeline de investigación TradingView

Los fotogramas identifican estos cinco proyectos. Atención: el quinto es robswc, no fabston.

- [https://github.com/rongardF/tvdatafeed](https://github.com/rongardF/tvdatafeed): `C:\Users\MIKE\Desktop\Repos\tvdatafeed`, commit `e6f6aaa7de439ac6e454d9b26d2760ded8dc4923`. clonado; entorno aislado e import comprobado.
- [https://github.com/bukosabino/ta](https://github.com/bukosabino/ta): `C:\Users\MIKE\Desktop\Repos\ta`, commit `a890410710a6e483c9ba08da7f3dd5089e4b9dff`. clonado; entorno aislado e import comprobado.
- [https://github.com/joshyattridge/smart-money-concepts](https://github.com/joshyattridge/smart-money-concepts): `C:\Users\MIKE\Desktop\Repos\smart-money-concepts`, commit `1b62fd6c41e1f508e7ed76831a039fa4c82d42f6`. clonado; entorno aislado e import comprobado.
- [https://github.com/PyneSys/pynecore](https://github.com/PyneSys/pynecore): `C:\Users\MIKE\Desktop\Repos\pynecore`, commit `eb7cff8696183bcf20ad2f008e0975b295449825`. clonado; entorno aislado e import comprobado.
- [https://github.com/robswc/tradingview-webhooks-bot](https://github.com/robswc/tradingview-webhooks-bot): `C:\Users\MIKE\Desktop\Repos\tradingview-webhooks-bot-robswc`, commit `a164fc88edafbe2e877c6193dd17afb4f76f1236`. clonado y README revisado; servidor y acciones no activados.

## Implementación realizada

Actinver contiene tools/reel_research.py y cinco pruebas en tools/test_reel_research.py. El módulo acepta CSV OHLCV o el JSON histórico de Futuros Lab; valida fechas, duplicados, precios, volumen y coherencia OHLC. Calcula SMA20, EMA20, MACD12/26/9, ATR14 y FVG confirmados usando TA y Smart Money Concepts. No rellena calentamiento ni utiliza MitigatedIndex, que contiene información futura. Desplaza el FVG una barra y descarta tripletes con intervalos irregulares; no aplica todavía un calendario del exchange. La prueba por prefijos confirma que agregar barras no altera resultados anteriores.

Se procesaron 6,901 barras guardadas de NQZ26: 12–19 de octubre de 2026, etiquetadas como histórico retrasado. Resultado: 1,506 FVG confirmados según esta definición. Son observaciones técnicas, no trades, recomendaciones ni evidencia de rentabilidad. Ver investigacion-offline/features.csv y summary.json. No se hicieron backtests de rentabilidad ni forward en esta entrega porque el reel no define reglas completas de entrada/salida.

Entorno: C:/Users/MIKE/Desktop/Repos/futuros-lab/.venv-reels-20261028. Se instalaron desde clones locales TA, SMC, TvDatafeed y PyneCore; sus importaciones pasaron. PyneCore se construyó en modo Python puro. El quinto proyecto es un framework web: solo clonado, sin levantar servidor, acciones ni rutas de ejecución.

## Uso local

Desde C:/Users/MIKE/Desktop/Repos/actinver-terminal, en PowerShell:

```powershell
& 'C:/Users/MIKE/Desktop/Repos/futuros-lab/.venv-reels-20261028/Scripts/python.exe' tools/reel_research.py --input 'C:/Users/MIKE/Desktop/Repos/futuros-lab/entregables/amt-lucid/diagnostico-real/_NQZ26_XCME-barras.json' --output 'C:/Users/MIKE/Desktop/Repos/futuros-lab/entregables/reels-20261028/investigacion-offline'
& 'C:/Users/MIKE/Desktop/Repos/futuros-lab/.venv-reels-20261028/Scripts/python.exe' -m unittest discover -s tools -p test_reel_research.py -v
```

## Compatibilidad y límites

| Recurso | Actinver/Futuros Lab | Quantower | TradingView |
|---|---|---|---|
| TvDatafeed | Import instalado; proveedor opcional no conectado. README limita descargas a 5,000 barras y acceso sin login a símbolos disponibles. No es API oficial ni garantiza CME actual. | No reemplaza un proveedor de plataforma. | Fuente histórica externa; no modifica derechos de datos del plan. |
| TA | Indicadores calculados offline. | Port C# requeriría comparar semillas y valores; no se afirma instalado como indicador. | Equivalentes deben contrastarse barra a barra con ta.* de Pine. |
| SMC | FVG confirmado offline; OB, swings y mitigación no se usan como señales causales sin auditar sus confirmaciones. | Se comparten CSV/resultados y protocolo, sin DLL nueva ni arranque. | No se importa Python en Pine. Port separado requeriría prueba de causalidad y ausencia de repintado. |
| PyneCore | Runtime instalado e importado; no se ha convertido el código Pine del usuario. | Herramienta externa para investigación, sin conector de órdenes. | Runtime libre; conversión de .pine mediante PyneComp es un servicio separado con API/planes. No se contrató. |
| robswc Webhooks Bot | Código disponible como referencia; acciones desactivadas. | Ningún puente a cuentas ni estrategias. | No se creó webhook, alerta ni exposición de servidor. |

Los proyectos Quantower y TradingView incluyen este informe, inventario, prompt, scripts offline y resultados. Es una incorporación de herramientas de investigación y documentación, no ejecución nativa ni bot operativo. El mandato vigente prohíbe cualquier trade, incluso demo, hasta autorización directa posterior del usuario. Todos los candados se verificaron deshabilitados. No se enviaron mensajes de Telegram ni comentarios/DM a los autores.
