/* Actinver Terminal — interfaz. Sin dependencias.
   Regla de seguridad: los datos nunca se insertan como HTML; todo se crea con textContent. */
"use strict";

const CSRF = document.querySelector('meta[name="csrf"]').content;
const estado = {
  propuestas: null, clasificacion: [], cartera: null, universo: null, datos: null, reto: null,
  universoSel: "acciones", lenteSel: "ajuste", lenteResumen: "ajuste", ultimoCiclo: null,
};

/* ---------- utilidades ---------- */
function h(tag, attrs, ...hijos) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "clase") el.className = v;
    else if (k === "texto") el.textContent = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of hijos.flat()) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}
const svgNS = "http://www.w3.org/2000/svg";
function s(tag, attrs, ...hijos) {
  const el = document.createElementNS(svgNS, tag);
  for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, v);
  for (const c of hijos) el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  return el;
}
const fmtMXN = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 0 });
const fmtMXN2 = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 2 });
const fmtNum = new Intl.NumberFormat("es-MX", { maximumFractionDigits: 4 });
const fmtPct = new Intl.NumberFormat("es-MX", { style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1 });
const fmtFecha = new Intl.DateTimeFormat("es-MX", { timeZone: "America/Mexico_City", dateStyle: "short", timeStyle: "short" });
const vacio = (v) => v === null || v === undefined || Number.isNaN(v);
const mxn = (v, dec) => (vacio(v) ? "—" : (dec ? fmtMXN2 : fmtMXN).format(v));
const pct = (v) => (vacio(v) ? "—" : fmtPct.format(v));
const num = (v) => (vacio(v) ? "—" : fmtNum.format(v));
const fechaLocal = (iso) => { if (!iso) return "—"; const d = new Date(iso); return Number.isNaN(d.getTime()) ? iso : fmtFecha.format(d); };
const signo = (v) => (v > 0 ? "positivo" : v < 0 ? "negativo" : "");
const ETIQ = { vigente: "Vigente", retrasado: "Dato retrasado", vencido: "Dato vencido", sin_datos: "Sin datos suficientes",
  sintetico: "Sintético", calculada: "Calculada", demostracion: "Demostración", suspendida: "Suspendida", desactualizada: "No actual" };
const chip = (e, texto) => h("span", { clase: `chip chip--${e || "sin_datos"}`, texto: texto || ETIQ[e] || e || "Sin datos" });
const CLASES = { accion: "Acción", reit: "Acción (REIT)", etf: "ETF", fibra: "FIBRA", fondo_deuda: "Fondo de deuda",
  fondo_renta_variable: "Fondo de renta variable", fondo_multiactivo: "Fondo multiactivo" };
const ETAPAS = { inscripcion: "Inscripción", practica: "Semana de práctica", previa_competencia: "Antes de la competencia",
  competencia: "Competencia", concluido: "Concluido" };
const LENTES = { rendimiento: "Máximo rendimiento", ajuste: "Ajuste a su perfil" };

function externo(url, texto) {
  if (typeof url !== "string" || !url.startsWith("https://")) return h("span", { texto });
  return h("a", { href: url, target: "_blank", rel: "noopener noreferrer", texto });
}
async function api(ruta, opciones = {}) {
  const o = { ...opciones, headers: { ...(opciones.headers || {}) } };
  if (o.method && o.method !== "GET") o.headers["X-CSRF-Token"] = CSRF;
  if (o.json !== undefined) { o.body = JSON.stringify(o.json); o.headers["Content-Type"] = "application/json"; delete o.json; }
  let r;
  try { r = await fetch(ruta, o); } catch { throw new Error("No hay conexión con el servidor local. ¿Sigue ejecutándose?"); }
  let datos = null;
  try { datos = await r.json(); } catch { /* respuesta sin JSON */ }
  if (!r.ok) {
    const err = new Error((datos && (datos.error || datos.detail)) || `Error ${r.status}`);
    err.errores = datos && datos.errores;
    throw err;
  }
  return datos;
}
function notificar(texto) {
  const n = document.getElementById("notificacion");
  n.textContent = texto; n.hidden = false;
  clearTimeout(notificar.t); notificar.t = setTimeout(() => { n.hidden = true; }, 6000);
}
function tabla(columnas, filas, { caption, vacio: textoVacio = "Sin registros." } = {}) {
  if (!filas.length) return h("p", { clase: "vacio", texto: textoVacio });
  const cab = h("tr", {}, columnas.map((c) => h("th", { scope: "col", clase: c.num ? "num" : null, texto: c.t })));
  const cuerpo = filas.map((f) => h("tr", {}, columnas.map((c) => {
    const v = c.f(f);
    return h("td", { clase: c.num ? "num" : null }, v instanceof Node ? v : (v ?? "—"));
  })));
  return h("div", { clase: "tabla-contenedor" }, h("table", {}, caption ? h("caption", { texto: caption }) : null,
    h("thead", {}, cab), h("tbody", {}, cuerpo)));
}
function limpiar(id, ...hijos) { const el = document.getElementById(id); el.replaceChildren(...hijos); return el; }
function errorCaja(e) { return h("div", { clase: "error-caja", role: "alert" }, e.message || String(e)); }
function ocupado(botones, si) { botones.forEach((b) => { b.disabled = si; b.setAttribute("aria-busy", si ? "true" : "false"); }); }
function kpi(etiqueta, valor, clase) { return h("div", { clase: "kpi" }, h("span", { clase: "etiqueta", texto: etiqueta }), h("span", { clase: `valor ${clase || ""}`, texto: valor })); }
function barraPct(v, max = 1) { const b = h("span"); b.style.width = `${Math.max(0, Math.min(v / max, 1)) * 100}%`; return h("span", { clase: "barra", "aria-hidden": "true" }, b); }
function segmentado(id, valorActual, alCambiar) {
  const g = document.getElementById(id);
  g.querySelectorAll("button").forEach((b) => {
    b.setAttribute("aria-checked", b.dataset.valor === valorActual);
    b.onclick = () => alCambiar(b.dataset.valor);
  });
}

/* ---------- pestañas (teclado: flechas, Inicio, Fin) ---------- */
const CARGAS = {
  "tab-alertas": () => cargarAlertas(), "tab-cartera": () => cargarCartera(), "tab-mercado": () => cargarMercado(),
  "tab-universo": () => cargarUniverso(), "tab-perfil": () => { cargarReto(); cargarPerfil(); },
};
function activarPestana(tab, enfocar) {
  document.querySelectorAll('[role="tab"]').forEach((t) => {
    const sel = t === tab;
    t.setAttribute("aria-selected", sel); t.tabIndex = sel ? 0 : -1;
    document.getElementById(t.getAttribute("aria-controls")).hidden = !sel;
  });
  if (enfocar) tab.focus();
  try { localStorage.setItem("pestana", tab.id); } catch { /* sin almacenamiento */ }
  if (CARGAS[tab.id]) CARGAS[tab.id]();
}
document.getElementById("lista-pestanas").addEventListener("keydown", (ev) => {
  const tabs = [...document.querySelectorAll('[role="tab"]')];
  const i = tabs.indexOf(document.activeElement);
  if (i < 0) return;
  const mapa = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 };
  if (ev.key in mapa) { ev.preventDefault(); activarPestana(tabs[(mapa[ev.key] + tabs.length) % tabs.length], true); }
});
document.querySelectorAll('[role="tab"]').forEach((t) => t.addEventListener("click", () => activarPestana(t)));
const irA = (id) => activarPestana(document.getElementById(id));

