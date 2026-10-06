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

## Estado comprobado (2026-10-01, v0.17.0, rama `main`)

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
