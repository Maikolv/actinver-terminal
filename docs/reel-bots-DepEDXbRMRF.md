# Laboratorio del reel DepEDXbRMRF

Ejemplo offline de investigación, no bot conectado ni estrategia rentable demostrada. Los cinco repositorios son los enumerados por artillerytrades en https://www.instagram.com/p/DepEDXbRMRF/. Se revisó su descripción visible; el reel propone herramientas, no una estrategia completa verificable. El cruce SMA20/50 es un ejemplo creado para comprobar el proceso, no una regla atribuida al autor.

## Qué está funcionando

`laboratorio.py`: CSV OHLCV con metadatos, validación, SMA20/50 long/flat con tamaño fijo 1 y ejecución en la apertura siguiente, coste por lado/unidad, spread fijo y reporte JSON. No importa librerías de brokers ni envía órdenes ni realiza peticiones de red. Selección de parámetros fija, sin optimización masiva. Reserva el último 20 % como tramo de evaluación y usa 50 barras previas sólo para calentamiento; no opera antes del corte. Repetir o ajustar reglas después de mirar ese tramo invalida su independencia. No se afirma control de holdout único ni validación estadística completa.

Ejemplo sintético: 600 barras matemáticas, sin sesiones reales. Siete pruebas aprobadas y demostración ejecutada con backtesting 0.6.5 en entorno independiente. La versión probada se fija para reproducibilidad; no se presenta como la última publicación de PyPI. No se modificó el entorno principal de la terminal.

## Arranque en Windows

Desde esta carpeta, crea un entorno independiente (Python 3.12 recomendado):

```powershell
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.lock.txt
.venv/Scripts/python.exe laboratorio.py --demo --salida resultados/demo.json
.venv/Scripts/python.exe -m pytest verificar_laboratorio.py -q
```

Para CSV propio autorizado:

```powershell
.venv/Scripts/python.exe laboratorio.py --csv barras.csv --metadata metadatos.json --salida resultados/propio.json --capital 1000000 --comision 1 --spread 0.0001
```

Los importes del comando son parámetros de demostración, no tarifas de broker ni recomendaciones. CSV: `fecha,Open,High,Low,Close,Volume`, entre 150 y 200000 barras, hasta 40 MiB; fechas con zona, únicas y ordenadas. Metadatos obligatorios: `simbolo`, `fuente`, `licencia`, `calidad` (proveedor/importado/sintetico) y `multiplicador` positivo. Usa el identificador y vencimiento reales, no un continuo genérico para simular ejecución. El contrato de este laboratorio se transforma explícitamente si partes de una exportación de la terminal; no se cambia su esquema de producción.

El entorno ya utilizado en este equipo está en `C:/Users/MIKE/Documents/Codex/2026-10-16/tienes-total-facultad-sobre-mi-pc-2/work/reel-bots-venv`; su Python puede ejecutar directamente este script sin reinstalar paquetes. `requirements.lock.txt` registra las versiones de ese entorno; no se incluye el entorno completo en el ZIP.

## Límites del modelo

Capital virtual; sin reglas Lucid/Apex. Margin=1, sin apalancamiento. Los precios OHLC se multiplican por el multiplicador declarado para expresar valor por unidad/contrato; el modelo no valida márgenes, tick value, vencimiento, rollover, interrupciones, límites de precio ni calendario de liquidación de futuros. Spread constante no es simulación del libro ni de la cola. No deduce Order Flow, Option Flow ni gamma de las velas. No se debe usar este P&L como prueba de una automatización de futuros lista para operar.

## Plataformas

- Actinver-terminal: usa este laboratorio como proceso offline opcional; conserva los backtests y pruebas de robustez existentes. Informe descargable en Aprender y recursos y referencia en la oficina. Sin un endpoint web que ejecute Python ni procesos en segundo plano.
- Quantower: trasladar reglas a C# con el SDK instalado y comprobar equivalencia sobre las mismas barras; ninguno de estos repositorios es por sí mismo un plugin Quantower. Prompt ampliado; plugin no compilado ni instalado.
- TradingView: `sma_referencia.pine` es un indicador de referencia para comparar medias y cruces confirmados; no abre operaciones ni envía alertas. Copia/compilación en Pine Editor quedan pendientes de la plataforma. No ejecuta Python/Rust, no llama HTTP a localhost y no importa los otros motores.
- Tradovate: LEAN y Nautilus no muestran Tradovate en las listas oficiales consultadas. Eso no prueba imposibilidad de un adaptador personalizado. TradersPost documenta conexiones Tradovate/ProjectX; es un servicio externo con sus propias condiciones, no un repositorio gratuito ni una obligación técnica. No se contrató ni conectó. Las reglas de cada firma/cuenta requieren verificación vigente antes de plantear cualquier ejecución.

## Recursos y licencias

Manifiesto `repositorios.json` con rutas, commits y estados. Freqtrade GPL-3.0; backtesting.py AGPL-3.0; LEAN Apache-2.0; Nautilus LGPL-3.0. vectorbt incluye Apache-2.0 y condición Commons Clause: no asumir reventa/hosting comercial irrestricto. No se ha copiado código de vectorbt al proyecto. Este subproyecto original se ofrece bajo AGPL-3.0; texto en LICENSE-AGPL-3.0.md. Sus dependencias mantienen sus licencias.

No se actualizó ni sobrescribió ninguno de los tres clones existentes. No se eliminó ningún repositorio. Las dependencias de LEAN, Freqtrade, vectorbt y Nautilus no se instalaron en esta entrega.

## Fuentes primarias

- Repositorios oficiales: enlaces en `repositorios.json`.
- https://kernc.github.io/backtesting.py/doc/backtesting/backtesting.html
- https://www.quantconnect.com/docs/v2/lean-cli/live-trading/brokerages
- https://nautilustrader.io/docs/latest/integrations/
- https://docs.traderspost.io/docs/all-supported-connections/tradovate
- https://docs.traderspost.io/docs/assets/prop-firm-trading
- https://help.quantower.com/quantower/quantower-algo/introduction
- https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/

La prueba opcional se llama `verificar_laboratorio.py` para que la batería normal de la terminal no importe un motor que no forma parte de sus dependencias. Ejecútala expresamente en el entorno del laboratorio.