/* ---------- estado de datos y motor ---------- */
async function cargarEstado() {
  try {
    const d = await api("/api/estado");
    estado.datos = d;
    document.getElementById("aviso-demo").hidden = d.modo !== "demo";
    const bm = document.getElementById("btn-modo");
    bm.dataset.destino = d.modo === "demo" ? "real" : "demo";
    bm.textContent = d.modo === "demo" ? "Usar datos reales y vigentes" : "Ver demostración";
    bm.classList.toggle("boton--real", d.modo === "demo");
    const c = document.getElementById("contador-alertas");
    c.hidden = !d.alertas_pendientes; c.textContent = d.alertas_pendientes || "";
    c.setAttribute("aria-label", `${d.alertas_pendientes} alertas nuevas`);
    const v = d.vigencia || {};
    const m = d.motor || {};
    limpiar("estado-datos",
      h("span", { clase: "grupo" }, "Precios:",
        ...["vigente", "retrasado", "vencido", "sin_datos", "sintetico"].filter((k) => v[k]).map((k) => chip(k, `${v[k]} ${ETIQ[k].toLowerCase()}`))),
      h("span", { clase: "grupo" }, "USD/MXN:", d.fx.valor ? h("span", { clase: "cifra", texto: num(d.fx.valor) }) : "", d.fx.valor ? `(${d.fx.fecha}, ${d.fx.proveedor})` : "", chip(d.fx.estado, d.fx.etiqueta)),
      h("span", { clase: "grupo" }, `Sesión cerrada: NYSE ${d.ultima_sesion.NYSE} · BMV ${d.ultima_sesion.BMV}`),
      h("span", { clase: "grupo" }, m.ultimo_ciclo ? `Motor: ${fechaLocal(m.ultimo_ciclo)} · ${m.recalculo}` : "Motor: en espera"),
      h("span", { clase: "grupo" }, "Tiempo real: no · Operaciones reales: deshabilitadas"));
    if (m.ultimo_ciclo && estado.ultimoCiclo && m.ultimo_ciclo !== estado.ultimoCiclo) {
      await cargarPropuestas(); // el motor terminó un ciclo: refrescar sin recargar la página
      if (m.alertas_nuevas) notificar(`${m.alertas_nuevas} alerta(s) nueva(s).`);
    }
    estado.ultimoCiclo = m.ultimo_ciclo || estado.ultimoCiclo;
  } catch (e) { limpiar("estado-datos", errorCaja(e)); }
}

/* ---------- gráfica de líneas (SVG accesible) ---------- */
function grafica(series, { alto = 220, formato = pct, etiqueta = "Gráfica" } = {}) {
  const ancho = 720, m = { i: 56, d: 12, s: 10, inf: 26 };
  const puntos = series.flatMap((se) => se.datos.filter((p) => !vacio(p.y)));
  if (puntos.length < 2) return h("p", { clase: "vacio", texto: "Sin historia suficiente para graficar." });
  const xs = [...new Set(series.flatMap((se) => se.datos.map((p) => p.x)))].sort();
  const pos = new Map(xs.map((x, i) => [x, i]));
  const ys = puntos.map((p) => p.y);
  let min = Math.min(...ys), max = Math.max(...ys);
  if (min === max) { min -= 1; max += 1; }
  const X = (x) => m.i + (pos.get(x) / Math.max(xs.length - 1, 1)) * (ancho - m.i - m.d);
  const Y = (y) => m.s + (1 - (y - min) / (max - min)) * (alto - m.s - m.inf);
  const svg = s("svg", { viewBox: `0 0 ${ancho} ${alto}`, class: "grafica", role: "img", "aria-label": etiqueta });
  for (let k = 0; k <= 3; k++) {
    const y = min + ((max - min) * k) / 3;
    svg.append(s("line", { x1: m.i, x2: ancho - m.d, y1: Y(y), y2: Y(y), stroke: "var(--borde)", "stroke-width": 1 }));
    svg.append(s("text", { x: m.i - 6, y: Y(y) + 4, "text-anchor": "end" }, formato(y)));
  }
  [xs[0], xs[Math.floor(xs.length / 2)], xs[xs.length - 1]].forEach((x, j) =>
    svg.append(s("text", { x: X(x), y: alto - 6, "text-anchor": ["start", "middle", "end"][j] }, x)));
  series.forEach((se) => {
    const d = se.datos.filter((p) => !vacio(p.y)).map((p, i) => `${i ? "L" : "M"}${X(p.x).toFixed(1)},${Y(p.y).toFixed(1)}`).join("");
    if (d) svg.append(s("path", { d, fill: "none", stroke: se.color, "stroke-width": 2 }));
  });
  const leyenda = h("div", { clase: "leyenda" }, series.map((se) => {
    const muestra = h("i"); muestra.style.background = se.color; // CSSOM: permitido por la CSP
    return h("span", {}, muestra, se.nombre);
  }));
  return h("figure", {}, svg, leyenda);
}

/* ---------- simulación ---------- */
async function simular(cambios, titulo) {
  const dlg = document.getElementById("dialogo-simulacion");
  document.getElementById("titulo-simulacion").textContent = titulo || "Simulación de cambio";
  limpiar("simulacion-contenido", h("div", { clase: "esqueleto esqueleto--bloque", "aria-hidden": "true" }));
  if (!dlg.open) dlg.showModal();
  try {
    const r = await api("/api/simular", { method: "POST", json: { cambios } });
    limpiar("simulacion-contenido",
      ...r.avisos.map((a) => h("div", { clase: "aviso-caja", texto: a })),
      h("div", { clase: "kpis" }, kpi("Valor total", mxn(r.valor_total)), kpi("Efectivo resultante", mxn(r.efectivo_resultante), signo(r.efectivo_resultante)),
        kpi("Costo (comisión + IVA + spread)", mxn(r.costo_total, true)), kpi("Emisoras", String(r.emisoras))),
      tabla([{ t: "Operación", f: (f) => f.operacion }, { t: "Instrumento", f: (f) => f.clave_operable },
        { t: "Títulos", f: (f) => f.titulos, num: true }, { t: "Precio (fecha)", f: (f) => `${mxn(f.precio_mxn, true)} (${f.fecha_precio || "—"})`, num: true },
        { t: "Importe", f: (f) => mxn(f.importe), num: true }, { t: "Costo", f: (f) => mxn(f.costo, true), num: true }],
      r.operaciones, { caption: "Títulos enteros con el último precio disponible" }),
      r.cumplimiento_reto.length ? h("ul", {}, r.cumplimiento_reto.map((c) => h("li", {}, h("span", { clase: c.cumple ? "cumple" : "no-cumple", texto: c.cumple ? "Cumple: " : "No cumple: " }), `${c.regla} (${c.detalle})`))) : null,
      h("p", { clase: "suave", texto: r.nota }));
  } catch (e) { limpiar("simulacion-contenido", errorCaja(e)); }
}
document.getElementById("cerrar-simulacion").addEventListener("click", () => document.getElementById("dialogo-simulacion").close());
const opsDeCambios = (p) => p.cambios.filas.filter((f) => f.accion !== "mantener").map((f) => ({ id: f.id, monto: f.monto_mxn }));

