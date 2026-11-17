// Accesibilidad medida (como en COATL): axe-core WCAG 2.1 A/AA en Estación, plan y portafolios, en escritorio
// (1440) y en 375 px vertical y horizontal. Espera <html data-calculo="listo"> (sin esperas fijas).
// Requiere la demo: TERMINAL_MODO=demo TERMINAL_SIN_MOTOR=1 uv run uvicorn terminal.app:app --port 8767
// Uso: npm run e2e   (ORIGEN=http://127.0.0.1:8767  CANAL=msedge)
"use strict";
const { chromium } = require("playwright");
const { AxeBuilder } = require("@axe-core/playwright");

const ORIGEN = process.env.ORIGEN || "http://127.0.0.1:8767";
const VISTAS = ["tab-mercado", "tab-resumen", "tab-portafolios"];
const TAMANOS = [[1440, 900], [375, 812], [812, 375]];

(async () => {
  const b = await chromium.launch({ channel: process.env.CANAL || "msedge", headless: true });
  let total = 0;
  try {
    for (const [w, hgt] of TAMANOS) {
      const c = await b.newContext({ viewport: { width: w, height: hgt } });
      const p = await c.newPage();
      const errores = [];
      p.on("pageerror", (e) => errores.push(e.message));
      for (const vista of VISTAS) {
        await p.goto(`${ORIGEN}/?vista=${vista}`);
        await p.waitForFunction(() => document.documentElement.dataset.calculo === "listo", null, { timeout: 90000 });
        const r = await new AxeBuilder({ page: p }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
          .exclude("iframe").analyze();  // los widgets de TradingView son de terceros
        for (const v of r.violations) {
          total += v.nodes.length;
          console.log(`${w}x${hgt} ${vista} · ${v.id} (${v.impact}) · ${v.nodes.length} nodo(s) · ${v.nodes[0].target.join(" ")}`);
        }
      }
      if (errores.length) { console.log(`errores de página ${w}x${hgt}:`, errores); total += errores.length; }
      await c.close();
    }
  } finally { await b.close(); }
  console.log(`violaciones axe + errores: ${total}`);
  process.exit(total ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
