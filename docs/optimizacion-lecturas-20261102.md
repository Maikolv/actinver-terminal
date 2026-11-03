# Optimización de lecturas — 2-nov-2026

El arranque y el compromiso privado del servidor bajaron en la comparación de tres repeticiones. Se evitó cargar los motores matemáticos para consultar información guardada. Las fórmulas, ventanas, semillas, límites, criterios y selección temporal conservan el código revisado; esta entrega no valida rentabilidad ni autoriza operar.

## Resultado medido

| Indicador | Antes: mediana / p95 | Final: mediana / p95 |
|---|---:|---:|
| Arranque HTTP, ms | 15087.16 / 20002.74 | 7053.57 / 8588.24 |
| Primera respuesta Estado desde navegación, ms | 2883.17 / 2956.74 | 3384.09 / 3590.40 |
| Catálogo local utilizable, ms | 1410.18 / 1435.72 | 1262.22 / 1623.70 |
| Recarga tibia de Mesa, ms | 224.72 / 233.71 | 263.85 / 264.62 |
| Estado tras navegación, ms (45 muestras) | 26.49 / 40.71 | 28.54 / 35.81 |
| Universo completo, ms (45 muestras) | 213.88 / 240.36 | 233.79 / 282.38 |
| Primer acceso a Pasado, ms | 2833.15 / 4449.92 | 1697.12 / 3059.65 |
| Primer acceso a Futuro, ms | 655.09 / 742.49 | 642.46 / 837.00 |
| Servidor: memoria privada final, MiB | 213.47 / 213.63 | 122.41 / 123.97 |
| Servidor: pico privado muestreado, MiB | 213.88 / 214.02 | 122.70 / 124.36 |
| Servidor: RSS final, MiB | 88.96 / 124.98 | 122.75 / 145.08 |
| Renderizadores: memoria privada final, MiB | 39.21 / 39.38 | 40.04 / 41.57 |
| Renderizadores: pico privado muestreado, MiB | 45.86 / 46.19 | 46.09 / 48.50 |
| Renderizadores: RSS final, MiB | 82.09 / 87.15 | 90.08 / 91.94 |
| CPU del servidor durante espera, s | 0.38 / 0.39 | 0.33 / 0.39 |
| Tareas de pestaña durante espera, s | 0.55 / 0.75 | 0.52 / 0.65 |
| Solicitudes durante espera | 1.00 / 1.00 | 1.00 / 1.00 |
| Bytes CDP durante espera | 2892.00 / 2892.00 | 2892.00 / 2892.00 |
| Solicitudes de página observadas, incluidas abortadas | 35.00 / 35.00 | 35.00 / 35.00 |
| Bytes CDP de página en recorrido | 135389.00 / 135394.00 | 135394.00 / 135395.00 |
| Duración real de ventana de espera, ms | 60611.34 / 61240.26 | 60613.66 / 60838.46 |

La primera respuesta de Estado empeoró tanto en mediana como en p95. Universo y recarga tibia también empeoraron; el p95 del catálogo y de Futuro no mejoró. El RSS del servidor y de renderizadores aumentó, aunque el compromiso privado del servidor bajó. No se declara reducción de memoria del navegador ni mejora global de todas las consultas. RSS depende de residencia/paginación de Windows y no equivale a memoria privada comprometida.

## Condiciones y límites

