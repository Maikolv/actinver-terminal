# Protocolo de robustez (preregistro, 6-oct-2026)

Este documento se escribió **antes** de ejecutar el protocolo. Lo que cambie después de ver resultados se agrega en
una sección «Enmiendas», con fecha y motivo, y se marca como exploratorio.

## Qué existía antes y qué agrega este protocolo

| Pieza | Antes | Este protocolo |
|---|---|---|
| Walk-forward | `optimizador._walk_forward` (historia común); `validacion_extendida` (panel dinámico V1); `investigacion/evaluacion` (70/15/15 con embargo, purga y prueba intacta para pronósticos) | Walk-forward **anidado**: los parámetros se eligen solo con datos de cada ventana de entrenamiento; resultados encadenados y un tramo final intacto |
| Estabilidad | `sensibilidad`: 4 variantes (ventana de 2 y 4 años, aversión ×0.5 y ×2) e índice de cambio de pesos | Cuadrícula completa con vecinas inmediatas, índice publicado y detección de picos aislados |
| Monte Carlo | No existía (solo bootstrap para intervalos) | El mismo número de simulaciones en **cada** combinación |
| SPP, mapas de calor, clústeres | No existían | Mapas por pares, mediana SPP y regiones contiguas con regla de vecindad explícita |

## 1. Diseño del experimento

**Separación de conceptos.** La *historia de entrenamiento* (cuántas sesiones se usan para estimar) es un parámetro
del experimento. El *horizonte de inversión* es fijo: las sesiones BMV que faltan hasta el cierre del Reto,
13-nov-2026 15:00. Lo calcula `reto.horizonte_anios` y no se toca para mejorar ningún resultado.

**Parámetros que afectan la selección de activos** (optimizador media-varianza de la terminal, `optimizador._modelo`):

| Parámetro | Qué controla | Valores (pasos fijos) | Restricción |
|---|---|---|---|
| λ, aversión al riesgo | Cuánto castiga la varianza: λ bajo concentra en lo de mayor rendimiento esperado | 0.25, 0.5, 1, 2, 4, 8 (escala ×2) | Incluye la lente «máximo rendimiento» (0.5) y el perfil moderado (4) |
| Tope por activo | Peso máximo por emisora | 0.10, 0.12, 0.15, 0.175, 0.20 | ≤ 0.20, para garantizar ≥ 5 emisoras (regla del Reto) y ≤ 50 % por emisora |
| Historia de entrenamiento | Sesiones usadas para estimar μ y Σ en cada rebalanceo | 126, 168, 252, 378, 504 | ≤ la historia disponible del instrumento (panel dinámico) |

Cuadrícula completa: 6 × 5 × 5 = **150 combinaciones por universo** («acciones» y «mixta»). Todas entran al
experimento y no se muestrea. Si el tiempo o la memoria no alcanzaran, la reducción se documentaría aquí **antes**
de evaluar.

Se mantienen fijos, como en la terminal:
- rebalanceo cada 21 sesiones y banda de 2 puntos;
- regularización L2 de 0.001;
- tope de exposición al dólar del perfil (75 %);
- sin cortos ni apalancamiento.

**Datos y controles** (se registran en `data/robustez/<corrida>/preregistro.json` antes de calcular):
- **Universo:** el elegible del Reto en `optimizador.universo`. Catálogo del simulador, excluye vencidos, apalancados
  e inversos, y exige 250 sesiones de historia.
- **Precios en MXN** (`mercado.precios_mxn`):
  - el SIC es la bolsa de origen × FIX de Banxico de la misma fecha (o el anterior, con límite). Es **precio de
    referencia, no cotización ejecutable del SIC**;
  - ajuste solo por splits, porque el Reto no reproduce dividendos (`reto.yaml`);
  - sin tipo de cambio, el dato queda vacío: nunca se inventa.
- **Costos base:** comisión del Reto, 0.116 % con IVA, sobre el giro (`costo_unitario`).
- **Semilla base:** 20261113. La semilla de cada combinación es la base más su índice, y se guarda.
- **Fechas:** las pruebas comienzan en la sesión 504 de la historia común, igual para todas las combinaciones, así
  que todas se comparan en las mismas fechas.