/* ---------- resumen ---------- */
function barrasPesos(pesos) {
  return h("ul", { clase: "barras" }, pesos.map((p) => h("li", {},
    h("span", { clase: "nombre-corto", title: p.id, texto: p.clave_operable || p.id }), barraPct(p.peso, 0.4),
    h("span", { clase: "num", texto: pct(p.peso) }))));
}
function tarjetaPropuesta(p, mejor) {
  if (!p) return h("div", { clase: "tarjeta" }, h("h2", { texto: "Sin calcular" }), h("p", { clase: "vacio", texto: "El motor la calculará en el próximo ciclo." }));
  const cuerpo = [];
  (p.avisos || []).forEach((a) => cuerpo.push(h("div", { clase: "aviso-caja", texto: a })));
  if (p.estado === "suspendida") {
    cuerpo.push(h("div", { clase: "error-caja" }, h("strong", { texto: "Suspendida. " }), p.motivos.join(" ")));
  } else {
    const m = (p.comparacion || [])[0] || {}, me = p.mejora_esperada || {};
    cuerpo.push(h("div", { clase: "puntuacion" }, h("span", { clase: "numero", texto: p.puntuacion.total.toFixed(0) }), h("span", { clase: "de", texto: "/ 100 puntos" })));
    cuerpo.push(h("div", { clase: "kpis" },
      kpi(`Esperado a ${me.horizonte_sesiones || "—"} sesiones`, pct(me.esperado_propuesta), signo(me.esperado_propuesta)),
      kpi("Volatilidad anual (fuera de muestra)", pct(m.volatilidad)), kpi("Caída máxima (fuera de muestra)", pct(m.max_caida), "negativo"),
      kpi("Escenario adverso (p10)", pct(p.escenarios && p.escenarios.adverso_p10), "negativo")));
    if ((p.cumplimiento_reto || []).length) cuerpo.push(h("p", { clase: "suave" }, "Reglas del Reto: ",
      ...p.cumplimiento_reto.map((c) => h("span", { clase: c.cumple ? "cumple" : "no-cumple", texto: `${c.cumple ? "✓" : "✗"} ${c.detalle}  ` }))));
    cuerpo.push(h("h3", { texto: "Mayores pesos" }), barrasPesos(p.pesos.slice(0, 6)));
    cuerpo.push(h("p", { clase: "suave" }, `Datos al ${p.datos_hasta || "—"} · calculada ${fechaLocal(p.calculado_en)} · ${p.n_elegibles} elegibles`));
  }
  return h("article", { clase: `tarjeta${mejor ? " tarjeta--destacada" : ""}`, "aria-label": p.nombre },
    h("h2", {}, p.universo_nombre || p.nombre, " ", chip(p.estado)), h("p", { clase: "suave", texto: `${p.lente_nombre || ""}${mejor ? " · mayor puntuación con sus criterios" : ""}` }),
    ...cuerpo,
    h("button", { type: "button", clase: "boton boton--texto", onclick: () => { estado.universoSel = p.tipo; estado.lenteSel = p.lente; irA("tab-propuestas"); pintarDetalle(); } }, "Ver detalle y cambios"));
}
function tarjetaReto(r, c) {
  if (!r || !r.activo) return null;
  const pend = (r.tareas || []).filter((t) => !t.hecha);
  return h("section", { clase: "tarjeta", "aria-labelledby": "t-reto" },
    h("h2", { id: "t-reto", texto: r.nombre }),
    h("div", { clase: "reto" },
      h("div", {}, h("span", { clase: "suave", texto: `Etapa: ${ETAPAS[r.etapa] || r.etapa}` }), h("br"),
        h("span", { clase: "cuenta", texto: String(r.sesiones_restantes) }), h("span", { clase: "suave", texto: " sesiones hasta el cierre (13 nov, 15:00)" })),
      h("div", {}, h("span", { clase: "suave", texto: "Su cartera frente a las reglas" }),
        c && c.cumplimiento_reto && c.n_operaciones ? h("ul", { clase: "tareas" }, c.cumplimiento_reto.map((x) => h("li", {}, h("span", { clase: x.cumple ? "cumple" : "no-cumple", texto: x.cumple ? "✓ " : "✗ " }), `${x.regla} — ${x.detalle}`)))
          : h("p", { clase: "vacio", texto: "Registre su portafolio para verificar las reglas." })),
      h("div", {}, h("span", { clase: "suave", texto: `Pendientes (${pend.length})` }),
        h("ul", { clase: "tareas" }, pend.slice(0, 3).map((t) => h("li", { texto: t.texto }))),
        h("button", { type: "button", clase: "boton boton--texto", onclick: () => irA("tab-perfil") }, "Ver todas"))),
    h("p", { clase: "suave", texto: "La calificación del Reto también cuenta el avance en Acelera Academy (track semanal y quiz diario); esta terminal solo cubre el portafolio." }));
}
async function pintarResumen() {
  const p = estado.propuestas, c = estado.cartera, d = estado.datos;
  const cont = [];
  if (d && d.alertas_pendientes) {
    let lista = [];
    try { lista = (await api("/api/alertas?limite=5")).alertas.filter((a) => a.estado === "nueva"); } catch { /* sin detalle */ }
    cont.push(h("section", { clase: "franja-alertas", "aria-label": "Alertas nuevas" },
      h("strong", { texto: `${d.alertas_pendientes} alerta(s) nueva(s). ` }), lista.slice(0, 3).map((a) => a.titulo).join(" · "), " ",
      h("button", { type: "button", clase: "boton boton--texto", onclick: () => irA("tab-alertas") }, "Revisar alertas")));
  }
  const tr = tarjetaReto(estado.reto, c);
  const tc = h("section", { clase: "tarjeta", "aria-labelledby": "t-cartera" }, h("h2", { id: "t-cartera", texto: "Cartera actual" }));
  if (!c) tc.append(h("div", { clase: "esqueleto esqueleto--bloque", "aria-hidden": "true" }));
  else if (!c.n_operaciones) tc.append(h("p", { clase: "vacio", texto: "Sin operaciones registradas. Regístrelas o impórtelas en «Mi cartera» para comparar las propuestas con su posición real." }));
  else {
    const ipc = (c.referencias || [])[0];
    tc.append(h("div", { clase: "kpis" },
      kpi("Valor total", mxn(c.valor_total)), kpi("Resultado total", mxn(c.resultado_total), signo(c.resultado_total)),
      kpi("Rend. ponderado por tiempo", pct(c.twr_acumulado), signo(c.twr_acumulado)), kpi("Caída máxima", pct(c.max_caida), "negativo"),
      kpi(ipc ? ipc.nombre : "Referencia", pct(ipc && ipc.rend_acumulado), signo(ipc && ipc.rend_acumulado))),
    h("p", { clase: "suave" }, "Precios: ", chip(c.vigencia), c.sin_precio.length ? ` · ${c.sin_precio.length} posición(es) sin precio: total incompleto` : ""));
  }
  cont.push(h("div", { clase: "rejilla" }, tr, tc));
  if (!p) cont.push(h("div", { clase: "tarjeta esqueleto esqueleto--bloque", "aria-hidden": "true" }));
  else {
    const L = estado.lenteResumen;
    const cands = ["acciones", "mixta"].map((u) => p[`${u}_${L}`]);
    const puntuadas = cands.filter((x) => x && x.puntuacion && x.estado !== "suspendida");
    const mejor = puntuadas.sort((a, b) => b.puntuacion.total - a.puntuacion.total)[0];
    const sel = h("div", { clase: "segmentado", role: "radiogroup", "aria-label": "Lente de comparación" },
      Object.entries(LENTES).map(([k, t]) => h("button", { type: "button", role: "radio", "aria-checked": String(k === L), onclick: () => { estado.lenteResumen = k; pintarResumen(); } }, t)));
    cont.push(h("div", { clase: "selectores" }, h("h2", { texto: "Comparación de propuestas" }), sel),
      h("div", { clase: "rejilla" }, cands.map((x) => tarjetaPropuesta(x, x && mejor && x.clave === mejor.clave))));
    if (estado.clasificacion.length) {
      cont.push(tabla([{ t: "#", f: (f) => f.posicion || "—" }, { t: "Alternativa", f: (f) => f.alternativa },
        { t: "Puntuación", f: (f) => (f.puntuacion === null ? "—" : f.puntuacion.toFixed(1)), num: true },
        { t: "Estado", f: (f) => chip(f.estado) }, { t: "Motivo", f: (f) => f.motivo || "" }],
      estado.clasificacion, { caption: "Clasificación según los criterios del perfil: orden relativo, no una certeza ni una promesa de rendimiento." }));
    }
    if (mejor) {
      cont.push(h("div", { clase: "rejilla" },
        h("section", { clase: "tarjeta" }, h("h2", { texto: "Riesgos principales" }), h("p", { clase: "suave", texto: mejor.nombre }), h("ul", {}, mejor.riesgos.map((r) => h("li", { texto: r })))),
        h("section", { clase: "tarjeta" }, h("h2", { texto: "Cambios sugeridos frente a su cartera" }), resumenCambios(mejor))));
    }
  }
  limpiar("resumen-contenido", ...cont);
}
function resumenCambios(p) {
  const c = p.cambios;
  const ops = c.filas.filter((f) => f.accion !== "mantener");
  if (!ops.length) return h("p", { clase: "vacio", texto: "Ningún cambio supera la banda de rebalanceo." });
  return h("div", {}, h("p", {}, `${ops.length} operaciones sobre ${mxn(c.base_mxn)}. Costo estimado ${mxn(c.costo_total)} + impuestos ${mxn(c.impuesto_estimado)}.`),
    h("ul", {}, ops.slice(0, 6).map((f) => h("li", {}, `${f.accion === "comprar" ? "Comprar" : "Vender"} ${f.clave_operable}: `, h("span", { clase: "cifra", texto: mxn(Math.abs(f.monto_mxn)) }), ` (${f.delta_pp > 0 ? "+" : ""}${f.delta_pp.toFixed(1)} pp)`))),
    h("button", { type: "button", clase: "boton boton--secundario", onclick: () => simular(opsDeCambios(p), `Simular: ${p.nombre}`) }, "Simular estos cambios"),
    h("p", { clase: "suave", texto: "Simulación informativa: las órdenes se capturan en el simulador del Reto." }));
}

