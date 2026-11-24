// Capturas de la DEMO PÚBLICA (datos simulados) para el video del concurso. Nunca usa la cuenta real.
//   node scripts/capturas_video.cjs   → data/medios/video/capturas/*.png
"use strict";
const { chromium } = require("playwright");
const fs = require("node:fs"), path = require("node:path");
const ORIGEN = process.env.ORIGEN || "https://maikolv.github.io/help-quote-terminal/terminal/";
const DIR = path.resolve(__dirname, "..", "data", "medios", "video", "capturas");
const VISTAS = ["resumen", "ayuda", "legal", "portafolios", "propuestas", "mercado", "tiempo", "intradia", "ficha",
  "investigacion", "riesgo", "robustez", "modelos", "cartera", "seguimiento"];
(async () => {
  fs.mkdirSync(DIR, { recursive: true });
  const b = await chromium.launch({ channel: process.env.CANAL || "msedge", headless: true });
  const c = await b.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1.2, colorScheme: "dark" });
  const p = await c.newPage();
  for (const v of VISTAS) {
    await p.goto(`${ORIGEN}?vista=tab-${v}`, { waitUntil: "networkidle" }).catch(() => {});
    await p.waitForFunction(() => document.documentElement.dataset.calculo === "listo", null, { timeout: 45000 }).catch(() => {});
    await p.waitForTimeout(2500);
    // Cierra las guías desplegadas y lleva el panel activo al inicio de la pantalla.
    await p.evaluate((id) => {
      document.querySelectorAll("details[open]").forEach((d) => { d.open = false; });
      const el = document.getElementById(id);
      if (el) window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 8);
    }, `tab-${v}`);
    await p.waitForTimeout(800);
    await p.screenshot({ path: path.join(DIR, `${v}.png`) });
    console.log(v);
  }
  await b.close();
})().catch((e) => { console.error(e); process.exit(1); });
