/* Terminal de portafolios — interfaz. Sin dependencias.
   Regla de seguridad: los datos nunca se insertan como HTML; todo se crea con textContent. */
"use strict";

const CSRF = document.querySelector('meta[name="csrf"]').content;
const estado = { propuestas: null, cartera: null, universo: null, perfil: null, datos: null, tipoDetalle: "acciones" };

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
const mxn = (v, dec) => (v === null || v === undefined || Number.isNaN(v) ? "—" : (dec ? fmtMXN2 : fmtMXN).format(v));
const pct = (v) => (v === null || v === undefined || Number.isNaN(v) ? "—" : fmtPct.format(v));
const num = (v) => (v === null || v === undefined ? "—" : fmtNum.format(v));
const signo = (v) => (v > 0 ? "positivo" : v < 0 ? "negativo" : "");
const ETIQ = { vigente: "Vigente", retrasado: "Dato retrasado", vencido: "Dato vencido", sin_datos: "Sin datos suficientes",
  sintetico: "Sintético", calculada: "Calculada", demostracion: "Demostración", suspendida: "Suspendida", desactualizada: "No actual" };
const chip = (e, texto) => h("span", { clase: `chip chip--${e || "sin_datos"}`, texto: texto || ETIQ[e] || e || "Sin datos" });
const CLASES = { accion: "Acción", reit: "Acción (REIT)", etf: "ETF", fibra: "FIBRA", fondo_deuda: "Fondo de deuda",
  fondo_renta_variable: "Fondo de renta variable", fondo_multiactivo: "Fondo multiactivo" };

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
  clearTimeout(notificar.t); notificar.t = setTimeout(() => { n.hidden = true; }, 5000);
}
function tabla(columnas, filas, { caption, vacio = "Sin registros." } = {}) {
  if (!filas.length) return h("p", { clase: "vacio", texto: vacio });
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

/* ---------- pestañas (teclado: flechas, Inicio, Fin) ---------- */
function activarPestana(tab, enfocar) {
  const tabs = [...document.querySelectorAll('[role="tab"]')];
  tabs.forEach((t) => {
    const sel = t === tab;
    t.setAttribute("aria-selected", sel); t.tabIndex = sel ? 0 : -1;
    document.getElementById(t.getAttribute("aria-controls")).hidden = !sel;
  });
  if (enfocar) tab.focus();
  try { localStorage.setItem("pestana", tab.id); } catch { /* sin almacenamiento */ }
  const cargas = { "tab-universo": cargarUniverso, "tab-cartera": cargarCartera, "tab-perfil": cargarPerfil };
  if (cargas[tab.id]) cargas[tab.id]();
}
document.getElementById("lista-pestanas").addEventListener("keydown", (ev) => {
  const tabs = [...document.querySelectorAll('[role="tab"]')];
  const i = tabs.indexOf(document.activeElement);
  if (i < 0) return;
  const mapa = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 };
  if (ev.key in mapa) { ev.preventDefault(); activarPestana(tabs[(mapa[ev.key] + tabs.length) % tabs.length], true); }
});
document.querySelectorAll('[role="tab"]').forEach((t) => t.addEventListener("click", () => activarPestana(t)));

/* ---------- estado de datos ---------- */
async function cargarEstado() {
  try {
    const d = await api("/api/estado");
    estado.datos = d;
    document.getElementById("aviso-demo").hidden = d.modo !== "demo";
    const bm = document.getElementById("btn-modo");
    bm.hidden = false;
    bm.dataset.destino = d.modo === "demo" ? "real" : "demo";
    bm.textContent = d.modo === "demo" ? "Usar datos reales y vigentes" : "Ver demostración";
    bm.classList.toggle("boton--real", d.modo === "demo");
    bm.title = d.modo === "demo"
      ? "Cambia a su base real y consulta ahora a los proveedores configurados (tipo de cambio, cierres)"
      : "Cambia a la base de demostración con datos sintéticos (su base real no se modifica)";
    const v = d.vigencia || {};
    const partes = [
      h("span", { clase: "grupo" }, "Precios:",
        ...["vigente", "retrasado", "vencido", "sin_datos", "sintetico"].filter((k) => v[k]).map((k) => chip(k, `${v[k]} ${ETIQ[k].toLowerCase()}`))),
      h("span", { clase: "grupo" }, "USD/MXN:", d.fx.valor ? `${num(d.fx.valor)} (${d.fx.fecha}, ${d.fx.proveedor})` : "", chip(d.fx.estado, d.fx.etiqueta)),
      h("span", { clase: "grupo" }, `Última sesión cerrada: NYSE ${d.ultima_sesion.NYSE} · BMV ${d.ultima_sesion.BMV}`),
      h("span", { clase: "grupo" }, "Operaciones reales: deshabilitadas"),
    ];
    limpiar("estado-datos", ...partes);
  } catch (e) {
    limpiar("estado-datos", errorCaja(e));
  }
}

