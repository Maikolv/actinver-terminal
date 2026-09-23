# 06 · Registro de decisiones

Formato: contexto → decisión → consecuencias. Fecha de todas: 2026-09-22.

### D-01 Repositorio central nuevo
Contexto: 63 repositorios con pilas y licencias heterogéneas. Decisión: crear `actinver-terminal` y depender solo de bibliotecas publicadas. Consecuencias: builds reproducibles (`uv.lock`), sin acoplar a código de terceros no mantenido.

### D-02 Un proceso Python + SQLite + HTML nativo
Contexto: uso local, un usuario. Decisión: FastAPI sirve API e interfaz estática; SQLite en `data/`. Alternativas descartadas: Node/React (cadena de build), Postgres/Supabase (servicio adicional, RLS innecesario sin multiusuario), Electron (peso). Consecuencias: arranque con un comando; sin cuentas ni autenticación (no hay acceso remoto).

### D-03 skfolio como motor de optimización
Contexto: se requiere optimización reproducible, restricciones por grupo, costos y validación temporal. Decisión: skfolio 1.3 (BSD-3). Descartadas: implementación propia con SciPy (más código a validar), Riskfolio-Lib (no presente localmente), backtrader (sin mantenimiento).

### D-04 Media-varianza con utilidad, μ contraída y Σ Ledoit-Wolf
Contexto: μ histórica es muy ruidosa. Decisión: `MAXIMIZE_UTILITY` con λ por perfil, `ShrunkMu` (James-Stein), `LedoitWolf`, regularización L2 γ=0.001, topes por activo y grupos. Consecuencias: pesos menos extremos; se informa la estabilidad.

### D-05 Validación walk-forward con costos y banda
Decisión: ventanas 504/63 sesiones, preselección de acciones dentro de cada ventana, costos de rotación descontados una vez por ventana, banda de 2 pp aplicada también en la simulación. Comparación con 1/N y con la cartera actual en el mismo periodo.

### D-06 El escenario ajusta μ solo en la propuesta final
Contexto: el usuario elige escenario base/adverso/favorable. Decisión: el escenario suma un ajuste anual explícito (−5 % renta variable en adverso, +3 % en favorable) a los rendimientos usados para estimar; la validación fuera de muestra usa siempre datos reales. Consecuencia: el escenario cambia la propuesta de forma visible sin contaminar la evaluación.

### D-07 Clase por verificación independiente, no por rótulo del PDF
Contexto: la sección «ETF's» del PDF repite las 146 acciones. Decisión: clasificar con Nasdaq Trader (bandera ETF, nombre del emisor), BMV (emisoras) y Actinver (fondos). FIBRA = clase propia (CBFI), fuera de «Solo acciones». AGNC = acción (REIT constituido como sociedad). Consecuencia: 0 de 146 símbolos rotulados como ETF son ETF.

### D-08 Validación por nombre del emisor
Contexto: GOLD y PARA hoy corresponden a otras empresas. Decisión: exigir coincidencia del nombre esperado; si no, estado `clave_reasignada` y exclusión. Consecuencia: evita valorar con precios de otra empresa.

### D-09 ETF candidatos con disponibilidad por confirmar
Contexto: el PDF no tiene ETF. Decisión: 10 ETF amplios verificados como ETF en Nasdaq Trader + SMARTRC (Actinver). Se incluyen por defecto con la advertencia visible «disponibilidad en el SIC por confirmar»; el usuario puede excluirlos. ANGELD y DIABLOI excluidos por apalancamiento/inversos.

### D-10 SIC valorado con el mercado de origen convertido a MXN
Contexto: no hay fuente gratuita de cotizaciones del SIC. Decisión: cierre del listado primario × tipo de cambio del mismo día. Consecuencia: aproximación documentada; la diferencia por spread se modela como costo.

### D-11 Sin simulación de tiempo real; datos sintéticos aislados
Decisión: el modo demo usa base separada, proveedor `demo_sintetico` y estado «sintético» que nunca cuenta como vigente; la calidad de datos de la propuesta es 0 en demo.

### D-12 Suspensión en lugar de degradación silenciosa
Decisión: sin tipo de cambio vigente no se valoran activos en USD; con menos de 5 instrumentos elegibles o historia común insuficiente, la propuesta se suspende con motivos. Las propuestas guardadas se marcan «no actual» si el perfil cambia o los datos envejecen.

