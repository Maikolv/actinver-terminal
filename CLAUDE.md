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

## Estado actual (2026-09-23, v0.3.0)

- 70 pruebas en verde (`uv run pytest`); Lighthouse escritorio 100/100/100, móvil 93/100/100.
- 4 propuestas (acciones/mixta × lente rendimiento/ajuste) con reglas del Reto
  (`config/reto.yaml`), μ global coherente (D-22), motor automático (`servicios.ciclo`),
  alertas con histéresis/enfriamiento y notificación de escritorio (`alertas.py`,
  `notificador.py`), contexto FF/SA/SEC/Barchart (`fuentes_web.py`), widget de
  TradingView en `/grafica/<id>`, simulación de cambios, universo del simulador.
- Reportes automáticos (`terminal/reportes.py`): `uv run terminal reporte preapertura|cierre|semanal` escribe
  `data/reportes/AAAA-MM-DD_<tipo>.md` (en `data/demo/reportes/` si el modo es demo); `scripts/programar_tareas.ps1`
  registra las tareas de Windows (08:00, 15:15, sáb 09:00). Suspendida/desactualizada ⇒ el reporte no recomienda.
- Docs con nombres pedidos: `docs/repos.md` (64 fichas), `fuentes.md`, `decisiones.md`
  (D-01 a D-30), `seguridad.md`, `matriz.md`, `diseno.md`; evidencia en `docs/13-evidencia.md`.
- No reintentes fuentes descartadas (D-16) sin una razón nueva. Otra sesión puede trabajar
  en paralelo en este repo (D-30): revisa `git log` y `git status` antes de commitear.

## Comandos

```bash
cd C:\Users\MIKE\Desktop\Repos\actinver-terminal
uv sync                      # entorno .venv (uv lo crea si falta)
uv run terminal demo         # datos sintéticos, base separada en data/demo/
uv run terminal actualizar   # descarga incremental respetando límites por proveedor
uv run terminal iniciar      # datos reales, http://127.0.0.1:8765
uv run terminal reporte cierre   # preapertura | cierre | semanal (--sin-actualizar para no consultar proveedores)
uv run pytest -q             # 70 pruebas
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
3. **`SEC_USER_AGENT` sin configurar** por defecto → la fuente de insiders queda
   inactiva hasta que el usuario ponga su contacto en `.env` (no es automatizable:
   es una declaración personal ante la SEC).
4. **Backtests de más modelos** (D-03/D-04 ya cubren media-varianza con skfolio):
   evaluar HRP, CVaR y risk parity de skfolio contra el mismo walk-forward y dejar
   el ranking automático si supera el actual fuera de muestra — ver `docs/matriz.md`.
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
