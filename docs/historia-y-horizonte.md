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

## Resultados (6-oct-2026, datos al 2-oct-2026)

Salida completa en `data/referencias/historia_ventanas.json` (`scripts/comparar_historia.py`). Rendimientos netos de
costos, en MXN. Exceso frente a 1/N con IC 90 % (bootstrap de bloques de 21 sesiones).

| Lente | Config | Sesiones fuera de muestra | Pliegues (gana a 1/N) | Rend. anual | 1/N | Exceso [IC 90 %] | Caída máx. (1/N) |
|---|---|---|---|---|---|---|---|
| acciones · rendimiento | V0 vigente | 87 | 5 | +102.5 % | +10.4 % | +85 % [−127 %, +302 %] | — |
| | **V1 168/21** | **1,099** (may-2022→oct-2026) | 53 (27) | +20.5 % | +16.9 % | +8.9 % [−14.5 %, +32.3 %] | −45.7 % (−23.4 %) |
| | V2 252/21 | 1,015 | 49 | +16.9 % | +21.4 % | +1.9 % [−22.8 %, +24.4 %] | |
| | V3 504/21 | 763 | 37 (21) | +54.7 % | +26.6 % | +24.5 % [+2.4 %, +43.8 %] | −36.2 % (−23.4 %) |
| acciones · ajuste | V0 | 87 | 5 | +32.7 % | +10.4 % | +27 % [−100 %, +176 %] | |
| | **V1** | 1,099 | 53 (24) | +13.3 % | +16.9 % | −2.8 % [−16.8 %, +11.1 %] | −27.7 % (−23.4 %) |
| | V2 | 1,015 | 49 | +23.5 % | +21.4 % | +1.8 % [−10.9 %, +14.0 %] | |
| | V3 | 763 | 37 | +25.2 % | +26.6 % | −1.0 % [−13.4 %, +11.4 %] | |
| mixta · rendimiento | V0 | 87 | 5 | +119.8 % | +8.1 % | +95 % [−123 %, +324 %] | |
| | **V1** | 1,099 | 53 (30) | +25.1 % | +16.4 % | +14.1 % [−11.4 %, +39.9 %] | −42.6 % (−22.4 %) |
| | V2 | 1,015 | 49 | +20.1 % | +20.8 % | +6.8 % [−20.9 %, +29.3 %] | |
| | V3 | 763 | 37 (19) | +49.2 % | +26.0 % | +22.2 % [−0.1 %, +43.3 %] | −36.0 % (−22.4 %) |
| mixta · ajuste | V0 | 87 | 5 | +51.1 % | +8.1 % | +42.5 % [−87 %, +200 %] | |
| | **V1** | 1,099 | 53 (27) | +22.9 % | +16.4 % | +6.6 % [−7.7 %, +22.5 %] | −26.4 % (−22.4 %) |
| | V2 | 1,015 | 49 | +26.2 % | +20.8 % | +5.1 % [−8.8 %, +18.3 %] | |
| | V3 | 763 | 37 | +28.1 % | +26.0 % | +2.2 % [−10.9 %, +15.9 %] | |

Periodos (V1, máximo rendimiento acciones): el peor tramo de 63 sesiones terminó el 27-oct-2023 (−33 %) y el mejor
el 22-jun-2026 (+65 %).

### Aplicación de la regla preregistrada

1. **Se adopta V1** como validación de la terminal. Es la de más sesiones fuera de muestra: 1,099 contra 87, 12 veces
   más. En el periodo común (las 87 sesiones de V0) ninguna lente es peor que V0 con un IC entero bajo cero: la
   diferencia anual va de −1 % a +10 %, con IC que cruzan el cero.
2. **No cambian propuestas ni ranking.** Con V1 ninguna lente supera a 1/N con IC 90 % entero sobre cero. La de
   máximo rendimiento rinde más que 1/N en promedio (+8.9 % y +14.1 % anual), pero la diferencia no es concluyente y
   su caída máxima duplica la de 1/N.
3. **V3 se informa, no se adopta.** «Acciones · máximo rendimiento» con 504/21 sí supera a 1/N con IC entero sobre
   cero (+24.5 % [+2.4 %, +43.8 %]). La regla fijada antes no permite elegir la configuración que mejor luce. Entre
   16 comparaciones, una significativa al 90 % puede deberse al azar. Queda como hipótesis para un preregistro aparte.

**Validación vieja frente a la nueva:** con V0 los intervalos medían cientos de puntos (no decían nada); con V1 miden
unos 40 puntos. La terminal dice ahora «sin ventaja demostrada» con evidencia de 4.4 años, en lugar de 4 meses.

### Implementado

- `terminal/validacion_extendida.py`: V1 en cada propuesta (`validacion_extendida`). Es evidencia: no cambia pesos
  ni puntuación. `/propuestas` la muestra con su veredicto frente a 1/N.
- `scripts/comparar_historia.py`: el experimento preregistrado, reproducible.
- `scripts/calidad_series.py` → `docs/evidencia/calidad_series.json`. De 233 instrumentos del catálogo:
  - 0 mezclas de divisas y 0 huecos mayores de 5 sesiones;
  - ningún split sin ajustar;
  - 44 saltos de más de 30 %, todos en emisoras volátiles del SIC y ninguno con el patrón de un split (caída de
    50–90 % con su inverso). Los que se revisaron son eventos conocidos: compresión de BYND (oct-2025), GME (2024), FUBO–Disney
    (ene-2025), MRNA (ago-2026) y resultados de UPST. Los escenarios ya acotan esos saltos a ±10 %;
  - 6 claves con problemas (ALFA→SIGMAF, GOLD→B, PARA, MRO, CPE, ELEKTRA): ya marcadas y sin precio, así que no
    entran a las propuestas;
  - 23 sin precio: además de esas 6, ETF apalancados o inversos excluidos por regla, ETF de BMV sin fuente y TERRA.

### Límites

- La historia larga solo existe para el SIC (5 años). La BMV sigue con 1 año del plan gratuito de EODHD: en V1, las
  emisoras BMV entran solo en los últimos pliegues. Ampliarla requiere una fuente BMV con historia (ver
  `docs/bmv-licencia.md`).
- El panel dinámico trata un hueco dentro de la prueba como efectivo (0 %) y no supone que el instrumento seguirá
  cotizando.
