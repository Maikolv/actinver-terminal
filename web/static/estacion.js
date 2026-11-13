/* Estación de Mercado (12-nov-2026): monitor de instrumentos · gráfico principal · inspector contextual.
   Organización inspirada en estaciones financieras profesionales, con identidad propia (DESIGN.md).
   Solo informa: nada se envía. Usa los helpers globales de app.js (h, s, api, chip, num, mxn, pct, signoPct, turno…).
   Datos: /api/visualizaciones/mercado (cierres por instrumento), /api/ficha-tecnica (serie y cotización),
   /api/futuro (pronósticos con rango 10–90 %). Nunca inventa una cotización: lo que falta se rotula «SIN DATO». */
"use strict";

const est = { filas: [], filtro: "", universo: "todos", orden: { col: "clave", dir: 1 }, sel: null, intervalo: 126,
  pronosticos: null, vista: "monitor" };
const EST_PREF = "estacion-preferencias";
const INTERVALOS = [[21, "1M"], [63, "3M"], [126, "6M"], [252, "1A"]];
const n2 = (v) => (v == null || Number.isNaN(v) ? "—" : v.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
const UNIVERSOS = [["todos", "Todos"], ["cartera", "Mi cartera"], ["BMV", "BMV"], ["SIC", "SIC"], ["etf", "ETF"]];

function estPref() { try { return JSON.parse(localStorage.getItem(EST_PREF) || "{}"); } catch { return {}; } }
function estGuardar() {
  try { localStorage.setItem(EST_PREF, JSON.stringify({ densidad: est.densidad, intervalo: est.intervalo, universo: est.universo, sel: est.sel })); } catch { /* sin almacenamiento */ }
}
function estRestaurar() {
  try { localStorage.removeItem(EST_PREF); } catch { /* */ }
  Object.assign(est, { densidad: "compacta", intervalo: 126, universo: "todos", filtro: "", orden: { col: "clave", dir: 1 } });
  montarEstacion(true);
}

const enCartera = () => new Set(((estado.cartera || {}).posiciones || []).map((p) => p.instrumento_id));

// Estado del dato a partir de sus metadatos reales: cierre de la última sesión de su mercado = vigente (cierre),
// anterior = desactualizado; sin cierre = sin dato. Nunca se rotula «tiempo real».
function estadoCelda(c) {
  const ult = (estado.datos || {}).ultima_sesion || {};
  const sesion = c.mercado === "BMV" ? ult.BMV : ult.NYSE;
  if (c.cierre == null) return ["sin_datos", "SIN DATO"];
  if (c.proveedor === "demo_sintetico" || (estado.datos || {}).modo === "demo") return ["sintetico", "SIMULADO"];
  return c.fecha && sesion && c.fecha >= sesion ? ["vigente", "Cierre"] : ["vencido", "Desactualizado"];
}

function filasVisibles() {
  const tengo = enCartera(), q = est.filtro.trim().toUpperCase();
  const f = est.filas.filter((c) => (est.universo === "todos" || (est.universo === "cartera" && tengo.has(c.id))
    || (est.universo === "etf" && c.clase === "etf") || c.mercado === est.universo)
    && (!q || c.clave.toUpperCase().includes(q) || (c.nombre || "").toUpperCase().includes(q)));
  const { col, dir } = est.orden;
  const v = (c) => (col === "clave" ? c.clave : col === "estado" ? estadoCelda(c)[1] : c[col] ?? -Infinity);
  return f.sort((a, b) => (v(a) > v(b) ? dir : v(a) < v(b) ? -dir : 0));
}

function franja(f) {
  if (f === undefined) f = est.ficha || null;
  if (!estado.datos) return h("div", { clase: "estacion-franja", role: "status", texto: "Estado de sesión y fuentes: cargando…" });
  const d = estado.datos, ab = d.mercado_abierto || {};
  const hora = new Intl.DateTimeFormat("es-MX", { timeZone: "America/Mexico_City", hour: "2-digit", minute: "2-digit" }).format(new Date());
  const sesion = (m, k) => `${m} ${ab[k] ? "abierta" : "cerrada"}`;
  return h("div", { clase: "estacion-franja", role: "status", "aria-live": "off" },
    h("span", { texto: `${hora} CDMX (America/Mexico_City)` }),
    h("span", { texto: `${sesion("BMV", "XMEX")} · ${sesion("NYSE", "XNYS")}` }),
    d.fx && d.fx.valor ? h("span", {}, "USD/MXN ", h("span", { clase: "cifra", texto: num(d.fx.valor) }), ` ${d.fx.fecha} · ${d.fx.proveedor}`) : h("span", { texto: "USD/MXN SIN DATO" }),
    f ? h("span", {}, h("strong", { clase: "mono", texto: f.clave }), ` · ${f.precio.proveedor || "sin proveedor"} · ${f.precio.etiqueta}`) : null,
    h("span", { texto: d.modo === "demo" ? "DATOS SIMULADOS" : "Datos reales · sin tiempo real verificado" }),
    h("span", { texto: "Operaciones reales: deshabilitadas" }));
}

function monitor() {
  const filas = filasVisibles(), tengo = enCartera();
  const cab = (col, t, num_) => {
    const activo = est.orden.col === col;
    return h("th", { scope: "col", clase: num_ ? "num" : "", "aria-sort": activo ? (est.orden.dir > 0 ? "ascending" : "descending") : "none" },
      h("button", { type: "button", clase: "orden", texto: `${t}${activo ? (est.orden.dir > 0 ? " ▲" : " ▼") : ""}`,
        onclick: () => { est.orden = { col, dir: activo ? -est.orden.dir : (num_ ? -1 : 1) }; pintarMonitor(); } }));
  };
  const cuerpo = h("tbody", {}, filas.map((c) => {
    const [ed, et] = estadoCelda(c);
    const tr = h("tr", { tabindex: "-1", "data-id": c.id, "aria-selected": String(c.id === est.sel), clase: c.id === est.sel ? "seleccionada" : "",
      onclick: () => seleccionar(c.id) },
      h("td", {}, h("span", { clase: "mono", texto: c.clave.replace(" *", "") }), tengo.has(c.id) ? h("span", { clase: "marca-cartera", title: "En su cartera", texto: " ●" }) : null),
      h("td", { clase: "num cifra", title: c.moneda && c.moneda !== "MXN" ? "Precio de la bolsa de origen, no la cotización del SIC" : null },
        c.cierre == null ? "—" : n2(c.cierre), h("span", { clase: "unidad", texto: ` ${c.moneda || ""}` })),
      h("td", { clase: `num cifra ${Math.abs(c.variacion ?? 0) < 0.0005 ? "" : signo(c.variacion)}`,
        texto: c.variacion == null ? "—" : Math.abs(c.variacion) < 0.0005 ? "0.0%" : `${c.variacion > 0 ? "▲" : "▼"} ${signoPct(c.variacion)}` }),  // ±0.0 % sin flecha
      h("td", {}, chip(ed, et)));
    return tr;
  }));
  return h("div", { clase: "tabla-contenedor estacion-tabla" },
    h("table", { "aria-label": "Monitor de instrumentos", "aria-describedby": "estacion-ayuda-monitor" },
      h("caption", { texto: `${filas.length} instrumentos · último cierre en su moneda (USD = bolsa de origen) · variación de la última sesión` }),
      h("thead", {}, h("tr", {}, cab("clave", "Símbolo"), cab("cierre", "Último", true), cab("variacion", "Var. 1 día", true), cab("estado", "Dato"))),
      cuerpo));
}

function pintarMonitor() {
  const cont = document.getElementById("estacion-monitor-tabla");
  if (cont) cont.replaceChildren(monitor());
}

function seleccionar(id, foco) {
  if (!id) return;
  est.sel = id; estGuardar();
  document.querySelectorAll("#estacion-monitor-tabla tr[data-id]").forEach((tr) => {
    const si = tr.dataset.id === id;
    tr.setAttribute("aria-selected", String(si)); tr.classList.toggle("seleccionada", si);
    if (si && foco) { tr.focus(); tr.scrollIntoView({ block: "nearest" }); }
  });
  if (window.matchMedia("(max-width: 720px)").matches && !foco) cambiarVistaMovil("grafico");
  cargarInstrumento();
}

function pronosticoDe(id) {
  const p = (est.pronosticos || []).filter((x) => x.instrumento_id === id && x.p10 != null && x.p90 != null);
  return p.sort((a, b) => (b.fecha_objetivo > a.fecha_objetivo ? 1 : -1) || b.horizonte - a.horizonte)[0] || null;
}

// Histórico (línea sólida) y proyección (banda 10–90 % y mediana discontinua) separados por un límite temporal.
function graficoPrincipal(f, pr) {
  const serie = (f.tecnico.serie || []).slice(-est.intervalo);
  if (serie.length < 2) return h("p", { clase: "vacio", texto: `Sin historia suficiente: ${f.tecnico.motivo || "no hay cierres guardados"}.` });
  const ancho = 760, alto = 300, m = { i: 64, d: 16, s: 14, inf: 30 };
  const proy = pr ? [{ x: pr.fecha_base, b: pr.precio_base, lo: pr.precio_base, hi: pr.precio_base },
    { x: pr.fecha_objetivo, b: pr.precio_base * (1 + pr.prediccion), lo: pr.precio_base * (1 + pr.p10), hi: pr.precio_base * (1 + pr.p90) }] : [];
  const xs = [...new Set([...serie.map((p) => p.fecha), ...proy.map((p) => p.x)])].sort();
  const pos = new Map(xs.map((x, i) => [x, i]));
  const ys = [...serie.map((p) => p.cierre), ...proy.flatMap((p) => [p.lo, p.hi])];
  let min = Math.min(...ys), max = Math.max(...ys);
  if (min === max) { min -= 1; max += 1; }
  const X = (x) => m.i + (pos.get(x) / Math.max(xs.length - 1, 1)) * (ancho - m.i - m.d);
  const Y = (y) => m.s + (1 - (y - min) / (max - min)) * (alto - m.s - m.inf);
  const unidad = "MXN";
  const svg = s("svg", { viewBox: `0 0 ${ancho} ${alto}`, class: "grafica estacion-grafica", role: "img",
    "aria-label": `${f.clave}: cierres en ${unidad} del ${serie[0].fecha} al ${serie[serie.length - 1].fecha}${pr ? `; proyección 10–90 % al ${pr.fecha_objetivo}` : "; sin proyección vigente"}` });
  for (let k = 0; k <= 4; k++) {
    const y = min + ((max - min) * k) / 4;
    svg.append(s("line", { x1: m.i, x2: ancho - m.d, y1: Y(y), y2: Y(y), stroke: "var(--borde)", "stroke-width": 1 }));
    svg.append(s("text", { x: m.i - 6, y: Y(y) + 4, "text-anchor": "end" }, n2(y)));
  }
  [xs[0], xs[Math.floor(xs.length / 2)], xs[xs.length - 1]].forEach((x, j) =>
    svg.append(s("text", { x: X(x), y: alto - 8, "text-anchor": ["start", "middle", "end"][j] }, x)));
  svg.append(s("path", { d: serie.map((p, i) => `${i ? "L" : "M"}${X(p.fecha).toFixed(1)},${Y(p.cierre).toFixed(1)}`).join(""),
    fill: "none", stroke: "var(--texto)", "stroke-width": 1.6 }));
  if (pr) {
    const limite = X(pr.fecha_base);
    svg.append(s("line", { x1: limite, x2: limite, y1: m.s, y2: alto - m.inf, stroke: "var(--texto-2)", "stroke-dasharray": "3 3" }));
    svg.append(s("text", { x: limite + 4, y: m.s + 10, class: "estacion-limite" }, `proyección emitida con cierre del ${pr.fecha_base} →`));
    svg.append(s("path", { class: "estacion-banda", d: `M${X(proy[0].x)},${Y(proy[0].hi)} L${X(proy[1].x)},${Y(proy[1].hi)} L${X(proy[1].x)},${Y(proy[1].lo)} L${X(proy[0].x)},${Y(proy[0].lo)} Z` }));
    svg.append(s("path", { d: `M${X(proy[0].x)},${Y(proy[0].b)} L${X(proy[1].x)},${Y(proy[1].b)}`, fill: "none", stroke: "var(--sintetico)", "stroke-width": 1.6, "stroke-dasharray": "5 4" }));
  }
  const muestra = (cls) => h("i", { clase: cls });
  return h("figure", { clase: "estacion-figura" }, svg,
    h("figcaption", { clase: "leyenda" },
      h("span", {}, muestra("ley-historico"), `Histórico: cierres diarios (${unidad})`),
      pr ? h("span", {}, muestra("ley-proyeccion"), `Proyección: rango 10–90 % y mediana, horizonte ${pr.horizonte} sesión(es)`) : h("span", { texto: "Sin proyección vigente para este instrumento" })));
}

function inspector(f, pr, celda) {
  const p = f.precio, t = f.tecnico, v = t.variacion || {}, pos = f.posicion;
  const fila = (a, b) => [h("dt", { texto: a }), h("dd", { texto: b ?? "—" })];
  const obs = h("section", { clase: "insp-bloque insp-observado", "aria-labelledby": "insp-obs" },
    h("h3", { id: "insp-obs", texto: "Cotización observada" }),
    h("p", { clase: "insp-precio" }, h("span", { clase: "cifra", texto: p.precio_mxn == null ? "SIN DATO" : n2(p.precio_mxn) }), h("span", { clase: "suave", texto: " MXN" })),
    h("p", {}, chip(p.tiempo_real ? "vigente" : p.vigencia, p.etiqueta)),
    h("dl", {}, fila("Fuente", p.proveedor || "—"), fila("Fecha del dato", `${p.fecha || "—"}${p.hora ? ` ${p.hora}` : ""} (cierre)`),
      fila("Var. 1 día", signoPct(v["1d"])), fila("Var. 1 mes", signoPct(v["1m"])), fila("Var. 1 año", signoPct(v["1a"])),
      fila("Rango 52 semanas", t.disponible ? `${n2(t.minimo_52s)} – ${n2(t.maximo_52s)} MXN` : "—")));
  const ref = h("section", { clase: "insp-bloque insp-referencia", "aria-labelledby": "insp-ref" },
    h("h3", { id: "insp-ref", texto: "Referencia de origen" }),
    p.precio_origen && p.moneda_origen && p.moneda_origen !== "MXN"
      ? h("dl", {}, fila("Bolsa de origen", `${f.perfil.listado || "—"} · ${f.perfil.bolsa_origen || "—"}`),
        fila("Precio de origen", `${n2(p.precio_origen)} ${p.moneda_origen} (estimado)`),
        fila("Tipo de cambio", (estado.datos || {}).fx?.valor ? `${num(estado.datos.fx.valor)} USD/MXN · ${estado.datos.fx.fecha}` : "SIN DATO"),
        h("p", { clase: "suave", texto: "Referencia = precio de origen × tipo de cambio. No es la cotización ejecutable del SIC." }))
      : h("p", { clase: "suave", texto: "Cotiza en MXN en la BMV: sin referencia de otra bolsa." }));
  const fut = h("section", { clase: "insp-bloque insp-futuro", "aria-labelledby": "insp-fut" },
    h("h3", { id: "insp-fut" }, h("span", { clase: "sello-futuro", texto: "FUTURO · ESTIMACIONES" })),
    pr ? h("dl", {}, fila("Horizonte", `${pr.horizonte} ses. · al ${pr.fecha_objetivo}`),
      fila("Rango 10–90 %", `${n2(pr.precio_base * (1 + pr.p10))} – ${n2(pr.precio_base * (1 + pr.p90))} MXN`),
      fila("Variación 10 / 50 / 90 %", `${signoPct(pr.p10)} / ${signoPct(pr.prediccion)} / ${signoPct(pr.p90)}`),
      fila("Probabilidad de subir", pct(pr.prob_subida)), fila("Modelo · base", `${pr.modelo} · cierre del ${pr.fecha_base}`),
      h("p", { clase: "suave", texto: "Señal experimental sin ventaja demostrada. No es una cotización ni una recomendación." }))
      : h("p", { clase: "suave", texto: "Sin pronóstico vigente para este instrumento." }));
  const posicion = h("section", { clase: "insp-bloque", "aria-labelledby": "insp-pos" },
    h("h3", { id: "insp-pos", texto: "Su posición" }),
    pos ? h("dl", {}, fila("Títulos", num(pos.titulos)), fila("Peso en cartera", pct(pos.peso)),
      fila("Plusvalía", `${mxn(pos.plusvalia, true)} (${signoPct(pos.plusvalia_pct)})`)) : h("p", { clase: "suave", texto: "No la tiene en su cartera." }),
    h("div", { clase: "fila-controles" },
      h("button", { type: "button", clase: "boton boton--secundario", texto: "Mi portafolio Actinver", onclick: () => irA("tab-cartera") }),
      h("button", { type: "button", clase: "boton boton--secundario", texto: "Ficha técnica completa", onclick: () => abrirFicha(f.id) })));
  return [obs, ref, fut, posicion];
}

async function cargarInstrumento() {
  const vigente = turno("estacion-instrumento");  // respuestas fuera de orden: solo pinta la última selección
  const id = est.sel;
  const g = document.getElementById("estacion-grafico"), i = document.getElementById("estacion-inspector");
  if (!g || !i) return;
  g.replaceChildren(h("div", { clase: "esqueleto esqueleto--bloque", "aria-hidden": "true" }), h("p", { clase: "suave", role: "status", texto: `Cargando ${id}…` }));
  i.replaceChildren(h("div", { clase: "esqueleto esqueleto--bloque", "aria-hidden": "true" }));
  try {
    const [f] = await Promise.all([api(`/api/ficha-tecnica?simbolo=${encodeURIComponent(id)}&flujo=false`),
      est.pronosticos ? null : api("/api/futuro").then((d) => { est.pronosticos = d.pronosticos || []; }).catch(() => { est.pronosticos = []; })]);
    if (!vigente() || est.sel !== id) return;
    const pr = pronosticoDe(id), celda = est.filas.find((c) => c.id === id);
    const intervalos = h("div", { clase: "segmentado", role: "radiogroup", "aria-label": "Intervalo del gráfico" },
      INTERVALOS.map(([n, t]) => h("button", { type: "button", role: "radio", "aria-checked": String(est.intervalo === n), texto: t,
        onclick: () => { est.intervalo = n; estGuardar(); cargarInstrumento(); } })));
    g.replaceChildren(
      h("div", { clase: "estacion-cabecera" },
        h("h2", {}, h("span", { clase: "mono", texto: f.clave.replace(" *", "") }), h("span", { clase: "suave", texto: ` ${f.nombre}` })),
        h("p", { clase: "suave", texto: `Cierres diarios en MXN · ${f.perfil.mercado || "—"} · intervalo ${INTERVALOS.find(([n]) => n === est.intervalo)[1]} · dato: ${f.precio.etiqueta}` }),
        intervalos),
      graficoPrincipal(f, pr));
    i.replaceChildren(...inspector(f, pr, celda));
    est.ficha = f;
    document.querySelector(".estacion-franja")?.replaceWith(franja(f));
  } catch (e) {
    if (!vigente()) return;
    g.replaceChildren(errorCaja(e), h("button", { type: "button", clase: "boton boton--secundario", texto: "Reintentar", onclick: () => cargarInstrumento() }));
    i.replaceChildren(h("p", { clase: "vacio", texto: "Sin detalle: no se pudo leer la ficha de este instrumento." }));
  }
}

function cambiarVistaMovil(v) {
  est.vista = v;
  const raiz = document.getElementById("estacion");
  if (!raiz) return;
  raiz.dataset.vista = v;
  raiz.querySelectorAll(".estacion-movil [role=tab]").forEach((b) => {
    const si = b.dataset.vista === v;
    b.setAttribute("aria-selected", String(si)); b.tabIndex = si ? 0 : -1;
  });
}

async function montarEstacion(forzar) {
  const raiz = document.getElementById("estacion");
  if (!raiz || (raiz.childElementCount && !forzar)) { if (raiz && est.sel) cargarInstrumento(); return; }
  const pref = estPref();
  Object.assign(est, { densidad: pref.densidad || est.densidad || "compacta", intervalo: pref.intervalo || est.intervalo,
    universo: pref.universo || est.universo, sel: est.sel || pref.sel || null });
  raiz.dataset.densidad = est.densidad;
  raiz.replaceChildren(franja(), h("div", { clase: "esqueleto esqueleto--bloque", "aria-hidden": "true" }));
  try {
    const d = await api("/api/visualizaciones/mercado?ventana=1");
    est.filas = d.celdas || [];
  } catch (e) { raiz.replaceChildren(franja(null), errorCaja(e), h("button", { type: "button", clase: "boton", texto: "Reintentar", onclick: () => montarEstacion(true) })); return; }
  if (!est.filas.length) {
    raiz.replaceChildren(franja(), h("p", { clase: "vacio", texto: "Sin cierres guardados para mostrar en el monitor. Actualice datos o importe precios; la terminal no inventa cotizaciones." }),
      h("button", { type: "button", clase: "boton boton--secundario", texto: "Reintentar", onclick: () => montarEstacion(true) }));
    return;
  }
  const tengo = [...enCartera()];
  if (!est.sel || !est.filas.some((c) => c.id === est.sel)) est.sel = tengo.find((id) => est.filas.some((c) => c.id === id)) || est.filas[0]?.id;
  const buscar = h("input", { type: "search", id: "estacion-buscar", placeholder: "Buscar símbolo o nombre  ( / )", "aria-label": "Buscar instrumento",
    autocomplete: "off", value: est.filtro });
  buscar.addEventListener("input", () => { est.filtro = buscar.value; pintarMonitor(); });
  buscar.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { buscar.value = ""; est.filtro = ""; pintarMonitor(); buscar.blur(); }
    if (e.key === "Enter" || e.key === "ArrowDown") { e.preventDefault(); const p = filasVisibles()[0]; if (p) seleccionar(p.id, true); }
  });
  const universo = h("select", { "aria-label": "Universo", onchange: (e) => { est.universo = e.target.value; estGuardar(); pintarMonitor(); } },
    UNIVERSOS.map(([v, t]) => h("option", { value: v, texto: t, selected: est.universo === v })));
  const densidad = h("button", { type: "button", clase: "boton boton--texto", "aria-pressed": String(est.densidad === "comoda"),
    texto: "Densidad cómoda", onclick: (e) => {
      est.densidad = est.densidad === "comoda" ? "compacta" : "comoda"; raiz.dataset.densidad = est.densidad;
      e.currentTarget.setAttribute("aria-pressed", String(est.densidad === "comoda")); estGuardar(); } });
  const movil = h("div", { clase: "estacion-movil", role: "tablist", "aria-label": "Vista de la estación" },
    [["monitor", "Monitor"], ["grafico", "Gráfico"], ["detalle", "Detalle"]].map(([v, t]) => h("button", { type: "button", role: "tab",
      "data-vista": v, "aria-selected": String(est.vista === v), tabindex: est.vista === v ? "0" : "-1", texto: t, onclick: () => cambiarVistaMovil(v) })));
  raiz.replaceChildren(franja(), movil,
    h("div", { clase: "estacion-cuerpo" },
      h("section", { clase: "estacion-panel estacion-monitor", "aria-label": "Monitor de instrumentos" },
        h("div", { clase: "estacion-controles" }, buscar, universo),
        h("p", { id: "estacion-ayuda-monitor", clase: "ayuda", texto: "«/» busca · ↑ ↓ cambian de fila · Enter abre · Escape limpia. Clic en un encabezado para ordenar." }),
        h("div", { id: "estacion-monitor-tabla" })),
      h("section", { clase: "estacion-panel estacion-centro", id: "estacion-grafico", "aria-label": "Gráfico principal", "aria-live": "polite" }),
      h("aside", { clase: "estacion-panel estacion-inspector", id: "estacion-inspector", "aria-label": "Inspector del instrumento" })),
    h("div", { clase: "fila-controles estacion-pie" }, densidad,
      h("button", { type: "button", clase: "boton boton--texto", texto: "Restaurar preferencias", onclick: estRestaurar })));
  cambiarVistaMovil(est.vista);
  pintarMonitor();
  cargarInstrumento();
}

