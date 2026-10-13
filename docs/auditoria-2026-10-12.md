# Auditoría integral — 12-oct-2026

Alcance: cambios recientes de Actinver Terminal (barra de comandos, opciones europeas, centro de investigación, mapa de
calor, serie local con SMA20/RSI14, enlace al widget de TradingView y separación real/demostración). Es diagnóstico:
**no se modificó código** en esta auditoría. No se imprimieron secretos.

## Estado de Git al auditar

| Tipo | Archivos |
|---|---|
| Confirmado y en GitHub | Todo hasta `db3a3d3` (historia externa, Finviz Elite apagado y capturas del Reto) |
| Confirmado, sin subir | `2d58bcf` (captura del 12-oct) y `e79ec3b` (concentración y precios atrasados en el plan; descarga de cierres tras una captura) |
| Modificados, sin confirmar (otra sesión, en curso) | `.env.example`, `CHANGELOG.md`, `CLAUDE.md`, `README.md`, `terminal/app.py`, `terminal/db.py`, `terminal/seguridad.py`, `terminal/servicios.py`, `web/index.html`, `web/static/app.css`, `web/static/app.js` |
| Sin seguimiento (otra sesión) | `terminal/visualizaciones.py`, `terminal/centro_conectores.py`, `terminal/centro_investigacion.py`, `terminal/modelos_opciones.py`, `config/fuentes_investigacion.json`, `docs/centro-investigacion.md`, `docs/fluere-referencia.md`, pruebas `test_visualizaciones_mercado.py`, `test_centro_investigacion.py`, `test_modelos_opciones.py`; y el trabajo de TradingView (`tradingview/`, `docs/tradingview-puente.md`, `tests/test_tradingview_pine.py`) |

Las funciones auditadas **están activas en la terminal local**, pero no están en Git ni en GitHub. Si se pierde la
carpeta, se pierden.

## 1. Inventario de funciones

