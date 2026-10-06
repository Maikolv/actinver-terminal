# Changelog

Formato libre en español (inspirado en Keep a Changelog). Fecha = día del commit, hora de México.

## [0.21.0] — 2026-10-05 (criterio «mayor ganancia» y precios del portal)

### Añadido
- **Criterio del plan `ganancia`** (D-50, decisión del usuario): elige la propuesta con mayor ganancia media esperada al cierre del Reto (media anual × años que faltan), no la mediana, que castigaba la volatilidad. Activado en el perfil y disponible en «Reto y perfil». El plan de Telegram muestra el promedio, lo más común y el mal escenario.
- **`terminal precios-portal <pdf>`** (`terminal/precios_portal.py`, D-51): lee el PDF de la pestaña «Acciones» que arma el participante. Las BMV se guardan como cierre del día (proveedor «archivo»). El SIC solo se compara con la referencia origen × tipo de cambio, sin mezclar MXN con la serie en USD. El 5-oct: 43 BMV importadas, diferencia mediana del SIC 0.32 %. Las BMV del catálogo sin precio pasan de 19 a 6.
- **6 emisoras del portal que faltaban** (`scripts/incorporar_acciones_portal.py`): B (Barrick), BYND, ROKU, TWLO, WYNN y SIGMAF A. Universo 236, catálogo 233.

### Pruebas
- 4 nuevas: `tests/test_precios_portal.py` (3) y el criterio `ganancia` en `tests/test_referencia_plan.py`.

## [0.20.0] — 2026-10-05 (fondos del portal, mensajes sencillos, auditoría)

### Añadido
- **Fondos del simulador (capturas del 5-oct):** ACTIRVT (B, renta variable, venta anual) y PROTEGE (B-1, deuda, diaria) en el universo, en `config/fondos_actinver.csv` y en el catálogo. Se reimportaron las hojas oficiales ya guardadas para asignarles NAV del 28-sep al 2-oct. Ahora hay 25/25 fondos con precio y un universo de 230. `config/simulador_etf.csv` pasa a `config/simulador_portal.csv` (ETF y fondos vistos en el portal).
- **Mensajes de Telegram en lenguaje sencillo** (`terminal/mensaje_simple.py`, D-49):
  - `/plan` y el envío diario dicen solo qué hacer: vender primero, luego comprar, con precio límite;
  - si el precio es aproximado, dan el rango para revisarlo en el portal;
  - avisan si el efectivo no alcanza sin las ventas, si la captura está vieja o si se rompe una regla del Reto;
  - incluyen el próximo evento macro de alto impacto (48 h) y el rango esperado al cierre del Reto.
- **Boletas sencillas:** `/boletas` en el mismo formato, con las ventas primero. El formato técnico sigue en `/completo`, `/detalle` y `/boletas detalle`; `alertas.formato_plan = "completo"` restaura el envío anterior.
- **Auditoría** `docs/auditoria-2026-10-05.md`:
  - noticias y macro: qué entra al portafolio (nada) y qué entra como aviso;
  - 19 emisoras BMV sin ningún precio por el cupo de EODHD;
  - fondos con 5 sesiones de historia;
  - decisiones pendientes.

### Corregido
- **El plan del día ya no conserva una propuesta dominada:** cambia si otra tiene más escenario central y al menos 2 puntos menos de pérdida adversa. El 6-oct era +0.9 %/−19.7 % frente a +1.6 %/−5.9 %. Antes de la apertura aplica la regla entre sesiones.

### Pruebas
- 11 nuevas: `tests/test_mensaje_simple.py` (8), 2 en `tests/test_referencia_plan.py` y `test_fondos_del_portal_del_simulador` (25 fondos).

## [0.19.1] — 2026-10-05 (plan del día estable)

