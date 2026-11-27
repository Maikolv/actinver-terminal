// Grabaciones en video de la terminal LOCAL del equipo (127.0.0.1:8765) para el video del concurso.
// Solo lee: no pulsa botones que guarden o envíen nada y nunca abre la cuenta de Actinver.
//   FORMATO=horizontal|vertical|tiktok node scripts/grabar_terminal.cjs [nombre…]   → data/medios/video/grabaciones/<formato>/<nombre>.webm
"use strict";
const { chromium } = require("playwright");
const fs = require("node:fs"), path = require("node:path");
const ORIGEN = process.env.ORIGEN || "http://127.0.0.1:8765/";
const BASE = path.resolve(__dirname, "..", "data", "medios", "video", "grabaciones");
// Mismo tamaño que el área de la terminal en el video (video_final.geometria «cont»): se usa 1:1, sin recorte ni escala.
const FORMATO = ["vertical", "tiktok"].includes(process.env.FORMATO) ? process.env.FORMATO : "horizontal";
// tiktok: zona segura de TikTok (sin la barra superior, los botones de la derecha ni la descripción de abajo).
const [W, H] = { horizontal: [1880, 680], vertical: [1060, 1100], tiktok: [840, 832] }[FORMATO];
const DIR = path.join(BASE, FORMATO);

const pausa = (p, ms) => p.waitForTimeout(ms);
async function desplazar(p, total, pasos = 40, ms = 60) {  // desplazamiento suave, como una persona con la rueda
  for (let i = 0; i < pasos; i++) { await p.mouse.wheel(0, total / pasos); await pausa(p, ms); }
}
// La terminal real tarda más que la demo: se espera a que no quede ningún marcador de carga visible.
const listo = (p) => p.waitForFunction(() => document.documentElement.dataset.calculo === "listo"
  && ![...document.querySelectorAll("section[role=tabpanel]:not([hidden]) :is(.esqueleto, .cargando)")].some((e) => e.offsetParent),
  null, { timeout: 150000, polling: 500 }).catch(() => {});