- Misma PC: AMD Ryzen 7 3700U, ocho procesadores lógicos, 6323187712 bytes de RAM. Python 3.12.14, Node 24.19.0, Playwright 1.64.1 y Google Chrome for Testing 143.0.7499.4, ya instalados. Sin dependencias nuevas.
- Tres procesos y contextos nuevos por fase; Windows sin purgar caché de disco ni cerrar aplicaciones del usuario. Tres muestras no permiten inferencia estadística fuerte: p95 de tres es el máximo; p95 de endpoints usa 45 observaciones por fase.
- Copia SQLite de 248385536 bytes, SHA256 0469a0ef07b9f0201cadec8fd3e0b7fb8832b7c6b31e9128b1ef875e1236b49b. Cada repetición partió de una copia idéntica. El archivo de origen permaneció intacto. No se compara como si fuera el dataset de la medición del 31-oct, cuya huella era distinta.
- Servidores solo en 127.0.0.1, sin motor, carga de .env o configuración local. Subprocesos con entorno limitado, sin claves heredadas. Conexiones/DNS externos bloqueados; navegador sin perfil personal y solicitudes externas o de modificación bloqueadas. No se crearon cuentas ni se consumieron cuotas de proveedores.
- Antes se cargaron instantáneas de servicios/optimizador/espacios en el proceso aislado, sin revertir el árbol de trabajo. Servicios y optimizador coinciden con las huellas del primer recorrido; las fuentes restantes anteriores se conservan para revisión. Ambas fases usaron el mismo mecanismo de carga para esos tres módulos. Los otros cambios entre fases forman parte del refactor documentado.
- La ventana se programó para 60 s; la lectura de contadores de Windows añade sobrecarga. Se publica la duración real, sin llamarla exactamente 60 s. El pico privado es el máximo muestreado en esa ventana, no el pico absoluto durante todo el arranque. Los renderizadores son los de la única pestaña/contexto de revisión, incluida su cinta global; se excluye la memoria del resto de Chrome del usuario.
- El primer control útil medido es el selector del catálogo local habilitado. No acredita una vela externa lista, dato vigente ni disponibilidad de TradingView/CME. Un HTTP 200 local no acredita la fuente externa. Precios de cierre/retrasados conservan su procedencia; no se presentan como actuales por estas métricas.
- Las 30 solicitudes explícitas a Estado/Universo por repetición y las dos lecturas de Pasado/Futuro se hicieron contra la copia local. No están incluidas en el contador CDP de solicitudes de página. No se guardaron cuerpos de API, información de cuenta o secretos en el informe.

## Qué cambió

Se trasladaron costo_unitario, _clase_costo y clasificar a criterios_propuestas.py; optimizador conserva las dos funciones públicas como reexportaciones. Servicios carga el optimizador dentro del cálculo explícito y usa las funciones ligeras para presentar resultados. La huella de cálculo incluye el archivo nuevo: propuestas guardadas pueden requerir recalcular por versión; no se recalcularon para forzar un resultado favorable.

La consulta ultimo de experimentos pasó a investigacion/lecturas.py y evaluacion conserva su entrada pública. Pronósticos e informes de robustez importan el motor matemático cuando se solicita cálculo, no al leer emisiones, experimentos o estados guardados. No se ejecutó aquí la emisión de señales, un broker ni una estrategia. La carga inicial de dependencias para un cálculo explícito sigue existiendo; la mejora es evitarla al consultar datos.

reorganizacion-ast.json verifica los ocho módulos en un alcance declarado: excluye importaciones, normaliza solo los alias trasladados y la inclusión del fichero en la huella de caché. Las cuatro funciones trasladadas conservan su AST exacto. Esta revisión no sustituye regresión de ejecución; las importaciones pueden tener efectos que una comparación estructural no demuestra.

## Pruebas y fallos conservados