### Corregido
- **El plan del día saltaba de propuesta con los precios en vivo.** Con el criterio «plusvalía», el plan elegía la propuesta con mayor escenario central, y esa estimación cambia con cada precio. El 5-oct, a la apertura, una diferencia de ruido (+0.9 % frente a +1.3 %) cambiaba toda la cartera del plan.
- **Regla nueva (`servicios._fijar_referencia`):**
  - la propuesta elegida al inicio de la sesión queda fija toda la sesión, con su misma versión;
  - si esa versión caduca por un recálculo, se usa la versión nueva de la misma propuesta, y mientras se recalcula el plan espera en vez de saltar a otra;
  - entre sesiones, solo cambia si otra la supera por 2 puntos de escenario central (o 5 de puntuación);
  - cambiar el criterio del perfil vuelve a elegir.
- **Pruebas:** 5 nuevas (`tests/test_referencia_plan.py`).

## [0.19.0] — 2026-10-01 (movimientos públicos: 13F e insiders con SEC EDGAR)

### Añadido
- **Módulo `terminal/movimientos/`, sección «Movimientos públicos»** ([docs/movimientos-publicos.md](docs/movimientos-publicos.md)), con fuente oficial SEC EDGAR:
  - Form 4 de las emisoras del SIC de su cartera, propuestas y seguimiento;
  - 13F de 8 gestores con CIK verificado.
- **Cada fila trae:** documento original, fechas separadas (operación o corte, publicación con hora de aceptación, y cuándo la conoció la terminal) y una explicación de sus límites.
- **Form 4:** distingue compra o venta discrecional (P/S) de adjudicación, ejercicio, retención de impuestos, donación, plan 10b5-1 y venta tras ejercicio el mismo día; también titularidad directa o indirecta y relación del declarante.
- **13F:** clasifica nueva posición, aumento, reducción, salida o sin cambio. Advierte que el cambio se infiere de dos fotografías trimestrales.
- **Casos difíciles con documentos reales:**
  - 4/A sin duplicar y con el original marcado «corregido por»;
  - 13F/A NEW HOLDINGS y RESTATEMENT aplicados solo desde su publicación;
  - split ajustado con `eventos_corporativos`, o «no comparable» si no está registrado;
  - CUSIP con varias clases sin atribuir;
  - VALUE declarado en miles reescalado y anotado (Baupost y Duquesne).
- **Grupos:** cartera, propuesta, seguimiento, operable en el Reto, fuera del catálogo y sin identificar. El precio del Form 4 en pesos se etiqueta «referencia EE. UU. × tipo de cambio; no es cotización del SIC».
- **Lista de seguimiento** (`seguimiento`), con API `POST/DELETE /api/seguimiento`.
- **Alertas «movimiento_publico»**, solo nuevas y materiales y sin duplicados:
  - compra discrecional ≥ 100 000 USD;
  - venta discrecional ≥ 1 000 000 USD;
  - nueva posición o salida en 13F.

  Siempre como contexto: no crean órdenes ni boletas.
- **Reporte diario, Telegram y línea de comandos:** sección fechada en el reporte, `/movimientos` en Telegram y `uv run terminal movimientos actualizar|resumen`.
- **Peso en la puntuación: 0.** No entra a la puntuación (no hay evidencia fuera de muestra). El 13F del 30-sep-2026 vence el 16-nov-2026, después del cierre del Reto.

### Cambiado
- **Consulta de Form 4:** la de `fuentes_web.SecEdgar` queda sustituida por el módulo nuevo (incremental, ≤ 5 peticiones/s, reintentos ante 429 o 5xx).
- **Migraciones 8 y 9:** tablas `mp_*` y `seguimiento`, y corrección de la escala del valor en documentos ya guardados.

### Verificado
- **Primera carga real:** 614 consultas a la SEC en 2 min 48 s (501 Form 4 y 25 13F). La segunda pasada hace 37 consultas y no repite documentos.
- **Pruebas:** 14 nuevas (`tests/test_movimientos.py`) con documentos reales de la SEC en `tests/fixtures/sec/`. Suite: 299 de Python y 19 del Worker en verde.