/* ---------- detalle de propuesta ---------- */
function pintarDetalle() {
  segmentado("selector-universo", estado.universoSel, (v) => { estado.universoSel = v; pintarDetalle(); });
  segmentado("selector-lente", estado.lenteSel, (v) => { estado.lenteSel = v; pintarDetalle(); });
  if (!estado.propuestas) return;
  const p = estado.propuestas[`${estado.universoSel}_${estado.lenteSel}`];
  if (!p) return limpiar("propuesta-detalle", h("p", { clase: "vacio", texto: "Sin propuesta calculada todavía; el motor la calculará en el próximo ciclo." }));
  const out = [];
  (p.avisos || []).forEach((a) => out.push(h("div", { clase: "aviso-caja", texto: a })));
  if (p.modo === "demo") out.push(h("div", { clase: "aviso-caja", texto: "Demostración con datos sintéticos: no utilizar para decisiones." }));
  if (p.estado === "suspendida") {
    out.push(h("div", { clase: "error-caja" }, h("strong", { texto: "Propuesta suspendida. " }), p.motivos.join(" ")));
  } else {
    const me = p.mejora_esperada || {};
    out.push(h("p", { clase: "info-caja" }, p.aviso));
    out.push(h("div", { clase: "rejilla" },
      h("section", { clase: "tarjeta" }, h("h2", { texto: "Puntuación y motivos" }),
        h("div", { clase: "puntuacion" }, h("span", { clase: "numero", texto: p.puntuacion.total.toFixed(0) }), h("span", { clase: "de", texto: "/ 100" })),
        h("ul", { clase: "criterios" }, p.puntuacion.criterios.map((c) => h("li", {},
          h("span", { texto: `${c.criterio.replace("_", " ")} (${pct(c.peso)})` }), barraPct(c.puntos, 100),
          h("span", { clase: "num", texto: c.puntos.toFixed(0) }), h("span", { clase: "explicacion", texto: c.explicacion }))))),
      h("section", { clase: "tarjeta" }, h("h2", { texto: "Rendimiento esperado y Reto" }),
        h("div", { clase: "kpis" }, kpi(`Esperado (${me.horizonte_sesiones} sesiones)`, pct(me.esperado_propuesta), signo(me.esperado_propuesta)),
          kpi("Cartera actual (mismo μ)", pct(me.esperado_actual)), kpi("Mejora neta de costos", pct(me.neta), signo(me.neta))),
        h("p", { clase: "suave", texto: `${me.nota || ""} Horizonte: ${p.reproducibilidad.horizonte_origen}.` }),
        (p.cumplimiento_reto || []).length ? h("ul", {}, p.cumplimiento_reto.map((c) => h("li", {}, h("span", { clase: c.cumple ? "cumple" : "no-cumple", texto: c.cumple ? "Cumple: " : "No cumple: " }), `${c.regla} (${c.detalle})`))) : null),
      h("section", { clase: "tarjeta" }, h("h2", { texto: "Escenarios" }), escenarios(p.escenarios))));
    out.push(h("h2", { texto: "Pesos, montos, títulos y razones" }),
      tabla([
        { t: "Instrumento", f: (f) => h("span", {}, h("strong", { texto: f.clave_operable }), h("br"), h("span", { clase: "suave", texto: `${CLASES[f.clase] || f.clase} · ${f.id}` })) },
        { t: "Peso", f: (f) => pct(f.peso), num: true }, { t: "Monto", f: (f) => mxn(f.monto_objetivo), num: true },
        { t: "Títulos", f: (f) => (f.titulos === null ? "—" : f.titulos), num: true },
        { t: "Precio MXN (fecha)", f: (f) => h("span", {}, mxn(f.precio_mxn, true), h("br"), h("span", { clase: "suave", texto: f.fecha_precio || "" })), num: true },
        { t: "Datos", f: (f) => chip(f.vigencia) },
        { t: "Razones", f: (f) => h("ul", { clase: "lista-motivos" }, f.motivos.map((m) => h("li", { texto: m }))) }],
      p.pesos, { caption: `Capital ${mxn(p.capital)} · efectivo residual por redondeo ${mxn(p.efectivo_residual)}. Precios de cierre, no en tiempo real.` }));
    out.push(h("h2", { texto: "Comparación fuera de muestra" }), tabla([
      { t: "Cartera", f: (f) => f.cartera }, { t: "Rend. anual", f: (f) => pct(f.rend_anual), num: true },
      { t: "Volatilidad", f: (f) => pct(f.volatilidad), num: true }, { t: "Sharpe", f: (f) => (vacio(f.sharpe) ? "—" : f.sharpe.toFixed(2)), num: true },
      { t: "Caída máx.", f: (f) => pct(f.max_caida), num: true }, { t: "Periodo", f: (f) => (f.desde ? `${f.desde} → ${f.hasta}` : "—") }],
    p.comparacion, { caption: "Walk-forward sin información futura; incluye costos de rotación y banda de rebalanceo." }));
    out.push(h("h2", { texto: "Cambios sugeridos frente a sus posiciones" }), tabla([
      { t: "Instrumento", f: (f) => f.clave_operable }, { t: "Actual", f: (f) => pct(f.peso_actual), num: true },
      { t: "Objetivo", f: (f) => pct(f.peso_objetivo), num: true }, { t: "Δ pp", f: (f) => f.delta_pp.toFixed(1), num: true },
      { t: "Monto", f: (f) => mxn(f.monto_mxn), num: true }, { t: "Acción", f: (f) => f.accion },
      { t: "Costo + impuesto", f: (f) => mxn(f.costo_estimado + f.impuesto_estimado), num: true }, { t: "Nota", f: (f) => f.nota }],
    p.cambios.filas, { caption: `Banda de no-rebalanceo activa. Costo total ${mxn(p.cambios.costo_total)}; impuesto estimado ${mxn(p.cambios.impuesto_estimado)}.` }));
    if (opsDeCambios(p).length) out.push(h("button", { type: "button", clase: "boton boton--secundario", onclick: () => simular(opsDeCambios(p), `Simular: ${p.nombre}`) }, "Simular estos cambios"));
    out.push(h("details", {}, h("summary", { texto: "Riesgos" }), h("ul", {}, p.riesgos.map((r) => h("li", { texto: r })))));
    out.push(h("details", {}, h("summary", { texto: `Sensibilidad (estabilidad ${pct(p.estabilidad)})` }), tabla([
      { t: "Variante", f: (f) => f.variante }, { t: "Cambio de pesos", f: (f) => (f.error ? f.error : pct(f.cambio_pesos)), num: true },
      { t: "Principales", f: (f) => (f.top || []).map((t) => `${t.id} ${pct(t.peso)}`).join(" · ") }], p.sensibilidad)));
  }
  out.push(h("details", {}, h("summary", { texto: `Instrumentos excluidos (${(p.excluidos || []).length})` }),
    tabla([{ t: "Instrumento", f: (f) => f.id }, { t: "Motivo", f: (f) => f.motivo }], p.excluidos || [])));
  if (p.reproducibilidad) {
    const r = p.reproducibilidad;
    out.push(h("details", {}, h("summary", { texto: "Reproducibilidad: objetivo, restricciones y datos" }),
      h("dl", { clase: "glosario" },
        ...[["Función objetivo", r.funcion_objetivo], ["Lente", `${LENTES[r.lente]} · λ = ${r.aversion_riesgo_lambda}`],
          ["Horizonte", `${r.horizonte_anios} años (${r.horizonte_origen})`], ["Precios", r.precios],
          ["Restricciones", r.restricciones.join(" · ")],
          ["Ventana de estimación", `${r.ventana_estimacion.desde} → ${r.ventana_estimacion.hasta} (${r.ventana_estimacion.sesiones} sesiones)`],
          ["Walk-forward", `${r.walk_forward.entrenamiento} / ${r.walk_forward.prueba}, ${r.walk_forward.ventanas} ventanas`],
          ["Escenario", `${r.escenario} (${JSON.stringify(r.ajuste_escenario)})`], ["Huella de datos", r.huella_datos],
          ["Versiones", Object.entries(r.versiones).map(([k, v]) => `${k} ${v}`).join(", ")]].flatMap(([a, b]) => [h("dt", { texto: a }), h("dd", { texto: String(b) })]))));
  }
  limpiar("propuesta-detalle", ...out);
}
function escenarios(e) {
  if (!e) return h("p", { clase: "vacio", texto: "—" });
  return h("div", {},
    h("div", { clase: "kpis" }, kpi("Favorable (p90)", pct(e.favorable_p90), "positivo"), kpi("Central (p50)", pct(e.central_p50), signo(e.central_p50)), kpi("Adverso (p10)", pct(e.adverso_p10), signo(e.adverso_p10))),
    h("div", { clase: "kpis" }, kpi("Peor mes histórico", pct(e.peor_mes_historico), "negativo"), kpi("Peor trimestre", pct(e.peor_trimestre_historico), "negativo"), kpi("Caída máx. histórica", pct(e.max_caida_historica), "negativo")),
    h("p", { clase: "suave" }, `Estrés hipotético (${e.estres_hipotetico.supuesto}): ${pct(e.estres_hipotetico.impacto)}.`),
    h("p", { clase: "suave", texto: `Horizonte ${e.horizonte_anios.toFixed(2)} años. ${e.nota}` }));
}

