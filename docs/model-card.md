# Ficha del modelo (model card)

| Campo | Valor |
|---|---|
| Nombre | Pronóstico de rendimiento a H sesiones: Ridge con filtro de correlación, Ridge o PCA + Ridge, según la validación |
| Versión | `<versión del código>+<huella de configuración>` en `versiones_modelo` y `pronosticos.version` |
| Semilla | 20261113 |
| Uso previsto | Investigación. Da rangos y probabilidades como **estimaciones** para revisión humana |
| Fuera de alcance | Ejecutar operaciones o decidirlas; sustituir el precio observado; emitir recomendaciones cuando no hay ventaja demostrada |
| Datos | Cierres diarios con `available_at`. Hoy no hay datos BMV reales (sin licencia ni claves) |
| Variables | 14 variables con ventanas hacia atrás (ver quant-methodology §3) |
| Validación | 70/15/15 cronológica, embargo ≥ H, purga, walk-forward purgado, prueba intacta, Diebold-Mariano con Newey-West |

## Resultados fuera de muestra

### Índices reales de FRED (S&P 500, Nasdaq Composite, Dow Jones), 2016–2026

Ejecutado con `scripts/experimento_indices_fred.py`; métricas en [evidencia/experimento_indices_fred.json](evidencia/experimento_indices_fred.json).

| H | Prueba | Modelo elegido | MSE modelo | MSE cambio cero | DM p vs cambio cero | Neto modelo | Mejor neto de las referencias | Veredicto |
|---|---|---|---|---|---|---|---|---|
| 1 | 2025-02-25 → 2026-09-21 | PCA + Ridge | 1.355e-4 | 1.366e-4 | 0.379 | −18.7 % | +33.2 % (media histórica) | **SIN VENTAJA DEMOSTRADA** |
| 5 | 2025-02-25 → 2026-09-15 | PCA + Ridge | 5.477e-4 | 5.697e-4 | 0.126 | +37.8 % | +36.4 % (tendencia simple) | **SIN VENTAJA DEMOSTRADA** |

En H=5 el error es menor que el de las tres referencias:

- frente a la media histórica y la tendencia simple la diferencia es significativa (p ≈ 0.038 y 0.035);
- frente al cambio cero **no** lo es (p = 0.126).

Además, la caída máxima del modelo (−16.4 %) es peor que la de la tendencia simple (−9.8 %). Solo son 3 índices muy correlacionados (correlación media en el entrenamiento en el JSON) y hay un solo periodo de prueba. **Conclusión:** no hay ventaja demostrada y no se emite recomendación.

### Datos sintéticos de la demo

No tienen valor para el mercado real. El modelo no supera a las referencias en H=1 ni en H=5, como se espera de datos aleatorios.

## Limitaciones y riesgos

- Sin datos BMV licenciados no hay evaluación en el universo real del Reto.
- El embargo y la purga evitan fugas de información; **no** garantizan que el modelo acierte.
- La probabilidad de subida está calibrada con residuos de validación; su cobertura observada fue de 0.75 a 0.80 contra el 0.80 nominal.
- Kronos está pendiente de autorización para descargar torch y sus pesos.

## Banco de estrategias simples frente a referencias (índices reales de FRED)

Script: `scripts/experimento_estrategias.py`; código: `terminal/investigacion/estrategias.py`.

- **Periodos:** entrenamiento 2016-09-26 → 2023-09-19; embargo de 5 sesiones; prueba 2023-09-27 → 2026-09-22.
- **Parámetros elegidos solo con el entrenamiento** (mayor Sharpe): {'impulso': {'L': 60}, 'reversion': {'L': 10}, 'inversa_vol': {'L': 60}, 'impulso_riesgo': {'L': 60, 'Lv': 60}}.
- **Configuraciones registradas:** 28.
- **Ejecución:** señal con el cierre de t, operación al cierre de t+1; rebalanceo cada 5 sesiones; tope de 50 %; costo de 0.116 % + deslizamiento de 0.1 %.

| Estrategia | Parámetros | Neto de la prueba | Neto con deslizamiento 0.5 % | Sharpe | Caída máx. | Rotación | Años mejores que pesos iguales | p (bootstrap) | Veredicto |
|---|---|---|---|---|---|---|---|---|---|
| efectivo | — | +0.0% | +0.0% | 0.00 | +0.0% | 0.0 | 0/4 | — | referencia |
| pesos_iguales | — | +79.2% | +77.9% | 1.33 | -19.5% | 1.8 | 0/4 | — | referencia |
| comprar_y_mantener | — | +79.9% | +79.2% | 1.33 | -19.7% | 1.0 | 3/4 | — | referencia |
| impulso | {'L': 60} | +55.2% | +39.6% | 1.23 | -10.6% | 26.4 | 0/4 | 0.834 | VENTAJA NO DEMOSTRADA |
| reversion | {'L': 10} | +61.7% | +24.3% | 1.08 | -20.8% | 65.6 | 0/4 | 0.983 | VENTAJA NO DEMOSTRADA |
| inversa_vol | {'L': 60} | +76.0% | +73.7% | 1.33 | -18.9% | 3.2 | 0/4 | 0.949 | VENTAJA NO DEMOSTRADA |
| impulso_riesgo | {'L': 60, 'Lv': 60} | +55.2% | +39.6% | 1.23 | -10.6% | 26.4 | 0/4 | 0.834 | VENTAJA NO DEMOSTRADA |

**Veredicto global: VENTAJA NO DEMOSTRADA.** Ninguna regla supera a pesos iguales ni en resultado neto ni en años ganados (p entre 0.83 y 0.98). Con solo 3 índices, «impulso con riesgo» coincide con «impulso», porque el tope del 50 % iguala los pesos. Se conserva la estrategia base transparente: diversificación con reglas del Reto (skfolio), sin señales direccionales.