/* ---------- gráfica de líneas (SVG accesible) ---------- */
function grafica(series, { alto = 220, formato = pct, etiqueta = "Gráfica" } = {}) {
  const ancho = 720, m = { i: 56, d: 12, s: 10, inf: 26 };
  const puntos = series.flatMap((se) => se.datos.filter((p) => p.y !== null && p.y !== undefined));
  if (puntos.length < 2) return h("p", { clase: "vacio", texto: "Sin historia suficiente para graficar." });
  const xs = [...new Set(series.flatMap((se) => se.datos.map((p) => p.x)))].sort();
  const ys = puntos.map((p) => p.y);
  let min = Math.min(...ys), max = Math.max(...ys);
  if (min === max) { min -= 1; max += 1; }
  const X = (x) => m.i + (xs.indexOf(x) / Math.max(xs.length - 1, 1)) * (ancho - m.i - m.d);
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
    const d = se.datos.filter((p) => p.y !== null && p.y !== undefined).map((p, i) => `${i ? "L" : "M"}${X(p.x).toFixed(1)},${Y(p.y).toFixed(1)}`).join("");
    svg.append(s("path", { d, fill: "none", stroke: se.color, "stroke-width": 2 }));
  });
  const leyenda = h("div", { clase: "leyenda" }, series.map((se) => {
    const muestra = h("i");
    muestra.style.background = se.color; // CSSOM: permitido por la CSP (no es estilo en línea)
    return h("span", {}, muestra, se.nombre);
  }));
  return h("figure", {}, svg, leyenda);
}

