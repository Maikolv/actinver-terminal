# Paleta principal compartida — 1-nov-2026

TP01-05: la barra existente de la terminal principal ahora muestra sugerencias de instrumentos activos y secciones por nombre. Mesa y terminal reutilizan `paleta.mjs`; no se importa el módulo completo de Mesa (con sus efectos DOM) en la página principal. Mesa conserva además sus acciones de paneles y disposiciones.

Se conservan los comandos con barra y la búsqueda exacta anterior. Flechas seleccionan, Enter navega, Escape cierra primero las sugerencias sin borrar el texto; Ctrl/Cmd+K enfoca la misma barra. El listado usa combobox/listbox, selección y descendiente activo. No hay nuevos botones ni dependencias. Usa tokens de la terminal.

La primera consulta escrita carga el módulo, navegación y catálogo ligero; las siguientes reutilizan la misma promesa. El catálogo ligero no sustituye al universo completo del resto de la aplicación. Una revisión de búsqueda impide que una respuesta pendiente reabra una paleta cerrada o pinte texto anterior. No se solicitan precios ni se ejecutan acciones financieras desde la paleta.

## Evidencia y límites

- `node --check web/static/app.js`: salida 0.
- `node --test tests/*.test.mjs`: 51 aprobadas, 0 fallidas, 2201.7208 ms; `proveedores-20261101-evidencia/paleta-node-20261101.txt`.
- Dos recorridos Chromium del componente real extraído de app.js (390/1440): sugerencias, selección por flecha, Escape, dos consultas de datos deduplicadas, Enter y navegación a Mesa; sin errores JS. `proveedores-20261101-evidencia/paleta-ui-20261101.json`.
- Los recorridos iniciales usan documento mínimo y respuestas simuladas; por sí solos no acreditan la integración completa.
- Continuación: cuatro recorridos de la **página completa**, servida por FastAPI en 127.0.0.1:8796 con motor, entorno y configuración local desactivados y base aislada. Chromium 390/1440 px en oscuro/claro: sugerencias de Mesa, selección por flecha, Escape conserva texto, comando `/INV` abre Investigación. Sin errores JS, desbordamiento horizontal ni solicitudes distintas de GET. Capturas inspeccionadas y resultados en `proveedores-20261101-evidencia/paleta-completa-ui/`. Los proveedores externos están bloqueados; no verifica sus datos ni disponibilidad. Se detuvo únicamente esta instancia de revisión.
- `git diff --check` de los archivos tocados: salida 0; avisos de conversión LF/CRLF de Git, sin errores de espacios.
- Sin cambios Python/worker; sus resultados anteriores no se presentan como pruebas de esta nueva interfaz.

codebase-memory: skill leída; list_projects y check_index_coverage no disponibles (Transport closed). Se usó fallback de lectura directa de app.js, mesa.mjs, index.html, app.css y navegacion.json. Se conservaron cambios previos.

Sin servidor de ejecución, trades, mensajes externos, commit ni push.

## Corrección posterior: flecha arriba inicial

Se reprodujo un error de índice: con ninguna sugerencia seleccionada y dos o más resultados, ↑ elegía la penúltima. Mesa y principal ahora usan `siguienteSugerencia` del módulo compartido: ↑ inicial elige la última, ↓ inicial la primera y el recorrido envuelve en ambos extremos. La prueba cubre 1, 2 y 8 opciones, lista vacía y tecla ajena.

Verificación posterior: **52 pruebas Node aprobadas**, 1072.778 ms (`proveedores-20261101-evidencia/paleta-flecha-node-20261101.txt`); dos recorridos Chromium del componente real en documento mínimo (390/1440) verifican ↑ inicial con dos destinos, ↓, Escape y navegación. `paleta-ui-20261101.json` se actualizó con este recorrido. No se repitieron los cuatro recorridos de página completa por esta corrección acotada; esos registros corresponden a la versión anterior. La función compartida se usa en ambos manejadores.
