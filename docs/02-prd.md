# 02 · PRD — Terminal local de análisis de portafolios

## Problema

El inversionista tiene acceso a una lista amplia de acciones (BMV y SIC), algunos ETF y fondos de Actinver, pero no cuenta con una vista única que (1) registre su cartera real, (2) proponga carteras alternativas con criterios explícitos y (3) le indique con honestidad qué tan actuales y confiables son los datos.

## Usuarios

| Usuario | Necesidad | Frecuencia |
|---|---|---|
| Estudiante en el Reto Actinver 2026 (principal) | Saber cada día qué cartera conviene con 1 000 000 actipesos, cumplir las reglas (≥ 5 emisoras, ≤ 50 %), enterarse a tiempo cuando conviene cambiar algo y no olvidar el avance educativo | Diaria durante la competencia |
| Inversionista individual | Ver su cartera, comparar propuestas, entender cambios y riesgos antes de decidir en su casa de bolsa | Semanal / tras cada operación |
| Asesor o familiar de confianza (secundario, en la misma PC) | Revisar la lógica y los supuestos | Ocasional |

## Casos de uso

1. **CU-1 Ver estado**: al abrir, ver vigencia de datos, cartera actual, comparación de las dos propuestas, riesgos y qué cambiaría.
2. **CU-2 Registrar operaciones**: capturar compra, venta, aportación, retiro, dividendo, comisión, impuesto o split; corregir o anular con motivo.
3. **CU-3 Importar**: cargar CSV de operaciones, posiciones iniciales o precios/NAV con vista previa y confirmación.
4. **CU-4 Ajustar criterios**: cambiar riesgo, horizonte, capital, topes, exposición USD, escenario y exclusiones sin tocar código.
5. **CU-5 Comparar propuestas**: ver puntuación desglosada, pesos, montos, títulos, motivos, validación fuera de muestra, escenarios, sensibilidad y cambios sugeridos con costo e impuesto estimados.
6. **CU-6 Revisar datos**: ver por instrumento proveedor, bolsa, moneda, zona horaria, hora del dato, tipo, retraso medido y vigencia; estado de cada proveedor y peticiones restantes.
7. **CU-7 Mantener**: actualizar datos, respaldar y restaurar.

## Requisitos funcionales

| Id | Requisito |
|---|---|
| RF-1 | Dos propuestas: «Solo acciones» (clases acción/REIT) y «Acciones + ETF + fondos» (acciones, ETF, FIBRA, fondos). La clase proviene de la verificación, no del rótulo del PDF. |
| RF-2 | Cada propuesta incluye pesos, montos, títulos aproximados, razones de inclusión, riesgos, fecha de cálculo, fecha de datos, calidad de datos y cambios frente a posiciones. |
| RF-3 | Puntuación 0–100 con seis criterios ponderados y explicación por criterio; clasificación rotulada como orden relativo, no certeza. |
| RF-4 | Optimización reproducible: función objetivo, restricciones, ventana y huella de datos visibles. |
| RF-5 | Validación walk-forward sin información futura, con costos; comparación contra 1/N y contra mantener la cartera actual. |
| RF-6 | Sensibilidad (ventana y aversión) y escenarios (p10/p50/p90, peor mes/trimestre, caída máxima, estrés hipotético). |
| RF-7 | Banda de no-rebalanceo (2 pp y monto mínimo) para evitar cambios por variaciones pequeñas. |
| RF-8 | Libro de operaciones con costo promedio, realizado, no realizado, dividendos, comisiones, impuestos, TWR, TIR y comparación con índice. |
| RF-9 | Importación validada (solo .csv, ≤ 1 MB, ≤ 5 000 filas), duplicados por huella, original conservado, auditoría. |
| RF-10 | Vigencia por dato; datos vencidos excluidos; propuesta suspendida si no hay datos suficientes o tipo de cambio; propuesta guardada marcada «no actual» si envejece o cambia el perfil. |
| RF-11 | Adaptadores sustituibles con límites de peticiones persistentes; credenciales solo por entorno. |
| RF-12 | Sin rutas de órdenes ni integración con brókers. |

## Requisitos no funcionales

