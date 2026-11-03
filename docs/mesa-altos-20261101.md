# Alto persistente de Mesa — 1-nov-2026

TP01-04: los marcos externos conservan su alto al cerrar/reabrir y recargar, tanto en la disposición actual como en las guardadas con nombre. Un deslizador etiquetado permite teclado (flechas, Inicio y Fin); conserva el arrastre nativo. Se aceptan únicamente IDs del catálogo y enteros entre 250 y 2000 px. Disposiciones antiguas sin altos siguen siendo válidas. Los paneles nativos mantienen su alto natural, sin recortar información.

El observador se desconecta al cerrar el marco. El crecimiento automático de navegación para mostrar el proveedor completo sigue funcionando y también se conserva. No hay bibliotecas nuevas, consultas de mercado ni cambios numéricos o financieros.

## Evidencia

- `node --test tests/*.test.mjs`: 49 aprobadas, 0 fallidas, 1596.7489 ms. Registro: `proveedores-20261101-evidencia/mesa-altos-node-20261101.txt`.
- Chromium aislado en 390 y 1440 px: teclado hasta 1999 px, cierre elimina iframe, reapertura y recarga restauran dimensión; sin errores JS ni desbordamiento. Registro: `proveedores-20261101-evidencia/mesa-altos-ui-20261101.json`.
- Proveedores simulados y conexiones externas bloqueadas: no acredita disponibilidad ni vigencia de datos externos.
- `git diff --check` de los archivos de código y estado modificados: sin errores.
- No se repitió Python/worker: esta continuación solo cambia JS/CSS y documentación. La suite anterior sigue documentada con su alcance original, no como prueba de estos cambios posteriores.

Exploración: skill codebase-memory leída; list_projects y check_index_coverage devolvieron Transport closed. Fallback explícito por lectura y búsqueda de mesa.mjs, mesa.css, navegacion.mjs y tests/mesa.test.mjs. Se preservaron los cambios previos del módulo.

Siguen abiertos los otros IDs del registro; no se convierte un bloqueo externo en aprobación. Sin commit ni push, sin operaciones ni notificaciones externas.

## Regresión posterior: cambiar de disposición sin recrear el marco

Se reprodujo un fallo real: al elegir la disposición de 900 px el marco reutilizado permanecía en 620 px. El ancho también podía conservar el estado anterior. La rama que conserva nodos ahora aplica alto, deslizador, salida en píxeles, clase de ancho y aria-pressed de la disposición seleccionada. No se reemplaza el iframe ni se vacía su contenido al cambiar dimensiones.

Prueba permanente: tests/navegador/mesa-disposiciones.cjs. Requiere Playwright y Chromium existentes; no instala dependencias ni inicia servidor. PLAYWRIGHT_MODULO y CHROMIUM_EJECUTABLE permiten usar instalaciones existentes; TERMINAL_RAIZ es opcional. Ejecutar con node tests/navegador/mesa-disposiciones.cjs.

Chromium 390/1440: alterna Compacta (620 px) y Amplia (900 px, toda la fila), confirma mismo objeto iframe, restaura ancho/alto, conserva teclado y recarga a 1999 px, y destruye el marco al plegar. Cero errores JS y cero desbordamiento. Evidencia: proveedores-20261101-evidencia/mesa-disposiciones-ui-20261101.json. Proveedores simulados: no acredita sus datos. Node completo en esa corrección: 52 aprobadas, 1431.1632 ms (mesa-disposiciones-node-20261101.txt). La acotación posterior del selector output se verificó con el recorrido permanente.
