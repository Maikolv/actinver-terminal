# Changelog

Formato libre en español (inspirado en Keep a Changelog). Fecha = día del commit, hora de México.

## [0.11.0] — 2026-09-29 (auditoría integral)

### Corregido
- **Seeking Alpha colapsaba todos los titulares de una emisora en uno:**
  - el enlace del RSS es genérico y servía como identificador;
  - ahora se usa el `guid` y el enlace real de la nota;
  - se descartan notas que no mencionan la emisora y se registran las otras emisoras mencionadas;
  - el tipo se clasifica como noticia, análisis o transcripción.
- **Titulares y cola de precios quedaban vacíos sin posiciones:**
  - titulares, insiders y la cola usan también las emisoras de las propuestas;
  - un ciclo sin emisoras ya no se reporta como «ok».
- **Cola de precios alfabética:**
  - el orden es cartera → propuestas → atrasadas (la más antigua primero) → nunca cargadas;
  - así rinden los cupos de EODHD (20 al día) y Tiingo.

### Añadido
- **«¿En qué puedo confiar hoy?»** (`/api/estado-informacion`, en Resumen): confirmado, estimado, vencido o falta, con la acción concreta.
- **Bloqueos:**
  - una captura del portal con posiciones sin precio bloquea propuestas, boletas y avisos de movimiento;
  - no se generan boletas con propuestas que tengan avisos.
- «Riesgos» advierte la validación corta (menos de 126 sesiones).
- El aviso «Posible movimiento» no se envía de noche (21:00–07:00): lo incluye el plan del día.
- Resumen rotula la cartera como «Confirmado» (captura del portal) o «Local» (registro de la terminal).
- Nueva guía para personas no técnicas: `docs/guia-rapida.md`.

## [0.10.0] — 2026-09-29

### Añadido
- **Plan del día por Telegram** (`terminal/resumen.py`): cada sesión hábil de la BMV a las 07:00 (CDMX, configurable en
  `resumen_matutino_hora`), una sola vez, con:
  - las órdenes de la propuesta mejor puntuada, con títulos enteros, precio y monto;
  - los cambios frente al plan del día anterior;
  - el porqué (criterios de la puntuación, motivo por emisora y riesgo principal).
  - `POST /api/resumen/muestra` envía una muestra en cualquier momento; los mensajes largos se parten en varios.
- **Cuenta del Reto según el portal** (`terminal/portal.py`, `GET/POST /api/portal/captura`):
  - el participante copia la tabla de su cuenta y la pega en «Mi cartera», con vista previa, cuadre y detección de duplicados;
  - la terminal nunca entra al portal (reglamento §17);
  - propuestas y alertas usan esa captura mientras sea la información más reciente;
  - el registro local (p. ej., la aportación virtual de práctica) se rotula aparte y nunca como saldo confirmado.
- **Alertas nuevas**, sin duplicados por clave y entregadas aunque la BMV esté cerrada:
  - `cambio_portal`: saldo, efectivo y títulos entre capturas;
  - `captura_pendiente`: recordatorio al cierre si no hay captura del día;
  - `plan_propuesta`: una sola vez por cada conjunto de órdenes distinto de la propuesta mejor puntuada.
- Cada aviso de Telegram y correo trae la hora de detección (CDMX) y la fuente de los datos.
- `notificar_correo` activo por omisión: solo envía si `SMTP_HOST` y `ALERTAS_CORREO_DESTINO` están en `.env`.
- La prueba de canales usa el formato real de las alertas.

### Corregido
- La captura del portal rechaza emisoras no reconocidas, efectivo ausente, descuadres mayores al 1 %, títulos inválidos
  y capturas anteriores a la última guardada. Si falta una cotización de la terminal, conserva el valor copiado del portal.
- Los recordatorios distinguen una captura anterior del registro local y la pantalla explica cuándo cambia la etapa.
- Si falla un canal de alerta, la terminal reintenta ese canal tras diez minutos mientras el aviso siga vigente;
  los canales que ya confirmaron la entrega no reciben copias.
- El tope de exposición en dólares del perfil se ignoraba cuando la preselección dejaba pocas acciones en pesos.

## [0.9.0] — 2026-09-29

### Añadido
- **Plan de órdenes en cada propuesta** (`ordenes`: total, compras, ventas, emisoras finales, costo y órdenes del SIC):
  - `consolidar_ordenes` elimina las posiciones menores a la banda de rebalanceo (2 %), que nunca llegarían a
    ejecutarse, y reparte su peso sin romper topes ni el mínimo de 5 emisoras;
  - el número de órdenes aparece en las tarjetas, en el detalle («Plan de órdenes») y al generar boletas.
- **`InfoselProvider` implementado con la API pública de Infosel Market v3**: último hecho BMV y SIC en MXN, hora del
  hecho en la Ciudad de México convertida a UTC, posturas de compra/venta, verificación de serie exacta y token rechazado
  explicado. Solo requiere `INFOSEL_URL_BASE` e `INFOSEL_API_KEY`.