/* ---------- resumen ---------- */
function tarjetaPropuesta(p, mejor) {
  if (!p) return h("div", { clase: "tarjeta" }, h("h2", { texto: "Sin calcular" }),
    h("p", { clase: "vacio", texto: "Aún no hay propuesta. Pulse «Recalcular propuestas»." }));
  const encabezado = h("div", { clase: "puntuacion" });
  const cuerpo = [];
  if (p.estado === "suspendida") {
    cuerpo.push(h("div", { clase: "error-caja" }, h("strong", { texto: "Suspendida. " }), p.motivos.join(" ")));
  } else {
    encabezado.append(h("span", { clase: "numero", texto: p.puntuacion.total.toFixed(0) }), h("span", { clase: "de", texto: "/ 100 puntos" }));
    const m = (p.comparacion || [])[0] || {};
    cuerpo.push(h("div", { clase: "kpis" },
      kpi("Rend. anual fuera de muestra", pct(m.rend_anual), signo(m.rend_anual)),
      kpi("Volatilidad", pct(m.volatilidad)),
      kpi("Caída máxima", pct(m.max_caida), "negativo"),
      kpi("Estabilidad de pesos", pct(p.estabilidad))));
    cuerpo.push(h("h3", { texto: "Mayores pesos" }), barrasPesos(p.pesos.slice(0, 6)));
    cuerpo.push(h("p", { clase: "suave" }, `Datos al ${p.datos_hasta || "—"} · calculada ${p.calculado_en.replace("T", " ").slice(0, 16)} UTC · `,
      `${p.n_elegibles} elegibles, ${p.n_excluidos} excluidos`));
  }
  (p.avisos || []).forEach((a) => cuerpo.unshift(h("div", { clase: "aviso-caja", texto: a })));
  return h("article", { clase: `tarjeta${mejor ? " tarjeta--destacada" : ""}`, "aria-label": p.nombre },
    h("div", { style: null }, h("h2", {}, p.nombre, " ", chip(p.estado)), mejor ? h("p", { clase: "suave", texto: "Mayor puntuación con sus criterios actuales" }) : null),
    encabezado, ...cuerpo,
    h("button", { type: "button", clase: "boton boton--texto", onclick: () => { estado.tipoDetalle = p.tipo; activarPestana(document.getElementById("tab-propuestas")); pintarDetalle(); } }, "Ver detalle y cambios"));
}
function kpi(etiqueta, valor, clase) { return h("div", { clase: "kpi" }, h("span", { clase: "etiqueta", texto: etiqueta }), h("span", { clase: `valor ${clase || ""}`, texto: valor })); }
function barrasPesos(pesos) {
  return h("ul", { clase: "barras" }, pesos.map((p) => h("li", {},
    h("span", { clase: "nombre-corto", title: p.id, texto: p.clave_operable || p.id }),
    h("span", { clase: "barra", "aria-hidden": "true" }, (() => { const b = h("span"); b.style.width = `${Math.min(p.peso * 100 / 0.4, 100)}%`; return b; })()),
    h("span", { clase: "num", texto: pct(p.peso) }))));
}
function pintarResumen() {
  const p = estado.propuestas, c = estado.cartera;
  const cont = [];
  // Cartera actual
  const tc = h("section", { clase: "tarjeta", "aria-labelledby": "t-cartera" }, h("h2", { id: "t-cartera", texto: "Cartera actual" }));
  if (!c) tc.append(h("p", { clase: "cargando", texto: "Cargando…" }));
  else if (!c.n_operaciones) tc.append(h("p", { clase: "vacio", texto: "Aún no hay operaciones registradas. Regístrelas o impórtelas en «Mi cartera» para comparar las propuestas con su posición real." }));
  else {
    tc.append(h("div", { clase: "kpis" },
      kpi("Valor total", mxn(c.valor_total)),
      kpi("Resultado total", mxn(c.resultado_total), signo(c.resultado_total)),
      kpi("Rend. ponderado por tiempo", pct(c.twr_acumulado), signo(c.twr_acumulado)),
      kpi(`Referencia (${(c.referencia && c.referencia.id) || "—"})`, pct(c.referencia && c.referencia.rend_acumulado), signo(c.referencia && c.referencia.rend_acumulado))),
      h("p", { clase: "suave" }, "Precios de la cartera: ", chip(c.vigencia), c.sin_precio.length ? ` · ${c.sin_precio.length} posición(es) sin precio: el total es incompleto` : ""));
  }
  cont.push(tc);
  // Propuestas
  if (!p) cont.push(h("p", { clase: "cargando", texto: "Cargando propuestas…" }));
  else {
    const primera = (p.clasificacion || []).find((f) => f.posicion === 1);
    cont.push(h("h2", { texto: "Comparación de propuestas" }),
      h("div", { clase: "rejilla" }, tarjetaPropuesta(p.acciones, primera && primera.tipo === "acciones"), tarjetaPropuesta(p.mixta, primera && primera.tipo === "mixta")));
    if ((p.clasificacion || []).length) {
      cont.push(tabla([
        { t: "Posición", f: (f) => f.posicion || "—" }, { t: "Alternativa", f: (f) => f.alternativa },
        { t: "Puntuación", f: (f) => (f.puntuacion === null ? "—" : f.puntuacion.toFixed(1)), num: true },
        { t: "Estado", f: (f) => chip(f.estado) }, { t: "Motivo", f: (f) => f.motivo || "" }],
        p.clasificacion, { caption: "Clasificación según los criterios del perfil. Es un orden relativo, no una certeza." }));
    }
    const mejor = primera ? p[primera.tipo] : null;
    if (mejor && mejor.riesgos) {
      cont.push(h("div", { clase: "rejilla" },
        h("section", { clase: "tarjeta" }, h("h2", { texto: `Riesgos principales — ${mejor.nombre}` }), h("ul", {}, mejor.riesgos.map((r) => h("li", { texto: r })))),
        h("section", { clase: "tarjeta" }, h("h2", { texto: "Qué cambiaría frente a su cartera" }), resumenCambios(mejor))));
    }
  }
  limpiar("resumen-contenido", ...cont);
}
function resumenCambios(p) {
  const c = p.cambios;
  const ops = c.filas.filter((f) => f.accion !== "mantener");
  if (!ops.length) return h("p", { clase: "vacio", texto: "Ningún cambio supera la banda de rebalanceo." });
  return h("div", {}, h("p", {}, `${ops.length} operaciones sugeridas sobre ${mxn(c.base_mxn)}. Costo estimado ${mxn(c.costo_total)} + impuestos estimados ${mxn(c.impuesto_estimado)}.`),
    h("ul", {}, ops.slice(0, 6).map((f) => h("li", {}, `${f.accion === "comprar" ? "Comprar" : "Vender"} ${f.clave_operable}: ${mxn(Math.abs(f.monto_mxn))} (${f.delta_pp > 0 ? "+" : ""}${f.delta_pp.toFixed(1)} pp)`))),
    h("p", { clase: "suave", texto: "Simulación informativa: la terminal no envía órdenes." }));
}

