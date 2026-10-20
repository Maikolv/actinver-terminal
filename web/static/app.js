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
  const clase = (c) => [c.num ? "num" : null, c.clase].filter(Boolean).join(" ") || null;
  const cab = h("tr", {}, columnas.map((c) => h("th", { scope: "col", clase: clase(c), texto: c.t })));
  const cuerpo = filas.map((f) => h("tr", { clase: claseFila ? claseFila(f) : null }, columnas.map((c) => {
    const v = c.f(f);
    return h("td", { clase: clase(c) }, v instanceof Node ? v : (v ?? "—"));
  })));
  return h("div", { clase: "tabla-contenedor", tabindex: "0", role: "region", "aria-label": caption || "Tabla desplazable" }, h("table", {}, caption ? h("caption", { texto: caption }) : null,
    h("thead", {}, cab), h("tbody", {}, cuerpo)));
}
function limpiar(id, ...hijos) { const el = document.getElementById(id); el.replaceChildren(...hijos.filter((x) => x != null && x !== false)); return el; }  // null/false: nada (antes se pintaba «null»)
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

document.getElementById("btn-detalle-datos").addEventListener("click", (ev) => {
  const abierto = document.getElementById("estado-datos").classList.toggle("abierto");
  ev.currentTarget.setAttribute("aria-expanded", String(abierto));
  ev.currentTarget.textContent = abierto ? "Ocultar detalle de datos" : "Ver detalle de datos";
});

/* Descarta respuestas antiguas: si el usuario cambia rápido de instrumento, solo se pinta la carga más reciente. */
const turnos = {};
function turno(clave) { const n = (turnos[clave] = (turnos[clave] || 0) + 1); return () => turnos[clave] === n; }

/* ---------- pestañas (teclado: flechas, Inicio, Fin) ---------- */
const CARGAS = {
  "tab-resumen": () => pintarResumen(), "tab-propuestas": () => pintarDetalle(), "tab-alertas": () => cargarAlertas(), "tab-cartera": () => cargarCartera(), "tab-mercado": () => cargarMercado(),
  "tab-universo": () => { cargarUniverso(); cargarCobertura(); }, "tab-tiempo": () => cargarTiempo(),
  "tab-investigacion": () => cargarCentroInvestigacion(),
  "tab-ranking": () => cargarRanking(), "tab-perfil": () => { cargarReto(); cargarPerfil(); },
  "tab-movimientos": () => cargarMovimientos(), "tab-robustez": () => cargarRobustez(),
};
const navPestanas = document.querySelector(".pestanas");
/* Pestañas agrupadas por tarea: el grupo elegido muestra solo sus pestañas (CSS por data-grupo). */
const ultimaDeGrupo = {};
function elegirGrupo(g) {
  navPestanas.dataset.grupo = g;
  document.querySelectorAll(".grupos-nav [data-grupo]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.grupo === g)));
  if (typeof flechasPestanas === "function") requestAnimationFrame(flechasPestanas);
}
document.querySelectorAll(".grupos-nav [data-grupo]").forEach((b) => b.addEventListener("click", () => {
  const g = b.dataset.grupo;
  activarPestana(document.getElementById(ultimaDeGrupo[g] || "") || document.querySelector(`[role="tab"][data-grupo="${g}"]`));
}));
elegirGrupo(navPestanas.dataset.grupo);
/* Flechas para las pestañas que no caben: solo aparecen si hay desbordamiento hacia ese lado. */
const listaPestanas = document.getElementById("lista-pestanas");
function flechasPestanas() {
  const max = listaPestanas.scrollWidth - listaPestanas.clientWidth;
  document.querySelectorAll(".desplazar-pestanas").forEach((b) => {
    b.hidden = b.dataset.dir === "-1" ? listaPestanas.scrollLeft <= 1 : listaPestanas.scrollLeft >= max - 1;
  });
}
document.querySelectorAll(".desplazar-pestanas").forEach((b) => b.addEventListener("click", () =>
  listaPestanas.scrollBy({ left: Number(b.dataset.dir) * listaPestanas.clientWidth * 0.7 })));
listaPestanas.addEventListener("scroll", flechasPestanas, { passive: true });
window.addEventListener("resize", flechasPestanas);
function activarPestana(tab, enfocar, cargar = true) {
  elegirGrupo(tab.dataset.grupo); ultimaDeGrupo[tab.dataset.grupo] = tab.id;
  const previo = document.querySelector('[role="tabpanel"]:not([hidden])');
  if (cargar && previo && typeof compartirSimbolo === "function") compartirSimbolo(previo.id, tab.id);
  document.querySelectorAll('[role="tab"]').forEach((t) => {
    const sel = t === tab;
    t.setAttribute("aria-selected", sel); t.tabIndex = sel ? 0 : -1;
    document.getElementById(t.getAttribute("aria-controls")).hidden = !sel;
  });
  tab.scrollIntoView({ block: "nearest", inline: "nearest" });
  if (enfocar) tab.focus();
  try { localStorage.setItem("pestana", tab.id); } catch { /* sin almacenamiento */ }
  const destino = new URL(location.href); destino.searchParams.set("vista", tab.id);
  history.replaceState(null, "", destino);
  document.dispatchEvent(new CustomEvent("terminal:pestana", {detail:tab.id}));
  if (cargar && CARGAS[tab.id]) CARGAS[tab.id]();
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

/* Barra de comandos: navega por secciones o abre una gráfica del universo local. */
const ATAJOS = { INV: "tab-investigacion", MOD: "tab-modelos", MER: "tab-mercado", ROB: "tab-robustez",
  CAR: "tab-cartera", DAT: "tab-universo", AL: "tab-alertas", PRO: "tab-propuestas" };
const barraComandos = document.getElementById("barra-comandos");
document.addEventListener("keydown", (ev) => {
  if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "k") {
    ev.preventDefault(); barraComandos.focus(); barraComandos.select();
  }
});
barraComandos.addEventListener("keydown", (ev) => {
  if (ev.key === "Escape") { barraComandos.value = ""; barraComandos.blur(); }
});
document.getElementById("form-comandos").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const entrada = barraComandos.value.trim().toUpperCase();
  if (!entrada) return;
  if (entrada.startsWith("/")) {
    const tab = ATAJOS[entrada.slice(1)];
    if (!tab) { notificar("Comando desconocido. Use /INV, /MOD, /MER, /ROB, /CAR, /DAT, /AL o /PRO."); return; }
    irA(tab); barraComandos.value = ""; return;
  }
  if (!/^[A-Z0-9._-]{1,24}$/.test(entrada)) { notificar("Escriba una clave de instrumento válida."); return; }
  try {
    if (!estado.universo) estado.universo = (await api("/api/universo")).instrumentos;
    const encontrados = estado.universo.filter((i) => String(i.id).toUpperCase() === entrada || String(i.clave_operable || "").toUpperCase() === entrada);
    if (encontrados.length !== 1) {
      notificar(encontrados.length ? "La clave coincide con varios instrumentos. Escriba su identificador exacto." : "Ese símbolo no está en el universo local.");
      return;
    }
    if (!encontrados[0].grafica) { notificar("Ese instrumento no tiene gráfica disponible."); return; }
    window.location.assign(`/grafica/${encodeURIComponent(encontrados[0].id)}`);
  } catch (e) { notificar(e.message); }
});

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
    h("div", { clase: "acciones-boletas" },
      h("button", { type: "button", clase: "boton", onclick: (ev) => boletasTelegram(ev.currentTarget, true) }, "Generar boletas y enviarlas por Telegram"),
      " ", h("button", { type: "button", clase: "boton boton--secundario", onclick: (ev) => boletasTelegram(ev.currentTarget, false) }, "Ver el texto sin enviar"),
      " ", h("button", { type: "button", clase: "boton boton--texto", onclick: () => irA("tab-tiempo") }, "Boletas en detalle")),
    h("div", { id: "resultado-boletas-telegram", "aria-live": "polite" }));
}
async function boletasTelegram(boton, enviar) {
  ocupado([boton], true);
  limpiar("resultado-boletas-telegram", h("p", { clase: "cargando", texto: enviar ? "Generando y enviando boletas…" : "Generando boletas…" }));
  try {
    const r = await api("/api/boletas/telegram", { method: "POST", json: { generar: true, enviar } });
    const c = r.conteo || {};
    const estadoTg = r.resultado ? r.resultado.telegram : null;
    const cab = enviar
      ? (estadoTg === "enviada" ? ["info-caja", `Enviadas por Telegram: ${c.listas} lista(s), ${c.condicionales} condicional(es) del SIC y ${c.por_investigar} por investigar.`]
        : ["error-caja", `Telegram: ${estadoTg || "no configurado"}. Revise TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en .env.`])
      : ["info-caja", `Vista previa (no se envió): ${c.listas} lista(s), ${c.condicionales} condicional(es) y ${c.por_investigar} por investigar.`];
    limpiar("resultado-boletas-telegram", h("div", { clase: cab[0], texto: cab[1] }),
      h("details", { open: !enviar }, h("summary", { texto: "Texto de las boletas" }), h("pre", { clase: "lectura-ocr", texto: r.texto })));
    if (enviar) notificar(estadoTg === "enviada" ? "Boletas enviadas por Telegram." : `Telegram: ${estadoTg || "no configurado"}.`);
  } catch (e) { limpiar("resultado-boletas-telegram", errorCaja(e)); }
  finally { ocupado([boton], false); }
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
async function pintarNube() {
  try {
    const n = await api("/api/nube/estado");
    const tit = h("h2", {}, "Monitor en la nube ", chip(n.activo ? "vigente" : (n.configurado ? "vencido" : "sin_datos"),
      n.activo ? "Activo" : (n.configurado ? "Inactivo" : "No configurado")));
    if (!n.configurado) return limpiar("nube-estado", tit, h("p", { clase: "suave", texto: n.mensaje }));
    const filas = [["Última sincronización", n.ultima_sincronizacion || "—"], ["Última ejecución en la nube", n.ultima_ejecucion || "—"],
      ["Próxima revisión", n.proxima_revision || "—"], ["Quién envía las alertas ahora", n.relevo_texto || "—"],
      ["Telegram en la nube", n.telegram_configurado ? "configurado" : "sin configurar"],
      ["Tipo de cambio que usa", n.fx ? `FIX ${n.fx.valor} del ${n.fx.fecha}` : "—"]];
    limpiar("nube-estado", tit, h("p", { clase: "suave", texto: n.mensaje + (n.error ? ` (${n.error})` : "") }),
      tabla([{ t: "Concepto", f: (f) => f[0] }, { t: "Valor", f: (f) => f[1] }], filas),
      (n.suspendidas || []).length ? tabla([{ t: "Alerta suspendida en la nube", f: (s) => s.alerta }, { t: "Motivo", f: (s) => s.motivo }], n.suspendidas)
        : h("p", { clase: "suave", texto: "Ninguna alerta suspendida en la nube." }),
      h("p", {}, h("button", { type: "button", clase: "boton boton--secundario", onclick: async () => {
        try { const r = await api("/api/nube/sincronizar", { method: "POST", json: {} }); notificar(r.ok ? "Sincronizado con la nube." : `No se sincronizó: ${r.error || r.motivo}`); pintarNube(); }
        catch (e) { notificar(e.message); } } }, "Sincronizar ahora")));
  } catch (e) { limpiar("nube-estado", h("h2", { texto: "Monitor en la nube" }), errorCaja(e)); }
}
async function cargarAlertas() {
  pintarNube();
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
/* Capturas de pantalla → texto (OCR local de Windows en el servidor de esta PC; las imágenes no se guardan) */
function horaLocalAhora() {
  return new Intl.DateTimeFormat("sv-SE", { timeZone: "America/Mexico_City", year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit" }).format(new Date()).replace(" ", "T");
}
async function leerCapturas(archivos) {
  const imgs = [...archivos].filter((a) => /^image\/(png|jpeg)$/.test(a.type)).slice(0, 6);
  if (!imgs.length) { notificar("Use capturas PNG o JPG."); return; }
  const fd = new FormData();
  imgs.forEach((a, i) => fd.append("imagenes", a, a.name || `captura-${i + 1}.png`));
  limpiar("resultado-capturas", h("p", { clase: "cargando", texto: `Leyendo ${imgs.length} captura(s)… (unos segundos por imagen)` }));
  try {
    const r = await fetch("/api/portal/capturas-imagen", { method: "POST", body: fd, headers: { "X-CSRF-Token": CSRF } });
    const d = await r.json();
    if (!r.ok) throw new Error((d.errores || []).join(" · ") || d.detail || d.error || "No se pudieron leer las capturas.");
    const f = document.getElementById("form-captura");
    f.elements.texto.value = d.texto;
    const sinHora = !f.elements.hora_portal.value;
    if (sinHora) f.elements.hora_portal.value = horaLocalAhora();
    limpiar("resultado-capturas",
      h("div", { clase: "info-caja", texto: `${d.imagenes} captura(s) leída(s): ${d.n_posiciones} posición(es)` + (Object.keys(d.resumen || {}).length ? ` y ${Object.keys(d.resumen).join(", ")}` : "") +
        `. Compare el texto con su captura${sinHora ? " y ajuste la hora a la que tomó la captura" : ""}; abajo está la vista previa.` }),
      ...(d.avisos || []).map((a) => h("div", { clase: "aviso-caja", texto: a })),
      (d.lectura || []).length ? h("details", {}, h("summary", { texto: "Ver lo que leyó el OCR (filas tal cual)" }),
        h("pre", { clase: "lectura-ocr", texto: d.lectura.join("\n") })) : null);
    if (d.texto) f.querySelector('[data-accion="previa"]').click();
  } catch (e) { limpiar("resultado-capturas", errorCaja(e)); }
}
(() => {
  const zona = document.getElementById("zona-capturas"), entrada = document.getElementById("archivo-capturas");
  zona.addEventListener("click", () => entrada.click());
  zona.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); entrada.click(); } });
  entrada.addEventListener("change", () => { if (entrada.files.length) leerCapturas(entrada.files); entrada.value = ""; });
  zona.addEventListener("dragover", (ev) => { ev.preventDefault(); zona.classList.add("encima"); });
  zona.addEventListener("dragleave", () => zona.classList.remove("encima"));
  zona.addEventListener("drop", (ev) => { ev.preventDefault(); zona.classList.remove("encima"); leerCapturas(ev.dataTransfer.files); });
  document.addEventListener("paste", (ev) => {  // Ctrl+V de una captura mientras se ve «Mi portafolio Actinver»
    if (document.getElementById("panel-cartera").hidden) return;
    const imgs = [...(ev.clipboardData ? ev.clipboardData.files : [])].filter((a) => a.type.startsWith("image/"));
    if (imgs.length) { ev.preventDefault(); leerCapturas(imgs); }
  });
})();
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
let visuales = null;
const filtroMapa = { mercado: "todos", clase: "todos", sector: "todos", proveedor: "todos", ventana: 1 };
let visualSeleccion = null;

function intensidadMapa(v) {
  if (v === null || v === undefined) return "sin-dato";
  const nivel = Math.abs(v) >= .04 ? 3 : Math.abs(v) >= .015 ? 2 : 1;
  return `${v >= 0 ? "sube" : "baja"}-${nivel}`;
}

function filtroSelect(clave, etiqueta, valores, nombres = {}) {
  const sel = h("select", { "aria-label": `Filtrar mapa por ${etiqueta.toLowerCase()}` },
    h("option", { value: "todos" }, "Todos"), ...valores.map((v) => h("option", { value: v }, nombres[v] || v)));
  sel.value = filtroMapa[clave];
  sel.addEventListener("change", () => { filtroMapa[clave] = sel.value; pintarMapaMercado(); });
  return h("label", {}, `${etiqueta} `, sel);
}

function fichaCelda(c) {
  const fila = (t, v) => [h("dt", { texto: t }), h("dd", { texto: v ?? "—" })];
  const botonVelas = esReferenciaSic(c.id) ? h("button", { type: "button", clase: "boton boton--secundario", texto: "Abrir velas OHLCV",
    onclick: () => { flujo.velas.simbolo = c.id; irA("tab-velas"); } }) : null;
  return h("section", { clase: "ficha-celda", "aria-label": `Detalle de ${c.clave}` },
    h("h3", { texto: `${c.clave} · ${c.nombre || ""}` }),
    h("dl", {}, fila("Variación", c.variacion == null ? "no disponible" : pct(c.variacion)),
      fila("Método", visuales.metodo),
      fila("Cierre usado", `${num(c.cierre)} ${c.moneda} (${c.fecha})`),
      fila("Cierre de comparación", c.cierre_anterior == null ? "—" : `${num(c.cierre_anterior)} ${c.moneda} (${c.fecha_anterior})`),
      fila("Ajuste por split", c.ajuste_split ? "sí: precios ajustados por un split en el periodo" : "no fue necesario"),
      fila("Fuente", `${c.proveedor} · tipo ${c.tipo_dato}`),
      fila("Captura", `${fechaLocal(c.obtenido_en)} (${visuales.zona_horaria})`),
      fila("Rezago", `${c.dias_calendario} día(s) calendario desde el cierre`),
      fila("Calidad", visuales.modo === "sintetico" ? "DATOS SINTÉTICOS de demostración" : "cierre histórico local; no es tiempo real ni la cotización del simulador"),
      fila("Mercado · clase · sector", `${c.mercado || "—"} · ${CLASES[c.clase] || c.clase || "—"} · ${c.sector || "—"}`)),
    h("div", { clase: "fila-controles" },
      h("button", { type: "button", clase: "boton boton--secundario", texto: "Ver cierres e indicadores", onclick: () => cargarSerieMercado(c.id) }),
      botonVelas,
      c.grafica ? h("a", { href: `/grafica/${encodeURIComponent(c.id)}`, target: "_blank", rel: "noopener", clase: "boton boton--secundario", texto: "Velas de TradingView (externo)" }) : null));
}

function pintarMapaMercado() {
  const raiz = document.getElementById("mercado-visualizaciones");
  if (!visuales) return;
  const unicos = (k) => [...new Set(visuales.celdas.map((c) => c[k] || "Sin dato"))].sort();
  const pasa = (c) => ["mercado", "clase", "sector", "proveedor"].every((k) => filtroMapa[k] === "todos" || (c[k] || "Sin dato") === filtroMapa[k]);
  const visibles = visuales.celdas.filter(pasa);
  const selVentana = h("select", { "aria-label": "Ventana de la variación" }, visuales.ventanas.map((v) => h("option", { value: v }, v === 1 ? "1 sesión" : `${v} sesiones`)));
  selVentana.value = String(filtroMapa.ventana);
  selVentana.addEventListener("change", () => { filtroMapa.ventana = Number(selVentana.value); cargarVisualizacionesMercado(); });
  const sel = visuales.celdas.find((c) => c.id === visualSeleccion);
  const tarjetas = visibles.map((c) => h("button", {
    type: "button", clase: `mercado-tile mercado-tile--${intensidadMapa(c.variacion)}`, "aria-pressed": String(c.id === visualSeleccion),
    title: `${c.nombre || c.clave}. Fuente ${c.proveedor}; cierre ${c.fecha}; rezago ${c.dias_calendario} día(s) calendario.`,
    "aria-label": `${c.clave}: ${c.variacion == null ? "variación no disponible" : pct(c.variacion)} en ${filtroMapa.ventana} sesión(es); cierre del ${c.fecha}`,
    onclick: () => { visualSeleccion = c.id; pintarMapaMercado(); },
  }, h("strong", { texto: c.clave || c.id }),
  h("span", { texto: c.variacion == null ? "—" : `${c.variacion > 0 ? "+" : ""}${pct(c.variacion)}` }),
  h("small", { texto: c.fecha })));
  const escala = h("div", { clase: "escala-mapa", "aria-label": "Escala de colores" }, h("span", { clase: "suave", texto: "Escala:" }),
    ...[["baja-3", "≤ −4 %"], ["baja-2", "−4 a −1.5 %"], ["baja-1", "−1.5 a 0 %"], ["sube-1", "0 a 1.5 %"], ["sube-2", "1.5 a 4 %"], ["sube-3", "≥ 4 %"], ["sin-dato", "sin dato"]]
      .map(([k, t]) => h("span", { clase: `mercado-tile--${k}`, texto: t })),
    h("span", { clase: "suave", texto: "(azul sube, naranja baja; también se indica el signo)" }));
  limpiar("mercado-visualizaciones", h("h2", { texto: "Mapa de calor de cierres" }),
    visuales.modo === "sintetico" ? h("div", { clase: "aviso-caja", texto: "DATOS SINTÉTICOS de demostración: no son precios reales." }) : null,
    h("p", { clase: "ayuda", texto: `${visuales.metodo} ${visuales.nota}` }),
    h("div", { clase: "fila-controles" }, h("label", {}, "Ventana ", selVentana),
      filtroSelect("mercado", "Mercado", unicos("mercado")), filtroSelect("clase", "Clase", unicos("clase"), CLASES),
      filtroSelect("sector", "Sector", unicos("sector")), filtroSelect("proveedor", "Proveedor", unicos("proveedor"))),
    escala,
    h("p", { clase: "suave", texto: `${visibles.length} de ${visuales.total} instrumentos con cierre. Seleccione uno para ver su ficha.` }),
    sel ? fichaCelda(sel) : null,
    visibles.length ? h("div", { clase: "mercado-mapa" }, ...tarjetas) : h("p", { clase: "vacio", texto: "No hay cierres disponibles con estos filtros." }),
    h("div", { id: "mercado-indicadores" }));
}

