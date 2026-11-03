# Excel instalado: revisión visual parcial — 1-nov-2026

Pendiente TP01-03 revalidado mediante computer-use, sin COM ni cambios de activación. No había sesiones conectadas al plugin de documentos.

## Comprobado

Excel 2013 abrió `docs/terminal-pro-20261101-evidencia/excel/plantilla-sintetico-despues.xlsx`. La ventana conserva «Error de activación de productos», pero permitió mostrar el archivo. No hubo aviso observado de reparación ni se habilitaron macros o vínculos.

- Guía: banda negra, título blanco, borde rojo, cuerpo blanco, texto legible y pestañas rojas.
- Paramétrico Acelera, maximizado: encabezados oscuros, texto blanco y bordes rojos punteados en entradas; matrices y cifras visibles. No se editaron valores ni fórmulas.
- Vista previa de impresión de esa hoja: tabla y resultados contenidos dentro de la página observada. No se pulsó Imprimir; la impresora mostraba «Sin conexión». No acredita impresión física, otras hojas ni legibilidad del segundo libro.

Capturas de Excel: `terminal-pro-20261101-evidencia/excel/revision-visual/plantilla-guia.png`, `plantilla-parametrico.png`, `plantilla-parametrico-maximizado.png` y `plantilla-impresion.png`. Se guardaron únicamente capturas de la muestra de Excel como evidencia; no se guardaron imágenes incidentales de otras aplicaciones.

## Límites y recuperación

Al abrir el archivo se creó una ventana de libro distinta de Libro1. Se reenumeraron ventanas y se seleccionó por título exacto. Posteriormente el controlador reportó un ancho de 8 px para esa ventana, pese a mostrar otra captura de contenido. Un clic en Cancelar falló por límites; se recuperó la ventana y se canceló el aviso mediante Escape. No se eligió Guardar ni No guardar. Maximizar mediante el menú del sistema permitió ver la hoja completa.

Ctrl+F12 mostró el selector para abrir el segundo libro, pero las observaciones siguientes no permitieron confirmar el foco del campo. No se escribió texto sin foco comprobado; se canceló el selector con Escape. El segundo libro no está revisado. Un intento de calcular el hash de la plantilla fue rechazado por bloqueo de archivo abierto: no se interpreta como corrupción ni se fuerza el cierre.

El archivo quedó abierto en Excel, sin guardado solicitado por el agente. No se modificaron ni sobrescribieron los libros de muestra. La validación programática previa de identidad numérica conserva su alcance, no sustituye esta revisión visual.

## Para completar TP01-03

1. Abrir `libro-sintetico-despues.xlsx` desde la misma carpeta en Excel.
2. Revisar sus hojas de presentación, entradas/resultados y gráficos con zoom legible.
3. Revisar Archivo → Imprimir sin imprimir, comprobando paginación y textos recortados por hoja.
4. Revisar también las hojas históricas y el gráfico de la plantilla, aún no comprobados visualmente.
5. Mantener rotulado sintético y no guardar cambios de datos o fórmulas. No requiere comprar ni activar un servicio para registrar lo que ya pudo comprobarse; el acceso futuro depende de la aplicación instalada.

No se marca el ID como terminado. Sin operaciones, mensajes externos, commit ni push.