/* ---------- detalle de propuesta ---------- */
document.querySelectorAll("#selector-propuesta button").forEach((b) => b.addEventListener("click", () => { estado.tipoDetalle = b.dataset.tipo; pintarDetalle(); }));
function pintarDetalle() {
  document.querySelectorAll("#selector-propuesta button").forEach((b) => b.setAttribute("aria-checked", b.dataset.tipo === estado.tipoDetalle));
  const p = estado.propuestas && estado.propuestas[estado.tipoDetalle];
  if (!estado.propuestas) return limpiar("propuesta-detalle", h("p", { clase: "cargando", texto: "Cargando…" }));
  if (!p) return limpiar("propuesta-detalle", h("p", { clase: "vacio", texto: "Sin propuesta calculada. Pulse «Recalcular propuestas»." }));
  const out = [];
  (p.avisos || []).forEach((a) => out.push(h("div", { clase: "aviso-caja", texto: a })));
  if (p.modo === "demo") out.push(h("div", { clase: "aviso-caja", texto: "Demostración con datos sintéticos: no utilizar para decisiones." }));
  if (p.estado === "suspendida") {
    out.push(h("div", { clase: "error-caja" }, h("strong", { texto: "Propuesta suspendida. " }), p.motivos.join(" ")));
  } else {
    out.push(h("p", { clase: "info-caja" }, p.aviso));
    out.push(h("div", { clase: "rejilla" },
      h("section", { clase: "tarjeta" }, h("h2", { texto: "Puntuación y motivos" }),
        h("div", { clase: "puntuacion" }, h("span", { clase: "numero", texto: p.puntuacion.total.toFixed(0) }), h("span", { clase: "de", texto: "/ 100" })),
        h("ul", { clase: "criterios" }, p.puntuacion.criterios.map((c) => h("li", {},
          h("span", { texto: c.criterio.replace("_", " ") + ` (${pct(c.peso)})` }),
          h("span", { clase: "barra", "aria-hidden": "true" }, (() => { const b = h("span"); b.style.width = `${c.puntos}%`; return b; })()),
          h("span", { clase: "num", texto: c.puntos.toFixed(0) }),
          h("span", { clase: "explicacion", texto: c.explicacion }))))),
      h("section", { clase: "tarjeta" }, h("h2", { texto: "Escenarios" }), escenarios(p.escenarios))));
    out.push(h("h2", { texto: "Pesos, montos y razones de inclusión" }),
      tabla([
        { t: "Instrumento", f: (f) => h("span", {}, h("strong", { texto: f.clave_operable }), h("br"), h("span", { clase: "suave", texto: `${CLASES[f.clase] || f.clase} · ${f.id}` })) },
        { t: "Peso", f: (f) => pct(f.peso), num: true },
        { t: "Monto objetivo", f: (f) => mxn(f.monto_objetivo), num: true },
        { t: "Títulos aprox.", f: (f) => (f.titulos === null ? "—" : f.titulos), num: true },
        { t: "Precio MXN (fecha)", f: (f) => h("span", {}, mxn(f.precio_mxn, true), h("br"), h("span", { clase: "suave", texto: f.fecha_precio || "" })), num: true },
        { t: "Datos", f: (f) => chip(f.vigencia) },
        { t: "Razones", f: (f) => h("ul", { clase: "lista-motivos" }, f.motivos.map((m) => h("li", { texto: m }))) }],
        p.pesos, { caption: `Capital ${mxn(p.capital)} · efectivo residual por redondeo ${mxn(p.efectivo_residual)}. Precios del cierre indicado, no en tiempo real.` }));
    out.push(h("h2", { texto: "Comparación fuera de muestra" }), tabla([
      { t: "Cartera", f: (f) => f.cartera }, { t: "Rend. anual", f: (f) => pct(f.rend_anual), num: true },
      { t: "Volatilidad", f: (f) => pct(f.volatilidad), num: true }, { t: "Sharpe", f: (f) => (f.sharpe == null ? "—" : f.sharpe.toFixed(2)), num: true },
      { t: "Caída máx.", f: (f) => pct(f.max_caida), num: true }, { t: "Periodo", f: (f) => (f.desde ? `${f.desde} → ${f.hasta}` : "—") }],
      p.comparacion, { caption: "Validación walk-forward sin información futura; la propuesta incluye costos de rotación." }));
    out.push(h("h2", { texto: "Cambios sugeridos frente a sus posiciones" }), tabla([
      { t: "Instrumento", f: (f) => f.clave_operable }, { t: "Actual", f: (f) => pct(f.peso_actual), num: true },
      { t: "Objetivo", f: (f) => pct(f.peso_objetivo), num: true }, { t: "Δ pp", f: (f) => f.delta_pp.toFixed(1), num: true },
      { t: "Monto", f: (f) => mxn(f.monto_mxn), num: true }, { t: "Acción", f: (f) => f.accion },
      { t: "Costo + impuesto est.", f: (f) => mxn(f.costo_estimado + f.impuesto_estimado), num: true }, { t: "Nota", f: (f) => f.nota }],
      p.cambios.filas, { caption: `Banda de no-rebalanceo activa. Costo total estimado ${mxn(p.cambios.costo_total)}; impuesto estimado ${mxn(p.cambios.impuesto_estimado)}.` }));
    out.push(h("details", {}, h("summary", { texto: "Riesgos" }), h("ul", {}, p.riesgos.map((r) => h("li", { texto: r })))));
    out.push(h("details", {}, h("summary", { texto: `Sensibilidad (estabilidad ${pct(p.estabilidad)})` }), tabla([
      { t: "Variante", f: (f) => f.variante }, { t: "Cambio de pesos", f: (f) => (f.error ? f.error : pct(f.cambio_pesos)), num: true },
      { t: "Principales", f: (f) => (f.top || []).map((t) => `${t.id} ${pct(t.peso)}`).join(" · ") }], p.sensibilidad)));
  }
  out.push(h("details", {}, h("summary", { texto: `Instrumentos excluidos (${(p.excluidos || []).length})` }),
    tabla([{ t: "Instrumento", f: (f) => f.id }, { t: "Motivo", f: (f) => f.motivo }], p.excluidos || [])));
  if (p.reproducibilidad) {
    const r = p.reproducibilidad;
    out.push(h("details", {}, h("summary", { texto: "Reproducibilidad: función objetivo, restricciones y datos" }),
      h("dl", { clase: "glosario" },
        h("dt", { texto: "Función objetivo" }), h("dd", { texto: r.funcion_objetivo }),
        h("dt", { texto: "Aversión al riesgo (λ)" }), h("dd", { texto: String(r.aversion_riesgo_lambda) }),
        h("dt", { texto: "Restricciones" }), h("dd", { texto: r.restricciones.join(" · ") }),
        h("dt", { texto: "Ventana de estimación" }), h("dd", { texto: `${r.ventana_estimacion.desde} → ${r.ventana_estimacion.hasta} (${r.ventana_estimacion.sesiones} sesiones)` }),
        h("dt", { texto: "Walk-forward" }), h("dd", { texto: `${r.walk_forward.entrenamiento} entrenamiento / ${r.walk_forward.prueba} prueba, ${r.walk_forward.ventanas} ventanas` }),
        h("dt", { texto: "Escenario" }), h("dd", { texto: `${r.escenario} (${JSON.stringify(r.ajuste_escenario)})` }),
        h("dt", { texto: "Huella de datos" }), h("dd", { texto: r.huella_datos }),
        h("dt", { texto: "Versiones" }), h("dd", { texto: Object.entries(r.versiones).map(([k, v]) => `${k} ${v}`).join(", ") }))));
  }
  limpiar("propuesta-detalle", ...out);
}
function escenarios(e) {
  if (!e) return h("p", { clase: "vacio", texto: "—" });
  return h("div", {},
    h("div", { clase: "kpis" }, kpi(`Favorable (p90, ${e.horizonte_anios} años)`, pct(e.favorable_p90), "positivo"),
      kpi("Central (p50)", pct(e.central_p50), signo(e.central_p50)), kpi("Adverso (p10)", pct(e.adverso_p10), signo(e.adverso_p10))),
    h("div", { clase: "kpis" }, kpi("Peor mes histórico", pct(e.peor_mes_historico), "negativo"),
      kpi("Peor trimestre histórico", pct(e.peor_trimestre_historico), "negativo"), kpi("Caída máxima histórica", pct(e.max_caida_historica), "negativo")),
    h("p", { clase: "suave" }, `Estrés hipotético (${e.estres_hipotetico.supuesto}): ${pct(e.estres_hipotetico.impacto)}.`),
    h("p", { clase: "suave", texto: e.nota }));
}

