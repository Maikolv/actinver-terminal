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

### D-31 Precio en vivo del SIC con Alpaca (solo datos)
Contexto: el usuario pidió cambios «en tiempo real» con fuentes gratuitas y dentro de las reglas del Reto. No existe fuente gratuita autorizada para la BMV local; las emisoras del SIC siguen a su bolsa de origen por el tipo de cambio.
Decisión: adaptador `Alpaca` (barras diarias crudas y ajustadas; SIP con respaldo IEX) y flujo `terminal/tiempo_real.py` (WebSocket IEX, 30 símbolos, reconexión con espera creciente, respaldo REST). Solo dominios de datos; una prueba verifica que el código no contiene rutas de la API de operaciones. Las cotizaciones se guardan como `alpaca_vivo` y el cierre oficial las reemplaza. El motor recalcula «en vivo» sin consultar otros proveedores (evita agotar límites de ForexFactory/SEC).
Descartado: leer el simulador del Reto (reglamento §11) y extraer páginas de cotizaciones (condiciones de uso).

### D-32 Avisos por Telegram con detalle
Decisión: Telegram activo por defecto y solo envía si `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` existen. El mensaje móvil incluye motivo y acción sugerida de cada alerta (máx. 5) y recuerda que las órdenes se capturan a mano. `uv run terminal telegram` detecta el chat, lo guarda en `.env` y envía una prueba sin mostrar el token; la pestaña Alertas tiene «Enviar aviso de prueba». Se mantiene el silencio fuera del horario de la BMV.

### D-33 Comparador de modelos (HRP, CVaR, paridad de riesgo) con walk-forward
Contexto: la mejora nº 4 pedía evaluar más modelos de skfolio contra el walk-forward vigente y dejar activo el mejor fuera de muestra.
Decisión: `terminal/comparador_modelos.py` (`uv run terminal comparar-modelos`) corre modelo vigente, 1/N, inversa de volatilidad, mínimo CVaR 95 %, paridad de riesgo y HRP con el mismo universo, topes, ventana y regla de costos que `optimizador._walk_forward`; ordena por Sharpe fuera de muestra neto de costos y guarda JSON en `data/comparacion_modelos/`.
Honestidad de datos: la base real tiene 0 precios (sin proveedor configurado) y la demo es sintética, así que **no se declara ganador ni se cambia el modelo activo**; el ranking será concluyente solo con precios reales. El ranking aún no está conectado a `proponer()`: hacerlo requiere historia real.

### D-34 Cotización BMV confiable o «SIN PRECIO CONFIABLE»
Contexto: el usuario pidió no marcar ninguna fuente como tiempo real por su publicidad y no sustituir la cotización BMV en pesos por la de EE. UU. en dólares.
Decisión: interfaz `MarketDataProvider` (`terminal/cotizaciones.py`). Una cotización es confiable solo si una consulta real verificó ese instrumento exacto (moneda MXN, mercado local o SIC) y no está obsoleta. El estado REAL_TIME/DELAYED/EOD/UNKNOWN sale de la latencia medida. La conmutación entre fuentes solo ocurre si la otra fuente también tiene cobertura verificada. El precio de origen en USD (Alpaca/Tiingo) se muestra como «referencia externa». Las propuestas estadísticas siguen usando la historia de origen como aproximación del rendimiento del SIC, y el PRESENTE nunca la presenta como precio BMV.

### D-35 Conectores contratados por especificación, sin endpoints inventados
Decisión: `BmvLicensedProvider`, `LsegProvider` e `IceProvider` son conectores REST descritos por un JSON que el usuario copia de la documentación de su contrato (`config/proveedores/ejemplo_especificacion.json`). Sin contrato, especificación, URL o credencial quedan «pendiente», con la lista exacta de lo que falta, y no hacen ninguna petición. Un contrato por streaming requerirá un adaptador de flujo aparte.

### D-36 Webhook de TradingView como eventos
Decisión: `POST /webhook/tradingview` es la única ruta sin CSRF. Se autentica con un secreto en el cuerpo. Acepta solo POST de ≤ 10 KB, 30 por minuto, con Host local o de un túnel declarado. Valida símbolo, moneda, hora (≤ 300 s y no futura), duplicados (huella) y valores. Registra el precio con estado UNKNOWN y genera una alerta «REVISAR». No es un flujo de precios. Exponerlo requiere un túnel HTTPS que decide el usuario.

### D-37 Tiempos event_time / available_at y tres espacios
Decisión: migración versionada (`terminal/migraciones.py`, tabla `version_esquema`) que añade `event_time` y `available_at` a precios, tipo de cambio, eventos, operaciones, noticias, calendario macro e insiders, más la etapa de cada operación. `available_at` nunca se sobrescribe. La interfaz separa PASADO, PRESENTE y FUTURO. Los pronósticos viven en su propia tabla y se etiquetan como estimaciones. El saldo del portal se captura a mano, como valuación oficial.

