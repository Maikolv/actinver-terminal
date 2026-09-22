# 02 · PRD — Terminal local de análisis de portafolios

## Problema

El inversionista tiene acceso a una lista amplia de acciones (BMV y SIC), algunos ETF y fondos de Actinver, pero no cuenta con una vista única que (1) registre su cartera real, (2) proponga carteras alternativas con criterios explícitos y (3) le indique con honestidad qué tan actuales y confiables son los datos.

## Usuarios

| Usuario | Necesidad | Frecuencia |
|---|---|---|
| Inversionista individual (principal) | Ver su cartera, comparar propuestas, entender cambios y riesgos antes de decidir en su casa de bolsa | Semanal / tras cada operación |
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
- Solo escucha en 127.0.0.1; ver [12-seguridad.md](12-seguridad.md).

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
| CA-8 | Matriz de aplicabilidad completa | [07-matriz-aplicabilidad.md](07-matriz-aplicabilidad.md) |

## Límites (fuera de alcance)

- Envío de órdenes, conexión a brókers, CFD, apalancamiento, ventas en corto, derivados.
- Datos en tiempo real (no contratados).
- Asesoría personalizada o promesa de rendimientos.
- Deducción de tenencias o rentabilidad a partir del PDF.
- Multiusuario, acceso remoto y publicación en internet (previsto solo como plan en [12-seguridad.md](12-seguridad.md)).
- Cálculo fiscal definitivo (el ISR es una estimación configurable).