async function cargarSerieMercado(iid) {
  visualSeleccion = iid;
  const destino = document.getElementById("mercado-indicadores");
  if (!destino) return;
  destino.replaceChildren(h("p", { clase: "suave", texto: "Cargando cierres e indicadores…" }));
  try {
    const d = await api(`/api/visualizaciones/serie/${encodeURIComponent(iid)}`);
    if (visualSeleccion !== iid || !destino.isConnected) return;
    const ultimo = d.puntos[d.puntos.length - 1];
    const celda = visuales.celdas.find((c) => c.id === iid);
    destino.replaceChildren(h("h3", { texto: `${d.clave} · cierres e indicadores` }),
      h("p", { clase: "ayuda", texto: d.nota }),
      d.puntos.length ? grafica([
        { nombre: `Cierre (${d.moneda})`, color: "var(--acento)", datos: d.puntos.map((p) => ({ x: p.fecha, y: p.cierre })) },
        { nombre: "Media móvil 20 sesiones", color: "var(--retrasado)", datos: d.puntos.map((p) => ({ x: p.fecha, y: p.media_20 })) },
      ], { formato: num, etiqueta: `Cierres y media móvil de ${d.clave}` }) : h("p", { clase: "vacio", texto: "Sin cierres históricos disponibles." }),
      ultimo ? h("p", { clase: "ayuda", texto: `RSI de 14 sesiones (Wilder): ${ultimo.rsi_14 == null ? "sin historia suficiente" : num(ultimo.rsi_14)} · Fuente: ${d.proveedor} · fecha del cierre: ${d.fecha} · captura: ${fechaLocal(d.obtenido_en)} (America/Mexico_City) · rezago: ${celda?.dias_calendario ?? "sin dato"} día(s) calendario · calidad: cierre histórico local, sin verificación intradía. ${d.modo === "sintetico" ? "DATOS SINTÉTICOS." : "No es precio en tiempo real."}` }) : null);
  } catch (e) { if (destino.isConnected) destino.replaceChildren(errorCaja(e)); }
}

async function cargarVisualizacionesMercado() {
  try {
    visuales = await api(`/api/visualizaciones/mercado?ventana=${filtroMapa.ventana}`);
    pintarMapaMercado();
  } catch (e) { limpiar("mercado-visualizaciones", errorCaja(e)); }
}