### D-38 Investigación predictiva con prueba intacta
Decisión:
- División cronológica 70/15/15 con embargo e = max(H, mínimo) y purga por ventana de etiqueta.
- Walk-forward purgado en el entrenamiento; imputación, escalado, filtro de correlación (|r| ≥ 0.95, prioridad declarada) y PCA ajustados solo con el entrenamiento de cada pliegue.
- La validación elige la variante y calibra los intervalos. La prueba se usa una vez, y un reajuste posterior queda marcado `prueba_ya_vista`.
- Comparación con tres referencias simples. Si el modelo no las supera en error y en resultado neto de costos, no se emite recomendación.

Resultado con datos demo (sintéticos, sin valor para el mercado real): el modelo no superó a las referencias en H=1 ni en H=5.

### D-39 Reglas del Reto re-verificadas (23-sep-2026)
Decisión: práctica y competencia son carteras separadas; la competencia reinicia el saldo en 1 000 000 (§5). La regla de «5 acciones distintas» (§6) cuenta las compras confirmadas de acciones, FIBRAs y REIT en la competencia; los ETF no se cuentan hasta que el Comité lo confirme.

Sobre el límite del 50 % (§6/§7) se advierten dos lecturas antes de presentar una propuesta:
- **Crítica:** una compra individual mayor al 50 % del valor del portafolio.
- **Aviso:** una compra cuya posición resultante supere el 50 %.

Se incorpora la prohibición de automatización (§17): la terminal no entra al portal.

### D-40 Integridad temporal y de mercado en la base
Decisión: disparadores de SQLite, además de las validaciones en Python. Así, un error de ingesta futuro no puede colar una noticia conocida antes de publicarse, un dato marcado REAL_TIME sin latencia medida ni una serie SIC en USD.

### D-41 Inhibición direccional ante incertidumbre
Decisión: sin precio BMV confiable, o con noticias de alto impacto de signo opuesto en 24 h, las alertas stop-loss, toma de utilidad, caída, cambio brusco y rebalanceo no se disparan. Se emite una alerta de datos. Se configura en `[alertas] exigir_precio_confiable`.

### D-42 Veredicto con significancia
Decisión: «VENTAJA» exige un error menor y significativo (Diebold-Mariano con Newey-West, p < 0.05) frente a cada referencia, **y** un resultado neto mayor que el de las estrategias de referencia. Con índices reales de FRED, en H=5 el error fue menor pero no significativo frente al cambio cero (p = 0.126) → SIN VENTAJA DEMOSTRADA.

### D-43 backtrader como verificador externo
Decisión: se usa desde su clon local (GPL-3.0), sin incorporarlo al código MIT, para comprobar la contabilidad del backtest (títulos enteros, comisión + IVA, efectivo). Coincidencia exacta con los datos sintéticos y con los reales.

### D-44 Recursos que requieren autorización
Decisión: Kronos (torch + pesos de Hugging Face) y whisper (torch) quedan con interfaz y pruebas, sin descarga. Descargar torch, del orden de cientos de MB, requiere autorización explícita del usuario.

### D-45 Repositorio `reto-actinver`
Contexto: la instrucción nombra `reto-actinver`, que no existe localmente. Decisión: se trabaja sobre `actinver-terminal`, que es el repositorio del Reto, en la rama `ampliacion-integral`, sin renombrarlo.

### D-46 Pronóstico al cierre del Reto y barrera de decisión
Contexto: se pidió un pronóstico hasta el 13-nov en MXN que influya en el plan solo con ventaja demostrada. Decisión: horizonte dinámico de sesiones BMV y precios del SIC × tipo de cambio ya publicado. El pronóstico solo influye si, en la prueba final intacta y después de costos, supera a «sin cambio», a pesos iguales y a la estrategia actual (media histórica, como el optimizador), con DM p < 0.05 frente a cada referencia de error. Con los datos al 30-sep no la supera: se muestra «señal experimental: sin ventaja demostrada» y el plan sigue el método actual. Kronos no se añade sin una prueba medida que quepa en memoria y mejore fuera de muestra. Ver `docs/pronostico-reto.md`.

