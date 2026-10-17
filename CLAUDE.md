# CLAUDE.md — actinver-terminal

Este repo opera bajo el **prompt de autonomía total** («Terminal local de análisis
de portafolios»). **Versión vigente: `docs/mandato-autonomia-v2.txt`**, aprobada por el
usuario el 6-oct-2026. La v1, del 23-sep, se conserva como historial. Procedencia, sha256 y
cambios en `docs/mandato-autonomia.md`. Si un texto choca con una instrucción posterior del
usuario, gana la más restrictiva.
Resumen de sus límites duros (sección 6, no negociables):
sin dinero real ni órdenes en vivo, secretos solo en `.env`, datos solo por vía
legal (sin saltar anti-bot/paywalls), sin automatizar la cuenta personal de
Actinver, nada destructivo fuera de este repo y de los adjuntos, nunca simular un
precio como si fuera vigente, servir solo en `127.0.0.1`.

## Qué es

Terminal local (FastAPI + SQLite + HTML/CSS/JS sin build) para comparar dos
propuestas de portafolio (solo acciones / acciones+ETF+fondos) contra la cartera
real del inversionista, calibrada para el **Reto Actinver 2026**. Solo informa y
simula: ninguna ruta envía órdenes a una casa de bolsa. Ver `README.md` para
arranque rápido y `docs/` para el diseño completo.

## Cómo orientarte (Claude Code / Claude Cowork)

Abre esta carpeta como proyecto. Lee primero, en este orden:
1. `docs/resumen-ejecutivo.md`: qué es, estado, resultados y decisiones pendientes (una página).
2. `docs/initial-audit.md`: arquitectura y flujo de datos.
3. `docs/actinver-rules.md`: reglas del Reto con su fragmento oficial y la prueba que las cubre.

Antes de leer archivos completos, busca el fragmento mínimo con
`uv run python scripts/indice_contexto.py buscar "<tema>"` (ver `docs/token-budget.md`).
El arranque para vista previa está en `.claude/launch.json` (`actinver-terminal`, puerto 8765).

## Estado comprobado (2026-10-12, v0.30.0, rama `main`)

- **Cuenta del Reto (viernes 16-oct, 14:00, captura confirmada):**
  - Valuación $906,431.05 (−9.36 %); poder de compra $4,077.32; ACTDUAL B $0.21.
  - Desde el 15-oct: NVAX −12.4 %, AMD −5.3 %, MU −4.9 %, ALPEK −0.9 %, NVDA −0.8 %; XOM +3.1 %, GMEXICO +2.0 %.
- **Cuenta del Reto (jueves 15-oct, cierre 14:00, captura confirmada):**
  - Valuación $935,448.69 (−6.46 %); poder de compra $4,077.32; ACTDUAL B $0.21.
  - Desde el 14-oct: AMD +3.5 %, MU +1.4 %; NVDA −2.4 %, XOM −2.1 %, ALPEK −1.9 %, NVAX −1.2 %, GMEXICO −0.7 %.
- **Cuenta del Reto (miércoles 14-oct, 15:06, captura confirmada):**
  - Valuación $930,543.32 (−6.95 %); poder de compra $4,077.32. Nueva posición mínima: 1 título de ACTDUAL B ($0.21).
  - Desde el 13-oct: AMD −10.0 %, MU −3.6 %, NVDA −2.4 %, GMEXICO −1.5 %; ALPEK +4.2 %, XOM +2.5 %, NVAX +1.7 %.
- **Cuenta del Reto (martes 13-oct, 14:30, captura confirmada):**
  - Mismas 7 posiciones; valuación $962,453.35 (−3.75 %); poder de compra $4,077.32.
  - Desde el 12-oct: MU −3.1 %, ALPEK −3.0 %; NVAX +3.2 %, AMD +2.2 %, XOM +1.8 %, NVDA +1.5 %, GMEXICO +1.0 %.
- **12-oct noche (v0.30.0, etapa 3):** Riesgo (VaR/CVaR, exposición, contribución al riesgo; MU aporta 74 % del
  riesgo con 47 % del peso), Seguimiento (lista unificada con Movimientos, ficha, comparación) y Backtesting
  reproducible (t → t+1, costos del Reto, huellas). Las tres etapas de `docs/integracion-repositorios.md` están completas.