/* ---------- alertas ---------- */
async function cargarAlertas() {
  try {
    const d = await api("/api/alertas?limite=200");
    const c = d.configuracion;
    document.getElementById("alertas-config").textContent = `Deriva ≥ ${c.deriva_pp} pp (rearme < ${c.deriva_rearme_pp} pp) con mejora neta ≥ ${pct(c.mejora_neta_min)} · stop ${pct(c.stop_loss)} · toma de utilidad ${pct(c.take_profit)} · caída desde máximo ${pct(c.caida_desde_maximo)} · enfriamiento ${c.enfriamiento_horas} h · ${c.silenciar_fuera_de_horario ? "silencio fuera de horario BMV" : "notifica 24 h"}.`;
    if (!d.alertas.length) return limpiar("alertas-contenido", h("p", { clase: "vacio", texto: "Sin alertas. El motor evalúa las reglas en cada ciclo." }));
    limpiar("alertas-contenido", h("ul", { clase: "alertas" }, d.alertas.map((a) => h("li", { clase: `alerta alerta--${a.severidad}${a.estado !== "nueva" ? " alerta--vista" : ""}` },
      h("h3", { texto: a.titulo }),
      h("div", { clase: "meta" }, `${fechaLocal(a.ts)} · ${a.fuente || "—"} · ${a.regla.replace("_", " ")} · ${a.estado}`, a.notificada === "silenciada_fuera_de_horario" ? " · no notificada (fuera de horario)" : ""),
      h("p", { texto: a.motivo }), a.accion ? h("p", {}, h("strong", { texto: "Acción sugerida: " }), a.accion) : null,
      a.datos && a.datos.enlace ? h("p", {}, externo(a.datos.enlace, "Ver fuente")) : null,
      h("div", { clase: "acciones" },
        a.simulacion ? h("button", { type: "button", clase: "boton boton--secundario", onclick: () => simular(a.simulacion, a.titulo) }, "Simular cambio") : null,
        a.estado === "nueva" ? h("button", { type: "button", clase: "boton boton--secundario", onclick: () => marcarAlerta(a.id, "vista") }, "Marcar como vista") : null,
        a.estado !== "descartada" ? h("button", { type: "button", clase: "boton boton--texto", onclick: () => marcarAlerta(a.id, "descartada") }, "Descartar") : null)))));
  } catch (e) { limpiar("alertas-contenido", errorCaja(e)); }
}
async function marcarAlerta(id, est) {
  try { await api(`/api/alertas/${id}`, { method: "POST", json: { estado: est } }); await cargarAlertas(); cargarEstado(); }
  catch (e) { notificar(e.message); }
}

/* ---------- cartera ---------- */
async function cargarCartera() {
  try {
    const [c, tx] = await Promise.all([api("/api/cartera"), api("/api/transacciones?anuladas=true")]);
    estado.cartera = c;
    pintarCartera(c, tx.transacciones);
  } catch (e) { limpiar("cartera-contenido", errorCaja(e)); }
}
const COLORES = ["var(--serie-1)", "var(--serie-2)", "var(--sin-datos)", "var(--sintetico)"];
function pintarCartera(c, txs) {
  const out = [];
  if (!c.n_operaciones) {
    out.push(h("div", { clase: "info-caja", texto: "Sin operaciones. Registre su aportación de 1,000,000 actipesos y sus compras, o importe un archivo. La terminal no deduce posiciones del PDF." }));
  } else {
    out.push(h("div", { clase: "kpis" },
      kpi("Valor total", mxn(c.valor_total)), kpi("Efectivo", mxn(c.efectivo)), kpi("Aportación neta", mxn(c.aportacion_neta)),
      kpi("Realizado", mxn(c.realizado), signo(c.realizado)), kpi("No realizado", mxn(c.no_realizado), signo(c.no_realizado)),
      kpi("Dividendos netos", mxn(c.dividendos)), kpi("Comisiones con IVA", mxn(c.comisiones)), kpi("Caída máxima", pct(c.max_caida), "negativo"),
      kpi("Rend. ponderado por tiempo", pct(c.twr_acumulado), signo(c.twr_acumulado)), kpi("TIR anual (dinero)", pct(c.tir_anual))));
    if (c.sin_precio.length) out.push(h("div", { clase: "aviso-caja", texto: `Sin precio para ${c.sin_precio.join(", ")}: valor total incompleto.` }));
    const hist = c.historia || [];
    const refs = Object.keys((hist[0] || {}).referencias || {});
    out.push(h("h2", { texto: "Evolución frente a referencias" }), grafica([
      { nombre: "Cartera (ponderado por tiempo)", color: COLORES[0], datos: hist.map((p) => ({ x: p.fecha, y: p.twr })) },
      ...refs.map((n, i) => ({ nombre: n, color: COLORES[i + 1], datos: hist.map((p) => ({ x: p.fecha, y: p.referencias[n] })) }))],
    { etiqueta: "Rendimiento acumulado de la cartera frente a IPC, S&P 500 y 60/40" }),
    tabla([{ t: "Referencia", f: (f) => f.nombre }, { t: "Rend. acumulado", f: (f) => pct(f.rend_acumulado), num: true }, { t: "Nota", f: (f) => f.nota || f.id }], c.referencias || []));
    out.push(h("h2", { texto: "Caída desde máximo" }), grafica([{ nombre: "Caída de la cartera", color: "var(--negativo)", datos: hist.map((p) => ({ x: p.fecha, y: p.caida })) }], { alto: 140, etiqueta: "Caída desde el máximo de la cartera" }));
    if ((c.cumplimiento_reto || []).length) out.push(h("p", {}, "Reglas del Reto: ", ...c.cumplimiento_reto.map((x) => h("span", { clase: x.cumple ? "cumple" : "no-cumple", texto: `${x.cumple ? "✓" : "✗"} ${x.regla} (${x.detalle})  ` }))));
    out.push(h("h2", { texto: "Posiciones" }), tabla([
      { t: "Instrumento", f: (f) => f.clave_operable || f.instrumento_id }, { t: "Cantidad", f: (f) => num(f.cantidad), num: true },
      { t: "Costo prom.", f: (f) => mxn(f.costo_promedio, true), num: true }, { t: "Precio", f: (f) => mxn(f.precio_mxn, true), num: true },
      { t: "Valor", f: (f) => mxn(f.valor_mxn), num: true }, { t: "Peso", f: (f) => pct(f.peso), num: true },
      { t: "No realizado", f: (f) => h("span", { clase: signo(f.no_realizado), texto: `${mxn(f.no_realizado)} (${pct(f.no_realizado_pct)})` }), num: true },
      { t: "Realizado", f: (f) => mxn(f.realizado), num: true },
      { t: "Dato", f: (f) => h("span", {}, chip(f.vigencia, f.etiqueta_vigencia), h("br"), h("span", { clase: "suave", texto: `${f.fecha_precio || ""} ${f.proveedor || ""}` })) },
      { t: "", f: (f) => h("a", { href: `/grafica/${encodeURIComponent(f.instrumento_id)}`, target: "_blank", rel: "noopener", texto: "Gráfica" }) }],
    c.posiciones, { caption: "Costo promedio ponderado; comisiones de compra incluidas en el costo." }));
  }
  out.push(h("h2", { texto: "Operaciones registradas" }), tabla([
    { t: "#", f: (f) => f.id, num: true }, { t: "Fecha", f: (f) => f.fecha }, { t: "Tipo", f: (f) => f.tipo },
    { t: "Instrumento", f: (f) => f.instrumento_id || "" }, { t: "Cantidad", f: (f) => (f.cantidad ? num(f.cantidad) : ""), num: true },
    { t: "Precio", f: (f) => (f.precio ? num(f.precio) : ""), num: true }, { t: "Monto", f: (f) => (f.monto ? num(f.monto) : ""), num: true },
    { t: "Comisión", f: (f) => num(f.comision), num: true }, { t: "Origen", f: (f) => f.origen },
    { t: "Estado", f: (f) => (f.anulada ? chip("vencido", "Anulada") : chip("vigente", "Activa")) },
    { t: "", f: (f) => (f.anulada ? "" : h("span", {},
      h("button", { type: "button", clase: "boton boton--texto", onclick: () => anularOperacion(f) }, "Anular"),
      h("button", { type: "button", clase: "boton boton--texto", onclick: () => corregirOperacion(f) }, "Corregir"))) }],
  txs.slice().reverse(), { vacio: "Sin operaciones." }));
  out.push(h("details", { ontoggle: (ev) => { if (ev.target.open) cargarAuditoria(ev.target); } }, h("summary", { texto: "Registro de auditoría" }), h("p", { clase: "cargando", texto: "Cargando…" })));
  limpiar("cartera-contenido", ...out);
}
async function cargarAuditoria(det) {
  try {
    const a = await api("/api/auditoria?limite=200");
    det.replaceChildren(det.querySelector("summary"), tabla([
      { t: "Fecha", f: (f) => fechaLocal(f.ts) }, { t: "Entidad", f: (f) => `${f.entidad} ${f.entidad_id || ""}` },
      { t: "Acción", f: (f) => f.accion }, { t: "Motivo", f: (f) => f.motivo || "" }], a.eventos));
  } catch (e) { det.append(errorCaja(e)); }
}
async function anularOperacion(f) {
  const motivo = window.prompt(`Motivo para anular la operación #${f.id} (queda en auditoría):`);
  if (motivo === null) return;
  try { await api(`/api/transacciones/${f.id}/anular`, { method: "POST", json: { motivo } }); notificar("Operación anulada; las propuestas se recalculan solas."); cargarCartera(); }
  catch (e) { notificar(e.errores ? e.errores.join(" ") : e.message); }
}
function corregirOperacion(f) {
  const form = document.getElementById("form-operacion");
  for (const k of ["fecha", "tipo", "instrumento_id", "cantidad", "precio", "monto", "comision", "impuesto", "moneda", "tipo_cambio", "nota"]) {
    if (form.elements[k]) form.elements[k].value = f[k] ?? "";
  }
  form.dataset.corrige = f.id;
  form.querySelector('button[type="submit"]').textContent = `Guardar corrección de #${f.id}`;
  ajustarCampos();
  form.scrollIntoView({ behavior: "smooth", block: "start" });
  form.elements.fecha.focus();
}
const CAMPOS_POR_TIPO = {
  aportacion: ["monto"], retiro: ["monto"], comision: ["monto"], impuesto: ["monto"],
  compra: ["instrumento", "cantidad", "precio", "comision", "impuesto"], venta: ["instrumento", "cantidad", "precio", "comision", "impuesto"],
  dividendo: ["instrumento", "monto", "impuesto"], split: ["instrumento", "cantidad"],
};
function ajustarCampos() {
  const form = document.getElementById("form-operacion");
  const visibles = new Set(CAMPOS_POR_TIPO[form.elements.tipo.value] || []);
  if (form.elements.moneda.value === "USD") visibles.add("tipo_cambio");
  form.querySelectorAll("label[data-para]").forEach((l) => { l.hidden = !visibles.has(l.dataset.para); });
  const cant = Number(form.elements.cantidad.value), px = Number(form.elements.precio.value);
  const r = estado.reto;
  document.getElementById("ayuda-comision").textContent = r && r.activo && r.costo_operacion && cant > 0 && px > 0 && ["compra", "venta"].includes(form.elements.tipo.value)
    ? `Comisión del simulador (0.10 % + IVA): ${mxn(cant * px * r.costo_operacion, true)}` : "";
}
["tipo", "cantidad", "precio"].forEach((k) => document.getElementById("form-operacion").elements[k].addEventListener("input", ajustarCampos));
document.getElementById("form-operacion").elements.moneda.addEventListener("change", (ev) => {
  if (ev.target.value === "MXN") document.getElementById("form-operacion").elements.tipo_cambio.value = "1";
  ajustarCampos();
});
document.getElementById("form-operacion").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const form = ev.target, errores = document.getElementById("errores-operacion");
  const datos = Object.fromEntries(new FormData(form).entries());
  if (!new Set(CAMPOS_POR_TIPO[datos.tipo] || []).has("instrumento")) datos.instrumento_id = "";
  errores.replaceChildren();
  form.querySelectorAll("[aria-invalid]").forEach((i) => i.removeAttribute("aria-invalid"));
  const boton = form.querySelector('button[type="submit"]');
  ocupado([boton], true);
  try {
    if (form.dataset.corrige) {
      const motivo = window.prompt("Motivo de la corrección (queda en auditoría):");
      if (!motivo) { ocupado([boton], false); return; }
      await api(`/api/transacciones/${form.dataset.corrige}/corregir`, { method: "POST", json: { ...datos, motivo } });
      delete form.dataset.corrige; boton.textContent = "Guardar operación";
      notificar("Corrección guardada; el original queda anulado y auditado.");
    } else {
      const r = await api("/api/transacciones", { method: "POST", json: datos });
      notificar(r.id ? "Operación guardada; las propuestas se recalculan solas." : "Operación duplicada: ya existía.");
    }
    form.reset(); form.elements.fecha.value = new Date().toISOString().slice(0, 10); ajustarCampos(); cargarCartera();
  } catch (e) {
    const lista = e.errores || [e.message];
    errores.append(h("strong", { texto: "Revise los datos:" }), h("ul", {}, lista.map((m) => h("li", { texto: m }))));
    lista.forEach((m) => { const campo = form.elements[m.split(":")[0]]; if (campo) campo.setAttribute("aria-invalid", "true"); });
    errores.setAttribute("tabindex", "-1"); errores.focus();
  } finally { ocupado([boton], false); }
});

