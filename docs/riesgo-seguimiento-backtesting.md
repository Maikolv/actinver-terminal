# Riesgo, seguimiento y backtesting (etapa 3)

12-oct-2026. Tres pestañas en **Más**: **Riesgo**, **Seguimiento** y **Backtesting**. Atajos: `/RIE`, `/SEG` y `/BT`.
Todo es análisis y simulación: nada envía órdenes.

## Riesgo (`terminal/riesgo.py`, `GET /api/riesgo`)

Con los pesos de la cartera actual (captura del portal), mantenidos constantes hacia atrás:

| Métrica | Definición |
|---|---|
| Volatilidad anual | Desviación diaria × √252 |
| Caída máxima y actual | Desde el máximo previo de la curva con los pesos actuales |
| VaR histórico 95/99 % (1 día y horizonte) | Cuantil empírico de los rendimientos; el horizonte se escala por √h (sesiones al fin del Reto por omisión) |
| CVaR | Pérdida promedio en los días peores que el VaR |
| VaR paramétrico | Supone normalidad; se muestra para contrastar (subestima colas gruesas) |
| Exposición | Por emisora, mercado del simulador, clase y moneda del subyacente (el SIC sigue al dólar), más efectivo |
| Contribución al riesgo | Parte de la varianza que aporta cada emisora: wᵢ(Σw)ᵢ / wᵀΣw, que suma 100 % |
| Concentración | HHI y emisoras efectivas (1/HHI) |

Escenarios:
- **Hipotéticos:** la mayor posición −10 % y −20 %; el peso se aprecia 5 % (afecta al SIC); todo −10 %.
- **Históricos:** el peor tramo de 5 y de 20 sesiones con los pesos actuales.
- **Estrés:** volatilidad ×2 (`escenarios.estres_volatilidad`).

Los supuestos se listan en la propia vista. Con la cartera del 12-oct:
- volatilidad 47.6 % anual;
- VaR 95 % de 4.3 % en un día (≈ 41.7 mil MXN);
- MU pesa 47 % y aporta el 74 % del riesgo.

## Seguimiento (`terminal/seguimiento.py`)

- **Lista de seguimiento:** usa la **misma tabla** que «Movimientos públicos» (un solo lugar para lo que vigilas).
  - Muestra el último cierre en MXN, la variación a 1, 5 y 20 sesiones, el RSI 14 (Wilder) y las noticias de 7 días.
  - Rutas `GET/POST /api/lista-seguimiento`.
- **Ficha:** noticias del instrumento y estados financieros del centro de investigación (Alpha Vantage o importados).
  Ruta `GET /api/ficha/{id}`.
- **Comparación** (de 2 a 8 instrumentos más una referencia, NAFTRAC o SPY):
  - curva de 100 invertidos;
  - rendimiento, volatilidad, caída máxima, beta y Sharpe sin tasa;
  - matriz de correlación.

  Usa las fechas comunes, con cierres en MXN ajustados por splits. Ruta `GET /api/comparar`.

## Backtesting (`terminal/backtest.py`, `/api/backtests`)

| Estrategia (versión) | Parámetros |
|---|---|
| Comprar y mantener (1.0) | Pesos iguales al inicio |
| Pesos iguales (1.0) | Rebalanceo cada N sesiones |
| Cruce de medias (1.0) | SMA rápida y lenta; largo si rápida > lenta; si no, efectivo |
| Momento (1.0) | Los k mejores por rendimiento de N sesiones; rebalanceo periódico |

Reglas:
- **Sin fuga de información:** la señal usa cierres hasta el día t y se opera al cierre de t+1. Lo comprueba
  `tests/test_etapa3.py::test_backtest_ejecuta_al_dia_siguiente_sin_fuga`.
- **Costos:** comisión del Reto (comisión + IVA de `config/reto.yaml`) + deslizamiento en puntos base sobre cada
  importe. Banda de rebalanceo de 1 punto.
- **Calendario:** las sesiones con precio. Un instrumento sin precio ese día no se opera; su último precio se arrastra
  hasta 3 sesiones.
- **Referencia:** comprar y mantener el mismo universo con los mismos costos.
- **Registro (tabla `backtests`):** estrategia y versión, parámetros, sha256 de la configuración y de la matriz de
  precios usada, versión del código, resumen y resultado. Repetir una corrida idéntica la marca «idéntica a la
  corrida #n».
- **Exportación:** CSV con encabezado de procedencia, la curva y las operaciones (`/api/backtests/{id}/exportar`).

Limitaciones que muestra la propia vista:
- sin dividendos ni impuestos;
- sin las reglas de 5 emisoras y 50 %;
- sesgo de supervivencia (universo elegido hoy);
- los cierres guardados pueden incluir correcciones posteriores del proveedor.

**Un resultado en un solo periodo no demuestra ventaja.** Para evidencia fuera de muestra están la validación V1 y el
protocolo de robustez (`docs/historia-y-horizonte.md`, `docs/robustez.md`).

## Pruebas

`tests/test_etapa3.py` (7 pruebas):
- VaR y CVaR;
- ejecución al día siguiente;
- costos y determinismo;
- validación de parámetros;
- registro y reproducibilidad con huellas;
- exportación CSV;
- lista y comparación;
- API protegida.
