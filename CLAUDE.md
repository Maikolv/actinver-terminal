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

## Estado comprobado (18-oct-2026, v0.31.0, rama `main`)

El detalle por fecha (capturas del 30-sep al 16-oct, versiones 0.6–0.30 y entregas del 11 al 17-oct) está en
`docs/historial-estado.md`. Aquí solo lo vigente.

- **Cuenta del Reto, última captura confirmada (lunes 19-oct, 10:05):**
  - Valuación $929,338.13 (−7.07 %); poder de compra $4,077.53.
  - 7 acciones y 1 título de ACTDUAL B. Pesos: MU 45.0 %, GMEXICO 17.5 %, AMD 14.0 %, NVDA 11.4 %, ALPEK 5.9 %,
    XOM 2.9 %, NVAX 2.9 %. Cumple las reglas (≥ 5 emisoras, ≤ 50 %).
  - Las capturas se registran con `portal.guardar(..., confirmar=True)`. Precios en MXN, ajustados solo por splits.
- **Funciones** (todas informan o simulan; ninguna envía órdenes):
  - propuestas y plan del día (Telegram `/plan`);
  - riesgo (VaR/CVaR, contribución), seguimiento y backtesting reproducible;
  - velas con indicadores, Order Flow (footprint, TPO, POC/VAH/VAL) y Option Flow (Heston, GEX, cinta indicativa, filtro
    Skylit experimental);
  - Laboratorio (permutación, Holm, preregistro y holdout único);
  - TSM mensual educativo (`docs/tsm-mensual.md`) y anomalías de volumen (`docs/anomalias-volumen.md`);
  - centro de investigación y Aprender y recursos.
  - Asistente (`terminal/asistente.py`): datos, documentación y notas del usuario; Claude/Ollama si hay credencial.
- **Evidencia:** ningún modelo tiene ventaja demostrada: V1 frente a 1/N, pronóstico al cierre, Kronos y TSM
  (Holm 1.000 en 6 ETF). La estrategia activa es «máximo rendimiento» aceptando riesgo de cola (D-59).
- **Datos:**
  - Alpaca: SIP con ≥ 16 min de retraso, IEX y opciones indicativas. Contratos Paper de solo lectura, OI fechado de cierre previo y multiplicador, apagado por defecto.
  - EODHD: cierres BMV, 20 consultas al día.
  - Banxico FIX, FRED, EIA y Alpha Vantage.
  - Bitso por ccxt (cripto).
  - Historia externa hasta el 9-oct-2025.
  - Ningún dato en tiempo real. Matriz en `docs/proveedores-gratuitos.md`.
- **Pruebas:**
  - Python: 649 aprobadas el 18-oct tras integrar contratos Paper y notebook tema 3; véase el informe de esta entrega.
  - Worker: 19.
  - Integración continua en `.github/workflows/pruebas.yml` (Ubuntu, sin secretos).
- **Dependencias (18-oct):** `pip-audit` y `npm audit` sin vulnerabilidades. Numpy queda en 2.5.3 porque el notebook
  del tema 3 lo exige fijo. Auditoría en `docs/auditoria-2026-10-18.md`.
- **Sesiones paralelas (D-30):** revisa `git status` y `git log` antes de commitear. No incluyas trabajo ajeno sin
  commitear (TradingView): arma el índice desde `HEAD` con `git update-index
  --cacheinfo`.
- **Auditoría 19-oct** (`docs/auditoria-2026-10-19.md`): navegación sin duplicados, respuestas obsoletas descartadas en Order/Option Flow, `/api/cartera` más rápida. Navegación en 5 grupos por tarea y cabecera compacta en celular (§8).
- **Decisiones pendientes del usuario:**
  - fuentes de pago (Finviz, EODHD, Databento);
  - las 9 propuestas de revisión del mandato;
  - la referencia del plan frente a 1/N.

## Comandos