## [0.18.0] — 2026-10-01 (monitor de alertas en la nube, Cloudflare Workers Free)

### Añadido
- **`cloud-alerts/`: monitor independiente en Cloudflare Workers con D1**, en el plan gratuito y sin tarjeta. Envía avisos por Telegram aunque la PC esté apagada:
  - movimientos de posiciones SIC (Alpaca IEX × FIX, etiquetado como referencia y no como precio del SIC);
  - variación estimada de la cartera;
  - condiciones del plan validado;
  - cartera sin sincronizar, que además suspende compra y venta;
  - fallas persistentes de datos y posibles splits no registrados;
  - un resumen diario antes de la apertura de la BMV.
- **Relevo sin duplicados.** La terminal sincroniza cada 10 min, y esa sincronización funciona como latido. Mientras llegue, la nube no envía nada; tras 20 min sin latido toma el relevo. Cada aviso tiene una clave única en D1. La nube solo usa `sendMessage` y no lee el chat, así que no compite con el bot local.
- **Sincronización segura (`terminal/nube.py`).** Viaja la carga mínima (~11 KB), firmada con HMAC-SHA256 y con:
  - ventana de 5 min;
  - nonce de un solo uso;
  - secuencia creciente;
  - límite de 64 KB y validación estricta (cualquier campo desconocido se rechaza).

  Nunca suben la base, `.env`, claves, costos ni documentos del portal.
- **Estado en la terminal.** En «Alertas» → «Monitor en la nube»: activo o inactivo, última sincronización y ejecución, próxima revisión, quién envía las alertas y por qué se suspende cada una. También están `uv run terminal nube estado|sincronizar|prueba|carga|secreto`, `GET /api/nube/estado` y `POST /api/nube/sincronizar`.
- **Despliegue.** `cloud-alerts/scripts/desplegar.py` crea la D1, migra, despliega y carga los secretos desde `.env` sin imprimirlos; `--desactivar` quita el cron.
- **Pruebas.** 19 del Worker (`npm test`, con D1 simulada sobre `node:sqlite`) y 7 de Python (`tests/test_nube.py`). La firma usa un vector compartido entre Python y JS, y la carga real pasa el validador del Worker.

### Pendiente
- Desplegar requiere iniciar sesión en Cloudflare: `npx wrangler login`, lo hace el usuario. Hasta comprobar un aviso real enviado desde la nube, el acceso permanente no se da por completado.

## [0.17.0] — 2026-10-01 (pronóstico al cierre del Reto, con barrera)

### Añadido
- **Pronóstico al cierre del Reto** (`terminal/investigacion/reto_pronostico.py`, [docs/pronostico-reto.md](docs/pronostico-reto.md)). Además de 1 y 5 sesiones, emite un horizonte dinámico: sesiones de la BMV desde la última sesión cerrada hasta el 13-nov (31 el 30-sep). Todo va en pesos: el SIC se multiplica por el USD/MXN de su fecha, y solo si ya estaba publicado a la hora de emisión. Cada pronóstico guarda el precio base, la estimación, el rango 10–90 %, la probabilidad de subida, la fecha de emisión, el último cierre usado, la fecha objetivo y la versión del modelo (migración 7).
- **FUTURO en «Boletas e historial»** separa tres cosas:
  - cierre OBSERVADO;
  - ESTIMACIÓN al objetivo;
  - ESCENARIOS 10/90 %.

  Muestra cada emisora y la cartera de la captura del portal; si no hay captura, avisa «Cartera NO conciliada». También muestra:
  - la comparación de cada propuesta con el pronóstico: neto de comisión + IVA, exposición al SIC con tipo de cambio, reglas del Reto y catálogo del simulador;
  - los cambios frente a la emisión anterior;
  - la calidad por mercado (BMV y SIC) y la calibración;
  - las emisoras sin historia suficiente o sin precios, que no se ocultan.
