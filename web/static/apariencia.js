/* Apariencia y asistente de estética: tema, tamaño de letra, densidad y movimiento. Preferencias solo en este navegador.
   El asistente sugiere ajustes según la pantalla y la hora, y las preguntas libres van al asistente de la terminal. */
"use strict";
(() => {
  const CLAVE = "apariencia";
  const BASE = { tema: "sistema", letra: 100, densidad: "compacta", movimiento: "sistema" };
  const leer = () => { try { return { ...BASE, ...JSON.parse(localStorage.getItem(CLAVE) || "{}") }; } catch { return { ...BASE }; } };
  const guardar = (p) => { try { localStorage.setItem(CLAVE, JSON.stringify(p)); } catch { /* sin almacenamiento */ } };

  function aplicar(p) {
    const r = document.documentElement;
    if (p.tema === "sistema") r.removeAttribute("data-theme"); else r.setAttribute("data-theme", p.tema);
    r.style.fontSize = p.letra === 100 ? "" : `${p.letra}%`;
    r.dataset.densidad = p.densidad;
    r.dataset.movimiento = p.movimiento;
  }
  aplicar(leer());

  // Sugerencias del asistente: reglas simples y explicadas, sin enviar nada fuera del equipo.
  function sugerencias(p) {
    const s = [];
    const oscuroSistema = matchMedia("(prefers-color-scheme: dark)").matches;
    const hora = new Date().getHours();
    if ((hora >= 19 || hora < 7) && p.tema !== "dark" && !(p.tema === "sistema" && oscuroSistema))
      s.push(["Es de noche: el tema oscuro cansa menos la vista.", { tema: "dark" }]);
    if (hora >= 8 && hora < 18 && p.tema === "dark")
      s.push(["De día con mucha luz ambiente, el tema claro se lee mejor.", { tema: "light" }]);
    if (innerWidth < 720 && p.densidad === "compacta")
      s.push(["En pantalla chica, la densidad cómoda da filas más fáciles de tocar.", { densidad: "comoda" }]);
    if (innerWidth >= 1600 && p.letra < 110)
      s.push(["Pantalla grande: subir la letra a 110 % mejora la lectura a distancia (útil en un stand).", { letra: 110 }]);
    if (matchMedia("(prefers-contrast: more)").matches && p.letra < 110)
      s.push(["Su sistema pide más contraste: letra más grande ayuda.", { letra: 110 }]);
    return s;
  }

  function control(etiqueta, clave, opciones, p, pintar) {
    const g = document.createElement("fieldset");
    g.className = "apariencia-grupo";
    const l = document.createElement("legend"); l.textContent = etiqueta; g.append(l);
    for (const [valor, texto] of opciones) {
      const b = document.createElement("button");
      b.type = "button"; b.className = "boton boton--secundario"; b.textContent = texto;
      b.setAttribute("aria-pressed", String(p[clave] === valor));
      b.onclick = () => { const n = { ...leer(), [clave]: valor }; guardar(n); aplicar(n); pintar(); };
      g.append(b);
    }
    return g;
  }

  function pintar() {
    const cont = document.getElementById("apariencia");
    if (!cont) return;
    const p = leer();
    cont.replaceChildren(
      control("Tema", "tema", [["sistema", "Como el sistema"], ["dark", "Oscuro"], ["light", "Claro"]], p, pintar),
      control("Tamaño de letra", "letra", [[90, "90 %"], [100, "100 %"], [110, "110 %"], [125, "125 %"]], p, pintar),
      control("Densidad", "densidad", [["compacta", "Compacta"], ["comoda", "Cómoda"]], p, pintar),
      control("Movimiento", "movimiento", [["sistema", "Como el sistema"], ["reducido", "Reducido"]], p, pintar));
    const caja = document.createElement("section");
    caja.className = "tarjeta"; caja.setAttribute("aria-label", "Asistente de estética");
    const h = document.createElement("h2"); h.textContent = "Asistente de estética"; caja.append(h);
    const lista = sugerencias(p);
    if (!lista.length) {
      const ok = document.createElement("p"); ok.className = "suave";
      ok.textContent = "Su configuración ya es adecuada para esta pantalla y esta hora."; caja.append(ok);
    }
    for (const [texto, cambio] of lista) {
      const fila = document.createElement("p");
      const b = document.createElement("button");
      b.type = "button"; b.className = "boton boton--texto"; b.textContent = "Aplicar";
      b.onclick = () => { const n = { ...leer(), ...cambio }; guardar(n); aplicar(n); pintar(); };
      fila.append(`${texto} `, b); caja.append(fila);
    }
    const form = document.createElement("form");
    form.className = "fila-controles";
    const inp = document.createElement("input");
    inp.type = "text"; inp.placeholder = "Pregunte, p. ej. «¿qué tema conviene para presentar en un proyector?»";
    inp.setAttribute("aria-label", "Pregunta al asistente de estética"); inp.style.flex = "1";
    const env = document.createElement("button"); env.type = "submit"; env.className = "boton"; env.textContent = "Preguntar";
    const resp = document.createElement("p"); resp.className = "suave"; resp.setAttribute("aria-live", "polite");
    form.append(inp, env);
    form.onsubmit = async (e) => {
      e.preventDefault();
      if (!inp.value.trim()) return;
      resp.textContent = "Pensando…";
      try {
        const csrf = document.querySelector('meta[name="csrf"]').content;
        const r = await fetch("/api/asistente", { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
          body: JSON.stringify({ texto: `Sobre la apariencia y legibilidad de la terminal (tema, letra, densidad, contraste): ${inp.value.trim()}` }) });
        const d = await r.json();
        resp.textContent = d.respuesta || d.texto || d.detail || "Sin respuesta.";
      } catch { resp.textContent = "No hay conexión con el servidor local."; }
    };
    const restaurar = document.createElement("button");
    restaurar.type = "button"; restaurar.className = "boton boton--texto"; restaurar.textContent = "Restaurar apariencia";
    restaurar.onclick = () => { guardar(BASE); aplicar(BASE); pintar(); };
    caja.append(form, resp, restaurar);
    cont.append(caja);
  }
  document.addEventListener("click", (e) => { if (e.target.closest?.("#tab-apariencia")) setTimeout(pintar, 0); });
  if (document.readyState !== "loading") pintar(); else document.addEventListener("DOMContentLoaded", pintar);
})();