- **Conectores contratados** `InfoselProvider` (APIs de Infosel / Infosel HUB, tiempo real BMV y BIVA) y `EdimexProvider`:
  - quedan «pendiente» con la lista exacta de lo que falta;
  - `BmvLicensedProvider` documenta que SiBolsa se consume vía los Web Services de Grupo BMV.
- **Importador de calificaciones de Seeking Alpha** (`calificaciones_sa`): se muestran en el Ranking como contexto fechado.

## [0.8.0] — 2026-09-24

### Añadido
- **Lente «Máxima puntuación»** (`acciones_puntuacion`, `mixta_puntuacion`):
  - busca en una rejilla de 12 candidatos (aversión × tope por emisora ≤ 50 %);
  - elige con la 1.ª mitad del periodo fuera de muestra y verifica con la 2.ª;
  - con datos reales: acciones 83.7 (verificación 90.8), mixta 87.1 (verificación 88.9).
- **Mercado de emisoras** en «Reto y perfil»: nacionales y extranjeras, solo nacionales (BMV) o solo extranjeras (SIC).
- **Pestaña Ranking** (`terminal/ranking.py`, `GET /api/ranking`):
  - ordena todas las acciones, FIBRA y ETF con ≥ 61 sesiones, sin depender de la cartera;
  - puntuación por percentiles (rendimiento a 20 y 60 sesiones, estabilidad y tendencia);
  - filtro por mercado; se refresca cada minuto.
- **Alertas diferidas:** las silenciadas fuera de horario se entregan (escritorio y Telegram) al abrir la BMV.

## [0.7.0] — 2026-09-24 (rama `boleta-decision`)

### Añadido
- **Boleta de decisión** (`terminal/boleta.py`, `/api/boletas`), para captura manual:
  - serie exacta, cantidad entera y precio límite;
  - costos con deslizamiento y caso de no ejecución;
  - efecto en efectivo y concentración, rango histórico y pérdida plausible;
  - liquidez, alternativa, invalidación y caducidad;
  - recálculo antes de presentarla y marcado manual de la ejecución con folio.
- **Órdenes:** estados enviada/pendiente/ejecutada/cancelada/expirada; «ejecutada» solo con la operación confirmada.
- **Precios:** calidad `STALE` y `ForeignMarketLicensedProvider`, que cubre la bolsa de origen y nunca la serie SIC.
- **Importadores** con plantilla: confirmaciones con folio, saldos del portal, notas de Seeking Alpha y exportación de InsiderFinance.
- **Calendario macro versionado** (`eventos_macro_versiones`) y `macro_conocido_en(T)`, que oculta el dato efectivo antes de publicarse.
- **Alertas:** prioridad, caducidad, impacto en MXN y ruptura de tesis (nivel de invalidación en la bitácora).
- **Banco de estrategias simples** (`terminal/investigacion/estrategias.py`) frente a efectivo, pesos iguales y comprar y mantener. Con índices reales de FRED: **VENTAJA NO DEMOSTRADA** (28 configuraciones registradas).
- **Documentos:** decision-workflow, data-providers e instrument-mapping; model-card, quant-methodology y actinver-rules actualizados.
- `tests/test_boleta.py` (15 pruebas; 146 en total).

## [0.6.0] — 2026-09-23 (rama `ampliacion-integral`)

### Añadido
- **Reglas del Reto versionadas** (`terminal/registro.py`, tabla `versiones_reglas`): aviso de discrepancia y los cálculos guardados conservan su versión. Las bases se re-verificaron el 23-sep (docs/actinver-rules.md).
- **Entidades nuevas:**
  - correspondencia de símbolos (MIC, serie, origen);
  - órdenes pendientes solo como referencia, sin efecto en la tenencia;
  - bitácora de decisiones humanas (método de LuxAlgo/trade-journal);
  - instantáneas de cartera, versiones de modelo y licencias de fuente.
- **Migraciones v2 y v3:**
  - `ingested_at` en todas las tablas de hechos;
  - **disparadores de SQLite** que rechazan una noticia disponible antes de publicarse, un precio disponible antes del evento, `REAL_TIME` sin latencia medida ≤ 15 s y una cotización BMV o SIC fuera de MXN;
  - autor y tipo de contenido de Seeking Alpha;
  - fecha de presentación y marca «NO CUBRE BMV» en insiders.
- **Control de clasificación** (`terminal/clasificacion.py`): los CFD (ficha de Dukascopy) y los criptoactivos (formato de ccxt) nunca valúan el Reto.
- **Alertas:**
  - inhibición de las alertas direccionales sin precio confiable o con noticias contradictorias, con una alerta de datos en su lugar;
  - **ficha de revisión**: qué ocurrió, datos, qué falta confirmar, costos, riesgos y opciones.