- **Barrera verificable.** El pronóstico solo puede influir en compras, ventas o boletas si cumple todo esto:
  - la prueba final está intacta y es suficiente;
  - su error es menor que el de cada referencia, con Diebold-Mariano p < 0.05;
  - su resultado neto de costos es mejor que mantener, que pesos iguales y que la **estrategia actual** (nueva referencia: media histórica, como el optimizador);
  - no hay deterioro.

  Si no, aparece «señal experimental: sin ventaja demostrada» y el plan sigue el método actual. Una prueba comprueba que el plan, las boletas y el optimizador no leen los pronósticos.
- **Telegram y reporte.** Nuevo comando `/pronostico`, botón «Enviar pronóstico por Telegram», sección en el reporte diario, `uv run terminal pronostico`, `GET /api/pronostico` y `POST /api/pronostico/telegram`.
- **Emisión automática.** Una vez por sesión cerrada, en segundo plano: unos 140 s y 0.36 GB de memoria pico. Se desactiva con `[investigacion] emitir_diario = false`.
- **Métricas nuevas.** Calibración por tramos, error y dirección por mercado, días de prueba y lista de historia insuficiente.

### Cambiado
- **Rango por emisora.** Los residuos se estandarizan con la volatilidad de 60 sesiones × √H. Antes, un bono (AGG) y una acción volátil recibían el mismo rango.
- La línea de comandos escribe en UTF-8: la consola de Windows fallaba con emojis.

### Resultados reales (datos al 30-sep, 130 instrumentos)
- **SIN VENTAJA DEMOSTRADA** en 1, 5 y 31 sesiones:
  - el error relativo a «sin cambio» es de 1.000, 1.001 y 1.009;
  - Diebold-Mariano da p = 0.45, 0.63 y 0.72;
  - el neto del modelo es −35.4 %, −4.4 % y −0.0 %, frente a +8.8 %, +12.6 % y +4.5 % de mantener.
- **La probabilidad de subida está mal calibrada.** Cuando estimaba ≥ 70 %, la emisora subió el 49 % de las veces. La terminal y Telegram lo advierten.
- **Kronos no se añadió**: no hay una prueba medida que quepa en memoria y mejore fuera de muestra.
- **Pruebas:** 11 nuevas (`tests/test_pronostico_reto.py`).

## [0.16.1] — 2026-09-30 (boletas coherentes con el plan)

### Corregido
- **Boletas invalidadas al instante por punto flotante:** 7,994 × 14.91 ÷ 14.91 = 7,993.999… hacía «cambiar la cantidad» al recalcular. La boleta guarda ahora la acción y el monto originales, y redondea con tolerancia. En el plan del 1-oct faltaban ALPEK y FIBRAPL 14.
- **Las boletas «investigar» del SIC perdían su banda de referencia al recalcular.**
- **«Mantener» ya no se presenta como «investigar»** cuando falta cotización confiable.
- **Venta total en el SIC:** la guía indica los títulos que se tienen (LLY 1, JNJ 5), no los que resultan de dividir entre el precio máximo de la banda.

## [0.16.0] — 2026-09-30 (capturas de pantalla del portafolio)

### Añadido
- **Capturas de pantalla en «Mi portafolio Actinver».** Se arrastran, se eligen o se pegan con Ctrl+V. El OCR de Windows (español) las lee en esta PC, en un proceso aparte (sus bibliotecas chocan con las de scipy), sin guardar ni enviar las imágenes. El texto resultante pasa por la misma vista previa y confirmación que el texto pegado.
- **Robustez frente al OCR:**
  - dos lecturas (tamaño original y ampliada) que se combinan;
  - montos reconstruidos con sus centavos («$611.62509» → 611,625.09) y confusiones del «$» (3, 5, S, «SI» = «$1») resueltas por coherencia de la fila: costo ÷ costo unitario ≈ títulos y precio ≈ costo;
  - un título ilegible se deduce del costo;
  - encabezados por aproximación y filas ancladas en «Ver Detalle»;
  - «Ver lo que leyó el OCR» muestra la lectura tal cual.