async function cargarMercado() {
  try {
    cargarVisualizacionesMercado();
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
const signoPct = (x) => (vacio(x) ? "—" : `${x > 0 ? "+" : ""}${pct(x)}`);
function pintarReto(r) {
  if (!r || !r.emision) return h("p", { clase: "suave", texto: "Aún no hay pronóstico al cierre del Reto: pulse «Calcular investigación y pronósticos» (2–3 min)." });
  const e = r.emision, b = r.barrera, c = r.cartera, q = r.calidad, hz = r.horizonte, pr = r.propuestas;
  const tit = r.etiqueta === "reto" ? `Al cierre del Reto (${hz.hasta}, ${hz.H} sesiones de la BMV)` : `A ${hz.H} sesiones`;
  return h("div", {},
    h("h3", {}, `${tit} `, chip(b.permitida ? "vigente" : "vencido", b.leyenda)),
    h("p", { clase: "suave", texto: `Emitido ${fechaLocal(e.emitido_en)} · último cierre usado ${e.ultimo_cierre} · disponible desde ${fechaLocal(e.datos_hasta)} · modelo ${e.version} (${e.modelo}) · en ${e.moneda}. ${r.uso_en_decisiones}` }),
    tabla([{ t: "Criterio de la barrera", f: (x) => x.criterio }, { t: "", f: (x) => chip(x.cumple ? "vigente" : "vencido", x.cumple ? "Cumple" : "No cumple") },
      { t: "Detalle", f: (x) => x.detalle }], b.criterios,
      { caption: "Para influir en compras, ventas o boletas, el pronóstico debe superar fuera de muestra y después de costos a «sin cambio», a pesos iguales y a la estrategia actual." }),
    h("div", { clase: "kpis" }, kpi(c.conciliada ? "Cartera del portal (hoy)" : "Cartera local NO conciliada (hoy)", mxn(c.valor_actual, true)),
      kpi("Estimado al objetivo (escenario central)", mxn(c.central, true), signo(c.central - c.valor_actual)),
      kpi("Rango conservador 10–90 %", `${mxn(c.p10, true)} a ${mxn(c.p90, true)}`)),
    c.aviso ? h("div", { clase: "aviso-caja", role: "note", texto: c.aviso }) : h("p", { clase: "suave", texto: `Posiciones y efectivo de la captura del portal (${fechaLocal(c.hora_portal)}).` }),
    h("p", { clase: "suave", texto: c.nota + (c.sin_pronostico.length ? ` Sin pronóstico (se mantienen a su valor): ${c.sin_pronostico.map((x) => x.instrumento_id).join(", ")}.` : "") }),
    tabla([{ t: "Emisora", f: (x) => h("strong", { texto: x.clave }) }, { t: "Mercado", f: (x) => x.mercado },
      { t: "OBSERVADO: cierre base (MXN)", f: (x) => h("span", { title: x.fuente_precio_base }, `${num(x.precio_base)} · ${x.fecha_base}`), num: true },
      { t: "ESTIMADO al objetivo (MXN)", f: (x) => num(x.precio_central), num: true },
      { t: "ESCENARIOS 10 % / 90 % (MXN)", f: (x) => `${num(x.precio_p10)} / ${num(x.precio_p90)}` },
      { t: "Rendimiento estimado", f: (x) => signoPct(x.rend_central), num: true },
      { t: "Rango 10–90 %", f: (x) => `${signoPct(x.rend_p10)} a ${signoPct(x.rend_p90)}` },
      { t: q && q.prob_experimental === false ? "Prob. subida" : "Prob. subida (experimental)",
        f: (x) => (q && q.prob_experimental === false ? pct(x.prob_subida) : h("span", { clase: "suave" }, pct(x.prob_subida))), num: true },
      { t: "Estado", f: (x) => chip(x.vencido ? "vencido" : "calculada", x.vencido ? `Vencido (${x.atraso_sesiones} ses.)` : "Estimación") }],
      r.emisoras.slice(0, 80), { caption: r.aviso, claseFila: (x) => (x.vencido ? "fila-inactiva" : null) }),
    tabla([{ t: "Propuesta frente al pronóstico", f: (x) => x.nombre }, { t: "Puntuación", f: (x) => (vacio(x.puntuacion) ? "—" : x.puntuacion.toFixed(1)), num: true },
      { t: "Estimado neto", f: (x) => signoPct(x.rend_estimado_neto), num: true }, { t: "Costo rebalanceo", f: (x) => pct(x.costo_rebalanceo), num: true },
      { t: "Rango 10–90 %", f: (x) => `${signoPct(x.rango_p10)} a ${signoPct(x.rango_p90)}` },
      { t: "Peso con pronóstico", f: (x) => pct(x.peso_con_pronostico), num: true }, { t: "SIC (incluye tipo de cambio)", f: (x) => pct(x.peso_sic), num: true },
      { t: "Reglas del Reto", f: (x) => (x.cumple_reto == null ? "—" : chip(x.cumple_reto ? "vigente" : "vencido", x.cumple_reto ? "Cumple" : "No cumple")) },
      { t: "Simulador", f: (x) => x.simulador }, { t: "Escenario del optimizador", f: (x) => signoPct(x.escenario_optimizador), num: true }],
      pr.filas, { caption: `${pr.explicacion} ${pr.nota}` }),
    r.cambios.hay_anterior ? tabla([{ t: "Mayor cambio vs. emisión anterior", f: (x) => x.instrumento_id },
      { t: "Antes", f: (x) => signoPct(x.antes), num: true }, { t: "Ahora", f: (x) => signoPct(x.ahora), num: true },
      { t: "Prob. subida", f: (x) => `${pct(x.prob_antes)} → ${pct(x.prob_ahora)}` }], r.cambios.filas,
      { caption: `Frente a la emisión del ${fechaLocal(r.cambios.emitido_anterior)}${r.cambios.version_cambio ? " (cambió la versión del modelo)" : ""}.` })
      : h("p", { clase: "suave", texto: r.cambios.texto }),
    q ? h("div", {},
      q.calibracion_aviso ? h("div", { clase: "aviso-caja", role: "note", texto: q.calibracion_aviso }) : null,
      h("h4", { texto: `Calidad histórica fuera de muestra (H = ${q.H}, prueba ${(q.cortes && q.cortes.prueba || []).join(" → ")}): ${q.veredicto}` }),
      tabla([{ t: "Mercado", f: (m) => m.mercado }, { t: "Emisoras", f: (m) => m.instrumentos, num: true }, { t: "Ejemplos", f: (m) => num(m.n), num: true },
        { t: "Error / «sin cambio»", f: (m) => num(m.mse / m.mse_sin_cambio), num: true }, { t: "Acierto dirección", f: (m) => pct(m.acierto_direccion), num: true }],
        q.por_mercado, { caption: "Por mercado (BMV y SIC): un cociente ≥ 1 significa que el modelo no mejora a «sin cambio»." }),
      tabla([{ t: "Probabilidad estimada", f: (m) => m.tramo }, { t: "n", f: (m) => num(m.n), num: true },
        { t: "Media estimada", f: (m) => pct(m.prob_media), num: true }, { t: "Frecuencia observada de subida", f: (m) => pct(m.frecuencia_subida), num: true }],
        q.calibracion || [], { caption: `Calibración de la probabilidad de subida: ${q.prob_experimental === false ? "calibrada" : "EXPERIMENTAL, no es señal de compra"} (${q.prob_resumen}). Cobertura del rango 80 %: ${pct(q.cobertura_80)} · Brier ${num(q.brier)} · rotación ${num(q.rotacion_media)} · caída máxima ${pct(q.caida_maxima)} · neto de costos ${signoPct(q.resultado_neto)}.` }),
      q.historia_insuficiente.length ? h("p", { clase: "suave", texto: `Sin historia suficiente (no se ocultan): ${q.historia_insuficiente.map((x) => `${x.instrumento_id} (${x.sesiones}/${x.minimo})`).join(", ")}.` }) : null)
      : null,
    (r.sin_datos || []).length ? h("p", { clase: "suave", texto: `Sin precios en la terminal (sin pronóstico): ${r.sin_datos.join(", ")}.` }) : null);
}
function pintarFuturo(f) {
  const exps = f.experimentos || [];
  limpiar("futuro-contenido",
    h("div", { clase: f.recomendacion_permitida ? "aviso-caja" : "error-caja", role: "note", texto: `${f.etiqueta}. ${f.aviso}` }),
    pintarReto(f.reto),
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
document.getElementById("btn-pronostico-telegram").addEventListener("click", async () => {
  try {
    const r = await api("/api/pronostico/telegram", { method: "POST", json: {} });
    notificar(r.resultado.telegram === "enviada" ? "Pronóstico enviado por Telegram." : `Telegram: ${r.resultado.telegram || "no configurado"}.`);
  } catch (e) { notificar(e.errores ? e.errores.join(" · ") : e.message); }
});
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
estado.rankingClase = "acciones";
/* ---------- Movimientos públicos (SEC EDGAR: Form 4 y 13F) ---------- */
const GRUPO_CHIP = { cartera: "vigente", propuesta: "calculada", seguimiento: "retrasado", "operable en el Reto": "sin_datos" };
const enlaceSec = (url, texto) => h("a", { href: url, target: "_blank", rel: "noopener noreferrer", texto: texto || "documento SEC" });
const usd = (v) => (vacio(v) ? "—" : `${num(Math.round(v))} USD`);
async function cargarMovimientos(filtros) {
  const q = new URLSearchParams(Object.entries(filtros || {}).filter(([, v]) => v)).toString();
  try {
    const d = await api(`/api/movimientos${q ? `?${q}` : ""}`);
    const sel = document.getElementById("mov-gestor");
    if (sel.options.length <= 1) d.gestores.forEach((g) => sel.append(h("option", { value: g.cik, texto: g.nombre })));
    const ids = [...new Set([...d.form4, ...d.trece_f].map((r) => r.instrumento_id).filter(Boolean))].sort();
    limpiar("mov-emisoras", ...ids.map((i) => h("option", { value: i })));
    limpiar("mov-fuentes", tabla([{ t: "Fuente", f: (f) => f.fuente }, { t: "Estado", f: (f) => chip(f.estado === "vigente" ? "vigente" : f.estado === "antigua" ? "retrasado" : "vencido", f.estado) },
      { t: "Última consulta correcta", f: (f) => fechaLocal(f.ultimo_ok) }, { t: "Explicación", f: (f) => f.explicacion }], d.fuentes,
      { caption: d.aviso }));
    limpiar("mov-seguimiento", "Seguimiento: ", ...(d.seguimiento.length ? d.seguimiento.map((s) => h("span", { clase: "chip chip--retrasado" }, s.instrumento_id, " ",
      h("button", { type: "button", clase: "enlace", title: `Quitar ${s.instrumento_id}`, onclick: async () => { await api(`/api/seguimiento/${encodeURIComponent(s.instrumento_id)}`, { method: "DELETE" }); cargarMovimientos(filtros); } }, "×"))) : ["(vacía)"]), " ");
    const grupo = (r) => chip(GRUPO_CHIP[r.grupo] || "sin_datos", r.grupo);
    const fechas = (r, primera) => h("span", {}, primera, h("br"), h("span", { clase: "suave", texto: `publicado ${r.fecha_presentacion} (${fechaLocal(r.aceptado_en)}) · conocido ${fechaLocal(r.conocido_en)}` }));
    limpiar("mov-contenido",
      h("h2", { texto: `Insiders · Form 4 (${d.form4.length})` }),
      tabla([{ t: "Grupo", f: grupo }, { t: "Emisora", f: (r) => h("strong", { texto: r.clave || r.simbolo || r.emisor }) },
        { t: "Movimiento", f: (r) => h("span", { title: `${r.codigo}: ${r.descripcion}` }, chip(r.discrecional ? (r.clasificacion === "compra_mercado" ? "vigente" : "vencido") : "sin_datos", r.tipo),
          r.tipo_documento === "4/A" ? " (4/A)" : "", r.corregido_por ? h("span", { clase: "suave", texto: " · corregido por 4/A" }) : "") },
        { t: "Declarante", f: (r) => r.declarantes.map((x) => `${x.nombre} (${x.relacion})`).join("; ") },
        { t: "Títulos · precio", f: (r) => h("span", {}, `${num(r.titulos)} · ${vacio(r.precio_usd) ? "—" : `${num(r.precio_usd)} USD`}`, h("br"),
          h("span", { clase: "suave", texto: `≈ ${usd(r.valor_usd)} · titularidad ${r.titularidad || "—"}${r.referencia_mxn ? ` · ${mxn(r.referencia_mxn.valor, true)} (${r.referencia_mxn.etiqueta})` : ""}` })), num: true },
        { t: "Operación · publicación · conocido", clase: "col-fechas", f: (r) => fechas(r, `operación ${r.fecha_operacion || "—"}`) },
        { t: "Evidencia y límites", clase: "col-texto", f: (r) => h("span", {}, enlaceSec(r.url), " · ", enlaceSec(r.url_indice, "índice"), h("br"), h("span", { clase: "suave", texto: r.limite })) }],
        d.form4.slice(0, 150), { vacio: "Sin operaciones de insiders con estos filtros (o la fuente aún no se consulta).", claseFila: (r) => (r.discrecional ? null : "fila-inactiva") }),
      h("h2", { texto: `Institucionales · 13F (${d.trece_f.length})` }),
      tabla([{ t: "Grupo", f: grupo }, { t: "Emisora", clase: "col-corta", f: (r) => h("span", { title: `CUSIP ${r.cusip} · ${r.clase}` }, h("strong", { texto: r.simbolo || r.emisor }),
          h("br"), h("span", { clase: "suave", texto: r.simbolo ? `${r.emisor} (${r.clase})` : (r.candidatos ? `clases: ${r.candidatos}` : `CUSIP ${r.cusip}`) })) },
        { t: "Gestor", f: (r) => r.gestor },
        { t: "Cambio inferido", f: (r) => h("span", {}, chip(r.clasificacion === "nueva" || r.clasificacion === "aumento" ? "vigente" : r.clasificacion === "salida" || r.clasificacion === "reduccion" ? "vencido" : "sin_datos", r.tipo),
          r.antiguo ? h("span", { clase: "suave", texto: " · ANTIGUO" }) : "", r.nota ? h("br") : "", r.nota ? h("span", { clase: "suave", texto: r.nota }) : "") },
        { t: "Títulos (previo → actual)", f: (r) => `${num(Math.round(r.titulos_previo_ajustado))} → ${num(Math.round(r.titulos))}`, num: true },
        { t: "Valor declarado", f: (r) => usd(r.valor_usd), num: true },
        { t: "Corte · publicación · conocido", clase: "col-fechas", f: (r) => fechas(r, `corte ${r.periodo_previo || "—"} → ${r.periodo}`) },
        { t: "Evidencia y límites", clase: "col-texto", f: (r) => h("span", {}, ...r.documentos.flatMap((x, i) => [i ? " · " : "", enlaceSec(x.url, x.tipo + (x.tipo_enmienda ? ` (${x.tipo_enmienda})` : ""))]),
          h("br"), h("span", { clase: "suave", texto: [r.limite, ...r.documentos.map((x) => x.nota).filter(Boolean)].join(" ") })) }],
        d.trece_f.slice(0, 200), { vacio: "Sin cambios 13F con estos filtros.", claseFila: (r) => (r.antiguo ? "fila-inactiva" : null) }));
  } catch (e) { limpiar("mov-contenido", errorCaja(e)); }
}
document.getElementById("form-mov").addEventListener("submit", (ev) => {
  ev.preventDefault();
  cargarMovimientos(Object.fromEntries(new FormData(ev.currentTarget)));
});
document.getElementById("btn-mov-actualizar").addEventListener("click", async () => {
  try {
    await api("/api/movimientos/actualizar", { method: "POST", json: {} });
    notificar("Consultando la SEC (incremental, ≤ 5 peticiones por segundo)…");
    const t = setInterval(async () => {
      try {
        const e = await api("/api/movimientos/estado");
        if (e.estado !== "actualizando") { clearInterval(t); notificar(e.estado === "terminado" ? "SEC consultada." : `SEC: ${e.estado}`); cargarMovimientos(); }
      } catch (e) { clearInterval(t); notificar(e.message); }
    }, 4000);
  } catch (e) { notificar(e.message); }
});
document.getElementById("btn-mov-seguir").addEventListener("click", async () => {
  const i = document.getElementById("mov-seg-id").value.trim();
  if (!i) return;
  try { await api("/api/seguimiento", { method: "POST", json: { instrumento_id: i } }); document.getElementById("mov-seg-id").value = ""; cargarMovimientos(); }
  catch (e) { notificar(e.errores ? e.errores.join(" · ") : e.message); }
});
/* ---------- Robustez (histórico fuera de muestra + simulación; no es pronóstico) ---------- */
const robustezSel = { tipo: "acciones", par: 0, filtro: "mediana", metrica: "R" };
const METRICAS_ROB = { R: "Rend. anual fuera de muestra", exceso_1N: "Exceso vs 1/N", S: "Estabilidad S",
  prob_perdida: "MC: prob. de pérdida", ret_p5: "MC: rend. p5", caida_p5: "MC: caída p5", aprobada: "Aprobada (1 = sí)" };
const NOMBRE_PARAM = { aversion: "λ aversión", tope: "Tope por activo", historia: "Historia (sesiones)" };
const PARES_ROB = ["aversion|tope", "aversion|historia", "tope|historia"];
const MOTIVOS_ROB = { exceso_vs_1N: "no supera a 1/N", prob_perdida: "prob. de pérdida > 45 %",
  caida_p5: "caída p5 < −20 %", estabilidad: "inestable (S < 0.6)", no_pico_aislado: "pico aislado" };
function celdaColor(v, lo, hi, invertir, texto) {
  // el color se asigna por la propiedad style (la política CSP bloquea el atributo style en línea)
  const td = h("td", { clase: "num" }, texto);
  if (!vacio(v) && hi !== lo) {
    let t = (v - lo) / (hi - lo);
    if (invertir) t = 1 - t;
    td.style.backgroundColor = `hsl(${Math.round(10 + 110 * t)} 55% 42% / 0.55)`;
  }
  return td;
}
async function cargarRobustez() {
  segmentado("selector-robustez", robustezSel.tipo, (v) => { robustezSel.tipo = v; cargarRobustez(); });
  try { pintarRobustez(await api(`/api/robustez?tipo=${robustezSel.tipo}`)); }
  catch (e) { limpiar("robustez-contenido", errorCaja(e)); }
}
function pintarRobustez(r) {
  if (r.estado !== "ok") return limpiar("robustez-contenido", h("p", { clase: "aviso-caja", texto: r.mensaje || r.motivo || r.estado }));
  const f = r.fechas, w = r.walk_forward, e = r.elegida;
  const mapasPar = r.mapas.filter((m) => `${m.y}|${m.x}` === PARES_ROB[robustezSel.par]);
  const mapa = mapasPar.find((m) => String(m.filtro_valor) === String(robustezSel.filtro)) || mapasPar[mapasPar.length - 1];
  const celdas = mapa.celdas[robustezSel.metrica];
  const vals = celdas.flat().filter((v) => !vacio(v));
  const lo = Math.min(...vals), hi = Math.max(...vals), invertir = robustezSel.metrica === "prob_perdida";
  const fmt = (v) => (robustezSel.metrica === "S" || robustezSel.metrica === "aprobada" ? num(v) : pct(v));
  const sel = (id, opciones, valor, alCambiar) => h("select", { id, onchange: (ev) => alCambiar(ev.target.value) },
    ...opciones.map(([v, t]) => h("option", { value: v, selected: String(v) === String(valor) }, t)));
  const params = (x) => (x ? `λ ${x.aversion} · tope ${pct(x.tope)} · historia ${x.historia}` : "—");
  const fichas = [...(e ? [{ nombre: "Elegida (meseta)", ...e }] : []),
    ...Object.entries(r.actuales).map(([k, v]) => ({ nombre: `Actual: ${k.replaceAll("_", " ")}`, ...v }))];
  const wf = [["Encadenado: selección anidada", w.encadenado.anidado], ["Encadenado: estrategia actual", w.encadenado.actual],
    ["Encadenado: 1/N", w.encadenado.iguales_1N], ["Encadenado: mediana SPP", w.encadenado.mediana_SPP],
    ["Tramo intacto: selección anidada", w.intacto.anidado], ["Tramo intacto: estrategia actual", w.intacto.actual],
    ["Tramo intacto: 1/N", w.intacto.iguales_1N], ["Tramo intacto: mediana SPP", w.intacto.mediana_SPP]].map(([nombre, x]) => ({ nombre, ...x }));
  limpiar("robustez-contenido",
    h("div", { clase: r.veredicto === "MESETA" ? "aviso-caja" : "error-caja", role: "note" },
      h("strong", {}, r.veredicto === "MESETA" ? "Hay una región estable de parámetros. " : "No hay región robusta. "),
      `Walk-forward anidado: ${w.evidencia}. ${r.aviso}`),
    h("p", { clase: "suave", texto: `Datos ${f.datos.desde} → ${f.datos.hasta} · fuera de muestra ${f.oos_desde} → ${f.oos_hasta} (${r.cobertura.sesiones_oos} sesiones) · tramo intacto ${f.intacto_desde} → ${f.intacto_hasta} (${r.cobertura.sesiones_intacto}) · universo ${r.cobertura.universo} instrumentos (${r.cobertura.excluidos} excluidos) · ${r.combinaciones} combinaciones × ${r.simulaciones_por_combinacion.join("/")} simulaciones · horizonte ${r.horizonte_sesiones} sesiones (cierre del Reto) · calculado en ${r.recursos.segundos} s.` }),
    tabla([{ t: "", f: (x) => h("strong", {}, x.nombre) }, { t: "Parámetros", f: (x) => params(x.params) },
      { t: "HISTÓRICO: rend. anual", f: (x) => pct(x.oos?.R), num: true }, { t: "Exceso vs 1/N", f: (x) => pct(x.oos?.exceso_1N), num: true },
      { t: "Caída máx.", f: (x) => pct(x.oos?.D), num: true }, { t: "Estabilidad S", f: (x) => num(x.S), num: true },
      { t: "SIMULACIÓN al cierre: p5 / p50 / p95", f: (x) => (x.montecarlo ? `${pct(x.montecarlo.ret_p5)} / ${pct(x.montecarlo.ret_p50)} / ${pct(x.montecarlo.ret_p95)}` : "—") },
      { t: "Prob. pérdida", f: (x) => pct(x.montecarlo?.prob_perdida), num: true }, { t: "Caída p5", f: (x) => pct(x.montecarlo?.caida_p5), num: true },
      { t: "Veredicto", f: (x) => chip(x.aprobada ? "vigente" : "vencido", x.aprobada ? "Aprobada" : (x.pico_aislado ? "Pico aislado" : "Rechazada")) },
      { t: "Motivos de rechazo", f: (x) => (x.motivos_rechazo || []).map((m) => MOTIVOS_ROB[m] || m).join(", ") || "—" }], fichas,
      { caption: `SPP (todas las combinaciones): mediana ${pct(r.spp.mediana_R)}/año; ${pct(r.spp.pct_supera_1N)} superan a 1/N; aprobadas ${pct(r.pct_aprobadas)}.` + (e ? ` Distancia de la elegida al borde de su región: ${r.distancia_borde} paso(s).` : "") }),
    tabla([{ t: "Walk-forward anidado (histórico)", f: (x) => x.nombre }, { t: "Sesiones", f: (x) => num(x.sesiones), num: true },
      { t: "Rend. anual", f: (x) => pct(x.anual), num: true }, { t: "Acumulado", f: (x) => pct(x.acum), num: true },
      { t: "Caída máx.", f: (x) => pct(x.caida_max), num: true }], wf,
      { caption: `${w.fronteras} fronteras; en cada una se elige solo con las 252 sesiones anteriores. Tramo intacto evaluado una vez (elegida: ${params(w.intacto.elegida)}).` }),
    tabla([{ t: "Región", f: (x) => x.tipo }, { t: "Tamaño", f: (x) => num(x.tamano), num: true },
      { t: "Rend. medio", f: (x) => pct(x.R_media), num: true }, { t: "Dispersión (desv.)", f: (x) => pct(x.R_desv), num: true },
      { t: "Rango", f: (x) => `${pct(x.R_rango[0])} a ${pct(x.R_rango[1])}` }], r.regiones.slice(0, 6),
      { caption: "Regiones contiguas de combinaciones aprobadas (vecindad: un paso en un solo parámetro). Meseta: ≥ 5 combinaciones.", vacio: "Ninguna combinación aprueba los cinco umbrales." }),
    h("div", { clase: "fila-controles" },
      h("label", {}, "Par ", sel("rob-par", [[0, "λ × tope"], [1, "λ × historia"], [2, "tope × historia"]], robustezSel.par, (v) => { robustezSel.par = Number(v); robustezSel.filtro = "mediana"; pintarRobustez(r); })),
      h("label", {}, `${NOMBRE_PARAM[mapa.filtro_dim]} `, sel("rob-filtro", mapasPar.map((m) => [m.filtro_valor, m.filtro_valor === "mediana" ? "mediana (SPP)" : m.filtro_valor]), robustezSel.filtro, (v) => { robustezSel.filtro = v; pintarRobustez(r); })),
      h("label", {}, "Métrica ", sel("rob-metrica", Object.entries(METRICAS_ROB), robustezSel.metrica, (v) => { robustezSel.metrica = v; pintarRobustez(r); }))),
    h("div", { clase: "tabla-contenedor" }, h("table", { clase: "mapa-calor" },
      h("caption", {}, `${METRICAS_ROB[robustezSel.metrica]}: filas ${NOMBRE_PARAM[mapa.y]}, columnas ${NOMBRE_PARAM[mapa.x]}${invertir ? " (verde = menor)" : " (verde = mayor)"}.`),
      h("thead", {}, h("tr", {}, h("th", {}, ""), ...mapa.eje_x.map((x) => h("th", { scope: "col" }, String(x))))),
      h("tbody", {}, ...celdas.map((fila, i) => h("tr", {}, h("th", { scope: "row" }, String(mapa.eje_y[i])),
        ...fila.map((v) => celdaColor(v, lo, hi, invertir, vacio(v) ? "—" : fmt(v)))))))));
}
async function cargarRanking() {
  segmentado("selector-ranking", estado.rankingFiltro, (v) => { estado.rankingFiltro = v; cargarRanking(); });
  segmentado("selector-ranking-clase", estado.rankingClase, (v) => { estado.rankingClase = v; cargarRanking(); });
  const vigente = turno("ranking");
  try {
    const d = await api(`/api/ranking?mercado_filtro=${estado.rankingFiltro}&clase=${estado.rankingClase}`);
    if (!vigente()) return;
    const corta = d.filas.some((f) => f.historia_corta);
    document.getElementById("ranking-aviso").textContent = `${d.aviso} Criterio: 30 % rendimiento 20 sesiones, 30 % rendimiento 60 sesiones, 20 % estabilidad, 20 % tendencia; percentiles dentro de la clase elegida.`
      + (corta ? " Fondos con historia corta: las columnas «20 días» y «60 días» usan las ventanas indicadas en cada fila (no son comparables con 20 y 60 sesiones)." : "");
    document.getElementById("ranking-hora").textContent = `Actualizado ${fechaLocal(new Date().toISOString())} · ${d.n} de ${d.universo} instrumentos con historia suficiente. Se refresca cada minuto.`;
    limpiar("ranking-contenido", tabla([
      { t: "#", f: (f) => f.posicion, num: true },
      { t: "Instrumento", f: (f) => h("span", {}, h("strong", { texto: f.clave_operable }), h("br"), h("span", { clase: "suave", texto: f.nombre }),
        f.historia_corta ? h("span", {}, h("br"), chip("retrasado", `historia corta: ${f.sesiones} sesiones (ventanas ${f.ventanas[0]} y ${f.ventanas[1]})`)) : null) },
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
        + (d.fuera_del_catalogo ? ` Se omiten ${d.fuera_del_catalogo} instrumento(s) que no aparecen en el catálogo de su simulador.` : ""), vacio: estado.rankingClase === "fondos" ? "Sin fondos con al menos 11 sesiones de valor liquidativo." : "Sin instrumentos con al menos 61 sesiones de precio." }));
  } catch (e) { if (vigente()) limpiar("ranking-contenido", errorCaja(e)); }
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
  try { inicial = localStorage.getItem("pestana"); } catch { /* sin almacenamiento */ }
  const solicitada = new URLSearchParams(location.search).get("vista");
  const candidata = document.getElementById(solicitada || inicial || "");
  inicial = candidata?.matches('[role="tab"]') ? candidata.id : "tab-resumen";
  activarPestana(document.getElementById(inicial), false, false);
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
  const tab = document.querySelector('[role="tab"][aria-selected="true"]');
  if (tab && tab.id !== "tab-resumen") activarPestana(tab);
  setInterval(() => { if (!document.hidden) cargarEstado(); }, 60000); // detecta ciclos del motor y alertas nuevas
  document.addEventListener("visibilitychange", () => { if (!document.hidden) cargarEstado(); });
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

/* ---------- centro de investigación ---------- */
async function cargarCentroInvestigacion() {
  const simbolo = document.getElementById("form-investigacion-filtro").elements.simbolo.value.trim().toUpperCase();
  document.getElementById("investigacion-exportar").href = "/api/centro-investigacion/exportar?simbolo=" + encodeURIComponent(simbolo);
  try {
    const d = await api("/api/centro-investigacion?simbolo=" + encodeURIComponent(simbolo));
    const estados = { lista: "Lista para consultar", requiere_clave: "Falta clave", desactivada: "Desactivada", consulta_manual: "Consulta e importación", conector_existente: "Conector de precios existente" };
    const porId = new Map(d.fuentes.map((f) => [f.id, f]));
    const historial = document.getElementById("form-investigacion-filtro").elements.historial.checked;
    const vistos = new Set();
    const visibles = historial ? d.observaciones : d.observaciones.filter((x) => {
      const clave = `${x.fuente}:${x.simbolo}:${x.serie}:${x.origen}`;
      if (vistos.has(clave)) return false;
      vistos.add(clave); return true;
    });
    limpiar("investigacion-contenido",
      h("p", { clase: "ayuda", texto: d.nota }),
      d.modo === "demo" ? h("p", { clase: "aviso", texto: "Modo demostración: no se consultan APIs ni se importan registros reales." }) : document.createDocumentFragment(),
      h("h2", { texto: "Indicadores y notas" }),
      tabla([
        { t: "Fuente / método", f: (x) => `${(porId.get(x.fuente) || {}).nombre || x.fuente} · ${x.origen === "manual" ? "importación manual" : "API oficial"}` },
        { t: "Símbolo", f: (x) => x.simbolo || "Economía / energía" },
        { t: "Indicador", f: (x) => x.titulo },
        { t: "Período", f: (x) => x.periodo },
        { t: "Valor", num: true, f: (x) => x.valor === null ? "—" : `${num(x.valor)} ${x.unidad}` },
        { t: "Conocido aquí desde", f: (x) => fechaLocal(x.disponible_desde) },
        { t: "Última comprobación", f: (x) => `${fechaLocal(x.confirmado_en)}${x.requiere_actualizacion ? " · requiere actualización" : ""}${x.referencia_atrasada ? " · referencia atrasada" : ""}` },
        { t: "Notas / fuente", f: (x) => h("div", {}, h("p", { texto: x.texto }), x.hora_fuente ? h("p", { clase: "suave", texto: "Hora de la referencia: " + fechaLocal(x.hora_fuente) }) : null, externo(x.url, "Consultar fuente")) },
    ], visibles, { vacio: "Aún no hay registros. Actualice las fuentes disponibles o importe hallazgos con la plantilla." }),
      h("h2", { texto: "Herramientas y acceso" }),
      tabla([
        { t: "Herramienta", f: (x) => h("div", {}, externo(x.url, x.nombre), h("p", { clase: "suave", texto: `Identificador: ${x.id}` })) },
        { t: "Uso en su cartera", f: (x) => x.aplicacion },
        { t: "Vía / estado", f: (x) => h("div", {}, h("p", { texto: x.via }), chip("sin_datos", estados[x.estado]), x.ultima_consulta ? h("p", { texto: `${x.ultima_consulta.estado} · ${fechaLocal(x.ultima_consulta.intento_en)} · ${x.ultima_consulta.mensaje}` }) : null) },
        { t: "Acceso", f: (x) => h("div", {}, h("p", { texto: x.acceso }), externo(x.registro, "Acceso a la herramienta"), document.createTextNode(" · "), externo(x.documentacion, "Documentación")) },
      ], d.fuentes)
    );
  } catch (e) { limpiar("investigacion-contenido", errorCaja(e)); }
}
document.getElementById("form-investigacion-filtro").addEventListener("submit", (ev) => {
  ev.preventDefault(); cargarCentroInvestigacion();
});
document.getElementById("btn-investigacion-actualizar").addEventListener("click", async (ev) => {
  const b = ev.currentTarget;
  ocupado([b], true);
  limpiar("investigacion-estado", h("p", { texto: "Consultando fuentes disponibles…" }));
  try {
    const d = await api("/api/centro-investigacion/actualizar", { method: "POST", json: {} });
    const detalle = Object.entries(d.fuentes).map(([k, v]) => `${k}: ${v.estado}`).join(" · ");
    limpiar("investigacion-estado", h("p", { texto: d.estado === "demo_sin_consultas" ? "Modo demostración: no se consultaron fuentes reales." : `${d.nuevos} registros nuevos. ${detalle}` }));
    await cargarCentroInvestigacion();
  } catch (e) { limpiar("investigacion-estado", errorCaja(e)); }
  finally { ocupado([b], false); }
});
document.getElementById("form-investigacion-importar").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const f = ev.target, b = f.querySelector("button");
  ocupado([b], true);
  try {
    const d = await api("/api/centro-investigacion/importar", { method: "POST", body: new FormData(f) });
    limpiar("investigacion-estado", h("p", { texto: `${d.nuevos} registros nuevos. ${d.nota}` }));
    await cargarCentroInvestigacion(); f.reset();
  } catch (e) { limpiar("investigacion-estado", errorCaja(e)); }
  finally { ocupado([b], false); }
});

/* ---------- modelo cuantitativo de opciones ---------- */
document.getElementById("form-opciones").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const f = ev.currentTarget, boton = f.querySelector('button[type="submit"]');
  const cuerpo = { tipo: f.elements.tipo.value };
  for (const clave of ["spot", "strike", "dias", "volatilidad_pct", "tasa_pct", "dividendo_pct"]) {
    cuerpo[clave] = Number(f.elements[clave].value);
  }
  if (f.elements.prima_mercado.value.trim()) cuerpo.prima_mercado = Number(f.elements.prima_mercado.value);
  ocupado([boton], true);
  try {
    const r = await api("/api/modelos/opciones", { method: "POST", json: cuerpo });
    limpiar("modelo-opciones-resultado", h("section", { clase: "tarjeta" },
      h("h2", { texto: `${r.modelo} · ${r.tipo.toUpperCase()}` }),
      h("div", { clase: "kpis" },
        kpi("Precio teórico", num(r.precio_teorico)),
        kpi(r.volatilidad_implicita ? "Volatilidad implícita" : "Volatilidad ingresada", `${num(r.volatilidad_pct)} %`),
        kpi("Delta", num(r.delta)), kpi("Gamma", num(r.gamma)),
        kpi("Vega / +1 p. p.", num(r.vega_por_1pct)),
        kpi("Theta / día", num(r.theta_por_dia)),
        kpi("Rho / +1 p. p.", num(r.rho_por_1pct))),
      h("p", { clase: "ayuda", texto: r.nota })));
  } catch (e) { limpiar("modelo-opciones-resultado", errorCaja(e)); }
  finally { ocupado([boton], false); }
});

/* ---------- Velas, Order Flow y Option Flow (terminal/flujo): solo datos reales o importados ---------- */
const flujo = { estado: null, velas: { simbolo: "", intervalo: "1Day", dias: 180, sma: true, boll: false, vwap: false, ema20: false, ema50: false, sar: false, macd: false, estoc: false },
  of: { simbolo: "", minutos: 240, niveles: 20, pasoAmt: .25 }, op: { subyacente: "", filtros: {} } };
const fmtHora = new Intl.DateTimeFormat("es-MX", { timeZone: "America/Mexico_City", dateStyle: "short", timeStyle: "medium" });
const horaCdmx = (iso) => { if (!iso) return "—"; const d = new Date(iso); return Number.isNaN(d.getTime()) ? iso : `${fmtHora.format(d)} CDMX`; };
const retrasoTexto = (sg) => (vacio(sg) ? "retraso desconocido" : sg < 60 ? `retraso ${num(Math.round(sg))} s`
  : sg < 3600 ? `retraso ${num(Math.round(sg / 60))} min` : `retraso ${num(Math.round(sg / 3600))} h`);
const CALIDAD = { proveedor: ["vigente", "Proveedor"], importado: ["retrasado", "Importado por usted"], calculado: ["sin_datos", "Calculado"], sintetico: ["sintetico", "SINTÉTICO"] };
const chipCalidad = (c) => chip((CALIDAD[c] || ["sin_datos"])[0], (CALIDAD[c] || [null, c])[1]);
const muestraLeyenda = (pares) => h("div", { clase: "leyenda" }, pares.map(([c, t]) => { const i = h("i"); i.style.background = c; return h("span", {}, i, t); }));

function cajaProcedencia(lista) {
  if (!lista || !lista.length) return null;
  return h("div", { clase: "procedencia" }, lista.map((p) => h("p", { clase: "ayuda" }, chipCalidad(p.calidad), " ",
    `Fuente: ${p.fuente}${p.feed ? ` (${p.feed})` : ""} · mercado: ${p.mercado} · licencia: ${p.licencia} · ${retrasoTexto(p.retraso_s)} · captura: ${horaCdmx(p.capturado_en)}. ${p.nota || ""}`)));
}

async function estadoFlujo(forzar) {
  if (!flujo.estado || forzar) flujo.estado = await api("/api/flujo/estado");
  return flujo.estado;
}

function selectorSimbolo(valor, alCambiar, { incluirCripto = true, etiqueta = "Instrumento" } = {}) {
  const c = flujo.estado.catalogo;
  const sel = h("select", { "aria-label": etiqueta, onchange: (e) => alCambiar(e.target.value) },
    h("option", { value: "" }, "Elija un instrumento…"),
    c.con_datos.length ? h("optgroup", { label: "Con datos guardados" }, c.con_datos.map((x) => h("option", { value: x }, x))) : null,
    h("optgroup", { label: "SIC (precio de origen en EE. UU., USD)" }, c.sic.map((x) => h("option", { value: x.id }, `${x.clave} · ${x.origen}`))),
    incluirCripto && c.cripto.length ? h("optgroup", { label: "Cripto (fuera del Reto)" }, c.cripto.map((x) => h("option", { value: x.id }, x.id))) : null);
  sel.value = valor;
  return h("label", {}, `${etiqueta} `, sel);
}

function selectorSimple(valor, opciones, alCambiar, etiqueta) {
  const sel = h("select", { "aria-label": etiqueta, onchange: (e) => alCambiar(e.target.value) }, opciones.map(([v, t]) => h("option", { value: v }, t)));
  sel.value = String(valor);
  return h("label", {}, `${etiqueta} `, sel);
}

function formImportar(tipo, alTerminar) {
  const archivo = h("input", { type: "file", accept: ".csv,text/csv", required: true, "aria-label": `CSV de ${tipo}` });
  const boton = h("button", { type: "submit", clase: "boton boton--secundario", texto: "Importar CSV" });
  const salida = h("p", { clase: "ayuda", role: "status" });
  const form = h("form", { clase: "fila-controles" }, archivo, boton);
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const fd = new FormData(); fd.append("archivo", archivo.files[0]);
    ocupado([boton], true);
    try {
      const r = await api(`/api/flujo/importar/${tipo}`, { method: "POST", body: fd });
      salida.textContent = `${r.guardados} registros guardados de ${r.filas} filas. ${r.nota}`;
      await estadoFlujo(true); if (alTerminar) alTerminar();
    } catch (e) { salida.textContent = e.message; }
    finally { ocupado([boton], false); }
  });
  return h("details", { clase: "importar-flujo" }, h("summary", { texto: `Importar ${tipo} desde CSV (datos que usted tenga derecho a usar)` }),
    h("p", { clase: "ayuda", texto: "UTF-8, encabezados exactos de la plantilla, instantes ISO 8601 con zona horaria (p. ej. 2026-10-12T14:30:00-06:00). Todo o nada: una fila inválida rechaza el archivo. Se guarda como «importado» con la fuente y licencia que declare." }),
    h("a", { href: `/api/flujo/plantilla/${tipo}`, clase: "boton boton--secundario", texto: "Descargar plantilla" }), form, salida);
}

const ESTADOS_ACT = { ok: "Actualizado", vacio: "Sin datos nuevos", en_espera: "En espera", sin_fuente: "Sin fuente", error: "Error", demo: "Demostración" };
async function pedirActualizacion(tipo, simbolo, extra, boton) {
  if (!simbolo) { notificar("Elija primero un instrumento."); return null; }
  ocupado([boton], true);
  try {
    const r = await api("/api/flujo/actualizar", { method: "POST", json: { tipo, simbolo, ...extra } });
    notificar(`${ESTADOS_ACT[r.estado] || r.estado}: ${r.mensaje}`);
    return r;
  } catch (e) { notificar(e.message); return null; }
  finally { ocupado([boton], false); }
}