/* ---------- cartera ---------- */
async function cargarCartera() {
  try {
    const [c, tx] = await Promise.all([api("/api/cartera"), api("/api/transacciones?anuladas=true")]);
    estado.cartera = c;
    pintarCartera(c, tx.transacciones);
  } catch (e) { limpiar("cartera-contenido", errorCaja(e)); }
}
function pintarCartera(c, txs) {
  const out = [];
  if (!c.n_operaciones) {
    out.push(h("div", { clase: "info-caja", texto: "Sin operaciones. Registre una aportación y sus compras, o importe un archivo. La terminal no deduce posiciones del PDF ni de ninguna otra fuente." }));
  } else {
    out.push(h("div", { clase: "kpis" },
      kpi("Valor total", mxn(c.valor_total)), kpi("Efectivo", mxn(c.efectivo)),
      kpi("Aportación neta", mxn(c.aportacion_neta)), kpi("Realizado", mxn(c.realizado), signo(c.realizado)),
      kpi("No realizado", mxn(c.no_realizado), signo(c.no_realizado)), kpi("Dividendos netos", mxn(c.dividendos)),
      kpi("Comisiones", mxn(c.comisiones)), kpi("TIR anual (dinero)", pct(c.tir_anual))));
    if (c.sin_precio.length) out.push(h("div", { clase: "aviso-caja", texto: `Sin precio para ${c.sin_precio.join(", ")}: el valor total y el no realizado están incompletos.` }));
    const hist = c.historia || [];
    out.push(h("h2", { texto: "Evolución" }), grafica([
      { nombre: "Cartera (rend. ponderado por tiempo)", color: "var(--serie-1)", datos: hist.map((p) => ({ x: p.fecha, y: p.twr })) },
      { nombre: `Referencia ${(c.referencia && c.referencia.id) || ""}`, color: "var(--serie-2)", datos: hist.map((p) => ({ x: p.fecha, y: p.referencia })) }],
      { etiqueta: "Rendimiento acumulado de la cartera frente a la referencia" }));
    out.push(h("h2", { texto: "Posiciones" }), tabla([
      { t: "Instrumento", f: (f) => f.clave_operable || f.instrumento_id }, { t: "Cantidad", f: (f) => num(f.cantidad), num: true },
      { t: "Costo prom.", f: (f) => mxn(f.costo_promedio, true), num: true }, { t: "Precio", f: (f) => mxn(f.precio_mxn, true), num: true },
      { t: "Valor", f: (f) => mxn(f.valor_mxn), num: true }, { t: "Peso", f: (f) => pct(f.peso), num: true },
      { t: "No realizado", f: (f) => h("span", { clase: signo(f.no_realizado), texto: `${mxn(f.no_realizado)} (${pct(f.no_realizado_pct)})` }), num: true },
      { t: "Realizado", f: (f) => mxn(f.realizado), num: true }, { t: "Dividendos", f: (f) => mxn(f.dividendos), num: true },
      { t: "Dato", f: (f) => h("span", {}, chip(f.vigencia, f.etiqueta_vigencia), h("br"), h("span", { clase: "suave", texto: `${f.fecha_precio || ""} ${f.proveedor || ""}` })) }],
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
      { t: "Fecha (UTC)", f: (f) => f.ts }, { t: "Entidad", f: (f) => `${f.entidad} ${f.entidad_id || ""}` },
      { t: "Acción", f: (f) => f.accion }, { t: "Motivo", f: (f) => f.motivo || "" }], a.eventos));
  } catch (e) { det.append(errorCaja(e)); }
}
async function anularOperacion(f) {
  const motivo = window.prompt(`Motivo para anular la operación #${f.id} (queda registrada en auditoría):`);
  if (motivo === null) return;
  try { await api(`/api/transacciones/${f.id}/anular`, { method: "POST", json: { motivo } }); notificar("Operación anulada."); cargarCartera(); }
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
}
document.getElementById("form-operacion").elements.tipo.addEventListener("change", ajustarCampos);
document.getElementById("form-operacion").elements.moneda.addEventListener("change", (ev) => {
  const tc = document.getElementById("form-operacion").elements.tipo_cambio;
  if (ev.target.value === "MXN") tc.value = "1";
  ajustarCampos();
});
document.getElementById("form-operacion").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const form = ev.target, errores = document.getElementById("errores-operacion");
  const datos = Object.fromEntries(new FormData(form).entries());
  const visibles = new Set(CAMPOS_POR_TIPO[datos.tipo] || []);
  if (!visibles.has("instrumento")) datos.instrumento_id = "";
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
      notificar("Corrección guardada; el registro original queda anulado y auditado.");
    } else {
      const r = await api("/api/transacciones", { method: "POST", json: datos });
      notificar(r.id ? "Operación guardada." : "Operación duplicada: ya existía y no se volvió a registrar.");
    }
    form.reset(); ajustarCampos(); cargarCartera(); refrescarPropuestasTrasCambio();
  } catch (e) {
    const lista = e.errores || [e.message];
    errores.append(h("strong", { texto: "Revise los datos:" }), h("ul", {}, lista.map((m) => h("li", { texto: m }))));
    lista.forEach((m) => { const campo = form.elements[m.split(":")[0]]; if (campo) campo.setAttribute("aria-invalid", "true"); });
    errores.focus && errores.setAttribute("tabindex", "-1"); errores.focus();
  } finally { ocupado([boton], false); }
});
function refrescarPropuestasTrasCambio() {
  if (estado.propuestas) notificar("Su cartera cambió: recalcule las propuestas para actualizar los cambios sugeridos.");
}

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
    const nodos = [h("p", {}, `${rep.filas} filas: ${rep.aceptables ?? 0} válidas nuevas, ${rep.duplicadas} duplicadas, ${rep.rechazadas} con errores.`)];
    const problemas = rep.detalle.filter((d) => d.estado !== "aceptada");
    if (problemas.length) nodos.push(tabla([{ t: "Línea", f: (f) => f.linea, num: true }, { t: "Estado", f: (f) => f.estado }, { t: "Detalle", f: (f) => f.errores.join("; ") }], problemas.slice(0, 200)));
    if (!rep.rechazadas && rep.aceptables > 0) {
      nodos.push(h("button", { type: "button", clase: "boton boton--primario", onclick: async (e2) => {
        ocupado([e2.target], true);
        try { const fin = await enviarImportacion(form, true); notificar(`Importación confirmada: ${fin.aceptadas} registros.`); salida.replaceChildren(h("p", { texto: `Importadas ${fin.aceptadas} filas; ${fin.duplicadas} duplicadas omitidas. Archivo original conservado.` })); form.reset(); cargarCartera(); }
        catch (err) { salida.append(errorCaja(err)); ocupado([e2.target], false); }
      } }, `Confirmar importación de ${rep.aceptables} filas`));
    } else if (rep.rechazadas) nodos.push(h("p", { clase: "error-caja", texto: "Corrija las filas con errores y vuelva a revisar; no se importará nada parcialmente." }));
    salida.replaceChildren(...nodos);
  } catch (e) { salida.replaceChildren(errorCaja(e)); } finally { ocupado([boton], false); }
});

