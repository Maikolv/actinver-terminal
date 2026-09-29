# CLAUDE.md — actinver-terminal

Este repo opera bajo el **prompt de autonomía total** («Terminal local de análisis
de portafolios») guardado por el usuario en el proyecto de chat correspondiente
(no está en este repo como archivo; si no lo tienes a la vista, pide al usuario
que lo pegue de nuevo). Resumen de sus límites duros (sección 6, no negociables):
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

## Estado comprobado (2026-09-29, v0.12.1, rama `main`)

- 203 pruebas en verde. Hay 148 de 174 instrumentos con precio: 41 vigentes, 107 retrasados (cierre de la sesión anterior) y 26 emisoras BMV sin datos. Son cierres diarios o NAV, no cotizaciones BMV/SIC en tiempo real.
- La hoja oficial Actinver del 28-sep-2026 aporta NAV a los 23 fondos; JPMRVUS usa exactamente la serie B-1.
- «Mi cartera» separa la captura del portal y el registro local. Aún no hay captura confirmada del Reto: el millón mostrado es local. La captura exige hora, efectivo, valor total y posiciones coherentes.
- Las alertas de cambio, captura pendiente y posible movimiento llegan por Telegram y escritorio. Correo espera configuración SMTP en `.env`.
- Faltan la primera captura real del usuario y un contrato de datos con credenciales para BMV/SIC en tiempo real. EODHD gratuito recupera las emisoras faltantes paulatinamente, con cupo diario.

## Registro histórico (2026-09-23, v0.6.0)

- 146 pruebas en verde (`uv run pytest`). v0.7: boleta de decisión (`terminal/boleta.py`, `docs/decision-workflow.md`) y banco de estrategias (VENTAJA NO DEMOSTRADA). Lighthouse: escritorio 100/100/100, móvil 93/100/100.
- **Funciones:**
  - 4 propuestas (acciones/mixta × lente rendimiento/ajuste) con las reglas del Reto (`config/reto.yaml`, versionado en `versiones_reglas`).
  - Pestaña PASADO / PRESENTE / FUTURO; operaciones confirmadas (práctica ≠ competencia); órdenes pendientes solo como referencia.
  - Bitácora de decisiones y alertas con ficha de revisión e inhibición por datos.
  - Receptor de webhooks de TradingView e investigación sin fuga (`terminal/investigacion/`).
- **Precios:** `MarketDataProvider` (`terminal/cotizaciones.py`). Hoy **0/176 instrumentos con precio BMV verificado** (sin licencia ni claves): todo aparece como «SIN PRECIO CONFIABLE» a propósito.
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
uv run pytest -q             # 146 pruebas
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
5. **CloudflareSpeedTest_duplicates_backup** (duplicado verificado: 28/28 archivos idénticos)
   y otros repos mal ubicados detectados en `docs/repos.md`: pendiente de limpieza fuera
   de este repo (afecta a `Desktop/Repos`, no a `actinver-terminal`); dejar
   constancia en ese doc antes de borrar cualquier cosa, con respaldo o rama.

## Al cerrar cada sesión

Actualiza esta sección y `CHANGELOG.md` con: qué se construyó, qué mejoró (con
métrica: pruebas, retraso medido, cobertura del universo), qué sigue, y qué
necesita decisión del usuario (sección 7 del mandato: gastar dinero, cuentas o
tokens a su nombre, su sesión personal de Actinver, exponer la terminal fuera de
este PC, borrar trabajo no recuperable, o reglas del Reto que no se puedan
confirmar y cambien la estrategia).
