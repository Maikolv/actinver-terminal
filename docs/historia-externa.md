# Historia externa del usuario (Excel «Benchmarks_time_series»)

Entregada por el usuario el 7-oct-2026 como «data histórica 100 % verificable de los últimos años del Reto Actinver».

## Qué contiene (comprobado)

- Matriz de precios diarios del 2-ene-1962 al **9-oct-2025**: 226 instrumentos del universo del Reto, con claves al
  estilo Yahoo Finance (`GMEXICOB.MX`, `BRK-B`, `LIVEPOLC-1.MX`). Hay acciones BMV, SIC, ETF y 17 fondos Actinver.
- Tres series índice, «Conservador», «Moderado» y «Agresivo», con base 100 el 5-ene-2004. El archivo no dice cómo se
  construyen.
- **No son resultados de Retos anteriores** (posiciones, rankings o rendimientos de participantes): son precios.
- sha256 del archivo y conteos: `docs/evidencia/historia_externa.json`. La matriz se guarda en
  `data/referencias/historia_externa/` (fuera de Git, como el resto de `data/`).

## Reglas de uso

1. No entra a la tabla `precios`. Termina el 9-oct-2025: nunca se muestra como precio vigente.
2. Cada columna se verifica contra la serie que ya tiene la terminal (Tiingo/Alpaca para SIC, EODHD para BMV) en las
   fechas comunes. Se acepta si coinciden los rendimientos diarios: correlación ≥ 0.98, diferencia mediana ≤ 0.2 pp y
   al menos 10 sesiones en común.
3. Las aceptadas solo extienden **rendimientos** hacia atrás, antes del primer dato local, igual que el proxy ADR
   (`terminal/historia_externa.py`, `extender`).
4. Sin solape no hay verificación: esas columnas se informan y no se usan.

## Verificación (7-oct-2026)

| Resultado | Columnas | Detalle |
|---|---|---|
| Verificadas | 148 | 137 SIC/ETF: rendimientos idénticos a Tiingo (correlación 1.000, diferencia mediana 0) en ~1,000 sesiones. 11 BMV idénticas a EODHD, pero solo en 11 sesiones (solape corto) |
| Rechazadas | 5 | ALSEA, BIMBO, CHDRAUI, GCARSO y FIBRAMQ: difieren de EODHD (diferencia mediana de 0.1 a 0.8 pp diaria) |
| Sin verificar | 56 | 20 fondos (la terminal solo tiene sus NAV desde sep-2026); 26 BMV con < 10 sesiones en común o sin serie local; 10 ETF apalancados o inversos que el Reto excluye |
| No usadas | 20 | Fuera del catálogo del simulador, los 3 perfiles y la columna «AC» |

Hallazgos:
- **«AC» (sin .MX) no es Arca Continental**: es Associated Capital Group (NYSE, ≈ USD 36). Se descarta.
- Los fondos repiten el mismo valor en las últimas 4 sesiones (dato que dejó de actualizarse antes del corte).
- En SIC el archivo es el **precio ajustado por dividendos y splits** (coincide con el ajustado de Tiingo, no con el
  cierre). El simulador del Reto no paga dividendos: antes de 2021 la historia extendida incluye los dividendos.
  Eso sesga hacia arriba unos 1–3 puntos al año a las emisoras que pagan, en la estrategia y en 1/N por igual.

## Perfiles índice (referencia histórica, no se usan para decidir)

| Perfil | Rend. anual 2004–2025 | Volatilidad | Caída máx. | 2022 | 2024 |
|---|---|---|---|---|---|
| Conservador | +8.3 % | 4.7 % | −8.7 % | −0.7 % | +16.1 % |
| Moderado | +9.8 % | 10.0 % | −22.7 % | −10.1 % | +27.3 % |
| Agresivo | +10.9 % | 15.4 % | −35.8 % | −19.0 % | +39.3 % |