async function vista(p, tab) {
  await p.goto(`${ORIGEN}?vista=tab-${tab}`, { waitUntil: "networkidle" }).catch(() => {});
  await listo(p); await pausa(p, 1500); await listo(p);
  // Si el servidor estaba ocupado y quedó una caja de error, se recarga (hasta dos veces).
  for (let i = 0; i < 2 && await p.locator("section[role=tabpanel]:not([hidden]) .error-caja").first().isVisible().catch(() => false); i++) {
    await p.reload({ waitUntil: "networkidle" }).catch(() => {}); await listo(p); await pausa(p, 1500); await listo(p);
  }
  await p.evaluate((id) => {
    document.querySelectorAll("details[open]").forEach((d) => { d.open = false; });
    const el = document.getElementById(id);
    if (el) window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 8 });
  }, `tab-${tab}`);
  await pausa(p, 900);
  if (p._marca == null) p._marca = (Date.now() - p._t0) / 1000;  // segundo en que la vista ya está lista
}
async function irA(p, panel, prefijo) {
  await p.waitForFunction(([panel, prefijo]) => [...document.querySelectorAll(`#panel-${panel} :is(h2, h3)`)]
    .some((x) => x.textContent.trim().startsWith(prefijo)), [panel, prefijo], { timeout: 60000 }).catch(() => {});
  await p.evaluate(([panel, prefijo]) => {
    const h = [...document.querySelectorAll(`#panel-${panel} :is(h2, h3)`)].find((x) => x.textContent.trim().startsWith(prefijo));
    if (h) window.scrollTo({ top: h.getBoundingClientRect().top + window.scrollY - 8 });
  }, [panel, prefijo]);
  await pausa(p, 1200);
}
// Escribe MU en el buscador de la ficha (sin emisora elegida la ficha sale vacía) y espera la ficha.
async function fichaMU(p) {
  await vista(p, "ficha"); await pausa(p, 600);
  const caja = p.locator("#panel-ficha input").first();
  await caja.click({ timeout: 2000 }).catch(() => {}); await caja.fill("MU").catch(() => {}); await caja.press("Escape").catch(() => {});
  await pausa(p, 500); await p.locator("#panel-ficha button", { hasText: "Ver ficha" }).click({ timeout: 2000 }).catch(() => {});
  await p.waitForFunction(() => /MICRON/i.test(document.getElementById("panel-ficha")?.innerText || ""), null, { timeout: 60000 }).catch(() => {});
  await pausa(p, 800);
}
async function agresivo(p) {
  await p.locator("#panel-portafolios").getByText("Agresivo", { exact: true }).first().click({ timeout: 3000 }).catch(() => {});
  await pausa(p, 1500); await listo(p); await pausa(p, 800);
}
// Cada escena: lo que se hace frente a la cámara (12–20 s).
const ESCENAS = {
  // Ranking del universo con capitalización y vigencia de cada dato.
  inicio: async (p) => { await vista(p, "ranking"); await pausa(p, 1500); await desplazar(p, 1400, 60, 90); await pausa(p, 1500); },
  // Mesa de investigación: paleta de comandos y cuadrícula de paneles.
  mesa: async (p) => {
    await p.goto(`${ORIGEN}static/mesa.html`, { waitUntil: "networkidle" }).catch(() => {});
    await pausa(p, 2500); p._marca = (Date.now() - p._t0) / 1000;
    await desplazar(p, 900, 60, 90); await pausa(p, 1200);
  },
  // Plan de órdenes de la propuesta: qué vender, comprar o mantener y por qué.
  plan: async (p) => { await vista(p, "propuestas"); await irA(p, "propuestas", "Plan de órdenes"); p._marca = (Date.now() - p._t0) / 1000; await pausa(p, 1500); await desplazar(p, 900, 60, 90); await pausa(p, 1500); },
  // Datos y fuentes: cada proveedor gratuito con su retraso y vigencia.
  legal: async (p) => { await vista(p, "universo"); await pausa(p, 1200); await desplazar(p, 1100, 60, 90); await pausa(p, 1000); },
  portafolios: async (p) => {
    await vista(p, "portafolios"); await pausa(p, 1200);
    await agresivo(p);
    await desplazar(p, 1100, 60, 90); await pausa(p, 1500); await desplazar(p, 900, 60, 90); await pausa(p, 1200);
  },
  mercado: async (p) => {
    await vista(p, "mercado"); await pausa(p, 1200);
    // Busca MU con «/» como lo haría una persona.
    // La estación se vuelve a pintar al llegar datos: se reintenta hasta que el filtro quede escrito.
    for (let i = 0; i < 3; i++) {
      const caja = p.locator("#estacion-buscar");
      await caja.click({ timeout: 3000 }).catch(() => {}); await caja.pressSequentially("MU", { delay: 220 }).catch(() => {});
      await pausa(p, 900);
      if (await caja.inputValue().catch(() => "") === "MU") {
        await p.locator('#estacion-monitor-tabla tr[data-id="SIC:MU"]').click({ timeout: 3000 }).catch(() => caja.press("Enter").catch(() => {}));
        break;
      }
      await caja.fill("").catch(() => {});
    }
    await pausa(p, 2500);
    await desplazar(p, 450, 40, 90); await pausa(p, 1500); await desplazar(p, -450, 40, 90); await pausa(p, 1500);
  },
  tiempo: async (p) => { await vista(p, "tiempo"); await pausa(p, 1000); await desplazar(p, 1000, 60, 90); await pausa(p, 1000); },
  ficha: async (p) => {
    await fichaMU(p);
    await p.evaluate(() => { const e = [...document.querySelectorAll("#panel-ficha *")].find((x) => x.children.length === 0 && /MICRON TECHNOLOGY/i.test(x.textContent));
      if (e) window.scrollTo({ top: e.getBoundingClientRect().top + window.scrollY - 60 }); });
    p._marca = (Date.now() - p._t0) / 1000;
    await pausa(p, 2500); await desplazar(p, 850, 70, 90); await pausa(p, 1200);
  },
  // Lectura técnica de MU que calcula la terminal (medias, RSI, MACD, Bollinger).
  tecnico: async (p) => {
    await fichaMU(p);
    await p.evaluate(() => { const e = [...document.querySelectorAll("#panel-ficha :is(h2, h3, h4)")].find((x) => /an[aá]lisis t[eé]cnico/i.test(x.textContent));
      if (e) window.scrollTo({ top: e.getBoundingClientRect().top + window.scrollY - 8 }); });
    p._marca = (Date.now() - p._t0) / 1000;
    await pausa(p, 3000); await desplazar(p, 500, 60, 90); await pausa(p, 1500);
  },
  // Portafolios guardados: el idóneo de Markowitz y el botón «Usar como principal» (no se pulsa).
  guardados: async (p) => { await vista(p, "portafolios"); await irA(p, "portafolios", "Portafolios guardados"); p._marca = (Date.now() - p._t0) / 1000; await pausa(p, 2500); await desplazar(p, 500, 60, 90); await pausa(p, 1500); },
  // Alertas: umbrales, canales (Telegram) y avisos; no se pulsa «Enviar aviso de prueba».
  alertas: async (p) => { await vista(p, "alertas"); await pausa(p, 1500); await desplazar(p, 600, 60, 90); await pausa(p, 2000); await desplazar(p, 700, 60, 90); await pausa(p, 1500); },
  investigacion: async (p) => { await vista(p, "investigacion"); await pausa(p, 1000); await desplazar(p, 1100, 60, 90); await pausa(p, 1000); },
  // «Riesgo» necesita posiciones y la cuenta del Reto está archivada: se muestran el riesgo y los escenarios de la propuesta.
  riesgo: async (p) => { await vista(p, "propuestas"); await pausa(p, 1500); await desplazar(p, 700, 60, 90); await pausa(p, 2500); await desplazar(p, 500, 50, 90); await pausa(p, 1500); },
  // Prueba fuera de muestra frente a 1/N en «Mis portafolios».
  propuestas: async (p) => { await vista(p, "portafolios"); await irA(p, "portafolios", "Prueba fuera de muestra"); p._marca = (Date.now() - p._t0) / 1000; await pausa(p, 1500); await desplazar(p, 600, 60, 90); await pausa(p, 1500); },
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
  const rutaNec = path.join(BASE, "necesarios.json");
  const necesarios = fs.existsSync(rutaNec) ? JSON.parse(fs.readFileSync(rutaNec, "utf8")) : {};
  for (const n of nombres) {
    const c = await b.newContext({ viewport: { width: W, height: H }, colorScheme: "dark", recordVideo: { dir: DIR, size: { width: W, height: H } } });
    // Playwright solo graba cuadros cuando la página cambia: un píxel invisible que parpadea mantiene el reloj del video
    // igual al reloj real, para que las marcas de «vista lista» caigan en el segundo correcto.
    await c.addInitScript(() => addEventListener("DOMContentLoaded", () => {
      const d = Object.assign(document.createElement("div"), { style: "position:fixed;left:0;bottom:0;width:1px;height:1px;z-index:99999;pointer-events:none" });
      document.body.append(d); let k = 0;
      (function tic() { d.style.background = k++ % 2 ? "#090a0c" : "#0a0b0d"; requestAnimationFrame(tic); })();
    }));
    // En 16:9 la página de la terminal tiene ancho máximo: con zoom de 130 % ocupa toda la ventana y el texto se lee.
    if (FORMATO === "horizontal") await c.addInitScript(() => addEventListener("DOMContentLoaded", () => { document.documentElement.style.zoom = "1.3"; }));
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
