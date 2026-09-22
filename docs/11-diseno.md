# 11 · Decisiones de diseño

Objetivo: una herramienta sobria que responda en la primera pantalla «¿qué tan actuales son mis datos, cómo está mi cartera, qué propone cada alternativa, qué riesgos tiene y qué cambiaría?».

## Estructura

- **Vista inicial (Resumen)**: franja de estado de datos → cartera actual → dos tarjetas de propuesta lado a lado → clasificación → riesgos y cambios. Es el recorrido de lectura natural de arriba abajo.
- **Seis pestañas** con nombres de tarea (Resumen, Propuestas, Mi cartera, Datos, Perfil, Ayuda). Menos opciones visibles a la vez reduce el tiempo de decisión; el detalle técnico (reproducibilidad, excluidos, sensibilidad, auditoría) va en secciones plegables.
- **Una acción primaria**: «Recalcular propuestas» (botón de color de acento, arriba a la derecha y fijo abajo en móvil, al alcance del pulgar y con área ≥ 40 px). «Actualizar datos» es secundaria.

## Principios aplicados (en qué se nota)

| Principio | Aplicación |
|---|---|
| Menos opciones por decisión | Seis pestañas; formularios muestran solo los campos del tipo de operación elegido |
| Objetivos grandes y cercanos | Botones de 40–44 px; CTA fijo en móvil; pestañas de altura completa |
| Convenciones conocidas | Pestañas, tablas, chips de estado, formularios estándar; colores verde/ámbar/rojo con texto (no solo color) |
| Proximidad y región común | Cada propuesta es una tarjeta con su puntuación, métricas y pesos juntos; KPI agrupados |
| Similitud y consistencia | Mismos chips de vigencia en todas las vistas; mismas columnas de dato (proveedor, fecha, tipo) |
| Forma simple | Tipografía del sistema, sin sombras decorativas, una sola familia de radio y espaciado |
| Límite de memoria | Máx. 4 KPI por fila; top 6 pesos en el resumen; el resto en detalle |
| Respuesta < 400 ms | Consultas locales < 200 ms; el cálculo largo muestra estado «Calculando…» y deshabilita el botón |
| Elemento distinto destaca | Solo la propuesta con mayor puntuación lleva borde de acento; «Modo demostración» tiene franja propia |
| Posición serial | Lo más importante (estado de datos) al inicio; el aviso legal y «no envía órdenes» al final |
| Tareas inconclusas visibles | Vista previa de importación pendiente de confirmar; aviso «su cartera cambió: recalcule» |
| Pico y final | El cálculo termina con notificación clara; las importaciones cierran con resumen de lo guardado |
| Distancia al objetivo | Del resumen a los cambios sugeridos en un clic («Ver detalle y cambios») |
| Complejidad que absorbe el sistema | Conversión de moneda, calendarios, duplicados y vigencia se resuelven solos; el usuario solo ve el resultado |
| Tolerante al capturar, estricto al validar | Acepta comas de miles, mayúsculas, clave corta («IVV»), `;` o `,` en CSV y UTF-8/Latin-1; rechaza fechas futuras, signos o instrumentos inexistentes con mensajes por campo |
| Tiempo acotado | Cálculo con candado (uno a la vez) y límite de frecuencia |
| Lo mínimo necesario | Sin librerías de interfaz ni gráficos; SVG propio de ~40 líneas |
| Lo que más aporta primero | Resumen dedicado al 20 % de información que responde el 80 % de las preguntas |

## Accesibilidad

- `lang="es-MX"`, enlace «Saltar al contenido», un `h1` por vista, jerarquía h2/h3.
- Pestañas con `role="tablist"`, `aria-selected`, flechas/Inicio/Fin; foco visible de 3 px.
- Todos los campos con `<label>`; errores en región `role="alert"` y `aria-invalid` en el campo.
- Estados de datos en región `aria-live`.
- Gráfica con `role="img"` y `aria-label`; las cifras también están en tablas.
- Contraste medido: mínimo 5.24:1 en tema claro y 6.1:1 en oscuro (AA exige 4.5:1). Respeta `prefers-reduced-motion`.

## Estados

- **Carga**: texto «Cargando…» en cada región.
- **Vacío**: mensajes que dicen qué hacer («Registre una aportación…», «Pulse Recalcular…»).
- **Error**: cajas rojas con el mensaje del servidor; 404 propia; errores de formulario por campo.
- **Suspendido / no actual / sintético**: chips y avisos específicos.

## Temas y responsive

Tokens CSS con modo claro y oscuro (sigue al sistema). Rejillas `auto-fit`; tablas con desplazamiento dentro de su contenedor; sin desplazamiento horizontal de página a 375 px.
