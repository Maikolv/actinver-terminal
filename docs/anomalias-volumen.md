# Hipótesis abierta: anomalías de volumen sin repintado — versión 1.0

Algoritmo **propio**: no clona ni equivale al indicador privado del reel DeSsMwAOXWz, cuyas reglas no son públicas. La
comparación con ese indicador queda pendiente mientras no se conozca su especificación. Código: `terminal/anomalias.py`.
Ruta: `GET /api/investigacion/anomalias?simbolo=&intervalo=&ventana=&umbral=&h=`, sobre barras guardadas.

## Reglas escritas antes de evaluar

1. z_t = (ln V_t − media de ln V en las n barras **anteriores**) / desviación de esas n barras. La barra t no entra.
   n = 20 por omisión.
2. Anomalía si z_t ≥ 2.0 y la barra t está **cerrada**. Una barra cuyo intervalo no terminó nunca se marca.
3. Sentido: el signo del log-retorno ln(C_t/C_{t−1}).
4. Evaluación: log-retorno de t a t+h tras cada anomalía, en el sentido de la barra, frente a la media de todas las
   barras.

## Controles probados (`tests/test_tsm_anomalias.py`)

- **Sin repintado:** calcular con un prefijo de la serie da las mismas marcas pasadas que con la serie completa.
- **Sin anticipación:** cambiar el volumen de t+1 no altera z_t.
- **Calentamiento:** las primeras n barras valen nulo.
- **Barra abierta:** no marca.

## Límites

- Usar el logaritmo del precio no lo vuelve estacionario, y el log-retorno también requiere comprobación.
- Dos desviaciones no implican una probabilidad normal ni continuación.
- El resultado es descriptivo: no incluye costos ni prueba de significancia. Para evaluarlo como estrategia hace falta
  un preregistro en el Laboratorio.