| Función | Archivo o módulo | Estado | Fuente de datos | Calidad y retraso | Riesgo o limitación | Prueba existente |
|---|---|---|---|---|---|---|
| Investigación macro (tasas, producción, CPI, empleo) | `terminal/centro_conectores.py` (`FredMacro`, `BLS`) | **Funciona**: FRED 94 observaciones al 8-oct; BLS 115 al sep-2026 | FRED API, BLS API pública | Diario/mensual con 1–6 semanas de rezago de publicación; «disponible desde» = hora de descarga | El CPI interanual se calcula con datos revisables; no es «sorpresa» frente a consenso | `test_centro_investigacion.py` (BLS, FRED) |
| Energía: WTI, Brent e inventarios | `centro_conectores.EIA` | **Clave válida** (consulta mínima OK hoy); **aún sin primera consulta** registrada en la base | EIA API v2 | WTI/Brent diarios con 1–5 días de rezago; inventarios semanales | Referencia energética; no es precio de XOM | `test_eia_v2_seriesid` |
| Estados financieros y márgenes | `centro_conectores.AlphaVantage` | **Clave válida** (`INCOME_STATEMENT` OK hoy); **última consulta registrada: error, 0 registros** | Alpha Vantage gratuita | Anual (último ejercicio cerrado) | Un aviso de límite en cualquiera de los 4 símbolos anula los 4 (todo o nada) | `test_conector_alpha_confirma_simbolo...` |
| Contexto cripto | `centro_conectores.CoinGecko` | Implementado, **sin clave** | CoinGecko Demo | Con hora de la fuente | Solo contexto; fuera del Reto | `test_coingecko_conserva_hora_atrasada` |
| Importación de hallazgos (CSV/notas) | `centro_investigacion.importar_csv` | Funciona | Usuario | Rotulado «manual»; disponible desde la importación | No verifica que la transcripción sea correcta | 6 pruebas (atomicidad, fórmulas, claves, SSRN) |
| Mapa de calor | `terminal/visualizaciones.py::mapa` | Funciona | Los dos últimos cierres locales por instrumento | Cierre diario; muestra fecha, proveedor y días de rezago | Usa cierre **sin ajuste por splits**: un split entre ambos cierres aparece como caída o subida falsa. SIC en USD de origen, no en MXN del simulador | `test_mapa_usa_dos_cierres_reales...` |
| Filtro por mercado | `web/static/app.js` (vista Mercado) | Funciona (cliente) | Celdas del mapa | — | — | Sin prueba de interfaz |
| Gráfica local de cierres | `visualizaciones.serie` | Funciona (120 cierres) | `precios` (cierre/NAV) | Diario | Sin OHLC: no hay velas locales (se dice) | `test_serie_no_fabrica_velas...` |
| SMA20 y RSI14 | `visualizaciones._indicadores` | Funciona | Cierres locales | Retrospectivo | El RSI es de **promedio simple (Cutler)**, no de Wilder: no coincidirá con el RSI del widget de TradingView. Sin ajuste por splits | Solo un caso (serie creciente → RSI 100) |
| Widget de velas TradingView | `terminal/app.py::grafica`, `CSP_GRAFICA` | Funciona (enlace externo) | TradingView (gratuito) | Retraso según TradingView; la página lo dice | Script de terceros sin versión fija, ejecutado en el origen local `127.0.0.1:8765` | Prueba de 404 para símbolo inexistente |
| Barra de comandos (`Ctrl+K`, `/INV`, `/MOD`…) | `web/static/app.js`, `web/index.html` | Funciona (sintaxis JS válida) | Universo local | — | Solo coincidencia exacta | Sin prueba de interfaz |
| Opciones europeas (BSM, griegas, IV) | `terminal/modelos_opciones.py`, `POST /api/modelos/opciones` | Funciona | Entradas manuales | — | Europeo: no aplica a americanas con ejercicio anticipado; días/365 | 4 pruebas: valores de referencia, paridad, recuperación de IV y límites |
| Separación real / demostración | `visualizaciones._cierres`, `centro_investigacion.actualizar` | Funciona | `proveedor='demo_sintetico'` | — | La prioridad de proveedores está **duplicada** en SQL y difiere de `mercado.PRIORIDAD_FUENTE` (faltan `ice`, `edimex`) | `assert "demo_sintetico" not in ...`, `test_demo_no_red` |
| Propuestas, escenarios, riesgo, robustez, validación | `optimizador.py`, `escenarios.py`, `robustez/`, `validacion_extendida.py`, `historia_externa.py` | Funcionan (auditados el 6–7 oct) | Cierres locales + historia externa verificada | Diario | Sin ventaja demostrada frente a 1/N; sesgo de supervivencia en la historia larga | `test_robustez`, `test_validacion_extendida`, `test_historia_externa` y otras |
| Plan del día y boletas por Telegram | `mensaje_simple.py`, `boleta.py`, `bot_telegram.py` | Funcionan | Captura del portal + cierres | Captura manual | Boletas informativas; la terminal no envía órdenes | `test_mensaje_simple`, `test_boleta*` |
| Noticias y movimientos públicos | `adaptadores/` (Seeking Alpha RSS, ForexFactory), `movimientos/` (SEC EDGAR) | Funcionan | RSS, JSON, EDGAR | Minutos–días | Solo contexto, peso 0 | Pruebas de movimientos y contexto |
| Precio en vivo de EE. UU. | `tiempo_real.py` (Alpaca IEX) | Funciona (≤ 30 símbolos) | Alpaca IEX | Segundos; IEX ≈ 2–3 % del volumen | Precio de origen × tipo de cambio ≠ precio SIC del simulador | `test_tiempo_real*` |
| Finviz Elite | `terminal/finviz.py` | **Apagado** (sin token; es de pago) | — | Sin hora del último hecho → «retrasado» | Decisión de pago del usuario | `test_finviz.py` |
| Alertas | `alertas.py`, `notificador.py`, `cloud-alerts/` | Funcionan | Base local | — | — | Pruebas de alertas y del Worker |

## 2. Datos, licencias y retraso

