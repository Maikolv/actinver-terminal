// Exporta la terminal completa en MODO DEMO (datos simulados) a sitio/terminal/ para GitHub Pages.
// Recorre todas las pestañas con un navegador, graba cada respuesta GET de la API y copia la interfaz con rutas
// reescritas. Nunca usar con la base real: verifica que /api/estado diga modo demo y aborta si no.
//   1) TERMINAL_MODO=demo TERMINAL_SIN_MOTOR=1 uv run uvicorn terminal.app:app --host 127.0.0.1 --port 8767
//   2) npm run estatico            (ORIGEN=http://127.0.0.1:8767  PREFIJO=/actinver-terminal/terminal/)
// Además de las lecturas, graba los cálculos sin efectos fuera de la base demo (simulación, generador de Mis portafolios,
// backtest, Heston) para las combinaciones que se recorren aquí; el shim los sirve con la misma clave método+ruta+cuerpo.
"use strict";
const { chromium } = require("playwright");
const fs = require("node:fs"), path = require("node:path");

const RAIZ = path.resolve(__dirname, "..");
const ORIGEN = process.env.ORIGEN || "http://127.0.0.1:8767";
const PREFIJO = process.env.PREFIJO || "/actinver-terminal/terminal/";
const SALIDA = path.join(RAIZ, "sitio", "terminal");
// Cálculos que se graban: deben coincidir con CALCULOS de web/static/estatico.js.
const CALCULOS = ["/api/simular", "/api/portafolios/generar", "/api/backtests", "/api/flujo/heston", "/api/asistente"];
// Preguntas de ejemplo que el Asistente (motor local, sin red) responde en la demo estática.
const PREGUNTAS = ["¿Qué significa VaR?", "¿Qué es CVaR?", "¿Qué es el ratio de Sharpe?", "¿Cómo funciona Markowitz?", "¿Qué es la frontera eficiente?", "¿Qué hace esta terminal?", "¿Qué es el Order Flow?", "¿Qué es el GEX?", "¿Qué es el backtesting?", "¿De dónde salen los datos?"];
const hash = (s) => { let h = 0x811c9dc5; for (const c of Buffer.from(s, "utf8")) { h ^= c; h = Math.imul(h, 0x01000193) >>> 0; } return h.toString(16).padStart(8, "0"); };