- **12-oct noche (v0.29.0, etapa 2):**
  - Heston propio en Option Flow, exportación a hftbacktest (.npz) en Order Flow e importación de velas de
    TradingView, OpenBB y Yahoo.
  - Con MU, Heston converge (60 contratos, error de 3.7 puntos de volatilidad), pero σ queda en su límite y no cumple
    Feller: se muestra como advertencia.
- **12-oct noche (v0.28.0, etapa 1 aprobada por el usuario):**
  - Velas OHLCV, Order Flow y Option Flow en `terminal/flujo/` (`docs/flujo-ordenes-opciones.md`). Solo datos
    reales (Alpaca SIP/IEX/opciones indicativas; Bitso vía ccxt) o CSV importado; sin fuente, los paneles no simulan.
  - Mapa de calor con prioridad única, ajuste por splits, ventanas de 1/5/20 y ficha; RSI de Wilder.
  - Acciones del usuario: `docs/acciones-requeridas-usuario.md`. Etapas 2 y 3: `docs/integracion-repositorios.md`.
- **Cuenta del Reto (lunes 12-oct, 18:02, captura confirmada):**
  - Mismas 7 posiciones; valuación $970,442.17 (−2.96 %); poder de compra $4,077.53. La terminal valúa $969,921 (−0.05 %).
  - Desde el 9-oct: MU −4.6 %, AMD −2.9 %, NVDA −2.0 %, NVAX −2.6 %; ALPEK +4.9 %, XOM +0.8 %.
  - Plan para el 13-oct: no cambiar nada (mantener +5.1 % frente a propuesta +5.4 %, diferencia menor al margen de 1 punto).
- **Cuenta del Reto (viernes 9-oct, 14:30, captura confirmada):**
  - Mismas 7 posiciones; valuación $996,608.12 (−0.34 %); poder de compra $4,077.53.
  - Pesos: MU 47.5 %, GMEXICO 15.8 %, AMD 14.6 %, NVDA 11.0 %, ALPEK 5.2 %, NVAX 3.0 %, XOM 2.5 %.
  - Desde el 8-oct: NVAX +17.2 %, GMEXICO +5.3 %, ALPEK +3.7 %, XOM +2.8 %; AMD −1.0 %.
- **Cuenta del Reto (8-oct, 17:26, captura confirmada):**
  - Mismas 7 posiciones; valuación $980,186.87 (−1.98 %); poder de compra $4,077.53.
  - Día: MU −3.3 %, NVDA −1.5 %, AMD −2.5 %; XOM +2.6 %.
- **Cuenta del Reto (7-oct, 14:30, captura confirmada):**
  - Compras de XOM y NVAX ejecutadas por el usuario: 8 XOM a $2,947.54 y 126 NVAX a $203.23.
  - Valuación $1,001,256.90 (+0.13 %); poder de compra $4,077.53.
  - Posiciones: MU 48.3 %, AMD 15.1 %, GMEXICO 15.1 %, NVDA 11.1 %, ALPEK 5.0 %, NVAX 2.6 %, XOM 2.4 %.
- **7-oct (v0.26.0, D-61):**
  - Historia externa del usuario (Excel, 1962 → 9-oct-2025): 148 columnas verificadas extienden rendimientos
    hacia atrás (`docs/historia-externa.md`). Validación desde 2004: máximo rendimiento supera a 1/N
    (IC [+3.6 %, +23.8 %]), con sesgo de supervivencia y caída máx. −70 %; no se declara ventaja.
  - Finviz Elite conectado pero apagado: requiere `FINVIZ_AUTH_TOKEN` (de pago; decisión del usuario).
  - 348 pruebas en verde.
- **Cuenta del Reto (6-oct, 14:25, captura confirmada):**
  - El usuario hizo la alternativa C: vendió 6 QQQ y compró 26 NVDA a $4,344.02.
  - Valuación $987,988.71 (−1.2 %); poder de compra $6,318.77.
  - Posiciones: MU 47.5 %, GMEXICO 15.4 %, AMD 15.3 %, NVDA 11.3 %, ALPEK 5.0 %, AMAT 4.8 %.
  - Las boletas #289/#290 (AMAT → NVDA) se cancelaron el 7-oct: el usuario eligió petróleo.
