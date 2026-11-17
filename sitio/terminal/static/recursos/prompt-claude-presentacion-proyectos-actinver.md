# Prompt para Claude: proyectos demostrables con Actinver-terminal

Actúa como director de proyectos de analítica financiera, investigador cuantitativo y editor de un portafolio profesional. Presenta proyectos que puedo realizar a partir de los datos, código, documentación y experiencia de construcción de Actinver-terminal. El objetivo es ayudarme a elegir y explicar proyectos ante reclutadores, profesores, clientes o colaboradores, con evidencia de lo que realmente existe. Escribe en español claro y desarrolla los términos técnicos al usarlos por primera vez.

## Contexto que debes comprobar

Repositorio: `C:/Users/MIKE/Desktop/Repos/actinver-terminal`.

Entregables: `C:/Users/MIKE/Documents/Codex/2026-10-16/tienes-total-facultad-sobre-mi-pc-2/outputs`.

Lee las instrucciones vigentes del proyecto, CLAUDE.md y los documentos pertinentes de fuentes, calidad de datos, riesgo, backtesting, robustez, investigación, microestructura y permisos. Usa codebase-memory para explorar estructura si está disponible; comprueba su cobertura y contrasta el código actual donde esté desactualizado. Respeta cambios de otras sesiones. Utiliza únicamente los plugins y skills que aporten algo concreto y estén disponibles.

Consulta especialmente `docs/auditoria-post-terminal-Dej_B7_MXrX-2026-10-18.md`, `docs/recursos-certificaciones-2026-10-18.md` y la práctica `web/static/recursos/practica-proyectos-financieros.html`. Un informe antiguo orienta la revisión, pero no demuestra el estado actual.

La terminal analiza y simula; no envía órdenes. El hallazgo previo sobre el reel de la mini terminal fue: yfinance y FinBERT se instalaron y probaron fuera del motor; FRED era previo; SEC procesa Formulario 4 de insiders, no balances XBRL; las noticias auditadas procedían de Seeking Alpha con sentimiento léxico/Ollama. Revalida ese estado. No presentes estas piezas como una integración completa ni atribuyas al reel desarrollos que ya existían.

Esta tarea consiste en **evaluar y presentar opciones**. No implementes todos los proyectos, modifiques estrategias, contrates servicios, publiques contenido, conectes cuentas ni envíes datos privados a plataformas externas. Produce documentos de presentación en una carpeta de entregables; conserva el código del producto. Si un archivo necesario falta, identifica la limitación y sigue con los proyectos que sí tienen evidencia.

## Primero: inventario de evidencia y datos

Haz una revisión dirigida y de sólo lectura. Describe datos disponibles por fuente: instrumentos, campos, frecuencia, cobertura temporal, moneda, ajustes corporativos, retraso, huecos, revisiones y licencia. Comprueba qué está realmente almacenado y qué sólo está documentado. No expongas secretos, cartera personal, saldos, transacciones o identificadores: para la presentación usa agregados autorizados o ejemplos sintéticos rotulados.

Clasifica cada capacidad como implementada y comprobada, implementada pendiente de validación, demostración aislada o propuesta. Para afirmaciones materiales cita archivo y línea, fecha de prueba o artefacto. No inventes cifras de rendimiento, ahorro, precisión, experiencia laboral ni autoría. Distingue mi trabajo, contribuciones de terceros y asistencia de IA según la evidencia disponible.

## Catálogo de proyectos

Presenta entre 8 y 12 proyectos distintos, agrupando las ideas siguientes cuando se solapen. Descarta los que no aporten una pregunta o un entregable diferente:

