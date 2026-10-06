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