- **7-oct ≈ 08:38 (captura solo del resumen, no guardada):**
  - AMAT vendida (5 a $9,400.00, según el cambio en el poder de compra).
  - Poder de compra $53,264.25; valuación $993,855.25 (−0.61 %).
  - Boletas vigentes #298/#299: comprar ≈ 8 XOM y ≈ 126 NVAX, 50/50 por decisión del usuario.
  - NVAX: −0.2 % estimado al cierre y −23 % en un mal escenario.
  - Falta la captura con la tabla de posiciones para registrar la cartera nueva.
- **Cuenta del Reto (7-oct, 08:00, captura confirmada):**
  - Mismas 6 posiciones; valuación $979,561.91 (−2.04 %); poder de compra $6,318.77.
  - Boletas #291/#292 (vender AMAT y comprar ≈ 17 XOM): las pidió el usuario y vencían a las 08:19, porque usan el precio en vivo.
  - Medidas igual, bajan el escenario malo de −16.3 % a −15.1 %, sin mejorar la ganancia esperada.
  - Entre las acciones petroleras del catálogo (XOM, CVX, DVN, OXY, FANG), XOM tuvo la mayor estimación (+2.1 % al cierre). Todas tienen correlación negativa con la cartera.
- **6-oct (v0.25.0):**
  - El usuario mantiene máximo rendimiento aceptando el riesgo de cola (D-59).
  - Alternativa gratuita a EODHD: proxy ADR para 8 emisoras (`scripts/historia_adr.py`; `terminal robustez --proxy-adr`) y el PDF del portal para el precio del día.
  - Revisión del mandato con 9 propuestas, pendientes de decisión del usuario (`docs/mandato-autonomia.md`).
- **6-oct (v0.24.0, protocolo de robustez):**
  - `uv run terminal robustez` (reanudable, ≈ 15–20 min por universo, ≤ 0.36 GB).
  - Cuadrícula de 150 combinaciones × 500 simulaciones Monte Carlo.
  - Mesetas amplias: 66 % de la cuadrícula aprueba en acciones y 79 % en mixta.
  - La selección anidada NO supera a la configuración vigente, así que no se cambian parámetros.
  - Máximo rendimiento vigente: «no aprobada» por caída p5 −23/−24 %; decisión del usuario.
  - Vista «Robustez» en «Más».
- **6-oct (v0.23.0, auditoría de 7 mejoras):**
  - 329 pruebas en verde.
  - Validación V1 (1,099 sesiones fuera de muestra): sin ventaja frente a 1/N, propuestas sin cambios.
  - Probabilidad de subida EXPERIMENTAL (peor que la frecuencia base).
  - Kronos sin ventaja (494 MB, 95 min).
  - Se conserva el léxico de titulares (el LLM 1.5B invierte 9 direcciones).
  - Búsqueda de documentación con BM25 (13/15).
  - Mandato en `docs/mandato-autonomia.txt`.
  - Recomendación BMV en `docs/bmv-licencia.md` (EODHD Historian, USD 19.99/mes; decisión del usuario).
- **5-oct noche (v0.22.0):**
  - 321 pruebas en verde.
  - Con criterio de ganancia, el plan no opera si la propuesta no supera a mantener la cartera por 1 punto tras comisiones (mismo método, dos ventanas; D-52).
  - Para el 6-oct: «hoy no cambies nada» (mantener +7.6 % frente a propuesta +7.0 %).
- **5-oct noche (v0.21.0):**
  - Criterio del plan = `ganancia` (media esperada), decisión del usuario (D-50).
  - `terminal precios-portal <pdf>` importa los precios BMV del PDF de la pestaña Acciones que arma el usuario (D-51); las BMV sin precio bajan de 19 a 6.
  - Universo de 236 y catálogo de 233.