// Teclado en el monitor: ↑ ↓ mueven la selección; «/» enfoca el buscador desde cualquier parte de Mercado.
document.addEventListener("keydown", (e) => {
  const panel = document.getElementById("panel-mercado");
  if (!panel || panel.hidden) return;
  const enCampo = /^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement?.tagName || "");
  if (e.key === "/" && !enCampo) { e.preventDefault(); document.getElementById("estacion-buscar")?.focus(); return; }
  const tr = document.activeElement?.closest?.("#estacion-monitor-tabla tr[data-id]");
  if (!tr) return;
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();
    const sig = e.key === "ArrowDown" ? tr.nextElementSibling : tr.previousElementSibling;
    if (sig) seleccionar(sig.dataset.id, true);
  } else if (e.key === "Enter") { e.preventDefault(); seleccionar(tr.dataset.id, true); }
  else if (e.key === "Escape") { document.getElementById("estacion-buscar")?.focus(); }
});

// Vistas secundarias de Mercado: pestañas con flechas, Inicio y Fin.
function vistasMercado() {
  const lista = document.getElementById("mercado-vistas");
  if (!lista || lista.dataset.listo) return;
  lista.dataset.listo = "1";
  const tabs = [...lista.querySelectorAll("[role=tab]")];
  const activar = (t) => tabs.forEach((x) => {
    const si = x === t;
    x.setAttribute("aria-selected", String(si)); x.tabIndex = si ? 0 : -1;
    document.getElementById(x.getAttribute("aria-controls")).hidden = !si;
  });
  tabs.forEach((t, i) => {
    t.addEventListener("click", () => activar(t));
    t.addEventListener("keydown", (e) => {
      const j = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 }[e.key];
      if (j === undefined) return;
      e.preventDefault(); const n = tabs[(j + tabs.length) % tabs.length]; activar(n); n.focus();
    });
  });
}

const cargarMercadoBase = CARGAS["tab-mercado"];
CARGAS["tab-mercado"] = () => { vistasMercado(); montarEstacion(); return cargarMercadoBase(); };

// Reloj, sesión y fuente de la franja: se repinta cada 30 s (y al llegar el estado general).
setInterval(() => { const fr = document.querySelector("#estacion .estacion-franja"); if (fr && !document.getElementById("panel-mercado").hidden) fr.replaceWith(franja()); }, 30000);
