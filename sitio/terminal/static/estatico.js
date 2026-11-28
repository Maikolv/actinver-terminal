/* Versión estática (GitHub Pages): la terminal corre sin servidor con respuestas de la API grabadas en modo
   demostración (datos simulados). Las lecturas salen de api/<hash>.json; lo que guarda el visitante vive en su
   localStorage y lo demás que escribe o calcula en el servidor responde con un aviso. Solo se carga en la exportación estática (scripts/exportar_estatico.cjs). */
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

  // Lo que el visitante guarda (portafolios, principal, bitácora, listas de seguimiento) vive en su navegador, como
  // la base local de la terminal: se superpone a las respuestas grabadas. Nunca sale del navegador.
  const CLAVE = "actinver-demo-estado-v1";
  const leer = () => { try { return JSON.parse(localStorage.getItem(CLAVE)) || {}; } catch { return {}; } };
  const escribir = (e) => { try { localStorage.setItem(CLAVE, JSON.stringify(e)); } catch { /* sin almacenamiento: dura la visita */ } };
  let memoria = null;
  const estado = () => (memoria = memoria || { portafolios: [], bitacora: [], lista: [], listaFuera: [], seguimiento: [], seguimientoFuera: [], sig: 1000, ...leer() });
  const cambiar = (f) => { const e = estado(); const r = f(e); escribir(e); return r; };
  const ahora = () => new Date().toISOString();
  // Propuestas calculadas en esta visita, por especificación: «Guardar» guarda exactamente la que se ve.
  const firma = (s) => JSON.stringify(Object.keys(s || {}).filter((k) => k !== "nombre" && k !== "descripcion").sort().map((k) => [k, s[k]]));
  const generados = new Map();
  const errorLocal = (texto, status = 422) => json({ error: texto, detail: texto, errores: [texto] }, status);
  const resumenPf = (p) => ({ id: p.id, nombre: p.nombre, actualizado_en: p.actualizado_en, especificacion: p.especificacion,
    metricas: p.respuesta.resultado.metricas, metodo_nombre: p.respuesta.resultado.metodo_nombre, objetivo_nombre: p.respuesta.resultado.objetivo_nombre,
    calculado_en: p.respuesta.resultado.calculado_en, n_activos: (p.respuesta.resultado.activos || []).filter((a) => a.peso >= 0.005).length });
  const universo = async () => {
    try { return (await (await window.fetch("/api/universo")).json()).instrumentos || []; } catch { return []; }
  };

  async function escrituraLocal(metodo, ruta, cuerpo) {
    let m;
    if (metodo === "POST" && ruta === "/api/portafolios" || metodo === "PUT" && (m = ruta.match(/^\/api\/portafolios\/(\d+)$/))) {
      const respuesta = generados.get(firma(cuerpo));
      if (!respuesta) return errorLocal("Genere la propuesta antes de guardarla.");
      if (!String(cuerpo.nombre || "").trim()) return errorLocal("Póngale un nombre al portafolio.");
      return json(cambiar((e) => {
        const id = m ? Number(m[1]) : e.sig++;
        const p = { id, nombre: String(cuerpo.nombre).slice(0, 80), actualizado_en: ahora(), especificacion: cuerpo, respuesta };
        e.portafolios = e.portafolios.filter((x) => x.id !== id).concat(p);
        return { id, ...respuesta.resultado, especificacion: cuerpo };
      }));
    }
    if (metodo === "DELETE" && (m = ruta.match(/^\/api\/portafolios\/(\d+)$/))) {
      cambiar((e) => { e.portafolios = e.portafolios.filter((x) => x.id !== Number(m[1])); if (e.principal === Number(m[1])) e.principal = null; });
      return json({ ok: true });
    }
    if (metodo === "PUT" && (m = ruta.match(/^\/api\/portafolios\/(\d+)\/principal$/))) { cambiar((e) => { e.principal = Number(m[1]); }); return json({ ok: true }); }
    if (metodo === "DELETE" && ruta === "/api/portafolio-principal") { cambiar((e) => { e.principal = null; }); return json({ ok: true }); }
    if (metodo === "POST" && ruta === "/api/bitacora") {
      const tipos = ["tesis", "entrada", "salida", "revision", "error", "leccion"], tipo = cuerpo.tipo || "tesis";
      if (!tipos.includes(tipo)) return errorLocal(`tipo: ${tipos.join(", ")}`);
      if (!String(cuerpo.decision_humana || "").trim()) return errorLocal("Escriba la decisión humana.");
      return json(cambiar((e) => {
        const id = e.sig++;
        e.bitacora.unshift({ id, creada_en: ahora(), tipo, instrumento_id: cuerpo.instrumento_id || null, tesis: cuerpo.tesis || "",
          decision_humana: String(cuerpo.decision_humana), version_reglas: null, version_modelo: "demo" });
        return { id };
      }));
    }
    if (metodo === "POST" && ruta === "/api/lista-seguimiento") {
      const id = String(cuerpo.id || "");
      if (!id) return errorLocal("Elija un instrumento.");
      const clave = ((await universo()).find((i) => i.id === id) || {}).clave_operable || id;
      cambiar((e) => {
        e.lista = e.lista.filter((x) => x.instrumento_id !== id);
        e.listaFuera = e.listaFuera.filter((x) => x !== id);
        if (cuerpo.quitar) e.listaFuera.push(id);
        else e.lista.push({ instrumento_id: id, clave, nota: String(cuerpo.nota || "").slice(0, 300), variacion: {}, ultimo_mxn: null, fecha: null, rsi14: null, noticias_7d: null });
      });
      return window.fetch("/api/lista-seguimiento");
    }
    if (metodo === "POST" && ruta === "/api/seguimiento" || metodo === "DELETE" && (m = ruta.match(/^\/api\/seguimiento\/(.+)$/))) {
      const id = m ? decodeURIComponent(m[1]) : String(cuerpo.instrumento_id || "");
      if (!id) return errorLocal("Escriba un instrumento.");
      cambiar((e) => {
        e.seguimiento = e.seguimiento.filter((x) => x !== id); e.seguimientoFuera = e.seguimientoFuera.filter((x) => x !== id);
        (m ? e.seguimientoFuera : e.seguimiento).push(id);
      });
      return json({ ok: true });
    }
    return null;
  }

  // Superpone lo guardado en el navegador a una lectura grabada.
  function lecturaLocal(ruta, d) {
    const e = estado();
    if (ruta === "/api/portafolios") {
      d.portafolios = (d.portafolios || []).concat(e.portafolios.map(resumenPf));
      if ("principal" in e) d.principal = e.principal;
    } else if (ruta === "/api/bitacora") d.entradas = e.bitacora.concat(d.entradas || []);
    else if (ruta === "/api/lista-seguimiento") {
      const locales = new Set(e.lista.map((x) => x.instrumento_id));
      d.instrumentos = (d.instrumentos || []).filter((x) => !e.listaFuera.includes(x.instrumento_id) && !locales.has(x.instrumento_id)).concat(e.lista);
    } else if (ruta === "/api/movimientos" && Array.isArray(d.seguimiento)) {
      const ids = new Set(d.seguimiento.map((s) => s.instrumento_id).concat(e.seguimiento));
      e.seguimientoFuera.forEach((x) => ids.delete(x));
      d.seguimiento = [...ids].sort().map((instrumento_id) => ({ instrumento_id }));
    }
    return d;
  }
  const LOCALES = ["/api/portafolios", "/api/bitacora", "/api/lista-seguimiento", "/api/movimientos"];

  window.fetch = async (recurso, opciones = {}) => {
    const url = new URL(typeof recurso === "string" ? recurso : recurso.url, location.href);
    const ruta = url.pathname.replace(/^.*?(\/api\/)/, "/api/");
    if (!ruta.startsWith("/api/")) return original(recurso, opciones);
    const metodo = (opciones.method || (typeof recurso === "string" ? "GET" : recurso.method) || "GET").toUpperCase();
    indice = indice || original(`${BASE}api/indice.json`).then((r) => r.json()).then((xs) => new Set(xs)).catch(() => new Set());
    if (metodo !== "GET") {
      let cuerpoJson = {};
      try { cuerpoJson = typeof opciones.body === "string" && opciones.body ? JSON.parse(opciones.body) : {}; } catch { /* no es JSON */ }
      const local = await escrituraLocal(metodo, ruta, cuerpoJson);
      if (local) return local;
      // Cálculos sin efectos (simular, generar, backtest, Heston): se sirven si esa misma consulta se grabó.
      if (metodo === "POST" && CALCULOS.includes(ruta)) {
        const cuerpo = typeof opciones.body === "string" ? opciones.body : "";
        const clave = hash(`POST ${ruta}${url.search}
${cuerpo}`);
        if ((await indice).has(clave)) {
          const d = await original(`${BASE}api/${clave}.json`).then((r) => r.json());
          if (ruta === "/api/portafolios/generar" && d?.resultado?.especificacion) generados.set(firma(d.resultado.especificacion), d);
          return d && d.__estado ? json(d.cuerpo, d.__estado) : json(d);
        }
        if (ruta === "/api/portafolios/generar") {
          // Abrir un portafolio guardado: mismos instrumentos y parámetros que la propuesta que se guardó.
          const g = cuerpoJson, igual = (a, b) => JSON.stringify([...(a || [])].sort()) === JSON.stringify([...(b || [])].sort());
          const p = estado().portafolios.find((x) => { const s = x.especificacion;
            return igual(s.activos, g.fijos) && ["objetivo", "metodo", "peso_max", "ventana", "covarianza", "capital"].every((k) => s[k] === g[k]); });
          if (p) { generados.set(firma(p.respuesta.resultado.especificacion), p.respuesta); return json(p.respuesta); }
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
    const propio = ruta.match(/^\/api\/portafolios\/(\d+)$/) && estado().portafolios.find((x) => x.id === Number(ruta.split("/").pop()));
    if (propio) return json({ id: propio.id, ...propio.respuesta.resultado, especificacion: propio.especificacion });
    for (const clave of [ruta + url.search, ruta]) {
      if (!hay.has(hash(clave))) continue;
      const r = await original(`${BASE}api/${hash(clave)}.json`);
      return LOCALES.includes(ruta) && r.ok ? json(lecturaLocal(ruta, await r.json())) : r;
    }
    if (ruta === "/api/lista-seguimiento") return json(lecturaLocal(ruta, { instrumentos: [] }));
    return json({ error: "Sin dato en la versión estática para esta consulta (solo se grabaron las vistas principales).", detail: AVISO }, 503);
  };
  // La vela en vivo usa EventSource: en la versión estática no hay transmisión.
  window.EventSource = class { constructor() { this.readyState = 2; } close() {} addEventListener() {} };
  document.addEventListener("DOMContentLoaded", () => {
    const b = document.createElement("div");
    b.className = "aviso-caja aviso-estatica";
    b.setAttribute("role", "note");
    b.textContent = "Versión estática en GitHub Pages con DATOS SIMULADOS. Sus portafolios, el principal, la bitácora y las listas de seguimiento se guardan solo en este navegador; descargar datos, importar archivos, Excel, Telegram y cálculos con otras especificaciones requieren la terminal local.";
    document.body.prepend(b);
  });
})();
