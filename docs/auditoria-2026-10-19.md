# Auditoría técnica, estética y de utilidad — 19-oct-2026

Encargo: `web/static/recursos/prompt-auditoria-tecnica-estetica-claude.md`. Base: `main` en cd5bfb5. Verificación en
**modo demostración** (datos sintéticos, base `data/demo/`), sin datos privados. codebase-memory no estuvo
disponible (servidor desconectado), así que el mapa se hizo con búsquedas directas en el código.

## 1. Hallazgos

| # | Severidad | Hallazgo | Evidencia | Efecto | Estado |
|---|---|---|---|---|---|
| 1 | P1 | El sondeo de «Movimientos públicos» (cada 4 s) no se detenía si `/api/movimientos/estado` fallaba | `setInterval` sin `try/catch` en `app.js` | Peticiones y rechazos sin fin hasta recargar | **Corregido**: se detiene y avisa del error |
| 2 | P1 | Order Flow y Option Flow podían pintar una respuesta antigua si se cambiaba rápido de instrumento | Solo Velas tenía protección (`cargaVelasId`) | Panel con datos de otro símbolo | **Corregido**: el helper `turno()` descarta cargas obsoletas, también en los errores |
| 3 | P1 | El instrumento solo pasaba entre Velas, Order Flow y Option Flow con los botones «Análisis relacionados»; con la navegación principal se perdía | `compartirSimbolo` solo en el clic de `[data-ir]` | El usuario debía volver a elegir el instrumento | **Corregido**: `activarPestana` comparte el instrumento del panel visible. Comprobado en el navegador (SIC:AMD pasa de Velas a Order Flow y a Option Flow) |
| 4 | P2 | Navegación duplicada | En el Plan de acción, 6 de 8 botones repetían pestañas siempre visibles. Además, 7 barras «Análisis relacionados», una por panel de análisis, repetían la navegación principal | 30+ botones redundantes y espacio vertical en cada panel | **Retirados** (ver §3) |
| 5 | P2 | `/api/cartera` lenta | Perfil: `cartera.serie_historica` hacía 2,662 lecturas `.at` por celda | Hasta 5.5 s con el motor demo activo | **Corregido**: lectura por posición en NumPy; misma salida (`DataFrame.equals` verdadero) |
| 6 | P3 | La consulta de estado cada 60 s seguía con la pestaña del navegador oculta | `setInterval(cargarEstado, 60000)` | Peticiones sin nadie mirando | **Corregido**: se omite si `document.hidden` y se actualiza al volver |
| 7 | P3 | En celular, la cabecera ocupa ≈ 600 de 844 px antes del contenido | Captura a 390 px | Hay que desplazarse para ver el plan | **Parcial**: se oculta la línea de atajos de teclado en ≤ 720 px. Estado de datos, procedencia y aviso demo se conservan a propósito (ver §7) |

Sin hallazgos en:
- **XSS:** no se usa `innerHTML`, `outerHTML`, `insertAdjacentHTML` ni `eval`; el DOM se construye con `h()` y `textContent`.
- **CSP:** estricta (`script-src 'self'`, sin `unsafe-inline`), también en la oficina.
- **Escucha:** solo en 127.0.0.1.
- **CSRF** en los POST; pruebas de seguridad aprobadas.
- **Separación de datos:** real, importado, calculado y sintético rotulados (chips y aviso «DATOS SIMULADOS»).
- **Controles sin nombre accesible:** 0 de los visibles.

## 2. Mapa de organización y recorridos

- **Antes:** 23 pestañas (11 principales y 12 en «Más»), más el acceso fijo «Oficina».
  - El Plan de acción tenía 8 accesos, 6 de ellos duplicados.
  - Cada panel de análisis tenía una barra «Análisis relacionados» con 5 o 6 botones que repetían la navegación.
- **Después:** las mismas 23 pestañas y la Oficina.
  - El Plan de acción tiene 2 accesos, solo a secciones de «Más»: Aprender y recursos, y Plan intradía.
  - Los paneles de análisis empiezan directamente con su contenido.
  - El cambio de instrumento entre Velas, Order Flow y Option Flow funciona con la navegación principal.
- **Recorridos revisados en el navegador:** Plan de acción → Velas → Order Flow → Option Flow con el instrumento
  conservado; Cartera, Propuestas, Riesgo y Laboratorio a 390 px.