/* Velas japonesas con volumen, SMA20, Bollinger, VWAP anclado y RSI (Wilder). */
function graficaVelas(barras, op, intervalo) {
  const ancho = 760, alto = 300, altoVol = 70, m = { i: 64, d: 12, s: 10, inf: 22 };
  const n = barras.length;
  const extra = [];
  if (op.boll) barras.forEach((b) => { if (b.boll_inf != null) extra.push(b.boll_inf, b.boll_sup); });
  ["ema20", "ema50", "sar"].forEach((k) => { if (op[k]) barras.forEach((b) => { if (b[k] != null) extra.push(b[k]); }); });
  let min = Math.min(...barras.map((b) => b.minimo), ...extra), max = Math.max(...barras.map((b) => b.maximo), ...extra);
  if (min === max) { min -= 1; max += 1; }
  const paso = (ancho - m.i - m.d) / n, cuerpo = Math.max(1, paso * 0.65);
  const X = (i) => m.i + paso * (i + 0.5);
  const Y = (y) => m.s + (1 - (y - min) / (max - min)) * (alto - m.s - m.inf);
  const svg = s("svg", { viewBox: `0 0 ${ancho} ${alto + altoVol}`, class: "grafica grafica--velas", role: "img",
    "aria-label": `Velas de ${n} barras; el detalle numérico está en la tabla siguiente` });
  for (let k = 0; k <= 4; k++) {
    const y = min + ((max - min) * k) / 4;
    svg.append(s("line", { x1: m.i, x2: ancho - m.d, y1: Y(y), y2: Y(y), stroke: "var(--borde)", "stroke-width": 1 }));
    svg.append(s("text", { x: m.i - 6, y: Y(y) + 4, "text-anchor": "end" }, num(y)));
  }
  const vmax = Math.max(...barras.map((b) => b.volumen || 0), 1);
  barras.forEach((b, i) => {
    const sube = b.cierre >= b.apertura, color = sube ? "var(--vela-sube)" : "var(--vela-baja)";
    const g = s("g", { class: "vela" },
      s("title", {}, `${etiquetaBarra(b.inicio, intervalo)} · A ${num(b.apertura)} · Máx ${num(b.maximo)} · Mín ${num(b.minimo)} · C ${num(b.cierre)} · Vol ${num(b.volumen)} · ${b.fuente}${b.feed ? ` (${b.feed})` : ""} · ${CALIDAD[b.calidad] ? CALIDAD[b.calidad][1] : b.calidad} · ${retrasoTexto(b.retraso_s)}`),
      s("line", { x1: X(i), x2: X(i), y1: Y(b.maximo), y2: Y(b.minimo), stroke: color, "stroke-width": 1 }),
      s("rect", { x: X(i) - cuerpo / 2, y: Y(Math.max(b.apertura, b.cierre)), width: cuerpo,
        height: Math.max(1, Math.abs(Y(b.apertura) - Y(b.cierre))), fill: sube ? "var(--superficie)" : color, stroke: color, "stroke-width": 1 }));
    if (b.volumen) {
      const hv = (b.volumen / vmax) * (altoVol - 8);
      g.append(s("rect", { x: X(i) - cuerpo / 2, y: alto + altoVol - hv, width: cuerpo, height: hv, fill: color, opacity: 0.55 }));
    }
    svg.append(g);
  });
  const linea = (campo, color, guion) => {
    const d = barras.map((b, i) => (b[campo] == null ? null : `${X(i).toFixed(1)},${Y(b[campo]).toFixed(1)}`)).filter(Boolean);
    if (d.length > 1) {
      const attrs = { points: d.join(" "), fill: "none", stroke: color, "stroke-width": 1.6 };
      if (guion) attrs["stroke-dasharray"] = "4 3";
      svg.append(s("polyline", attrs));
    }
  };
  if (op.sma) linea("sma20", "var(--retrasado)");
  if (op.boll) { linea("boll_inf", "var(--serie-2)", true); linea("boll_sup", "var(--serie-2)", true); }
  if (op.vwap) linea("vwap_anclado", "var(--sintetico)");
  if (op.ema20) linea("ema20", "var(--acento)");
  if (op.ema50) linea("ema50", "var(--texto-2)", true);
  if (op.sar) barras.forEach((b, i) => { if (b.sar != null) svg.append(s("circle", { cx: X(i), cy: Y(b.sar), r: 2.2, fill: b.sar_alcista ? "var(--vela-sube)" : "var(--vela-baja)" },
    s("title", {}, `SAR ${num(b.sar)} · ${b.sar_alcista ? "tendencia alcista (punto bajo el precio)" : "tendencia bajista (punto sobre el precio)"}`))); });
  svg.append(s("text", { x: m.i, y: alto + 14 }, "Volumen"));
  [0, Math.floor(n / 2), n - 1].forEach((i, j) => svg.append(s("text", { x: X(i), y: alto - 4, "text-anchor": ["start", "middle", "end"][j] },
    etiquetaBarra(barras[i].inicio, intervalo).replace("sesión ", "").replace(" CDMX", ""))));
  const leyenda = muestraLeyenda([["var(--vela-sube)", "Sube (cuerpo hueco)"], ["var(--vela-baja)", "Baja (cuerpo lleno)"],
    op.sma ? ["var(--retrasado)", "SMA 20"] : null, op.boll ? ["var(--serie-2)", "Bollinger 20, 2σ"] : null,
    op.vwap ? ["var(--sintetico)", "VWAP anclado al inicio del rango"] : null, op.ema20 ? ["var(--acento)", "EMA 20"] : null,
    op.ema50 ? ["var(--texto-2)", "EMA 50 (guiones)"] : null, op.sar ? ["var(--vela-sube)", "SAR 0.02 / 0.2 (puntos)"] : null].filter(Boolean));
  // eje ordenable: fecha de sesión (diario) o instante UTC (intradía)
  const rsi = barras.map((b) => ({ x: intervalo === "1Day" ? fmtSesion.format(new Date(b.inicio)) : `${String(b.inicio).slice(0, 16).replace("T", " ")} UTC`, y: b.rsi14 }));
  return h("figure", {}, svg, leyenda,
    rsi.some((p) => p.y != null) ? grafica([{ nombre: "RSI 14 (Wilder)", color: "var(--acento)", datos: rsi }], { alto: 140, formato: num, etiqueta: "RSI de 14 periodos" }) : null,
    op.macd ? panelIndicador(barras, intervalo, { titulo: "MACD 12/26/9", lineas: [{ campo: "macd", color: "var(--acento)", nombre: "MACD" }, { campo: "macd_senal", color: "var(--retrasado)", nombre: "Señal" }],
      hist: "macd_hist", cero: true }) : null,
    op.estoc ? panelIndicador(barras, intervalo, { titulo: "Estocástico 14/3/3", lineas: [{ campo: "estoc_k", color: "var(--acento)", nombre: "%K (lento)" }, { campo: "estoc_d", color: "var(--retrasado)", nombre: "%D" }],
      fijo: [0, 100], niveles: [20, 80] }) : null);
}

/* Panel inferior alineado con las velas (mismo eje X): líneas, histograma opcional y eje propio. Los nulos del calentamiento
   quedan sin dibujar: no se rellenan ni se unen. */
function panelIndicador(barras, intervalo, { titulo, lineas, hist, fijo, niveles = [], cero = false }) {
  const ancho = 760, alto = 150, m = { i: 64, d: 12, s: 10, inf: 22 };
  const campos = [...lineas.map((l) => l.campo), hist].filter(Boolean);
  const vals = barras.flatMap((b) => campos.map((c) => b[c]).filter((v) => v != null));
  if (!vals.length) return h("p", { clase: "ayuda", texto: `${titulo}: sin datos suficientes (calentamiento incompleto o rango plano); no se rellena.` });
  let min = fijo ? fijo[0] : Math.min(...vals, cero ? 0 : Infinity), max = fijo ? fijo[1] : Math.max(...vals, cero ? 0 : -Infinity);
  if (min === max) { min -= 1; max += 1; }
  const n = barras.length, paso = (ancho - m.i - m.d) / n;
  const X = (i) => m.i + paso * (i + 0.5), Y = (y) => m.s + (1 - (y - min) / (max - min)) * (alto - m.s - m.inf);
  const svg = s("svg", { viewBox: `0 0 ${ancho} ${alto}`, class: "grafica", role: "img", "aria-label": `${titulo}; ${vals.length} valores calculados, el detalle numérico está en la tabla de velas` });
  for (let k = 0; k <= 3; k++) {
    const y = min + ((max - min) * k) / 3;
    svg.append(s("line", { x1: m.i, x2: ancho - m.d, y1: Y(y), y2: Y(y), stroke: "var(--borde)", "stroke-width": 1 }));
    svg.append(s("text", { x: m.i - 6, y: Y(y) + 4, "text-anchor": "end" }, num(y)));
  }
  niveles.forEach((y) => { svg.append(s("line", { x1: m.i, x2: ancho - m.d, y1: Y(y), y2: Y(y), stroke: "var(--texto-2)", "stroke-width": 1, "stroke-dasharray": "3 3" })); });
  if (min < 0 && max > 0) svg.append(s("line", { x1: m.i, x2: ancho - m.d, y1: Y(0), y2: Y(0), stroke: "var(--texto-2)", "stroke-width": 1 }));
  if (hist) barras.forEach((b, i) => {
    const v = b[hist];
    if (v == null) return;
    const y0 = Y(Math.max(min, Math.min(0, max)));
    svg.append(s("rect", { x: X(i) - Math.max(1, paso * 0.6) / 2, y: Math.min(Y(v), y0), width: Math.max(1, paso * 0.6), height: Math.max(0.5, Math.abs(Y(v) - y0)),
      fill: v >= 0 ? "var(--vela-sube)" : "var(--vela-baja)", opacity: 0.45 }, s("title", {}, `Histograma ${num(v)}`)));
  });
  lineas.forEach((l) => {
    let d = "", previo = false;
    barras.forEach((b, i) => { const v = b[l.campo]; if (v == null) { previo = false; return; } d += `${previo ? "L" : "M"}${X(i).toFixed(1)},${Y(v).toFixed(1)}`; previo = true; });
    if (d) svg.append(s("path", { d, fill: "none", stroke: l.color, "stroke-width": 1.6 }));
  });
  [0, Math.floor(n / 2), n - 1].forEach((i, j) => svg.append(s("text", { x: X(i), y: alto - 6, "text-anchor": ["start", "middle", "end"][j] },
    etiquetaBarra(barras[i].inicio, intervalo).replace("sesión ", "").replace(" CDMX", ""))));
  return h("figure", {}, h("figcaption", { clase: "ayuda", texto: titulo }), svg,
    muestraLeyenda([...lineas.map((l) => [l.color, l.nombre]), hist ? ["var(--vela-sube)", "Histograma (azul ≥ 0, naranja < 0)"] : null].filter(Boolean)));
}

const fmtSesion = new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York", year: "numeric", month: "2-digit", day: "2-digit" });
/* Barra diaria: fecha de la sesión (el proveedor marca su inicio a medianoche de Nueva York); intradía: hora CDMX. */
const etiquetaBarra = (iso, intervalo) => (intervalo === "1Day" ? `sesión ${fmtSesion.format(new Date(iso))}` : horaCdmx(iso));
const NOMBRE_INTERVALO = { "1Min": "1 minuto", "5Min": "5 minutos", "15Min": "15 minutos", "1Hour": "1 hora", "1Day": "1 día" };
let cargaVelasId = 0;
async function cargarVelas() {
  const solicitud = ++cargaVelasId;
  try {
    await estadoFlujo();
    if (solicitud !== cargaVelasId) return;
    const v = flujo.velas;
    const botonAct = h("button", { type: "button", clase: "boton boton--primario", texto: "Actualizar desde proveedor" });
    botonAct.addEventListener("click", async () => { if (await pedirActualizacion("velas", v.simbolo, { intervalo: v.intervalo, dias: v.dias }, botonAct)) cargarVelas(); });
    const casillas = [["sma", "SMA 20"], ["ema20", "EMA 20"], ["ema50", "EMA 50"], ["sar", "SAR parabólico"], ["boll", "Bollinger"], ["vwap", "VWAP"],
      ["macd", "Panel MACD"], ["estoc", "Panel estocástico"]].map(([k, t]) => {
      const c = h("input", { type: "checkbox" }); c.checked = v[k];
      c.addEventListener("change", () => { v[k] = c.checked; cargarVelas(); });
      return h("label", {}, c, ` ${t}`);
    });
    const controles = h("div", { clase: "fila-controles" },
      selectorSimbolo(v.simbolo, (x) => { v.simbolo = x; cargarVelas(); }),
      selectorSimple(v.intervalo, flujo.estado.catalogo.intervalos.map((x) => [x, NOMBRE_INTERVALO[x] || x]), (x) => { v.intervalo = x; cargarVelas(); }, "Intervalo"),
      selectorSimple(v.dias, [5, 30, 90, 180, 365].map((d) => [d, `${d} días`]), (x) => { v.dias = Number(x); cargarVelas(); }, "Rango"),
      ...casillas, botonAct);
    if (!v.simbolo) {
      limpiar("velas-contenido", controles, h("p", { clase: "vacio", texto: "Elija un instrumento. Proveedores: Alpaca (SIC: OHLCV del consolidado SIP con ≥ 15 min de retraso) y cripto (exchange público). Para la BMV importe un CSV." }), formImportar("velas", cargarVelas), formImportarExterno("", cargarVelas));
      return;
    }
    const d = await api(`/api/flujo/velas?simbolo=${encodeURIComponent(v.simbolo)}&intervalo=${v.intervalo}&dias=${v.dias}`);
    if (solicitud !== cargaVelasId) return;
    const ult = d.barras.slice(-12).reverse();
    limpiar("velas-contenido", controles,
      d.barras.length ? h("div", {},
        h("p", { clase: "ayuda" }, chip("retrasado", v.intervalo === "1Day" ? "Barras diarias" : "Barras intradía"), " ", `${d.zona_horaria}. ${d.nota}`),
        cajaProcedencia(d.procedencia), graficaVelas(d.barras, v, v.intervalo),
        tabla([{ t: v.intervalo === "1Day" ? "Sesión (Nueva York)" : "Inicio (CDMX)", f: (b) => etiquetaBarra(b.inicio, v.intervalo).replace("sesión ", "") }, { t: "Apertura", f: (b) => num(b.apertura), num: true },
          { t: "Máximo", f: (b) => num(b.maximo), num: true }, { t: "Mínimo", f: (b) => num(b.minimo), num: true },
          { t: "Cierre", f: (b) => num(b.cierre), num: true }, { t: "Volumen", f: (b) => num(b.volumen), num: true },
          { t: "RSI 14", f: (b) => num(b.rsi14), num: true },
          ...(v.ema20 ? [{ t: "EMA 20", f: (b) => num(b.ema20), num: true }] : []), ...(v.ema50 ? [{ t: "EMA 50", f: (b) => num(b.ema50), num: true }] : []),
          ...(v.sar ? [{ t: "SAR", f: (b) => (b.sar == null ? "—" : `${num(b.sar)} ${b.sar_alcista ? "▲" : "▼"}`), num: true }] : []),
          ...(v.macd ? [{ t: "MACD", f: (b) => num(b.macd), num: true }, { t: "Señal", f: (b) => num(b.macd_senal), num: true }, { t: "Hist.", f: (b) => num(b.macd_hist), num: true }] : []),
          ...(v.estoc ? [{ t: "%K", f: (b) => num(b.estoc_k), num: true }, { t: "%D", f: (b) => num(b.estoc_d), num: true }] : []),
          { t: "Calidad", f: (b) => chipCalidad(b.calidad) }], ult,
        { caption: "Últimas 12 barras (alternativa accesible a la gráfica)" }))
        : h("div", { clase: "aviso-caja", role: "status", texto: d.vacio }),
      formImportar("velas", cargarVelas), formImportarExterno(v.simbolo, cargarVelas));
  } catch (e) { if (solicitud === cargaVelasId) limpiar("velas-contenido", errorCaja(e)); }
}

/* Order Flow: libro, profundidad, cinta, delta y perfil de volumen. */
function graficaProfundidad(libro) {
  const pts = libro.profundidad;
  if (!pts.length) return null;
  const ancho = 720, alto = 200, m = { i: 64, d: 12, s: 10, inf: 26 };
  const ps = pts.map((p) => p.precio), as = pts.map((p) => p.acumulado);
  const pmin = Math.min(...ps), pmax = Math.max(...ps), amax = Math.max(...as) || 1;
  const X = (p) => m.i + ((p - pmin) / ((pmax - pmin) || 1)) * (ancho - m.i - m.d);
  const Y = (a) => m.s + (1 - a / amax) * (alto - m.s - m.inf);
  const svg = s("svg", { viewBox: `0 0 ${ancho} ${alto}`, class: "grafica", role: "img", "aria-label": "Profundidad acumulada del libro por precio" });
  for (const [lado, color] of [["bid", "var(--vela-sube)"], ["ask", "var(--vela-baja)"]]) {
    const l = pts.filter((p) => p.lado === lado).sort((a, b) => a.precio - b.precio);
    if (l.length) svg.append(s("polyline", { points: l.map((p) => `${X(p.precio).toFixed(1)},${Y(p.acumulado).toFixed(1)}`).join(" "), fill: "none", stroke: color, "stroke-width": 2 }));
  }
  svg.append(s("text", { x: m.i, y: alto - 6 }, num(pmin)));
  svg.append(s("text", { x: ancho - m.d, y: alto - 6, "text-anchor": "end" }, num(pmax)));
  svg.append(s("text", { x: m.i - 6, y: m.s + 8, "text-anchor": "end" }, num(amax)));
  return h("figure", {}, svg, muestraLeyenda([["var(--vela-sube)", "Bid acumulado"], ["var(--vela-baja)", "Ask acumulado"]]));
}

function perfilVolumen(perfil) {
  if (!perfil.length) return null;
  const vmax = Math.max(...perfil.map((p) => p.volumen)) || 1;
  return h("div", { clase: "perfil-volumen", role: "list", "aria-label": "Perfil de volumen por precio" }, [...perfil].reverse().map((p) =>
    h("div", { clase: "perfil-fila", role: "listitem" }, h("span", { clase: "suave", texto: `${num(p.desde)} – ${num(p.hasta)}` }),
      barraPct(p.volumen, vmax), h("span", { clase: "num", texto: num(p.volumen) }))));
}

function botonAccion(texto, clase, alPulsar) {
  const b = h("button", { type: "button", clase: `boton ${clase}`, texto });
  b.addEventListener("click", () => alPulsar(b));
  return b;
}

function pintarSubasta(d, procedencia) {
  const estados = { sin_referencia: "Sin referencia previa", aceptacion_alcista: "Aceptación alcista", aceptacion_bajista: "Aceptación bajista", rechazo_superior: "Rechazo superior", rechazo_inferior: "Rechazo inferior", rechazo_ambos_extremos: "Rechazo de ambos extremos", rotacion_en_valor: "Rotación en valor", exploracion_fuera_de_valor: "Exploración fuera de valor" };
  return h("section", { clase: "tarjeta" },
    h("h2", { texto: "Auction Market Theory · contexto de subasta" }),
    h("p", { clase: "ayuda", texto: d ? `${d.zona} · ${d.sesion} · rejilla fija ${num(d.paso_precio)}. ${d.nota}` : "Sin sesión de origen verificada. No se supone un horario ni se inventan niveles." }),
    cajaProcedencia(procedencia),
    d?.sesiones.length ? tabla([
      { t: "Sesión", f: (s) => s.fecha },
      { t: "Contexto", f: (s) => estados[s.estado] || s.estado },
      { t: "Cobertura", f: (s) => pct(s.cobertura) },
      { t: "POC observado", f: (s) => num(s.perfil_tpo_observado?.poc) },
      { t: "VAL / VAH previo", f: (s) => s.referencia ? `${num(s.referencia.val)} / ${num(s.referencia.vah)} (${s.referencia.fecha})` : "Sin referencia completa" },
      { t: "Balance inicial", f: (s) => s.ib ? `${num(s.ib.bajo)} – ${num(s.ib.alto)}` : "Pendiente / incompleto" }
    ], d.sesiones, { caption: "AMT descriptivo con barras cerradas; no son órdenes de trading" })
      : h("p", { clase: "vacio", texto: "Sin barras intradía suficientes. Importe o actualice barras de 5 minutos en Velas." }),
    h("details", {}, h("summary", { texto: "Cómo leerlo y usarlo en Quantower / TradingView" }),
      h("p", { clase: "ayuda", texto: "Aceptación: dos cierres consecutivos fuera del valor previo. Rechazo: la última barra explora fuera y cierra dentro. Rotación: cierre dentro sin barrido. Son hipótesis, no evidencia de ventaja. La sesión es RTH 09:30–16:00 de Nueva York; no es la sesión Globex." }),
      h("a", { href: "/static/recursos/auction-market-theory.md", texto: "Guía, fuentes y límites del módulo" }),
      h("p", {}, h("a", { href: "/static/recursos/actinver_amt.pine", download: "actinver_amt.pine", texto: "Descargar indicador AMT para TradingView" })),
      h("p", {}, h("a", { href: "/static/recursos/amt-proyectos-financieros.zip", download: "amt-proyectos-financieros.zip", texto: "Descargar fuentes, observador Quantower y prompt de Claude" }))));
}

function pintarTpo(d) {
  const letra = (i) => i < 26 ? String.fromCharCode(65 + i) : String.fromCharCode(97 + i - 26);
  return h("section", { clase: "tarjeta" }, h("h2", { texto: "TPO observado / Market Profile" }),
    h("p", { clase: "ayuda", texto: `${d.zona_horaria} · ${d.apertura}–${d.cierre} · periodos de 30 min · barras ${d.intervalo}. ${d.nota}` }),
    cajaProcedencia(d.procedencia),
    !d.sesiones.length ? h("p", { clase: "vacio", texto: "Sin barras intradía guardadas suficientes. Importe o actualice barras de 5 minutos en Velas; no se inventan niveles." }) : null,
    ...d.sesiones.map((sesion) => h("div", {}, h("h3", { texto: sesion.fecha }),
      sesion.perfil ? tabla([{ t: "Precio (cubeta)", f: (p) => `${num(p.desde)}–${num(p.hasta)}` },
        { t: "TPO", f: (p) => p.tpo }, { t: "Periodos observados", f: (p) => p.periodos.map(letra).join(" ") }],
      [...sesion.perfil].reverse(), { caption: `TPO observado del ${sesion.fecha}; cota inferior OHLC` })
        : h("p", { clase: "vacio", texto: sesion.motivo }),
      h("p", { clase: "ayuda", texto: sesion.periodos.map((p) => `${letra(p.indice)}: ${p.inicio.slice(11, 16)}`).join(" · ") }))));
}