- Regresión final específica: 74 aprobadas, 130.75 s, salida 0. Incluye optimizador, investigación, pronóstico del Reto, robustez y lectura fría por cinco rutas. El proceso frío bloquea red externa y prueba que esas rutas no cargan sklearn/skfolio; después comprueba las entradas públicas del motor.
- Node: 51 aprobadas, cero fallidas, 1427.1121 ms, salida 0. Worker: 19 aprobadas, cero fallidas, 638.2023 ms, salida 0. El aviso de npm sobre una versión nueva no se ejecutó ni motivó instalar nada.
- Suite Python completa de esta versión: 881 aprobadas, cero fallidas, una advertencia de deprecación de Starlette/AnyIO, 569.91 s (9:29), salida 0, en pytest-conjunto-final.txt. Los once archivos del parche y las cinco fuentes principales medidas conservaron sus hashes al terminar. La anterior de Retry-After tuvo 878 aprobadas y se conserva como historia; no se suman selecciones diferentes.
- El primer grupo tuvo 48 aprobadas y un fallo por carga de dependencias en lectura. La variante intermedia redujo arranque pero empeoró Pasado/Futuro; se conserva en despues-controlado-http-memoria.json y se corrigió antes de la medición final.
- Hubo fallos de la prueba aislada por bloquear el socket local interno de Windows y por usar el host virtual testserver. Se corrigió el aislamiento para permitir solo loopback y usar 127.0.0.1. No se eliminó la comprobación de ausencia de motores en lecturas.
- Dos intentos iniciales del instrumento contaban la cinta global como panel de Mesa y se detuvieron por aserción. Se delimitó el control a #mesa-paneles y se mantuvo la cinta en memoria/tráfico. No se contaron como mediciones aprobadas ni como fallos de la interfaz.
- El parche inicial tuvo conversión CRLF de Windows; se escribió en LF y pasó git apply --check --reverse. Este comando fue solo comprobación: no aplicó ni revirtió cambios. Sin commit/push.

## Entregables y reproducción

Parche acotado: cambios-lecturas.patch. Manifiesto con once archivos y SHA256: manifiesto-cambios-lecturas.json. Fuentes anteriores: originales/. Datos y resumen: antes-controlado-http-memoria.json, despues-lecturas-http-memoria.json y comparacion-controlada-final.json. La variante intermedia permanece separada.

Instrumentos propios: servidor_aislado.py y medir_http_memoria.cjs; verificar_reorganizacion.py produce la evidencia estructural. Los originales congelados no son órdenes para ejecutar ni sustituyen las instrucciones humanas vigentes. El grafo codebase-memory y su cobertura devolvieron Transport closed; se usó lectura directa acotada y búsquedas en las rutas implicadas, sin atribuir cobertura al índice.

Los comandos de pruebas fueron uv run --offline --frozen pytest, node --test tests/*.test.mjs y npm --prefix cloud-alerts test, con TERMINAL_SIN_ENV=1, TERMINAL_SIN_CONFIG_LOCAL=1 y TERMINAL_SIN_MOTOR=1; BLAS/OMP/MKL a un hilo. El navegador usó la instalación existente de Playwright/Chromium. El origen SQLite se suministró explícitamente con PERFIL_BASE_SQLITE, nunca con la base habitual.

estado-futuros-lab.json conserva PAPER y los tres candados apagados; sin diario disponible, incidentes no auditados y sin ventaja demostrada. No se iniciaron estrategias, adaptadores de ejecución, órdenes, cuentas, evaluaciones ni avisos Telegram. Las fuentes sin identidad/licencia, historia NQ insuficiente, disponibilidad externa y condición GEX futura conservan sus bloqueos: este informe no los convierte en aprobados.


## Revisión visual complementaria

Cuatro recorridos de la interfaz de costos, 390/1440 px y esquemas de navegador claro/oscuro: tres servicios de pago bloqueados y cero botones de aprobación, sin peticiones externas. Dos capturas (móvil oscuro/escritorio claro) inspeccionadas. Archivos en rendimiento-20261102-evidencia/ui-costos/: resultado.json y cuatro PNG. Se usaron costos sintéticos que incluyen una aprobación histórica ficticia para comprobar que no habilita gasto; el resto de APIs devuelve SIN DATO. El HTML de revisión sustituye los marcadores como el servidor en modo real, con CSRF ficticio y POST bloqueado. No verifica disponibilidad de proveedores, cuentas ni estrategias; no se cambiaron HTML/CSS/JS de producto en este refactor.
