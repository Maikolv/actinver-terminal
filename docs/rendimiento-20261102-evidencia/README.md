> Actualización posterior: este perfil inicial se conserva como historia anterior al refactor. La entrega final, sus regresiones y 881 pruebas aprobadas están en ../optimizacion-lecturas-20261102.md. PERF31-04/05 ya tienen medición final; consultar el JSON vigente de pendientes.

# Perfil de importaciones y memoria propia — 2-nov-2026

Se ejecutó perfilar_importaciones.py tras terminar la suite completa, con tres procesos Python 3.12.14 nuevos, configuración personal/entorno/motor desactivados, directorio temporal vacío y conexiones socket prohibidas. No se levantó un servidor ni navegador, no se cargaron claves y no se consultaron proveedores. Caché de disco Windows sin purgar; importación instrumentada con -X importtime. No se atribuyen diferencias a una optimización todavía inexistente.

| Medida | Mediana | p95 empírico (máximo de 3) |
|---|---:|---:|
| Importar terminal.app | 9023.36 ms | 11961.18 ms |
| Memoria privada al terminar | 165.43 MiB | 166.00 MiB |
| RSS al terminar | 197.30 MiB | 197.83 MiB |

Repeticiones de importación: 11961.18, 8892.21 y 9023.36 ms. Pico RSS de cada proceso igual al valor final observado. El campo pico_comprometido_bytes procede de PeakPagefileUsage de Windows y no se presenta como pico privado muestreado de un navegador. Con tres muestras, el p95 es descriptivo y débil para inferencia.

En la tercera repetición, las rutas acumuladas principales fueron terminal.espacios 5274.03 ms, terminal.servicios 5253.07 ms y terminal.optimizador 5242.06 ms; sklearn aparece con aproximadamente 2894.48 ms. Los tiempos acumulados se superponen: no deben sumarse. Optimizador define clases que heredan de skfolio/sklearn durante la importación; no basta mover una línea de importación sin revisar clases y primeras consultas.

Siguiente comprobación: arranque HTTP y primera consulta/p95 de estado y universo con la misma copia SQLite y configuración en tres repeticiones; memoria privada y pico muestreado de los procesos de navegador creados para esa revisión. El archivo de medición previo conserva el tamaño 248385536 bytes, pero su SHA256 actual es 0469a0ef07b9f0201cadec8fd3e0b7fb8832b7c6b31e9128b1ef875e1236b49b, distinto del registrado el 31-oct. No usarlo como si fuera la misma línea base histórica ni modificarlo: las repeticiones nuevas deben partir de copias iguales y registrar su huella.

PERF31-04 y PERF31-05 continúan parciales. Esta medición acredita importación y memoria propia, no arranque HTTP, p95 de endpoints, memoria de pestaña ni ahorro antes/después. No se cambiaron servicios.py, espacios.py u optimizador.py ni la estrategia financiera. Evidencia: perfil-importaciones.json e importaciones-1/2/3.txt, con fuente/hash y entorno resumidos.
