# Propuesta del mejor portafolio con la plantilla de Markowitz — 25-nov-2026

Simulación educativa. No es asesoría de inversión y la terminal no envía órdenes.

## Qué se hizo

- **Universo:** los 12 instrumentos de la última captura confirmada del Reto (12-nov-2026, valor $784,440.07).
  Son FEMSA, KOF, TGT, MRK, AC, CVX, LLY, XOM, NVAX, ABBV, MRNA y PFE.
- **Método:** el mismo de la plantilla de Markowitz (`terminal/markowitz.py`, `terminal/excel_markowitz.py`):
  - máximo Sharpe (portafolio tangente);
  - covarianza muestral de 252 sesiones (2-dic-2025 a 24-nov-2026);
  - tasa libre CETES 28 de Banxico (6.19 %);
  - tope de 40 % por emisora (perfil agresivo del equipo).
- **Dónde se ve:**
  - En la terminal: «Mis portafolios», portafolio «Propuesta Markowitz · último registro del Reto (12-nov-2026)» (id 6).
    No se marcó como portafolio principal, así que el plan y Telegram no cambian.
  - En Excel: `entregables/Propuesta_Markowitz_Lynx_Market.xlsx`. Trae el modelo de Solver ya cargado; solo hay que pulsar «Resolver».
  - En el informe del concurso: sección 4.6, con la figura 10 y dos tablas.
- **Cómo se reproduce:** `markowitz.guardar` con la especificación anterior. La gráfica sale de `scripts/propuesta_markowitz_grafica.py`.

## Resultado

| Instrumento | Peso 12-nov | Peso propuesto |
|---|---|---|
| TGT | 15.5 % | 25.5 % |
| AC | 9.2 % | 24.4 % |
| CVX | 6.9 % | 13.8 % |
| KOF | 17.9 % | 12.7 % |
| XOM | 6.3 % | 10.6 % |
| ABBV | 2.7 % | 4.2 % |
| FEMSA | 17.9 % | 3.8 % |
| MRNA | 2.1 % | 3.4 % |
| NVAX | 5.1 % | 1.2 % |
| LLY | 6.6 % | 0.5 % |
| MRK, PFE | 9.8 % | 0 % |

| Métrica (1 año) | Propuesta | 1/N |
|---|---|---|
| Rendimiento esperado anual | 59.8 % | 68.0 % |
| σ anual | 15.3 % | 24.2 % |
| Sharpe | 3.51 | 2.56 |

**Fuera de muestra (2-jun a 24-nov-2026, rebalanceo mensual):**

| | Rendimiento | Sharpe |
|---|---|---|
| Propuesta | 58.8 % | 3.04 |
| 1/N | 54.2 % | 3.82 |

La propuesta rindió más que 1/N, pero con menor Sharpe. Un solo periodo no demuestra ventaja.

Moderna pesa 3.4 % y aporta 21 % del riesgo: es la posición a vigilar.

## Límites

- Los rendimientos esperados vienen de un año excepcional para estas emisoras. Son una extrapolación, no un pronóstico.
- La estimación depende de la ventana elegida. Con Ledoit-Wolf los pesos cambian: Moderna sube a 20.6 %.