/* ---------- universo y proveedores ---------- */
async function cargarUniverso() {
  try {
    if (!estado.universo) estado.universo = (await api("/api/universo")).instrumentos;
    const sel = document.getElementById("filtro-clase");
    if (sel.options.length === 1) [...new Set(estado.universo.map((i) => i.clase))].sort().forEach((c) => sel.append(h("option", { value: c, texto: CLASES[c] || c })));
    pintarUniverso();
    const d = estado.datos || (await api("/api/estado"));
    limpiar("proveedores", h("h2", { texto: "Proveedores" }), tabla([
      { t: "Proveedor", f: (f) => f.proveedor }, { t: "Uso", f: (f) => f.descripcion },
      { t: "Tipo de dato", f: (f) => f.tipo_dato }, { t: "Credencial", f: (f) => (f.requiere_credencial ? "Requerida" : "No") },
      { t: "Estado", f: (f) => (f.configurado ? chip("vigente", "Configurado") : chip("sin_datos", "No configurado")) },
      { t: "Peticiones restantes", f: (f) => (f.peticiones_restantes ?? "—"), num: true },
      { t: "Última corrida", f: (f) => (f.ultima_corrida ? `${f.ultima_corrida.fin || ""} · ${f.ultima_corrida.estado} · ${f.ultima_corrida.mensaje || ""}` : "—") },
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
    { t: "Bolsa · moneda · zona", f: (f) => `${f.bolsa_referencia || "—"} · ${f.moneda_referencia || "—"} · ${f.zona_horaria_referencia || "—"}` },
    { t: "Precio (fecha)", f: (f) => (f.precio == null ? "—" : `${num(f.precio)} ${f.moneda} (${f.fecha})`), num: true },
    { t: "Tipo de dato", f: (f) => f.tipo_dato || "—" }, { t: "Proveedor", f: (f) => f.proveedor || "—" },
    { t: "Retraso", f: (f) => (f.retraso_horas == null ? "—" : `${f.retraso_horas} h`), num: true },
    { t: "Vigencia", f: (f) => chip(f.vigencia, f.etiqueta) }],
    filas.slice(0, 400), { caption: `${filas.length} de ${estado.universo.length} instrumentos. Clase verificada con fuente independiente; la sección del PDF no determina la clase.` }));
}
["filtro-texto", "filtro-clase", "filtro-vigencia"].forEach((id) => document.getElementById(id).addEventListener("input", () => estado.universo && pintarUniverso()));

/* ---------- perfil ---------- */
async function cargarPerfil() {
  try {
    const d = await api("/api/perfil");
    estado.perfil = d.perfil;
    const f = document.getElementById("form-perfil");
    f.querySelectorAll('input[name="riesgo"]').forEach((r) => { r.checked = r.value === d.perfil.riesgo; });
    f.elements.horizonte_anios.value = d.perfil.horizonte_anios;
    f.elements.capital.value = d.perfil.capital;
    f.elements.max_peso_activo.value = Math.round(d.perfil.max_peso_activo * 100);
    f.elements.max_exposicion_usd.value = Math.round(d.perfil.max_exposicion_usd * 100);
    f.elements.escenario.value = d.perfil.escenario || "base";
    f.elements.incluir_etf_por_confirmar.checked = !!d.perfil.incluir_etf_por_confirmar;
    f.elements.excluir.value = (d.perfil.excluir || []).join(", ");
    limpiar("criterios", h("h2", { texto: "Pesos de la puntuación y supuestos de costos" }),
      h("p", { clase: "ayuda", texto: "Se modifican en config/local.toml (ver README). Se muestran para que la clasificación sea transparente." }),
      tabla([{ t: "Criterio", f: (x) => x[0].replace("_", " ") }, { t: "Peso", f: (x) => x[1], num: true }], Object.entries(d.puntuacion)),
      h("p", { clase: "suave" }, `Comisión ${pct(d.costos.comision_pct)} + IVA ${pct(d.costos.iva)}; spreads estimados: ${Object.entries(d.costos.spread_pct).map(([k, v]) => `${k} ${pct(v)}`).join(", ")}; ISR ganancias ${pct(d.costos.impuesto_ganancia)}; banda de rebalanceo ${d.optimizacion.banda_rebalanceo_pp} pp.`));
  } catch (e) { limpiar("criterios", errorCaja(e)); }
}
document.getElementById("form-perfil").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const f = ev.target, errores = document.getElementById("errores-perfil");
  errores.replaceChildren();
  const riesgo = (f.querySelector('input[name="riesgo"]:checked') || {}).value;
  const n = (v) => Number(String(v).replace(/[\s,$%]/g, ""));
  const cuerpo = {
    riesgo, horizonte_anios: n(f.elements.horizonte_anios.value), capital: n(f.elements.capital.value),
    max_peso_activo: n(f.elements.max_peso_activo.value) / 100, max_exposicion_usd: n(f.elements.max_exposicion_usd.value) / 100,
    escenario: f.elements.escenario.value, incluir_etf_por_confirmar: f.elements.incluir_etf_por_confirmar.checked,
    excluir: f.elements.excluir.value.split(/[,;\s]+/).map((x) => x.trim().toUpperCase()).filter(Boolean),
  };
  try {
    await api("/api/perfil", { method: "PUT", json: cuerpo });
    notificar("Perfil guardado. Recalcule las propuestas para aplicarlo.");
    cargarPropuestas();
  } catch (e) {
    errores.append(h("strong", { texto: "Revise:" }), h("ul", {}, (e.errores || [e.message]).map((m) => h("li", { texto: m.replace("max_peso_activo: entre 0.02 y 1 (2 % a 100 %)", "Peso máximo por activo: entre 2 y 100 %").replace("max_exposicion_usd: entre 0 y 1", "Exposición máxima a dólar: entre 0 y 100 %") }))));
  }
});