| Proveedor | Dato real | Acceso y cuota | Retraso / zona | Condiciones | ¿Se presenta con honestidad? |
|---|---|---|---|---|---|
| FRED | Tasas, producción industrial, USD/MXN de respaldo | Gratis con clave | 1+ día hábil (fecha de la serie) | Citar FRED; algunas series tienen derechos de terceros | Sí: período y hora de descarga |
| EIA | WTI, Brent, inventarios | Gratis con clave | Diario/semanal con rezago | Dominio público (EE. UU.) | Sí: «no es precio de XOM» |
| BLS | CPI, desempleo, nóminas | Público; 25 consultas/día sin clave | Mensual | Dominio público | Sí; se excluye M13 |
| Alpha Vantage | Estado de resultados anual | Gratis 25/día y límite por ráfaga | Anual | Uso según sus términos | Sí: «no es TTM ni cotización» |
| CoinGecko | BTC/ETH | Demo con clave | Hora de la fuente | Pide atribución | Sí: hora de la fuente y «atrasada» |
| TradingView (widget) | Velas e indicadores | Gratis; widget oficial | Según TradingView y bolsa (la BMV puede ir diferida) | Atribución incluida en el widget | Sí: «datos y retraso según TradingView» |
| Alpaca | Barras diarias y último precio IEX | Gratis, 1 conexión, 30 símbolos | IEX en segundos; histórico SIP | Solo dominios de datos | Sí: «tiempo real» solo con latencia medida |
| Tiingo | Cierres EE. UU. ajustados | Gratis, uso personal | Tras el cierre de NYSE | Sin redistribución | Sí |
| EODHD | Cierres BMV | Gratis 20/día | Tras el cierre BMV | Precios «indicativos» | Sí: cierre con fecha |
| Banxico SIE | FIX USD/MXN | Gratis con token | FIX ≈ 12:00 CDMX | API oficial | Sí |
| SEC EDGAR | Form 4 y 13F | Gratis; User-Agent con contacto; ≤ 10/s | Minutos–45 días (13F) | Uso justo | Sí: contexto, no orden |
| Actinver (PDF de fondos; PDF del portal del usuario) | NAV de fondos; precios del simulador | Público / del usuario | T+1 (fondos) | Sin automatizar el portal | Sí |

**Riesgo diario usado como intradía.** El mapa y la serie usan solo `tipo_dato IN ('cierre','nav')`, así que excluyen
los precios en vivo. El plan del día ya avisa si la valuación usa precios atrasados (`e79ec3b`). Ningún texto auditado
presenta un cierre como tiempo real. El riesgo que queda es de interpretación: la variación del SIC en el mapa está en
USD de origen, no en el precio en MXN del simulador. La nota lo dice, pero conviene ponerlo a la vista en la celda.

## 3. Hallazgos por severidad

No hay hallazgos **críticos**: ninguna ruta envía órdenes, `.env` y `data/` están excluidos de Git y el escaneo del árbol
no encontró secretos.

### Alta
1. **Alpha Vantage no guarda datos pese a la clave válida.** `investigacion_consultas` registra «error, 0 registros»
   en la última consulta de la terminal. Una consulta mínima de hoy a `INCOME_STATEMENT` sí respondió.
   - Causas probables:
     - el servidor aún corría el conector anterior (`OVERVIEW`, premium);
     - el límite por ráfaga del plan gratuito: `AlphaVantage.consultar` pide 4 símbolos seguidos sin pausa
       (`centro_conectores.py` ≈ l. 75) y un aviso en cualquiera anula los 4 (≈ l. 79).
   - Falta confirmarlo con el próximo ciclo; la última consulta guardada es anterior al último reinicio.
2. **Funciones nuevas sin control de versiones.** Todo el centro de investigación, el mapa, la serie, opciones y la barra
   de comandos están sin confirmar en Git (otra sesión trabajando). Un error de disco o una limpieza los borraría.

### Media
3. **Mapa de calor y SMA/RSI con cierre sin ajustar por splits** (`visualizaciones.py` l. 17 y 52). El día de un split
   la celda muestra un −50 % o −90 % falso, y la SMA/RSI se distorsionan. La terminal ya tiene `mercado._solo_splits` y
   `eventos_corporativos` para corregirlo.
4. **RSI de Cutler, no de Wilder** (`_indicadores`, l. 73–77). No coincide con el RSI de TradingView que el usuario abre
   al lado. Debe rotularse o cambiarse a Wilder.