- Paquetes `winrt-*` (MIT) solo en Windows.

### Seguridad
- Una captura cuyas posiciones difieren más de 1 % de «Inversiones» del portal ya no se puede guardar.
- Si no se lee la «Valuación total», se calcula con el resumen del portal y no con las filas leídas, para que el cuadre sí detecte un título o precio mal leído.
- Límite de 30 MB solo para la ruta de capturas; el resto sigue en 1 MB.

## [0.15.1] — 2026-09-30 (criterio «mayor plusvalía» y tabla real del portal)

### Añadido
- **Criterio del plan de acción** en «Reto y perfil». «Máxima puntuación» queda por omisión; «Mayor plusvalía esperada al cierre del Reto» elige la propuesta con mayor ganancia esperada (escenario central) y declara su riesgo (escenario adverso). Lo usan por igual el plan de acción, Telegram, las boletas y la alerta «Posible movimiento».

### Corregido
- **Tabla de posiciones del portal:** la columna «Valor al Costo» es el costo unitario; antes se tomaba como valor de mercado.
- **`/plan` y la muestra después del cierre** muestran la próxima sesión de la BMV (por ejemplo, jue 01-10) en vez de la de hoy.
- **Venta total en el SIC** (objetivo 0 %): la referencia indica todos los títulos que se tienen.

## [0.15.0] — 2026-09-30 (plan de acción, «Mi portafolio Actinver», interfaz simplificada, Telegram)

### Añadido
- **Plan de acción** (`terminal/plan_accion.py`, `/api/plan-accion`, primera sección de la interfaz). Para cada instrumento indica comprar, vender, mantener o «decisión pendiente», con cantidad, precio límite, monto, peso actual y objetivo, fuente y fecha del precio, motivo e invalidación, ordenado por prioridad. Antes de calcular verifica las reglas: fecha de consulta de las bases, comisión, al menos 5 emisoras, máximo 50 % y catálogo del simulador. Sin saldo confirmado del portal, sin cotización confiable (el SIC es referencia) o sin efectivo, la decisión queda pendiente y dice qué falta; las compras se limitan al poder de compra confirmado, en orden de prioridad.
- **«Mi portafolio Actinver»** (antes «Mi cartera»). Reconoce el recuadro «Tu inversión» del portal (Valuación Total Ahora, Inversiones, Poder de compra, Movimientos por liquidar) más la tabla de «Ver detalle de mi inversión». El cuadre incluye lo por liquidar (migración 6). La vista previa muestra diferencias frente a la captura anterior y al registro local y avisa de duplicados; se confirma con «Confirmar y guardar mi portafolio». Muestra la hora de la última actualización. No existe integración oficial: el simulador no ofrece API y el reglamento §17 prohíbe programas en el portal.
- **Telegram:** el plan del día incluye las propuestas con máxima puntuación (desglose, rendimiento esperado, rango, validación fuera de muestra frente a pesos iguales), cuál alimenta el plan y por qué, la de mayor rendimiento esperado cuando es otra (con la diferencia de riesgo) y un resumen de compras, ventas, mantener y pendientes. Nuevos comandos `/detalle` y `/propuestas`, y enlace privado de Tailscale. Sin cuenta confirmada no da órdenes con títulos.

### Cambiado
- **Navegación:** cinco secciones principales (Plan de acción, Mi portafolio Actinver, Propuestas, Alertas, Reto y perfil). Boletas e historial, Ranking, Mercado, Datos y fuentes y Ayuda pasan a «Más». La comparación de lentes que se repetía en el resumen se quitó de allí; sigue en «Propuestas». El registro local y la importación quedan en una sección avanzada. No se borró ningún dato.