async function cargarOrderFlow() {
  const vigente = turno("orderflow");
  try {
    await estadoFlujo();
    if (!vigente()) return;
    const o = flujo.of;
    const controles = h("div", { clase: "fila-controles" },
      selectorSimbolo(o.simbolo, (x) => { o.simbolo = x; cargarOrderFlow(); }),
      selectorSimple(o.minutos, [[30, "30 min"], [240, "4 h"], [1440, "1 día"], [10080, "7 días"]], (x) => { o.minutos = Number(x); cargarOrderFlow(); }, "Ventana de operaciones"),
      selectorSimple(o.niveles, [5, 10, 20, 50].map((x) => [x, String(x)]), (x) => { o.niveles = Number(x); cargarOrderFlow(); }, "Niveles"),
      selectorSimple(o.pasoAmt, [.01, .05, .25, .5, 1, 5, 10].map((x) => [x, String(x)]), (x) => { o.pasoAmt = Number(x); cargarOrderFlow(); }, "Rejilla AMT (precio; no tick verificado)"),
      botonAccion("Actualizar libro", "boton--primario", async (b) => { if (await pedirActualizacion("libro", o.simbolo, {}, b)) cargarOrderFlow(); }),
      botonAccion("Actualizar operaciones", "boton--secundario", async (b) => { if (await pedirActualizacion("operaciones", o.simbolo, {}, b)) cargarOrderFlow(); }));
    const provs = h("p", { clase: "ayuda", texto: `Fuentes: ${flujo.estado.proveedores.map((p) => `${p.nombre} — ${p.configurado ? "disponible" : "no configurado"}`).join(" · ")}. No disponible gratuitamente: ${flujo.estado.no_disponible.join("; ")}.` });
    if (!o.simbolo) {
      limpiar("orderflow-contenido", controles, provs, h("p", { clase: "vacio", texto: "Elija un instrumento. Con datos públicos reales: cripto (libro por niveles y operaciones con lado del agresor). SIC: solo el mejor bid/ask de IEX y operaciones SIP con retraso, sin lado." }),
        formImportar("libro", cargarOrderFlow), formImportar("operaciones", cargarOrderFlow));
      return;
    }
    const [d, perfiles] = await Promise.all([   // independientes: en paralelo
      api(`/api/flujo/libro-operaciones?simbolo=${encodeURIComponent(o.simbolo)}&minutos=${o.minutos}&niveles=${o.niveles}`),
      api(`/api/flujo/perfiles?simbolo=${encodeURIComponent(o.simbolo)}&paso_precio=${o.pasoAmt}`)]);
    if (!vigente()) return;
    const L = d.libro, R = d.resumen;
    const filasLibro = L ? Array.from({ length: Math.max(L.bids.length, L.asks.length) }, (_, i) => ({ b: L.bids[i], a: L.asks[i] })) : [];
    limpiar("orderflow-contenido", controles, provs,
      h("h2", { texto: "Libro y profundidad" }),
      L ? h("div", {}, cajaProcedencia([d.libro_meta]), h("p", { clase: "ayuda", texto: `Instante del libro: ${horaCdmx(d.libro_meta.instante)}.` }),
        h("div", { clase: "kpis" }, kpi("Mejor bid", num(L.mejor_bid)), kpi("Mejor ask", num(L.mejor_ask)),
          kpi("Diferencial", L.diferencial_pb == null ? "—" : `${num(L.diferencial_pb)} pb`),
          kpi(`Desequilibrio (${L.bids.length}/${L.asks.length} niveles)`, L.desequilibrio == null ? "—" : pct(L.desequilibrio), signo(L.desequilibrio))),
        h("p", { clase: "ayuda", texto: "Desequilibrio = (tamaño bid − tamaño ask) / total de los niveles mostrados. Descriptivo; no predice el precio." }),
        graficaProfundidad(L),
        tabla([{ t: "Bid tamaño", f: (f) => num(f.b?.tamano), num: true }, { t: "Bid", f: (f) => num(f.b?.precio), num: true },
          { t: "Ask", f: (f) => num(f.a?.precio), num: true }, { t: "Ask tamaño", f: (f) => num(f.a?.tamano), num: true }],
        filasLibro, { caption: "Libro de órdenes por nivel" }))
        : h("div", { clase: "aviso-caja", role: "status", texto: d.vacio_libro }),
      pintarMicroestructura(d),
      pintarSubasta(perfiles.subasta, perfiles.procedencia),
      pintarTpo(perfiles),
      h("h2", { texto: "Cinta de operaciones" }),
      d.operaciones.length ? h("div", {}, cajaProcedencia(d.procedencia_operaciones),
        h("div", { clase: "kpis" }, kpi("Operaciones", num(R.n)), kpi("Volumen", num(R.volumen)),
          kpi("Delta de volumen", R.delta == null ? "No disponible" : num(R.delta), signo(R.delta))),
        R.delta == null ? h("p", { clase: "ayuda", texto: `Delta no disponible: la fuente informa el lado del agresor en ${R.con_lado} de ${R.n} operaciones. No se infiere.` })
          : grafica([{ nombre: "Delta acumulado (compras − ventas del agresor)", color: "var(--acento)", datos: R.delta_acumulado.map((p) => ({ x: p.instante, y: p.delta })) }], { alto: 160, formato: num, etiqueta: "Delta de volumen acumulado" }),
        h("h3", { texto: "Perfil de volumen por precio" }), perfilVolumen(R.perfil),
        R.area_valor ? h("div", {}, h("div", { clase: "kpis" },
          kpi("POC (centro de cubeta)", num(R.area_valor.poc)), kpi("VAH", num(R.area_valor.vah)), kpi("VAL", num(R.area_valor.val))),
          h("p", { clase: "ayuda", texto: "Área de valor ≥ 70 % del volumen observado del rango; cubetas contiguas desde POC. No representa una sesión completa." }))
          : h("p", { clase: "ayuda", texto: "POC / VAH / VAL: datos insuficientes (se requieren al menos dos operaciones y dos niveles)." }),
        tabla([{ t: "Hora", f: (f) => horaCdmx(f.instante) }, { t: "Precio", f: (f) => num(f.precio), num: true },
          { t: "Tamaño", f: (f) => num(f.tamano), num: true },
          { t: "Lado del agresor", f: (f) => (f.lado ? h("span", { clase: f.lado === "compra" ? "positivo" : "negativo", texto: f.lado }) : "no informado") }],
        d.operaciones.slice(-50).reverse(), { caption: "Últimas 50 operaciones" }))
        : h("div", { clase: "aviso-caja", role: "status", texto: d.vacio_operaciones }),
      h("p", { clase: "ayuda", texto: d.nota }),
      L || d.operaciones.length ? enlaceHftbacktest(o.simbolo) : null,
      formImportar("libro", cargarOrderFlow), formImportar("operaciones", cargarOrderFlow));
  } catch (e) { if (vigente()) limpiar("orderflow-contenido", errorCaja(e)); }
}

/* Option Flow: cadena, curva y superficie de IV, regla descriptiva de volumen inusual. */
function graficaXY(series, { alto = 220, etiquetaX = "", formatoY = num, etiqueta = "Gráfica" } = {}) {
  const ancho = 720, m = { i: 56, d: 12, s: 10, inf: 30 };
  const pts = series.flatMap((se) => se.datos);
  if (pts.length < 2) return h("p", { clase: "vacio", texto: "Sin datos suficientes para graficar." });
  const xs = pts.map((p) => p.x), ys = pts.map((p) => p.y);
  const xmin = Math.min(...xs), xmax = Math.max(...xs);
  let ymin = Math.min(...ys), ymax = Math.max(...ys);
  if (ymin === ymax) { ymin -= 0.01; ymax += 0.01; }
  const X = (x) => m.i + ((x - xmin) / ((xmax - xmin) || 1)) * (ancho - m.i - m.d);
  const Y = (y) => m.s + (1 - (y - ymin) / (ymax - ymin)) * (alto - m.s - m.inf);
  const svg = s("svg", { viewBox: `0 0 ${ancho} ${alto}`, class: "grafica", role: "img", "aria-label": etiqueta });
  for (let k = 0; k <= 3; k++) {
    const y = ymin + ((ymax - ymin) * k) / 3;
    svg.append(s("line", { x1: m.i, x2: ancho - m.d, y1: Y(y), y2: Y(y), stroke: "var(--borde)" }));
    svg.append(s("text", { x: m.i - 6, y: Y(y) + 4, "text-anchor": "end" }, formatoY(y)));
  }
  svg.append(s("text", { x: m.i, y: alto - 8 }, num(xmin)));
  svg.append(s("text", { x: ancho - m.d, y: alto - 8, "text-anchor": "end" }, num(xmax)));
  svg.append(s("text", { x: ancho / 2, y: alto - 8, "text-anchor": "middle" }, etiquetaX));
  series.forEach((se) => {
    const d = [...se.datos].sort((a, b) => a.x - b.x);
    svg.append(s("polyline", { points: d.map((p) => `${X(p.x).toFixed(1)},${Y(p.y).toFixed(1)}`).join(" "), fill: "none", stroke: se.color, "stroke-width": 1.8 }));
    d.forEach((p) => svg.append(s("circle", { cx: X(p.x), cy: Y(p.y), r: 2.4, fill: se.color },
      s("title", {}, `${etiquetaX} ${num(p.x)}: ${formatoY(p.y)}${p.t ? ` · origen ${p.t}` : ""}`))));
  });
  return h("figure", {}, svg, muestraLeyenda(series.map((se) => [se.color, se.nombre])));
}

function superficieTabla(curvas) {
  const vencs = Object.keys(curvas);
  const strikes = [...new Set(vencs.flatMap((v) => curvas[v].map((p) => p.strike)))].sort((a, b) => a - b);
  const paso = Math.max(1, Math.ceil(strikes.length / 14));
  const cols = strikes.filter((_, i) => i % paso === 0);
  const tramo = ((strikes[strikes.length - 1] - strikes[0]) / Math.max(cols.length, 1)) || 1;
  const ivs = vencs.flatMap((v) => curvas[v].map((p) => p.iv));
  const lo = Math.min(...ivs), hi = Math.max(...ivs);
  return tabla([{ t: "Vencimiento", f: (v) => v }, ...cols.map((k) => ({ t: num(k), num: true, f: (v) => {
    const cerca = curvas[v].filter((p) => Math.abs(p.strike - k) <= tramo / 2);
    if (!cerca.length) return "—";
    const iv = cerca.reduce((a, p) => a + p.iv, 0) / cerca.length;
    const marca = h("span", { clase: "celda-iv", texto: pct(iv) });  // color por CSSOM (la CSP bloquea style en línea)
    if (hi > lo) marca.style.backgroundColor = `color-mix(in srgb, var(--serie-2) ${Math.round(15 + 60 * (iv - lo) / (hi - lo))}%, transparent)`;
    return marca;
  } }))], vencs, { caption: "Superficie de volatilidad implícita (promedio de calls y puts alrededor de cada strike)" });
}

function controlesContratosPaper(subyacente) {
  const proveedor = flujo.estado.proveedores.find((p) => p.id === "alpaca_contratos_paper");
  const disponible = Boolean(proveedor?.configurado) && flujo.estado.modo !== "sintetico";
  const boton = botonAccion("Actualizar OI y multiplicador (Paper)", "boton--secundario", async (b) => {
    if (await pedirActualizacion("contratos_oi", subyacente, {}, b)) cargarOptionFlow();
  });
  boton.disabled = !disponible || !subyacente;
  return h("section", { clase: "tarjeta", "aria-label": "Contratos Alpaca Paper de solo lectura" },
    h("h2", { texto: "Interés abierto y tamaño del contrato" }),
    h("p", { clase: "ayuda", texto: "Consulta autorizada únicamente en Paper y de solo lectura. El interés abierto corresponde a un cierre previo, con su fecha; no es tiempo real. No compra contratos ni habilita órdenes o suscripciones." }),
    h("p", { clase: disponible ? "ayuda" : "aviso-caja", role: "status", texto: disponible
      ? "Consulta disponible bajo demanda; no se actualiza automáticamente."
      : "Consulta desactivada o sin credenciales Paper. Configure las claves Paper y habilite contratos_oi en la configuración local; reinicie la terminal. En demo no se consultan proveedores." }),
    h("p", { clase: "ayuda", texto: "Actualice primero los metadatos y después la cadena. Solo se combina OI de cierre previo que ya era conocido al instante de la referencia; no se rellena un snapshot histórico con información posterior." }), boton);
}

async function cargarOptionFlow() {
  const vigente = turno("optionflow");
  try {
    await estadoFlujo();
    if (!vigente()) return;
    const o = flujo.op, F = o.filtros;
    const campo = (k, t) => {
      const i = h("input", { type: "number", step: "any", size: 7 }); i.value = F[k] ?? "";
      i.addEventListener("change", () => { F[k] = i.value; cargarOptionFlow(); });
      return h("label", {}, `${t} `, i);
    };
    const sim = selectorSimbolo(o.subyacente, (x) => { o.subyacente = x; o.filtros = {}; cargarOptionFlow(); }, { incluirCripto: false, etiqueta: "Subyacente" });
    const botonAct = botonAccion("Actualizar cadena desde proveedor", "boton--primario", async (b) => { if (await pedirActualizacion("opciones", o.subyacente, {}, b)) cargarOptionFlow(); });
    if (!o.subyacente) {
      limpiar("optionflow-contenido", h("div", { clase: "fila-controles" }, sim, botonAct),
        controlesContratosPaper(o.subyacente),
        h("p", { clase: "vacio", texto: "Elija un subyacente del SIC. Proveedor: Alpaca, feed «indicative» de OPRA (gratuito y diferido; sin interés abierto). Opciones de MexDer: solo por CSV." }),
        formImportar("opciones", cargarOptionFlow), seccionSkylit());
      return;
    }
    const qs = new URLSearchParams({ subyacente: o.subyacente, ...Object.fromEntries(Object.entries(F).filter(([, v]) => v !== "" && v != null)) });
    const d = await api(`/api/flujo/optionflow?${qs}`);
    if (!vigente()) return;
    const curvas = d.iv.curvas, vSel = F.vencimiento || Object.keys(curvas)[0];
    const curva = vSel && curvas[vSel] ? curvas[vSel] : [];
    const usarEnModelo = (c) => botonAccion("Al modelo", "boton--secundario", () => {
      const f = document.getElementById("form-opciones");
      f.elements.tipo.value = c.tipo; f.elements.strike.value = c.strike; f.elements.dias.value = Math.max(1, c.dias);
      if (c.iv) f.elements.volatilidad_pct.value = (c.iv * 100).toFixed(2);
      if (c.bid && c.ask) f.elements.prima_mercado.value = ((c.bid + c.ask) / 2).toFixed(4);
      irA("tab-modelos"); notificar("Complete el precio del subyacente y la tasa: el modelo no los toma del mercado.");
    });
    limpiar("optionflow-contenido",
      h("div", { clase: "fila-controles" }, sim, botonAct),
      controlesContratosPaper(o.subyacente),
      h("div", { clase: "fila-controles" },
        selectorSimple(F.vencimiento || "", [["", "Todos"], ...d.vencimientos.map((v) => [v, v])], (x) => { F.vencimiento = x; cargarOptionFlow(); }, "Vencimiento"),
        selectorSimple(F.tipo || "", [["", "Calls y puts"], ["call", "Calls"], ["put", "Puts"]], (x) => { F.tipo = x; cargarOptionFlow(); }, "Tipo"),
        campo("strike_min", "Strike mín."), campo("strike_max", "Strike máx."), campo("volumen_min", "Volumen mín."),
        campo("oi_min", "Interés abierto mín."), campo("delta_abs_max", "|Delta| máx.")),
      d.total ? h("div", {},
        cajaProcedencia(d.procedencia),
        h("p", { clase: "ayuda", texto: `${d.contratos.length} de ${d.total} contratos con los filtros. ${d.nota} Tasa usada para la IV calculada: ${d.tasa_para_iv_calculada}.` }),
        h("h2", { texto: `Curva de volatilidad implícita${vSel ? ` · ${vSel}` : ""}` }),
        graficaXY([{ nombre: "Calls", color: "var(--vela-sube)", datos: curva.filter((p) => p.tipo === "call").map((p) => ({ x: p.strike, y: p.iv, t: p.origen })) },
          { nombre: "Puts", color: "var(--vela-baja)", datos: curva.filter((p) => p.tipo === "put").map((p) => ({ x: p.strike, y: p.iv, t: p.origen })) }].filter((x) => x.datos.length),
        { etiquetaX: "Strike", formatoY: pct, etiqueta: "Volatilidad implícita por strike" }),
        d.iv.superficie ? h("div", {}, h("h2", { texto: "Superficie de volatilidad" }), superficieTabla(curvas))
          : h("p", { clase: "ayuda", texto: "Superficie no disponible: hacen falta al menos 2 vencimientos con 3 strikes con IV." }),
        botonHeston(o.subyacente),
        h("h2", { texto: "Volumen inusual (regla descriptiva)" }),
        h("div", { clase: "fila-controles" }, campo("vol_inusual_min", "Volumen mínimo"), campo("percentil", "Percentil (0–1)"), campo("ratio_oi", "Volumen / interés abierto ≥")),
        h("p", { clase: "ayuda", texto: `Regla: volumen ≥ ${num(d.regla.minimo)} y, con interés abierto, volumen/interés abierto ≥ ${num(d.regla.ratio_oi)}; sin interés abierto, volumen ≥ percentil ${pct(d.regla.percentil)} de la cadena filtrada. Describe el volumen negociado; no es una recomendación ni una lectura de intención.` }),
        tabla([{ t: "Contrato", f: (c) => c.contrato }, { t: "Venc.", f: (c) => c.vencimiento }, { t: "Strike", f: (c) => num(c.strike), num: true },
          { t: "Tipo", f: (c) => c.tipo }, { t: "Volumen", f: (c) => num(c.volumen), num: true }, { t: "Motivo", f: (c) => c.motivo }], d.inusual.slice(0, 30),
        { vacio: "Ningún contrato cumple la regla con estos parámetros." }),
        h("h2", { texto: "Cadena de opciones" }),
        tabla([{ t: "Venc.", f: (c) => c.vencimiento }, { t: "Días", f: (c) => c.dias, num: true }, { t: "Strike", f: (c) => num(c.strike), num: true },
          { t: "Tipo", f: (c) => c.tipo }, { t: "Bid", f: (c) => num(c.bid), num: true }, { t: "Ask", f: (c) => num(c.ask), num: true },
          { t: "Último", f: (c) => num(c.ultimo), num: true }, { t: "Volumen", f: (c) => num(c.volumen), num: true },
          { t: "Int. abierto", f: (c) => (c.interes_abierto == null ? "no informado" : `${num(c.interes_abierto)}${c.fecha_oi ? ` (cierre ${c.fecha_oi})` : ""}`), num: true },
          { t: "Multiplicador", f: (c) => (c.multiplicador == null ? "no informado" : num(c.multiplicador)), num: true },
          { t: "IV", f: (c) => (c.iv == null ? "—" : pct(c.iv)), num: true }, { t: "Origen IV", f: (c) => (c.origen_iv ? chipCalidad(c.origen_iv) : "—") },
          { t: "Delta", f: (c) => num(c.delta), num: true }, { t: "Gamma", f: (c) => num(c.gamma), num: true },
          { t: "Theta", f: (c) => num(c.theta), num: true }, { t: "Vega", f: (c) => num(c.vega), num: true },
          { t: "", f: (c) => usarEnModelo(c) }], d.contratos.slice(0, 400),
        { caption: d.contratos.length > 400 ? "Primeros 400 contratos: use los filtros para acotar." : "Cadena filtrada" }))
        : h("div", { clase: "aviso-caja", role: "status", texto: d.vacio }),
      h("h2", { texto: "GEX: exposición gamma por strike y vencimiento" }),
      h("div", { id: "gex-contenido", "aria-live": "polite" }, h("p", { clase: "ayuda", texto: "Calculando disponibilidad…" })),
      formImportar("opciones", cargarOptionFlow), seccionSkylit());
    cargarGex(o.subyacente);
  } catch (e) { if (vigente()) limpiar("optionflow-contenido", errorCaja(e)); }
}

CARGAS["tab-velas"] = () => cargarVelas();
CARGAS["tab-orderflow"] = () => cargarOrderFlow();
CARGAS["tab-optionflow"] = () => cargarOptionFlow();
Object.assign(ATAJOS, { VEL: "tab-velas", OF: "tab-orderflow", OPC: "tab-optionflow" });

/* ---------- Etapa 2: Heston, exportación a hftbacktest e importación de formatos externos ---------- */
function pintarHeston(r) {
  const p = r.parametros;
  return h("section", { clase: "tarjeta", "aria-label": "Calibración de Heston" },
    h("h3", { texto: `Heston calibrado · ${r.contratos} contratos · ${r.convergio ? "convergió" : "NO convergió"}` }),
    h("div", { clase: "kpis" }, kpi("v0 (varianza inicial)", `${num(p.v0)} (vol ${pct(Math.sqrt(p.v0))})`),
      kpi("θ (varianza de largo plazo)", `${num(p.theta)} (vol ${pct(Math.sqrt(p.theta))})`), kpi("κ (reversión)", num(p.kappa)),
      kpi("σ (vol de la vol)", num(p.sigma)), kpi("ρ (correlación)", num(p.rho)),
      kpi("Error medio", `${num(r.rmse_iv * 100)} p. de vol.`), kpi("Feller 2κθ − σ²", num(r.feller), r.feller > 0 ? "positivo" : "negativo")),
    r.avisos.length ? h("div", { clase: "aviso-caja", role: "status" }, r.avisos.join(" ")) : null,
    h("p", { clase: "ayuda", texto: `${r.nota} Subyacente: ${num(r.spot)} (${r.origen_spot}); tasa ${pct(r.tasa)} (${r.origen_tasa}); sin dividendos.` }),
    tabla([{ t: "Contrato", f: (c) => c.contrato }, { t: "Venc.", f: (c) => c.vencimiento }, { t: "Strike", f: (c) => num(c.strike), num: true },
      { t: "Tipo", f: (c) => c.tipo }, { t: "IV mercado", f: (c) => pct(c.iv_mercado), num: true },
      { t: "Error (p. de vol.)", f: (c) => num(c.error_iv * 100), num: true }],
    [...r.ajuste].sort((a, b) => Math.abs(b.error_iv) - Math.abs(a.error_iv)).slice(0, 10), { caption: "Los 10 contratos peor ajustados" }));
}