- **5-oct (v0.20.0, competencia):**
  - 314 pruebas en verde, sin contar las de TradingView.
  - Telegram en lenguaje sencillo: `/plan` y `/boletas`; el formato técnico sigue en `/completo`, `/detalle` y `/boletas detalle` (D-49).
  - El plan cambia si otra propuesta domina a la fijada.
  - Universo de 230, con 56 ETF y 25 fondos del portal.
  - Auditoría en `docs/auditoria-2026-10-05.md`. Lo más urgente: 19 BMV del catálogo sin ningún precio (cupo de EODHD), fondos con solo 5 sesiones de historia, y la decisión pendiente frente a 1/N.

- Pruebas: 283 de Python en verde (`uv run pytest -q`, sin contar las de TradingView de otra sesión) y 19 del Worker (`npm --prefix cloud-alerts test`).
- Pronóstico al cierre del Reto (D-46, `docs/pronostico-reto.md`): 1, 5 y 31 sesiones, en MXN y con barrera. Con datos al 30-sep: SIN VENTAJA DEMOSTRADA en los tres horizontes y probabilidad de subida mal calibrada → «señal experimental», no cambia el plan. Se emite solo una vez por sesión (≈140 s, 0.36 GB). `/pronostico` en Telegram.
- Monitor en la nube (`cloud-alerts/`, D-47): Worker + D1 desplegados el 1-oct en Cloudflare Workers Free. URL pública responde y `/estado` rechaza solicitudes sin firma (401). La terminal sincroniza automáticamente; sigue pendiente comprobar un aviso real de relevo tras el primer cron, a partir de las 06:00 CDMX.
- Movimientos públicos (`terminal/movimientos/`, D-48, `docs/movimientos-publicos.md`): SEC EDGAR conectada (Form 4 de cartera/propuestas/seguimiento y 13F de 8 gestores); alertas solo de contexto, peso 0 en la puntuación. Pendiente: resolver CUSIP ambiguos en `config/cusip.csv` si interesa alguno.
- Cuenta del Reto (1-oct): hay una captura del portal confirmada (30-sep 21:43); el pronóstico de cartera la usa.
- Lo que sigue es del 30-sep:
- Precios (14:35 CDMX, tras el cierre BMV de las 14:00): 0 vigentes, 147 retrasados (cierre del 29-sep; cupo por hora de Tiingo/EODHD agotado), 5 vencidos y 22 BMV sin datos, de 174. Fondos: 23/23 con NAV del 28-sep (la hoja pública de Actinver aún no publica el 29-sep). FX: Banxico FIX 18.0692 del 30-sep. Son cierres, no tiempo real; el SIC es referencia origen × FX.
- Catálogo del simulador: 165 instrumentos; propuestas y Ranking excluyen los 11 que no están (10 ETF y SMARTRC).
- Propuestas: con media robusta ya no aparecen FUBO ni MRNA. Validación fuera de muestra de solo 84 sesiones en las principales. La referencia del plan («Acciones · Máxima puntuación», 73.0) rindió +1.1 % anual fuera de muestra contra +10.8 % del 1/N: decisión pendiente del usuario.
- Cuenta del Reto: sin captura del portal; el millón es LOCAL.
- Acceso: lanzador `.exe` probado apagado/encendido; escucha solo en 127.0.0.1; Serve «tailnet only»; `.ts.net` probado solo desde esta PC.
- Alertas: Telegram y escritorio «enviada» (prueba del 30-sep); correo sin SMTP. Claude sin `ANTHROPIC_API_KEY` (chatbot local).
- Respaldos: diario verificado en `data/respaldos` (el primero, del 30-sep).

## Registro histórico (2026-09-23, v0.6.0)

- 146 pruebas en verde (`uv run pytest`). v0.7: boleta de decisión (`terminal/boleta.py`, `docs/decision-workflow.md`) y banco de estrategias (VENTAJA NO DEMOSTRADA). Lighthouse: escritorio 100/100/100, móvil 93/100/100.
- **Funciones:**
  - 4 propuestas (acciones/mixta × lente rendimiento/ajuste) con las reglas del Reto (`config/reto.yaml`, versionado en `versiones_reglas`).
  - Pestaña PASADO / PRESENTE / FUTURO; operaciones confirmadas (práctica ≠ competencia); órdenes pendientes solo como referencia.
  - Bitácora de decisiones y alertas con ficha de revisión e inhibición por datos.
  - Receptor de webhooks de TradingView e investigación sin fuga (`terminal/investigacion/`).