## [0.14.1] — 2026-09-30 (conciliación de efectivo e invertido; horario en el plan del día)

### Añadido
- **Alerta «Diferencia con el portal»:** ahora compara el efectivo y lo invertido además del total, cada uno en puntos del valor del portal. Con la captura de las 14:45 el total difería 0.49 % y no alertaba, pero el efectivo difería +77.4 % y lo invertido −61.5 %. Nuevas columnas `invertido` y `por_liquidar` en `saldos_portal` (migración 5), con campos en el formulario y un desglose en «Presente».
- **Plan del día por Telegram:** indica a qué hora consultar el portal (la apertura: 07:30, o 08:30 desde el 3-nov) y a qué hora retirarse (cierre + 15 min: 14:15, o 15:15), además de recordar que las órdenes limitadas vencen al cierre y que hay que copiar la cuenta. El 13-nov avisa que cierra el Reto.

## [0.14.0] — 2026-09-30 (auditoría: horario BMV, escenarios, alertas, respaldos, lanzador)

### Corregido
- **Horario de la BMV.** `exchange_calendars` fija XMEX en 08:30–15:00 todo el año; las bases del Reto dicen 07:30–14:00 hasta el 2-nov-2026. Entre 14:00 y 15:00 la terminal creía abierta la bolsa y no daba por cerrada la sesión; de 07:30 a 08:30 la creía cerrada. `vigencia.apertura_sesion` y `cierre_sesion` usan ahora `horario_bmv` de `config/reto.yaml`, y los festivos siguen saliendo del calendario.
- **Escenarios demasiado estrechos.** Usaban la volatilidad dentro de muestra de pesos ya optimizados, sesgada a la baja: en «Mixta · Ajuste», 16.6 % frente a 42.5 % fuera de muestra, con un adverso de −2.8 % en vez de −11.7 %. Ahora se toma la mayor volatilidad y la menor media entre dentro y fuera de muestra; el escenario informa qué fuente usó.
- **Media robusta en el optimizador.** Cada activo acota sus saltos de un solo día a máx(10 %, 5 σ robusta) al estimar la media; la covarianza sigue usando la serie completa. MRNA (+175 % el 19-ago) salió de las propuestas principales, donde tenía 11.9 %.
- **Alertas «Posible movimiento» acumuladas.** Cada recálculo dejaba otra como «nueva»; ahora la última reemplaza a las anteriores.
- **El Ranking mostraba instrumentos que el simulador no ofrece** (QQQ era 5.º). Ahora se filtra por el catálogo del simulador, como las propuestas, y avisa cuántos omite.
- **El iniciador no arrancaba la terminal si fallaba Tailscale.** Ahora arranca en local y avisa que el acceso remoto no está activo.
- **Precio SIC sin marcar.** En «Propuestas» y en la simulación, las filas del SIC ahora llevan «*» (referencia: bolsa de origen × tipo de cambio) y «≈» en los títulos.
- **Boletas.** Etiqueta explícita por estado (Capturable, Solo guía, Invalidada, Vencida, Descartada, Ejecutada); las capturables van primero y las demás se atenúan. En móvil, las filas pasan de más de 142 px a 80–99 px.

### Añadido
- Respaldo diario verificado de la base desde el ciclo del motor (`data/respaldos`, 14 copias). Antes no existía ningún respaldo.
- Riesgo «No supera a la referencia simple» cuando la propuesta rinde menos que 1/N fuera de muestra.
- `config/reto.yaml`: bases re-verificadas el 30-sep; el criterio es «mayor ganancia absoluta».

## [0.13.0] — 2026-09-30 (auditoría integral)