5. **Prioridad de proveedores duplicada** (`visualizaciones.py` l. 21–25 frente a `mercado.PRIORIDAD_FUENTE`). Ya
   difieren (`ice` y `edimex`), y un empate de prioridad no tiene desempate determinista.
6. **Script de TradingView en el origen local.** `/grafica/{iid}` carga `embed-widget-advanced-chart.js` sin versión fija
   ni SRI, en `127.0.0.1:8765`. Lo mitigan:
   - `connect-src` limitado a `*.tradingview.com`;
   - el CSRF por cabecera.

   Falta `form-action` en `CSP_GRAFICA`. Conviene servir la gráfica en un iframe con `sandbox` o en otro puerto.
7. **Mensaje de error genérico en el centro de investigación** (`centro_investigacion.py` l. 264–266). Evita filtrar la
   clave, pero no distingue clave rechazada, cupo, red o formato. Por eso el hallazgo 1 no se pudo diagnosticar desde la
   interfaz.

### Baja
8. Escáner de secretos lento: `scripts/escanear_secretos.py` lanza un `git show` por archivo y por commit, y solo revisa
   la historia, no el árbol sin confirmar. El escaneo del árbol se hizo aparte.
9. Mapa: `dias_calendario` usa `date.today()` de la PC; si la variación cubre más de una sesión, no se marca aparte
   (`fecha_anterior` sí se entrega).
10. Opciones: `dias/365` en calendario y ejercicio europeo; los rótulos lo dicen. No hay dividendos discretos ni
    americanas.
11. `resumen()` del centro usa los intervalos por omisión (`DEFAULTS`), no la configuración local, para marcar
    «requiere actualización» (l. 312).

### Cálculos verificados sin defecto
- BSM: precio, `d1`/`d2`, delta, gamma, vega (por 1 pp), theta (por día), rho (por 1 pp) y descuento por dividendo
  continuo coinciden con las fórmulas estándar. La paridad put-call y la recuperación de IV están probadas. La bisección
  de IV acota por arbitraje y usa 80 iteraciones.
- SMA20: ventana exacta de 20; `None` con historia insuficiente.
- Separación demo/real: filtros por proveedor y tipo en SQL; el centro no consulta APIs en demostración.
- Validación y robustez (auditadas el 6–7 oct):
  - walk-forward sin solapes, con costos del Reto y referencia 1/N;
  - Monte Carlo con semilla fija y preregistro antes de ver resultados;
  - la historia externa solo extiende rendimientos verificados.

## 4. Seguridad y privacidad

| Control | Resultado |
|---|---|
| `.env` y `data/` fuera de Git | Sí (`.gitignore` l. 8 y 43) |
| Secretos en el árbol (301 archivos, con y sin seguimiento) | 0 hallazgos con los patrones de `escanear_secretos.py` |
| Secretos en la historia de Git | Escáner completo lanzado; ver «Pruebas» |
| URL con claves en registros | `httpx` en WARNING; los adaptadores informan solo el tipo de error; el centro nunca devuelve cuerpo ni URL |
| CSRF / CSP | CSRF por cabecera en POST; CSP estricta en la app (`script-src 'self'`); CSP propia en `/grafica` |
| Límite de peticiones | `/api/centro-investigacion/actualizar` 4/min e `importar` 10/min (`seguridad.py`) |
| CSV manipulado | Encabezados exactos, ≤ 1 MB / 1,000 filas, períodos no futuros, dominio oficial obligatorio, sin credenciales, fórmulas neutralizadas al exportar, todo o nada |
| Webhook de TradingView | Secreto, huella anti-repetición y solo registro de alertas (auditoría previa) |
| Rutas que envíen órdenes | **Ninguna.** Alpaca solo usa `data.alpaca.markets` y `stream.data.alpaca.markets`; no hay código de `/v2/orders` |

## 5. Experiencia del usuario

- **Qué funciona hoy de forma confiable:**
  - plan del día y boletas informativas;
  - valuación con capturas del portal;
  - propuestas con sus avisos de evidencia;
  - mapa y gráfica de cierres;
  - macro FRED/BLS;
  - modelo de opciones con hipótesis propias.