/* importación con vista previa */
document.getElementById("form-importar").elements.tipo.addEventListener("change", (ev) => {
  document.getElementById("enlace-plantilla").href = `/api/plantilla/${ev.target.value}`;
});
async function enviarImportacion(form, confirmar) {
  const fd = new FormData(form);
  fd.set("confirmar", confirmar ? "si" : "no");
  const r = await fetch("/api/importar", { method: "POST", body: fd, headers: { "X-CSRF-Token": CSRF } });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.error || (d.errores || []).join(" ") || `Error ${r.status}`);
  return d;
}
document.getElementById("form-importar").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const form = ev.target, salida = document.getElementById("resultado-importacion");
  const archivo = form.elements.archivo.files[0];
  if (!archivo) { salida.replaceChildren(errorCaja(new Error("Seleccione un archivo .csv"))); return; }
  if (archivo.size > 1_000_000) { salida.replaceChildren(errorCaja(new Error("El archivo supera 1 MB"))); return; }
  const boton = form.querySelector('button[type="submit"]');
  ocupado([boton], true);
  salida.replaceChildren(h("p", { clase: "cargando", texto: "Validando…" }));
  try {
    const rep = await enviarImportacion(form, false);
    const esUniverso = rep.tipo === "universo";
    const nodos = [h("p", {}, `${rep.filas} filas: ${rep.aceptables ?? 0} válidas, ${rep.duplicadas} duplicadas, ${rep.rechazadas} ${esUniverso ? "no reconocidas" : "con errores"}.`)];
    const problemas = rep.detalle.filter((d) => d.estado !== "aceptada");
    if (problemas.length) nodos.push(tabla([{ t: "Línea", f: (f) => f.linea, num: true }, { t: "Estado", f: (f) => f.estado }, { t: "Detalle", f: (f) => f.errores.join("; ") }], problemas.slice(0, 200)));
    if ((esUniverso || !rep.rechazadas) && rep.aceptables > 0) {
      nodos.push(h("button", { type: "button", clase: "boton boton--primario", onclick: async (e2) => {
        ocupado([e2.target], true);
        try { const fin = await enviarImportacion(form, true); notificar(`Importación confirmada: ${fin.aceptadas} registros.`); salida.replaceChildren(h("p", { texto: `Importadas ${fin.aceptadas} filas. Archivo original conservado. Las propuestas se recalculan solas.` })); form.reset(); cargarCartera(); }
        catch (err) { salida.append(errorCaja(err)); ocupado([e2.target], false); }
      } }, `Confirmar importación de ${rep.aceptables} filas`));
    } else if (rep.rechazadas) nodos.push(h("p", { clase: "error-caja", texto: "Corrija las filas con errores; no se importa nada parcialmente." }));
    salida.replaceChildren(...nodos);
  } catch (e) { salida.replaceChildren(errorCaja(e)); } finally { ocupado([boton], false); }
});