function botonHeston(subyacente) {
  const destino = h("div", { "aria-live": "polite" });
  const b = botonAccion("Calibrar modelo de Heston", "boton--secundario", async (btn) => {
    ocupado([btn], true);
    destino.replaceChildren(h("p", { clase: "suave", texto: "Calibrando (unos segundos)…" }));
    try { destino.replaceChildren(pintarHeston(await api("/api/flujo/heston", { method: "POST", json: { subyacente } }))); }
    catch (e) { destino.replaceChildren(errorCaja(e)); }
    finally { ocupado([btn], false); }
  });
  return h("div", {}, h("h2", { texto: "Modelo de volatilidad estocástica (Heston)" }),
    h("p", { clase: "ayuda", texto: "Ajusta los 5 parámetros de Heston a los precios medios de contratos fuera del dinero (7–180 días). Describe la superficie; no predice. Código propio desde los artículos publicados (Heston 1993; Albrecher et al. 2007; Cui et al. 2017)." }),
    b, destino);
}

function enlaceHftbacktest(simbolo) {
  return h("p", { clase: "ayuda" }, h("a", { href: `/api/flujo/hftbacktest?simbolo=${encodeURIComponent(simbolo)}`, clase: "boton boton--secundario", texto: "Exportar a hftbacktest (.npz)" }),
    " Libro y operaciones guardados en el formato de eventos de hftbacktest (MIT), para backtests fuera de la terminal. Las instantáneas son espaciadas: no equivalen a un libro continuo.");
}

function formImportarExterno(simboloActual, alTerminar) {
  const campo = (nombre, etiqueta, valor, extra = {}) => { const i = h("input", { name: nombre, required: true, ...extra }); i.value = valor; return h("label", {}, `${etiqueta} `, i); };
  const sel = (nombre, etiqueta, opciones) => h("label", {}, `${etiqueta} `, h("select", { name: nombre }, opciones.map(([v, t]) => h("option", { value: v }, t))));
  const archivo = h("input", { type: "file", name: "archivo", accept: ".csv,text/csv", required: true, "aria-label": "CSV exportado" });
  const boton = h("button", { type: "submit", clase: "boton boton--secundario", texto: "Importar exportación" });
  const salida = h("p", { clase: "ayuda", role: "status" });
  const form = h("form", { clase: "formulario" }, archivo,
    campo("simbolo", "Símbolo", simboloActual || "", { size: 18 }), campo("mercado", "Mercado", "BMV", { size: 10 }),
    sel("intervalo", "Intervalo", Object.entries(NOMBRE_INTERVALO).reverse()),
    campo("fuente", "Fuente", "tradingview", { size: 14 }), campo("licencia", "Licencia o permiso", "", { size: 28, placeholder: "p. ej. suscripción personal" }),
    sel("zona", "Zona de fechas sin zona", [["America/Mexico_City", "Ciudad de México"], ["America/New_York", "Nueva York"], ["UTC", "UTC"]]), boton);
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const fd = new FormData(form);
    ocupado([boton], true);
    try {
      const r = await api("/api/flujo/importar-externo", { method: "POST", body: fd });
      salida.textContent = `Formato detectado: ${r.formato_detectado}. ${r.guardados} velas guardadas de ${r.filas} filas. ${r.nota}`;
      await estadoFlujo(true); if (alTerminar) alTerminar();
    } catch (e) { salida.textContent = e.message; }
    finally { ocupado([boton], false); }
  });
  return h("details", { clase: "importar-flujo" }, h("summary", { texto: "Importar velas exportadas de TradingView, OpenBB o una hoja (Yahoo/Excel)" }),
    h("p", { clase: "ayuda", texto: "Se reconocen columnas time/date/datetime y open, high, low, close (volume opcional). TradingView: «Exportar datos del gráfico» (tiempo Unix). OpenBB: obb.equity.price.historical(...).to_csv(). Solo datos que tenga derecho a usar; se guardan como «importado» con la fuente y licencia que declare." }),
    form, salida);
}

/* ---------- Etapa 3: riesgo, seguimiento y comparación, backtesting ---------- */
const PALETA = ["var(--serie-1)", "var(--serie-2)", "var(--retrasado)", "var(--sintetico)", "var(--positivo)", "var(--negativo)", "var(--acento)", "var(--sin-datos)"];
const etapa3 = { riesgo: { ventana: 252, horizonte: "" }, comparar: { ids: [], referencia: "BMV:NAFTRAC", ventana: 252 },
  bt: { ids: [], estrategia: "pesos_iguales", parametros: {}, desde: "", hasta: "", deslizamiento_pb: 5 }, ficha: null };
async function universo() {
  if (!estado.universo) estado.universo = (await api("/api/universo")).instrumentos;
  return estado.universo.filter((i) => i.estado === "activo" || i.estado === undefined);
}
function selectorUniverso(lista, valor, alCambiar, etiqueta, multiple = false) {
  const sel = h("select", { "aria-label": etiqueta, multiple: multiple || null, size: multiple ? 8 : null },
    multiple ? null : h("option", { value: "" }, "Elija…"), lista.map((i) => h("option", { value: i.id }, `${i.clave_operable || i.id} · ${i.id}`)));
  if (multiple) [...sel.options].forEach((o) => { o.selected = valor.includes(o.value); }); else sel.value = valor;
  sel.addEventListener("change", () => alCambiar(multiple ? [...sel.selectedOptions].map((o) => o.value) : sel.value));
  return h("label", {}, `${etiqueta} `, sel);
}
const barraPeso = (w) => h("span", { clase: "fila-peso" }, barraPct(Math.abs(w), 1), h("span", { clase: "num", texto: pct(w) }));

async function cargarRiesgo() {
  try {
    const R = etapa3.riesgo;
    const d = await api(`/api/riesgo?ventana=${R.ventana}${R.horizonte ? `&horizonte=${R.horizonte}` : ""}`);
    const horiz = h("input", { type: "number", min: 1, max: 252, size: 5 }); horiz.value = R.horizonte || "";
    horiz.addEventListener("change", () => { R.horizonte = horiz.value; cargarRiesgo(); });
    const controles = h("div", { clase: "fila-controles" },
      selectorSimple(R.ventana, [[126, "126 sesiones (6 meses)"], [252, "252 sesiones (1 año)"], [504, "504 sesiones (2 años)"]], (x) => { R.ventana = Number(x); cargarRiesgo(); }, "Ventana"),
      h("label", {}, "Horizonte (sesiones; vacío = fin del Reto) ", horiz));
    if (!d.suficiente) { limpiar("riesgo-contenido", controles, h("div", { clase: "aviso-caja", texto: d.motivo || "Historia insuficiente para medir el riesgo." })); return; }
    const m = d.metricas, v95 = m.var["95"], v99 = m.var["99"];
    limpiar("riesgo-contenido", controles,
      h("p", { clase: "ayuda", texto: `Cartera valuada en ${mxn(d.valor_mxn)} (fuente: ${d.fuente_cartera === "portal" ? "captura del portal" : "registro local"}). ${d.nota}` }),
      h("div", { clase: "kpis" }, kpi("Volatilidad anual", pct(m.vol_anual)), kpi("Caída máxima", pct(m.max_drawdown), "negativo"),
        kpi("Caída desde el máximo", pct(m.drawdown_actual), m.drawdown_actual < 0 ? "negativo" : ""),
        kpi("VaR 95 % 1 día (histórico)", `${pct(v95.historico_1d)} · ${mxn(v95.historico_1d_mxn)}`),
        kpi("CVaR 95 % 1 día", `${pct(v95.cvar_1d)} · ${mxn(v95.cvar_1d_mxn)}`),
        kpi(`VaR 95 % a ${d.horizonte_sesiones} sesiones`, `${pct(v95.historico_h)} · ${mxn(v95.historico_h_mxn)}`),
        kpi("VaR 99 % 1 día", pct(v99.historico_1d)), kpi("VaR 95 % paramétrico (normal)", pct(v95.parametrico_1d))),
      h("p", { clase: "ayuda", texto: `Peor día: ${pct(m.peor_dia)} (${m.fecha_peor_dia}); caída máxima tocó fondo el ${m.fecha_max_drawdown}. VaR = pérdida que solo se superó en el 5 % (o 1 %) de los días de la ventana; CVaR = pérdida promedio de esos días.` }),
      h("h2", { texto: "Exposición y concentración" }),
      h("div", { clase: "kpis" }, kpi("Mayor posición", `${d.concentracion.mayor} · ${pct(d.concentracion.peso_mayor)}`),
        kpi("Índice HHI", num(d.concentracion.hhi)), kpi("Emisoras efectivas", num(d.concentracion.emisoras_efectivas)), kpi("Efectivo", pct(d.exposicion.efectivo))),
      tabla([{ t: "Emisora", f: (r) => r[0] }, { t: "Peso", f: (r) => barraPeso(r[1]) },
        { t: "Contribución al riesgo", f: (r) => (d.contribucion_riesgo[r[0]] == null ? "—" : barraPeso(d.contribucion_riesgo[r[0]])) }],
      Object.entries(d.exposicion.emisora), { caption: "Peso en la cartera y parte de la varianza que aporta cada emisora (suma 100 %)" }),
      tabla([{ t: "Mercado", f: (r) => r[0] }, { t: "Peso", f: (r) => barraPeso(r[1]) }], Object.entries(d.exposicion.mercado), { caption: "Por mercado del simulador" }),
      tabla([{ t: "Moneda del subyacente", f: (r) => r[0] }, { t: "Peso", f: (r) => barraPeso(r[1]) }], Object.entries(d.exposicion.moneda_subyacente), { caption: "Exposición al tipo de cambio: el SIC sigue al dólar" }),
      h("h2", { texto: "Escenarios" }),
      tabla([{ t: "Escenario", f: (e) => e.escenario }, { t: "Tipo", f: (e) => e.tipo },
        { t: "Cambio de la cartera", f: (e) => h("span", { clase: signo(e.cambio), texto: pct(e.cambio) }), num: true },
        { t: "En pesos", f: (e) => mxn(e.cambio_mxn), num: true }], d.escenarios, { caption: "Hipotéticos (choques instantáneos), históricos (peores tramos con los pesos actuales) y de estrés" }),
      d.sin_historia.length ? h("div", { clase: "aviso-caja", texto: `Sin historia suficiente (no entran al cálculo): ${d.sin_historia.join(", ")}.` }) : null,
      h("h2", { texto: "Supuestos" }), h("ul", { clase: "ayuda" }, d.supuestos.map((x) => h("li", { texto: x }))));
  } catch (e) { limpiar("riesgo-contenido", errorCaja(e)); }
}

function pintarFicha(f) {
  return h("section", { clase: "tarjeta", "aria-label": `Ficha de ${f.clave}` }, h("h3", { texto: `${f.clave} · ${f.nombre || ""}` }),
    h("p", { clase: "ayuda", texto: f.nota }),
    h("h4", { texto: "Noticias" }),
    tabla([{ t: "Publicado", f: (n) => fechaLocal(n.publicado) }, { t: "Titular", f: (n) => externo(n.enlace, n.titulo) }, { t: "Fuente", f: (n) => n.fuente },
      { t: "Sentimiento", f: (n) => h("span", { clase: signo(n.sentimiento), texto: n.sentimiento > 0 ? "Positivo" : n.sentimiento < 0 ? "Negativo" : "Neutro" }) }],
    f.noticias.slice(0, 15), { vacio: "Sin titulares guardados para este instrumento." }),
    h("h4", { texto: "Estados financieros e investigación" }),
    tabla([{ t: "Periodo", f: (o) => o.periodo }, { t: "Dato", f: (o) => o.titulo }, { t: "Valor", f: (o) => (o.unidad === "fracción" ? pct(o.valor) : num(o.valor)), num: true },
      { t: "Unidad", f: (o) => o.unidad }, { t: "Fuente", f: (o) => `${o.fuente} (${o.origen})` }], f.financieros,
    { vacio: "Sin estados financieros: Alpha Vantage cubre MU, AMD, NVDA y XOM; el resto se importa en «Investigación»." }));
}

async function cargarSeguimiento() {
  try {
    const lista = await universo();
    const d = await api("/api/lista-seguimiento");
    const C = etapa3.comparar;
    let nuevo = "";
    const nota = h("input", { type: "text", maxlength: 300, size: 24, placeholder: "Nota (opcional)", "aria-label": "Nota" });
    const agregar = botonAccion("Agregar a la lista", "boton--primario", async (b) => {
      if (!nuevo) { notificar("Elija un instrumento."); return; }
      ocupado([b], true);
      try { await api("/api/lista-seguimiento", { method: "POST", json: { id: nuevo, nota: nota.value } }); cargarSeguimiento(); }
      catch (e) { notificar(e.message); } finally { ocupado([b], false); }
    });
    const quitar = (iid) => botonAccion("Quitar", "boton--secundario", async () => { await api("/api/lista-seguimiento", { method: "POST", json: { id: iid, quitar: true } }); cargarSeguimiento(); });
    const fichaBtn = (iid) => botonAccion("Ficha", "boton--secundario", async () => {
      try { etapa3.ficha = iid; document.getElementById("seguimiento-ficha").replaceChildren(pintarFicha(await api(`/api/ficha/${encodeURIComponent(iid)}`))); }
      catch (e) { notificar(e.message); }
    });
    const marcar = (iid) => { const c = h("input", { type: "checkbox", "aria-label": `Comparar ${iid}` }); c.checked = C.ids.includes(iid);
      c.addEventListener("change", () => { C.ids = c.checked ? [...C.ids, iid] : C.ids.filter((x) => x !== iid); }); return c; };
    const v = (x) => (x == null ? "—" : h("span", { clase: signo(x), texto: `${x > 0 ? "+" : ""}${pct(x)}` }));
    limpiar("seguimiento-contenido",
      h("h2", { texto: "Lista de seguimiento" }),
      h("div", { clase: "fila-controles" }, selectorUniverso(lista, "", (x) => { nuevo = x; }, "Instrumento"), nota, agregar),
      tabla([{ t: "Comparar", f: (f) => marcar(f.instrumento_id) }, { t: "Clave", f: (f) => f.clave }, { t: "Último (MXN)", f: (f) => num(f.ultimo_mxn), num: true },
        { t: "Fecha", f: (f) => f.fecha }, { t: "1 sesión", f: (f) => v(f.variacion["1"]), num: true }, { t: "5 sesiones", f: (f) => v(f.variacion["5"]), num: true },
        { t: "20 sesiones", f: (f) => v(f.variacion["20"]), num: true }, { t: "RSI 14", f: (f) => num(f.rsi14), num: true },
        { t: "Noticias 7 d", f: (f) => f.noticias_7d, num: true }, { t: "Nota", f: (f) => f.nota || "—" },
        { t: "", f: (f) => h("span", { clase: "fila-controles" }, fichaBtn(f.instrumento_id), quitar(f.instrumento_id)) }],
      d.instrumentos, { caption: d.nota, vacio: "Lista vacía: agregue instrumentos para seguirlos y compararlos." }),
      h("div", { id: "seguimiento-ficha", "aria-live": "polite" }),
      h("h2", { texto: "Comparación de instrumentos" }),
      h("p", { clase: "ayuda", texto: "Marque de 2 a 8 instrumentos en la lista (o elíjalos abajo) y pulse «Comparar»." }),
      h("div", { clase: "fila-controles" }, selectorUniverso(lista, C.ids, (x) => { C.ids = x; }, "Instrumentos", true),
        selectorSimple(C.referencia, [["BMV:NAFTRAC", "NAFTRAC (IPC)"], ["SIC:SPY", "SPY (S&P 500)"]], (x) => { C.referencia = x; }, "Referencia"),
        selectorSimple(C.ventana, [[63, "3 meses"], [126, "6 meses"], [252, "1 año"], [504, "2 años"]], (x) => { C.ventana = Number(x); }, "Ventana"),
        botonAccion("Comparar", "boton--primario", async (b) => {
          ocupado([b], true);
          try { pintarComparacion(await api(`/api/comparar?ids=${encodeURIComponent(C.ids.join(","))}&ventana=${C.ventana}&referencia=${encodeURIComponent(C.referencia)}`)); }
          catch (e) { document.getElementById("comparacion").replaceChildren(errorCaja(e)); } finally { ocupado([b], false); }
        })),
      h("div", { id: "comparacion", "aria-live": "polite" }));
    if (etapa3.ficha) { try { document.getElementById("seguimiento-ficha").replaceChildren(pintarFicha(await api(`/api/ficha/${encodeURIComponent(etapa3.ficha)}`))); } catch { /* sin ficha */ } }
  } catch (e) { limpiar("seguimiento-contenido", errorCaja(e)); }
}

function pintarComparacion(d) {
  const ids = d.correlacion.ids;
  const clave = (i) => (d.metricas.find((m) => m.id === i) || {}).clave || i;
  const corr = (v) => { const s = h("span", { clase: "celda-iv", texto: num(v) }); s.style.backgroundColor = `color-mix(in srgb, var(--serie-1) ${Math.round(Math.abs(v) * 60)}%, transparent)`; return s; };
  document.getElementById("comparacion").replaceChildren(
    h("p", { clase: "ayuda", texto: `${d.desde} a ${d.hasta} · ${d.sesiones} sesiones comunes. ${d.nota}` }),
    grafica(ids.map((i, k) => ({ nombre: clave(i), color: PALETA[k % PALETA.length], datos: d.serie.fechas.map((f, j) => ({ x: f, y: d.serie[i][j] })) })),
      { formato: num, etiqueta: "Valor de 100 invertidos al inicio" }),
    tabla([{ t: "Instrumento", f: (m) => `${m.clave}${m.es_referencia ? " (referencia)" : ""}` }, { t: "Rend. total", f: (m) => pct(m.rend_total), num: true },
      { t: "Rend. anual", f: (m) => pct(m.rend_anual), num: true }, { t: "Volatilidad", f: (m) => pct(m.vol_anual), num: true },
      { t: "Caída máx.", f: (m) => pct(m.max_drawdown), num: true }, { t: "Beta", f: (m) => num(m.beta), num: true },
      { t: "Sharpe (sin tasa)", f: (m) => num(m.sharpe_sin_tasa), num: true }], d.metricas, { caption: "Métricas en el periodo común" }),
    tabla([{ t: "", f: (r) => clave(r.i) }, ...ids.map((j, k) => ({ t: clave(j), num: true, f: (r) => corr(d.correlacion.matriz[ids.indexOf(r.i)][k]) }))],
      ids.map((i) => ({ i })), { caption: "Correlación de rendimientos diarios" }));
}

async function cargarBacktesting() {
  try {
    const lista = await universo();
    const meta = await api("/api/backtests");
    const B = etapa3.bt;
    if (!B.ids.length) {
      try { B.ids = (await api("/api/lista-seguimiento")).instrumentos.map((i) => i.instrumento_id).slice(0, 10); } catch { /* lista vacía */ }
    }
    const est = meta.estrategias[B.estrategia];
    const params = Object.entries(est.parametros).map(([k, def]) => {
      const i = h("input", { type: "number", min: meta.limites[k][0], max: meta.limites[k][1], step: 1, size: 5 });
      i.value = B.parametros[k] ?? def; i.addEventListener("change", () => { B.parametros[k] = Number(i.value); });
      return h("label", {}, `${{ rebalanceo: "Rebalanceo cada (sesiones)", rapida: "SMA rápida", lenta: "SMA lenta", lookback: "Ventana de momento", k: "Cuántos (k)" }[k] || k} `, i);
    });
    const fecha = (k, t) => { const i = h("input", { type: "date" }); i.value = B[k]; i.addEventListener("change", () => { B[k] = i.value; }); return h("label", {}, `${t} `, i); };
    const desl = h("input", { type: "number", min: 0, max: 200, step: 1, size: 5 }); desl.value = B.deslizamiento_pb;
    desl.addEventListener("change", () => { B.deslizamiento_pb = Number(desl.value); });
    limpiar("backtesting-contenido",
      h("div", { clase: "fila-controles" }, selectorUniverso(lista, B.ids, (x) => { B.ids = x; }, "Instrumentos (Ctrl+clic)", true),
        h("div", { clase: "formulario" },
          selectorSimple(B.estrategia, Object.entries(meta.estrategias).map(([k, e]) => [k, `${e.nombre} · v${e.version}`]), (x) => { B.estrategia = x; B.parametros = {}; cargarBacktesting(); }, "Estrategia"),
          ...params, fecha("desde", "Desde"), fecha("hasta", "Hasta"), h("label", {}, "Deslizamiento (pb) ", desl),
          botonAccion("Correr backtest", "boton--primario", async (b) => {
            ocupado([b], true);
            try { pintarBacktest(await api("/api/backtests", { method: "POST", json: B })); cargarHistorialBt(); }
            catch (e) { document.getElementById("backtest-resultado").replaceChildren(errorCaja(e)); } finally { ocupado([b], false); }
          }))),
      h("p", { clase: "ayuda", texto: "Simulación con cierres diarios: la señal usa datos hasta el cierre de un día y se opera al cierre del siguiente; comisión del Reto + deslizamiento; banda de 1 punto. Sin fecha inicial se usan 2 años. Nunca envía órdenes." }),
      h("div", { id: "backtest-resultado", "aria-live": "polite" }),
      h("h2", { texto: "Historial de corridas" }), h("div", { id: "backtest-historial" }));
    pintarHistorialBt(meta.historial);
  } catch (e) { limpiar("backtesting-contenido", errorCaja(e)); }
}

