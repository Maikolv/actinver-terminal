# Mejoras: indicadores, GEX, laboratorio de permutaciones y plan intradía

Todo es informativo: ninguna ruta envía órdenes, modifica la cartera ni activa un broker. No se atribuye a ninguna fuente externa no verificada.

## 1. Indicadores sobre OHLCV (`terminal/flujo/calculos.py`)
- SMA 20 (ya existía), **EMA 20/50** (semilla = SMA de las primeras n barras), **MACD 12/26/9**, **estocástico lento 14/3/3** y **SAR parabólico** (0.02; máx. 0.2, Wilder).
- Valores `null` durante el calentamiento (EMA20: 19 barras; MACD: 25, señal: 33; %K: 15, %D: 17; SAR: la barra 0). Sin relleno.
- Estocástico con rango máximo = mínimo: indefinido → `null` (no 0 ni 50). SAR: dirección inicial según el cierre de la barra 1 vs. la 0; al girar toma el extremo previo.
- `GET /api/flujo/velas` agrega `ema20, ema50, macd, macd_senal, macd_hist, estoc_k, estoc_d, sar, sar_alcista`.
- UI (Velas): EMA/SMA/SAR sobre las velas; MACD (líneas + histograma, eje con cero) y estocástico (eje fijo 0–100, niveles 20/80) en paneles separados alineados al eje X; la tabla accesible añade las columnas activas.

## 2. Navegación
Mercado, Velas, Order Flow, Option Flow, Riesgo y Laboratorio son pestañas principales (ya no están en «Más»); «Plan intradía» está en «Más». El Plan de acción tiene una botonera de accesos y cada panel de análisis, enlaces a los demás; al pasar de Velas/Order Flow/Option Flow se conserva el instrumento (en opciones solo si es del SIC). Se mantiene `role=tab`, flechas/Inicio/Fin y el diseño móvil; atajos `/LAB`, `/INT`, `/GEX`.

## 3. GEX (`terminal/flujo/gex.py`, `GET /api/flujo/gex?subyacente=`)
- Por contrato exige gamma, interés abierto, multiplicador, spot y moneda **de la misma cadena** (columnas nuevas opcionales `multiplicador, spot, moneda` en `flujo_opciones`; la importación CSV de opciones las acepta al final del encabezado; las bases anteriores se migran solas). No se supone multiplicador 100 ni se toma spot de otra tabla, hora o moneda.
- USD por movimiento de 1 % = `gamma × OI × multiplicador × S² × 0.01` (en la moneda del spot).
- Dos vistas: **absoluta** (calls + puts) y **firmada** (calls +, puts −), esta última una **convención**, no la posición conocida de los intermediarios.
- Solo se usa una referencia (instante, spot, moneda); lo demás se excluye y se cuenta. Si faltan datos, la vista dice cuántos contratos faltan por causa y qué importar/qué proveedor hace falta.
- **Con el feed gratuito de Alpaca (sin interés abierto ni multiplicador) el GEX no es calculable**: solo aparece con CSV importado con esas columnas o un proveedor OPRA con interés abierto y especificaciones de contrato. Es exposición de contratos, no flujo de operaciones (no es tape de Option Flow).

## 4. Laboratorio de alfa (`terminal/laboratorio.py`, `POST /api/laboratorio/permutacion`)
- Entrada: CSV (encabezado con `benchmark` y ≥ 1 columna de estrategia; `fecha` opcional) o JSON `{benchmark, estrategias}`; rendimientos simples **netos**, en decimal, emparejados. En la UI hay un ejemplo **SINTÉTICO** explícito.
- H0: exceso medio neto ≤ 0 frente a H1: > 0. Estadístico: media de (estrategia − benchmark). Se voltean signos de bloques contiguos completos (conserva dependencia dentro del bloque); `p = (extremos + 1)/(B + 1)`; semilla reproducible (`huella_sha256` de entradas + parámetros).
- Supuesto: simetría/intercambiabilidad de signos bajo H0. No es universal: asimetría fuerte, colas gruesas o dependencia más larga que el bloque pueden invalidar p.
- Varias estrategias → ajuste de Holm; `hipotesis_exploradas` cuenta variantes probadas no reportadas (como p = 1).
- Límites: 20–5 000 observaciones, ≥ 8 bloques, B 199–20 000, 20 estrategias, `B × bloques × estrategias ≤ 2·10⁸`, cuerpo ≤ 1.2 MB, 6 solicitudes/min; se rechazan NaN/inf, vacíos, textos y rendimientos ≤ −100 %.
- El resultado nunca dice «alfa probado»: advierte preregistro, walk-forward con purga/embargo, holdout y costos.
- Seguridad: mismos controles que el resto de POST (CSRF, origen local, tamaño, límite por minuto); no guarda datos.