- **Qué requiere clave, archivo o intervención manual:**
  - capturas del portal y PDF de precios del simulador;
  - Alpha Vantage (por confirmar) y EIA (primera consulta pendiente);
  - CoinGecko (sin clave);
  - Finviz Elite (de pago);
  - herramientas sin conector (ROIC.ai, Quartr, SpotGamma…), que entran por CSV.
- **Qué no es señal de compra o venta:** mapa, SMA/RSI, investigación, movimientos públicos, opciones teóricas,
  pronóstico experimental.
- **Qué no es tiempo real:**
  - todo lo diario (cierres, mapa, investigación);
  - el SIC calculado como precio de origen × tipo de cambio.

  Solo los precios IEX con latencia medida se rotulan «tiempo real».
- **Qué puede confundir a una persona nueva:**
  - la diferencia entre el RSI local y el del widget;
  - la variación del SIC en USD;
  - «Investigación» frente a «Propuestas»: la primera no cambia la segunda;
  - un error genérico sin causa en el centro.
- **Qué falta para Order Flow / Option Flow:**
  - trades y cotizaciones con hora, bolsa y bandera de agresor;
  - libro de órdenes;
  - cadenas de opciones con bid/ask, volumen, interés abierto, IV y vencimiento;
  - todo de un proveedor con licencia y retraso declarado.

  Nada de esto existe hoy en fuentes gratuitas conectadas.

## 6. Plan priorizado

### Etapa 1 — Correcciones críticas y seguridad
| # | Acción | P | Beneficio | Riesgo | Archivos | Dependencias | Pruebas nuevas | Criterio de fin |
|---|---|---|---|---|---|---|---|---|
| 1.1 | Confirmar en Git el trabajo de la otra sesión, cuando esa sesión lo cierre | P0 | No perder funciones activas | Mezclar trabajo a medias | Los listados arriba | Acuerdo con la otra sesión | — | `git status` limpio salvo lo intencional |
| 1.2 | Alpha Vantage: pausa ≥ 1.2 s entre símbolos y guardado parcial por símbolo | P0 | Que la clave válida entregue datos | Bajo | `centro_conectores.py` | Cupo AV | Respuesta simulada con aviso en el 2.º símbolo → se guardan 1.º, 3.º y 4.º | Consulta real con ≥ 1 símbolo guardado y estado «ok/parcial» |
| 1.3 | Errores clasificados sin filtrar secretos (credencial, cupo, red, formato) | P1 | Diagnóstico desde la interfaz | Filtrar la URL si se hace mal | `centro_investigacion.py` | — | Error 401/aviso/timeout → mensaje distinto, sin la clave | Cada tipo muestra su causa |
| 1.4 | `/grafica` en iframe `sandbox`, `form-action 'none'` en su CSP | P1 | Aísla el script de terceros | Que el widget no cargue | `app.py`, `web/` | TradingView | CSP con `form-action`; carga del widget | El widget carga y la CSP lo restringe |
| 1.5 | Escáner de secretos incremental y del árbol | P2 | Que se pueda correr en cada commit | — | `scripts/escanear_secretos.py` | — | Árbol con un secreto falso → lo detecta | < 30 s |

### Etapa 2 — Calidad de datos y trazabilidad
| # | Acción | P | Beneficio | Riesgo | Archivos | Pruebas nuevas | Criterio de fin |
|---|---|---|---|---|---|---|---|
| 2.1 | Mapa y serie con precio ajustado por splits (`mercado._solo_splits`) | P1 | Sin caídas falsas | Bajo | `visualizaciones.py` | Split 1:10 entre dos cierres → variación real, no −90 % | Prueba verde |
| 2.2 | Usar `mercado.PRIORIDAD_FUENTE` en lugar del `CASE` duplicado | P1 | Una sola regla | — | `visualizaciones.py`, `mercado.py` | Proveedores `ice`/`edimex` ganan a `tiingo` el mismo día | Una sola fuente de prioridad |
| 2.3 | Celda del mapa con variación en MXN del simulador (SIC = origen × FX) además de USD | P2 | Comparable con el portal | Mezclar FX de días distintos | `visualizaciones.py`, `app.js` | FX del mismo día o etiqueta «FX de otra fecha» | Ambas cifras visibles |
| 2.4 | Marcar en el mapa «cubre N sesiones» cuando hay hueco entre cierres | P2 | No leer 3 días como 1 | — | `visualizaciones.py`, `app.js` | Hueco de 2 sesiones → aviso | Visible |
| 2.5 | Primera consulta EIA y AV registradas y visibles en «Investigación» | P1 | Confirmar acceso real | Cupo | — | — | Estado «ok» con fecha |

