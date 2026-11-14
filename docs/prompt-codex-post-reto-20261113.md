# Prompt para Codex — aplicar la directriz post-Reto (13-nov-2026)

Copie todo lo que está debajo de la línea en Codex, abierto en la carpeta del repositorio.

---

Trabajas en el repositorio `help-quote-terminal` (antes `actinver-terminal`; FastAPI + SQLite + HTML/JS sin build).
Lee primero `CLAUDE.md`, `docs/directriz-post-reto.md` y `docs/resumen-ejecutivo.md`. Responde y documenta en español.

## Ya hecho (no lo repitas)
- Repositorio de GitHub renombrado a `Maikolv/help-quote-terminal`; `origin` actualizado; rama `pre-help-quote` subida.
- Respaldo verificado de `data/` en `data/respaldos/` (13-nov, después de las 15:00).
- Nombre visible «Help Quote Terminal» en interfaz, Telegram, lanzador, scripts, Excel y Worker.
- README, GitHub Pages (`sitio/`), Codespaces (`.devcontainer/`, `docs/codespaces.md`).

## Tu tarea: pasos 2–4 y 6 de `docs/directriz-post-reto.md`
1. **Quita las reglas del Reto** sin borrar funciones:
   - `config/reto.yaml`: `activo: false` y que el código lo respete en un solo lugar (`terminal/reto.py`).
   - Elimina como restricción: mínimo de 5 emisoras, máximo 50 % por emisora, catálogo cerrado del simulador, horario y comisión del Reto, días restantes y etapas.
   - Usa topes configurables propios en `config/ajustes.ejemplo.toml`, por ejemplo `max_peso_emisora = 0.35` y `min_emisoras = 1`.
   - La cartera de referencia pasa a ser la que el usuario registre (importación o captura). La captura del portal queda como una fuente más, con etiqueta «Reto 2026 (archivo)».
2. **Nuevo objetivo, en dos horizontes:**
   - largo plazo: propuestas, Markowitz y Black-Litterman;
   - intradía: `plan_intradia.py`.
   - Siempre contra 1/N y fuera de muestra; si no hay ventaja demostrada, dilo.
3. **Textos:**
   - quita «Reto» de títulos, guías (`web/static/guias.mjs`), Telegram (`mensaje_simple.py`, `bot_telegram.py`) y reportes;
   - renombra el paquete en `pyproject.toml` a `help-quote-terminal`, sin romper el comando `terminal`;
   - renombra `launcher/ActinverTerminal.cs` → `HelpQuoteTerminal.cs`, y el `.ico`, si no rompe el lanzador.
4. **Archiva, no borres:**
   - capturas, transacciones y backtests del Reto se quedan en la base, etiquetados «Reto 2026»;
   - no borres tablas ni filas.
5. **Pruebas:**
   - adapta las que dependan del Reto al nuevo objetivo, sin borrarlas sin reemplazo;
   - deben pasar `uv run pytest -q` (hoy 953), `node --test tests/*.test.mjs` (52) y `npm --prefix cloud-alerts test` (20).
6. **Documenta:**
   - CLAUDE.md: nombre, estado vigente y quita lo del Reto como regla activa;
   - `docs/historial-estado.md` y CHANGELOG, con métricas.

## Límites que NO cambian
- Sin órdenes ni dinero real, ni siquiera demo.
- Secretos solo en `.env`.
- Servir solo en 127.0.0.1 (más la excepción exacta de Codespaces y Tailscale ya existente).
- Datos solo por vía legal y solo proveedores gratuitos.
- Nunca presentar un precio vencido como vigente.
- No bajes la CSP ni el CSRF.
- Revisa `git status` antes de commitear: puede haber otra sesión trabajando.
- Commit y push a `main` solo con la suite en verde.

## Al terminar
Entrega un informe breve:
- qué cambió;
- archivos clave;
- pruebas con su conteo;
- lo que no pudiste completar.
