# Investigación predictiva sin fuga de información

Código en `terminal/investigacion/` y pruebas en `tests/test_investigacion.py`. Se ejecuta con `uv run terminal investigar` o con el botón «Calcular investigación y pronósticos» de la pestaña **Pasado · Presente · Futuro**.

## 1. Tiempo de los datos: `event_time` y `available_at`

Cada fila de precios, tipo de cambio, eventos corporativos, operaciones, noticias, calendario macro e insiders guarda dos horas: cuándo ocurrió (`event_time`) y cuándo pudo conocerla el modelo (`available_at`). Las reglas están en `terminal/migraciones.py`:

| Dato | event_time | available_at |
|---|---|---|
| Cierre diario | cierre oficial de la sesión (calendario NYSE o BMV) | cierre + retraso de publicación del proveedor (`[disponibilidad]`: Tiingo 3 h, EODHD 4 h, FRED 72 h…) |
| CSV del usuario | cierre de la sesión | el menor entre cierre + 24 h y la hora de importación, nunca antes del cierre |
| Cotización en vivo o por webhook | hora de la operación o de la alerta | hora de recepción |
| Operación registrada | fecha de la operación | hora en que se registró en la terminal |
| Noticia, evento macro, insider | publicación | hora en que la terminal la obtuvo |
| Evento corporativo | la del precio del mismo día | la del precio del mismo día |

Una hora ya fijada **no se sobrescribe**: si un dato se revisa después, no por eso se «conoció antes». Un pronóstico emitido a la hora T usa solo filas con `available_at <= T`. También entrena solo con ejemplos cuya etiqueta ya se conocía en T (`disponible_etiqueta <= T`).

Los precios se usan **sin ajuste por dividendos**, por dos razones: el Reto no paga dividendos (§13) y el ajuste por dividendos se recalcula con información futura. Los splits se aplican solo si su `available_at <= T`. Las variables usan ventanas que miran únicamente hacia atrás, con un máximo de L = 60 sesiones.

## 2. División cronológica, embargo y purga

Sobre las n fechas negociadas ordenadas (nunca se barajan):

```
n_ent = ⌊0.70 n⌋   n_val = ⌊0.15 n⌋   e = max(H, embargo_min)
entrenamiento = [0, n_ent)
validación    = [n_ent + e, n_ent + n_val)
prueba        = [n_ent + n_val + e, n)
```

- **Embargo:** se omiten e ≥ H fechas entre periodos. Son las únicas que se descartan y su número se informa (`fechas_embargadas = 2e`).
- **Purga:** se elimina el ejemplo de un periodo cuya ventana de etiqueta [t, t+H] termina en el primer día del periodo siguiente o después. Con e ≥ H casi nunca ocurre. Cubre los festivos distintos entre la BMV y NYSE, en los que t+H del instrumento cae más lejos. El número de ejemplos purgados se reporta.
- **L** no exige un embargo adicional: las variables solo miran hacia atrás y el entrenamiento siempre precede a la evaluación. Que una variable de validación use precios del entrenamiento es información pasada legítima.

| H | Embargo | Fechas descartadas |
|---|---|---|
| 1 (próxima sesión) | 1 sesión | 2 |
| 5 (cinco días hábiles) | 5 sesiones | 10 |

## 3. Walk-forward, filtro de correlación y comparación de métodos

Dentro del entrenamiento se usa una validación progresiva de 4 pliegues con ventana creciente. Entre el entrenamiento y la validación de cada pliegue hay un embargo de H fechas, y el entrenamiento de cada pliegue se purga contra su bloque.

Todo lo aprendible se ajusta **solo** con el entrenamiento de cada pliegue: imputación (mediana), escalado, filtro de correlación, PCA y α de Ridge. Validación y prueba solo reciben las transformaciones ya aprendidas.

Se comparan tres variantes con α ∈ {1, 10, 100, 1000}:

1. `filtro_correlacion`: matriz de correlación de las **variables predictoras** calculada en el entrenamiento. Se recorren en el orden de prioridad declarado antes de evaluar (`datos.VARIABLES`) y se descarta la variable cuyo |r| con una ya conservada sea ≥ 0.95. Luego se aplica Ridge.
2. `ridge`: solo regularización.
3. `pca`: componentes que explican el 95 % de la varianza del entrenamiento, luego Ridge.

La correlación entre **activos reales** no se reduce. Se informa en el PASADO porque representa riesgo verdadero.

## 4. Prueba final intacta y registro

1. El walk-forward elige α por variante y la validación elige la variante. Los residuos de validación calibran el intervalo 10–90 % y la probabilidad de subida (conformal por partición).
2. Con el modelo fijado, se reentrena con entrenamiento + validación purgados contra la prueba. La prueba se evalúa **una vez**.
3. Cada corrida queda en la tabla `experimentos` con la configuración, la semilla, los cortes, las huellas de la configuración y de los datos, la versión del código y los resultados. Si ya existe un experimento con los mismos datos y cortes pero **otra** configuración, el nuevo queda marcado `prueba_ya_vista`: no sirve para elegir modelo, porque la prueba ya se había visto.
4. Los pronósticos emitidos se guardan en `pronosticos`, **separados de las cotizaciones**. Registran la hora de emisión, los datos usados hasta, la versión y la semilla. El resultado observado se añade después, sin modificar la predicción.

## 5. Referencias y criterio de recomendación

El modelo se compara con tres referencias simples:

- **Sin cambio:** pronóstico 0.
- **Retorno histórico reciente:** media de 60 sesiones × H.
- **Regla predefinida:** momento de 20 sesiones si el precio está sobre su media de 50; si no, 0.

Métricas en la prueba:

- **Error:** MSE y MAE.
- **Dirección:** porcentaje de aciertos en el sentido del movimiento.
- **Calibración:** cobertura del intervalo 80 % y Brier de la probabilidad de subida.
- **Estabilidad:** meses en que el modelo tiene menos error que «sin cambio».
- **Estrategia:** rotación y resultado neto de costos de una cartera top-5 que rebalancea cada H sesiones, con comisión 0.10 % + IVA en cada cambio.

**Si el modelo no supera a las tres referencias** en error y en resultado neto, se declara así y no se emite recomendación de cambio (`recomendacion_permitida = 0`). Un embargo evita fugas de información; no hace que un pronóstico acierte.

Además, la alerta de **deterioro estadístico** compara el error de los pronósticos ya resueltos con el de «sin cambio» y revisa la cobertura del intervalo.