/* ---------- mercado ---------- */
async function cargarMercado() {
  try {
    const d = await api("/api/mercado");
    const insiderEstado = (estado.datos && estado.datos.proveedores || []).find((p) => p.proveedor === "sec_edgar");
    limpiar("mercado-contenido",
      h("h2", { texto: "Calendario macro (USD y MXN, impacto alto y medio)" }),
      tabla([{ t: "Fecha (CDMX)", f: (f) => fechaLocal(f.fecha) }, { t: "País", f: (f) => f.pais }, { t: "Evento", f: (f) => f.titulo },
        { t: "Impacto", f: (f) => chip(f.impacto === "High" ? "vencido" : "retrasado", f.impacto === "High" ? "Alto" : "Medio") },
        { t: "Pronóstico", f: (f) => f.pronostico || "—", num: true }, { t: "Previo", f: (f) => f.previo || "—", num: true }],
      d.macro, { caption: `Fuente: ${d.fuentes.macro}. Semana en curso.`, vacio: "Sin eventos (se actualiza cada hora)." }),
      h("h2", { texto: "Titulares de sus emisoras" }),
      tabla([{ t: "Publicado", f: (f) => fechaLocal(f.publicado) }, { t: "Emisora", f: (f) => f.instrumento_id },
        { t: "Titular", f: (f) => externo(f.enlace, f.titulo) },
        { t: "Impacto", f: (f) => (f.impacto === "alto" ? chip("retrasado", "Alto") : chip("sin_datos", "Normal")) },
        { t: "Sentimiento", f: (f) => h("span", { clase: signo(f.sentimiento), texto: f.sentimiento > 0 ? "Positivo" : f.sentimiento < 0 ? "Negativo" : "Neutro" }) }],
      d.noticias, { caption: `Fuente: ${d.fuentes.noticias}; clasificación por léxico (o LLM local si está configurado). Solo emisoras de EE. UU. en cartera.`, vacio: d.cartera.length ? "Sin titulares recientes." : "Registre posiciones para ver titulares de sus emisoras." }),
      h("h2", { texto: "Operaciones de insiders" }),
      insiderEstado && !insiderEstado.configurado ? h("div", { clase: "aviso-caja", texto: "Requiere configuración: defina SEC_USER_AGENT (nombre y correo de contacto) en .env para consultar SEC EDGAR." }) : null,
      tabla([{ t: "Fecha", f: (f) => f.fecha }, { t: "Emisora", f: (f) => f.instrumento_id }, { t: "Persona", f: (f) => `${f.nombre} (${f.cargo || "—"})` },
        { t: "Tipo", f: (f) => ({ P: "Compra", S: "Venta" }[f.codigo] || f.codigo) }, { t: "Acciones", f: (f) => num(f.acciones), num: true },
        { t: "Valor USD", f: (f) => num(f.valor), num: true }, { t: "", f: (f) => externo(f.enlace, "Formulario 4") }],
      d.insiders, { caption: `Fuente: ${d.fuentes.insiders}.`, vacio: "Sin operaciones de insiders registradas." }));
  } catch (e) { limpiar("mercado-contenido", errorCaja(e)); }
}

/* ---------- universo y proveedores ---------- */
async function cargarUniverso() {
  try {
    if (!estado.universo) estado.universo = (await api("/api/universo")).instrumentos;
    const sel = document.getElementById("filtro-clase");
    if (sel.options.length === 1) [...new Set(estado.universo.map((i) => i.clase))].sort().forEach((c) => sel.append(h("option", { value: c, texto: CLASES[c] || c })));
    pintarUniverso();
    const d = estado.datos || (await api("/api/estado"));
    limpiar("proveedores", h("h2", { texto: "Fuentes" }), tabla([
      { t: "Fuente", f: (f) => f.proveedor }, { t: "Uso", f: (f) => f.descripcion }, { t: "Tipo de dato", f: (f) => f.tipo_dato },
      { t: "Credencial", f: (f) => (f.requiere_credencial ? "Requerida" : "No") },
      { t: "Estado", f: (f) => (f.configurado ? chip("vigente", "Configurado") : chip("sin_datos", f.requiere_credencial ? "Requiere credencial" : "Desactivado")) },
      { t: "Peticiones restantes", f: (f) => (f.peticiones_restantes ?? "—"), num: true },
      { t: "Última corrida", f: (f) => (f.ultima_corrida ? `${fechaLocal(f.ultima_corrida.fin)} · ${f.ultima_corrida.estado} · ${f.ultima_corrida.mensaje || ""}` : "—") },
      { t: "Condiciones", f: (f) => f.uso_permitido }], d.proveedores));
  } catch (e) { limpiar("universo-tabla", errorCaja(e)); }
}
function pintarUniverso() {
  const t = document.getElementById("filtro-texto").value.trim().toLowerCase();
  const c = document.getElementById("filtro-clase").value, v = document.getElementById("filtro-vigencia").value;
  const filas = estado.universo.filter((i) => (!c || i.clase === c) && (!v || i.vigencia === v) &&
    (!t || `${i.id} ${i.clave_operable} ${i.nombre}`.toLowerCase().includes(t)));
  limpiar("universo-tabla", tabla([
    { t: "Instrumento", f: (f) => h("span", {}, h("strong", { texto: f.clave_operable }), h("br"), h("span", { clase: "suave", texto: f.nombre || "" })) },
    { t: "Clase verificada", f: (f) => h("span", {}, CLASES[f.clase] || f.clase, f.secciones_pdf && f.secciones_pdf.includes("ETF") && f.clase !== "etf" ? h("span", { clase: "suave", texto: " (rotulado «ETF's» en el PDF)" }) : "") },
    { t: "Estado", f: (f) => (f.estado === "activo" ? "Activo" : h("span", { title: f.detalle_verificacion, texto: f.estado.replaceAll("_", " ") })) },
    { t: "Simulador", f: (f) => (f.en_simulador === null ? "—" : f.en_simulador ? "Sí" : "No") },
    { t: "Bolsa · moneda · zona", f: (f) => `${f.bolsa_referencia || "—"} · ${f.moneda_referencia || "—"} · ${f.zona_horaria_referencia || "—"}` },
    { t: "Precio (fecha)", f: (f) => (f.precio == null ? "—" : `${num(f.precio)} ${f.moneda} (${f.fecha})`), num: true },
    { t: "Tipo", f: (f) => f.tipo_dato || "—" }, { t: "Proveedor", f: (f) => f.proveedor || "—" },
    { t: "Retraso", f: (f) => (f.retraso_horas == null ? "—" : `${f.retraso_horas} h`), num: true },
    { t: "Vigencia", f: (f) => chip(f.vigencia, f.etiqueta) },
    { t: "", f: (f) => (f.grafica ? h("a", { href: `/grafica/${encodeURIComponent(f.id)}`, target: "_blank", rel: "noopener", texto: "Gráfica" }) : "") }],
  filas.slice(0, 400), { caption: `${filas.length} de ${estado.universo.length} instrumentos. Clase verificada con fuente independiente; la sección del PDF no determina la clase.` }));
}
["filtro-texto", "filtro-clase", "filtro-vigencia"].forEach((id) => document.getElementById(id).addEventListener("input", () => estado.universo && pintarUniverso()));