### Corregido (crítico)
- **Splits sin ajustar en el Reto.** Para excluir dividendos, que el Reto no paga, se usaba el cierre sin ajustar. Eso también dejaba los splits sin ajustar, aunque las bases dicen que sí se replican. El *reverse split* 1:10 de FUBO (24-mar-2026) aparecía como +994 % y el optimizador le daba 11–20 % en todas las propuestas; la «máxima puntuación» de 95.7 estaba inflada por ese salto. Otros saltos ficticios: WMT, NVDA, AVGO, NFLX, SPCE y LCID. Ahora se usa precio ajustado **solo por splits** (`precios_mxn(..., ajustados="splits")`) en el optimizador, el ranking, las boletas y las alertas. La valuación de la cartera sigue usando el cierre real.
- **Escenarios irreales.** Antes daban +162 % / −37 % a 0.25 años. Ahora usan el horizonte real al 13-nov (29 sesiones, sin piso de 0.25 años). La media histórica se contrae 50 % por sesgo de selección y los días de salto único se acotan a ±10 %. Se informan la volatilidad con saltos y los saltos acotados.
- **La hoja de fondos tiraba el ciclo completo.** El User-Agent contenía «pública» (no ASCII) y httpx lo rechazaba, así que no se recalculaban propuestas. Se corrigió la cabecera y un fallo de esa fuente ya no detiene el ciclo.

### Añadido
- `uv run terminal catalogo-simulador [--confirmar]`: limita el universo del Reto a lo que muestra el simulador del participante (transcripción de «Datos Actinver.pdf», 22-sep-2026: 146 acciones y 23 fondos). Quedan fuera AGG, IAU, IEF, IVV, QQQ, SHV, VEA, VNQ, VOO, VWO y SMARTRC; antes la variante extranjera ponía 47 % en cinco de esos ETF. Si el catálogo cambia, las propuestas se recalculan.
- **Boletas SIC condicionales.** Sin cotización confiable del SIC, la boleta sigue en «investigar» (no ejecutable), pero trae títulos aproximados y una banda de ±2 % alrededor de la referencia (cierre de origen × tipo de cambio, con fuente y fecha). Solo se captura si el precio del portal cae dentro de la banda.
- **Plan corregido.** Si un recálculo cambia las órdenes después de enviado el plan del día y antes de la apertura del Reto (07:30; 08:30 desde el 3-nov), se reenvía una vez marcado «🔁 PLAN CORREGIDO», con un máximo de 2 por sesión.
- `config/reto.yaml`: bases re-verificadas el 29-sep. Queda registrada la discrepancia: las bases no mencionan el SIC ni publican catálogo.

## [0.12.2] — 2026-09-29 (iniciador remoto)

### Corregido
- `iniciar-remoto.bat` encuentra Tailscale aunque no esté en `PATH`, obtiene el host y usuario de la sesión privada, actualiza solo esas dos claves de `.env` y reutiliza la terminal cuando ya acepta ese acceso. Si necesita aplicar la configuración, reinicia únicamente el proceso de esta terminal.
- La guía de acceso remoto describe la instalación oficial para Windows cuando `winget` no está disponible.
- El acceso remoto no se activa si Tailscale no ha iniciado sesión; se comprobó este fallo seguro y el rechazo de un host no autorizado. La conexión real entre dispositivos queda pendiente del inicio de sesión del usuario.

## [0.12.1] — 2026-09-29 (serie exacta de JPMRVUS)

### Corregido
- `JPMRVUS` ahora usa la serie **B-1** y la clave operable `JPMRVUS B-1`, coherentes con el identificador oficial `52_JPMRVUS_B-1`. Se volvió a importar la hoja oficial conservada del 28-sep-2026: 23 de 23 fondos con NAV, incluido `JPMRVUS` a 1.344672 MXN.
- Se actualizó la prueba de coincidencia exacta de series. La suite completa pasó: 203 pruebas. Cobertura observada: 148 de 174 instrumentos con precio; 26 emisoras BMV sin datos. El millón inicial sigue siendo un registro local, sin captura confirmada del portal; no hay cotización BMV/SIC en tiempo real.

