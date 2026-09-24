# Metodología cuantitativa

Complementa [investigacion.md](investigacion.md), que detalla las fórmulas de división, embargo y purga. Código: `terminal/investigacion/`, `terminal/optimizador.py`, `terminal/comparador_modelos.py`.

## 1. Datos y limpieza

- **Series y símbolos:** `normalizar_simbolo` y `correspondencia_simbolos` separan BMV local, SIC y origen extranjero. `clasificacion.py` rechaza CFD y cripto.
- **Zona horaria y moneda:**
  - Todo `event_time`, `available_at` e `ingested_at` se guarda en UTC y se muestra en America/Mexico_City.
  - El USD se convierte solo con un tipo de cambio vigente; si no lo hay, la valuación queda vacía y no se inventa.
- **Huecos y calendarios:** se usan XMEX y XNYS (`exchange-calendars`). Un precio sin sesión en su calendario recibe el fin del día de Nueva York, que es conservador.
- **Splits:** se aplican solo si su `available_at` ≤ T. Los dividendos no se ajustan, porque el Reto no los paga (§13).
- **Duplicados:** para una misma fecha de dos proveedores se conserva el dato conocido primero.
- **Instrumentos inactivos o supervivencia:** se incluyen los que tienen estado `por_confirmar` o están deslistados, con su motivo. El universo parte del PDF y no de los sobrevivientes de hoy. El sesgo residual está documentado: sin historia de emisoras ya deslistadas.
- **Volumen:** la variable `vol_rel20` usa el logaritmo del volumen relativo a su media de 20 sesiones. Si no hay volumen (índices de FRED) se imputa de forma constante (`keep_empty_features`).

## 2. Referencias (no son recomendaciones)

| Referencia | Tipo | Definición |
|---|---|---|
| Cambio cero | pronóstico | 0 |
| Media histórica | pronóstico | media de 60 sesiones × H |
| Tendencia simple | pronóstico | momento de 20 sesiones si el precio está sobre su media de 50; si no, 0 |
| Mantener cartera | estrategia | compra inicial y se conserva |
| Pesos iguales | estrategia | todas las emisoras elegibles, rebalanceo cada H |

## 3. Variables

Todas se calculan con ventanas hacia atrás de L ≤ 60 sesiones:

- retornos de 1, 5, 20 y 60 sesiones;
- volatilidad de 20 y 60 sesiones;
- distancia a las medias de 20 y 50 sesiones;
- RSI de 14 sesiones;
- volumen relativo;
- caída desde el máximo de 20 sesiones;
- retorno del mercado y retorno relativo, ambos de la misma fecha;
- número de noticias de alto impacto **conocidas** en los últimos 5 días.

La exposición sectorial y el tipo de cambio quedan como extensión: requieren datos con disponibilidad trazable.

## 4. Modelos

- Ridge, que es regularizado.
- Ridge con filtro de correlación (|r| ≥ 0.95, ajustado en el entrenamiento).
- PCA + Ridge.
- Kronos como candidato experimental, pendiente de recursos.

Solo se añade complejidad si se supera a las referencias.

## 5. Asignación (skfolio)

El modelo vigente es media-varianza con utilidad, con restricciones del Reto: un máximo por emisora ≤ 50 %, 5 emisoras o más y sin cortos. `comparador_modelos.py` lo compara con 1/N, la inversa de la volatilidad, el mínimo CVaR, la paridad de riesgo y HRP en el mismo walk-forward. `_asignacion_discreta` simula títulos enteros y efectivo remanente. Los costos son 0.10 % + IVA.

## 6. Backtest y verificación cruzada

- **Motor por eventos:** backtrader, usado desde su copia local; es GPL y queda fuera del código MIT.
- **Cálculo de referencia:** uno independiente con las mismas reglas: rebalanceo al cierre, títulos enteros, ventas antes que compras, comisión + IVA.
- **Resultado:** coincidencia exacta en datos sintéticos (72 operaciones) y en índices reales de FRED (diferencia 0.0). Lo cubre `test_backtrader_coincide_con_calculo_independiente`.
- **nautilus_trader:** se leyeron sus modelos de llenado y latencia. No se ejecuta, porque sin libro de órdenes BMV no aporta fidelidad adicional.

## 7. Validación

- División cronológica 70/15/15, embargo ≥ H y purga.
- Walk-forward purgado dentro del entrenamiento; todo lo aprendible se ajusta ahí.
- Prueba final intacta y registro de todos los experimentos (`experimentos`, `prueba_ya_vista`). Es el método tomado de RD-Agent: registrar todos los intentos.
- Métricas:
  - error: MAE y MSE;
  - dirección;
  - calibración: cobertura del intervalo 80 % y Brier;
  - estabilidad mensual;
  - rendimiento neto, caída máxima, rotación y exposición;
  - **sensibilidad a costos** con multiplicadores ×0, ×1, ×2 y ×5;
  - **Diebold-Mariano con Newey-West** frente a cada referencia.
- **Veredicto:** hay «VENTAJA FUERA DE MUESTRA» solo si el error es menor **y** significativo (p < 0.05) frente a las tres referencias, **y** el resultado neto supera también a las estrategias de referencia. En cualquier otro caso: **«SIN VENTAJA DEMOSTRADA»** y no se emite recomendación.

## 8. Escala temporal del Reto

Seis semanas de competencia (~29 sesiones) no bastan para entrenar desde cero. Los modelos se validan con historia anterior comparable (años) y se vigilan durante el Reto con la alerta de **deterioro estadístico** (pronósticos resueltos frente a cambio cero y cobertura del intervalo). No se reentrena para «perseguir» el régimen sin pasar de nuevo por la validación.

## 9. Escenarios de estrés

Módulo `escenarios.py` y pruebas en `test_ampliacion.py`:

- volatilidad ×2 (VaR y CVaR);
- spread adicional;
- precio retrasado;
- suspensión de una emisora;
- falta de cotización SIC;
- noticias contradictorias.

Ante incertidumbre material se **inhiben** las alertas direccionales y se emite una alerta de datos.

## 10. Agentes y LLM

Se evaluaron TradingAgents, AutoHedge, Vibe-Trading, crewAI y RD-Agent. Ningún agente decide ni fabrica precios. El único LLM opcional es local (Ollama) y solo para clasificar titulares.

## 11. Banco de estrategias simples y boleta

- **Hipótesis predefinidas:**
  - impulso a 20, 60 y 120 sesiones;
  - reversión a 5 y 10 sesiones;
  - inversa de volatilidad a 60 sesiones;
  - impulso con tamaño por riesgo.
- **Referencias:** efectivo, pesos iguales, comprar y mantener.
- **Selección:** el parámetro de cada familia se elige solo en el entrenamiento; la prueba se evalúa una vez.
- **Evaluación:** subperiodos anuales, deslizamiento de 0, 0.1 % y 0.5 %, y bootstrap por bloques del exceso diario frente a pesos iguales.
- **Registro:** todas las configuraciones, no solo las ganadoras.
- **Veredicto:** «VENTAJA NO DEMOSTRADA» salvo que se superen efectivo y pesos iguales, se ganen la mayoría de los años y p < 0.05.
- **Pendiente:** sensibilidad al tipo de cambio del SIC y diversificación por sector, porque requieren series BMV y SIC reales y un catálogo con sector.
- **Boleta de decisión:** usa una estimación **histórica** (no el modelo, que no tiene ventaja demostrada). Ver [decision-workflow.md](decision-workflow.md).

