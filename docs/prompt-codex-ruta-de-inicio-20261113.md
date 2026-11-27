# Prompt para Codex — recorrer y validar la ruta de inicio (13-nov-2026)

Copie todo lo que está debajo de la línea en Codex, abierto en la carpeta del repositorio.

---

Trabajas en `actinver-terminal` (https://github.com/Maikolv/actinver-terminal; FastAPI + SQLite + HTML/JS sin
build). Responde y documenta en español, con lenguaje sencillo. Lee primero `CLAUDE.md` y `docs/ruta-de-inicio.md`.

## Objetivo

Seguir **paso a paso** la guía `docs/ruta-de-inicio.md` como lo haría alguien nuevo, desde entrar al repositorio hasta
ver la terminal funcionando. Hazlo en sus tres rutas. Corrige lo que falle y deja la guía exacta y enlazada desde el README.

## Tareas

1. **Ruta A — demo en el navegador.**
   - Abre https://maikolv.github.io/actinver-terminal/ y `estacion.html`.
   - Confirma que cargan sin errores de consola, que el monitor muestra instrumentos y que todo dice «DATOS SIMULADOS».
   - Comprueba que se ve bien a 390 px de ancho.

2. **Ruta C — PC con Windows, desde cero.**
   - Clona en una carpeta temporal **distinta** (por ejemplo `%TEMP%\hqt-prueba`):
     `git clone https://github.com/Maikolv/actinver-terminal.git`.
   - Ejecuta exactamente los comandos de la guía:
     - `uv sync`;
     - `copy .env.example .env`;
     - `.\start.bat demo`, con `--sin-navegador` si lo necesitas para automatizar.
   - Verifica que `http://127.0.0.1:8765/api/estado` responde 200 y que la página principal carga.
   - Si el puerto 8765 está ocupado por la terminal real del usuario, **no la detengas**: usa otro puerto solo para la prueba y documenta cómo.
   - Al terminar, detén tu servidor de prueba y borra la carpeta temporal.

3. **Ruta B — Codespaces.**
   - Solo si `gh auth status` muestra el permiso `codespace`:
     - crea un Codespace en `main`;
     - corre `uv run terminal demo --sin-navegador`;
     - comprueba el puerto 8765 por el reenvío privado;
     - **detén y borra el Codespace**.
   - Si no tienes el permiso, no lo pidas ni lo fuerces. Valida con el workflow `.github/workflows/codespace.yml` (`gh workflow run codespace.yml` y revisa que pase) y deja anotado que la prueba real requiere `gh auth refresh -h github.com -s codespace` del usuario.

4. **Corrige la guía.**
   - Cada comando debe funcionar tal cual en PowerShell 5.1.
   - Cada botón y texto mencionado debe existir (nombres de pestañas, «Actualizar datos», «Mi portafolio», «Plan de acción»).
   - Ajusta tiempos aproximados con lo que midas.
   - Amplía la tabla «Si algo falla» con lo que encuentres.

5. **Enlaza.**
   - En `README.md`, sección «Cómo correr»: enlace visible a `docs/ruta-de-inicio.md` («Guía paso a paso»).
   - En `sitio/index.html`: botón o enlace a la guía en GitHub.

6. **Pruebas y entrega.**
   - Corre `node --test tests/*.test.mjs` y `uv run pytest -q tests/test_seguridad.py`; la suite completa si tocas Python.
   - Agrega una entrada a `CHANGELOG.md` con lo medido.
   - Revisa `git status` antes de commitear: puede haber otra sesión trabajando. Incluye solo tus archivos.
   - Commit y push a `main`.

## Límites (no negociables)

- Sin órdenes ni dinero real, ni siquiera demo.
- No leas ni imprimas `.env` real ni ninguna clave. En la prueba usa solo el `.env` copiado de `.env.example`.
- Servir solo en `127.0.0.1`. No pongas puertos de Codespaces en «Public».
- No toques `data/` de la carpeta real del usuario ni detengas su terminal.
- Solo servicios gratuitos. Si algo pide pago o tarjeta, detente y avisa.
- No renombres carpetas ni repositorios.

## Al terminar

Entrega un informe breve:
- qué rutas probaste y su resultado (con tiempos);
- qué corregiste en la guía;
- commit;
- lo que quedó pendiente y qué necesita el usuario.
