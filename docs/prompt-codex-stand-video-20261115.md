# Prompt para Codex — video con pantalla real, recorrido sin espacios en blanco y materiales del stand (15-nov-2026)

Copie lo que está debajo de la línea en Codex, abierto en la carpeta del repositorio.

---

Trabajas en `help-quote-terminal` (FastAPI + SQLite + HTML/JS sin build). Responde en español. Lee `CLAUDE.md`,
`docs/propuesta-stand.md`, `docs/reporte-ejecutivo/reporte-ejecutivo.html` y `scripts/video_terminal.py`.
Revisa `git status` antes de commitear: Claude puede estar trabajando en paralelo; incluye solo tus archivos.

## Tareas

1. **Recorrido sin espacios en blanco.**
   - Arranca la demo en un puerto libre: `TERMINAL_MODO=demo TERMINAL_SIN_MOTOR=1 uv run uvicorn terminal.app:app --host 127.0.0.1 --port 8767`.
   - Entra a cada una de las 23 pestañas (`/?vista=tab-...`) a 1440, 1024 y 390 px.
   - Mide si queda una zona vacía de más de 200 px:
     - columnas de distinta altura dentro de un mismo panel;
     - un panel sin contenido mientras carga;
     - huecos al final de una cuadrícula.
   - Corrige con CSS existente (`web/static/app.css`): igualar alturas, «Cargando…» en lugar de vacío, `grid-auto-flow: dense`.
   - Ya corregido: la Estación de Mercado en escritorio (columnas de igual altura).
   - Deja `docs/auditoria-espacios-20261115.md` con el antes y el después por pestaña.
2. **Video con la pantalla real.**
   - Amplía `scripts/video_terminal.py` (o crea `scripts/video_recorrido.py` con Playwright) para grabar un recorrido real de la demo:
     - buscar un símbolo;
     - seleccionar;
     - cambiar el intervalo;
     - abrir «Mis portafolios» y marcar un portafolio como principal;
     - ver el plan.
   - Narración con la voz de Windows «Microsoft Sabina Desktop», como ya hace el script.
   - Salida: `docs/video/help-quote-terminal-recorrido.mp4`, de 2–3 min, 1920×1080.
   - Solo datos simulados.
3. **Materiales del stand.** Archivos listos para imprenta en `docs/stand/`:
   - lona de 3 × 2 m;
   - roll-up de 85 × 200 cm;
   - tríptico carta;
   - tarjeta 9 × 5 cm.
   - Formato: HTML/SVG con medidas reales a 150 dpi, más PDF exportado con Edge (`--print-to-pdf`).
   - Identidad: negro/grafito, rojo `#b3261e`, tipografía sans y el logo `web/static/favicon.svg`.
   - Contenido: el de `docs/propuesta-stand.md`, con QR a https://maikolv.github.io/help-quote-terminal/. Genera el QR con una librería ya instalada o en SVG; no agregues dependencias pesadas.
4. **Reporte ejecutivo.** Revisa `docs/reporte-ejecutivo/reporte-ejecutivo.pdf`:
   - que no queden tablas cortadas entre páginas;
   - que las imágenes se vean.
   - Si algo falla, corrige el HTML y vuelve a exportar.

## Límites

- Sin órdenes ni dinero real.
- No leas ni imprimas `.env`.
- Solo `127.0.0.1`.
- Solo recursos gratuitos.
- No muestres datos de la cuenta real del usuario (usa la demo).
- No borres datos.

## Al terminar

- Corre `node --test tests/*.test.mjs` y las pruebas de Python que toques.
- Commit y push a `main`.
- Entrega un informe breve: qué cambió, archivos y lo pendiente.
