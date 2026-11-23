// Capturas de la DEMO (datos simulados) para README, Pages, informe y video. No usa la base real.
//   TERMINAL_MODO=demo TERMINAL_SIN_MOTOR=1 uv run uvicorn terminal.app:app --port 8767 ; node scripts/capturas_demo.cjs
"use strict";
const { chromium } = require("playwright");
const path = require("node:path");
const ORIGEN = process.env.ORIGEN || "http://127.0.0.1:8767";
const DIR = path.resolve(__dirname, "..", "docs", "capturas");
const listo = (p) => p.waitForFunction(() => document.documentElement.dataset.calculo === "listo", null, { timeout: 120000 });
(async () => {
  const estado = await (await fetch(`${ORIGEN}/api/estado`)).json();
  if (estado.modo !== "demo") throw new Error("Solo con la demo (datos simulados).");
  const b = await chromium.launch({ channel: process.env.CANAL || "msedge", headless: true });
  const c = await b.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: "dark" });
  const p = await c.newPage();
  for (const [vista, archivo] of [["tab-resumen", "inicio.png"], ["tab-propuestas", "propuestas.png"], ["tab-portafolios", "portafolios.png"],
    ["tab-riesgo", "riesgo.png"], ["tab-ranking", "ranking.png"], ["tab-mercado", "mercado.png"]]) {
    await p.goto(`${ORIGEN}/?vista=${vista}`); await listo(p);
    await p.screenshot({ path: path.join(DIR, archivo) });
  }
  await p.goto(`${ORIGEN}/?vista=tab-mercado`); await listo(p);
  await p.locator("#estacion").scrollIntoViewIfNeeded();
  await p.locator("#estacion").screenshot({ path: path.join(DIR, "mercado-despues-demo-1440.jpg"), quality: 88 });
  const claro = await b.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: "light" });
  const pc = await claro.newPage(); await pc.goto(`${ORIGEN}/?vista=tab-mercado`); await listo(pc);
  await pc.locator("#estacion").screenshot({ path: path.join(DIR, "mercado-despues-demo-claro-1440.jpg"), quality: 88 });
  const movil = await b.newContext({ viewport: { width: 375, height: 812 }, deviceScaleFactor: 2, colorScheme: "dark" });
  const pm = await movil.newPage(); await pm.goto(`${ORIGEN}/?vista=tab-mercado`); await listo(pm);
  await pm.locator("#estacion").scrollIntoViewIfNeeded();
  await pm.screenshot({ path: path.join(DIR, "estacion-movil.jpg"), quality: 88 });
  await b.close();
  console.log("capturas listas en docs/capturas");
})().catch((e) => { console.error(e); process.exit(1); });
