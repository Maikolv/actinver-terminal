// Grabaciones en video de la DEMO PÚBLICA (datos simulados) para el video del concurso. Nunca usa la cuenta real.
//   node scripts/grabar_terminal.cjs [nombre…]   → data/medios/video/grabaciones/<nombre>.webm
"use strict";
const { chromium } = require("playwright");
const fs = require("node:fs"), path = require("node:path");
const ORIGEN = process.env.ORIGEN || "https://maikolv.github.io/help-quote-terminal/";
const DIR = path.resolve(__dirname, "..", "data", "medios", "video", "grabaciones");
// Mismo tamaño que la ventana del video (1060×770): se usa 1:1, sin recorte ni escala.
const W = 1060, H = 770;

const pausa = (p, ms) => p.waitForTimeout(ms);
async function desplazar(p, total, pasos = 40, ms = 60) {  // desplazamiento suave, como una persona con la rueda
  for (let i = 0; i < pasos; i++) { await p.mouse.wheel(0, total / pasos); await pausa(p, ms); }
}
async function vista(p, tab) {
  await p.goto(`${ORIGEN}terminal/?vista=tab-${tab}`, { waitUntil: "networkidle" }).catch(() => {});
  await p.waitForFunction(() => document.documentElement.dataset.calculo === "listo", null, { timeout: 45000 }).catch(() => {});
  await p.evaluate((id) => {
    document.querySelectorAll("details[open]").forEach((d) => { d.open = false; });
    const el = document.getElementById(id);
    if (el) window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 8 });
  }, `tab-${tab}`);
  await pausa(p, 900);
  if (p._marca == null) p._marca = (Date.now() - p._t0) / 1000;  // segundo en que la vista ya está lista
}
// Cada escena: lo que se hace frente a la cámara (12–20 s).
const ESCENAS = {
  inicio: async (p) => { await p.goto(ORIGEN, { waitUntil: "networkidle" }); await pausa(p, 1500); p._marca = (Date.now() - p._t0) / 1000; await pausa(p, 1000); await desplazar(p, 1400, 60, 90); await pausa(p, 1500); },
  plan: async (p) => { await vista(p, "resumen"); await pausa(p, 1500); await desplazar(p, 900, 50, 90); await pausa(p, 1500); },
  legal: async (p) => { await vista(p, "legal"); await pausa(p, 1200); await desplazar(p, 1100, 60, 90); await pausa(p, 1000); },
  portafolios: async (p) => {
    await vista(p, "portafolios"); await pausa(p, 1200);
    for (const t of ["Agresivo", "Crecimiento", "Agresivo"]) { await p.getByText(t, { exact: true }).first().click({ timeout: 2000 }).catch(() => {}); await pausa(p, 1300); }
    await desplazar(p, 900, 50, 90); await pausa(p, 1200);
  },
  mercado: async (p) => {
    await vista(p, "mercado"); await pausa(p, 1200);
    // Sin clics en otras emisoras: en la demo estática solo el instrumento inicial tiene gráfica grabada.
    await p.mouse.move(800, 450); await pausa(p, 1500);
    await desplazar(p, 450, 40, 90); await pausa(p, 1500); await desplazar(p, -450, 40, 90); await pausa(p, 1500);
  },
  tiempo: async (p) => { await vista(p, "tiempo"); await pausa(p, 1000); await desplazar(p, 1000, 60, 90); await pausa(p, 1000); },
  ficha: async (p) => {
    // Se escribe MU en el buscador de la ficha (sin emisora elegida la ficha sale vacía).
    await vista(p, "ficha"); await pausa(p, 600);
    const caja = p.locator("#panel-ficha input").first();
    await caja.click({ timeout: 2000 }).catch(() => {}); await caja.pressSequentially("MU", { delay: 220 }).catch(() => {});
    await pausa(p, 500); await p.locator("#panel-ficha button", { hasText: "Ver ficha" }).click({ timeout: 2000 }).catch(() => {});
    await pausa(p, 2500); await desplazar(p, 850, 70, 90); await pausa(p, 1200);  // termina en la gráfica, antes de los widgets que la demo no trae
  },
  investigacion: async (p) => { await vista(p, "investigacion"); await pausa(p, 1000); await desplazar(p, 1100, 60, 90); await pausa(p, 1000); },
  riesgo: async (p) => { await vista(p, "riesgo"); await pausa(p, 1200); await desplazar(p, 1300, 70, 90); await pausa(p, 1200); },
  propuestas: async (p) => { await vista(p, "propuestas"); await pausa(p, 1200); await desplazar(p, 1200, 70, 90); await pausa(p, 1000); },
  // Deja a la vista la estrategia de pesos iguales (1/N).
  backtesting: async (p) => { await vista(p, "backtesting"); await pausa(p, 1500); await desplazar(p, 330, 50, 90); await pausa(p, 1200); },
  robustez: async (p) => { await vista(p, "robustez"); await pausa(p, 1200); await desplazar(p, 900, 60, 90); await pausa(p, 1000); },
};

(async () => {
  fs.mkdirSync(DIR, { recursive: true });
  const nombres = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(ESCENAS);
  const b = await chromium.launch({ channel: process.env.CANAL || "msedge", headless: true });
  const rutaMarcas = path.join(DIR, "marcas.json");
  const marcas = fs.existsSync(rutaMarcas) ? JSON.parse(fs.readFileSync(rutaMarcas, "utf8")) : {};
  // Segundos que pide cada bloque del video (python scripts/video_final.py necesidades).
  const rutaNec = path.join(DIR, "necesarios.json");
  const necesarios = fs.existsSync(rutaNec) ? JSON.parse(fs.readFileSync(rutaNec, "utf8")) : {};
  for (const n of nombres) {
    const c = await b.newContext({ viewport: { width: W, height: H }, colorScheme: "dark", recordVideo: { dir: DIR, size: { width: W, height: H } } });
    const p = await c.newPage();
    p._t0 = Date.now();
    await ESCENAS[n](p);
    // Si la escena terminó antes de lo que dura la voz, se sigue leyendo la página con movimientos suaves.
    const meta = (p._marca ?? 0) + (necesarios[n] ?? 0) + 1;
    for (let i = 0; (Date.now() - p._t0) / 1000 < meta; i++) {
      await p.mouse.move(300 + (i % 5) * 90, 300 + (i % 3) * 60, { steps: 8 });
      await desplazar(p, i % 4 < 2 ? 160 : -160, 16, 70);
    }
    marcas[n] = Math.max(0, (p._marca ?? 0) - 0.3);
    fs.writeFileSync(rutaMarcas, JSON.stringify(marcas, null, 1));
    const v = p.video(); await c.close();
    const destino = path.join(DIR, `${n}.webm`);
    fs.rmSync(destino, { force: true }); fs.renameSync(await v.path(), destino);
    console.log(n);
  }
  await b.close();
})().catch((e) => { console.error(e); process.exit(1); });