## Validación con historia larga — preregistro (antes de correr)

- **Qué:** V1 (walk-forward 168/21, panel dinámico, banda y costos del Reto, referencia 1/N del mismo universo) con
  la historia local extendida por las columnas verificadas, desde el 2-ene-2004. Las 4 lentes de siempre.
- **Regla:** las propuestas y el ranking solo cambian si una lente supera a 1/N con el IC 90 % del exceso entero por
  encima de cero. Si no, se informa «sin ventaja demostrada» con la historia larga.
- **Sesgos conocidos, que se informan con el resultado:**
  - Supervivencia: el universo es el de 2026; las emisoras que quebraron o salieron de bolsa no están. Eso infla el
    rendimiento de la estrategia y de 1/N, y más el de una lente que concentra en ganadoras.
  - Dividendos antes de 2021 (ver arriba).
  - BMV con solape corto.

## Resultados (7-oct-2026)

Salida completa en `data/referencias/historia_externa/validacion.json` (`scripts/historia_externa.py validar`).
Fuera de muestra del 25-ago-2004 al 6-oct-2026: 5,690 sesiones y 271 pliegues (antes, 1,099). Netos de costos, en MXN.

| Lente | Rend. anual | 1/N | Exceso [IC 90 %] | Caída máx. (1/N) | Pliegues que ganan a 1/N |
|---|---|---|---|---|---|
| acciones · máximo rendimiento | +30.5 % | +18.7 % | **+13.4 % [+3.6 %, +23.8 %]** | **−70 %** (−38 %) | 144 de 271 |
| acciones · ajuste | +24.3 % | +18.7 % | +5.0 % [−0.3 %, +10.7 %] | −37 % (−38 %) | 142 |
| mixta · máximo rendimiento | +22.5 % | +17.6 % | +6.5 % [−2.3 %, +15.7 %] | −61 % (−37 %) | 139 |
| mixta · ajuste | +15.2 % | +17.6 % | −2.3 % [−7.2 %, +2.9 %] | −30 % (−37 %) | 120 |

Por periodo, «acciones · máximo rendimiento» frente a 1/N: 2004–08 +12.1 % vs +9.9 %; 2009–13 +14.8 % vs +23.9 %;
2014–18 +30.5 % vs +20.1 %; 2019–23 +51.5 % vs +17.1 %; 2024–26 +60.4 % vs +24.8 %.

### Aplicación de la regla y lectura honesta

1. Por la regla preregistrada, «acciones · máximo rendimiento» **supera a 1/N** con el IC 90 % entero sobre cero. Es la
   lente que el usuario ya eligió (D-59), así que **no cambia nada en las propuestas**: los pesos y la puntuación
   siguen iguales.
2. **No se declara «ventaja demostrada».** El sesgo de supervivencia es grande y favorece justo a esta lente:
   - 1/N del universo actual rinde +18.7 % anual en MXN, frente a +13.4 % del S&P 500 (SPY, con dividendos) y +9.6 %
     del NAFTRAC en el mismo periodo. Unos 5 puntos al año salen solo de elegir hoy las emisoras que sobrevivieron.
   - Casi todo el exceso está en 2019–2026, con emisoras que están en el catálogo porque subieron (NVDA, AMD, MU). En
     2009–2013 la lente perdió contra 1/N.
   - El IC no corrige que entre 4 lentes una salga significativa por azar.
3. Lo que sí queda medido con 22 años es el riesgo: la caída máxima de máximo rendimiento fue **−70 %**, casi el doble
   que 1/N. Es coherente con la caída p5 de −23/−24 % al cierre del Reto (protocolo de robustez) que el usuario aceptó.
4. Las lentes de ajuste no muestran ventaja. «Mixta · ajuste» queda por debajo de 1/N, pero con la menor caída (−30 %).

La evidencia queda en este documento y en el informe JSON, con su sesgo. No se usa para afirmar que el modelo maximiza
ganancias.