1. **Calidad y trazabilidad de datos financieros:** detectar datos vencidos, huecos, discrepancias de moneda/mercado y splits. Entregable: panel de calidad y reporte de incidencias reproducible.
2. **Riesgo y construcción de carteras:** concentración, correlación, VaR/CVaR y comparación con una referencia sencilla como 1/N. Separar el análisis histórico de una recomendación de inversión.
3. **Investigación reproducible de estrategias:** hipótesis registrada, costes, periodos separados de desarrollo/prueba, permutaciones apropiadas y corrección por múltiples pruebas. Un resultado sin ventaja también es un proyecto valioso si explica sus límites.
4. **Contexto macro y regímenes:** explorar relaciones entre series FRED/Banxico y mercados, cuidando calendarios, revisiones, fecha de disponibilidad y correlaciones espurias.
5. **Noticias y sentimiento:** auditar el flujo existente y comparar alternativas sólo con un corpus autorizado. Distinguir clasificación de texto de capacidad para anticipar retornos; tratar FinBERT como extensión condicionada por licencia y validación.
6. **Microestructura y simulación educativa:** footprint, delta, perfiles y liquidez con replays o datos autorizados. Si faltan operaciones clasificadas o profundidad, usar ejercicios sintéticos y declarar que no equivalen a un mercado real.
7. **Opciones y gamma:** estudiar sensibilidad de un mapa GEX o una superficie de volatilidad a sus supuestos. Identificar datos faltantes, multiplicadores, interés abierto fechado y supuestos sobre inventario; no afirmar posiciones reales de dealers.
8. **Análisis fundamental y valoración:** informe de una página, DCF/reverse DCF y tres estados conciliados. La práctica local es un punto de partida educativo; un caso real requiere reportes primarios y datos que quizá todavía no estén integrados.
9. **Analítica corporativa y contable:** ratios, flujo de efectivo, variaciones presupuesto-real y dashboard de segmentos. Marcar como extensión los datos empresariales que no existan en la terminal; no fabricarlos para aparentar integración.
10. **Ingeniería de una terminal financiera local:** arquitectura, límites de seguridad, API informativa, manejo de errores, pruebas y experiencia de uso. Mostrar decisiones y mejoras medibles sin atribuir cifras que no se hayan medido.
11. **Reportes y comunicación de riesgo:** generar informes claros y auditables que expliquen fuentes, supuestos, cambios y calidad de información para un lector no técnico.

Para cada proyecto entrega una ficha con: título, problema y usuario objetivo; pregunta comprobable; datos existentes y faltantes; piezas reutilizables y trabajo nuevo; método y referencia de comparación; validación y criterios de aceptación; entregables; competencias demostrables; limitaciones; dificultad y esfuerzo estimado con supuestos. Incluye una demostración concreta que pueda presentarse y explica qué resultado invalidaría la hipótesis.

No prometas alfa, beneficio, empleo ni clientes. No uses datos sintéticos o de entrenamiento como evidencia fuera de muestra. No combines futuros, acciones mexicanas, opciones e índices como si sus unidades, sesiones y riesgos fueran equivalentes.

## Priorización y presentación

Construye una matriz comparativa: evidencia disponible, viabilidad con datos actuales, esfuerzo, coste adicional, utilidad para el puesto objetivo y claridad de la demostración. Explica los criterios y recomienda tres proyectos iniciales; si no conoces mi audiencia, asume un portafolio profesional orientado a finanzas y analítica de datos, y declara ese supuesto.

Para los tres seleccionados prepara:

- Una explicación de 60 segundos, sin jerga innecesaria.
- Una ficha de una página: problema, contribución propia comprobable, método, resultado disponible, evidencia y límites. Si todavía no existe resultado, presenta el protocolo para obtenerlo.
- Un guion de demostración de cinco minutos y las capturas o artefactos necesarios, señalando cuáles existen y cuáles faltan.
- Un plan por etapas con primer entregable pequeño, pruebas y condición de finalización. No ejecutes la implementación en esta tarea.

Entrega un documento maestro, la matriz editable y un guion de 8–10 diapositivas. Incluye borradores breves para la sección Proyectos de LinkedIn/CV, con verbos y métricas respaldados; no los publiques. Añade una explicación sencilla de cómo elegir el tema y qué información tendría que aportar para empezar.

Mantén las certificaciones en su catálogo separado. Menciónalas sólo como complemento opcional cuando sean pertinentes; no sustituyen un proyecto demostrable ni deben mezclarse con las fichas de proyectos. Al cerrar, enumera lo comprobado, lo supuesto, los datos faltantes y las rutas completas de los entregables.