- **Tramo final intacto:** las últimas **63 sesiones**. No se usa para estabilidad, Monte Carlo, clústeres,
  umbrales ni selección. Se evalúa **una vez** al final.

## 2. Estabilidad de parámetros

Vecinas inmediatas: las combinaciones que difieren en **un** paso de **un** parámetro (vecindad de von Neumann; hasta
6 vecinas). Métricas antes del tramo intacto, netas de costos:
- R: rendimiento anualizado;
- D: caída máxima;
- V: volatilidad anual;
- w̄: pesos promedio.

**Índice de estabilidad**, con N(c) = c y sus vecinas:

  S(c) = 1 − ¼ · [ min(1, sd_N(R)/0.10) + min(1, sd_N(D)/0.10) + min(1, sd_N(V)/0.10) + min(1, C_N(c)/0.50) ]

donde C_N(c) es el promedio, sobre las vecinas, de ½·Σ|w̄_c − w̄_v|: el cambio de composición, de 0 a 1.
- S = 1: perfectamente estable.
- **Umbral:** S ≥ 0.60.

**Pico aislado:** R(c) − mediana_vecinas(R) > 0.10 (10 puntos anuales) **y** R(c) en el decil superior de la
cuadrícula. Se penaliza usando el **rendimiento robusto** R̃(c) = mediana de R en N(c), y no R(c), para elegir.

## 3. Monte Carlo (en todas las combinaciones)

- **Mismo número de simulaciones para todas:** M = 500. Se prueba que ninguna quede con menos.
- **Base:** la serie diaria fuera de muestra de cada combinación (antes del tramo intacto), con su giro por fecha.
- **Remuestreo:** bloques de 10 sesiones con inicio aleatorio, lo que conserva la dependencia temporal. Como cada
  día se toma completo para todos los activos, también se conserva la correlación entre activos.
- **Horizonte simulado:** el del Reto (sesiones restantes al cierre).
- **Perturbaciones por simulación**, uniformes:
  - multiplicador de comisión en [0.75, 2.0];
  - deslizamiento en [0, 15] pb por unidad de giro;
  - diferencial cambiario y de ejecución del SIC en [0, 60] pb por unidad de giro en activos del SIC (en el portal se
    midió una mediana de 32 pb frente a la referencia, el 5-oct);
  - la fecha de inicio la aporta el remuestreo.
- **Se informa:**
  - percentiles 5, 50 y 95 del rendimiento neto y de la caída máxima en el horizonte;
  - probabilidad de pérdida;
  - riesgo de cola (CVaR 5 %: media del 5 % peor).

## 4. SPP y clústeres

- **SPP (System Parameter Permutation):** distribución del resultado de **todas** las combinaciones. Su mediana es la
  estimación no sesgada del desempeño esperado del sistema.
- **Mapas de calor por pares** (λ × tope, λ × historia, tope × historia), con filtro de la tercera dimensión. Cada
  celda muestra el rendimiento fuera de muestra, la probabilidad de pérdida y el p5 del Monte Carlo, y S(c).
- **Combinación aprobada:** cumple los cinco umbrales.
  1. Exceso fuera de muestra frente a 1/N (mismas fechas y universo) > 0.
  2. Probabilidad de pérdida en el horizonte (Monte Carlo) ≤ 45 %.
  3. p5 de la caída máxima en el horizonte (Monte Carlo) ≥ −20 %.
  4. S(c) ≥ 0.60.
  5. No es pico aislado.
- **Regiones:** componentes conexas de combinaciones aprobadas con la misma vecindad de von Neumann (búsqueda en
  anchura).
  - **Meseta:** región de ≥ 5 combinaciones.
  - **Máximo aislado:** región de 1–2 combinaciones, o pico aislado.
  - Por región se informa tamaño, dispersión de R (desviación y rango) y porcentaje de la cuadrícula que aprueba.
  - Para la combinación elegida, su distancia al borde: pasos hasta la celda más cercana fuera de la región. El
    límite de la cuadrícula cuenta como borde.
- **Regla de elección:** dentro de la meseta más grande, la combinación con mayor R̃(c); si empatan, la más alejada del
  borde. Sin meseta, el veredicto es «sin región robusta» y se recomienda la configuración vigente.

## 5. Walk-forward anidado

- Las series fuera de muestra de cada combinación ya son causales: los pesos de cada prueba se estiman con datos
  anteriores a su inicio.