function reescribir(texto) {
  return texto
    .replace(/(["'`(])\/static\//g, `$1${PREFIJO}static/`)
    .replace(/(["'`])\/widget\/([a-z-]+)\?/g, `$1${PREFIJO}widget/$2.html?`)
    .replace(/(["'`])\/widget\//g, `$1${PREFIJO}widget/`)
    .replace(/(["'`])\/\?vista=/g, `$1${PREFIJO}?vista=`)
    .replace(/href="\/"/g, `href="${PREFIJO}"`);
}
// El token CSRF del servidor demo no sirve sin servidor: se reemplaza para no publicarlo ni cambiar el sitio en cada exportación.
const conShim = (html) => reescribir(html).replace(/<meta name="csrf" content="[^"]*">/, '<meta name="csrf" content="estatico">').replace(/<head>/i, `<head>\n<script src="${PREFIJO}static/estatico.js"></script>`);

// Recorre los cálculos interactivos tal como los haría un visitante que acaba de abrir la página.
async function interacciones(p, grabarCalculo) {
  const listo = () => p.waitForFunction(() => document.documentElement.dataset.calculo === "listo", null, { timeout: 120000 }).catch(() => {});
  const abrir = async (id) => { await p.goto(`${ORIGEN}/?vista=${id}`, { timeout: 60000 }); await listo(); };
  // Ejecuta la acción, espera la respuesta del cálculo y la graba antes de seguir (navegar descarta el cuerpo).
  const tras = async (ruta, accion) => {
    const [r] = await Promise.all([p.waitForResponse((x) => x.url().includes(ruta) && x.request().method() === "POST", { timeout: 120000 }).catch(() => null), accion()]);
    if (r) await grabarCalculo(r).catch(() => {});
  };
  let n = 0;
  // Mis portafolios: cada perfil y cada clase, desde el estado inicial (perfil→clase y clase→perfil).
  await abrir("tab-portafolios");
  const perfiles = await p.locator("[aria-label=Perfil] [role=radio]").count();
  const clases = await p.locator(".pf-generador label:has-text('Clase') select option").evaluateAll((xs) => xs.map((x) => x.value));
  const clase = (v) => p.locator(".pf-generador label:has-text('Clase') select").first().selectOption(v);
  const perfil = (i) => p.locator("[aria-label=Perfil] [role=radio]").nth(i).click();
  for (let i = 0; i < perfiles; i++) for (const c of clases) {
    for (const orden of [0, 1]) {
      await abrir("tab-portafolios"); await p.waitForTimeout(800);
      if (orden) { await tras("/api/portafolios/generar", () => clase(c)); await tras("/api/portafolios/generar", () => perfil(i)); }
      else { await tras("/api/portafolios/generar", () => perfil(i)); await tras("/api/portafolios/generar", () => clase(c)); }
      n++;
    }
  }
  process.stdout.write(`
portafolios: ${n} recorridos `);
  // Simulaciones de cambios: cada universo × lente (× mercado, si aplica) de Propuestas, y las de Resumen/Alertas.
  const simularVisibles = async () => {
    const botones = p.locator("button:has-text('Simular')");
    for (let i = 0, k = await botones.count(); i < k; i++) {
      const b = botones.nth(i);
      if (!(await b.isVisible())) continue;
      await tras("/api/simular", () => b.click()); await p.keyboard.press("Escape"); n++;
    }
  };
  for (const id of ["tab-resumen", "tab-alertas"]) { await abrir(id); await simularVisibles(); }
  await abrir("tab-propuestas");
  const seg = (s) => p.locator(`#${s} button`);
  for (let u = 0, nu = await seg("selector-universo").count(); u < nu; u++) {
    await seg("selector-universo").nth(u).click();
    for (let l = 0, nl = await seg("selector-lente").count(); l < nl; l++) {
      await seg("selector-lente").nth(l).click(); await p.waitForTimeout(300);
      const merc = p.locator("#selector-mercado-propuesta:not([hidden]) button");
      const nm = await merc.count();
      if (!nm) await simularVisibles();
      for (let m = 0; m < nm; m++) { await merc.nth(m).click(); await p.waitForTimeout(300); await simularVisibles(); }
    }
  }
  // Backtesting: cada estrategia con sus parámetros predeterminados.
  await abrir("tab-backtesting");
  const sel = () => p.locator("#backtesting-contenido label:has-text('Estrategia') select").first();
  const estrategias = await sel().locator("option").evaluateAll((xs) => xs.map((x) => x.value)).catch(() => []);
  const calcular = () => tras("/api/backtests", () => p.locator("button:has-text('Calcular backtest')").first().click());
  await calcular(); n++;  // estado inicial, tal como abre la pestaña
  for (const e of estrategias) {
    await abrir("tab-backtesting");
    await sel().selectOption(e); await listo();
    await tras("/api/backtests", () => p.locator("button:has-text('Calcular backtest')").first().click()); n++;
  }
  // Heston, si la ficha del instrumento tiene cadena de opciones en la base demo.
  await abrir("tab-ficha");
  const of = p.locator("button:has-text('Option Flow')").first();
  if (await of.count()) { await of.click(); await listo(); }
  const hb = p.locator("button:has-text('Calibrar modelo de Heston')").first();
  if (await hb.count()) { await tras("/api/flujo/heston", () => hb.click()); n++; }
  await abrir("tab-asistente");
  for (const q of PREGUNTAS) {
    await p.fill("#asistente-texto", q);
    await tras("/api/asistente", () => p.locator("#form-asistente button[type=submit]").click()); n++;
  }
  // Botones rápidos de solo lectura (/plan, /estado, /notas…); /nota escribe y no se graba.
  const rapidos = p.locator("button[data-pregunta]");
  for (let i = 0, k = await rapidos.count(); i < k; i++) {
    if (/^\/nota\s/.test(await rapidos.nth(i).getAttribute("data-pregunta"))) continue;
    await tras("/api/asistente", () => rapidos.nth(i).click()); n++;
  }
  process.stdout.write(`interacciones: ${n}
`);
}

(async () => {
  const estado = await (await fetch(`${ORIGEN}/api/estado`)).json();
  if (estado.modo !== "demo") throw new Error(`El servidor no está en modo demo (modo=${estado.modo}): no se exportan datos reales.`);
  // Vacía la salida sin borrar las carpetas mismas (en Windows una carpeta abierta por otro proceso no se puede borrar).
  const vaciar = (d) => { if (!fs.existsSync(d)) return; for (const e of fs.readdirSync(d, { withFileTypes: true })) { const r = path.join(d, e.name); if (e.isDirectory()) { vaciar(r); try { fs.rmdirSync(r); } catch { /* en uso */ } } else fs.rmSync(r, { force: true }); } };
  vaciar(SALIDA);
  fs.mkdirSync(path.join(SALIDA, "api"), { recursive: true });
  const grabadas = new Map();
  const guardar = (clave, cuerpo) => { if (!grabadas.has(clave)) grabadas.set(clave, cuerpo); };

  // Un cálculo rechazado (p. ej. 422) se graba con su código para mostrar el mismo error.
  const grabarCalculo = async (r) => {
    const u = new URL(r.url()), t = await r.text();
    guardar(`POST ${u.pathname}${u.search}
${r.request().postData() || ""}`, r.status() === 200 ? t : JSON.stringify({ __estado: r.status(), cuerpo: JSON.parse(t) }));
  };
  const b = await chromium.launch({ channel: process.env.CANAL || "msedge", headless: true });
  const c = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const p = await c.newPage();
  p.on("response", async (r) => {
    const u = new URL(r.url()), metodo = r.request().method();
    const calculo = metodo === "POST" && CALCULOS.includes(u.pathname);
    if (u.origin !== ORIGEN || !u.pathname.startsWith("/api/") || (r.status() !== 200 && !calculo)) return;
    if (!(r.headers()["content-type"] || "").includes("json")) return;
    try {
      if (metodo === "GET") { const t = await r.text(); guardar(u.pathname + u.search, t); guardar(u.pathname, t); }
      else if (calculo) await grabarCalculo(r);
    } catch { /* respuesta cancelada */ }
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
  await interacciones(p, grabarCalculo);
  for (const pagina of ["/static/mesa.html"]) await p.goto(ORIGEN + pagina).then(() => p.waitForLoadState("networkidle").catch(() => {}));
  await b.close();

  for (const [clave, cuerpo] of grabadas) fs.writeFileSync(path.join(SALIDA, "api", `${hash(clave)}.json`), cuerpo);
  fs.writeFileSync(path.join(SALIDA, "api", "preguntas.json"), JSON.stringify(PREGUNTAS));
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
