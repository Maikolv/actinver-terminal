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
arranque rápido y `docs/` para el diseño completo (numerado 00–13).

## Estado actual (2026-09-23)

- 63 pruebas en verde (`uv run pytest`).
- Commit `4ff11b7`: renombre a `actinver-terminal` + reglas del Reto Actinver 2026
  (`config/reto.yaml`, `terminal/reto.py`) integradas en el optimizador y en el
  cumplimiento de cartera + alertas de contexto (`terminal/alertas.py`,
  `terminal/notificador.py`, `terminal/fuentes_web.py`: calendario ForexFactory,
  noticias Seeking Alpha, insiders SEC EDGAR) + `detect-secrets`/`pip-audit` en dev.
- `docs/06-decisiones.md` tiene D-01 a D-20. Antes de cambiar algo ya decidido, léelo.
- `docs/10-fuentes.md` documenta qué fuentes están evaluadas y cuáles quedaron
  descartadas (D-16); no reintentes las descartadas sin una razón nueva.

## Comandos

```bash
cd C:\Users\MIKE\Desktop\Repos\actinver-terminal
uv sync                      # entorno .venv (uv lo crea si falta)
uv run terminal demo         # datos sintéticos, base separada en data/demo/
uv run terminal actualizar   # descarga incremental respetando límites por proveedor
uv run terminal iniciar      # datos reales, http://127.0.0.1:8765
uv run pytest -q             # 63 pruebas
uv run python scripts/verificar_universo.py --descargar   # re-verifica universo BMV/Nasdaq
```

Sin credenciales en `.env`, el modo real obtiene tipo de cambio de FRED pero las
propuestas quedan «suspendidas» hasta tener precios de un proveedor configurado o
importados por el usuario — es intencional (D-12), no un bug.

## Brechas conocidas / próximas mejoras (mayor impacto primero)

1. **Datos en tiempo real verdadero**: ninguna fuente configurada lo ofrece hoy
   (D-16, `docs/10-fuentes.md#tiempo-real`). Cerrar esto requeriría un proveedor de
   pago — **requiere decisión del usuario**, no se contrata solo.
2. **Cobertura completa de BMV/SIC**: EODHD da 20 peticiones/día gratis; el universo
   verificado puede ir por delante de lo que se puede refrescar a diario. Vigilar
   `docs/07-matriz-aplicabilidad.md` y considerar una cola de actualización que
   priorice los instrumentos con posición abierta o en una propuesta activa.
3. **`SEC_USER_AGENT` sin configurar** por defecto → la fuente de insiders queda
   inactiva hasta que el usuario ponga su contacto en `.env` (no es automatizable:
   es una declaración personal ante la SEC).
4. **Backtests de más modelos** (D-03/D-04 ya cubren media-varianza con skfolio):
   evaluar HRP, CVaR y risk parity de skfolio contra el mismo walk-forward y dejar
   el ranking automático si supera el actual fuera de muestra — ver `docs/07`.
5. **Reportes automáticos** (pre-apertura 08:00, cierre 15:15, semanal del Reto):
   no implementados aún; `scripts/programar_tareas.ps1` ya crea tareas programadas
   de Windows para `actualizar`/`respaldar`, faltaría una tercera tarea que genere
   y guarde el reporte (reutilizar `terminal/servicios.py` para el cálculo).
6. **CloudflareSpeedTest_duplicates_backup** y otros repos duplicados/mal ubicados
   detectados en `docs/08-inventario-repositorios.md`: pendiente de limpieza fuera
   de este repo (afecta a `Desktop/Repos`, no a `actinver-terminal`); dejar
   constancia en ese doc antes de borrar cualquier cosa, con respaldo o rama.

## Al cerrar cada sesión

Actualiza esta sección y `CHANGELOG.md` con: qué se construyó, qué mejoró (con
métrica: pruebas, retraso medido, cobertura del universo), qué sigue, y qué
necesita decisión del usuario (sección 7 del mandato: gastar dinero, cuentas o
tokens a su nombre, su sesión personal de Actinver, exponer la terminal fuera de
este PC, borrar trabajo no recuperable, o reglas del Reto que no se puedan
confirmar y cambien la estrategia).