### D-13 Costo promedio ponderado
Contexto: práctica habitual en México para acciones. Decisión: comisiones de compra al costo; de venta, restadas del ingreso; splits ajustan cantidad sin cambiar costo total.

### D-14 Libro inmutable
Decisión: no se borran operaciones; se anulan o corrigen creando un registro que referencia al anterior, con motivo y auditoría. Importaciones todo-o-nada con archivo original conservado.

### D-15 Seguridad local por defecto
Decisión: solo 127.0.0.1 (el CLI rechaza otro host), verificación de Host, CSRF de doble control, CSP sin `unsafe-inline`, límites de cuerpo y frecuencia, sin documentación OpenAPI expuesta. Ver [seguridad.md](seguridad.md).

### D-16 Proveedores y extracción permitida
Descartados: Stooq (desafío anti-bot), Yahoo (acceso automatizado restringido, 429), TradingView/Barchart/Seeking Alpha/Forex Factory/InsiderFinance sin API contratada (condiciones prohibitivas para extracción). Elegidos: FRED, Banxico, Tiingo, EODHD, CSV del usuario.

### D-17 Normalización de términos ambiguos del encargo
- «CAIO» → Capacidades, Arquitectura, Información, Operación (ver [00](00-diagnostico-caio.md)).
- «Mejor portafolio» → mayor puntuación por criterios visibles, no certeza.
- «Tiempo real» → solo si el proveedor lo ofrece y está contratado; hoy ninguno.
- Números sueltos y errores tipográficos de las listas del encargo → no se tratan como metas ni requisitos.
- Requisitos de sitio público → evaluados en la [matriz de aplicabilidad](matriz.md).

### D-18 Renombre a `actinver-terminal`
Contexto: el nombre `terminal-portafolios` no reflejaba que el uso inmediato es el Reto Actinver 2026. Decisión: renombrar paquete, carpeta y referencias en documentación. Consecuencias: ninguna funcional; solo nombres.

### D-19 Reglas del Reto Actinver como configuración, no como código
Contexto: capital, fechas, comisión, tope por emisora y mínimo de emisoras del Reto pueden cambiar de edición a edición. Decisión: `config/reto.yaml` (versionado, con la fuente y fecha de consulta) + `terminal/reto.py` como capa de lectura; regla no confirmada = `null` con aviso visible en la interfaz, nunca un valor inventado. Consecuencias: el optimizador (`optimizador.py`) aplica el tope de 50 % por emisora y el horizonte automático (sesiones hábiles hasta el cierre de la competencia) sin tocar código; `servicios.py` calcula `cumplimiento_reto` (mínimo de 5 emisoras, tope por emisora) sobre la cartera real y las propuestas.

### D-20 Contexto de mercado sin generar órdenes
Contexto: el encargo original menciona calendario macro, noticias e insiders como señales de apoyo. Decisión: `terminal/fuentes_web.py` consume solo vías explícitamente públicas y documentadas en su propio encabezado (feed de exportación de ForexFactory, RSS público de Seeking Alpha por emisora, Formulario 4 de SEC EDGAR con `SEC_USER_AGENT` de contacto obligatorio), con límite de frecuencia y sin sortear anti-bot ni paywalls. La clasificación de titulares es léxica y transparente por defecto; un LLM local opcional (Ollama, `OLLAMA_URL`) puede afinar el sentimiento de titulares de alto impacto sin que el texto salga del equipo. `terminal/alertas.py` y `terminal/notificador.py` convierten esto en avisos locales (nunca en operaciones automáticas).

### D-21 Dos lentes por universo (cuatro propuestas)
Contexto: el Reto premia el rendimiento absoluto, pero el inversionista tiene perfil y cartera propios. Decisión: cada universo se calcula con dos lentes: **máximo rendimiento esperado** (λ = 0.5, sin regularización, sin costo de salida desde la cartera actual, tope 20 % por activo ⇒ ≥ 5 emisoras) y **ajuste a su perfil y cartera** (λ del perfil, γ L2, costos frente a las posiciones, tope del perfil ≤ 50 % del Reto). La puntuación compara ambas con los mismos criterios; la agresiva muestra su riesgo (volatilidad, caída, p10) al lado. Consecuencias: 4 cálculos por ciclo (~20 s).

