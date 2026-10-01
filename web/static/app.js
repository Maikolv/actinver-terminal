/* Actinver Terminal — interfaz. Sin dependencias.
   Regla de seguridad: los datos nunca se insertan como HTML; todo se crea con textContent. */
"use strict";

const CSRF = document.querySelector('meta[name="csrf"]').content;
const estado = {
  alertasResumen: null, propuestas: null, clasificacion: [], cartera: null, universo: null, datos: null, reto: null,
  universoSel: "acciones", lenteSel: "ajuste", mercadoSel: "ambos", lenteResumen: "ajuste", ultimoCiclo: null,
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
const LENTES = { rendimiento: "Máximo rendimiento", ajuste: "Ajuste a su perfil", puntuacion: "Máxima puntuación" };

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
function tabla(columnas, filas, { caption, vacio: textoVacio = "Sin registros.", claseFila } = {}) {
  if (!filas.length) return h("p", { clase: "vacio", texto: textoVacio });
  const cab = h("tr", {}, columnas.map((c) => h("th", { scope: "col", clase: c.num ? "num" : null, texto: c.t })));
  const cuerpo = filas.map((f) => h("tr", { clase: claseFila ? claseFila(f) : null }, columnas.map((c) => {
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
  "tab-resumen": () => pintarResumen(), "tab-propuestas": () => pintarDetalle(), "tab-alertas": () => cargarAlertas(), "tab-cartera": () => cargarCartera(), "tab-mercado": () => cargarMercado(),
  "tab-universo": () => { cargarUniverso(); cargarCobertura(); }, "tab-tiempo": () => cargarTiempo(),
  "tab-ranking": () => cargarRanking(), "tab-perfil": () => { cargarReto(); cargarPerfil(); },
};
const navPestanas = document.querySelector(".pestanas");
function mostrarSecundarias(si) {
  navPestanas.classList.toggle("con-secundarias", si);
  const b = document.getElementById("btn-mas");
  b.setAttribute("aria-expanded", String(si)); b.textContent = si ? "Menos ▴" : "Más ▾";
  try { localStorage.setItem("mas", si ? "1" : "0"); } catch { /* sin almacenamiento */ }
}
document.getElementById("btn-mas").addEventListener("click", () => mostrarSecundarias(!navPestanas.classList.contains("con-secundarias")));
function activarPestana(tab, enfocar) {
  if (tab.classList.contains("secundaria")) mostrarSecundarias(true);
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
  const tabs = [...document.querySelectorAll('[role="tab"]')].filter((t) => getComputedStyle(t).display !== "none");
  const i = tabs.indexOf(document.activeElement);
  if (i < 0) return;
  const mapa = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 };
  if (ev.key in mapa) { ev.preventDefault(); activarPestana(tabs[(mapa[ev.key] + tabs.length) % tabs.length], true); }
});
document.querySelectorAll('[role="tab"]').forEach((t) => t.addEventListener("click", () => activarPestana(t)));
const irA = (id) => activarPestana(document.getElementById(id));
const pestanaVisible = (id) => !document.getElementById(id).hidden;

/* ---------- estado de datos y motor ---------- */
const MODOS_VIVO = { websocket: "en vivo (IEX)", consulta: "cada minuto (respaldo)", mercado_cerrado: "mercado de EE. UU. cerrado",
  sin_credencial: "sin claves de Alpaca", demo: "no en demostración", error: "error", reconectando: "reconectando…",
  conectando: "conectando…", desactivado: "desactivado", apagado: "apagado", iniciando: "iniciando…", sin_simbolos: "sin símbolos" };
function textoVivo(t) {
  if (!t) return "Tiempo real: no";
  const base = `SIC/ETF en vivo: ${MODOS_VIVO[t.modo] || t.modo}`;
  return t.activo ? `${base} · ${t.simbolos}/${t.limite_simbolos} símbolos${t.ultimo_precio ? ` · último ${fechaLocal(t.ultimo_precio)}` : ""}` : base;
}
async function cargarEstado(previo) {
  try {
    const d = previo || await api("/api/estado");
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
      h("span", { clase: "grupo" }, textoVivo(d.tiempo_real), " · Operaciones reales: deshabilitadas"));
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
        { t: "Títulos", f: (f) => titulosConMarca(f.id, f.titulos), num: true }, { t: "Precio (fecha)", f: (f) => precioConMarca(f.id, f.precio_mxn, f.fecha_precio || "—"), num: true },
        { t: "Importe", f: (f) => mxn(f.importe), num: true }, { t: "Costo", f: (f) => mxn(f.costo, true), num: true }],
      r.operaciones, { caption: "Títulos enteros con el último precio disponible. * SIC: precio de referencia (bolsa de origen × tipo de cambio), no la cotización del SIC." }),
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
      kpi("Escenario adverso (p10)", pct(p.escenarios && p.escenarios.adverso_p10), "negativo"),
      kpi("Órdenes a capturar", p.ordenes ? `${p.ordenes.total} (${p.ordenes.compras} compra · ${p.ordenes.ventas} venta)` : "—")));
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
const DECISION = { comprar: ["vigente", "Comprar"], vender: ["vencido", "Vender"], mantener: ["calculada", "Mantener"],
  pendiente: ["retrasado", "Decisión pendiente"] };