async function cargarHistorialBt() { try { pintarHistorialBt((await api("/api/backtests")).historial); } catch { /* sin historial */ } }
function pintarHistorialBt(hist) {
  const ver = (id) => botonAccion("Ver", "boton--secundario", async () => pintarBacktest(await api(`/api/backtests/${id}`)));
  document.getElementById("backtest-historial").replaceChildren(tabla([{ t: "#", f: (r) => r.id, num: true }, { t: "Fecha", f: (r) => fechaLocal(r.ts) },
    { t: "Estrategia", f: (r) => `${r.estrategia} v${r.version}` }, { t: "Instrumentos", f: (r) => r.parametros.ids.length, num: true },
    { t: "Periodo", f: (r) => `${r.resumen.desde} a ${r.resumen.hasta}` }, { t: "Rend. total", f: (r) => pct(r.resumen.rend_total), num: true },
    { t: "Caída máx.", f: (r) => pct(r.resumen.max_drawdown), num: true }, { t: "Datos", f: (r) => r.huella_datos }, { t: "", f: (r) => ver(r.id) }], hist,
  { vacio: "Aún no hay corridas." }));
}

function pintarBacktest(d) {
  const s = d.resumen, ref = s.referencia_comprar_y_mantener || {};
  const rep = d.reproducibilidad || {};
  document.getElementById("backtest-resultado").replaceChildren(h("section", { clase: "tarjeta" },
    h("h2", { texto: `Corrida #${d.id} · ${s.estrategia} v${s.version} · ${s.desde} a ${s.hasta}` }),
    h("div", { clase: "kpis" }, kpi("Rend. total", pct(s.rend_total), signo(s.rend_total)), kpi("Rend. anual", pct(s.rend_anual)),
      kpi("Volatilidad", pct(s.vol_anual)), kpi("Caída máx.", pct(s.max_drawdown), "negativo"), kpi("Sharpe (sin tasa)", num(s.sharpe_sin_tasa)),
      kpi("Operaciones", num(s.operaciones)), kpi("Costos", mxn(s.costo_total)), kpi("Giro anual", `${num(s.giro_anual)}×`)),
    ref.rend_total != null ? h("p", { clase: "ayuda", texto: `Referencia (comprar y mantener los mismos instrumentos, mismos costos): rendimiento ${pct(ref.rend_total)}, volatilidad ${pct(ref.vol_anual)}, caída máxima ${pct(ref.max_drawdown)}. Una diferencia en un solo periodo no demuestra ventaja.` }) : null,
    grafica([{ nombre: "Valor de la cartera simulada (MXN)", color: "var(--acento)", datos: d.curva.map((c) => ({ x: c.fecha, y: c.valor })) }], { formato: (x) => mxn(x), etiqueta: "Curva de valor del backtest" }),
    h("p", { clase: "ayuda", texto: `Reproducibilidad: huella de datos ${String(rep.huella_datos || "").slice(0, 16)}…, configuración ${String(rep.huella_config || "").slice(0, 16)}…, código v${rep.version_codigo}.${rep.igual_a_corrida ? ` Idéntica a la corrida #${rep.igual_a_corrida}.` : ""}` }),
    h("a", { href: `/api/backtests/${d.id}/exportar`, clase: "boton boton--secundario", texto: "Exportar CSV (curva y operaciones)" }),
    h("h3", { texto: "Supuestos" }), h("ul", { clase: "ayuda" }, (d.supuestos || []).map((x) => h("li", { texto: x }))),
    tabla([{ t: "Fecha", f: (o) => o.fecha }, { t: "Instrumento", f: (o) => o.id }, { t: "Títulos", f: (o) => num(o.titulos), num: true },
      { t: "Precio (MXN)", f: (o) => num(o.precio), num: true }, { t: "Importe", f: (o) => mxn(o.importe), num: true }, { t: "Costo", f: (o) => mxn(o.costo, true), num: true }],
    d.operaciones.slice(-30).reverse(), { caption: "Últimas 30 operaciones simuladas" })));
}

CARGAS["tab-riesgo"] = () => cargarRiesgo();
CARGAS["tab-seguimiento"] = () => cargarSeguimiento();
CARGAS["tab-backtesting"] = () => cargarBacktesting();
Object.assign(ATAJOS, { RIE: "tab-riesgo", SEG: "tab-seguimiento", BT: "tab-backtesting" });


/* ---------- Accesos y navegación orgánica entre análisis ---------- */
function compartirSimbolo(origen, destino) {
  const sym = { "panel-velas": flujo.velas.simbolo, "panel-orderflow": flujo.of.simbolo, "panel-optionflow": flujo.op.subyacente }[origen];
  if (!sym) return;
  if (destino === "tab-velas") flujo.velas.simbolo = sym;
  if (destino === "tab-orderflow") flujo.of.simbolo = sym;
  if (destino === "tab-optionflow" && !sym.includes("/")) flujo.op.subyacente = sym; // las opciones solo existen para el SIC
}
document.addEventListener("click", (ev) => {
  const b = ev.target.closest("[data-ir]");
  if (!b) return;
  irA(b.dataset.ir);   // activarPestana comparte el instrumento del panel visible
});

/* ---------- GEX (terminal/flujo/gex.py): mapa de calor por strike y vencimiento ---------- */
const gexUI = { vista: "absoluta" };
const fmtCompacto = new Intl.NumberFormat("es-MX", { notation: "compact", maximumFractionDigits: 1 });
async function cargarGex(subyacente) {
  const cont = document.getElementById("gex-contenido");
  if (!cont) return;
  try { cont.replaceChildren(pintarGex(await api(`/api/flujo/gex?subyacente=${encodeURIComponent(subyacente)}`))); }
  catch (e) { cont.replaceChildren(errorCaja(e)); }
}
function pintarGex(d) {
  const encabezado = h("p", { clase: "ayuda", texto: `${d.formula}. ${d.nota}` });
  const avisoOi = d.aviso_oi ? h("div", { clase: "aviso-caja", role: "status",
    texto: `${d.aviso_oi}${d.oi_desactualizado ? " Hay interés abierto desactualizado; revise la fecha antes de interpretar la exposición." : ""}` }) : null;
  if (!d.disponible) {
    const desc = Object.entries(d.descartados || {}).map(([k, v]) => `${v} ${k}`).join("; ");
    return h("div", {}, encabezado, avisoOi,
      h("div", { clase: "aviso-caja", role: "status" }, h("strong", { texto: "GEX no disponible. " }), `${d.motivo}${desc && !d.motivo.includes(desc) ? ` Descartados: ${desc}.` : ""}`),
      h("p", { clase: "ayuda", texto: `Qué se necesita: ${d.requisito}` }), h("p", { clase: "ayuda", texto: d.convencion }));
  }
  const cont = h("div", {});
  const dibujar = () => {
    const firmada = gexUI.vista === "firmada";
    const valor = (z) => (firmada ? z.firmada : z.absoluta);
    let strikes = d.strikes;
    if (strikes.length > 24) strikes = [...strikes].sort((a, b) => Math.abs(a - d.spot) - Math.abs(b - d.spot)).slice(0, 24).sort((a, b) => a - b);
    const mapa = new Map(d.celdas.map((z) => [`${z.vencimiento}|${z.strike}`, z]));
    const mx = Math.max(...d.celdas.map((z) => Math.abs(valor(z))), 1e-12);
    const cols = [{ t: "Vencimiento", f: (v) => v }, ...strikes.map((k) => ({ t: num(k), num: true, f: (v) => {
      const z = mapa.get(`${v}|${k}`);
      if (!z) return "—";
      const x = valor(z), marca = h("span", { clase: "celda-gex", texto: fmtCompacto.format(x),
        title: `Strike ${num(k)} · ${v}: calls ${fmtCompacto.format(z.calls)}, puts ${fmtCompacto.format(z.puts)} ${d.moneda} por 1 %; ${z.n} contrato(s)` });
      const color = firmada && x < 0 ? "var(--vela-baja)" : firmada ? "var(--vela-sube)" : "var(--serie-2)";
      marca.style.backgroundColor = `color-mix(in srgb, ${color} ${Math.round(12 + 70 * Math.abs(x) / mx)}%, transparent)`;
      return marca;
    } }))];
    cont.replaceChildren(...[
      h("div", { clase: "fila-controles" }, selectorSimple(gexUI.vista, [["absoluta", "Exposición absoluta (calls + puts)"], ["firmada", "Estimación firmada (convención)"]], (x) => { gexUI.vista = x; dibujar(); }, "Vista")),
      d.aviso ? h("div", { clase: "aviso-caja", role: "status", texto: d.aviso }) : null,
      firmada ? h("div", { clase: "aviso-caja", role: "note", texto: d.convencion }) : h("p", { clase: "ayuda", texto: "Absoluta: cuánta gamma hay abierta, sin signo ni dirección. Cambie a «firmada» para ver la convención calls + / puts −." }),
      h("div", { clase: "kpis" }, kpi("Spot de la referencia", `${num(d.spot)} ${d.moneda}`), kpi("Instante de la cadena", horaCdmx(d.instante)),
        kpi(firmada ? "Total firmado (convención)" : "Total absoluto", `${fmtCompacto.format(firmada ? d.totales.firmada : d.totales.absoluta)} ${d.moneda}/1 %`),
        kpi("Contratos usados", `${d.contratos_usados} de ${d.total}`)),
      cajaProcedencia(d.procedencia),
      tabla(cols, d.vencimientos, { caption: `${firmada ? "GEX firmado (convención)" : "GEX absoluto"} por vencimiento y strike, ${d.moneda} por movimiento de 1 % del subyacente${d.strikes.length > 24 ? " (24 strikes más cercanos al spot)" : ""}` }),].filter(Boolean));
  };
  dibujar();
  return h("div", {}, encabezado, avisoOi, cont);
}

/* ---------- Laboratorio de alfa: permutación de signos por bloques ---------- */
const lab = { ejemplo: null };
function ejemploSintetico() {  // datos INVENTADOS con semilla fija (mulberry32 + Box-Muller); no son rendimientos de nadie
  let a = 20261016;
  const u = () => { a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  const z = () => Math.sqrt(-2 * Math.log(u() || 1e-12)) * Math.cos(2 * Math.PI * u());
  const filas = ["benchmark,estrategia_sin_exceso_sintetica,estrategia_con_exceso_sintetica"];
  for (let i = 0; i < 160; i++) {
    const b = 0.0004 + 0.01 * z();
    filas.push([b, b + 0.006 * z(), b + 0.0012 + 0.006 * z()].map((x) => x.toFixed(6)).join(","));
  }
  return filas.join("\n");
}
function cargarLaboratorio() {
  const ta = h("textarea", { rows: 9, spellcheck: "false", "aria-label": "Rendimientos netos emparejados en CSV", clase: "area-csv", placeholder: "benchmark,mi_estrategia\n0.0042,0.0051\n-0.0031,-0.0012" });
  ta.value = lab.ejemplo || "";
  const archivo = h("input", { type: "file", accept: ".csv,text/csv", "aria-label": "Archivo CSV de rendimientos" });
  archivo.addEventListener("change", async () => { if (archivo.files[0]) { ta.value = await archivo.files[0].text(); lab.ejemplo = null; } });
  const campo = (etq, nombre, valor, extra = {}) => h("label", {}, `${etq} `, h("input", { type: "number", name: nombre, value: valor, step: "any", ...extra }));
  const salida = h("div", { "aria-live": "polite" });
  const ejemplo = botonAccion("Cargar ejemplo SINTÉTICO", "boton--secundario", () => { lab.ejemplo = ejemploSintetico(); ta.value = lab.ejemplo; salida.replaceChildren(); });
  const form = h("form", { clase: "tarjeta" },
    h("p", { clase: "ayuda", texto: "Pegue o cargue un CSV con encabezado: una columna «benchmark» (o «referencia»), una o más columnas de estrategia y, opcionalmente, «fecha». Rendimientos simples NETOS de costos, en decimal (0.01 = 1 %), emparejados por fecha. Máx. 5 000 filas y 20 estrategias." }),
    h("div", { clase: "fila-controles" }, archivo, ejemplo), ta,
    h("div", { clase: "fila-controles" }, campo("Bloque (vacío = automático)", "bloque", "", { min: 1, step: 1 }), campo("Volteos B", "B", 5000, { min: 199, max: 20000, step: 1 }),
      campo("Semilla", "semilla", 12345, { min: 0, step: 1 }), campo("Nivel α", "alpha", 0.05, { min: 0.001, max: 0.49 }),
      campo("Hipótesis exploradas (≥ estrategias)", "exploradas", "", { min: 1, step: 1 })),
    h("button", { type: "submit", clase: "boton boton--primario", texto: "Ejecutar prueba" }));
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const boton = form.querySelector('button[type="submit"]'), f = form.elements;
    ocupado([boton], true);
    try {
      const r = await api("/api/laboratorio/permutacion", { method: "POST", json: { csv: ta.value, bloque: f.bloque.value || null, B: Number(f.B.value), semilla: Number(f.semilla.value),
        alpha: Number(f.alpha.value), hipotesis_exploradas: f.exploradas.value || null } });
      salida.replaceChildren(pintarPermutacion(r, lab.ejemplo !== null && ta.value === lab.ejemplo));
    } catch (e) { salida.replaceChildren(errorCaja(e)); } finally { ocupado([boton], false); }
  });
  limpiar("laboratorio-contenido", h("div", { clase: "aviso-caja", role: "note", texto: "Preregistre hipótesis y variantes antes de mirar resultados; valide con walk-forward con purga/embargo y un holdout; use solo rendimientos netos de costos. Un p < 0.05 aislado no es alfa probado." }), form, salida);
  seccionPreregistro(ta, form).then((x) => document.getElementById("laboratorio-contenido").append(x));
}
function pintarPermutacion(r, sintetico) {
  return h("div", { clase: "tarjeta" },
    sintetico ? h("p", {}, chip("sintetico", "DATOS SINTÉTICOS"), " Ejemplo inventado para ver cómo funciona la prueba; no son rendimientos reales de ninguna estrategia.") : null,
    h("h2", { texto: "Resultado" }),
    h("p", { clase: "ayuda", texto: `${r.hipotesis}. Estadístico: ${r.estadistico}. Método: ${r.metodo}.` }),
    h("div", { clase: "kpis" }, kpi("Observaciones", String(r.n)), kpi("Bloque / bloques", `${r.bloque} / ${r.bloques}`), kpi("Volteos B", String(r.B)),
      kpi("Semilla", String(r.semilla)), kpi("p mínimo posible", num(r.p_minimo)), kpi("Familia (Holm)", `${r.familia} → ${r.familia_total_holm}`)),
    tabla([{ t: "Estrategia", f: (x) => x.estrategia }, { t: "Exceso medio por periodo", f: (x) => `${(x.exceso_medio * 100).toFixed(3)} %`, num: true },
      { t: "p", f: (x) => num(x.p), num: true }, { t: "p Holm", f: (x) => num(x.p_holm), num: true },
      { t: `Holm ≤ ${num(r.alpha)}`, f: (x) => (x.supera_alpha_holm ? "Sí" : "No") }, { t: "Lectura", f: (x) => x.lectura }], r.resultados, { caption: "Hipótesis unilateral: exceso medio neto > 0" }),
    h("h3", { texto: "Advertencias y supuestos" }), h("ul", {}, r.advertencias.map((a) => h("li", { texto: a }))),
    h("p", { clase: "ayuda", texto: `Huella sha256 de entradas y parámetros (reproducibilidad): ${r.huella_sha256}` }));
}

/* ---------- Plan intradía defensivo (informativo) ---------- */
const intradia = { perdida: "" };
async function cargarIntradia() {
  try {
    const q = intradia.perdida !== "" ? `?perdida_dia_mxn=${encodeURIComponent(intradia.perdida)}` : "";
    const d = await api(`/api/plan-intradia${q}`);
    const entrada = h("input", { type: "number", min: 0, step: "any", value: intradia.perdida, "aria-label": "Pérdida del día en pesos (positiva)" });
    const boton = botonAccion("Evaluar pausa", "boton--secundario", () => { intradia.perdida = entrada.value; cargarIntradia(); });
    const P = d.presupuesto_perdida, C = d.concentracion;
    let V = null;
    try { V = await api("/api/variacion-dia"); } catch { /* sin precios de hoy: la tarjeta lo dice */ }
    const tarjetaHoy = V ? h("div", { clase: "tarjeta" }, h("h2", { texto: "Hoy frente al cierre anterior" }),
      h("div", { clase: "kpis" }, kpi("Cartera hoy", V.variacion == null ? "—" : pct(V.variacion), signo(V.variacion)), kpi("Cambio", mxn(V.cambio_mxn)),
        kpi("Aviso de pérdida", `cartera cada ${pct(V.umbrales.cartera)} · posición cada ${pct(V.umbrales.posicion)}`)),
      tabla([{ t: "Instrumento", f: (x) => x.clave }, { t: "Hoy", f: (x) => (x.variacion == null ? "sin precio de hoy" : h("span", { clase: signo(x.variacion) }, pct(x.variacion))), num: true },
        { t: "Impacto", f: (x) => (x.impacto_mxn == null ? "—" : mxn(x.impacto_mxn)), num: true },
        { t: "Cierre anterior", f: (x) => `${mxn(x.cierre_previo, true)} (${x.fecha_cierre})`, num: true }], V.posiciones, { vacio: "Sin posiciones." }),
      h("p", { clase: "ayuda", texto: V.nota })) : null;
    limpiar("intradia-contenido",
      h("div", { clase: "aviso-caja", role: "note", texto: d.aviso }),
      tarjetaHoy,
      h("div", { clase: `tarjeta ${d.inhibida ? "" : "tarjeta--destacada"}` }, h("h2", { texto: "Señal ejecutable" }),
        h("p", {}, chip(d.inhibida ? "retrasado" : "vigente", d.inhibida ? "INHIBIDA" : "Sin inhibiciones de datos"), " ", d.nota_senal),
        d.motivos_inhibicion.length ? h("ul", {}, d.motivos_inhibicion.map((m) => h("li", { texto: m }))) : null),
      h("div", { clase: "tarjeta" }, h("h2", { texto: "Pausa y presupuesto de pérdida" }),
        h("div", { clase: "fila-controles" }, h("label", {}, "Pérdida del día (MXN, positiva) ", entrada), boton),
        h("p", {}, chip(d.pausa.activa ? "vencido" : "sin_datos", d.pausa.estado.replaceAll("_", " ")), " ", d.pausa.mensaje),
        h("div", { clase: "kpis" }, kpi("Valor de la cartera", mxn(P.valor_cartera_mxn)), kpi(`Pérdida diaria máx. (${num(P.perdida_diaria_pct)} %)`, mxn(P.perdida_diaria_mxn)),
          kpi(`Pérdida máx. por idea (${num(P.perdida_por_idea_pct)} %)`, mxn(P.perdida_por_idea_mxn))),
        h("p", { clase: "ayuda", texto: `Umbrales de disciplina editables en [intradia] de la configuración (no son resultados de un modelo): ${Object.entries(d.parametros).map(([k, v]) => `${k} = ${v}`).join("; ")}.` })),
      h("div", { clase: "tarjeta" }, h("h2", { texto: "Concentración" }),
        h("div", { clase: "kpis" }, kpi("Mayor posición", C.mayor ? `${C.mayor} · ${pct(C.peso_mayor)}` : "—"), kpi("Tope aplicable", pct(C.tope)), kpi("HHI", num(C.hhi))),
        C.excede.length ? h("div", { clase: "aviso-caja", role: "status", texto: `Exceden el tope: ${C.excede.map(([k, w]) => `${k} ${pct(w)}`).join(", ")}.` }) : null),
      h("div", { clase: "tarjeta" }, h("h2", { texto: "No promediar pérdidas" }), h("p", { texto: d.no_promediar.regla }),
        tabla([{ t: "Instrumento", f: (x) => x.clave || x.instrumento_id }, { t: "No realizado", f: (x) => pct(x.no_realizado_pct), num: true }], d.no_promediar.posiciones_en_perdida, { vacio: "Ninguna posición en pérdida registrada." })),
      h("div", { clase: "tarjeta" }, h("h2", { texto: "Liquidez" }),
        tabla([{ t: "Instrumento", f: (x) => x.instrumento_id }, { t: "Títulos", f: (x) => num(x.titulos), num: true },
          { t: "% del volumen diario", f: (x) => (x.pct_del_volumen == null ? "—" : `${num(x.pct_del_volumen)} %`), num: true },
          { t: "Estado", f: (x) => chip(x.estado === "ok" ? "vigente" : x.estado === "alerta" ? "vencido" : "sin_datos", x.estado === "sin_datos" ? "Sin datos" : x.estado === "ok" ? "Dentro del límite" : "Supera el límite") },
          { t: "Nota", f: (x) => x.nota }], d.liquidez, { vacio: "Sin posiciones." })),
      h("div", { clase: "tarjeta" }, h("h2", { texto: "Costos del Reto" }),
        h("div", { clase: "kpis" }, kpi("Por operación (comisión + IVA)", d.costos.por_operacion_pct == null ? "—" : pct(d.costos.por_operacion_pct)),
          kpi("Ida y vuelta", d.costos.ida_y_vuelta_pct == null ? "—" : pct(d.costos.ida_y_vuelta_pct))), h("p", { clase: "ayuda", texto: d.costos.nota })),
      h("div", { clase: "tarjeta" }, h("h2", { texto: "Datos intradía por posición" }),
        tabla([{ t: "Instrumento", f: (x) => x.instrumento_id }, { t: "Tipo", f: (x) => x.tipo }, { t: "Apto", f: (x) => chip(x.apto ? "vigente" : "retrasado", x.apto ? "Apto" : "Inhibe") }, { t: "Motivo", f: (x) => x.motivo }], d.datos, { vacio: "Sin posiciones." })),
      h("div", { clase: "tarjeta" }, h("h2", { texto: "Disponibilidad" }),
        tabla([{ t: "Dato", f: (x) => x.dato }, { t: "Estado", f: (x) => chip(x.estado === "ok" ? "vigente" : "retrasado", x.estado === "ok" ? "Disponible" : "Falta") }, { t: "Qué se necesita", f: (x) => x.requiere }], d.disponibilidad)),
      h("div", { clase: "tarjeta" }, h("h2", { texto: "Reglas" }), h("ul", {}, d.reglas.map((r) => h("li", { texto: r })))));
  } catch (e) { limpiar("intradia-contenido", errorCaja(e)); }
}
/* ---------- Option Flow: perfil EXPERIMENTAL del filtro de Skylit (CSV de operaciones; no guarda nada) ---------- */
const NOMBRES_SKYLIT = { prima: "Prima ≥ USD 100 000", vencimiento: "≤ 183 días", volumen_oi: "Volumen/OI ≥ 10", fuera_del_dinero: "Fuera del dinero",
  accion: "Subyacente acción", una_pata: "Una sola pata", en_ask: "En el ask o encima" };
function seccionSkylit() {
  const ta = h("textarea", { rows: 5, spellcheck: "false", clase: "area-csv", "aria-label": "Operaciones de opciones en CSV (plantilla Skylit)" });
  const archivo = h("input", { type: "file", accept: ".csv,text/csv", "aria-label": "Archivo CSV de operaciones de opciones" });
  archivo.addEventListener("change", async () => { if (archivo.files[0]) ta.value = await archivo.files[0].text(); });
  const salida = h("div", { "aria-live": "polite" });
  const estado = (e) => chip(e === "cumple" || e === "pasa" ? "vigente" : e === "no_evaluable" ? "sin_datos" : "vencido",
    e === "cumple" ? "Cumple" : e === "pasa" ? "Pasa" : e === "no_evaluable" ? "No evaluable" : e === "no_pasa" ? "No pasa" : "No cumple");
  const evaluar = async (b, guardado = false) => {
    ocupado([b], true);
    try {
      const r = guardado ? await api(`/api/flujo/skylit?subyacente=${encodeURIComponent(flujo.op.subyacente)}`)
        : await api("/api/flujo/skylit", { method: "POST", json: { csv: ta.value } });
      const faltan = Object.entries(r.no_evaluables_por_criterio);
      salida.replaceChildren(h("div", {},
        h("p", { clase: "aviso-caja", role: "status", texto: r.nota }), cajaProcedencia(r.procedencia || []),
        h("div", { clase: "kpis" }, kpi("Operaciones", String(r.operaciones)), kpi("Pasan", String(r.conteo.pasa)), kpi("No pasan", String(r.conteo.no_pasa)),
          kpi("No evaluables", String(r.conteo.no_evaluable)), kpi("Filtro completo aplicado", r.filtro_completo_aplicado ? "Sí" : "No")),
        faltan.length ? h("div", { clase: "aviso-caja", role: "status",
          texto: "Criterios sin datos: " + faltan.map(([k, n]) => `${NOMBRES_SKYLIT[k]} (${n})`).join(", ") + ". Esas operaciones no cuentan como filtradas." }) : null,
        tabla([{ t: "Instante", f: (x) => horaCdmx(x.instante) }, { t: "Contrato", f: (x) => x.contrato }, { t: "Días", f: (x) => x.dte, num: true },
          { t: "Prima USD", f: (x) => (x.prima_usd == null ? "—" : num(x.prima_usd)), num: true },
          { t: "Volumen contrato", f: (x) => (x.volumen_contrato_dia == null ? "—" : num(x.volumen_contrato_dia)), num: true },
          { t: "Interés abierto", f: (x) => (x.interes_abierto == null ? "—" : `${num(x.interes_abierto)}${x.fecha_oi ? ` (${x.fecha_oi})` : ""}`), num: true },
          ...Object.keys(NOMBRES_SKYLIT).map((k) => ({ t: NOMBRES_SKYLIT[k], f: (x) => h("span", { title: x.criterios[k].motivo || "" }, estado(x.criterios[k].estado)) })),
          { t: "Resultado", f: (x) => estado(x.resultado) }], r.filas, { caption: `Criterios del video por operación (calidad: ${r.calidad})` }),
        r.errores.length ? h("p", { clase: "ayuda", texto: `Filas descartadas: ${r.errores.map((e) => `${e.fila} (${e.error})`).join("; ")}` }) : null,
        h("ul", {}, r.avisos.map((a) => h("li", { texto: a })))));
    } catch (e) { salida.replaceChildren(errorCaja(e)); } finally { ocupado([b], false); }
  };
  const boton = botonAccion("Evaluar CSV", "boton--primario", (b) => evaluar(b));
  const guardado = botonAccion("Evaluar cinta guardada", "boton--secundario", (b) => evaluar(b, true));
  const contratos = h("input", { type: "text", maxlength: 2400, "aria-label": "Contratos de la cadena para actualizar cinta (OCC separados por coma)" });
  const actualizar = botonAccion("Actualizar cinta indicativa (≥ 15 min)", "boton--secundario", async (b) => {
    const seleccion = contratos.value.split(",").map((x) => x.trim().toUpperCase()).filter(Boolean);
    if (await pedirActualizacion("opciones_operaciones", flujo.op.subyacente, seleccion.length ? { contratos: seleccion } : {}, b)) await evaluar(guardado, true);
  });
  return h("div", { clase: "tarjeta" }, h("h2", { texto: "Filtro de Option Flow (perfil experimental, criterios de un video de Skylit)" }),
    h("p", { clase: "ayuda", texto: "Necesita la cinta de operaciones de opciones con NBBO del instante, condición, número de patas, interés abierto con su fecha, spot y clase del subyacente. Una cadena de opciones no la sustituye; el feed gratuito de Alpaca no trae interés abierto ni patas. Sin esos campos el criterio queda «no evaluable». No es una regla validada ni una recomendación." }),
    h("p", { clase: "aviso-caja", texto: "Cinta Alpaca indicativa y retrasada: el filtro completo no se aplica sin NBBO del instante, patas e interés abierto. Actualice primero la cadena para elegir contratos." }),
    h("label", { clase: "campo-bloque" }, "Contratos de la cadena para consultar (OCC separados por coma; máximo 100; vacío usa toda la cadena si cabe) ", contratos),
    h("div", { clase: "fila-controles" }, guardado, actualizar),
    h("div", { clase: "fila-controles" }, archivo, h("a", { href: "/api/flujo/skylit/plantilla", clase: "boton boton--secundario", texto: "Descargar plantilla" }), boton), ta, salida);
}

/* ---------- Laboratorio: preregistro y holdout de un solo uso ---------- */
async function seccionPreregistro(taCsv, formParams) {
  const t = (n, etq, max, filas = 1) => h("label", { clase: "campo-bloque" }, `${etq} `, filas > 1 ? h("textarea", { name: n, rows: filas, maxlength: max }) : h("input", { name: n, maxlength: max }));
  const salida = h("div", { "aria-live": "polite" });
  const lista = h("div", {});
  const form = h("form", { clase: "tarjeta" }, h("h2", { texto: "1. Preregistro (antes de mirar resultados)" }),
    h("p", { clase: "ayuda", texto: "Fija hipótesis, estrategias, costos, fuentes, cómo se estimaron los parámetros (walk-forward), holdout y embargo. Usa B, semilla, α, bloque e hipótesis exploradas del formulario de arriba. Queda guardado con huella sha256 y fecha." }),
    t("nombre", "Nombre", 80), t("hipotesis", "Hipótesis", 600, 2), t("benchmark", "Benchmark", 120), t("costos", "Costos incluidos", 400, 2),
    t("fuentes", "Fuentes y licencia de los datos", 600, 2), t("walk_forward", "Walk-forward y purga usados para generar los rendimientos", 600, 2),
    t("estrategias", "Estrategias (nombres de columna, separados por coma)", 400),
    h("div", { clase: "fila-controles" }, h("label", {}, "Holdout (fracción final) ", h("input", { type: "number", name: "holdout", value: 0.3, min: 0.1, max: 0.5, step: 0.05 })),
      h("label", {}, "Embargo (observaciones) ", h("input", { type: "number", name: "embargo", value: 5, min: 0, max: 250, step: 1 }))),
    h("button", { type: "submit", clase: "boton boton--primario", texto: "Guardar preregistro" }));
  const pintarEvaluacion = (r) => salida.replaceChildren(h("div", { clase: "tarjeta" },
    r.holdout_ya_usado ? h("div", { clase: "aviso-caja", role: "status", texto: r.aviso_reuso }) : null,
    h("div", { clase: "kpis" }, kpi("Exploración", String(r.tramos.exploracion)), kpi("Embargo", String(r.tramos.embargo)), kpi("Holdout", String(r.tramos.holdout))),
    h("p", { clase: "ayuda", texto: r.lectura }), h("h3", { texto: "Holdout (confirmatorio)" }), pintarPermutacion(r.holdout, false),
    h("h3", { texto: "Exploración (descriptiva)" }), pintarPermutacion(r.exploracion, false),
    h("p", { clase: "ayuda", texto: `Huella del preregistro: ${r.huella_preregistro}` })));
  const pintarLista = async () => {
    const d = await api("/api/laboratorio/experimentos");
    lista.replaceChildren(h("h2", { texto: "2. Evaluar con el CSV de arriba (el holdout se usa una sola vez)" }),
      tabla([{ t: "#", f: (x) => x.id, num: true }, { t: "Nombre", f: (x) => x.nombre }, { t: "Preregistrado", f: (x) => horaCdmx(x.creado_en) },
        { t: "Holdout", f: (x) => (x.evaluado_en ? `usado ${horaCdmx(x.evaluado_en)}` : "sin usar") },
        { t: "", f: (x) => h("span", {}, botonAccion(x.evaluado_en ? "Ver resultado" : "Evaluar", "boton--secundario", async (b) => {
          ocupado([b], true);
          try { pintarEvaluacion(await api(`/api/laboratorio/experimentos/${x.id}/evaluar`, { method: "POST", json: { csv: taCsv.value } })); pintarLista(); }
          catch (e) { salida.replaceChildren(errorCaja(e)); } finally { ocupado([b], false); }
        }), " ", h("a", { href: `/api/laboratorio/experimentos/${x.id}/exportar`, clase: "boton boton--texto", texto: "Exportar JSON" })) }],
      d.experimentos, { vacio: "Sin preregistros." }));
  };
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const f = form.elements, p = formParams.elements, b = form.querySelector('button[type="submit"]');
    ocupado([b], true);
    try {
      const r = await api("/api/laboratorio/preregistro", { method: "POST", json: { nombre: f.nombre.value, hipotesis: f.hipotesis.value, benchmark: f.benchmark.value,
        costos: f.costos.value, fuentes: f.fuentes.value, walk_forward: f.walk_forward.value, estrategias: f.estrategias.value.split(",").map((s) => s.trim()).filter(Boolean),
        holdout: Number(f.holdout.value), embargo: Number(f.embargo.value), B: Number(p.B.value), semilla: Number(p.semilla.value), alpha: Number(p.alpha.value),
        bloque: p.bloque.value || null, exploradas: p.exploradas.value || null } });
      notificar(`Preregistro #${r.id} guardado (huella ${r.huella_preregistro.slice(0, 12)}…).`);
      pintarLista();
    } catch (e) { salida.replaceChildren(errorCaja(e)); } finally { ocupado([b], false); }
  });
  try { await pintarLista(); } catch (e) { lista.replaceChildren(errorCaja(e)); }
  return h("div", {}, form, h("div", { clase: "tarjeta" }, lista), salida);
}
/* ---------- Asistente (terminal/asistente.py): datos, documentación y notas del usuario ---------- */
const asistenteUI = { mensajes: [] };
const NOMBRE_MOTOR = { claude: "Claude", ollama: "Ollama (local)", local: "respuestas locales", documentacion: "documentación y notas", comando: "comando", notas: "notas" };
function pintarAsistente() {
  const c = document.getElementById("asistente-conversacion");
  if (!asistenteUI.mensajes.length) {
    c.replaceChildren(h("p", { clase: "ayuda", texto: "Escribe una pregunta, por ejemplo «¿qué significa VaR?» o «¿por qué MU?». Para enseñarme algo: /nota <texto>." }));
    return;
  }
  c.replaceChildren(...asistenteUI.mensajes.map((m) => h("div", { clase: `asistente-msg asistente-msg--${m.de}` },
    h("span", { clase: "asistente-quien", texto: m.de === "tu" ? "Tú" : `Asistente${m.motor ? ` · ${NOMBRE_MOTOR[m.motor] || m.motor}` : ""}` }),
    h("div", { clase: "asistente-texto", texto: m.texto }))));
  c.scrollTop = c.scrollHeight;
}
async function preguntarAsistente(texto) {
  texto = (texto || "").trim();
  if (!texto) return;
  const f = document.getElementById("form-asistente"), b = f.querySelector('button[type="submit"]');
  asistenteUI.mensajes.push({ de: "tu", texto });
  pintarAsistente();
  ocupado([b], true);
  try {
    const r = await api("/api/asistente", { method: "POST", json: { texto } });
    asistenteUI.mensajes.push({ de: "asistente", texto: r.respuesta, motor: r.motor });
    if (["claude", "ollama", "local"].includes(r.motor)) document.getElementById("asistente-motor").textContent = `Motor: ${NOMBRE_MOTOR[r.motor]}.`;
  } catch (e) { asistenteUI.mensajes.push({ de: "asistente", texto: `Error: ${e.message}` }); }
  finally { ocupado([b], false); pintarAsistente(); }
}
document.getElementById("form-asistente").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const t = document.getElementById("asistente-texto");
  const v = t.value; t.value = "";
  preguntarAsistente(v);
});
document.getElementById("asistente-texto").addEventListener("keydown", (ev) => {
  if (ev.key === "Enter" && !ev.shiftKey) { ev.preventDefault(); document.getElementById("form-asistente").requestSubmit(); }
});
document.querySelectorAll("[data-pregunta]").forEach((b) => b.addEventListener("click", () => preguntarAsistente(b.dataset.pregunta)));
CARGAS["tab-asistente"] = () => { pintarAsistente(); document.getElementById("asistente-texto").focus(); };
ATAJOS.ASI = "tab-asistente";
CARGAS["tab-laboratorio"] = () => cargarLaboratorio();
CARGAS["tab-intradia"] = () => cargarIntradia();
Object.assign(ATAJOS, { LAB: "tab-laboratorio", INT: "tab-intradia", GEX: "tab-optionflow" });