- Arranque en un comando; respuesta de consultas < 200 ms; cálculo de propuestas < 30 s con indicador de progreso.
- Accesibilidad: contraste AA, navegación por teclado (incluidas pestañas con flechas), etiquetas en todos los campos, mensajes de error asociados.
- Adaptable a 375 px sin desplazamiento horizontal de página.
- Solo escucha en 127.0.0.1; ver [seguridad.md](seguridad.md).

## Criterios de aceptación

| # | Criterio | Evidencia |
|---|---|---|
| CA-1 | Se inicia localmente con instrucciones claras | README; [13-evidencia.md](13-evidencia.md) §1 |
| CA-2 | Las dos vistas funcionan y no mezclan clases por la etiqueta del PDF | `test_universo.py`, `test_optimizador.py::test_solo_acciones_no_mezcla_clases` |
| CA-3 | Posiciones y rendimientos correctos con transacciones de prueba conocidas | `test_cartera.py` (valores calculados a mano) |
| CA-4 | Cada dato muestra fuente, fecha y vigencia; fuente caída o dato vencido no produce recomendación actual | `test_optimizador.py::test_dato_vencido...`, `test_sin_tipo_de_cambio...`; captura del modo real |
| CA-5 | Clasificación y motivos cambian de forma reproducible con riesgo, horizonte o restricciones | `test_optimizador.py::test_cambia_con_riesgo...`, `test_reproducible` |
| CA-6 | Sin claves en el repositorio ni operaciones reales | `test_seguridad.py::test_sin_secretos...`, `test_no_existen_rutas_de_ordenes_reales` |
| CA-7 | Escritorio y móvil; accesibilidad básica, errores y rendimiento verificados | [13-evidencia.md](13-evidencia.md) §5–7 |
| CA-8 | Matriz de aplicabilidad completa | [matriz.md](matriz.md) |

## Límites (fuera de alcance)

- Envío de órdenes, conexión a brókers, CFD, apalancamiento, ventas en corto, derivados.
- Datos en tiempo real (no contratados).
- Asesoría personalizada o promesa de rendimientos.
- Deducción de tenencias o rentabilidad a partir del PDF.
- Multiusuario, acceso remoto y publicación en internet (previsto solo como plan en [seguridad.md](seguridad.md)).
- Cálculo fiscal definitivo (el ISR es una estimación configurable).

## Ampliación 2026-09-23 (Reto)

**Casos de uso nuevos**
- **CU-8 Reto**: ver etapa, sesiones restantes, reglas (con «regla sin confirmar»), cumplimiento de su cartera y tareas pendientes (incluido el avance en Acelera Academy, que la terminal no cubre).
- **CU-9 Lentes**: comparar «máximo rendimiento esperado» (agresiva, con riesgo explícito) y «ajuste a su perfil y cartera» en cada universo.
- **CU-10 Alertas**: recibir un aviso de escritorio cuando la deriva supera el umbral con mejora neta de costos, cuando una posición toca stop/toma de utilidad/caída desde máximo, ante un evento macro de alto impacto, una operación de insider o una noticia relevante, o cuando un dato está vencido; simular el cambio sugerido.
- **CU-11 Mercado**: calendario macro, titulares e insiders de sus emisoras; gráfica por activo.
- **CU-12 Universo del simulador**: importar la lista de instrumentos del simulador para restringir el universo.

**Criterios de aceptación añadidos**

| # | Criterio | Evidencia |
|---|---|---|
| CA-9 | Las propuestas se recalculan solas al llegar datos nuevos y cambian de forma reproducible | `servicios.ciclo`, `test_reproducible`, estado del motor en la barra |
| CA-10 | Cada regla de alerta dispara en una prueba simulada y respeta enfriamiento | `tests/test_alertas.py` |
| CA-11 | Reglas del Reto aplicadas y visibles | `tests/test_reto.py` |
| CA-12 | Cada repositorio tiene ficha; cada URL tiene uso documentado | `docs/repos.md` (64), `docs/fuentes.md` |

**Límites añadidos**: la terminal no captura órdenes en el simulador ni automatiza la sesión del Reto (el reglamento solo reconoce órdenes del navegador); no hay tiempo real de la BMV sin contrato.