/* ---------- Reto y perfil ---------- */
async function cargarReto() {
  try {
    const r = await api("/api/reto");
    estado.reto = r;
    if (!r.activo) return limpiar("reto-contenido", h("p", { clase: "vacio", texto: "Reglas del Reto desactivadas (config/reto.yaml → activo: false)." }));
    const reglas = Object.entries(r.reglas || {});
    limpiar("reto-contenido",
      h("div", { clase: "rejilla" },
        h("section", { clase: "tarjeta" }, h("h2", { texto: r.nombre }),
          h("p", {}, `Etapa: ${ETAPAS[r.etapa] || r.etapa} · `, h("span", { clase: "cifra", texto: `${r.sesiones_restantes} sesiones` }), " hasta el cierre"),
          h("ul", {}, [["Semana de práctica", `${r.fechas.practica_inicio.slice(0, 10)} a ${r.fechas.practica_fin.slice(0, 10)}`],
            ["Competencia", `${r.fechas.competencia_inicio.slice(0, 10)} a ${r.fechas.competencia_fin.replace("T", " ").slice(0, 16)} CDMX`],
            ["Inscripción hasta", r.fechas.inscripcion_fin.replace("T", " ").slice(0, 16)], ["Capital", mxn(r.capital) + " actipesos"],
            ["Comisión", `${(r.costo_operacion * 100).toFixed(3)} % por orden (0.10 % + IVA)`],
            ["Horario BMV", r.horario_bmv.map((x) => `${x.apertura}–${x.cierre} (${x.desde} a ${x.hasta})`).join("; ")]].map(([a, b]) => h("li", {}, h("strong", { texto: `${a}: ` }), b))),
          h("p", { clase: "suave" }, "Fuente: ", externo(r.fuente, "bases y mecánica oficiales"), ` (consultado ${r.consultado}).`)),
        h("section", { clase: "tarjeta" }, h("h2", { texto: "Reglas de rendimiento" }),
          tabla([{ t: "Regla", f: (f) => f[0].replaceAll("_", " ") }, { t: "Valor", f: (f) => (f[1] === null ? h("span", { clase: "sin-confirmar", texto: "regla sin confirmar" }) : Array.isArray(f[1]) ? (f[1].join(", ") || "ninguno") : String(f[1])) }], reglas)),
        h("section", { clase: "tarjeta" }, h("h2", { texto: "Pendientes del Reto" }),
          h("ul", { clase: "tareas" }, r.tareas.map((t) => h("li", {}, h("label", {},
            h("input", { type: "checkbox", checked: t.hecha, onchange: async (ev) => { try { await api(`/api/reto/tareas/${t.id}`, { method: "PUT", json: { hecha: ev.target.checked } }); estado.reto = null; } catch (e) { notificar(e.message); ev.target.checked = !ev.target.checked; } } }),
            t.texto)))),
          h("p", { clase: "suave", texto: `${r.evaluacion.avance} ${r.evaluacion.nota}` }))));
  } catch (e) { limpiar("reto-contenido", errorCaja(e)); }
}
async function cargarPerfil() {
  try {
    const d = await api("/api/perfil");
    const f = document.getElementById("form-perfil");
    f.querySelectorAll('input[name="riesgo"]').forEach((r) => { r.checked = r.value === d.perfil.riesgo; });
    f.elements.horizonte_reto.checked = d.perfil.horizonte_reto !== false;
    f.elements.horizonte_anios.value = d.perfil.horizonte_anios;
    f.elements.capital.value = d.perfil.capital;
    f.elements.max_peso_activo.value = Math.round(d.perfil.max_peso_activo * 100);
    f.elements.max_exposicion_usd.value = Math.round(d.perfil.max_exposicion_usd * 100);
    f.elements.escenario.value = d.perfil.escenario || "base";
    f.elements.incluir_etf_por_confirmar.checked = !!d.perfil.incluir_etf_por_confirmar;
    f.elements.excluir.value = (d.perfil.excluir || []).join(", ");
    limpiar("criterios", h("h2", { texto: "Criterios de puntuación, costos y alertas" }),
      h("p", { clase: "ayuda", texto: `Horizonte efectivo: ${d.perfil_efectivo.horizonte_anios} años (${d.perfil_efectivo.horizonte_origen || "perfil"}). Se cambian en config/local.toml y config/reto.yaml.` }),
      tabla([{ t: "Criterio", f: (x) => x[0].replace("_", " ") }, { t: "Peso", f: (x) => x[1], num: true }], Object.entries(d.puntuacion)),
      h("p", { clase: "suave", texto: `Spreads estimados: ${Object.entries(d.costos.spread_pct).map(([k, v]) => `${k} ${pct(v)}`).join(", ")}; ISR ${pct(d.costos.impuesto_ganancia)}; banda ${d.optimizacion.banda_rebalanceo_pp} pp.` }));
  } catch (e) { limpiar("criterios", errorCaja(e)); }
}
document.getElementById("form-perfil").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const f = ev.target, errores = document.getElementById("errores-perfil");
  errores.replaceChildren();
  const n = (v) => Number(String(v).replace(/[\s,$%]/g, ""));
  const cuerpo = {
    riesgo: (f.querySelector('input[name="riesgo"]:checked') || {}).value, horizonte_reto: f.elements.horizonte_reto.checked,
    horizonte_anios: n(f.elements.horizonte_anios.value), capital: n(f.elements.capital.value),
    max_peso_activo: n(f.elements.max_peso_activo.value) / 100, max_exposicion_usd: n(f.elements.max_exposicion_usd.value) / 100,
    escenario: f.elements.escenario.value, incluir_etf_por_confirmar: f.elements.incluir_etf_por_confirmar.checked,
    excluir: f.elements.excluir.value.split(/[,;\s]+/).map((x) => x.trim().toUpperCase()).filter(Boolean),
  };
  try {
    await api("/api/perfil", { method: "PUT", json: cuerpo });
    notificar("Perfil guardado. Las propuestas se recalculan en segundo plano.");
    cargarPerfil();
  } catch (e) {
    errores.append(h("strong", { texto: "Revise:" }), h("ul", {}, (e.errores || [e.message]).map((m) => h("li", { texto: m }))));
  }
});

/* ---------- acciones globales ---------- */
async function cargarPropuestas() {
  try {
    const d = await api("/api/propuestas");
    estado.propuestas = d.propuestas; estado.clasificacion = d.clasificacion;
  } catch (e) { limpiar("resumen-contenido", errorCaja(e)); return; }
  try { estado.cartera = await api("/api/cartera"); } catch { /* se muestra en su pestaña */ }
  pintarResumen(); pintarDetalle();
}
async function recalcular() {
  const botones = [document.getElementById("btn-calcular"), document.getElementById("btn-calcular-movil")];
  ocupado(botones, true);
  botones.forEach((b) => { b.dataset.t = b.textContent; b.textContent = "Calculando 4 propuestas…"; });
  try {
    const d = await api("/api/propuestas/calcular", { method: "POST", json: {} });
    estado.propuestas = d.propuestas; estado.clasificacion = d.clasificacion;
    await cargarEstado(); pintarResumen(); pintarDetalle();
    notificar("Propuestas recalculadas y alertas evaluadas.");
  } catch (e) { notificar(e.message); }
  finally { ocupado(botones, false); botones.forEach((b) => { b.textContent = b.dataset.t; }); }
}
document.getElementById("btn-calcular").addEventListener("click", recalcular);
document.getElementById("btn-calcular-movil").addEventListener("click", recalcular);
document.getElementById("btn-actualizar").addEventListener("click", async (ev) => {
  const b = ev.currentTarget;
  ocupado([b], true); b.textContent = "Actualizando…";
  try {
    const r = await api("/api/datos/actualizar", { method: "POST", json: {} });
    notificar(`Ciclo completo: ${r.resultado.nuevos_datos} datos nuevos, recálculo: ${r.resultado.recalculo}, ${r.resultado.alertas_nuevas} alerta(s).`);
    estado.universo = null; await cargarEstado(); await cargarPropuestas();
  } catch (e) { notificar(e.message); }
  finally { ocupado([b], false); b.textContent = "Actualizar datos"; }
});
function resumenActualizacion(r) {
  if (!r) return "";
  if (r.modo === "demo") return "Datos sintéticos de demostración generados.";
  const fx = r.fx || {};
  const partes = [fx.estado === "ok" || fx.estado === "al_dia" ? `Tipo de cambio ${fx.estado === "al_dia" ? "al día" : "actualizado"} (${fx.proveedor}).` : "Sin tipo de cambio disponible."];
  const con = Object.entries(r.precios || {}).filter(([, v]) => v.registros || v.al_dia);
  partes.push(con.length ? `Precios: ${con.map(([k, v]) => `${k} ${v.registros} nuevos, ${v.al_dia} al día`).join("; ")}.` : "Ningún proveedor de precios configurado: las propuestas quedarán suspendidas hasta añadir claves en .env o importar precios.");
  return partes.join(" ");
}
document.getElementById("btn-modo").addEventListener("click", async (ev) => {
  const b = ev.currentTarget, destino = b.dataset.destino;
  ocupado([b], true);
  b.textContent = destino === "real" ? "Consultando datos reales…" : "Cambiando a demostración…";
  try {
    const r = await api("/api/modo", { method: "POST", json: { modo: destino } });
    try { sessionStorage.setItem("aviso", `${destino === "real" ? "Modo real activo." : "Modo demostración activo."} ${resumenActualizacion(r.actualizacion)}`); } catch { /* sin almacenamiento */ }
    window.location.reload();
  } catch (e) { notificar(e.message); ocupado([b], false); cargarEstado(); }
});

async function iniciar() {
  try { const aviso = sessionStorage.getItem("aviso"); if (aviso) { sessionStorage.removeItem("aviso"); notificar(aviso); } } catch { /* sin almacenamiento */ }
  document.getElementById("form-operacion").elements.fecha.value = new Date().toISOString().slice(0, 10);
  let inicial = null;
  try { inicial = localStorage.getItem("pestana"); } catch { /* sin almacenamiento */ }
  await cargarEstado();
  try { estado.reto = await api("/api/reto"); } catch { estado.reto = null; }
  ajustarCampos();
  await cargarPropuestas();
  const tab = inicial && document.getElementById(inicial);
  if (tab && tab.id !== "tab-resumen") activarPestana(tab);
  setInterval(cargarEstado, 60000); // detecta ciclos del motor y alertas nuevas
}
/* La lista de instrumentos del formulario se carga solo al usar el campo (evita 137 KB al inicio). */
document.querySelector('#form-operacion input[name="instrumento_id"]').addEventListener("focus", async () => {
  const dl = document.getElementById("lista-instrumentos");
  if (dl.children.length) return;
  try {
    if (!estado.universo) estado.universo = (await api("/api/universo")).instrumentos;
    dl.replaceChildren(...estado.universo.filter((i) => i.estado === "activo").map((i) => h("option", { value: i.id, texto: `${i.clave_operable} — ${i.nombre || ""}` })));
  } catch { /* el campo sigue aceptando la clave escrita */ }
});
iniciar();