### Etapa 3 — Investigación, gráficos, riesgo y backtesting
| # | Acción | P | Beneficio | Archivos | Pruebas nuevas | Criterio de fin |
|---|---|---|---|---|---|---|
| 3.1 | RSI de Wilder (o rótulo «RSI simple») | P1 | Coincide con TradingView | `visualizaciones.py` | Serie de referencia con RSI Wilder conocido (± 0.01) | Prueba verde |
| 3.2 | Pruebas de interfaz para barra de comandos y filtro por mercado | P2 | Evitar regresiones | `tests/` (Playwright o pruebas de API) | Navegación `/INV`, símbolo exacto, símbolo inexistente | Verde en CI local |
| 3.3 | Sensibilidad de la cartera a tasas, WTI y CPI (descriptiva, con fecha de disponibilidad) | P3 | Contexto de riesgo | Nuevo módulo de investigación | Sin anticipación: solo datos con `disponible_desde` ≤ fecha | Informe con IC, sin afectar propuestas |
| 3.4 | Escenario de estrés por concentración (MU ≈ 47 %) en «Riesgo» | P2 | Ver el efecto de una sola emisora | `escenarios.py`, `app.js` | −10/−20 % en la mayor posición | Visible y probado |

### Etapa 4 — Base para Order Flow y Option Flow (solo investigación; nada de ejecución)
| # | Acción | P | Beneficio | Dependencias externas | Pruebas nuevas | Criterio de fin |
|---|---|---|---|---|---|---|
| 4.1 | Esquema normalizado de trades/cotizaciones/opciones (símbolo, contrato, mercado, instante con zona, bid/ask, tamaño, volumen, interés abierto, origen, retraso medido) | P3 | Base trazable | Ninguna para el esquema | Validación de esquema e instantes sin zona → rechazo | Tablas y validador probados |
| 4.2 | Elegir un proveedor con licencia para cadenas de opciones y trades | P3 | Datos reales | **Decisión y posible pago del usuario** | — | Contrato o plan gratuito documentado |
| 4.3 | Backtesting sin anticipación sobre esos datos, con costos y calendario | P3 | Medir antes de usar | 4.1 y 4.2 | Embargo temporal y preregistro | Informe con evidencia fuera de muestra |

Toda ejecución sigue simulada. No se propone trading automático.

## 7. Pruebas ejecutadas

| Verificación | Resultado |
|---|---|
| Pruebas focalizadas: visualizaciones, centro de investigación, opciones, Finviz, historia externa, compilación, plan, seguridad/webhook | **162 aprobadas** |
| Suite completa (`uv run pytest`, sin las de TradingView de la otra sesión) | 473 aprobadas el 12-oct (tras `e79ec3b`); repetida durante esta auditoría (ver respuesta) |
| `node --check web/static/app.js` | Sintaxis válida |
| `git diff --check` | Sin errores de espacios |
| Secretos en el árbol de trabajo (301 archivos) | 0 hallazgos |
| `scripts/escanear_secretos.py` (toda la historia) | Lanzado; lento por diseño (hallazgo 8) |
| Claves (consulta mínima, sin imprimir valores) | Alpha Vantage: OK (`INCOME_STATEMENT`); EIA: OK (1 observación WTI); FRED: OK en el último ciclo (94 observaciones) |

## 8. Pendientes y requisitos externos

- Confirmar en Git el trabajo de la otra sesión (1.1) cuando termine.
- CoinGecko: clave Demo opcional (gratuita).
- Finviz Elite: de pago, decisión del usuario.
- Order Flow / Option Flow: proveedor con licencia (decisión del usuario).
- Datos BMV en tiempo real: siguen requiriendo contrato (D-16).
