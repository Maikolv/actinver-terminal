# Historia para validar frente a horizonte de decisión

## Dos cosas distintas

| Concepto | Qué es | Valor vigente (6-oct-2026) |
|---|---|---|
| **Horizonte de decisión** | Hasta cuándo importa el resultado: el cierre del Reto, 13-nov-2026 15:00. | 29 sesiones BMV (≈ 0.115 años). Se calcula solo (`reto.horizonte_anios`) y **no cambia** con esta revisión. |
| **Historia para entrenar y validar** | Cuántos días pasados se usan para estimar y para probar fuera de muestra. | Historia común de **255 sesiones** (7-oct-2025 a 1-oct-2026); walk-forward 168/21. La validación fuera de muestra es de **84 sesiones**. |

### Por qué la historia común es tan corta

`optimizador.rendimientos` empieza donde empieza el instrumento con menos historia. El plan gratuito de EODHD solo da
el último año de cierres BMV, así que 25 emisoras BMV elegibles (LIVEPOL, GFNORTE, GRUMA, KOF, KIMBER, LAB, GENTERA,
GFINBUR…) tienen unas 251–254 sesiones. Los instrumentos del SIC (Tiingo y Alpaca) tienen 5 años. `config/local.toml`
bajó el mínimo a 250 sesiones para no excluir a esas emisoras. A cambio, la evidencia fuera de muestra cubre solo
jun–sep-2026.

## Preregistro (escrito el 6-oct-2026, ANTES de calcular cualquier resultado de rendimiento)

Lo único visto antes de escribir esto es el número de sesiones por instrumento. No se vio ningún rendimiento.

### Configuraciones de validación que se comparan (fijas)

| Clave | Universo por pliegue | Entrenamiento / prueba (sesiones) | Notas |
|---|---|---|---|
| **V0 vigente** | Los instrumentos elegibles con historia común completa (hoy 255 sesiones) | 168 / 21 | Lo que hace la terminal hoy |
| **V1 panel dinámico 168/21** | En cada pliegue, los elegibles con datos completos en ese entrenamiento y esa prueba | 168 / 21 | Más historia; las emisoras de 1 año entran solo en los pliegues donde tienen datos |
| **V2 panel dinámico 252/21** | Igual que V1 | 252 / 21 | Entrenamiento de un año |
| **V3 panel dinámico 504/21** | Igual que V1 | 504 / 21 | Entrenamiento de dos años, como el valor por omisión del proyecto |

Condiciones comunes:
- Mismos modelos y lentes de la terminal (`acciones` y `mixta` × `rendimiento`, `ajuste`).
- La misma banda de rebalanceo de 2 puntos.
- Costos del Reto: 0.116 % con IVA por operación, sobre el giro de cada rebalanceo.
- Sin ventas en corto ni apalancamiento.
- Mismas reglas de catálogo del simulador.
- Referencia: pesos iguales (1/N) sobre el MISMO universo de cada pliegue, con los mismos costos.

### Métricas que se reportan

- Sesiones fuera de muestra y número de pliegues.
- Rendimiento neto anualizado, volatilidad, caída máxima y Sharpe.
- Exceso frente a 1/N con IC 90 % por bootstrap de bloques de 21 sesiones.
- Fracción de pliegues que superan a 1/N.
- Mejores y peores periodos de 63 sesiones.
- Comparación en el periodo común a todas (el más reciente).

### Regla de selección (fija)

1. La configuración de validación que se adopta es la que tenga **más sesiones fuera de muestra**, siempre que en el
   periodo común no sea peor que V0 en rendimiento neto con un IC 90 % entero por debajo de cero. Su propósito es dar
   evidencia más larga y menos incierta, no lucir mejor.
2. Las **propuestas y el ranking solo cambian** si, con la configuración adoptada, la lente correspondiente supera a
   1/N fuera de muestra con IC 90 % del exceso entero por encima de cero. Si no, se mantienen como están y se informa
   «sin ventaja demostrada».
3. No se agregan configuraciones después de ver resultados. Si hiciera falta otra, se preregistra aparte y se marca
   como exploratoria.

## Resultados

(Se completan con `uv run python scripts/comparar_historia.py`; ver la sección de resultados más abajo.)
