# Proyecto explicable en Google Colab (secuencia de los reels de quantbryan)

Estado: **paso 1, esperando que usted elija el tema.** No se programó ningún notebook todavía. Tampoco se contrataron
datos ni se publicó contenido académico.

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

Siguiente paso: dígame el número del tema y armo el notebook.