function tarjetaPlan(plan) {
  const c = plan.cuenta, r = plan.reglas || {}, res = plan.resumen;
  const cuenta = c.confirmada
    ? h("p", {}, chip("vigente", "Cuenta confirmada"), ` Portal ${plan.cuenta_hora_texto}: valuación ${mxn(c.valor_total)} · poder de compra ${mxn(c.efectivo)}`
      + (c.por_liquidar ? ` · por liquidar ${mxn(c.por_liquidar)}` : "") + (c.efectivo_tras_compras !== null ? ` · efectivo tras las compras sugeridas ${mxn(c.efectivo_tras_compras)}` : ""))
    : h("div", { clase: "aviso-caja" }, h("strong", { texto: "Cuenta NO confirmada. " }),
      "La terminal no conoce sus títulos ni su efectivo del portal: todas las decisiones quedan pendientes y los montos son orientativos. ",
      h("button", { type: "button", clase: "boton boton--texto", onclick: () => irA("tab-cartera") }, "Capturar mi portafolio"));
  const reglas = r.activo ? h("p", { clase: "suave", texto: `Reglas verificadas (bases consultadas ${r.consultado}): ≥${r.min_emisoras} emisoras · ≤${pct(r.max_peso_emisora)} por emisora · comisión ${(r.comision * 100).toFixed(3)} % con IVA · catálogo del simulador: ${r.catalogo} instrumentos · competencia ${r.competencia}.` }) : null;
  const avisos = [...(r.errores || []), ...(r.avisos || [])].map((a) => h("div", { clase: "aviso-caja", texto: a }));
  const faltan = plan.faltan.length ? h("div", { clase: "aviso-caja" }, h("strong", { texto: "Datos que faltan: " }), plan.faltan.join(" · ")) : null;
  const filas = plan.acciones;
  return h("section", { clase: "tarjeta", "aria-labelledby": "t-plan" },
    h("h2", { id: "t-plan", texto: plan.propuesta ? `Plan de acción — «${plan.propuesta.nombre}» (${plan.propuesta.puntuacion.toFixed(1)}/100, datos al ${plan.propuesta.datos_hasta})` : "Plan de acción" }),
    cuenta, reglas, ...avisos, faltan,
    h("div", { clase: "kpis" }, kpi("Compras", `${res.comprar} · ${mxn(res.monto_compras)}`), kpi("Ventas", `${res.vender} · ${mxn(res.monto_ventas)}`),
      kpi("Mantener", String(res.mantener)), kpi("Decisión pendiente", String(res.pendiente), res.pendiente ? "negativo" : "")),
    tabla([
      { t: "#", f: (a) => a.prioridad, num: true },
      { t: "Decisión", f: (a) => chip(...DECISION[a.decision]) },
      { t: "Instrumento", f: (a) => h("span", {}, h("strong", { texto: a.clave }), h("br"), h("span", { clase: "suave", texto: `${a.mercado} · propuesta: ${a.accion_propuesta}` })) },
      { t: "Cantidad", f: (a) => (a.cantidad ? num(a.cantidad) : "—"), num: true },
      { t: "Precio límite", f: (a) => (a.precio_limite ? mxn(a.precio_limite, true) : "—"), num: true },
      { t: "Monto", f: (a) => (a.decision === "pendiente" ? `≈ ${mxn(a.monto)}` : mxn(a.monto)), num: true },
      { t: "Peso actual → objetivo", f: (a) => `${pct(a.peso_actual)} → ${pct(a.peso_objetivo)}` },
      { t: "Precio (fuente · fecha)", f: (a) => h("span", { title: a.precio.nota || "" }, `${a.precio.fuente || "—"} · ${a.precio.fecha || "—"}${a.precio.es_referencia ? " · referencia *" : ""}`) },
      { t: "Motivo", f: (a) => a.motivo },
      { t: "Falta o se invalida si", f: (a) => (a.falta.length ? h("span", { clase: "no-cumple", texto: `Falta: ${a.falta.join(" · ")}` }) : a.invalidacion || "—") }],
    filas, { caption: "Ordenadas por prioridad: ventas, luego compras por tamaño del ajuste, luego mantener. * SIC: referencia de la bolsa de origen × tipo de cambio, no cotización ejecutable. Nada se envía: usted captura cada orden en el portal.",
      vacio: "Sin acciones: la cartera está dentro de la banda de rebalanceo o no hay propuesta vigente.",
      claseFila: (a) => (a.decision === "pendiente" ? "fila-inactiva" : null) }),
    h("p", { clase: "suave", texto: plan.aviso }),
    h("p", {}, h("button", { type: "button", clase: "boton boton--secundario", onclick: () => irA("tab-tiempo") }, "Generar o ver boletas")));
}
async function pintarResumen() {
  const d = estado.datos;
  const cont = [];
  if (d && d.alertas_pendientes) {
    let lista = [];
    try { lista = (estado.alertasResumen || (await api("/api/alertas?limite=5")).alertas).filter((a) => a.estado === "nueva"); } catch { /* sin detalle */ }
    estado.alertasResumen = null;
    cont.push(h("section", { clase: "franja-alertas", "aria-label": "Alertas nuevas" },
      h("strong", { texto: `${d.alertas_pendientes} alerta(s) nueva(s). ` }), lista.slice(0, 3).map((a) => a.titulo).join(" · "), " ",
      h("button", { type: "button", clase: "boton boton--texto", onclick: () => irA("tab-alertas") }, "Revisar alertas")));
  }
  let plan = null;
  try { plan = await api("/api/plan-accion"); } catch (e) { cont.push(errorCaja(e)); }
  if (plan) cont.push(tarjetaPlan(plan));
  if (plan && plan.propuestas_texto.length) {
    cont.push(h("section", { clase: "tarjeta", "aria-labelledby": "t-ref" }, h("h2", { id: "t-ref", texto: "Propuesta que alimenta el plan (igual que en Telegram)" }),
      h("ul", {}, plan.propuestas_texto.map((t) => h("li", { texto: t }))),
      h("button", { type: "button", clase: "boton boton--texto", onclick: () => irA("tab-propuestas") }, "Ver todas las propuestas")));
  }
  const tr = tarjetaReto(estado.reto, estado.cartera);
  if (tr) cont.push(tr);
  try {
    const ei = await api("/api/estado-informacion");
    const NIV = { confirmado: ["vigente", "Confirmado"], estimado: ["retrasado", "Estimado"], vencido: ["vencido", "Vencido"], falta: ["sin_datos", "Falta"] };
    cont.push(h("details", { clase: "tarjeta" }, h("summary", { texto: "¿En qué puedo confiar hoy? (fuentes, frescura y lo que falta)" }),
      tabla([{ t: "Tema", f: (f) => f.tema }, { t: "Estado", f: (f) => chip(...NIV[f.nivel]) }, { t: "Qué hay", f: (f) => f.texto },
        { t: "Qué falta hacer", f: (f) => f.accion || "—" }], ei.items,
      { caption: Object.entries(ei.leyenda).map(([k, v]) => `${NIV[k][1]}: ${v}`).join(" · ") })));
  } catch { /* el resto se muestra igual */ }
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
function clavePropuestaSel() {
  const base = `${estado.universoSel}_${estado.lenteSel}`;
  const v = `${base}_${estado.mercadoSel}`;
  return estado.lenteSel === "puntuacion" && estado.mercadoSel !== "ambos" && estado.propuestas && v in estado.propuestas ? v : base;
}
function pintarDetalle() {
  segmentado("selector-universo", estado.universoSel, (v) => { estado.universoSel = v; pintarDetalle(); });
  segmentado("selector-lente", estado.lenteSel, (v) => { estado.lenteSel = v; pintarDetalle(); });
  const hayVariantes = estado.lenteSel === "puntuacion" && estado.propuestas && `${estado.universoSel}_puntuacion_nacionales` in estado.propuestas;
  document.getElementById("selector-mercado-propuesta").hidden = !hayVariantes;
  segmentado("selector-mercado-propuesta", estado.mercadoSel, (v) => { estado.mercadoSel = v; pintarDetalle(); });
  if (!estado.propuestas) return;
  const p = estado.propuestas[clavePropuestaSel()];
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
    if (p.ordenes) {
      const o = p.ordenes;
      out.push(h("section", { clase: "tarjeta" }, h("h2", { texto: `Plan de órdenes: ${o.total} órdenes` }),
        h("div", { clase: "kpis" }, kpi("Compras", String(o.compras)), kpi("Ventas", String(o.ventas)),
          kpi("Emisoras finales", String(o.posiciones)), kpi("Costo estimado", mxn(o.costo_total)),
          kpi("Precio a tomar del portal (SIC)", String(o.sin_precio))),
        h("p", { clase: "suave", texto: o.criterio }),
        o.eliminadas.length ? h("p", { clase: "suave", texto: `Consolidadas por ser menores al mínimo: ${o.eliminadas.map((e) => `${e.id.split(":")[1]} ${pct(e.peso)}`).join(", ")}; su peso se repartió entre las demás.` }) : null,
        o.sin_precio ? h("p", { clase: "aviso-caja", texto: `${o.sin_precio} orden(es) del SIC: la terminal solo tiene el precio de la bolsa de origen como referencia; la boleta sale como «investigar» y los títulos se calculan con el precio del portal.` }) : null));
    }
    out.push(h("h2", { texto: "Pesos, montos, títulos y razones" }),
      tabla([
        { t: "Instrumento", f: (f) => h("span", {}, h("strong", { texto: f.clave_operable }), h("br"), h("span", { clase: "suave", texto: `${CLASES[f.clase] || f.clase} · ${f.id}` })) },
        { t: "Peso", f: (f) => pct(f.peso), num: true }, { t: "Monto", f: (f) => mxn(f.monto_objetivo), num: true },
        { t: "Títulos", f: (f) => titulosConMarca(f.id, f.titulos), num: true },
        { t: "Precio MXN (fecha)", f: (f) => precioConMarca(f.id, f.precio_mxn, f.fecha_precio || ""), num: true },
        { t: "Datos", f: (f) => chip(f.vigencia) },
        { t: "Razones", f: (f) => h("ul", { clase: "lista-motivos" }, f.motivos.map((m) => h("li", { texto: m }))) }],
      p.pesos, { caption: `Capital ${mxn(p.capital)} · efectivo residual por redondeo ${mxn(p.efectivo_residual)}. Precios de la última cotización disponible (ver fecha y tipo en «Datos»). * SIC: precio de referencia (bolsa de origen × tipo de cambio), no la cotización del SIC; títulos aproximados (≈).` }));
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
  out.push(h("details", { ontoggle: (ev) => { if (ev.target.open && ev.target.children.length === 1) ev.target.append(tabla([{ t: "Instrumento", f: (f) => f.id }, { t: "Motivo", f: (f) => f.motivo }], p.excluidos || [])); } },
    h("summary", { texto: `Instrumentos excluidos (${(p.excluidos || []).length})` })));
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
// SIC: el precio es la bolsa de origen × tipo de cambio (referencia), nunca la cotización del SIC: se marca con «*» y
// los títulos con «≈»; la cifra ejecutable sale del portal.
const esReferenciaSic = (id) => String(id || "").startsWith("SIC:");
const TXT_REF_SIC = "Referencia: bolsa de origen × tipo de cambio; no es la cotización del SIC. Confirme el precio en el portal.";
function precioConMarca(id, precio, fecha) {
  const ref = esReferenciaSic(id);
  return h("span", { title: ref ? TXT_REF_SIC : "" }, mxn(precio, true), ref ? " *" : "", fecha ? h("br") : null,
    fecha ? h("span", { clase: "suave", texto: fecha + (ref ? " · referencia" : "") }) : null);
}
function titulosConMarca(id, t) {
  return t === null || t === undefined ? "—" : (esReferenciaSic(id) ? `≈ ${num(t)}` : num(t));
}
function escenarios(e) {
  if (!e) return h("p", { clase: "vacio", texto: "—" });
  return h("div", {},
    h("div", { clase: "kpis" }, kpi("Favorable (p90)", pct(e.favorable_p90), "positivo"), kpi("Central (p50)", pct(e.central_p50), signo(e.central_p50)), kpi("Adverso (p10)", pct(e.adverso_p10), signo(e.adverso_p10))),
    h("div", { clase: "kpis" }, kpi("Peor mes histórico", pct(e.peor_mes_historico), "negativo"), kpi("Peor trimestre", pct(e.peor_trimestre_historico), "negativo"), kpi("Caída máx. histórica", pct(e.max_caida_historica), "negativo")),
    h("p", { clase: "suave" }, `Estrés hipotético (${e.estres_hipotetico.supuesto}): ${pct(e.estres_hipotetico.impacto)}.`),
    h("p", { clase: "suave", texto: `Horizonte ${e.sesiones_horizonte ? e.sesiones_horizonte + " sesiones" : e.horizonte_anios.toFixed(2) + " años"}. ${e.nota}` }),
    e.saltos_excluidos_de_la_media && e.saltos_excluidos_de_la_media.length ? h("p", { clase: "suave", texto: "Saltos únicos acotados a ±10 % en los percentiles (sí cuentan en peor mes y caída máxima): "
      + e.saltos_excluidos_de_la_media.map((x) => `${x.fecha} ${pct(x.rend)}`).join(", ") }) : null);
}

/* ---------- alertas ---------- */
function pintarCanales() {
  const n = (estado.datos && estado.datos.notificaciones) || {};
  const t = (estado.datos && estado.datos.tiempo_real) || {};
  const si = (x) => (x ? "configurado" : "sin configurar");
  document.getElementById("canales").textContent = `Canales: escritorio ${si(n.escritorio)} · Telegram ${si(n.telegram)} · correo ${si(n.correo)}. ${textoVivo(t)}${t.mensaje ? ` (${t.mensaje})` : ""}.`;
}
document.getElementById("btn-probar-avisos").addEventListener("click", async (ev) => {
  const b = ev.currentTarget;
  ocupado([b], true);
  try {
    const r = (await api("/api/notificaciones/prueba", { method: "POST", json: {} })).resultado;
    const txt = { enviada: "enviado", no_configurado: "sin configurar", error: "error", no_disponible: "no disponible" };
    notificar(`Prueba: ${Object.entries(r).map(([k, v]) => `${k} ${txt[v] || v}`).join(" · ")}.`);
  } catch (e) { notificar(e.message); }
  finally { ocupado([b], false); }
});
async function cargarAlertas() {
  try {
    const d = await api("/api/alertas?limite=200");
    const c = d.configuracion;
    pintarCanales();
    document.getElementById("alertas-config").textContent = `Deriva ≥ ${c.deriva_pp} pp (rearme < ${c.deriva_rearme_pp} pp) con mejora neta ≥ ${pct(c.mejora_neta_min)} · stop ${pct(c.stop_loss)} · toma de utilidad ${pct(c.take_profit)} · caída desde máximo ${pct(c.caida_desde_maximo)} · enfriamiento ${c.enfriamiento_horas} h · ${c.silenciar_fuera_de_horario ? "silencio fuera de horario BMV" : "notifica 24 h"}.`;
    if (!d.alertas.length) return limpiar("alertas-contenido", h("p", { clase: "vacio", texto: "Sin alertas. El motor evalúa las reglas en cada ciclo." }));
    limpiar("alertas-contenido", h("ul", { clase: "alertas" }, d.alertas.map((a) => h("li", { clase: `alerta alerta--${a.severidad}${a.estado !== "nueva" ? " alerta--vista" : ""}` },
      h("h3", { texto: a.titulo }),
      a.ficha ? h("details", { clase: "ficha" }, h("summary", { texto: "Ficha de revisión" }),
        h("dl", {},
          h("dt", { texto: "Qué ocurrió" }), h("dd", { texto: a.ficha.que_ocurrio }),
          h("dt", { texto: "Qué datos lo sustentan" }), h("dd", { texto: Object.entries(a.ficha.datos_que_lo_sustentan).filter(([, v]) => v !== null && v !== undefined && typeof v !== "object").map(([k, v]) => `${k}: ${v}`).join(" · ") }),
          h("dt", { texto: "Qué falta confirmar" }), h("dd", { texto: a.ficha.falta_confirmar.join(" ") }),
          h("dt", { texto: "Costos" }), h("dd", { texto: a.ficha.costos ? `Importe ${mxn(a.ficha.costos.importe, true)} · comisión ${mxn(a.ficha.costos.comision, true)} · IVA ${mxn(a.ficha.costos.iva, true)} · total ${mxn(a.ficha.costos.total, true)}` : "No aplica" }),
          h("dt", { texto: "Riesgos" }), h("dd", { texto: a.ficha.riesgos }),
          h("dt", { texto: "Opciones para revisar" }), h("dd", { texto: a.ficha.opciones_para_revisar.join(" · ") }))) : null,
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
    const [c, tx, cp] = await Promise.all([api("/api/cartera"), api("/api/transacciones?anuladas=true"), api("/api/portal/captura")]);
    estado.cartera = c;
    pintarPortal(cp, c);
    pintarCartera(c, tx.transacciones);
  } catch (e) { limpiar("cartera-contenido", errorCaja(e)); }
}
function pintarPortal(cp, c) {
  const k = cp.captura;
  if (!k) {
    limpiar("portal-resumen", h("div", { clase: "aviso-caja", texto: "Sin saldo confirmado: aún no ha capturado su cuenta del Reto. El plan de acción deja todo como «decisión pendiente» hasta que pegue su portafolio abajo. El registro local de la terminal (sección avanzada) no es su saldo del portal." }));
    return;
  }
  const horas = (Date.now() - new Date(k.hora_portal).getTime()) / 3600000;
  const out = [h("div", { clase: horas > 24 || !cp.vigente ? "aviso-caja" : "info-caja" },
    h("strong", { texto: `Última actualización del portal: ${fechaLocal(k.hora_portal)}` }),
    ` (hace ${horas < 1 ? "menos de 1 h" : `${Math.round(horas)} h`}). ` + (horas > 24 ? "Actualícela después de operar o al cierre de cada sesión." : "")),
  h("div", { clase: "kpis" },
    kpi("Valuación total (portal)", mxn(k.valor_portafolio)), kpi("Poder de compra (portal)", mxn(k.efectivo)),
    kpi("Por liquidar (portal)", mxn(k.por_liquidar || 0)), kpi("Posiciones (portal)", String(k.n_posiciones))),
  h("p", { clase: "suave", texto: `Fuente: ${k.fuente}. Hora del portal: ${fechaLocal(k.hora_portal)}; capturado en la terminal: ${fechaLocal(k.capturado_en)}.` })];
  if (!cp.vigente) out.push(h("div", { clase: "aviso-caja", texto: "Esta captura ya no alimenta las propuestas: pudo cambiar la etapa del Reto o registrarse una operación local después. La terminal usa el registro local hasta recibir una captura nueva." }));
  if (cp.cambios.length) out.push(h("p", {}, h("strong", { texto: "Cambios frente a la captura anterior: " }), cp.cambios.join(" ")));
  out.push(tabla([{ t: "Emisora", f: (f) => f.texto || f.instrumento_id }, { t: "Instrumento", f: (f) => f.instrumento_id },
    { t: "Títulos", f: (f) => num(f.titulos), num: true }, { t: "Costo prom.", f: (f) => mxn(f.costo_promedio, true), num: true },
    { t: "Precio (portal)", f: (f) => mxn(f.precio, true), num: true }, { t: "Valor (portal)", f: (f) => mxn(f.valor), num: true }],
  k.posiciones, { caption: "Tal como se copió del portal. Abajo, la terminal los valúa con sus propios precios.", vacio: "La captura no incluyó posiciones." }));
  limpiar("portal-resumen", ...out);
}
function datosCaptura(f, confirmar) {
  return { texto: f.elements.texto.value, hora_portal: f.elements.hora_portal.value, efectivo: f.elements.efectivo.value,
    por_liquidar: f.elements.por_liquidar.value, valor_portafolio: f.elements.valor_portafolio.value, confirmar };
}
document.getElementById("form-captura").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const f = ev.target;
  try {
    const r = await api("/api/portal/captura", { method: "POST", json: datosCaptura(f, false) });
    const out = [];
    (r.errores || []).forEach((e) => out.push(h("div", { clase: "error-caja", texto: e })));
    (r.advertencias || []).forEach((a) => out.push(h("div", { clase: "aviso-caja", texto: a })));
    out.push(h("div", { clase: "kpis" }, kpi("Valuación total", mxn(r.valor_portafolio)), kpi("Poder de compra", mxn(r.efectivo)),
      kpi("Por liquidar", mxn(r.por_liquidar || 0)), kpi("Inversiones (portal)", mxn(r.invertido)), kpi("Posiciones", String(r.posiciones.length))),
    tabla([{ t: "Copiado", f: (x) => x.texto }, { t: "Instrumento reconocido", f: (x) => x.instrumento_id }, { t: "Títulos", f: (x) => num(x.titulos), num: true },
      { t: "Costo prom.", f: (x) => mxn(x.costo_promedio, true), num: true }, { t: "Precio (portal)", f: (x) => mxn(x.precio, true), num: true },
      { t: "Valor (portal)", f: (x) => mxn(x.valor), num: true }], r.posiciones, { vacio: "Sin posiciones reconocidas." }));
    const dif = r.diferencias || {};
    if ((dif.frente_a_captura_anterior || []).length) out.push(h("p", {}, h("strong", { texto: "Frente a la última captura: " }), dif.frente_a_captura_anterior.join(" ")));
    if ((dif.frente_al_registro_local || []).length) out.push(h("p", {}, h("strong", { texto: "Frente al registro local de la terminal: " }), dif.frente_al_registro_local.join(" ")));
    if (!(r.errores || []).length) {
      out.push(h("p", { clase: "suave", texto: dif.nota || "" }),
        h("button", { type: "button", clase: "boton", onclick: async (e2) => {
          e2.target.disabled = true;
          try {
            const g = await api("/api/portal/captura", { method: "POST", json: datosCaptura(f, true) });
            if (!g.confirmado) { limpiar("captura-previa", ...(g.errores || ["No se guardó."]).map((x) => h("div", { clase: "error-caja", texto: x }))); return; }
            limpiar("captura-previa", h("div", { clase: "info-caja", texto: `Portafolio guardado (hora del portal ${fechaLocal(g.hora_portal)}). El plan de acción y las propuestas ya usan su cuenta confirmada.` }));
            f.reset(); cargarCartera();
          } catch (e3) { limpiar("captura-previa", errorCaja(e3)); }
        } }, "Confirmar y guardar mi portafolio"));
    }
    limpiar("captura-previa", ...out);
  } catch (e) { limpiar("captura-previa", errorCaja(e)); }
});
const COLORES = ["var(--serie-1)", "var(--serie-2)", "var(--sin-datos)", "var(--sintetico)"];
function pintarCartera(c, txs) {
  const out = [];
  out.push(c.fuente === "portal"
    ? h("div", { clase: "info-caja", texto: `Propuestas y alertas usan su cuenta del Reto (captura del ${fechaLocal(c.captura.hora_portal)}) valuada con los precios de la terminal.` + (c.registro_local ? ` El registro local de la terminal (${mxn(c.registro_local.valor_total)}) se conserva aparte.` : "") })
    : h("div", { clase: "aviso-caja", texto: "Registro LOCAL de la terminal: aportaciones y operaciones capturadas a mano. No es el saldo confirmado del portal del Reto." }));
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
      d.noticias, { caption: `Fuente: ${d.fuentes.noticias}; clasificación por léxico (o LLM local si está configurado). Emisoras de EE. UU. en cartera o, sin posiciones, las de la propuesta de referencia. Noticia = hecho reportado; análisis = opinión de un autor; ninguna es una señal.`, vacio: d.cartera.length ? "Sin titulares recientes." : "Registre posiciones para ver titulares de sus emisoras." }),
      h("h2", { texto: "Operaciones de insiders" }),
      insiderEstado && !insiderEstado.configurado ? h("div", { clase: "aviso-caja", texto: "Requiere configuración: defina SEC_USER_AGENT (nombre y correo de contacto) en .env para consultar SEC EDGAR." }) : null,
      tabla([{ t: "Fecha", f: (f) => f.fecha }, { t: "Emisora", f: (f) => f.instrumento_id }, { t: "Persona", f: (f) => `${f.nombre} (${f.cargo || "—"})` },
        { t: "Tipo", f: (f) => ({ P: "Compra", S: "Venta" }[f.codigo] || f.codigo) }, { t: "Acciones", f: (f) => num(f.acciones), num: true },
        { t: "Valor USD", f: (f) => num(f.valor), num: true }, { t: "", f: (f) => externo(f.enlace, "Formulario 4") }],
      d.insiders, { caption: `Fuente: ${d.fuentes.insiders}.`, vacio: "Sin operaciones de insiders registradas." }));
  } catch (e) { limpiar("mercado-contenido", errorCaja(e)); }
}

/* ---------- PASADO · PRESENTE · FUTURO ---------- */
const LAT = { REAL_TIME: "vigente", DELAYED: "retrasado", EOD: "retrasado", UNKNOWN: "sin_datos" };
function celdaPrecioBmv(pb) {
  if (!pb || pb.estado !== "confiable") {
    return h("span", { title: (pb && pb.motivos || []).join(" · ") }, chip("vencido", "SIN PRECIO CONFIABLE"));
  }
  const q = pb.cotizacion;
  return h("span", {}, h("span", { clase: "cifra", texto: `${num(q.precio)} ${q.moneda}` }), " ", chip(LAT[q.estado_latencia], q.estado_latencia),
    h("br"), h("span", { clase: "suave", texto: `${q.proveedor} · ${fechaLocal(q.hora_evento)} · latencia ${q.latencia_medida_s == null ? "—" : `${Math.round(q.latencia_medida_s)} s`}${q.sintetico ? " · FICTICIO" : ""}` }));
}
function celdaReferencia(r) {
  if (!r) return "—";
  return h("span", { title: r.etiqueta }, `${num(r.precio)} USD`, h("br"),
    h("span", { clase: "suave", texto: `≈ ${mxn(r.precio_mxn_estimado, true)} estimado · ${r.estado_latencia} · ${r.proveedor}` }));
}
function pintarPresente(p) {
  const g = p.ganancia, a = p.acciones_operadas;
  limpiar("presente-contenido",
    h("p", { clase: "suave", texto: `Hora ${fechaLocal(p.hora)} (America/Mexico_City) · etapa del Reto: ${ETAPAS[p.etapa_reto] || p.etapa_reto} · cartera: ${p.cartera_de} · BMV ${p.mercado_bmv_abierto ? "abierta" : "cerrada"}` }),
    h("div", { clase: "kpis" }, kpi("Valor estimado", mxn(p.valor_estimado, true)), kpi("Efectivo", mxn(p.efectivo, true)),
      kpi("Ganancia estimada", `${mxn(g.ganancia, true)} (${pct(g.ganancia_pct)})`, signo(g.ganancia)),
      kpi("Comisiones pagadas", mxn(g.comisiones_pagadas, true)), kpi("Comisión si liquidara", mxn(g.comision_salida_estimada, true)),
      kpi("Acciones operadas", `${a.n} de ${a.minimo}`, a.cumple ? "positivo" : "negativo")),
    h("p", { clase: "suave", texto: g.nota }),
    p.saldo_portal ? h("div", {}, h("p", {}, `Portal (${p.saldo_portal.hora_portal}): ${mxn(p.saldo_portal.valor_portafolio, true)} · diferencia de la estimación `,
      h("strong", { texto: pct(p.diferencia_portal) })),
      tabla([{ t: "Concepto", f: (f) => f.c }, { t: "Portal", f: (f) => (vacio(f.p) ? "—" : mxn(f.p, true)), num: true },
        { t: "Terminal", f: (f) => mxn(f.t, true), num: true },
        { t: "Diferencia (% del valor)", f: (f) => (vacio(f.p) ? "—" : pct((f.t - f.p) / p.saldo_portal.valor_portafolio)), num: true }],
      [{ c: "Valor total", p: p.saldo_portal.valor_portafolio, t: p.valor_estimado },
        { c: "Efectivo / poder de compra", p: p.saldo_portal.efectivo, t: p.efectivo },
        { c: "Invertido", p: p.saldo_portal.invertido, t: p.valor_estimado - p.efectivo },
        { c: "Por liquidar (solo portal)", p: p.saldo_portal.por_liquidar, t: 0 }],
      { caption: "Si el efectivo o lo invertido difieren, capture sus posiciones del portal en «Mi portafolio Actinver»: las propuestas usan esta cartera." }))
      : h("p", { clase: "suave", texto: "Aún no se captura el saldo del portal." }),
    tabla([
      { t: "Posición confirmada", f: (f) => h("strong", { texto: f.clave_operable || f.instrumento_id }) },
      { t: "Títulos", f: (f) => num(f.cantidad), num: true },
      { t: "Precio BMV (MXN)", f: (f) => celdaPrecioBmv(f.precio_bmv) },
      { t: "Referencia externa", f: (f) => celdaReferencia(f.referencia_externa) },
      { t: "Valor estimado", f: (f) => mxn(f.valor_estimado, true), num: true },
      { t: "Exposición", f: (f) => pct(f.peso), num: true }],
      p.posiciones, { caption: "El precio BMV solo aparece si una fuente con cobertura verificada lo entrega vigente; la referencia externa es la bolsa de origen convertida a pesos.", vacio: "Sin posiciones confirmadas en esta cartera." }),
    h("h3", { texto: `Alertas activas (${p.alertas_activas.length})` }),
    p.alertas_activas.length ? h("ul", {}, p.alertas_activas.slice(0, 10).map((x) => h("li", { texto: `${x.titulo} — ${x.fuente || ""}` }))) : h("p", { clase: "suave", texto: "Ninguna." }),
    h("h3", { texto: "Proveedores de precios" }),
    tabla([{ t: "Proveedor", f: (f) => f.proveedor }, { t: "Descripción", f: (f) => f.descripcion },
      { t: "Estado", f: (f) => (f.configurado ? chip("vigente", "Configurado") : chip("sin_datos", "Pendiente")) },
      { t: "Pendiente", f: (f) => f.pendientes.join(" · ") || "—" }], p.proveedores),
    h("p", { clase: "suave", texto: p.nota }));
}
function pintarPasado(p) {
  const exps = p.experimentos || [];
  limpiar("pasado-contenido",
    h("p", { clase: "suave", texto: p.descripcion + (p.demo ? " Modo demostración: datos FICTICIOS." : "") }),
    tabla([{ t: "Fuente", f: (f) => f.proveedor }, { t: "Tipo", f: (f) => f.tipo_dato }, { t: "Filas", f: (f) => num(f.filas), num: true },
      { t: "Instrumentos", f: (f) => f.instrumentos, num: true }, { t: "Desde", f: (f) => f.desde }, { t: "Hasta", f: (f) => f.hasta },
      { t: "Último available_at", f: (f) => fechaLocal(f.ultimo_disponible) }], p.fuentes, { caption: "Precios históricos", vacio: "Sin precios históricos." }),
    tabla([{ t: "Fecha", f: (f) => f.fecha }, { t: "Tipo", f: (f) => f.tipo }, { t: "Instrumento", f: (f) => f.instrumento_id || "—" },
      { t: "Títulos", f: (f) => num(f.cantidad), num: true }, { t: "Precio", f: (f) => num(f.precio), num: true },
      { t: "Etapa", f: (f) => f.etapa || "fuera del Reto" }, { t: "Registrada (available_at)", f: (f) => fechaLocal(f.available_at) }],
      p.operaciones_confirmadas, { caption: "Operaciones confirmadas", vacio: "Sin operaciones registradas." }),
    exps.length ? tabla([{ t: "H", f: (f) => f.H, num: true }, { t: "Entrenamiento", f: (f) => (f.cortes.entrenamiento || []).join(" → ") },
      { t: "Validación", f: (f) => (f.cortes.validacion || []).join(" → ") }, { t: "Prueba", f: (f) => (f.cortes.prueba || []).join(" → ") },
      { t: "Embargo", f: (f) => `${f.cortes.embargo_sesiones} ses.`, num: true },
      { t: "Purgados", f: (f) => `${f.purgados.entrenamiento} / ${f.purgados.validacion}` },
      { t: "Variables eliminadas (|r| ≥ 0.95)", f: (f) => (f.variables_eliminadas_final || []).map((x) => `${x.variable}≈${x.conservada}`).join(", ") || "ninguna" },
      { t: "Corr. media entre activos", f: (f) => num(f.correlacion_activos_entrenamiento && f.correlacion_activos_entrenamiento.media), num: true },
      { t: "Semilla · versión", f: (f) => `${f.semilla} · ${f.version_codigo}+${f.huella_config}` }], exps,
      { caption: "Cortes temporales de la investigación (sin barajar). La correlación entre activos es riesgo real: se informa, no se reduce." })
      : h("p", { clase: "suave", texto: "Aún no se ejecuta la investigación." }),
    tabla([{ t: "Publicado", f: (f) => fechaLocal(f.publicado) }, { t: "Conocido (available_at)", f: (f) => fechaLocal(f.available_at) },
      { t: "Emisora", f: (f) => f.instrumento_id }, { t: "Titular", f: (f) => f.titulo }], p.noticias, { caption: "Noticias", vacio: "Sin noticias." }));
}
function pintarFuturo(f) {
  const exps = f.experimentos || [];
  limpiar("futuro-contenido",
    h("div", { clase: f.recomendacion_permitida ? "aviso-caja" : "error-caja", role: "note", texto: `${f.etiqueta}. ${f.aviso}` }),
    ...exps.map((e) => h("div", {},
      h("h3", {}, `Fuera de muestra, H = ${e.H} sesión(es) · ${e.datos} `, chip(e.recomendacion_permitida ? "vigente" : "vencido", e.veredicto || (e.recomendacion_permitida ? "VENTAJA" : "SIN VENTAJA DEMOSTRADA"))),
      tabla([{ t: "Modelo / referencia", f: (m) => m.modelo }, { t: "MSE", f: (m) => (m.mse * 1e4).toFixed(3) + "e-4", num: true },
        { t: "Acierto dirección", f: (m) => pct(m.acierto_direccion), num: true }, { t: "Cobertura 80 %", f: (m) => pct(m.cobertura_intervalo_80), num: true },
        { t: "Brier", f: (m) => num(m.brier_prob_subida), num: true }, { t: "Meses mejor que «sin cambio»", f: (m) => m.meses_mejor_que_sin_cambio },
        { t: "Rotación", f: (m) => num(m.rotacion_media), num: true }, { t: "Neto de costos", f: (m) => pct(m.resultado_neto), num: true }],
        e.prueba, { caption: `${e.conclusion}${e.prueba_ya_vista ? " · Prueba ya vista: resultado no válido para elegir modelo." : ""}` }))),
    tabla([{ t: "Instrumento", f: (p) => p.clave_operable || p.instrumento_id }, { t: "H", f: (p) => p.horizonte, num: true },
      { t: "Desde (cierre)", f: (p) => p.fecha_base }, { t: "Estimación", f: (p) => pct(Math.expm1(p.prediccion)), num: true },
      { t: "Rango 10–90 %", f: (p) => `${pct(Math.expm1(p.p10))} a ${pct(Math.expm1(p.p90))}` },
      { t: "Prob. subida", f: (p) => pct(p.prob_subida), num: true }, { t: "Emitido · datos hasta", f: (p) => `${fechaLocal(p.emitido_en)} · ${fechaLocal(p.datos_hasta)}` }],
      (f.pronosticos || []).slice(0, 60), { caption: "ESTIMACIONES con incertidumbre. No son cotizaciones ni recomendaciones de compra o venta.", vacio: "Sin pronósticos emitidos." }));
}
async function pintarRegistro() {
  try {
    const [b, o] = await Promise.all([api("/api/bitacora"), api("/api/pendientes-portal?todas=true")]);
    limpiar("bitacora-lista", tabla([{ t: "Fecha", f: (f) => fechaLocal(f.creada_en) }, { t: "Tipo", f: (f) => f.tipo },
      { t: "Instrumento", f: (f) => f.instrumento_id || "—" }, { t: "Tesis", f: (f) => f.tesis || "—" },
      { t: "Decisión humana", f: (f) => f.decision_humana }, { t: "Reglas · modelo", f: (f) => `v${f.version_reglas ?? "—"} · ${f.version_modelo || "—"}` }],
      b.entradas, { vacio: "Sin entradas en la bitácora." }));
    limpiar("ordenes-lista", h("p", { clase: "suave", texto: o.nota }), tabla([{ t: "Creada", f: (f) => fechaLocal(f.creada_en) },
      { t: "Instrumento", f: (f) => f.instrumento_id }, { t: "Lado", f: (f) => f.lado }, { t: "Tipo", f: (f) => f.tipo_orden },
      { t: "Cantidad", f: (f) => num(f.cantidad), num: true }, { t: "Límite", f: (f) => num(f.precio_limite), num: true },
      { t: "Estado", f: (f) => f.estado }], o.ordenes, { vacio: "Sin órdenes pendientes registradas." }));
  } catch (e) { limpiar("bitacora-lista", errorCaja(e)); }
}
document.getElementById("form-bitacora").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const f = ev.currentTarget, d = Object.fromEntries(new FormData(f));
  d.fuentes = (d.fuentes || "").split(/\s+/).filter(Boolean);
  try { await api("/api/bitacora", { method: "POST", json: d }); notificar("Decisión registrada en la bitácora."); f.reset(); pintarRegistro(); }
  catch (e) { notificar(e.errores ? e.errores.join(" · ") : e.message); }
});
document.getElementById("form-orden").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const f = ev.currentTarget, d = Object.fromEntries(new FormData(f));
  try { await api("/api/pendientes-portal", { method: "POST", json: d }); notificar("Orden pendiente registrada como referencia (no cambia su cartera)."); f.reset(); pintarRegistro(); }
  catch (e) { notificar(e.errores ? e.errores.join(" · ") : e.message); }
});
const TIPO_PRECIO = { REAL_TIME: "tiempo real", DELAYED: "retrasado", EOD: "cierre diario", UNKNOWN: "sin clasificar", STALE: "vencido" };
function datoPrecio(b) {
  const f = b.fuente_precio;
  if (!f) return h("span", {}, chip("sin_datos", "Sin datos"), h("br"), h("span", { clase: "suave", texto: "sin cotización fiable: no se calcula la orden" }));
  const cal = b.calidad_precio === "STALE" ? "vencido" : (b.calidad_precio === "REAL_TIME" ? "vigente" : "retrasado");
  return h("span", {}, chip(cal, TIPO_PRECIO[b.calidad_precio] || b.calidad_precio), h("br"),
    h("span", { clase: "suave", texto: `${f.proveedor} · ${f.moneda || "MXN"} · ${fechaLocal(f.hora_evento)} · ${TIPO_PRECIO[f.estado_latencia] || f.estado_latencia}` }));
}
async function importarHoja(fd) {
  try {
    const r = await fetch("/api/fondos/hoja", { method: "POST", body: fd, headers: { "X-CSRF-Token": CSRF } });
    const d = await r.json();
    if (!r.ok) throw Object.assign(new Error(d.error || "Error"), { errores: d.errores });
    limpiar("hoja-fondos-resultado", h("div", { clase: "info-caja", texto: d.estado === "al_dia" ? `Ya está al día (valuación ${d.fecha_valuacion}).`
      : `Valuación al ${d.fecha_valuacion}: ${d.asignados} fondos con precio.` + ((d.sin_serie_en_documento || []).length ? ` Sin la serie del universo en el documento: ${d.sin_serie_en_documento.join(", ")}.` : "") }));
  } catch (e) { limpiar("hoja-fondos-resultado", errorCaja(e)); }
}
document.getElementById("form-hoja-fondos").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const fd = new FormData(ev.target);
  if (!fd.get("archivo") || !fd.get("archivo").size) { notificar("Elija el PDF de la hoja de precios."); return; }
  importarHoja(fd);
});
document.getElementById("btn-hoja-descargar").addEventListener("click", () => importarHoja(new FormData()));
async function pintarBoletas() {
  try {
    const d = await api("/api/boletas");
    // Solo una boleta vigente con lado y títulos se puede capturar; el resto se etiqueta y se atenúa.
    const capturable = (b) => b.estado === "vigente" && b.lado && Number(b.cantidad) > 0;
    const estado = (b) => (capturable(b) ? ["vigente", "Capturable"]
      : b.estado === "vigente" ? ["retrasado", b.referencia_condicional ? "Solo guía (sin cotización confiable)" : "Investigar: sin precio"]
        : ({ invalidada: ["vencido", "Invalidada"], caducada: ["sin_datos", "Vencida"], descartada: ["sin_datos", "Descartada"],
          marcada_ejecutada: ["calculada", "Ejecutada"] })[b.estado] || ["sin_datos", b.estado]);
    const orden = (b) => (capturable(b) ? 0 : b.estado === "vigente" ? 1 : b.estado === "marcada_ejecutada" ? 2 : 3);
    const filas = [...d.boletas].sort((a, b) => orden(a) - orden(b)).slice(0, 40);
    const n = filas.filter(capturable).length;
    limpiar("boletas-lista", h("p", { clase: "suave", texto: d.aviso }),
      h("p", { clase: n ? "suave" : "aviso-caja", texto: n ? `${n} boleta(s) capturable(s) arriba; las «Solo guía», vencidas, invalidadas y descartadas NO se capturan.`
        : "Ninguna boleta es capturable ahora: las vigentes son guías sin cotización confiable o ya vencieron." }), tabla([
      { t: "Emisora", f: (b) => h("strong", { texto: b.emisora_serie || b.instrumento_id }) },
      { t: "Estado", f: (b) => { const [c, txt] = estado(b); return h("span", { title: b.motivo_estado || b.estado }, chip(c, txt)); } },
      { t: "Tipo", f: (b) => b.tipo }, { t: "Lado · títulos", f: (b) => (b.lado ? `${b.lado} · ${num(b.cantidad)}` : b.referencia_condicional
        ? h("span", { title: b.referencia_condicional.nota }, `${b.referencia_condicional.lado_sugerido} · ≈ ${num(b.referencia_condicional.titulos_aprox)} (condicional)`) : "—") },
      { t: "Límite", f: (b) => (b.precio_limite ? mxn(b.precio_limite, true) : b.referencia_condicional
        ? `banda ${mxn(b.referencia_condicional.precio_min, true)}–${mxn(b.referencia_condicional.precio_max, true)}` : "—"), num: true },
      { t: "Costo (com.+IVA)", f: (b) => (b.costos ? mxn(b.costos.total, true) : "—"), num: true },
      { t: "Efectivo después", f: (b) => mxn(b.efecto.efectivo_despues, true), num: true },
      { t: "Peso después", f: (b) => pct(b.efecto.peso_emisora_despues), num: true },
      { t: "Rango 10–90 % (estimado)", f: (b) => (b.rango && b.rango.disponible ? `${pct(b.rango.p10)} a ${pct(b.rango.p90)}` : "—") },
      { t: "Precio (fuente · moneda · fecha y hora · tipo)", f: datoPrecio },
      { t: "Falta", f: (b) => { const t = (b.datos_faltantes || []).join(" · "); return t ? h("span", { title: t }, t.length > 120 ? t.slice(0, 117) + "…" : t) : "—"; } },
      { t: "", f: (b) => (b.estado !== "vigente" ? "" : h("span", {},
          capturable(b) ? h("button", { type: "button", clase: "boton boton--secundario", onclick: () => ejecutarBoleta(b) }, "Marcar ejecutada") : null, " ",
          h("button", { type: "button", clase: "boton boton--secundario", onclick: async () => { await api(`/api/boletas/${b.id}/descartar`, { method: "POST", json: {} }); pintarBoletas(); } }, "Descartar"))) }],
      filas, { vacio: "Sin boletas. Genérelas desde la propuesta vigente.", claseFila: (b) => (capturable(b) ? null : "fila-inactiva") }));
  } catch (e) { limpiar("boletas-lista", errorCaja(e)); }
}
async function ejecutarBoleta(b) {
  const folio = window.prompt(`Folio de la confirmación del portal para ${b.emisora_serie}:`);
  if (!folio) return;
  const cantidad = window.prompt("Títulos ejecutados (según la confirmación):", String(b.cantidad));
  const precio = window.prompt("Precio ejecutado (según la confirmación):", String(b.precio_limite));
  const fecha = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Mexico_City" }).format(new Date());
  try { await api(`/api/boletas/${b.id}/ejecutada`, { method: "POST", json: { folio, cantidad, precio, fecha } }); notificar("Operación confirmada registrada."); cargarTiempo(); }
  catch (e) { notificar(e.errores ? e.errores.join(" · ") : e.message); }
}
async function boletasPlanDelDia() {
  try {
    const r = (await api("/api/boletas/generar", { method: "POST", json: { propuesta: "plan_del_dia" } })).resultado[0];
    notificar(`Plan del día (${r.nombre_propuesta}, ${r.puntuacion.toFixed(1)}/100): ${r.numero_ordenes} órdenes a capturar (${r.ordenes_compra} compra · ${r.ordenes_venta} venta)`
      + (r.por_investigar ? ` y ${r.por_investigar} por investigar sin precio` : "") + (r.reemplazadas ? `; se reemplazaron ${r.reemplazadas} boletas anteriores` : "") + ".");
    irA("tab-propuestas"); pintarBoletas();
  } catch (e) { notificar(e.errores ? e.errores.join(" · ") : e.message); }
}
document.getElementById("btn-boletas-plan").addEventListener("click", boletasPlanDelDia);
document.getElementById("btn-boletas-telegram").addEventListener("click", async () => {
  try {
    const r = await api("/api/boletas/telegram", { method: "POST", json: {} });
    notificar(r.resultado.telegram === "enviada" ? "Boletas enviadas por Telegram." : `Telegram: ${r.resultado.telegram || "no configurado"}.`);
  } catch (e) { notificar(e.errores ? e.errores.join(" · ") : e.message); }
});
document.getElementById("btn-boletas").addEventListener("click", async () => {
  try {
    const r = (await api("/api/boletas/generar", { method: "POST", json: { propuesta: clavePropuestaSel() } })).resultado[0];
    notificar(`${r.numero_ordenes} órdenes a capturar (${r.ordenes_compra} compra · ${r.ordenes_venta} venta)` + (r.por_investigar ? ` y ${r.por_investigar} por investigar sin precio` : "") + ".");
    pintarBoletas();
  }
  catch (e) { notificar(e.errores ? e.errores.join(" · ") : e.message); }
});
async function cargarTiempo() {
  pintarRegistro();
  pintarBoletas();
  const [pa, pr, fu] = await Promise.allSettled([api("/api/pasado"), api("/api/presente"), api("/api/futuro")]);
  pa.status === "fulfilled" ? pintarPasado(pa.value) : limpiar("pasado-contenido", errorCaja(pa.reason));
  pr.status === "fulfilled" ? pintarPresente(pr.value) : limpiar("presente-contenido", errorCaja(pr.reason));
  fu.status === "fulfilled" ? pintarFuturo(fu.value) : limpiar("futuro-contenido", errorCaja(fu.reason));
}
document.getElementById("form-portal").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const f = ev.currentTarget, datos = Object.fromEntries(new FormData(f));
  try {
    await api("/api/saldo-portal", { method: "POST", json: datos });
    notificar("Saldo del portal guardado."); f.reset(); cargarTiempo();
  } catch (e) { notificar(e.errores ? e.errores.join(" · ") : e.message); }
});
document.getElementById("btn-investigar").addEventListener("click", async (ev) => {
  const b = ev.currentTarget, st = document.getElementById("investigacion-estado");
  ocupado([b], true); st.textContent = "Calculando (≈1 min por horizonte)…";
  try {
    await api("/api/investigacion/calcular", { method: "POST", json: {} });
    for (let i = 0; i < 90; i++) {
      await new Promise((r) => setTimeout(r, 4000));
      const e = await api("/api/investigacion/estado");
      if (e.estado !== "calculando") { st.textContent = e.estado === "terminado" ? "Listo." : `Error: ${e.resultado}`; break; }
    }
    cargarTiempo();
  } catch (e) { st.textContent = e.message; }
  finally { ocupado([b], false); }
});
async function cargarCobertura() {
  try {
    const d = await api("/api/cobertura");
    const provs = ["bmv_licenciado", "lseg", "ice", "eodhd_bmv", "manual_csv"];
    const est = { verificado: "vigente", pendiente: "sin_datos", no_cubierto: "vencido", no_coincide: "vencido", no_aplica: "sin_datos", sin_verificar: "retrasado" };
    limpiar("cobertura-contenido",
      h("p", { clase: "suave", texto: d.catalogo_simulador_importado ? "Catálogo: lista del simulador importada." : "Catálogo: la lista del simulador aún no se importa; se muestra el universo verificado." }),
      h("p", { clase: "suave", texto: `Latencias medidas: ${d.latencias.length ? d.latencias.map((l) => `${l.proveedor} mediana ${l.mediana_s} s`).join(" · ") : "ninguna todavía"}. Webhook TradingView: ${d.webhook_tradingview.configurado ? "configurado" : "sin secreto (uv run terminal webhook-secreto)"}.` }),
      tabla([{ t: "Instrumento", f: (f) => f.clave_operable }, { t: "Mercado", f: (f) => f.mercado }, { t: "Moneda", f: (f) => f.moneda },
        ...provs.map((p) => ({ t: p, f: (f) => chip(est[f[p]] || "sin_datos", f[p]) }))], d.tabla));
  } catch (e) { limpiar("cobertura-contenido", errorCaja(e)); }
}
document.getElementById("btn-cobertura").addEventListener("click", async (ev) => {
  const b = ev.currentTarget; ocupado([b], true);
  try { await api("/api/cobertura/verificar", { method: "POST", json: {} }); await cargarCobertura(); notificar("Cobertura verificada."); }
  catch (e) { notificar(e.message); } finally { ocupado([b], false); }
});

