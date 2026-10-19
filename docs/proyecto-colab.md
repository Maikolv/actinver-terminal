# Proyecto explicable en Google Colab (secuencia de los reels de quantbryan)

Estado: **tema 3 elegido por el usuario el 18-oct-2026 e implementado** en
[`notebooks/multiples_estrategias.ipynb`](../notebooks/multiples_estrategias.ipynb).
No se contrataron datos ni se publicó contenido académico. El ejemplo SINTÉTICO demuestra
ejecución y bloquea conclusiones financieras; no hay ventaja demostrada.

## Secuencia

1. **Ideas y elección.** El prompt pide 20 proyectos con 13 campos: nombre, dificultad, función, relevancia
   financiera, habilidades, fuentes/API, bibliotecas, plan, conceptos, visualizaciones, uso profesional comparable,
   valor curricular y tiempo. El valor curricular es una opinión, no evidencia de empleabilidad. Cada proyecto lleva una
   pregunta comprobable y una referencia simple que debe superar.
2. **Notebook en Colab.** Celdas separadas para instalación, configuración, datos, validación, análisis, evaluación y
   exportación. Versiones y semilla congeladas; una prueba final reservada. El modo sintético solo demuestra que el
   código funciona y bloquea conclusiones. Usted abre Colab, carga solo datos que tenga derecho a usar y ejecuta en
   orden. El «un minuto» del reel es promocional: ejecutar no es validar.
3. **Explicación y defensa.** Revisión celda por celda, supuestos irreales, tres mejoras, preguntas de entrevista y un
   cálculo a mano. Se distingue lo que generó la IA de lo que usted verificó.
4. **Paper (ampliación propia, no del creador).** Pregunta estrecha, bibliografía primaria verificada, H0/H1
   preregistradas, separación cronológica con purga/embargo, multiplicidad, resultados nulos incluidos y reproducción
   desde un entorno limpio. Publicar es decisión suya.

## Recomendación con los datos actuales de la terminal

Los 20 temas están en el prompt maestro. Para empezar, de alcance manejable:

| # | Pregunta | Por qué encaja | Referencia a superar |
|---|---|---|---|
| 1 | ¿Reduce el drawdown una regla defensiva frente a mantener la cartera? | Usa el plan intradía y el backtesting ya existentes; costos del Reto incluidos | Comprar y mantener |
| 3 | ¿Siguen siendo significativos los excesos tras probar muchas variantes? | Usa el Laboratorio (preregistro, holdout, Holm) | Exceso 0 frente al benchmark |
| 19 | ¿Cómo cambia el resultado al incorporar el tipo de cambio en el SIC? | Cierres de origen en USD más FIX de Banxico, ambos ya disponibles | Mismo cálculo en USD |

Los temas 15 a 18 necesitan cinta, OI o ticks con lado del agresor que hoy no hay gratis
(`docs/proveedores-gratuitos.md`). Con series diarias no se puede afirmar que se evaluó el Order Flow.

## Dependencias

Se eligen por utilidad y licencia, en el notebook y no en el entorno de la terminal: `pandas`, `numpy`, `matplotlib`,
`scipy` y, solo si el tema lo exige, `statsmodels`. No se instalan paquetes por aparecer en una infografía.

## Uso del tema 3

1. Abra el notebook en Colab y ejecute las celdas en orden. La instalación es explícita y
   opcional: NumPy 2.5.3 y pandas 3.0.6. No requiere SciPy, servidor de la terminal ni claves.
2. Ejecute primero el modo **SINTÉTICO**, sin cambiar nada. Exporta un JSON y un CSV locales
   con ese rótulo; no descarga datos ni presenta los resultados como evidencia financiera.
3. Antes de pasar a REAL, declare todas las variantes probadas, familia total, benchmark,
   fuente, costos, generación causal, semilla, bloque, purga, embargo y corte del holdout.
   Conserve configuración y huella con fecha verificable **antes de observar los datos**.
4. Cargue manualmente un CSV autorizado con `fecha,benchmark,variante_1,variante_2,variante_3`
   (o los nombres configurados): rendimientos simples netos, misma moneda y periodo,
   fechas ISO únicas crecientes, sin faltantes. Confirme netos y preregistro externo.
   Se aceptan 100–5000 observaciones, hasta 20 variantes y al menos ocho bloques por tramo.
5. La selección usa exclusivamente la exploración. Se descartan purga y embargo; el holdout
   evalúa toda la familia mediante volteo de signos por bloques y Holm, con referencia de
   exceso medio cero. Las variantes exploradas no publicadas cuentan como p=1.
6. Descargue desde Archivos los resultados de `resultados_tema3/`. El JSON conserva
   configuración, versiones, huellas, cortes, selección y todas las filas, incluidos nulos;
   el CSV contiene todas las variantes. No se sobrescriben archivos distintos.

El holdout queda congelado en la sesión: reevaluar devuelve lo guardado, y cambiar datos,
configuración o selección bloquea la evaluación. **No equivale a un registro externo ni
impide reiniciar Colab para eludir el control**. El usuario debe conservar el preregistro y
no reutilizar el tramo reservado. El notebook no verifica cómo se generó el CSV: la purga
de la frontera no corrige estrategias entrenadas con datos futuros. Ajuste su longitud al
solapamiento máximo antes de observar resultados. Los supuestos de simetría de signos y
dependencia dentro del bloque pueden fallar; no rechazar H0 no demuestra equivalencia.

Verificación reproducible: `tests/test_notebook_tema3.py` ejecuta todas las celdas sin pip
en directorio temporal, comprueba exportación sintética y congelación, un caso conocido de
Holm, rechazo de fechas/faltantes inválidos, cambios de configuración/selección,
reextracción del holdout y protección de exportaciones anteriores. El CSV usa saltos
de línea explícitos para permitir reevaluación idéntica en Windows y Colab. No se conectó Colab ni se evaluó un CSV real.