### D-47 Monitor de alertas en la nube
Contexto: avisos por Telegram con la PC apagada, sin tarjeta ni facturación. Decisión: Cloudflare Workers Free + D1 (1 cron cada 15 min, 12–21 h UTC, lun-vie) en `cloud-alerts/`; al exceder un límite falla, no cobra. La terminal sincroniza cada 10 min una carga mínima firmada (HMAC, nonce, ventana de 5 min, secuencia) que también es latido: mientras llega, la nube no envía (relevo sin duplicados). Fuentes en la nube: Alpaca IEX y FIX de Banxico; la BMV usa el último cierre sincronizado (EODHD da 20 consultas/día y son de la terminal). El optimizador no se duplica: la nube recibe el plan ya calculado.

### D-48 Movimientos públicos con SEC EDGAR (sin puntuación)
Contexto: se pidió un módulo tipo Dataroma de 13F e insiders. Decisión: fuente oficial SEC EDGAR (gratuita; User-Agent y ≤ 5 peticiones/s); Dataroma, WhaleWisdom, Quiver, GuruFocus y HedgeFollow no se conectan (sin API autorizada o de pago). Los movimientos son contexto: alertas materiales sin duplicados, peso 0 en la puntuación porque no hay evidencia fuera de muestra y el 13F del 3T-2026 vence el 16-nov-2026, después del Reto. Consultas «a una fecha» por hora de aceptación de la SEC.

### D-49 Mensajes de Telegram en lenguaje sencillo y plan que no conserva una propuesta dominada
Contexto: el usuario pidió mensajes concisos, para alguien sin la jerga, que solo digan qué hacer considerando todas las variables. Además, el 6-oct la regla de estabilidad (D: plan fijo, margen de 2 puntos) conservaba una propuesta con +0.9 % central y −19.7 % adverso frente a otra con +1.6 % y −5.9 %. Decisión: `/plan`, `/boletas` y el envío diario usan `terminal/mensaje_simple.py` (ventas antes que compras, precio límite, rango si el precio es aproximado, efectivo, captura vieja, reglas del Reto, evento macro de 48 h y rango al cierre); el formato completo queda en `/completo`, `/detalle`, `/boletas detalle` y `alertas.formato_plan = "completo"`. El plan cambia de propuesta si otra la domina (más central y ≥ 2 puntos menos de pérdida adversa), y antes de la apertura se aplica la regla entre sesiones. Las noticias y el calendario macro siguen siendo aviso, no entrada del optimizador.

### D-50 Criterio del plan: mayor ganancia (decisión del usuario, 5-oct-2026)
Contexto: decisión pendiente del 30-sep (la referencia rendía menos que 1/N fuera de muestra). El usuario decide: «prioridad, la mayor ganancia». El criterio «plusvalía» usaba la mediana al cierre (`central_p50`), que castiga la volatilidad: elegía «Máxima puntuación» (+1.3 % mediana, 12.4 % media anual, +12.2 % anual fuera de muestra) frente a «Máximo rendimiento» (+0.9 % mediana, 21.5 % media anual, +92.9 % anual fuera de muestra en 84 sesiones). Decisión: nuevo criterio `ganancia` = media anual usada × años que faltan, activado en el perfil; mismas reglas de estabilidad y dominancia (con la media en lugar de la mediana). Se informa el escenario adverso (≈ −19 %) en cada mensaje. No es una garantía: la validación fuera de muestra es corta (84 sesiones) y coincide con un periodo alcista de semiconductores.

### D-51 Precios del portal desde el PDF del participante
Contexto: 19 emisoras BMV del catálogo nunca tuvieron precio (cupo de EODHD). Decisión: `terminal precios-portal <pdf>` lee el PDF de la pestaña «Acciones» que arma el participante (nunca el portal): BMV se guarda como cierre del día con proveedor «archivo»; el SIC no se mezcla con la serie en USD y solo se compara con la referencia origen × tipo de cambio (5-oct: diferencia mediana 0.32 %). Se agregan al universo las 6 emisoras que el portal muestra y la terminal no tenía (B, BYND, ROKU, TWLO, WYNN, SIGMAF).

### D-52 El plan no sugiere operar si no supera a mantener la cartera (mismo método)
Contexto: con criterio «ganancia», el plan sugería rotar la cartera porque la propuesta tenía la mayor ganancia esperada entre las propuestas, pero sus escenarios usaban su validación walk-forward (+2.2 %) y la cartera actual otra medida. Medidas igual (pesos fijos, misma regla de media y volatilidad), la cartera actual esperaba +7.6 % y la propuesta +7.0 % al cierre. Decisión: cada propuesta guarda `frente_a_mantener` (ambas con el mismo método; sin comparación si menos del 90 % de lo invertido tiene historia). Se mide en dos ventanas de validación, la del walk-forward (3-jun a 28-sep: propuesta +5.8 % frente a +4.2 %) y las sesiones más recientes del mismo largo (8-jun a 1-oct: +7.0 % frente a +7.6 %), y cuenta la menos favorable para la propuesta, porque desplazar la ventana unos días cambiaba al ganador. Con criterio de ganancia, si la propuesta no supera a mantener por `margen_mejora_mantener` (1 punto) después de comisiones, el plan marca «mantener» en todo, no genera boletas y el mensaje lo explica con las dos cifras y sus escenarios adversos.