- **Precios (dato del 23-sep, OBSOLETO):** entonces había 0/176 instrumentos con precio BMV verificado. Hoy hay cierres diarios de EODHD para la BMV y NAV oficiales para los fondos (ver «Estado comprobado»); siguen sin ser cotizaciones BMV en tiempo real.
- **Resultados con datos reales (índices de FRED):** SIN VENTAJA DEMOSTRADA en H=1 y H=5 (`docs/model-card.md`). backtrader coincide exactamente con el cálculo independiente.
- **Kronos:** dependencias en el grupo opcional `uv sync --group kronos --inexact`; pesos Kronos-mini en la caché de Hugging Face. El experimento completo (`scripts/experimento_kronos.py`) **no terminó**: el equipo se quedó sin memoria (5.9 GB, 0.3 GB libres). Reintentarlo con `--muestras 1 --contexto 256` y otras apps cerradas.
- **FRED (24-sep):** el CSV público deja colgadas las peticiones con el User-Agent de la terminal. No se falsifica el User-Agent: la vía es `FRED_API_KEY` (API oficial, gratis) o `BANXICO_TOKEN`.
- **Decisiones:** D-01 a D-45 en `docs/decisiones.md`. Otra sesión puede trabajar en paralelo (D-30): revisa `git log` y `git status` antes de commitear.

## Comandos

```bash
cd C:\Users\MIKE\Desktop\Repos\actinver-terminal
uv sync                      # entorno .venv (uv lo crea si falta)
uv run terminal demo         # datos sintéticos, base separada en data/demo/
uv run terminal actualizar   # descarga incremental respetando límites por proveedor
uv run terminal iniciar      # datos reales, http://127.0.0.1:8765
uv run terminal reporte cierre   # preapertura | cierre | semanal (--sin-actualizar para no consultar proveedores)
uv run pytest -q             # 283 pruebas (más npm --prefix cloud-alerts test: 19)
uv run terminal comparar-modelos   # walk-forward de modelos (TERMINAL_MODO=demo solo como prueba funcional)
start.bat                    # arranque en un comando (Windows)
uv run python scripts/verificar_universo.py --descargar   # re-verifica universo BMV/Nasdaq
```

Sin credenciales en `.env`, el modo real obtiene tipo de cambio de FRED pero las
propuestas quedan «suspendidas» hasta tener precios de un proveedor configurado o
importados por el usuario — es intencional (D-12), no un bug.

## Brechas conocidas / próximas mejoras (mayor impacto primero)

1. **Datos en tiempo real verdadero**: ninguna fuente configurada lo ofrece hoy
   (D-16, `docs/fuentes.md#tiempo-real`). Cerrar esto requeriría un proveedor de
   pago — **requiere decisión del usuario**, no se contrata solo.
2. **Cobertura completa de BMV/SIC**: EODHD da 20 peticiones/día gratis; el universo
   verificado puede ir por delante de lo que se puede refrescar a diario. Vigilar
   `docs/matriz.md` y considerar una cola de actualización que
   priorice los instrumentos con posición abierta o en una propuesta activa.
3. **Cuenta del Reto**: no hay captura confirmada del portal. El usuario debe copiar
   saldo y posiciones manualmente para comparar propuestas y alertas con su cartera real.
4. **Ranking de modelos** (D-33): el comparador ya existe; falta evaluarlo con las
   series reales disponibles y una prueba fuera de muestra suficiente. La cobertura
   parcial y la historia corta impiden declarar una ventaja predictiva.
5. **CloudflareSpeedTest_duplicates_backup:** eliminado el 6-oct-2026 por orden del usuario.
   Respaldo en `Desktop/Repos/_respaldos/` y carpeta en la Papelera de reciclaje.
   Otros repos mal ubicados de `docs/repos.md` siguen pendientes; borrarlos requiere
   confirmación expresa del usuario (mandato v2).

