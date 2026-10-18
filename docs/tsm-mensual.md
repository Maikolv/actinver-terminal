# Protocolo: momentum temporal (TSM) mensual, largo/efectivo — versión 1.0

Elección del usuario (17-oct-2026): investigación **A**. Es un experimento **educativo**, separado de la estrategia
activa (propuestas, plan y cartera no cambian) y del momentum transversal diario existente. No se traslada a operación
intradía ni a Lucid. Código: `terminal/tsm_mensual.py` (`tsm-mensual 1.0`). Pruebas: `tests/test_tsm_anomalias.py`.

## 1. Origen de cada regla

| Regla | Origen |
|---|---|
| Chequeo una vez al mes; se cierra la posición opuesta y se decide de nuevo | Contenido del autor (reel DejEnwmBclA) |
| Comparar el último cierre mensual con el de 3, 6 o 12 meses antes | Contenido del autor |
| Lookback por mercado elegido solo con datos antiguos | Contenido del autor |
| Largo si subió; fuera si bajó (corto solo en forex, que no se usa aquí) | Contenido del autor |
| Sin stop ni target: decide el siguiente chequeo | Contenido del autor |
| Tamaño por rango diario medio | Contenido del autor (sin periodo ni importe) |
| Cita a Kakushadze/Serur | Dato contrastado: [arXiv 1912.04492](https://arxiv.org/abs/1912.04492); el registro de Springer figura como RETRACTED BOOK (motivo no verificado) |
| Igualdad = fuera | **Supuesto propio** |
| Señal al cierre de la última sesión del mes; ejecución al cierre de la sesión siguiente | **Supuesto propio** (evita fuga temporal) |
| Rango = media de \|rendimiento diario\| de 20 sesiones (proxy: la historia externa no tiene máximos/mínimos) | **Supuesto propio**, desactivado por omisión |
| Riesgo por omisión: exposición completa (1) cuando es largo | **Supuesto propio** |
| Costo por cambio de exposición: comisión + IVA del Reto + 5 pb de deslizamiento | **Supuesto propio** |
| Selección de L: mayor media mensual neta en entrenamiento, con mínimo de 24 meses | **Supuesto propio** |
| Mercados: SPY, QQQ, DIA, EEM, GLD y NAFTRAC (ETF, no contratos US100/US500 ni NQ/ES) | **Supuesto propio** |

Pendientes del autor, sin los cuales **no hay reproducción fiel**:
- periodo del rango e importe de riesgo;
- igualdad;
- dataset y licencia;
- instrumento exacto;
- fechas de entrenamiento;
- entrada y fills;
- costos completos (comisión y swap).

Su especificación ofrecida por DM («MOMENTUM») no se recuperó ni se solicitó.

## 2. Datos

Historia externa del usuario (`docs/historia-externa.md`): cierres diarios en moneda de origen hasta el 9-oct-2025. Es
local y de uso personal. Tiene sesgo de supervivencia, porque el universo se eligió hoy. No hay ticks ni swaps.

## 3. Preregistro (antes de mirar el holdout)

- **Configuración por omisión:**
  - corte en 2018-01: entrenamiento con ejecuciones anteriores;
  - embargo de 1 mes y holdout desde 2018-02;
  - B = 4,999, semilla 2026, bloque de 3 meses, α = 0.05.
- **H0:** el exceso medio mensual neto de TSM sobre comprar y mantener el mismo ETF es ≤ 0.
- **H1:** el exceso es > 0, unilateral.
- **Familia:** 3 lookbacks × 6 mercados = 18 variantes. Holm cuenta las 18, aunque solo se contraste el L elegido por mercado.
- **Fracaso:** que ningún mercado tenga p de Holm ≤ 0.05. Se reporta igual.
- **Rutas:**
  - `POST /api/investigacion/tsm/preregistro` guarda la configuración con huella sha256;
  - `POST /api/investigacion/tsm/{id}/evaluar` evalúa una sola vez; repetir devuelve lo guardado;
  - `GET /api/investigacion/tsm` lista los experimentos.

## 4. Controles

- **Sin fuga temporal:** la señal usa cierres hasta la última sesión del mes. Cambiar precios posteriores no altera la exposición (probado).
- **Mes incompleto:** no genera señal.
- **Holdout de un solo uso:** cuando se elige L con el entrenamiento, la configuración queda congelada.
- **Huellas** de la configuración y de los datos.

## 5. Resultado

Ver §6, si ya se ejecutó. Un exceso negativo o no significativo es un resultado válido y se publica igual. Es una
simulación histórica con supuestos propios, no ganancias obtenidas ni una recomendación.

## 6. Resultado de la única evaluación del holdout (17-oct-2026)

- **Preregistro #1:** configuración por omisión, huella `3bd704306ed6deea…`.
- **Datos:** huella `8fe2d3e0f8a641d6…`.
- **Holdout:** 92 meses (feb-2018 a sep-2025); costo por cambio de exposición del 0.166 %.

| Mercado | L elegido (entrenamiento) | TSM total | TSM caída máx. | Comprar y mantener total | Su caída máx. | Exposición media | Exceso/mes | p | p Holm (18) |
|---|---|---|---|---|---|---|---|---|---|
| SPY | 12 | +99.9 % | −23.9 % | +168.2 % | −23.8 % | 0.85 | −0.35 % | 0.950 | 1.000 |
| QQQ | 3 | +195.3 % | −18.0 % | +278.0 % | −33.2 % | 0.76 | −0.35 % | 0.864 | 1.000 |
| DIA | 12 | +31.0 % | −27.8 % | +105.9 % | −27.0 % | 0.83 | −0.52 % | 1.000 | 1.000 |
| EEM | 3 | +38.8 % | −14.7 % | +26.6 % | −36.1 % | 0.55 | +0.02 % | 0.491 | 1.000 |
| GLD | 6 | +97.5 % | −22.7 % | +178.0 % | −17.3 % | 0.75 | −0.39 % | 0.958 | 1.000 |
| NAFTRAC | 3 | +31.4 % | −16.3 % | +42.1 % | −32.1 % | 0.66 | −0.14 % | 0.703 | 1.000 |

**Lectura:** no se rechaza H0 en ningún mercado. TSM rindió menos que comprar y mantener en 5 de 6 mercados; en EEM la
diferencia es nula en la práctica. Redujo la caída máxima en QQQ, EEM y NAFTRAC, pero no en SPY, DIA ni GLD.
Con estos supuestos propios no hay ventaja demostrada.

**Sin verificar:** si la historia externa incluye dividendos (si no, ambos rendimientos quedan subestimados, y comprar y mantener algo más
por su mayor exposición).

Este holdout ya se usó. Una variante nueva requiere un preregistro nuevo y datos posteriores a sep-2025.