/* ---------- ranking de todas las acciones ---------- */
estado.rankingFiltro = "ambos";
async function cargarRanking() {
  segmentado("selector-ranking", estado.rankingFiltro, (v) => { estado.rankingFiltro = v; cargarRanking(); });
  try {
    const d = await api(`/api/ranking?mercado_filtro=${estado.rankingFiltro}`);
    document.getElementById("ranking-aviso").textContent = `${d.aviso} Criterio: 30 % rendimiento 20 sesiones, 30 % rendimiento 60 sesiones, 20 % estabilidad, 20 % tendencia.`;
    document.getElementById("ranking-hora").textContent = `Actualizado ${fechaLocal(new Date().toISOString())} · ${d.n} de ${d.universo} emisoras con historia suficiente. Se refresca cada minuto.`;
    limpiar("ranking-contenido", tabla([
      { t: "#", f: (f) => f.posicion, num: true },
      { t: "Emisora", f: (f) => h("span", {}, h("strong", { texto: f.clave_operable }), h("br"), h("span", { clase: "suave", texto: f.nombre })) },
      { t: "Mercado", f: (f) => f.mercado },
      { t: "Puntuación", f: (f) => h("span", {}, h("span", { clase: "cifra", texto: f.puntuacion.toFixed(1) }), " ", barraPct(f.puntuacion, 100)), num: true },
      { t: "Precio MXN", f: (f) => h("span", { title: f.precio_es_referencia ? "Referencia: bolsa de origen × tipo de cambio (no es el precio SIC)" : "" }, mxn(f.precio_mxn, true), f.precio_es_referencia ? " *" : ""), num: true },
      { t: "1 día", f: (f) => h("span", { clase: signo(f.rend_1) }, pct(f.rend_1)), num: true },
      { t: "5 días", f: (f) => h("span", { clase: signo(f.rend_5) }, pct(f.rend_5)), num: true },
      { t: "20 días", f: (f) => h("span", { clase: signo(f.rend_20) }, pct(f.rend_20)), num: true },
      { t: "60 días", f: (f) => h("span", { clase: signo(f.rend_60) }, pct(f.rend_60)), num: true },
      { t: "Volatilidad", f: (f) => pct(f.vol_60), num: true },
      { t: "Caída 60 d", f: (f) => pct(f.caida_60), num: true },
      { t: "Seeking Alpha", f: (f) => (f.calificacion_sa ? h("span", { title: `Autores ${f.calificacion_sa.autores ?? "—"} · Wall Street ${f.calificacion_sa.wall_street ?? "—"} · importada ${f.calificacion_sa.fecha}` }, `Quant ${f.calificacion_sa.quant ?? "—"}`) : "—") },
      { t: "Dato", f: (f) => h("span", {}, chip(f.vigencia), h("br"), h("span", { clase: "suave", texto: `${f.tipo_dato || "—"} · ${f.fecha || "—"} · ${f.proveedor || "—"}` })) }],
      d.filas, { caption: "* Precio de referencia de la bolsa de origen convertido a pesos; no es la cotización del SIC."
        + (d.fuera_del_catalogo ? ` Se omiten ${d.fuera_del_catalogo} instrumento(s) que no aparecen en el catálogo de su simulador.` : ""), vacio: "Sin emisoras con al menos 61 sesiones de precio." }));
  } catch (e) { limpiar("ranking-contenido", errorCaja(e)); }
}
setInterval(() => { if (pestanaVisible("panel-ranking")) cargarRanking(); }, 60000);

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
function avisoReglas(r) {
  const v = r && r.version_reglas;
  if (!v || !v.discrepancia) return null;
  return h("div", { clase: "error-caja", role: "alert" }, `${v.aviso} (versión ${v.version}, huella ${v.huella}). `,
    h("button", { type: "button", clase: "boton boton--secundario", onclick: async () => { await api(`/api/reto/reglas/${v.version}/revisada`, { method: "POST", json: {} }); cargarReto(); } }, "Marcar como revisadas"));
}
async function cargarReto() {
  try {
    const r = await api("/api/reto");
    estado.reto = r;
    if (!r.activo) return limpiar("reto-contenido", h("p", { clase: "vacio", texto: "Reglas del Reto desactivadas (config/reto.yaml → activo: false)." }));
    const reglas = Object.entries(r.reglas || {});
    limpiar("reto-contenido", avisoReglas(r),
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
    f.elements.mercado_acciones.value = d.perfil.mercado_acciones || "ambos";
    f.elements.criterio_plan.value = d.perfil.criterio_plan || "puntuacion";
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
    mercado_acciones: f.elements.mercado_acciones.value, criterio_plan: f.elements.criterio_plan.value,
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
  pintarResumen(); if (pestanaVisible("panel-propuestas")) pintarDetalle();
}
async function recalcular() {
  const botones = [document.getElementById("btn-calcular"), document.getElementById("btn-calcular-movil")];
  ocupado(botones, true);
  botones.forEach((b) => { b.dataset.t = b.textContent; b.textContent = "Calculando 4 propuestas…"; });
  try {
    const d = await api("/api/propuestas/calcular", { method: "POST", json: {} });
    estado.propuestas = d.propuestas; estado.clasificacion = d.clasificacion;
    await cargarEstado(); pintarResumen(); if (pestanaVisible("panel-propuestas")) pintarDetalle();
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
  try { inicial = localStorage.getItem("pestana"); if (localStorage.getItem("mas") === "1") mostrarSecundarias(true); } catch { /* sin almacenamiento */ }
  // Carga inicial en paralelo y un solo pintado (menos recálculos de estilo y diseño).
  const [e, r, p, c, a] = await Promise.allSettled([api("/api/estado"), api("/api/reto"), api("/api/propuestas"),
    api("/api/cartera"), api("/api/alertas?limite=5")]);
  const valor = (x) => (x.status === "fulfilled" ? x.value : null);
  estado.reto = valor(r);
  estado.cartera = valor(c);
  estado.alertasResumen = valor(a) && valor(a).alertas;
  if (valor(p)) { estado.propuestas = valor(p).propuestas; estado.clasificacion = valor(p).clasificacion; }
  await cargarEstado(valor(e) || undefined);
  ajustarCampos();
  pintarResumen();
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
