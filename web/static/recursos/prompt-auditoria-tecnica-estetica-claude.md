# Prompt para Claude Code: auditoría técnica, estética y de utilidad de Actinver-terminal

Actúa como auditor de software y diseñador de producto. Audita y mejora `C:/Users/MIKE/Desktop/Repos/actinver-terminal`, incluida su oficina de inversión. El objetivo es una terminal fiable, rápida, comprensible y visualmente coherente, donde cada elemento tenga una función comprobable. Da prioridad al espacio útil, a la jerarquía y a los recorridos de trabajo; añadir más controles no es una mejora por sí mismo.

## Preparación y evidencia

Lee CLAUDE.md, el mandato vigente, docs/resumen-ejecutivo.md, docs/token-budget.md y las instrucciones aplicables. Comprueba Git y conserva cambios ajenos. Usa codebase-memory para explorar estructura, comprueba cobertura y actualidad, pagina resultados relevantes y consulta las fuentes cuando el grafo esté incompleto. No hagas afirmaciones de código muerto basadas en una búsqueda aislada. No leas ni exportes .env, credenciales o datos personales para el informe.

Levanta un mapa de rutas, vistas, componentes, fuentes de datos, servicios, persistencia y pruebas. Identifica los recorridos principales: ver cartera, comparar propuestas, estudiar un instrumento, revisar velas/flujo/riesgo, consultar investigación y entrar/salir de la oficina. Registra capturas antes de cambiar cada vista, usando demostración o datos públicos autorizados y sin publicar información privada.

## 1. Auditoría técnica

- Revisa contratos de API, manejo de errores, estados vacíos/carga/parcial/antiguo y recuperación. Verifica validación de entradas, tipado, nulos, fechas, zonas horarias, monedas, vencimientos y feeds. No equipares un instrumento del catálogo con disponibilidad de datos intradía.
- Revisa separación entre datos reales, importados, calculados y sintéticos. Las capturas y los cierres diarios no deben transformarse en ticks/velas ficticias. No infieras agresor, liquidez, gamma ni precios faltantes. Fuente, fecha, calidad y retraso deben acompañar las interpretaciones.
- Revisa concurrencia, cancelación, respuestas fuera de orden, caché, límites de proveedores, consultas SQLite e integridad de transacciones. No repitas cálculos ni solicitudes en pestañas ocultas. Mide CPU/RAM, peticiones y latencias con una carga reproducible antes y después; no inventes porcentajes.
- Revisa dependencias/licencias, superficie de ataque, CSRF, XSS, CSP, exposición de secretos, logging y permisos. Mantén 127.0.0.1 y sólo lectura/simulación. No actives órdenes, túneles ni conexiones reales.
- Verifica cálculos financieros con pruebas independientes y casos límite; separa precisión matemática de evidencia de rentabilidad. Toda afirmación de alfa requiere datos, costes, validación temporal y pruebas estadísticas adecuadas.

## 2. Auditoría estética y de espacio

Usa `web/static/app.css` como fuente de los estilos compartidos: tipografía, paleta, superficies, bordes, botones, foco y modos claro/oscuro. Evita crear otra identidad visual para la oficina. Sin ilustraciones generadas, personajes decorativos, degradados arbitrarios ni fuentes descargadas por adorno. Usa recursos del producto o recursos con licencia verificada sólo cuando comuniquen algo útil.

Para cada pantalla dibuja una jerarquía: tarea principal, evidencia, acciones relacionadas y ayuda secundaria. El tamaño y la posición deben responder a esa prioridad. Reduce espacio desperdiciado, pero conserva legibilidad y separación entre grupos; no confundas densidad con saturación.

Para cada botón/enlace documenta: propósito, resultado, frecuencia de uso, ubicación lógica y alternativa existente. Una acción primaria por grupo; acciones secundarias junto al contenido que afectan; navegación separada de cambios de datos. No añadas botones aislados para llenar huecos. Evita barras saturadas, controles duplicados, textos repetidos y tarjetas que sólo repitan un título.

Revisa alineación, escala tipográfica, ancho de lectura, márgenes, rejilla, ritmo vertical, saltos de línea, tablas, etiquetas y estados. Comprueba teclado, foco, etiquetas accesibles, lectores de pantalla y contraste WCAG AA. No uses sólo color para expresar estado. Prueba escritorio y anchos pequeños (390 y 768 px) con y sin datos, nombres largos, zoom 200 %, carga y errores; ningún control esencial debe quedar oculto o producir desbordamiento horizontal.

## 3. Eliminar lo que no sirve

Clasifica cada elemento como esencial, apoyo útil, duplicado, obsoleto o sin función demostrada. Retira por completo los duplicados/obsoletos comprobados: interfaz, eventos, estilos, imports, enlaces y documentación que queden huérfanos. No te limites a ocultarlos con CSS.

Antes de eliminar código comprueba referencias estáticas y dinámicas, rutas/API, configuración, comandos, tareas y pruebas. La ausencia de clics en una sesión no demuestra inutilidad. Conserva controles de riesgo, procedencia, accesibilidad, estados de error y funciones poco frecuentes que evitan pérdidas de información. No borres datos, repositorios externos, respaldos o trabajo ajeno. Documenta qué se retiró, por qué, qué evidencia lo respalda y cómo revertirlo desde Git. Si una utilidad es incierta, déjala identificada como pendiente en vez de afirmar que sobra.

## 4. Oficina de inversión

Verifica el acceso Oficina en la navegación principal y Volver a la terminal en su cabecera. El regreso debe recuperar la sección previa que recuerda la terminal y funcionar también si se abre la oficina directamente. Evita un segundo acceso idéntico en el mismo grupo.

El instrumento se selecciona del catálogo, incluyendo símbolos importados con vencimiento exacto. Revisa deduplicación por identificador, instrumentos inactivos, nombres largos, catálogo vacío/parcial y errores de carga. No conviertas MES/MNQ genéricos en vencimientos inventados. Cambiar instrumento o intervalo debe invalidar el informe anterior y deshabilitar su exportación hasta obtener el nuevo. No fabriques resultados si no hay datos. Conserva informe, procedencia y preparación de análisis para Claude, con una ubicación consistente.

## 5. Ejecutar, verificar y entregar

Prioriza P0 integridad/seguridad, P1 funciones y navegación, P2 espacio/jerarquía/accesibilidad, P3 detalle visual. Aplica mejoras reversibles dentro del alcance, no sólo recomendaciones. Prueba según el cambio: cálculos con pruebas financieras, API con contratos e integración, navegación con navegador y diseño con capturas de estados y tamaños. No crees pruebas triviales que sólo copien el HTML ni ejecutes toda la batería sin justificación. No declares aprobado lo que no probaste.

Entrega: (1) hallazgos con severidad, evidencia y efecto; (2) mapa antes/después de organización y recorridos; (3) tabla de controles reubicados y elementos eliminados con justificación; (4) archivos cambiados y pruebas/resultados; (5) capturas comparables sin datos privados; (6) medidas de rendimiento realmente obtenidas; (7) riesgos y pendientes. Explica qué quedó aplicado, qué fue sólo propuesto y qué requiere una decisión del usuario. Actualiza la documentación necesaria y no incluyas cambios ajenos en commits.
