# Nueve posts de Instagram — análisis y aplicación a Actinver-terminal

Revisión:17-oct-2026. Se leyeron las nueve páginas con la sesión disponible, se recuperó su audio público para transcripción local y se inspeccionaron fotogramas de los reels con listas/reglas. La transcripción automática puede fallar en nombres: se contrastaron con texto visible y fuentes oficiales. No se enviaron comentarios ni mensajes privados.

## Fuentes y aplicación

| Post / autor | Información observable | Aplicación y límites |
|---|---|---|
| [Dej_B7_MXrX — chrispathway](https://www.instagram.com/p/Dej_B7_MXrX/) | Mini terminal con Replit: yfinance para mercado, SEC EDGAR para estados, FRED para macro, Yahoo para titulares y FinBERT para sentimiento. Es colaboración pagada; ofrece el enlace por comentario «TERMINAL». | Reutilizar los módulos actuales y la matriz de proveedores de la terminal. Una interfaz similar no da cobertura ni derechos de Bloomberg. No se obtuvo el proyecto privado; se identificaron los repositorios públicos de yfinance y FinBERT por sus fuentes oficiales. |
| [Dd2ABKWSCzp — choicooks](https://www.instagram.com/p/Dd2ABKWSCzp/) | Arbitraje de resultados complementarios entre Kalshi/Polymarket; usa cuotas positivas+238 y+176 y afirma beneficio sin riesgo. | Solo ejemplo educativo de equivalencia de contratos, costes y riesgo de ejecución; no apostar ni añadir un canal a esos mercados. Costes, resolución distinta y una pata sin ejecutar pueden eliminar el supuesto beneficio. |
| [DeSsMwAOXWz — jesutraderchile](https://www.instagram.com/p/DeSsMwAOXWz/) | Promociona un indicador de anomalías gratuito y acceso mediante comentario. | No copiar un algoritmo propietario ni afirmar equivalencia sin especificación. Diferenciar observación anómala de señal rentable; verificar cierre de barra, estabilidad y repintado antes de evaluar. |
| [DejEnwmBclA — italian_founder](https://www.instagram.com/p/DejEnwmBclA/) | Time-Series Momentum mensual, referencia a Kakushadze/Serur; lookback elegido con datos antiguos y una evaluación posterior; seis mercados con resultados diferentes. | Incorporar protocolo de investigación separado. El momentum transversal diario existente en la terminal no replica esta estrategia. No ejecutar su regla mensual sin stop en Lucid intradía. |
| [DdCEkOBBjc4 — quantbryan](https://www.instagram.com/p/DdCEkOBBjc4/) | Presenta cursos/certificados LSE como gratuitos y flexibles; muestra el catálogo de Online Certificate Courses. | El catálogo oficial describe semanas/módulos y fechas de solicitud; no confirma la gratuidad universal ni ausencia de fechas. Mantener coste/acceso/certificado como campos independientes. |
| [DdXnw2lRsuK — chase_enloe](https://www.instagram.com/p/DdXnw2lRsuK/) | Lista Bloomberg ESG, simulaciones BofA y Wells Fargo, dos cursos CFI, Duke, Columbia, freeCodeCamp, Alteryx y Saylor. | Ruta de formación con proyectos aplicables: riesgo, estados financieros, datos y valoración. Ver condiciones reales abajo; «diez certificados gratis» no queda demostrado en bloque. |
| [DcbSXQPqHH8 — matebreton](https://www.instagram.com/p/DcbSXQPqHH8/) | Nombra IBM, GitHub Foundations, AWS, Microsoft Learn, BMC, Cisco, Salesforce Trailhead/Superbadge, Oracle y Snowflake. | Son categorías heterogéneas: badges, formación y exámenes no son equivalentes. El reel dice diez, pero la lista hablada no identifica diez programas inequívocos separados; no inventarlos para completar el número. |
| [DdAWgncB1Sj — chase_enloe](https://www.instagram.com/p/DdAWgncB1Sj/) | BMC, Forage, Excel/contabilidad CFI, Yale, Wharton, Kaggle, HackerRank y Microsoft Learn. | Diferenciar simulación laboral, curso, badge y certificación con examen. «Ivy League prep» se superpone al contenido y no es por sí mismo un emisor acreditado. |
| [DebBqQzhcHC — nishantaqc](https://www.instagram.com/p/DebBqQzhcHC/) | Presenta finanzas corporativas de Penn, formación de EDUCBA y Columbia para currículum. | EDUCBA no es una universidad Ivy League. Vincular capacidades a trabajos demostrables; certificados no garantizan empleo ni resultado de trading. |

## Momentum: pasos públicos que sí se pueden seguir

1. Una vez al mes, cerrar la posición opuesta existente.
2. Comparar el cierre del mes anterior con el de3,6 o12meses antes. Elegir ventana por mercado usando solo datos antiguos.
3. Si es mayor, comprar y mantener el mes. Si es menor, quedar fuera; para forex el reel indica vender. No se especifica el tratamiento de igualdad.
4. No usar stop ni target en la versión del reel: decide el siguiente chequeo mensual.
5. Ajustar tamaño para que un rango diario medio represente el mismo importe de riesgo. El período del rango y ese importe no se publican en lo observado.

El caption declara ticks, comisión y swap, oro/forex deabril2022–septiembre2026 e índices deenero/mayo2024–septiembre2026. Son afirmaciones del autor, no resultados reproducidos aquí. Faltan dataset/licencia, instrumento/contrato, entrenamiento exacto, fills, tamaño, costes desglosados y todos los parámetros. No confundir US100/US500 con NQ/ES. Su oferta de especificación completa mediante «MOMENTUM» no se recuperó por DM.

La [versión académica en español](https://arxiv.org/abs/1912.04492) es descriptiva; no prueba rentabilidad actual. El [registro editorial de Springer](https://link.springer.com/book/10.1007/978-3-030-02792-6) aparece titulado RETRACTED BOOK; no se verificó aquí el motivo. Conservar esa advertencia y contrastar cualquier fórmula con otras fuentes primarias.

## Arbitraje: corrección aritmética y límites

Con cuotas decimales3.38 y2.76, q=1/3.38+1/2.76≈0.65817. Si realmente son resultados complementarios, con igual pago bruto y ejecución simultánea, el margen por unidad de pago es1−q≈0.34183; el retorno sobre capital es1/q−1≈51.93%, antes de costes. No son la misma métrica. No se verifica que las oportunidades mostradas fueran ejecutables o liquidadas con reglas equivalentes. La promesa de «sin riesgo» no se incorpora a la terminal.

## Investigación/paper: qué pertenece a los videos y qué es diseño propio

Estos nueve posts no ofrecen un procedimiento completo de prompting ni de escritura de paper. El reel de momentum cita un trabajo y describe un backtest. Los pasos siguientes son una adaptación propia para hacerlo reproducible, no una transcripción literal:

1. Elegir tema. Opciones: A) TSM mensual largo/efectivo sobre índices; B) anomalías de volumen sin repintado; C) valor incremental de Order Flow en MES/MNQ. Conservar el tema3 ya elegido en docs/proyecto-colab.md: no reemplazarlo automáticamente.
2. Prerregistrar hipótesis, universo, referencia, costes, muestras y criterio de fracaso antes de mirar el holdout.
3. Inventariar datos y derechos. La terminal tiene módulos diarios; sin ticks/Level2 no certificar un backtest de microestructura.
4. Seleccionar parámetros solo con entrenamiento; registrar todas las variantes. Congelar configuración, código y huellas de datos.
5. Ejecutar una vez el holdout. Si se modifica la estrategia después de verlo, deja de ser intacto; reservar nueva muestra futura.
6. Comparar contra referencias, medir drawdown, incertidumbre y sensibilidad a costes. Usar las pruebas de permutación bajo sus supuestos; no «fabricar alfa» con un p-valor.
7. Redactar pregunta, datos, método, resultados, limitaciones y fuentes; publicar también resultados negativos. No inventar citas, datasets o experimentos.

La terminal muestra las nueve fichas de fuente en Aprender y recursos, con ejercicios y límites. Para cálculo existente se reutilizan Backtesting, Laboratorio y el notebook elegido; no se reemplaza la estrategia activa ni se generan órdenes.

Corrección LSE: [AI Law, Policy and Governance](https://www.lse.ac.uk/study-at-lse/executive-education/programmes/ai-law-policy-and-governance), visible en el reel, publica2420GBP de matrícula y seis semanas. Esto contradice su presentación general como gratuito.

## Licencias de los dos recursos de código

- [yfinance](https://github.com/ranaroussi/yfinance): código Apache2.0; biblioteca no afiliada a Yahoo. Los permisos de datos no quedan concedidos por la licencia del código; comprobar uso personal y condiciones de Yahoo.
- [FinBERT](https://github.com/ProsusAI/finBERT): código Apache2.0, pero [pesos ProsusAI/finbert](https://huggingface.co/ProsusAI/finbert) CC-BY-NC-SA4.0. Se prueba como demostración educativa no comercial con frases sintéticas locales. No se autoriza automáticamente integrarlo al bot de fondeo; resolver derechos o elegir una alternativa apropiada antes de uso comercial. No se envían textos privados a inferencia externa.

Corrección estadística del reel de anomalías: aplicar logaritmo al nivel del precio no garantiza estacionariedad. El log-retorno es log(Pt/Pt-1), y su estacionariedad también exige comprobación; dos desviaciones estándar no garantizan continuación ni probabilidad normal sin contrastar distribución y dependencia. No se reproduce un umbral propietario sin ventana y reglas completas.

## Estado de integración

Las nueve fichas y sus ejercicios se muestran en Aprender y recursos mediante config/aprendizaje.json. Se reutilizan Backtesting, Investigación y Laboratorio existentes. No se implementa el indicador propietario ni se declara reproducido el backtest de ticks. Verificación:8 pruebas de recursos/microestructura aprobadas y sintaxis JavaScript correcta.
