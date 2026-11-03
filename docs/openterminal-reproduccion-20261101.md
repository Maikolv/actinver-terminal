# OpenTerminal: reproducción local — 1-nov-2026

Pendiente R31-20: se diferencia el estado actual comprobado de las afirmaciones históricas del 31-oct. Esta revisión no instala ni inicia OpenTerminal dentro de Actinver.

## Identidad y condiciones

- Clon existente: `C:\Users\MIKE\Desktop\Repos\OpenTerminal`.
- Remoto inventariado: `https://github.com/ErTasselli/OpenTerminal.git`.
- Commit actual: `aed097c680cd8ec1c391ae06966babe7d6d91fc6`, coincide con el inventario.
- Árbol limpio antes y después de las pruebas; dependencias ya instaladas. No se ejecutó npm ci ni instalación alguna.
- Node v24.19.0, npm 11.17.0; Windows, fecha local 1-nov-2026.
- `gh api --silent user/starred/ErTasselli/OpenTerminal`: salida 0 (estrella presente). No se añadió de nuevo. La revisión anterior de 37 repositorios consta en `proveedores-20261101-evidencia/repos-estrellas-20261101.json`.

## Pruebas reproducidas

`npm --offline --ignore-scripts test`: **26 aprobadas en 8 archivos**, salida 0, Vitest 2.1.9, duración 10.51 s. Incluye caché, concurrencia, límite, SQLite temporal y proveedores con respuestas simuladas. Evidencia íntegra: `proveedores-20261101-evidencia/openterminal-pruebas-20261101.txt`.

Los casos de transacciones pertenecen a SQLite temporal del upstream: no se conecta un broker ni se envían órdenes. Sus pruebas no convierten los proveedores públicos no documentados del upstream en APIs autorizadas para Actinver, ni prueban datos vigentes.

La cifra histórica «13 pruebas» no se reescribe como si fuera la cifra actual. Esta ejecución encontró 26. La verificación de estrellas actuales tampoco prueba quién las añadió históricamente o cuántas acciones ocurrieron el 31-oct.

## Compilación

Se ejecutó `npm --offline --ignore-scripts run build`, con telemetría Next desactivada y un preload de prueba que bloquea fetch y conexiones TCP externas. No hay archivos .env en raíz, server o web según enumeración de nombres; no se leyeron valores. El preload reside en el directorio temporal de trabajo, no modifica el upstream ni configura hooks globales. No se ejecuta `start` ni `dev`.

Registro de compilación: `proveedores-20261101-evidencia/openterminal-build-20261101.txt`. El resultado terminal se registra al finalizar el proceso; un mensaje intermedio de compilación correcta no acredita la generación completa.

**Resultado final:** el proceso terminó con salida 0 después de generar 4/4 páginas, finalizar optimización y recoger trazas. El registro incluye la tabla final de rutas. Se verificaron los artefactos `server/dist/index.js`, `web/.next/BUILD_ID` y el servidor standalone generado; el árbol Git continúa limpio. No se inició ninguno de esos artefactos. La compilación web declara 105 kB para la primera carga de la página raíz; es una cifra del paquete de OpenTerminal, no una medición de rendimiento o consumo de Actinver.

Exploración estructural: codebase-memory list_projects y check_index_coverage devolvieron Transport closed. Fallback directo en los package.json, pruebas y layout/config de Next del alcance; no se afirma cobertura completa de su código.

Sin copia de código, modificaciones de licencia, estrategias, cuentas, compras, Telegram, commit ni push.
