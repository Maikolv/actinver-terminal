# Pronóstico al cierre del Reto

Extiende `terminal/investigacion/` (no es un sistema aparte). Código: `terminal/investigacion/reto_pronostico.py`,
`pronosticos.py`, `evaluacion.py`, `datos.py`. Pruebas: `tests/test_pronostico_reto.py` y `tests/test_investigacion.py`.

## Qué emite

| Horizonte | Etiqueta | Fecha objetivo |
|---|---|---|
| 1 sesión | `1s` | sesión siguiente en el calendario del instrumento (NYSE para el SIC y BMV para el resto) |
| 5 sesiones | `5s` | quinta sesión siguiente en ese calendario |
| Dinámico | `reto` | 13-nov-2026: sesiones de la BMV desde la última sesión cerrada (31 el 30-sep-2026; el 2-nov es feriado) |

Cada fila de `pronosticos` guarda la fecha de emisión, la hora en que los datos estaban disponibles, la fecha base (último cierre usado), la fecha objetivo, el precio base en MXN, la estimación central, el rango 10–90 %, la probabilidad de subida, el modelo, la versión (`<código>+<huella de configuración>`), la semilla y si la barrera permitía usarla.

- **En pesos.** El Reto se mide en MXN. Los cierres del SIC (Tiingo/Alpaca, bolsa de EE. UU.) se convierten con el USD/MXN de su misma fecha (o el previo, hasta 5 días) y solo si ese tipo de cambio ya se había publicado (`available_at` del FX ≤ hora de corte). La fila convertida se conoce a la hora más tardía de ambos datos. Sin tipo de cambio, la fila se descarta, no se inventa. El rendimiento incluye así el riesgo cambiario.
- **Precio base.** Es el último cierre observado, no una cotización en vivo. En el SIC es una referencia de la bolsa de EE. UU. × tipo de cambio, nunca un precio ejecutable del SIC.
- **Rango por emisora.** Los residuos de validación se estandarizan con la volatilidad de 60 sesiones de cada emisora (conocida en la fecha base) × √H. Antes, un bono y una acción volátil recibían el mismo rango.
- **Cotización vencida.** Una emisora cuyo último cierre tiene más de 2 sesiones de atraso se marca «VENCIDO» y no entra al pronóstico de la cartera ni a la comparación de propuestas.
- **Sin ocultar.** Se listan las emisoras con historia insuficiente (mínimo 60 + H + 5 sesiones) y las que no tienen precios.

## Cartera y propuestas

- **Cartera.** Usa las posiciones y el efectivo (más los movimientos por liquidar) de la última captura del portal. Si no hay captura, usa el registro local y lo dice: «Cartera NO conciliada con el portal».
- **Rango de la cartera.** Suma los extremos de cada posición, como si todas se movieran juntas. Es conservador y no es la distribución de la cartera.
- **Comparación de propuestas.** Cada propuesta vigente y «Mantener mi cartera» se comparan con el pronóstico mediante:
  - rendimiento estimado neto del costo de rebalanceo (comisión + IVA, el que calcula el optimizador);
  - rango y peso con pronóstico;
  - exposición al SIC (incluye el tipo de cambio);
  - cumplimiento de las reglas del Reto;
  - si el catálogo del simulador importado cambió.
- **Propuesta del plan.** Se indica la propuesta de máxima puntuación y si difiere de la de mayor rendimiento estimado.

## Barrera entre investigación y decisiones

El pronóstico solo puede influir en compras, ventas o boletas si cumple **todos** estos criterios (`reto_pronostico.barrera`):

1. La prueba final tiene al menos 3 periodos sin traslape del horizonte.
2. La prueba final está intacta: no se usó antes con otra configuración (`prueba_ya_vista`).
3. Su error es menor que el de cada referencia («sin cambio», media histórica y tendencia simple), con Diebold-Mariano (Newey-West) p < 0.05.
4. Su resultado neto de costos es mejor que «sin cambio» (mantener), que pesos iguales y que la **estrategia actual**: top-k por la media histórica de 60 sesiones, el estimador del optimizador.
5. No hay deterioro en los pronósticos ya resueltos (error/«sin cambio» < 1), cuando hay al menos 30.

Si falla cualquiera, se muestra **«señal experimental: sin ventaja demostrada»**, se guarda `recomendacion_permitida = 0` y el plan sigue el método actual. Una prueba comprueba que `plan_accion`, `boleta`, `optimizador`, `resumen` y `ranking` no leen la tabla de pronósticos.

## Validación

- **Sin fuga de información.** Las variables y etiquetas se construyen solo con filas cuyo `available_at` ≤ hora de emisión. Las pruebas cubren: un tipo de cambio publicado después, la modificación de precios futuros y la ausencia de tipo de cambio.
- **Corte cronológico.** 70/15/15, con embargo = max(H, mínimo) y purga de las etiquetas que cruzan el corte. Walk-forward purgado para elegir alfa; validación para elegir la variante y calibrar el rango; prueba final intacta.
- **Registro.** Cada experimento se guarda en `experimentos` con su configuración, huella, semilla, cortes y métricas. La versión del modelo se guarda en `versiones_modelo`.
- **Métricas.** MSE y MAE, acierto de dirección, calibración por tramos de probabilidad, Brier, cobertura del rango 80 %, resultado neto de costos con sensibilidad ×0/×1/×2/×5, rotación, caída máxima y métricas por mercado (BMV y SIC).

## Resultados reales (emisión del 1-oct-2026, datos al 30-sep-2026)