## 5. Plan intradía (`terminal/plan_intradia.py`, `GET /api/plan-intradia?perdida_dia_mxn=`)
- Separado de `plan_accion.py`. `ordenes` siempre vacío y `senal_ejecutable` siempre `false`.
- Inhibe la señal si hay solo datos diarios, retraso desconocido o > 60 s, barra no reciente, mercado cerrado, sin captura del portal o pausa activa. Con los proveedores gratuitos actuales (≥ 15 min) queda siempre inhibida; incluso sin inhibición la vista no genera señales.
- Muestra concentración (tope = mínimo entre 50 % del Reto y el perfil), presupuesto de pérdida diaria/por idea, **pausa** al alcanzar la pérdida límite que usted informa (la terminal no mide su P&L intradía), lista de posiciones en pérdida (**no promediar**), liquidez (% del volumen diario guardado), costos del Reto (comisión + IVA, ida y vuelta) y disponibilidad.
- Umbrales (`perdida_diaria_pct` 1, `perdida_por_idea_pct` 0.25, `liquidez_max_pct_volumen` 1, `retraso_max_s` 60) son parámetros de disciplina, editables en `[intradia]`; no salen de un modelo.
- Las coberturas con futuros no son elegibles en el Reto y no se consideran.

## Limitaciones
- Pruebas: `tests/test_mejoras_intradia.py` (indicadores, GEX, permutaciones, API, plan). La interfaz se verificó en localhost con datos de prueba, sin errores de consola/CSP; no hay prueba automatizada del JS.
- El valor p de permutación no corrige por selección de estrategia fuera de la familia declarada.
- El volumen de liquidez del SIC es el de la bolsa de origen.

## Verificación final (16-oct-2026)
- Suite completa: 561 pruebas aprobadas. Ajustes finales cubiertos por 41 pruebas enfocadas (incluyen rechazo de parámetros infinitos y barras sintéticas en contexto intradía).
- `node --check web/static/app.js` correcto; revisión de patrones de secretos en 15 archivos de la entrega sin hallazgos.
- Navegador: controles de indicadores conservan selección al cambiar rápido; respuestas antiguas ya no reemplazan la vista más reciente. Con solo 21 barras, MACD avisa calentamiento insuficiente y no inventa valores; estocástico sí aparece cuando hay datos suficientes.
- Ejemplo del laboratorio ejecutado desde la UI, con rótulo sintético, semilla y Holm visibles. No representa resultados financieros reales.

## 6. Preregistro y holdout de un solo uso (`terminal/laboratorio.py`, 16-oct-2026)
- `POST /api/laboratorio/preregistro` guarda, antes de ver datos:
  - nombre, hipótesis, benchmark, costos, fuentes, cómo se generaron los rendimientos (walk-forward/purga) y estrategias;
  - B, semilla, α, bloque e hipótesis exploradas;
  - fracción de holdout (0.1–0.5) y embargo (0–250 observaciones).
  Se guarda en la tabla `laboratorio_experimentos` con huella sha256 y fecha.
- `POST /api/laboratorio/experimentos/{id}/evaluar`:
  - exige exactamente las estrategias preregistradas;
  - corta en orden cronológico: exploración | embargo (descartado) | holdout;
  - aplica la misma prueba de permutación y Holm a ambos tramos; solo el holdout es confirmatorio.
- El holdout se usa una sola vez: una segunda evaluación devuelve el resultado guardado y no recalcula, aunque cambien los datos.
- `GET /api/laboratorio/experimentos/{id}/exportar` entrega un JSON con preregistro, huellas y resultado.
- Límite: la terminal no puede comprobar que los rendimientos vengan de un walk-forward real. El preregistro lo declara y queda trazado.

## 7. Filtro de Option Flow, perfil experimental de Skylit (`terminal/flujo/skylit.py`, `POST /api/flujo/skylit`)
- Criterios del video, no reglas validadas ni recomendación de comprar opciones:
  - prima ≥ USD 100 000 (precio × tamaño × multiplicador, moneda USD);
  - DTE ≤ 183;
  - volumen del contrato / OI ≥ 10;
  - fuera del dinero;
  - subyacente acción;
  - una sola pata;
  - precio ≥ ask del NBBO del instante.
- Prima, volumen y OI se muestran por separado. Cada criterio es `cumple`, `no_cumple` o `no_evaluable` (falta NBBO, condición, patas, OI u OI = 0, spot, clase o multiplicador).
- Una operación «pasa» solo si los 7 criterios se cumplen. `filtro_completo_aplicado` es falso si alguno no fue evaluable.
- Entrada: CSV con la plantilla `GET /api/flujo/skylit/plantilla`. No se guarda nada; la calidad es «importado».
- Volumen/OI no prueba apertura de posiciones: el OI tiene desfase y la operación puede cerrar, cubrir o ser parte de una estructura.
- Con las fuentes gratuitas no es completo: Alpaca trae operaciones indicativas con condición, pero no el NBBO del instante, las patas ni el OI (`docs/proveedores-gratuitos.md`).
- Pruebas: `tests/test_preregistro_skylit.py` (17).