- **Selección:** en cada frontera b (cada 63 sesiones, desde que hay 252 sesiones de historia fuera de muestra), se
  aplica la regla del § 4 solo con las 252 sesiones **anteriores** a b. Usa los umbrales 1, 4 y 5; el Monte Carlo
  completo es para el informe estático. La combinación elegida se usa las 63 sesiones siguientes.
- **Separación:** el rebalanceo ocurre en la frontera y los pesos se estiman con datos anteriores, así que no hay
  posiciones ni etiquetas solapadas entre selección y prueba (embargo 0, justificado). Una prueba verifica que toda
  fecha de selección sea anterior a la de su prueba.
- **Encadenado y comparación:** contra la **estrategia actual** (lente máximo rendimiento: λ 0.5, tope 0.20,
  historia 168; y lente ajuste: λ 4, tope 0.12, historia 168), contra **1/N** y contra la **mediana SPP**.
- **Tramo intacto:** la última selección se hace en su inicio, con datos anteriores, y se evalúa una sola vez.
- **«Evidencia insuficiente»** si el encadenado tiene menos de 252 sesiones, si hay menos de 4 fronteras o si el
  tramo intacto tiene menos de 42 sesiones.

## 6. Integración

- Vista «Robustez» y `/api/robustez`.
- Las propuestas cuyos parámetros caen en una combinación no aprobada o en un pico aislado se marcan **frágiles** y
  no pueden ser la referencia del plan si hay otra opción.
- En propuestas, Telegram y reportes se separan tres cosas:
  - **histórico fuera de muestra**: lo que ya pasó;
  - **simulación Monte Carlo**: remuestreo del pasado;
  - **pronóstico/estimación**: modelo hacia adelante.

  Ninguna es garantía.
- **Ejecución por lotes y reanudable:** cada combinación se guarda al terminar y una corrida interrumpida retoma
  donde quedó.

## Resultados (corrida del 6-oct-2026, datos al 5-oct-2026)

Comando: `uv run terminal robustez --tipo ambos` (reanudable). Tiempo: acciones 893 s, mixta 1,214 s; pico de memoria
337–355 MB. Resultados en `data/robustez/<tipo>_<huella>/` (locales, fuera de Git):
`preregistro.json`, `combos/*.npz` con semilla por combinación y `resumen.json`.

**Fechas:** historia 28-sep-2021 a 5-oct-2026 (1,267 sesiones). Fuera de muestra: 29-sep-2023 a 8-jul-2026 (700
sesiones). Tramo intacto: 9-jul a 5-oct-2026 (63 sesiones). Horizonte de la simulación: 28 sesiones, al cierre del
Reto. **Cobertura:** 150 combinaciones × 500 simulaciones en cada universo, ninguna omitida.

| | Acciones | Mixta (acciones + ETF + fondos) |
|---|---|---|
| Mediana SPP (rend. anual de todas las combinaciones) | +35.3 % | +36.8 % |
| Combinaciones que superan a 1/N / que aprueban los 5 umbrales | 71 % / 66 % | 96 % / 79 % |
| Región | 1 meseta de 99 (R medio +37.8 %, desv. 6.4 pts) | 1 meseta de 118 (+36.7 %, desv. 5.4 pts) |
| Picos aislados | 0 | 1 |
| Elegida por la regla | λ 0.25 · tope 20 % · historia 504 (S 0.81) | λ 0.5 · tope 20 % · historia 504 (S 0.78) |
| Elegida: histórico (R, exceso vs 1/N, caída máx.) | +49.9 %, +21.6 pts, −35.8 % | +45.5 %, +19.0 pts, −34.7 % |
| Elegida: simulación al cierre (p5 / p50 / p95, prob. pérdida, caída p5) | −12.4 % / +4.7 % / +22.9 %, 34 %, −19.4 % | −12.6 % / +4.9 % / +21.2 %, 32 %, −18.9 % |
| **Actual «máximo rendimiento»** (λ 0.5 · 20 % · 168) | +36.1 %, +12.8 pts; S 0.63; caída p5 **−23.1 %** ⇒ no aprobada (riesgo) | +48.4 %, +24.9 pts; S 0.68; caída p5 **−24.2 %** ⇒ no aprobada (riesgo) |
| Actual «ajuste» (λ 4 · 12 % · 168) | no aprobada: exceso vs 1/N −2.7 pts | **aprobada** (+36.0 %, +10.9 pts, caída p5 −14.9 %) |
| **Walk-forward anidado, encadenado** (448 sesiones, 8 fronteras): anidado / actual / 1/N / mediana diaria de combinaciones | +33.5 % / **+39.2 %** / +16.0 % / +17.6 % anual | +33.0 % / **+47.2 %** / +14.6 % / +25.2 % anual |
| **Tramo intacto** (63 sesiones, acumulado) | +35.7 % / **+45.6 %** / +6.7 % / +1.2 % | +3.8 % / **+46.6 %** / +6.4 % / +2.6 % |

