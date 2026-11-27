// Audita la versión estática (sitio/) como la serviría GitHub Pages: recorre cada pestaña y lista las consultas a la
// API que no tienen respuesta grabada (503 del shim) y los errores de consola. No usa red salvo CDNs.
//   node scripts/auditar_estatico.cjs
"use strict";
const { chromium } = require("playwright");
const fs = require("node:fs"), path = require("node:path");
const RAIZ = path.resolve(__dirname, "..");
const SITIO = path.join(RAIZ, "sitio");
const BASE = "https://demo.local/actinver-terminal/";
const TIPOS = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".pdf": "application/pdf", ".csv": "text/csv", ".zip": "application/zip" };

(async () => {
  const b = await chromium.launch({ channel: process.env.CANAL || "msedge", headless: true });
  const c = await b.newContext({ viewport: { width: 1440, height: 900 } });
  await c.route("https://demo.local/**", (r) => {
    let rel = decodeURIComponent(new URL(r.request().url()).pathname.replace(/^\/actinver-terminal\//, ""));
    let f = path.join(SITIO, rel);
    if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, "index.html");
    if (!fs.existsSync(f)) return r.fulfill({ status: 404, body: "no" });
    r.fulfill({ status: 200, contentType: TIPOS[path.extname(f)] || "application/octet-stream", body: fs.readFileSync(f) });
  });
  const p = await c.newPage();
  let faltan = [], errores = [];
  p.on("response", async (r) => { if (r.status() === 503 && r.url().includes("/api/")) faltan.push(new URL(r.url()).pathname + new URL(r.url()).search); });
  p.on("console", (m) => { if (m.type() === "error") errores.push(m.text().slice(0, 160)); });
  p.on("pageerror", (e) => errores.push("EXC " + e.message.slice(0, 160)));
  await p.goto(BASE + "terminal/");
  const tabs = await p.$$eval("#lista-pestanas [role=tab]", (xs) => xs.map((x) => x.id));
  const informe = {};
  const extra = (process.env.PAGINAS || "static/mesa.html,static/recursos/oficina-inversion.html").split(",");
  for (const id of [...tabs, ...extra]) {
    faltan = []; errores = [];
    const url = id.startsWith("tab-") ? `${BASE}terminal/?vista=${id}` : `${BASE}terminal/${id}`;
    await p.goto(url).catch(() => {});
    await p.waitForTimeout(Number(process.env.ESPERA || 6000));
    const cajas = await p.$$eval(".error, .aviso-error, [role=alert]", (xs) => xs.filter((x) => x.offsetParent && x.textContent.trim()).map((x) => x.textContent.trim().slice(0, 120))).catch(() => []);
    informe[id] = { faltan: [...new Set(faltan)], errores: [...new Set(errores)], cajas };
    console.log(id, "faltan", informe[id].faltan.length, "errores", informe[id].errores.length, "cajas", cajas.length);
  }
  fs.writeFileSync(process.env.SALIDA || path.join(require("node:os").tmpdir(), "auditoria-estatico.json"), JSON.stringify(informe, null, 1));
  await b.close();
})().catch((e) => { console.error(e); process.exit(1); });