## Al cerrar cada sesión

Actualiza esta sección y `CHANGELOG.md` con: qué se construyó, qué mejoró (con
métrica: pruebas, retraso medido, cobertura del universo), qué sigue, y qué
necesita decisión del usuario (sección 7 del mandato: gastar dinero, cuentas o
tokens a su nombre, su sesión personal de Actinver, exponer la terminal fuera de
este PC, borrar trabajo no recuperable, o reglas del Reto que no se puedan
confirmar y cambien la estrategia).


## Actualización 11-oct-2026 — centro de investigación

- Nueva sección **Más → Investigación**, con las 15 fuentes/herramientas solicitadas.
- Conectores de contexto: Alpha Vantage INCOME_STATEMENT (OVERVIEW es premium), FRED macro, CoinGecko Demo, EIA v2 y BLS público.
- Finviz Elite conserva su conector existente. Las otras nueve herramientas se aplican por consulta y CSV/notas manuales; sus APIs de pago no se activan ni contratan.
- Tablas `investigacion_observaciones` y `investigacion_consultas`: revisiones y disponibilidad desde la ingestión, separadas de precios/universo/propuestas.
- Refresco en ciclos completos con caché y cupos; falla de una fuente no detiene las demás. Demo no consulta APIs.
- Configuración, plantillas y proyectos cuantitativos: `docs/centro-investigacion.md`.
- Verificación de esta entrega: 150 pruebas relevantes en verde; consulta real BLS con 115 observaciones; interfaz comprobada en escritorio/móvil sin errores JavaScript. Alpha Vantage/FRED/CoinGecko/EIA pendientes de claves; otras APIs no activadas.

## Actualización 16-oct-2026 — indicadores, GEX y laboratorio

- Velas: EMA20/50, MACD12/26/9, estocástico14/3/3 y SAR0.02–0.2, con calentamiento nulo; se descartan respuestas antiguas si cambian los controles rápido.
- Mercado, Velas, Order Flow, Option Flow, Riesgo y Laboratorio visibles en la navegación principal. GEX conserva signo convencional separado de exposición absoluta y exige OI, gamma, multiplicador, spot y moneda compatibles.
- Laboratorio: signos por bloques, semilla, p con corrección +1 y Holm; no demuestra alfa. Plan intradía informativo separado, sin órdenes, con pausa y calidad de datos.
- Verificación: suite completa de 561 pruebas aprobada; después de los ajustes finales, 41 pruebas enfocadas aprobadas. Sintaxis JS y 15 archivos nuevos/modificados revisados sin patrones de secretos. Laboratorio y persistencia de controles comprobados en navegador; datos sintéticos solo como ejemplo identificado.
- Pendientes: feed apto de tiempo real, tape de opciones y OI/especificaciones para poblar GEX; medir pérdida intradía requiere entrada manual. No se contrataron servicios ni activaron órdenes. Ver `docs/mejoras-intradia-permutaciones.md`.

## Actualización 16-oct-2026 — adjuntos y práctica de microestructura

- Aprender y recursos: síntesis de cuatro PDF y diez capturas, fórmulas precisadas y fuentes verificables en config/aprendizaje.json; API de lectura /api/aprendizaje.
- Order Flow: footprint de 5 minutos y selector bid/ask, volumen/delta; heatmap de snapshots compatibles sin interpolar ni mezclar feeds.
- Referencia personal de precios solo en data local ignorado; no se incorpora a cartera ni cotizaciones. Artifact independiente ampliado con replay y ejercicios.
- Verificación: 83 pruebas enfocadas aprobadas; sintaxis JS y comprobación de catálogo, replay y medias en navegador.
- Pendiente: dos URL exactas de playlists, revisión integral de videos y fuente Level 2/tape autorizada para datos completos. No se contrataron servicios ni se habilitaron órdenes. Ver docs/recursos-educativos.md.

## Actualización 16-oct-2026 — preregistro, filtro de Skylit y proveedores gratuitos