/* Recursos aportados: fórmulas verificadas y microestructura sin inventar datos. */
async function cargarAprendizaje() {
  try {
    const d = await api('/api/aprendizaje');
    const link = (titulo, url) => url ? h('a', {href:url, target:'_blank', rel:'noopener noreferrer', texto:titulo}) : h('span', {texto:titulo});
    const c = d.captura_referencia;
    limpiar('aprendizaje-contenido', h('p', {clase:'ayuda', texto:`Revisión ${d.revisado}. ${d.aviso}`}),
      h('h2', {texto:'Catálogo maestro y configuración de plataformas'}),
      ...(d.documentos || []).map(r => h('article', {clase:'tarjeta'}, h('h3', {}, link(r.titulo,r.url)), h('p', {texto:r.detalle}))),
      h('h2', {texto:'Indicadores — PDF de Ana Jiménez, Actinver Acelera Academy'}),
      ...d.indicadores.map(i => h('article', {clase:'tarjeta'}, h('h3', {texto:i.titulo}), h('p', {}, h('code', {texto:i.formula})),
        h('p', {texto:i.interpretacion}), h('p', {clase:'ayuda', texto:`Precisión: ${i.precision} Fuente: ${i.archivo}, página 1.`}))),
      h('p', {}, h('button', {type:'button', clase:'boton', 'data-ir':'tab-velas', texto:'Practicar con las velas'})),
      h('h2', {texto:'Capturas de la plataforma'}), ...d.capturas_plataforma.map(r => h('p', {texto:`${r.archivo}: ${r.observado} ${r.aplicacion}`})),
      h('h2', {texto:'Videos, investigación y documentación de mercados'}),
      ...d.cursos.map(r => h('article', {clase:'tarjeta'}, h('h3', {}, link(r.titulo,r.url)), h('p', {texto:`${r.autor} · ${r.captura}. ${r.estado}`}),
        h('p', {texto:r.conceptos.join(' · ')}), h('p', {texto:`Ejercicio: ${r.ejercicio}`}))),
      h('h2', {texto:'Formación de las capturas y los posts: condiciones de acceso'}),
      h('p', {texto:'Orden por área: gratuitas, condicionadas, contenido gratis con certificado de pago, de pago y pendientes. Cursos, badges y certificaciones profesionales tienen alcances distintos. No se contrata ni inscribe a ningún curso.'}),
      tabla([{t:'Área',f:r=>r.area || 'Por clasificar'},{t:'Programa',f:r=>link(r.nombre,r.url)},{t:'Referencia',f:r=>r.imagen},{t:'Verificación y límites',f:r=>r.estado}],d.certificaciones,{caption:'Acceso al contenido y certificado son condiciones distintas'}),
      h('h2', {texto:'Captura de cotizaciones: referencia local'}),
      c ? h('div', {}, h('p', {clase:'aviso-caja', texto:c.nota+' Fecha, moneda y mercado no confirmados. No se usa para valorar la cartera.'}),
        tabla([{t:'Símbolo visible',f:r=>r.simbolo},{t:'Número de la captura (sin moneda confirmada)',f:r=>num(r.precio_captura),num:true}],c.filas,{caption:'Referencia aportada por el usuario; no son precios actuales ni posiciones confirmadas'}))
        : h('p',{texto:'No hay captura local de cotizaciones; no se incorporaron números sin fecha a la base de precios.'}));
  } catch(e) { limpiar('aprendizaje-contenido',errorCaja(e)); }
}

function pintarMicroestructura(d) {
  const F=d.footprint, H=d.liquidez_historica;
  const vista=h('div'), hist=h('div');
  const modo=selectorSimple('bidask',[['bidask','Bid × Ask ejecutado'],['volumen','Volumen'],['delta','Delta']], valor=>dibujar(valor),'Lectura del footprint');
  function dibujar(valor) {
    const columnas=[{t:'Inicio UTC',f:r=>horaCdmx(r.inicio)},{t:'Fuente / feed',f:r=>`${r.fuente} / ${r.feed}`},{t:'Precio',f:r=>num(r.precio),num:true}];
    if(valor==='bidask') columnas.push({t:'Bid · ventas agresoras',f:r=>num(r.bid),num:true},{t:'Ask · compras agresoras',f:r=>num(r.ask),num:true});
    else columnas.push({t:valor==='delta'?'Delta':'Volumen',f:r=>num(r[valor]),num:true});
    vista.replaceChildren(tabla(columnas,F.celdas,{caption:'Footprint por precio e intervalos de 5 minutos',vacio:'Sin operaciones guardadas para construir footprint.'}));
    const campo=valor==='delta'?'delta':'volumen', valores=F.barras.map(b=>b[campo]).filter(x=>x!=null);
    const max=Math.max(1,...valores.map(Math.abs)), ancho=740, alto=140, paso=700/Math.max(1,F.barras.length);
    const svg=s('svg',{viewBox:`0 0 ${ancho} ${alto}`,class:'grafica',role:'img','aria-label':`Histograma de ${campo} por intervalo guardado`});
    svg.append(s('line',{x1:20,x2:720,y1:70,y2:70,stroke:'var(--borde)'}));
    F.barras.forEach((b,i)=>{const v=b[campo];if(v==null)return;const altura=Math.abs(v)/max*60;
      svg.append(s('rect',{x:20+i*paso,y:v>=0?70-altura:70,width:Math.max(.5,paso-2),height:altura,fill:v>=0?'var(--serie-2)':'var(--vencido)'},
        s('title',{},`${b.inicio} · ${b.fuente}/${b.feed}: ${campo} ${num(v)}`)));});
    hist.replaceChildren(F.barras.length?svg:h('p',{texto:'Sin intervalos para el histograma.'}),
      tabla([{t:'Intervalo',f:r=>horaCdmx(r.inicio)},{t:'Fuente',f:r=>r.fuente},{t:'Volumen',f:r=>num(r.volumen),num:true},
        {t:'Delta',f:r=>num(r.delta),num:true},{t:'Delta %',f:r=>r.delta_pct==null?'—':`${num(r.delta_pct)} %`,num:true}],F.barras,{caption:'Estadísticas por intervalo; delta nulo cuando falta agresor'}));
  }
  dibujar('bidask');
  const tiempos=H.instantes.slice(-20), porCelda=new Map(H.celdas.map(c=>[`${c.precio}|${c.instante}`,c]));
  const maxL=Math.max(1,...H.celdas.map(c=>c.tamano));
  const mapa=tabla([{t:'Precio',f:p=>num(p),num:true},...tiempos.map(t=>({t:horaCdmx(t),num:true,f:p=>{
    const c=porCelda.get(`${p}|${t}`);if(!c)return '—';
    const el=h('span',{texto:`${c.lado} ${num(c.tamano)}`});
    el.style.backgroundColor=`color-mix(in srgb, var(--serie-2) ${Math.round(10+65*c.tamano/maxL)}%, transparent)`;return el;
  }}))],H.precios,{caption:'Heatmap de liquidez pasiva: últimas 20 capturas; — significa no observado',vacio:'Sin capturas de profundidad guardadas. IEX de un nivel no equivale a Level 2 completo.'});
  return h('section',{},h('h2',{texto:'Footprint, volumen y delta'}),modo,vista,hist,h('p',{clase:'ayuda',texto:F.nota+(F.parcial?' Cobertura parcial por límites de la consulta.':'')}),
    h('h2',{texto:'Historial de liquidez visible (DOM)'}),mapa,h('p',{clase:'ayuda',texto:H.nota}),
    h('p',{},h('button',{type:'button',clase:'boton boton--texto','data-ir':'tab-aprendizaje',texto:'Ver conceptos y recursos de las capturas'})));
}
CARGAS['tab-aprendizaje']=cargarAprendizaje;
Object.assign(ATAJOS,{APRENDER:'tab-aprendizaje'});