- **Investigación:**
  - variable de noticias sujeta a `available_at` y caída de 20 sesiones;
  - estrategias de referencia «mantener» y «pesos iguales»;
  - caída máxima, exposición y sensibilidad a costos (×0, ×1, ×2, ×5);
  - **Diebold-Mariano con Newey-West** y veredicto «SIN VENTAJA DEMOSTRADA».
- **Verificación cruzada con backtrader**, que coincide exactamente con el cálculo independiente. **Candidato Kronos** con verificación de disponibilidad.
- **Experimento con índices reales de FRED** (`scripts/experimento_indices_fred.py`): sin ventaja demostrada en H=1 ni en H=5.
- **Escenarios de estrés** (`terminal/escenarios.py`).
- **Política de tokens** (`scripts/indice_contexto.py`, índice con hashes y caché) y uso de `codebase-memory-mcp`.
- **Documentos:** initial-audit, actinver-rules, source-matrix con `sources/` (7 fichas), instrument-matrix, repository-adoption-matrix (63 repositorios), quant-methodology, model-card, token-budget, arquitectura y DESIGN.md.
- **Interfaz:** bitácora, órdenes pendientes, ficha en cada alerta, veredicto en FUTURO, aviso de reglas y la banda «DATOS SIMULADOS».
- `tests/test_ampliacion.py` (23 pruebas; 129 en total), incluidas pruebas que **deben fallar** ante una noticia futura en el pasado, un precio de EE. UU. como serie SIC o un dato de cierre marcado como tiempo real.

## [0.5.0] — 2026-09-23

### Añadido
- **Proveedores intercambiables** (`terminal/cotizaciones.py`):
  - Interfaz `MarketDataProvider`, con `BmvLicensedProvider`, `LsegProvider` e `IceProvider` (por especificación del contrato; hoy pendientes), `ManualOrCsvProvider`, `DemoProvider`, `EodhdBmvProvider` y `ReferenciaOrigenProvider`.
  - Registro de cotizaciones con proveedor, símbolo de origen y normalizado, bolsa, precio, moneda, hora del evento, hora de recepción, latencia declarada y medida, y estado REAL_TIME/DELAYED/EOD/UNKNOWN.
  - Caché, límite de consultas, métricas de fallos, reconexión, obsolescencia, conmutación solo con cobertura verificada y «SIN PRECIO CONFIABLE».
- **Cobertura por símbolo:** `uv run terminal cobertura`, botón «Verificar cobertura» y `docs/cobertura.md`.
- **Webhook de TradingView** (`TradingViewAlertReceiver`): secreto, símbolo, moneda, hora, duplicados y valores atípicos; `uv run terminal webhook-secreto`.
- **Migraciones versionadas** con `event_time` / `available_at` y etapa de cada operación (práctica o competencia, con saldo reiniciado).
- **Pestaña Pasado · Presente · Futuro:**
  - Hechos con su disponibilidad.
  - Precio BMV frente a referencia externa y a la valuación estimada.
  - Captura del saldo del portal.
  - Pronósticos etiquetados como estimaciones.
- **Investigación predictiva** (`terminal/investigacion/`, `uv run terminal investigar`, `docs/investigacion.md`):
  - División 70/15/15 con embargo y purga.
  - Walk-forward purgado; filtro de correlación, PCA y Ridge ajustados solo con el entrenamiento.
  - Prueba intacta y registro de experimentos.
  - Tres referencias simples; métricas de error, calibración, estabilidad, rotación y resultado neto.
  - Pronósticos con resultado observado posterior.
- **Reglas del Reto:**
  - Cinco acciones operadas.
  - Advertencia de compra mayor al 50 % en propuestas y simulaciones.
  - Comisión 0.10 % + IVA desglosada; ganancia absoluta y porcentual con comisión de salida estimada.
- **Alertas nuevas:** cambio brusco, concentración, falta de cinco acciones, diferencia con el portal, pérdida máxima propia, evento corporativo, deterioro del modelo y eventos de TradingView. Todas invitan a «REVISAR» e incluyen cálculo e incertidumbre.
- **Documentación y ejemplos:** `ejemplos/` (CSV y mensaje de alerta ficticios) y `docs/proveedores.md`.
- **Pruebas:** `tests/test_monitor.py` y `tests/test_investigacion.py` (22 pruebas; 106 en total).

### Cambiado
- Los `INSERT` a tablas existentes nombran sus columnas: requisito para las columnas nuevas.
- Los textos de acción de las alertas dejaron de sugerir vender o comprar; ahora invitan a revisar.

## [0.4.0] — 2026-09-23

### Añadido
- `uv run terminal comparar-modelos`: walk-forward de modelo vigente, 1/N, inversa de volatilidad, mínimo CVaR, paridad de riesgo y HRP (D-33); sin ganador con datos demo. `tests/test_comparador_modelos.py` (2 pruebas; 84 en total).
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