/* ---------- acciones globales ---------- */
async function cargarPropuestas() {
  try { estado.propuestas = await api("/api/propuestas"); }
  catch (e) { estado.propuestas = null; limpiar("resumen-contenido", errorCaja(e)); return; }
  pintarResumen(); pintarDetalle();
}
async function recalcular() {
  const botones = [document.getElementById("btn-calcular"), document.getElementById("btn-calcular-movil")];
  ocupado(botones, true);
  botones.forEach((b) => { b.dataset.t = b.textContent; b.textContent = "Calculando… (unos segundos)"; });
  try {
    estado.propuestas = await api("/api/propuestas/calcular", { method: "POST", json: {} });
    pintarResumen(); pintarDetalle();
    notificar("Propuestas recalculadas.");
  } catch (e) { notificar(e.message); }
  finally { ocupado(botones, false); botones.forEach((b) => { b.textContent = b.dataset.t; }); }
}
document.getElementById("btn-calcular").addEventListener("click", recalcular);
document.getElementById("btn-calcular-movil").addEventListener("click", recalcular);
document.getElementById("btn-actualizar").addEventListener("click", async (ev) => {
  const b = ev.currentTarget;
  ocupado([b], true); b.textContent = "Actualizando…";
  try { await api("/api/datos/actualizar", { method: "POST", json: {} }); notificar("Datos actualizados. Revise la pestaña Datos para el detalle por proveedor."); estado.universo = null; await cargarEstado(); }
  catch (e) { notificar(e.message); }
  finally { ocupado([b], false); b.textContent = "Actualizar datos"; }
});

