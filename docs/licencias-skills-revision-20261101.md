# Licencias por skill: corrección del inventario — 1-nov-2026

R31-09 sigue parcial, con una incertidumbre resuelta: `anthropics/skills` no carece de licencias. El inventario anterior solo había considerado archivos en la raíz; el commit fijado `dbd4588f9e1033efb41dad4bef2f7947c8993d44` incluye 18 archivos LICENSE.txt dentro de skills.

Se enumeraron los archivos rastreados mediante git ls-tree y se leyeron sus textos locales. Resultado: **14 Apache-2.0 y 4 propietarias/source-available** (docx, pdf, pptx, xlsx). El README también distingue estos dos grupos. No se interpreta que disponer de una copia conceda permiso para copiar, modificar o redistribuir todo el repositorio bajo MIT.

`config/repositorios-20261031.json` ahora enumera los 18 archivos, clasificación, SHA256 y enlace fijado al commit por cada skill. Evidencia derivada: `proveedores-20261101-evidencia/skills-licencias-20261101.json`. No cambió el remoto ni el commit ni se descargó otra copia.

El verificador existente puede seguir marcando como desconocidas las cuatro licencias propietarias: ese aviso se conserva, pues su clasificador solo reconoce familias de licencias abiertas. No se alteró para producir un resultado verde ni se ejecutaron las skills del clon. La clasificación por archivo no se hereda a versiones instaladas por un plugin con distinta huella.

Los otros límites continúan: taste-skill de senlindesign y andrej-karpathy-skills no contienen archivos de licencia rastreados en los commits inventariados; Caveman instalado tiene una huella distinta de la versión archivada. No se infiere autorización de copia por nombre, popularidad o licencia de otra versión. Sin permiso verificable, quedan como referencias de lectura, no código incorporado.

### Precisión posterior: declaraciones MIT comprobadas

La ausencia de un archivo LICENSE no significa ausencia de declaración. Se leyeron directamente los archivos con `git show` en los commits fijados, sin cambiar clones:

- `senlindesign/taste-skill`, `6dce223f2f5665d3636ca9a44ec3a7aa1322a9b8`: README.md termina con «MIT © 2025 Sen Lin».
- `multica-ai/andrej-karpathy-skills`, `2c606141936f1eeef17fa3043a72095b4765b9c2`: README.md declara MIT y `.claude-plugin/plugin.json` contiene `license: MIT`, autor `forrestchang` y versión 1.0.0.

Los README oficiales públicos también muestran esas declaraciones: [Taste](https://github.com/senlindesign/taste-skill/blob/6dce223f2f5665d3636ca9a44ec3a7aa1322a9b8/README.md) y [Karpathy](https://github.com/multica-ai/andrej-karpathy-skills/blob/2c606141936f1eeef17fa3043a72095b4765b9c2/README.md). Se registra `licencia_declarada: MIT` y se conserva vacía la lista de archivos LICENSE. No se inventa un texto de licencia ni titular para Karpathy, ni se confunde una declaración con un expediente completo de términos y atribución. La política local de referencia sin incorporación sigue vigente. Esto reduce la incertidumbre documental; no resuelve Caveman ni convierte el verificador en aprobado.

La suite completa de Actinver se inició antes de este ajuste de metadatos y continúa en seguimiento. No se publica un resultado hasta observar su salida terminal. Los cambios de esta revisión no afectan código financiero ni habilitan ejecución.

Sin lecturas de .env, compras, cuentas, mensajes externos, commit o push.

Actualización posterior: la repetición completa de Actinver terminó con 858 aprobadas, una advertencia y salida 0; docs/verificacion-conjunto-20261101.md. No convierte licencias o procedencias pendientes en aprobadas.

## Caveman: comparación adicional

Se comparó la instalación del plugin con las dos ubicaciones de Caveman en el clon archivado. No coinciden ni normalizando saltos de línea ni retirando el frontmatter. El plugin declara nombre/versión, pero no URL o commit de procedencia en su plugin.json. Por tanto, no se resuelve el permiso por una supuesta diferencia de empaquetado. La similitud textual es un diagnóstico, no una prueba de autoría o licencia.

Evidencia sin copiar el contenido de la skill: `proveedores-20261101-evidencia/caveman-procedencia-20261101.json`, con hashes y comparación. El LICENSE raíz del clon es Apache-2.0 y contiene además LICENSE-MIT; tampoco basta con encontrar un archivo MIT para atribuírselo a otra versión instalada. No se alteró la skill ni se activó su estilo de respuesta.

Se amplió el cotejo al historial público del repositorio archivado, con 1.888 commits alcanzables desde FETCH_HEAD. Se compararon 128 blobs distintos de SKILL.md con la instalación tras normalizar espacios y saltos de línea. Hubo cero coincidencias. La procedencia de la versión instalada sigue sin verificarse y el recurso permanece como referencia.