### D-53 Mandato de autonomía versionado
Contexto: el mandato solo existía en el chat. Decisión: `docs/mandato-autonomia.txt` guarda su texto exacto, extraído del mensaje que el usuario pegó el 23-sep-2026 (sha256 e3957ec1…). `docs/mandato-autonomia.md` registra su procedencia y su precedencia: ganan las restricciones posteriores, más estrictas. La confirmación del usuario de que es la versión vigente está pendiente.

### D-54 Validación con historia larga (V1) y horizonte del Reto
Contexto: la historia común era de 255 sesiones (EODHD gratis: 1 año de la BMV) y dejaba 87 sesiones fuera de muestra. Decisión (preregistro en `docs/historia-y-horizonte.md`, escrito antes de los resultados): se adopta el panel dinámico 168/21, con 1,099 sesiones fuera de muestra. Ninguna lente supera a 1/N con IC 90 %, así que propuestas y ranking no cambian. El horizonte de decisión sigue siendo el cierre del 13-nov.

### D-55 Probabilidad de subida experimental
Contexto: auditoría con Brier frente a la frecuencia base, recalibración isotónica y Platt, e IC por fechas. Resultado: en H = 1, 5 y 28 es peor que la frecuencia base; recalibrada solo la iguala. Decisión: queda marcada experimental y con menos prominencia (Telegram ya no la muestra por emisora). No es señal.

### D-56 Kronos sigue como candidato sin uso
Contexto: experimento completo con el protocolo previo (índices de FRED, mismas fechas y referencias, 5 muestras, contexto 400, lotes de 8; pico de 494 MB, 95 min). Resultado: MSE 40 % mayor que «sin cambio» a H = 1 y 2.3 veces mayor a H = 5; dirección 48 % y 43 %; Diebold-Mariano p = 1.0. Decisión: SIN VENTAJA DEMOSTRADA; no entra a pronósticos ni propuestas.

### D-57 Titulares: se conserva el léxico; búsqueda con BM25
Contexto: 161 titulares etiquetados, los mismos para todos los métodos. Decisión: el LLM local (Qwen 1.5B) no se integra: invierte 9 direcciones, tiene 37 % de precisión en «negativo» y cuesta 1 GB y 3.5 s por titular. No se agrega memoria conversacional: no se midió necesidad. La búsqueda de documentación pasa a BM25 (13/15 frente a 4/15); la semántica e5-small (12/15) no se adopta.

### D-58 Protocolo de robustez de parámetros
Contexto: se pidió estabilidad de parámetros, Monte Carlo por combinación, SPP y clústeres, y walk-forward anidado. Decisión: `terminal/robustez/` con preregistro (`docs/robustez.md`, commit previo a la ejecución). La cuadrícula de 150 combinaciones por universo y las 500 simulaciones por combinación no tienen omisiones. Resultado al 5-oct: mesetas amplias, del 66 % y 79 % de la cuadrícula. La selección anidada no supera a la configuración vigente fuera de muestra, así que no se cambian parámetros. La configuración vigente de máximo rendimiento es estable, pero no pasa el umbral de caída p5 (−20 %). Enmienda 1: «frágil» queda solo para pico aislado o inestable; lo «no aprobado» por riesgo se informa y la decisión es del usuario, por D-50.

### D-59 Se mantiene máximo rendimiento aceptando el riesgo de cola
Contexto: el protocolo de robustez marca la configuración de máximo rendimiento como «no aprobada» (caída p5 de −23/−24 % en simulación). Decisión del usuario (6-oct-2026): mantenerla. Se guarda en `ajustes_usuario.decisiones_usuario.acepta_riesgo_cola`, fuera del perfil para no forzar el recálculo. El plan por Telegram lo dice junto al aviso de riesgo.

### D-60 Mandato de autonomía, versión 2
Contexto: el usuario confirmó la versión 1 como base vigente y autorizó los cambios necesarios para la versión final (6-oct-2026). Decisión: `docs/mandato-autonomia-v2.txt` aplica los 9 puntos de la revisión como reemplazos exactos e incorpora dos restricciones posteriores (otras sesiones; boletas informativas). Queda autorizado el acceso por Tailscale Serve solo dentro de la red privada. La v1 se conserva intacta. El borrado de `CloudflareSpeedTest_duplicates_backup` sigue requiriendo confirmación expresa: la v2 lo exige y no se ejecutó.