function resumenActualizacion(r) {
  if (!r) return "";
  if (r.modo === "demo") return "Datos sintéticos de demostración generados.";
  const partes = [];
  const fx = r.fx || {};
  if (fx.estado === "ok" || fx.estado === "al_dia") partes.push(`Tipo de cambio ${fx.estado === "al_dia" ? "al día" : "actualizado"} (${fx.proveedor}).`);
  else partes.push("Sin tipo de cambio disponible.");
  const precios = Object.entries(r.precios || {});
  const conDatos = precios.filter(([, v]) => v.registros || v.al_dia);
  if (conDatos.length) partes.push(`Precios: ${conDatos.map(([k, v]) => `${k} ${v.registros} registros nuevos, ${v.al_dia} al día`).join("; ")}.`);
  else partes.push("Ningún proveedor de precios configurado: las propuestas quedarán suspendidas hasta añadir claves en .env o importar precios (vea la pestaña Datos).");
  return partes.join(" ");
}
document.getElementById("btn-modo").addEventListener("click", async (ev) => {
  const b = ev.currentTarget, destino = b.dataset.destino;
  ocupado([b], true);
  b.textContent = destino === "real" ? "Consultando datos reales…" : "Cambiando a demostración…";
  try {
    const r = await api("/api/modo", { method: "POST", json: { modo: destino } });
    const msg = `${destino === "real" ? "Modo real activo." : "Modo demostración activo."} ${resumenActualizacion(r.actualizacion)}`;
    try { sessionStorage.setItem("aviso", msg); } catch { /* sin almacenamiento */ }
    window.location.reload();
  } catch (e) { notificar(e.message); ocupado([b], false); cargarEstado(); }
});

async function iniciar() {
  try { const aviso = sessionStorage.getItem("aviso"); if (aviso) { sessionStorage.removeItem("aviso"); notificar(aviso); } } catch { /* sin almacenamiento */ }
  document.getElementById("form-operacion").elements.fecha.value = new Date().toISOString().slice(0, 10);
  ajustarCampos();
  let inicial = null;
  try { inicial = localStorage.getItem("pestana"); } catch { /* sin almacenamiento */ }
  const tab = inicial && document.getElementById(inicial);
  if (tab && tab.id !== "tab-resumen") activarPestana(tab);
  cargarEstado();
  try { estado.cartera = await api("/api/cartera"); } catch { estado.cartera = null; }
  await cargarPropuestas();
  api("/api/universo").then((u) => {
    estado.universo = u.instrumentos;
    const dl = document.getElementById("lista-instrumentos");
    dl.replaceChildren(...u.instrumentos.filter((i) => i.estado === "activo").map((i) => h("option", { value: i.id, texto: `${i.clave_operable} — ${i.nombre || ""}` })));
  }).catch(() => {});
}
iniciar();