```bash
cd C:\Users\MIKE\Desktop\Repos\actinver-terminal
uv sync                      # entorno .venv (uv lo crea si falta)
uv run terminal demo         # datos sintéticos, base separada en data/demo/
uv run terminal actualizar   # descarga incremental respetando límites por proveedor
uv run terminal iniciar      # datos reales, http://127.0.0.1:8765
uv run terminal reporte cierre   # preapertura | cierre | semanal (--sin-actualizar para no consultar proveedores)
uv run pytest -q             # ≈ 650 pruebas, duración dependiente del equipo (más npm --prefix cloud-alerts test: 19)
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
3. **Cuenta del Reto**: depende de capturas manuales del portal (no se automatiza, por reglamento). La última
   confirmada es del 16-oct; sin captura reciente, el plan compara contra una cartera desactualizada.
4. **Ranking de modelos** (D-33): el comparador ya existe; falta evaluarlo con las
   series reales disponibles y una prueba fuera de muestra suficiente. La cobertura
   parcial y la historia corta impiden declarar una ventaja predictiva.
5. **CloudflareSpeedTest_duplicates_backup:** eliminado el 6-oct-2026 por orden del usuario.
   Respaldo en `Desktop/Repos/_respaldos/` y carpeta en la Papelera de reciclaje.
   Otros repos mal ubicados de `docs/repos.md` siguen pendientes; borrarlos requiere
   confirmación expresa del usuario (mandato v2).

## Al cerrar cada sesión

Actualiza «Estado comprobado» (solo lo vigente), agrega el detalle fechado a `docs/historial-estado.md` y `CHANGELOG.md` con: qué se construyó, qué mejoró (con
métrica: pruebas, retraso medido, cobertura del universo), qué sigue, y qué
necesita decisión del usuario (sección 7 del mandato: gastar dinero, cuentas o
tokens a su nombre, su sesión personal de Actinver, exponer la terminal fuera de
este PC, borrar trabajo no recuperable, o reglas del Reto que no se puedan
confirmar y cambien la estrategia).

## Recursos de formación añadidos el 18-oct-2026

Aprender y recursos ofrece 92 fichas por área/coste, PDF maestro, CSV, doce posts, enlaces TheBenchmark/Flickflow/Quantower/TradingView y los dos prompts. La práctica local de tesis, DCF/reverse DCF y volatilidad usa ejemplos sintéticos, sin red/persistencia (13 comprobaciones JS aprobadas). 8 pruebas de recursos/microestructura aprobadas; no suite completa. Ver `docs/recursos-certificaciones-2026-10-18.md`. La auditoría `docs/auditoria-post-terminal-Dej_B7_MXrX-2026-10-18.md` distingue demos aisladas de yfinance/FinBERT de conectores reales; SEC actual es Formulario 4, no balances.


## Entrega 18-oct-2026 — contratos Paper y Colab tema 3

Autorización posterior del usuario: contratos Alpaca solo lectura, sin suscripciones
pagadas; tema 3 elegido y Skylit parcial si no hay fuente gratuita completa.
Adaptador limitado a GET de contratos Paper, apagado por defecto y con par de claves
específico; una consulta mínima real exitosa. OI fechado de cierre previo y multiplicador
se unen solo a snapshots compatibles, sin fuga temporal ni atribuir campos preexistentes.
Notebook autocontenido con holdout congelado y Holm; doce pruebas, ejecución sintética
local y ninguna ventaja demostrada. No se ejecutó Colab remoto ni un CSV real.
Se aislaron las pruebas de config/local.toml; sus ventanas corresponden a las historias
sembradas, sin cambiar las ventanas predeterminadas de producción.
NBBO histórico y patas siguen parciales: no se verificó una fuente gratuita permanente
completa. Detalles, uso y validación final: docs/contratos-paper-colab-2026-10-18.md.


### Incorporación del TikTok — 19-oct-2026

Oficina de inversión incorporada en `web/static/recursos/oficina-inversion.html`, accesible desde Aprender y recursos. Tres repositorios clonados (manifiesto `config/oficina-pixel-repos.json`), sin instalar dependencias ni arrancar sus servidores. Código original de sólo lectura con seis roles descriptivos, informe y preparación de prompt para Claude. Compatibilidad nativa Quantower/TradingView aún requiere adaptadores/verificación. Ver `docs/oficina-inversion-pixel.md`.


La oficina comparte `app.css` desde el 19-oct: diseño de informe numerado, sin personajes ni ilustraciones, con sidebar adaptable. Funciones de consulta e informe conservadas; revisión visual en escritorio y 390 px, sin desbordamiento.


Oficina: acceso fijo en navegación principal; selector unificado de universo e instrumentos importados; invalida informes al cambiar selección. Depuración de controles/estilos duplicados. Seis pruebas Node y recorrido de ida/vuelta verificados. Prompt de auditoría técnica/estética en `web/static/recursos/prompt-auditoria-tecnica-estetica-claude.md`; auditoría completa aún no ejecutada.


### Reel de backtesting — 19-oct-2026

Reel DepEDXbRMRF incorporado: laboratorio offline opcional `laboratorios/reel-bots/` (backtesting.py 0.6.5), siete pruebas y demo sintética ejecutadas. Dos repositorios descargados (backtesting.py/LEAN), tres existentes verificados. ZIP y guía desde Aprender y recursos/oficina. Prompts Quantower, TradingView y recursos ampliados; sin integración nativa instalada ni ejecución real.