- Laboratorio: preregistro con huella, tramos exploración | embargo | holdout (un solo uso) y exportación JSON (`docs/mejoras-intradia-permutaciones.md` §6).
- Option Flow: perfil experimental del filtro de Skylit sobre CSV; los criterios sin datos quedan «no evaluables» y no cuentan como filtro completo (§7).
- `docs/proveedores-gratuitos.md` (fuentes oficiales al 16-oct, matriz por herramienta, disponibilidad comprobada) y `docs/proyecto-colab.md` (esperando que el usuario elija el tema).
- 591 pruebas en verde. Decisión del usuario: usar o no el endpoint de contratos de Alpaca (API de trading) para OI/multiplicador.

## Actualización 16-oct-2026 — cinta de opciones y perfiles de sesión

- Alpaca Market Data: cinta indicativa con corte de 16 min, procedencia y campos originales
  `t/x/p/s/c` en `flujo_opciones_operaciones`. Selección explícita de hasta 100 contratos
  de la cadena guardada, tres páginas como máximo y caché de 120 s por selección.
- Option Flow: evaluación Skylit de cinta guardada además del CSV. No reutiliza NBBO de
  otra hora, no inventa OI/patas, no une fracciones temporales distintas en nanosegundos.
  Con esta fuente el filtro completo sigue sin aplicarse.
- Order Flow: TPO observado por sesión de 30 min, zona de origen, sin interpolar;
  es una cota inferior OHLC. POC/VAH/VAL ≥70 % del perfil de volumen del rango,
  con algoritmo documentado y valores nulos si no alcanzan los datos.
- Nuevas lecturas limitadas a 30/min; tablas desplazables con foco de teclado.
- Recorrido demo de preregistro guardar/evaluar/reevaluar/exportar verificado, con
  huella conservada tras cambiar datos. Revisión móvil a 375 px: Laboratorio,
  Order Flow y Skylit con ejemplos SINTÉTICOS, sin errores JS en los recorridos.
- Arranque normal carga `.env` y detecta presencia de credenciales; no se reprodujo
  el fallo anterior. `TERMINAL_SIN_ENV` omite la carga deliberadamente;
  `TERMINAL_SIN_MOTOR` no la omite. No se alteraron esos interruptores.
- Twelve Data Basic no cubre la BMV general según ficha XMEX oficial; Finnhub conserva
  límites gratuitos no confirmados. Ambos desconectados. Ver matriz de proveedores.
- Suite completa: 601 aprobadas; tras los últimos ajustes, 49 pruebas enfocadas
  finales aprobadas. Sintaxis JS correcta y 0 hallazgos de secretos en 18 archivos.
  Secuencia y límites de revisión en el informe de verificación de esta entrega.
- Pendientes: autorización textual del endpoint de contratos Alpaca y tema Colab.
  GEX sin datos nuevos de OI; ningún modelo tiene ventaja predictiva demostrada.
  Detalles: `docs/verificacion-pendientes-2026-10-16.md`, `docs/perfiles-sesion.md`
  y `docs/mejoras-intradia-permutaciones.md` §8. TradingView ajeno preservado.

## Cierre 16-oct-2026 — revisión visual de la versión final

- Resuelta la desconexión del navegador: comprobados a 375 px el campo de contratos
  OCC, el orden de Tab/Enter y el desplazamiento de la tabla Skylit con flechas.
  La región conserva el foco y su desplazamiento pasó de 0 a 120 px.
- Repetidas las vistas finales de Order Flow/TPO y Laboratorio. Al reabrir el
  experimento demo con otros rendimientos conserva la huella y devuelve el resultado
  guardado. Consola del recorrido final: cero errores.
- Base demo, credenciales/motor desactivados, ningún proveedor consultado; tamaño
  del navegador restaurado, pestaña y servidor temporal cerrados.
- Suite completa repetida sobre la revisión final: **610 pruebas aprobadas** en
  831.34 s; solo el aviso de deprecación preexistente de Starlette/AnyIO.
  Sintaxis JS y revisión de secretos correctas. Evidencia definitiva en
  `docs/verificacion-pendientes-2026-10-16.md`.
- Solo siguen condicionados el endpoint de contratos de Alpaca (autorización textual)
  y el notebook Colab (tema elegido). Sin datos nuevos para GEX ni ventaja demostrada.