**Lectura:**
1. Los parámetros del optimizador están en una **meseta amplia**: 66–79 % de la cuadrícula aprueba y la dispersión es
   de unos 6 puntos. No dependen de un punto con suerte.
2. La selección anidada **no supera** a la configuración actual de máximo rendimiento, ni encadenada ni en el tramo
   intacto. Elegir parámetros con el protocolo reduce el riesgo de cola, pero no mejora el rendimiento fuera de muestra.
3. La configuración actual de máximo rendimiento falla **solo** el umbral de riesgo de cola: en 1 de cada 20
   simulaciones cae más del 20 % antes del cierre. Su estabilidad es aceptable (S ≥ 0.6) y no es pico aislado.
4. Todo esto ocurre en un periodo muy alcista para semiconductores (2023–2026), y el tramo intacto (jul–oct-2026)
   también lo es. Nada de esto es un pronóstico.

**Parámetros:** no se cambian automáticamente. La evidencia fuera de muestra no muestra que la regla elegida rinda
más que la configuración actual; solo que arriesga menos. Hacerlo es decisión del usuario (ver abajo).

## Enmiendas

**Enmienda 1 (6-oct-2026, después de ver resultados; exploratoria).** El § 6 decía que toda combinación no aprobada
se marcaría «frágil» y no podría ser la referencia. Las propuestas vigentes (λ 0.5 · 20 % · ≈ 252 sesiones) no son
inestables: S ≈ 0.6–0.7 y sin pico. Fallan solo el umbral de caída p5, por poco: −20.1 % en acciones y −21.8 % en
mixta. Aplicar la regla tal cual cambiaba el plan del usuario y contradecía su decisión D-50 («prioridad: mayor
ganancia»). Se separan dos estados:
- **frágil** (pico aislado o S < 0.60): no puede ser la referencia del plan si hay alternativa;
- **no aprobada** (estable, pero falla rendimiento o riesgo): se informa con sus motivos en lenguaje sencillo y la
  decisión queda en el usuario.

Los umbrales y la regla de elección **no** cambiaron.

**Enmienda 2 (6-oct-2026, escrita ANTES de correr la variante; exploratoria).** Variante «proxy ADR» como
alternativa gratuita a la historia de pago de EODHD (`terminal/proxy_adr.py`, `scripts/historia_adr.py`).
- **Qué cambia:** solo los datos. Las emisoras BMV cuyo ADR (Tiingo, clave gratuita) tiene correlación diaria ≥ 0.80
  con la serie local, en ≥ 120 sesiones comunes, se extienden hacia atrás con el rendimiento del ADR en MXN (FIX de
  cada fecha, solo splits).
- **Qué no cambia:** cuadrícula, umbrales, Monte Carlo, regla de elección y walk-forward.
- **Uso:** corrida aparte (`uv run terminal robustez --proxy-adr`). Se compara con la principal y **no cambia
  parámetros ni propuestas**; sirve para saber si la conclusión se sostiene cuando las emisoras nacionales entran
  con historia larga.
- **Validación del 6-oct:**

  | | Emisoras | Correlación |
  |---|---|---|
  | Aceptadas | AMX, FEMSA, CEMEX, ASUR, GAP, KOF, GFNORTE, KIMBER | 0.89–0.96 |
  | Rechazadas | BIMBO, GMEXICO (ADR OTC poco operados) | 0.52 y 0.75 |
  | Sin datos para validar | OMA, TLEVISA, VESTA, VOLAR, WALMEX, GCARSO, ORBIA, PE&OLES (sin historia local) | — |