Son 130 instrumentos con historia suficiente (23 BMV y 107 SIC). Quedan fuera 23 fondos, con solo 2 NAV, y 21 instrumentos sin precios.

| H | Prueba | MSE modelo / «sin cambio» | DM p vs «sin cambio» | Neto modelo | Mantener | Pesos iguales | Estrategia actual | Dirección | Cobertura 80 % | Veredicto |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-01-20 → 09-29 | 1.000 | 0.451 | −35.4 % | +8.8 % | +9.4 % | +24.5 % | 50.8 % | 75.6 % | SIN VENTAJA |
| 5 | 2026-01-20 → 09-23 | 1.001 | 0.634 | −4.4 % | +12.6 % | +12.5 % | +8.8 % | 50.5 % | 76.1 % | SIN VENTAJA |
| 31 (Reto) | 2026-01-23 → 08-17 | 1.009 | 0.720 | −0.0 % | +4.5 % | +2.2 % | −1.1 % | 49.5 % | 77.0 % | SIN VENTAJA |

El error relativo a «sin cambio» por mercado, a 31 sesiones, es de 1.05 en la BMV (dirección 42 %) y de 1.01 en el SIC (dirección 51 %).

**Calibración.** A 31 sesiones, cuando el modelo estimaba una probabilidad de subida de 70 % o más (868 casos, media 77 %), la emisora subió el 49 % de las veces. **La probabilidad de subida no es fiable.** La terminal y Telegram lo advierten cuando el desvío de algún tramo supera 10 puntos.

**Conclusión.** No hay ventaja demostrada en ningún horizonte. El pronóstico **no** maximiza la ganancia: es una señal experimental que no cambia el plan.

## Auditoría de la probabilidad de subida (6-oct-2026)

Módulo `terminal/investigacion/calibracion.py`, integrado en cada experimento (`calibracion_auditoria`). Todo se
mide en la **prueba intacta** (fechas posteriores a la validación):
- Brier del modelo frente a la **frecuencia base** de subidas conocida antes de la prueba y frente a 0.5;
- curva de confiabilidad en 10 tramos;
- recalibración **isotónica** y **Platt**, ajustadas solo con la validación;
- IC 90 % por bootstrap de fechas completas, porque las emisoras de un mismo día están correlacionadas y las
  etiquetas a H sesiones se solapan.

Criterio, fijado antes de medir: se considera «calibrada» solo si el Brier es menor que el de la frecuencia base con
un IC 90 % entero bajo cero y el desvío máximo de la curva es ≤ 10 puntos en tramos con n ≥ 30.

| H | Prueba (n · fechas) | Frecuencia base | Brier base | Brier modelo [dif. IC 90 %] | Isotónica | Platt | Desvío máx. | Veredicto |
|---|---|---|---|---|---|---|---|---|
| 1 | 30,403 · 181 (ene–oct-2026) | 49.8 % | 0.2500 | 0.2515 [+0.0002, +0.0027] | 0.2504 | 0.2502 | 17 pts | experimental |
| 5 | 29,538 · 176 | 50.2 % | 0.2500 | 0.2523 [+0.0002, +0.0044] | 0.2507 | 0.2506 | 20 pts | experimental |
| 28 (al cierre del Reto) | 25,214 · 150 | 51.2 % | 0.2502 | 0.2613 [+0.0085, +0.0139] | 0.2597 | 0.2598 | 41 pts | experimental |

**Lectura:**
- En los tres horizontes la probabilidad es **peor** que decir siempre «≈ 50 %», y la diferencia es significativa.
- Recalibrada (isotónica o Platt), queda al nivel de la frecuencia base, sin superarla: el modelo no tiene
  información direccional demostrable.
- A 28 sesiones, la curva llega a desviarse 41 puntos: cuando decía 83 %, subió el 42 % de las veces.

**Qué cambió:**
- La probabilidad queda marcada como **EXPERIMENTAL**.
- En Telegram (`/pronostico`) ya no aparece junto a cada emisora: hay una sola línea con el Brier frente a la
  frecuencia base.
- En la pestaña Futuro, su columna se llama «Prob. subida (experimental)» y va en gris.
- No es, ni se convierte en, señal de compra.
- Tamaño de muestra e incertidumbre: los de la tabla. Datos al 2-oct-2026, cortes 70/15/15.

## Recursos

- **Memoria y tiempo.** La emisión de los tres horizontes con 130 instrumentos tarda unos 140 s y su memoria pico es de 0.36 GB, medida en un equipo de 5.9 GB.
- **Kronos.** No se añadió. La única prueba medida (`scripts/experimento_kronos.py`) se quedó sin memoria y no hay evidencia de que mejore fuera de muestra.

## Uso

- **Terminal.** «Boletas e historial» → FUTURO:
  - «Calcular investigación y pronósticos» emite los tres horizontes en 2–3 min;
  - «Enviar pronóstico por Telegram» manda el resumen.
- **Automático.** El monitor emite una vez por sesión cerrada, en segundo plano. Se desactiva con `[investigacion] emitir_diario = false`.
- **Telegram.** `/pronostico`. El reporte diario (`uv run terminal reporte cierre`) incluye la misma sección.
- **Línea de comandos.**
  - `uv run terminal investigar` emite 1 y 5 sesiones y el horizonte del Reto (`--sin-reto` lo omite).
  - `uv run terminal pronostico` muestra el resumen.
- **API.**
  - `GET /api/pronostico`
  - `POST /api/pronostico/telegram` (`{"enviar": false}` solo devuelve el texto)