## [0.12.0] — 2026-09-29 (cobertura de precios)

### Corregido
- **EODHD pedía Peñoles como «PEOLES»:** su código es `PE&OLES`; ahora se conserva el `&` (codificado en la URL). El resto del mapeo se verificó contra la lista oficial de la BMV en EODHD.
- **Las emisoras BMV nunca cargadas no recibían cupo:** las actualizaciones diarias consumían las 18 consultas. Ahora se reservan 6 por día para emisoras nuevas.
- **Zona horaria:** un precio con solo fecha se tomaba como medianoche UTC (el día anterior en CDMX) y se marcaba obsoleto. Ahora usa la hora de cierre de la sesión.
- **Desempate entre fuentes con la misma fecha:** antes era alfabético; ahora sigue una prioridad explícita (`PRIORIDAD_FUENTE`).
- Si se agota el cupo de una fuente, se prueba la siguiente que cubra el instrumento.

### Añadido
- **Hoja oficial de precios de los fondos Actinver** (`terminal/fondos_actinver.py`):
  - 22 de 23 fondos con NAV y fecha de valuación del propio documento, huella SHA-256 y copia local del PDF;
  - descarga diaria automática, subida manual en «Datos» o `uv run terminal fondos [--archivo PDF]`.
- **Twelve Data** (`TwelveData`):
  - alternativa de cierre diario para la BMV (plan Pro);
  - solo para los 37 símbolos verificados con `uv run terminal cobertura-twelvedata`, y solo con `TWELVEDATA_API_KEY`.
- **Fuentes confiables para boletas** `twelvedata_bmv` y `actinver_pdf`: la cobertura se verifica al descargar la serie exacta.
- **Boletas** (pantalla y Telegram) muestran fuente, moneda, fecha y hora, y tipo (tiempo real, retrasado o cierre diario); sin cotización fiable muestran «Sin datos» y no calculan la orden.
- Documentación de Grupo BMV INTRA: qué contrato, infraestructura y contacto requiere.

## [0.11.0] — 2026-09-29 (auditoría integral)

### Añadido (boletas)
- **Bot de Telegram** (`terminal/bot_telegram.py`):
  - atiende solo al chat de `TELEGRAM_CHAT_ID`;
  - comandos `/plan`, `/boletas` (genera y envía las del plan del día), `/estado`, `/alertas`, `/cartera` y `/ayuda`, con menú en la app;
  - responde preguntas libres con Claude (`claude-opus-5-5` con `fallbacks: "default"`; opcional: `uv add anthropic` y credencial), con Ollama o con los datos de la terminal (ficha por emisora);
  - tope de 20 consultas por hora; nunca ejecuta órdenes.
- **Boletas del plan del día:**
  - se generan con el botón «Generar boletas del plan del día» (Propuestas), con `uv run terminal boletas` o con `POST /api/boletas/generar {"propuesta": "plan_del_dia"}`;
  - usan la misma propuesta que el mensaje de Telegram y reemplazan las boletas vigentes anteriores para no duplicar órdenes.

### Corregido
- **Plan del día:**
  - un envío fallido ya no cuenta como enviado: se reintenta cada 10 minutos, hasta 12 veces al día;
  - la base de comparación es el último plan que sí llegó;
  - si las propuestas se están recalculando, espera hasta 60 minutos para no mandar un plan viejo.
- **Las propuestas se recalculan solas al cambiar el código o la configuración:**
  - cada propuesta guarda `huella_calculo`, un sha256 de `optimizador`, `servicios`, `mercado`, `portal`, `reto`, `vigencia`, `config/reto.yaml` y las secciones de configuración del cálculo;
  - si no coincide, la propuesta deja de ser actual y el motor la recalcula en su siguiente ciclo.
  - Solo disparan recálculo los avisos que se resuelven recalculando (código, perfil o datos). El bloqueo por captura incompleta ya no provoca un recálculo en cada ciclo.
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
