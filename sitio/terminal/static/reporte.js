/* Resultado para llevar (como en COATL): reporte propio para imprimir o guardar en PDF, con un QR que reabre la
   misma vista. El QR codifica SOLO parámetros del escenario en el fragmento #r= (vista, fecha, modo de venta y si es
   demostración): nunca títulos, montos, pesos ni datos de la cuenta, y nunca en la consulta de la URL. */
"use strict";
(() => {
  const VERSION = 1;
  const codificar = (o) => btoa(unescape(encodeURIComponent(JSON.stringify(o)))).replace(/=+$/, "");
  const decodificar = (t) => JSON.parse(decodeURIComponent(escape(atob(t))));

  // Parámetros permitidos: cualquier otra clave se descarta (defensa ante cambios futuros).
  const PERMITIDOS = ["v", "vista", "fecha", "modo_venta", "demo"];
  function escenario(datos) {
    const o = { v: VERSION, ...datos };
    return Object.fromEntries(Object.entries(o).filter(([k]) => PERMITIDOS.includes(k)));
  }
  function enlace(datos) {
    return `${location.origin}${location.pathname}#r=${codificar(escenario(datos))}`;
  }
  function svgQR(texto) {
    const qr = window.qrcode(0, "M");
    qr.addData(texto);
    qr.make();
    const doc = new DOMParser().parseFromString(qr.createSvgTag({ cellSize: 4, margin: 2, scalable: true }), "image/svg+xml");
    const svg = doc.documentElement;
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Código QR que reabre esta vista");
    return document.importNode(svg, true);
  }
  const el = (tag, clase, texto) => { const e = document.createElement(tag); if (clase) e.className = clase; if (texto != null) e.textContent = texto; return e; };

  // Plan del día: tabla de decisiones (sin montos ni títulos de la cuenta en el QR; en el papel sí, es su reporte).
  function imprimirPlan(plan) {
    const demo = !!document.querySelector(".aviso-demo:not([hidden]), #aviso-demo:not([hidden])") || !!window.HQT_ESTATICA;
    const fecha = (plan.generado_en || new Date().toISOString()).slice(0, 10);
    const url = enlace({ vista: "tab-resumen", fecha, modo_venta: plan.gestion_riesgo?.reglas?.modo_venta, demo });
    const hoja = el("section", "reporte-impreso");
    hoja.setAttribute("aria-label", "Reporte para imprimir");
    const cab = el("header", "reporte-cabecera");
    cab.append(el("h1", null, "Help Quote Terminal · Plan de acción"),
      el("p", null, `Generado ${fecha}${demo ? " · DATOS SIMULADOS (demostración)" : ""} · ${plan.propuesta ? `Objetivo: «${plan.propuesta.nombre}»` : "Sin propuesta vigente"}`));
    const qr = el("figure", "reporte-qr");
    qr.append(svgQR(url), el("figcaption", null, "Escanee para reabrir esta vista"));
    cab.append(qr);
    const t = el("table");
    const thead = el("thead"), tr = el("tr");
    for (const c of ["#", "Instrumento", "Decisión", "Títulos", "Precio límite", "Peso actual → objetivo", "Motivo"]) tr.append(el("th", null, c));
    thead.append(tr);
    const tbody = el("tbody");
    for (const a of plan.acciones || []) {
      const f = el("tr");
      for (const v of [a.prioridad, a.clave, a.decision, a.cantidad ?? "—", a.precio_limite != null ? a.precio_limite.toFixed(2) : "—",
        `${(a.peso_actual * 100).toFixed(1)} % → ${(a.peso_objetivo * 100).toFixed(1)} %`, a.motivo_corto || a.motivo || ""]) f.append(el("td", null, String(v)));
      tbody.append(f);
    }
    t.append(thead, tbody);
    hoja.append(cab, t, el("p", "reporte-aviso", "Solo informa y simula: verifique cada precio con su casa de bolsa y capture usted las órdenes. No es asesoría de inversión."));
    document.body.append(hoja);
    document.documentElement.classList.add("imprimiendo");
    const limpiar = () => { hoja.remove(); document.documentElement.classList.remove("imprimiendo"); window.removeEventListener("afterprint", limpiar); };
    window.addEventListener("afterprint", limpiar);
    window.print();
  }

  // Reapertura desde el QR: #r=… lleva a la vista y avisa de qué escenario viene.
  function reabrir() {
    const m = location.hash.match(/^#r=([A-Za-z0-9+/]+)$/);
    if (!m) return null;
    let datos;
    try { datos = escenario(decodificar(m[1])); } catch { return null; }
    if (datos.v !== VERSION) return null;
    window.HQT_REABIERTO = datos;
    if (datos.vista && /^tab-[a-z]+$/.test(datos.vista)) {
      const tab = document.getElementById(datos.vista);
      if (tab) tab.click();
    }
    const aviso = el("div", "aviso-caja", `Reabierto desde un QR: plan del ${datos.fecha || "—"}${datos.demo ? " (demostración)" : ""}. Las cifras se recalculan con los datos de hoy.`);
    aviso.setAttribute("role", "status");
    document.querySelector("main")?.prepend(aviso);
    return datos;
  }
  window.HQTReporte = { imprimirPlan, enlace, escenario, codificar, decodificar, reabrir };
  // Script diferido: el DOM y los manejadores de app.js ya existen; no se espera a «load» (los widgets lo retrasan).
  reabrir();
})();
