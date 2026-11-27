# Portafolio idóneo tras el último registro del Reto — plantilla de Markowitz

Fechas: 25 y 27-nov-2026. Es una simulación educativa: no es asesoría de inversión y la terminal no envía órdenes.

## Cómo se obtuvo

- **Punto de partida:** los 12 instrumentos de la última captura confirmada del Reto (12-nov-2026, valor $784,440.07).
- **Herramientas de la terminal:** el generador de «Mis portafolios» (`markowitz.generar`) y la plantilla de Markowitz (`terminal/excel_markowitz.py`).
  - El generador completa con el Ranking hasta 16 instrumentos con correlación ≤ 0.85.
  - Usa el mismo Solver del Excel: máximo Sharpe, covarianza muestral de 252 sesiones y CETES 28 de Banxico (6.19 %).
- **Configuraciones comparadas fuera de muestra frente a 1/N:** 36 en total, con estas variantes:
  - 12, 16 o 20 instrumentos;
  - topes de 10 a 40 % por emisora;
  - covarianza muestral o Ledoit-Wolf;
  - con o sin ETF.
- **Elegida:** la que mejor equilibra rendimiento, riesgo y diversificación con el mismo cálculo del Excel. Es perfil agresivo, 16 instrumentos, tope de 10 % por emisora y covarianza muestral. Como se eligió entre varias, su resultado fuera de muestra es algo optimista.

## Dónde se ve

- **Terminal:** «Mis portafolios» → «Portafolio idóneo · Markowitz tras el último registro (12-nov-2026)» (id 7).
  - Se puede marcar como principal; así, el plan de acción y Telegram avisan contra él.
  - La versión con los mismos 12 instrumentos y tope de 40 % queda como id 6.
- **Excel:** `entregables/Propuesta_Markowitz_Lynx_Market.xlsx`, hojas P1 (idóneo) y P2 (12 instrumentos), con Solver cargado.
- **Informe:** sección 4.6, con la figura 10 (`scripts/propuesta_markowitz_grafica.py`).

## Resultado

**Pesos del portafolio idóneo:**

- ABBV, FEMSA, XOM, KOF, CVX, TGT, AC y PG: 10 % cada una.
- DIS: 7.2 %.
- COST: 4.8 %.
- MRNA: 3.6 %.
- LLY: 3.2 %.
- NVAX: 1.1 %.
- MRK, PFE y WMT: 0 %.

| | Idóneo (16, tope 10 %) | Mismos 12, tope 40 % | 1/N |
|---|---|---|---|
| E(r) anual | 51.7 % | 59.8 % | 57.4 % |
| σ anual | 14.6 % | 15.3 % | 20.0 % |
| Sharpe | 3.13 | 3.51 | 2.57 |
| Sharpe fuera de muestra | 4.02 | 2.99–3.04 | 4.44 |
| Rendimiento fuera de muestra | 56.8 % | 56.9–58.8 % | 50.3 % |

La prueba fuera de muestra va del 2-jun al 24-nov-2026, con rebalanceo cada 21 sesiones.

En la columna «Mismos 12», el primer valor de cada rango es de la rejilla del 27-nov y el segundo es la cifra que publica la sección 4.6 del informe (corrida del 25-nov).

El tope de 10 % mejoró el Sharpe fuera de muestra de 3.0 a 4.0. Aun así, 1/N tuvo mejor Sharpe (4.44). La ventaja no está demostrada.

Moderna pesa 3.6 % y aporta 27 % del riesgo: es la posición que hay que vigilar.
