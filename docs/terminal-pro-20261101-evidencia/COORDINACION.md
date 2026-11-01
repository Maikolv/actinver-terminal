# Coordinación — terminal profesional y funciones OpenTerminal (1-nov-2026)

**Hecho observado (02:51 CDMX):** otra sesión (formación Python JPMorgan) escribió entre 02:43 y 02:49 archivos nuevos
`terminal/formacion_python.py`, `web/static/recursos/formacion-python-jpm.*`, `web/static/recursos/jpm/`,
`config/formacion-python-jpm.json`, `docs/integracion-python-training-20261101.md`,
`docs/formacion-python-jpm-*`, `tests/test_formacion_python_jpm.py`, y agregó entradas propias en `CHANGELOG.md`,
`CLAUDE.md`, `docs/historial-estado.md`, `web/static/referencias.json` y un enlace en el Cuaderno.

## Reparto
| Archivos | Dueño | Regla |
|---|---|---|
| `formacion_python*`, `formacion-python-jpm*`, `recursos/jpm/`, sus docs y prueba | sesión de formación | Claude no los edita |
| Entradas de formación en CHANGELOG, CLAUDE.md, historial, referencias y el enlace del Cuaderno | sesión de formación | Claude edita con reemplazos puntuales y nunca reescribe esos bloques |
| `app.css`, `navegacion.*`, `mesa.*`, `app.js`, `index.html`, `excel_markowitz.py`, `DESIGN.md` y pruebas nuevas de esta entrega | Claude | La otra sesión no los ha tocado según el diff de línea base |

Línea base: `git-status-inicial.txt`, `hashes-inicial.txt`, `git-diff-inicial.patch` (HEAD en `head.txt`).
Antes de cada escritura en un archivo compartido Claude compara su hash con la línea base.

## Registro
- 01-nov-2026 02:51 · Claude: escribe este documento y la línea base. Revisión en 127.0.0.1 con `TERMINAL_SIN_MOTOR=1`.
