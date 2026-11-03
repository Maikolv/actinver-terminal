# Correcciones verificadas en Excel — 1-nov-2026

La apertura manual del usuario permitió recuperar el control de Excel. Se abrió también el segundo libro desde el selector nativo y se eligió su ventana nueva por título, sin tocar documentos personales. Este informe amplía la revisión parcial anterior; no elimina sus fallos de controlador ni las capturas previas.

## Defectos observados y cambios

1. Histórico Datos de la plantilla mostraba encabezados editables blancos sobre fondo rosa muy claro. `_entrada` ahora copia la fuente y cambia solo su color a TEXTO oscuro, preservando negritas y demás atributos. La copia final se abrió en Excel y los cinco encabezados editables se observan oscuros y legibles; la regresión programática pasa.
2. Resumen recortaba el nombre de Método. Ahora ajusta las columnas de texto a varias líneas. La copia nueva muestra «Máximo Sharpe (portafolio tangente)» completo en Excel.
3. P2 Modelo se repartía en siete páginas verticales sin escalado. La configuración del libro ahora usa horizontal, una página de ancho, altura sin limitar y filas de título repetidas. La vista previa de la copia nueva muestra dos páginas, con todas las columnas y el gráfico en una misma página de ancho. No se imprimió ni se garantiza legibilidad física para cualquier impresora.

Las muestras nuevas rotulan cada hoja con DATOS SINTÉTICOS. El script de muestras conserva el margen del título para el logo. No se sobrescribieron los originales abiertos; los archivos nuevos tienen sufijo `revision-20261101`.

## Evidencia

Capturas en `terminal-pro-20261101-evidencia/excel/revision-visual/`: Histórico Datos antes del arreglo, hojas del libro (Guía, Resumen, P1/P2 Datos y Modelo), impresión anterior y `libro-corregido-p2-impresion.png`, además de `libro-corregido-resumen.png`.

Pruebas posteriores: **17 aprobadas, una advertencia, 54.00 s**, salida 0; `proveedores-20261101-evidencia/excel-presentacion-pytest-20261101.txt`. Incluyen identidad visual, preservación de contenido/formato, configuración de impresión y generación Markowitz. La suite completa de **858 aprobadas** corresponde a la fase anterior a estos cambios de Excel; no se presenta como reejecución del código posterior.

Comparación en `terminal-pro-20261101-evidencia/excel/revision-visual/comparacion-presentacion-20261101.json`: tras normalizar únicamente el rótulo sintético añadido, la plantilla conserva igualdad exacta de estructura, valores, fórmulas y formatos del volcado. El libro recalculado tiene **36 diferencias de punto flotante**, máximo absoluto **1.6653345369377348e-16**; no hay otras diferencias en los campos comparados. No se llama igualdad exacta al libro. El volcado compara cantidades de imágenes/gráficos, no igualdad binaria de sus archivos internos.

Una generación anterior abortó con error de memoria OpenBLAS. Se esperó a terminar la selección de pruebas y se repitió con OPENBLAS/OMP/MKL limitados a un hilo; entonces se generaron ambas muestras. No se atribuye ahorro de rendimiento ni se oculta el intento fallido.

## Revisión final de TP01-03

- Contraste de Histórico Datos comprobado en la copia final: `plantilla-historico-datos-final.png`.
- Ejercicio Paramétrico Acelera comprobado en la copia final: una página horizontal, gráfico completo sin corte, contador «1 de 1» y rótulo sintético. Captura `plantilla-parametrico-impresion-final.png`. Esta hoja usa altura de una página; las hojas históricas conservan altura libre. Dos pruebas de identidad posteriores a este último ajuste: aprobadas en 6.69 s, salida 0 (`excel-final-identidad-20261101.txt`).
- Histórico Modelo comprobado en la copia final: una página horizontal, todas las columnas y resultados visibles, contador «1 de 1». Captura `plantilla-historico-modelo-impresion-final.png`.
- Guía de la plantilla: páginas 1 y 2 observadas, encabezado repetido y leyenda de entradas/resultados legible. Capturas `plantilla-guia-impresion-pagina1-final.png` y `plantilla-guia-impresion-pagina2-final.png`.
- Libro, Resumen: una página, método y columnas completos (`libro-resumen-impresion-final.png`). P1 Modelo: ambas páginas observadas, gráfico completo en la primera y continuación de frontera en la segunda (`libro-p1-modelo-impresion-pagina1-final.png` y `pagina2-final.png`).
- Libro, P1 Datos: ocho páginas indicadas por Excel; páginas 1 y 2 observadas, con precios y rendimientos en el mismo ancho y encabezados repetidos. P2 Datos: diez páginas indicadas; primera observada con todas las columnas. No se afirma haber inspeccionado las ocho o diez páginas completas. Capturas `libro-p1-datos-impresion-pagina1-final.png`, `pagina2-final.png` y `libro-p2-datos-impresion-pagina1-final.png`.
- Libro, Guía: ambas páginas observadas con encabezado repetido y leyenda visual en la segunda (`libro-guia-impresion-pagina1-final.png` y `pagina2-final.png`).
- Continuación posterior: P1 Datos ya inspeccionado íntegramente, páginas 1 a 8; encabezados, cinco precios y cinco rendimientos permanecen visibles, hasta la última fecha sintética 30-oct-2026. Capturas individuales `libro-p1-datos-impresion-pagina1-final.png` a `pagina8-final.png`. La segunda página de P2 Modelo también se observó y guardó (`libro-p2-modelo-impresion-pagina2-final.png`), con la continuación de la frontera y el título repetido.
- Revisión terminada: P2 Datos, páginas 1 a 10, y Histórico Datos de la plantilla final, páginas 1 a 8, inspeccionados individualmente. Capturas por página con prefijos `libro-p2-datos-impresion-pagina` y `plantilla-historico-datos-impresion-pagina`, sufijo `-final.png`. En ambos casos los encabezados se repiten y las columnas permanecen dentro de la página. La plantilla vacía conserva sus filas editables vacías: no se inventaron precios para revisarla.
- Las diez hojas de los dos archivos tienen revisión de contenido en pantalla y de todas sus páginas de vista previa. El alcance es Excel 2013 con el formato Carta mostrado por la aplicación; no incluye impresión física, otras impresoras ni validación financiera de los ejemplos sintéticos.
- La revisión no acredita exactitud de una optimización sobre datos reales, rentabilidad o protección del portafolio.

No se ejecutó Solver, no se editaron pesos ni valores en Excel, no se guardó desde Excel y no se enviaron órdenes. Los archivos de revisión permanecen abiertos; no se forzó su cierre. Sin commit ni push.

Nueva suite completa sobre el código posterior de Excel terminada: **859 aprobadas, cero fallidas, una advertencia, 1097.18 s (18:17), salida 0**. Motor, carga de entorno y configuración local desactivados; BLAS limitado a un hilo. Registro: `proveedores-20261101-evidencia/excel-conjunto-final-20261101.txt`. Advertencia de deprecación BlockingPortal de Starlette/AnyIO. Este resultado sustituye la nota de ejecución en curso, sin borrar el resultado de 858 de la fase anterior.

codebase-memory devolvió Transport closed durante la búsqueda; después el namespace fue retirado temporalmente. Fallback directo en excel_markowitz.py y pruebas. No se copió código de skills ni de otro repositorio.
