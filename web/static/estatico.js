/* Versión estática (GitHub Pages): la terminal corre sin servidor con respuestas de la API grabadas en modo
   demostración (datos simulados). Las lecturas salen de api/<hash>.json; todo lo que escribe o calcula en el
   servidor responde con un aviso. Solo se carga en la exportación estática (scripts/exportar_estatico.cjs). */
"use strict";
(() => {
  const BASE = document.currentScript.src.replace(/static\/estatico\.js.*$/, "");
  // FNV-1a de 32 bits: el mismo nombre de archivo que calcula el exportador.
  const hash = (s) => { let h = 0x811c9dc5; for (const c of new TextEncoder().encode(s)) { h ^= c; h = Math.imul(h, 0x01000193) >>> 0; } return h.toString(16).padStart(8, "0"); };
  const AVISO = "Versión estática de demostración (datos simulados): esta acción necesita la terminal local. Vea «Cómo correr» en el README.";
  const AVISO_CALCULO = "Versión estática: este cálculo se precalculó solo para las opciones predeterminadas (perfiles, clases, estrategias y simulaciones sugeridas). Con otras especificaciones, use la terminal local.";
  const CALCULOS = ["/api/simular", "/api/portafolios/generar", "/api/backtests", "/api/flujo/heston", "/api/asistente"];
  const json = (cuerpo, status = 200) => new Response(JSON.stringify(cuerpo), { status, headers: { "Content-Type": "application/json" } });
  const original = window.fetch.bind(window);
  let indice = null;  // respuestas grabadas (hashes), para no pedir archivos que no existen
  window.HQT_ESTATICA = true;
  window.fetch = async (recurso, opciones = {}) => {
    const url = new URL(typeof recurso === "string" ? recurso : recurso.url, location.href);
    const ruta = url.pathname.replace(/^.*?(\/api\/)/, "/api/");
    if (!ruta.startsWith("/api/")) return original(recurso, opciones);
    const metodo = (opciones.method || (typeof recurso === "string" ? "GET" : recurso.method) || "GET").toUpperCase();
    indice = indice || original(`${BASE}api/indice.json`).then((r) => r.json()).then((xs) => new Set(xs)).catch(() => new Set());
    if (metodo !== "GET") {
      // Cálculos sin efectos (simular, generar, backtest, Heston): se sirven si esa misma consulta se grabó.
      if (metodo === "POST" && CALCULOS.includes(ruta)) {
        const cuerpo = typeof opciones.body === "string" ? opciones.body : "";
        const clave = hash(`POST ${ruta}${url.search}
${cuerpo}`);
        if ((await indice).has(clave)) {
          const d = await original(`${BASE}api/${clave}.json`).then((r) => r.json());
          return d && d.__estado ? json(d.cuerpo, d.__estado) : json(d);
        }
        if (ruta === "/api/asistente") {  // el Asistente responde las preguntas de ejemplo grabadas
          const qs = await original(`${BASE}api/preguntas.json`).then((r) => r.json()).catch(() => []);
          if (/^\s*\//.test(cuerpo.replace(/^\{"texto":"/, ""))) return json({ error: AVISO, detail: AVISO }, 403);
          return json({ respuesta: `En la versión estática el Asistente solo responde estas preguntas de ejemplo (escríbalas tal cual): ${qs.map((q) => `«${q}»`).join(", ")}. La terminal local responde cualquier pregunta.`, motor: "estatico" });
        }
        return json({ error: AVISO_CALCULO, detail: AVISO_CALCULO }, 503);
      }
      return json({ error: AVISO, detail: AVISO }, 403);
    }
    const hay = await indice;
    for (const clave of [ruta + url.search, ruta]) {
      if (hay.has(hash(clave))) return original(`${BASE}api/${hash(clave)}.json`);
    }
    return json({ error: "Sin dato en la versión estática para esta consulta (solo se grabaron las vistas principales).", detail: AVISO }, 503);
  };
  // La vela en vivo usa EventSource: en la versión estática no hay transmisión.
  window.EventSource = class { constructor() { this.readyState = 2; } close() {} addEventListener() {} };
  document.addEventListener("DOMContentLoaded", () => {
    const b = document.createElement("div");
    b.className = "aviso-caja aviso-estatica";
    b.setAttribute("role", "note");
    b.textContent = "Versión estática en GitHub Pages con DATOS SIMULADOS: se puede navegar y explorar; calcular, guardar y operar requieren la terminal local.";
    document.body.prepend(b);
  });
})();
