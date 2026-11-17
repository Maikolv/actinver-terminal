// Exporta la terminal completa en MODO DEMO (datos simulados) a sitio/terminal/ para GitHub Pages.
// Recorre todas las pestañas con un navegador, graba cada respuesta GET de la API y copia la interfaz con rutas
// reescritas. Nunca usar con la base real: verifica que /api/estado diga modo demo y aborta si no.
//   1) TERMINAL_MODO=demo TERMINAL_SIN_MOTOR=1 uv run uvicorn terminal.app:app --host 127.0.0.1 --port 8767
//   2) npm run estatico            (ORIGEN=http://127.0.0.1:8767  PREFIJO=/help-quote-terminal/terminal/)
"use strict";
const { chromium } = require("playwright");
const fs = require("node:fs"), path = require("node:path");

const RAIZ = path.resolve(__dirname, "..");
const ORIGEN = process.env.ORIGEN || "http://127.0.0.1:8767";
const PREFIJO = process.env.PREFIJO || "/help-quote-terminal/terminal/";
const SALIDA = path.join(RAIZ, "sitio", "terminal");
const hash = (s) => { let h = 0x811c9dc5; for (const c of Buffer.from(s, "utf8")) { h ^= c; h = Math.imul(h, 0x01000193) >>> 0; } return h.toString(16).padStart(8, "0"); };

function reescribir(texto) {
  return texto
    .replace(/(["'`(])\/static\//g, `$1${PREFIJO}static/`)
    .replace(/(["'`])\/widget\/([a-z-]+)\?/g, `$1${PREFIJO}widget/$2.html?`)
    .replace(/(["'`])\/widget\//g, `$1${PREFIJO}widget/`)
    .replace(/(["'`])\/\?vista=/g, `$1${PREFIJO}?vista=`)
    .replace(/href="\/"/g, `href="${PREFIJO}"`);
}
const conShim = (html) => reescribir(html).replace(/<head>/i, `<head>\n<script src="${PREFIJO}static/estatico.js"></script>`);

(async () => {
  const estado = await (await fetch(`${ORIGEN}/api/estado`)).json();
  if (estado.modo !== "demo") throw new Error(`El servidor no está en modo demo (modo=${estado.modo}): no se exportan datos reales.`);
  fs.rmSync(SALIDA, { recursive: true, force: true });
  fs.mkdirSync(path.join(SALIDA, "api"), { recursive: true });
  const grabadas = new Map();
  const guardar = (clave, cuerpo) => { if (!grabadas.has(clave)) grabadas.set(clave, cuerpo); };

  const b = await chromium.launch({ channel: process.env.CANAL || "msedge", headless: true });
  const c = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const p = await c.newPage();
  p.on("response", async (r) => {
    const u = new URL(r.url());
    if (u.origin !== ORIGEN || r.request().method() !== "GET" || !u.pathname.startsWith("/api/") || r.status() !== 200) return;
    if (!(r.headers()["content-type"] || "").includes("json")) return;
    try { const t = await r.text(); guardar(u.pathname + u.search, t); guardar(u.pathname, t); } catch { /* respuesta cancelada */ }
  });
  await p.goto(`${ORIGEN}/`);
  const tabs = await p.$$eval("#lista-pestanas [role=tab]", (xs) => xs.map((x) => x.id));
  for (const id of tabs) {
    try {
      await p.goto(`${ORIGEN}/?vista=${id}`, { timeout: 60000 });
      await p.waitForFunction(() => document.documentElement.dataset.calculo === "listo", null, { timeout: 60000 });
    } catch (e) { console.warn(`\n${id}: ${e.message.split("\n")[0]} (se conserva lo grabado)`); }
    process.stdout.write(`${id} `);
  }
  // Estación y ficha: la serie de los instrumentos del monitor para que seleccionar cualquiera funcione.
  const mapa = JSON.parse(grabadas.get("/api/visualizaciones/mercado?ventana=1") || '{"celdas":[]}');
  for (const celda of mapa.celdas) {
    const q = `/api/ficha-tecnica?simbolo=${encodeURIComponent(celda.id)}&flujo=false`;
    const r = await fetch(ORIGEN + q);
    if (r.ok) guardar(q, await r.text());
  }
  for (const pagina of ["/static/mesa.html"]) await p.goto(ORIGEN + pagina).then(() => p.waitForLoadState("networkidle").catch(() => {}));
  await b.close();

  for (const [clave, cuerpo] of grabadas) fs.writeFileSync(path.join(SALIDA, "api", `${hash(clave)}.json`), cuerpo);
  fs.writeFileSync(path.join(SALIDA, "api", "indice.json"), JSON.stringify([...grabadas.keys()].map(hash)));
  // Interfaz: HTML que entrega el servidor (con su token, inútil sin servidor) y archivos estáticos reescritos.
  fs.writeFileSync(path.join(SALIDA, "index.html"), conShim(await (await fetch(`${ORIGEN}/`)).text()));
  const copiar = (origen, destino) => {
    for (const e of fs.readdirSync(origen, { withFileTypes: true })) {
      const o = path.join(origen, e.name), d = path.join(destino, e.name);
      if (e.isDirectory()) { fs.mkdirSync(d, { recursive: true }); copiar(o, d); continue; }
      if (/\.(js|mjs|css|json|html)$/.test(e.name)) {
        const t = fs.readFileSync(o, "utf8");
        fs.writeFileSync(d, e.name.endsWith(".html") ? conShim(t) : reescribir(t));
      } else fs.copyFileSync(o, d);
    }
  };
  fs.mkdirSync(path.join(SALIDA, "static"), { recursive: true });
  copiar(path.join(RAIZ, "web", "static"), path.join(SALIDA, "static"));
  fs.writeFileSync(path.join(SALIDA, "static", "mesa.html"), conShim(await (await fetch(`${ORIGEN}/static/mesa.html`)).text()));
  fs.mkdirSync(path.join(SALIDA, "widget"), { recursive: true });
  for (const w of ["cinta-macro", "mapa"]) {
    const r = await fetch(`${ORIGEN}/widget/${w}?tema=dark`);
    if (r.ok) fs.writeFileSync(path.join(SALIDA, "widget", `${w}.html`), reescribir(await r.text()));
  }
  console.log(`\n${grabadas.size} respuestas grabadas en ${path.relative(RAIZ, SALIDA)}`);
})().catch((e) => { console.error(e); process.exit(1); });
