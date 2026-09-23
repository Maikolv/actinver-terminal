# Changelog

Formato libre en español. Fecha = día del commit.

## [Sin publicar] — 2026-09-23

### Añadido
- Reglas del Reto Actinver 2026 como configuración versionada (`config/reto.yaml` +
  `terminal/reto.py`): capital, fechas, comisión (0.10 % + IVA), tope de 50 % por
  emisora, mínimo de 5 emisoras, horario de la BMV. Regla no confirmada por el
  reglamento público = `null` con aviso visible, nunca inventada.
- El optimizador aplica el tope por emisora del Reto y calcula el horizonte
  automáticamente (sesiones hábiles hasta el cierre de la competencia, 13-nov-2026).
- Pestaña/endpoint `/api/reto`: checklist de tareas del Reto (inscripción, semana de
  práctica, 5 emisoras, tracks semanales) persistido en SQLite.
- `cumplimiento_reto` en la cartera real y en cada propuesta (mínimo de emisoras,
  tope por emisora), calculado en `terminal/servicios.py`.
- Contexto de mercado sin generar órdenes (`terminal/fuentes_web.py`): calendario
  económico (feed de exportación de ForexFactory), noticias por emisora (RSS público
  de Seeking Alpha) e insiders (Formulario 4 de SEC EDGAR, requiere `SEC_USER_AGENT`
  de contacto en `.env`). Clasificación de titulares léxica y transparente; LLM local
  opcional (Ollama) solo para afinar sentimiento, nunca sale del equipo.
- `terminal/alertas.py` + `terminal/notificador.py`: convierten ese contexto en
  avisos locales.
- `detect-secrets` y `pip-audit` en el grupo de desarrollo.
- `tests/test_reto.py`, `tests/test_alertas.py`, `tests/test_fuentes_web.py`.

### Cambiado
- Repositorio y paquete renombrados de `terminal-portafolios` a `actinver-terminal`
  (sin efecto funcional).

### Estado de pruebas
- `uv run pytest`: 63 pruebas en verde.

## [0.1.0] — 2026-09-22
- Primera versión funcional: libro de operaciones, importación CSV, vigencia de
  datos, universo verificado (Nasdaq Trader + BMV + Actinver), optimizador
  media-varianza (skfolio) con validación walk-forward y escenarios, interfaz local
  en `127.0.0.1:8765`, modo demo con datos sintéticos aislados.
