# Changelog

Formato libre en español (inspirado en Keep a Changelog). Fecha = día del commit, hora de México.

## [0.4.0] — 2026-09-23

### Añadido
- **Precio en vivo para emisoras del SIC y ETF** (`terminal/tiempo_real.py`): WebSocket IEX de Alpaca (plan gratuito, 30 símbolos, solo datos), respaldo por consulta REST, persistencia cada 15 s como dato `tiempo_real` y recálculo automático de propuestas y alertas cada 5 min o ante movimientos ≥ 1 %.
- Adaptador `Alpaca` de barras diarias (crudas y ajustadas; SIP con respaldo IEX) como alternativa gratuita a Tiingo.
- Telegram con detalle (motivo y acción) por defecto cuando está configurado; `uv run terminal telegram` detecta el chat y prueba el envío; `uv run terminal alpaca` comprueba las claves.
- Botón «Enviar aviso de prueba» y estado de canales y del flujo en vivo en la interfaz; `/api/estado` informa `tiempo_real` y `notificaciones`.
- `tests/test_tiempo_real.py` (13 pruebas; 82 en total), incluida una que impide rutas de la API de operaciones de Alpaca.

### Cambiado
- Vigencia de datos `tiempo_real`: vigente ≤ 120 s; con mercado abierto, retrasado ≤ 20 min y vencido después; con mercado cerrado se evalúa como cierre de sesión.
- El cierre oficial reemplaza las cotizaciones en vivo del mismo día.

## [0.3.0] — 2026-09-23

### Añadido
- Reportes automáticos en Markdown (`terminal/reportes.py`, comando `terminal reporte preapertura|cierre|semanal`): Reto, motor, cartera con vigencia por posición, seguimiento (semanal), propuestas y alertas recientes. Una propuesta suspendida o desactualizada se reporta como tal y no emite recomendación; base vacía no inventa cifras. Se guardan en `data/reportes/` (o `data/demo/reportes/` en modo demo, sin mezclar datos sintéticos con reales) y quedan fuera de Git.
- `scripts/programar_tareas.ps1` registra tres tareas más: pre-apertura 08:00 y cierre 15:15 (lun–vie) y semanal (sáb 09:00).
- `tests/test_reportes.py` (7 pruebas; 70 en total).

## [0.2.0] — 2026-09-23

### Añadido
- Reglas del Reto Actinver 2026 como configuración versionada (`config/reto.yaml` + `terminal/reto.py`): capital 1 000 000 actipesos, práctica 28 sep–2 oct, competencia 5 oct–13 nov 15:00, comisión 0.10 % + IVA, ≥ 5 emisoras, ≤ 50 % por emisora, sin dividendos (sí splits), horario BMV 07:30–14:00 hasta el 2 nov y 08:30–15:00 desde el 3 nov. Regla no publicada = `null` con aviso «regla sin confirmar».
- Cuatro propuestas: «Solo acciones» y «Acciones + ETF + fondos», cada una con lente **máximo rendimiento** (agresiva, riesgo explícito, tope 20 % ⇒ ≥ 5 emisoras) y **ajuste a su perfil y cartera**.
- Horizonte automático = sesiones de la BMV hasta el cierre del Reto; precios sin ajustar por dividendos.
- Motor automático en segundo plano: adquisición → recálculo si hay datos nuevos / cambió el perfil / no hay propuestas → alertas; también se dispara tras operaciones, importaciones y cambios de perfil.
- Motor de alertas (`terminal/alertas.py`): deriva con histéresis (5 pp / rearme 3 pp) y mejora esperada neta de costos, stop-loss, toma de utilidad, caída desde máximo, evento macro USD/MXN, insider, noticia de alto impacto, dato vencido / fuente caída / propuesta suspendida. Enfriamiento, agrupación y silencio fuera de horario. Botón «Simular cambio».
- Notificación de escritorio de Windows sin dependencias (`terminal/notificador.py`); correo SMTP y Telegram opcionales vía `.env`.
- Contexto de mercado (`terminal/fuentes_web.py`): calendario ForexFactory (feed de exportación), titulares Seeking Alpha (RSS público por emisora), insiders SEC EDGAR Formulario 4 (requiere `SEC_USER_AGENT`), Barchart OnDemand (requiere contrato). Clasificación léxica; LLM local opcional (Ollama).
- Widget oficial de TradingView en página aislada `/grafica/<id>` con CSP propia.
- Simulación de cambios con títulos enteros, comisión del Reto y verificación de reglas.
- Importación de la lista de instrumentos del simulador (restringe el universo del Reto).
- Seguimiento: caída desde máximo y comparación con IPC (ACTIVAR), S&P 500 (IVV) y 60/40.
- Interfaz: pestañas Alertas y Mercado, franja de alertas en el resumen, tareas pendientes del Reto, cifras monoespaciadas, esqueletos de carga, punto de ruptura de tableta.
- `start.bat`, `scripts/escanear_secretos.py` (historial completo de Git), `detect-secrets` y `pip-audit` en desarrollo, `docs/repos.md` (64 fichas), `patches/README.md`.
- Pruebas: `test_reto.py`, `test_alertas.py`, `test_fuentes_web.py` (63 en total).
- `CLAUDE.md` raíz con mandato, estado y brechas para continuar entre sesiones.

### Cambiado
- Repositorio y paquete renombrados a `actinver-terminal`; renders del PDF en `_renders/` (fuera de Git).
- Documentos con nombre pedido: `docs/repos.md`, `fuentes.md`, `decisiones.md`, `seguridad.md`, `matriz.md`, `diseno.md`.
- El ajuste final usa un μ global (contracción sobre todo el universo) para optimizar y evaluar con el mismo estimador.
- Con el Reto activo, la comisión del simulador aplica a toda orden (incluidos fondos).
- Rendimiento: modo inyectado por el servidor, universo diferido, una consulta SQL para cotizaciones, calendarios memoizados, cliente HTTP perezoso.

### Seguridad
- Historial de Git y árbol sin secretos (escáner propio + `detect-secrets`); `pip-audit` sin vulnerabilidades conocidas.
- Informes crudos de Lighthouse fuera de Git (contienen el token CSRF efímero de la página).

## [0.1.0] — 2026-09-22
- Primera versión funcional: libro de operaciones, importación CSV, vigencia de datos, universo verificado (Nasdaq Trader + BMV + Actinver), optimizador media-varianza (skfolio) con validación walk-forward y escenarios, interfaz local en `127.0.0.1:8765`, modo demo con datos sintéticos aislados, botón para cambiar a datos reales, cartera demo de 1 000 000.