### D-22 μ global para optimizar y evaluar
Contexto: la preselección de acciones y la contracción de μ dentro del subconjunto producían un μ distinto al usado para comparar con la cartera actual (la lente agresiva salía con menor rendimiento esperado que la conservadora). Decisión: la propuesta final usa un μ global (James-Stein sobre todo el universo, con escenario) inyectado al optimizador (`MuFijo`) y el mismo μ mide rendimiento esperado y mejora neta. La validación walk-forward conserva la preselección dentro de cada ventana. Consecuencias: coherencia (prueba `test_lentes_cumplen_reglas_y_difieren`).

### D-23 Reglas del Reto sobre precios y costos
Decisión: con el Reto activo, (a) comisión del simulador 0.10 % + IVA a toda orden, más spread estimado; (b) precios **sin ajustar** por dividendos porque el Reto no los paga (§13); (c) horizonte = sesiones de la BMV hasta el 13 nov 15:00; (d) mínimo de deuda por horizonte corto desactivado (la regla de «horizonte corto ⇒ más deuda» es para inversión real, no para una competencia de 7 semanas); el perfil sigue decidiendo la deuda mínima en la lente de ajuste.

### D-24 Motor automático con recálculo condicionado
Decisión: hilo de fondo cada 15 min en horario de mercado y 60 min fuera; recalcula solo si hay datos nuevos, cambió el perfil, no hay propuestas o alguna quedó «no actual». Operaciones, importaciones y cambios de perfil disparan un ciclo inmediato. Un candado impide cálculos simultáneos entre API y motor. La interfaz consulta el estado cada 60 s y se refresca al terminar cada ciclo.

### D-25 Alertas: flanco de subida, histéresis y enfriamiento
Decisión: una alerta se dispara al pasar su condición de inactiva a activa, con enfriamiento de 6 h por (regla, clave); la deriva usa histéresis (5 pp / 3 pp) y exige mejora esperada neta de costos ≥ 0.5 %; los eventos puntuales (macro, insider, noticia) no se repiten. Fuera del horario de la BMV se registran pero no se notifican. Las notificaciones de un ciclo se agrupan en una sola. Cada alerta guarda motivo, datos, hora, fuente, acción sugerida y, si aplica, la lista de operaciones para «Simular cambio».

### D-26 Notificaciones sin dependencias
Decisión: toast nativo de Windows vía PowerShell (contenido en base64, sin interpolar texto en el script); correo SMTP y Telegram solo si el usuario los activa y configura en `.env`. Ningún mensaje incluye credenciales; los errores de Telegram no se registran porque su URL contiene el token.

### D-27 TradingView por widget oficial en página aislada
Decisión: la gráfica por activo es el widget embebible oficial en `/grafica/<id>`, con CSP propia que solo permite `s3.tradingview.com` y marcos de TradingView; la página principal conserva su CSP estricta. Se abre solo cuando el usuario lo pide (envía el símbolo a TradingView). No se extraen datos de TradingView.

### D-28 Universo del simulador importable
Decisión: el usuario puede importar la lista de instrumentos visible en el simulador; si existe, el universo del Reto se restringe a ella y el resto se excluye con motivo. Claves no reconocidas se listan pero no bloquean la importación.

### D-29 Rendimiento percibido
Decisión: el modo (demo/real) se inyecta en el HTML desde el servidor para que la cabecera no se desplace; la lista de 180 instrumentos se carga solo al enfocar el campo; una sola consulta SQL para últimas cotizaciones; cálculos de calendario memoizados; cliente HTTP perezoso (crear un contexto TLS por adaptador costaba ~300 ms en `/api/estado`).

### D-30 Trabajo concurrente de otra sesión
Contexto: una sesión paralela (Claude Sonnet 5) consolidó en commits (`4ff11b7`, `a04bafc`) parte del trabajo en curso y añadió `CLAUDE.md`, `CHANGELOG.md`, D-18–D-20 y variables en `.env.example`. Decisión: conservar sus aportes, integrarlos (CHANGELOG ampliado, referencias a documentos renombrados) y no reescribir su historial.