- **Oficina:**
  - un solo acceso en la navegación;
  - «Volver a la terminal» va a `/`, que restaura la última pestaña desde `localStorage`, y lleva al Plan de acción
    si la oficina se abrió directamente;
  - la selección invalida el informe y deshabilita la exportación (6 pruebas de Node aprobadas). No se modificó.

## 3. Controles reubicados o retirados

| Elemento | Decisión | Justificación | Cómo revertir |
|---|---|---|---|
| Plan de acción: Mercado, Velas e indicadores, Order Flow, Option Flow y GEX, Riesgo, Laboratorio de alfa | Retirados | Las 6 pestañas están siempre visibles en la navegación principal; ningún código ni prueba dependía de esos botones | `git revert` del commit de esta auditoría (`web/index.html`) |
| Plan de acción: Aprender con los recursos y Plan intradía | Conservados | Llevan a secciones ocultas tras «Más» | — |
| 7 barras `nav.accesos--relacionados` | Retiradas | Duplicaban la navegación. Su única función propia (pasar el instrumento) quedó en `activarPestana` | Ídem |
| Estilos `.accesos--relacionados` | Conservados | Sin uso actual. Ocupan 2 líneas y el CSS es compartido con la oficina; se marcan como pendientes en vez de afirmar que sobran | — |

No se borraron datos, rutas de API, comandos ni funciones poco frecuentes.

## 4. Archivos cambiados y pruebas

- **Archivos:**
  - `web/index.html`: accesos duplicados.
  - `web/static/app.js`: instrumento compartido, `turno()`, consultas de Order Flow en paralelo, sondeo de la SEC
    y estado con la pestaña oculta.
  - `web/static/app.css`: línea de atajos en celular.
  - `terminal/cartera.py`: `serie_historica`.
  - `docs/mejoras-intradia-permutaciones.md` §2 y este informe.
- **Pruebas:**
  - `node --check` correcto;
  - `tests/test_cartera.py`, `test_fuentes_web.py`, `test_seguridad.py` y `test_flujo.py`: 41 aprobadas;
  - `tests/oficina-inversion.test.mjs`: 6 aprobadas;
  - equivalencia de `serie_historica` antigua y nueva sobre la cartera demo: idéntica.
- **No se ejecutó la suite completa**: los cambios no tocan cálculos fuera de `serie_historica`.

## 5. Capturas

- **Después:** Plan de acción a 390 px en modo demo, en la conversación de esta entrega.
- **Antes:** no se obtuvieron capturas, porque el panel del navegador no dibujaba (pestaña oculta). El estado anterior
  se reproduce con `git checkout cd5bfb5 -- web/`.
- Desbordamiento horizontal medido a 390 px en Plan de acción, Cartera, Propuestas, Velas, Order Flow, Option Flow,
  Riesgo y Laboratorio: ancho del documento = 390 en todos y ningún elemento sale de la ventana.

## 6. Rendimiento medido (modo demo, esta PC)

| Medida | Antes | Después |
|---|---|---|
| `serie_historica` (cartera demo: 8 transacciones, 1,254 sesiones), media de 5 | 0.265 s | 0.022 s |
| `/api/cartera` con `curl`, 3 llamadas | 4.46 / 1.05 / 5.50 s (motor demo arrancando) | 0.49 / 0.77 / 0.34 s |
| Primera carga del Plan de acción | 7 peticiones `/api/`; la más lenta, cartera, 7.0 s | Sin repetir en condiciones equivalentes |

La comparación de `/api/cartera` mezcla condiciones distintas: antes el motor demo estaba en su primer ciclo. La
medida comparable es la de `serie_historica` aislada. No se midió CPU ni RAM del servidor.

## 7. Riesgos y pendientes

- **Cabecera en celular:** sigue alta. Reducirla más exigiría plegar el estado de datos (procedencia, retraso, modo
  demo), que el encargo pide conservar a la vista. Propuesta para tu decisión: un resumen de una línea con
  «Ver detalle» en ≤ 720 px.
- **23 pestañas:** reagruparlas por tarea (operar, analizar, investigar, aprender) cambiaría la navegación aprendida.
  Se deja como propuesta.
- **Sin probar:** zoom al 200 %, lector de pantalla real, contraste WCAG con herramienta. El contraste no se
  modificó.
- **Pendiente de uso:** los estilos `.accesos--relacionados` quedaron sin uso.
- **Fuera de alcance:** el resto de los 109 endpoints no se auditó uno por uno. Las pruebas de API existentes cubren
  los de seguridad.
