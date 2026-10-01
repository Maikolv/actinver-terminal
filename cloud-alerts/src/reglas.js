// Reglas del monitor (funciones puras). No inventan señales: si faltan precios fiables, tipo de cambio, cartera
// reciente o un plan validado, la alerta correspondiente se suspende y se explica el motivo.
import { fechaLocal, horaLocal } from "./calendario.js";
import { factorSplit, gradoIex, posibleSplit, referenciaSic } from "./precios.js";

const MXN = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 2 });
const PCT = (x) => `${x >= 0 ? "+" : ""}${(x * 100).toFixed(1)} %`;
const horas = (a, b) => (a - b) / 3600000;
const FX_MAX_DIAS = 4;
export const FALLOS_PERSISTENTES = 3;   // 3 ejecuciones seguidas (≈45 min con el disparador de 15 min)

export function fxUtil(fxBanxico, fxSync, ahora) {
  const hoy = fechaLocal(ahora);
  const dias = (f) => (Date.parse(hoy) - Date.parse(f.fecha)) / 86400000;
  for (const f of [fxBanxico, fxSync]) if (f && dias(f) <= FX_MAX_DIAS) return f;
  return null;
}

/** Precio vivo de una posición o una opción con su etiqueta, ajustado por splits; o el motivo de que no lo haya. */
export function precioVivo(item, ctx) {
  const { precios, fx, ahora, mercados, carga } = ctx;
  if (!item.simbolo_eeuu) return { motivo: "sin fuente intradía en la nube (BMV o fondo): se usa el último cierre sincronizado" };
  const q = precios[item.simbolo_eeuu];
  if (!q) return { motivo: "sin dato de Alpaca" };
  const g = gradoIex(q.hora, ahora, mercados.XNYS.sesion);
  if (g.grado === "vencido") return { motivo: g.etiqueta };
  const fechaTrade = String(q.hora).slice(0, 10);
  const splits = carga?.splits || [];
  const fPrev = q.fecha_previa ? factorSplit(splits, item.id, q.fecha_previa, fechaTrade) : 1;
  const previo = q.cierre_previo ? q.cierre_previo / fPrev : null;
  const razon = previo ? q.precio / previo : null;
  const dudoso = razon && fPrev === 1 && Math.abs(razon - 1) > 0.3 ? posibleSplit(razon) : null;
  const ref = referenciaSic(q.precio, fx);
  const fTitulos = item.fecha_precio ? factorSplit(splits, item.id, item.fecha_precio, fechaTrade) : 1;
  return { precio_usd: q.precio, hora: q.hora, grado: g.grado, etiqueta: g.etiqueta, cambio: razon ? razon - 1 : null,
    split_dudoso: dudoso, ref, factor_titulos: fTitulos, split_aplicado: fPrev !== 1 };
}

export function evaluar(ctx) {
  const { ahora, carga, syncEn, proveedores = {}, mercados } = ctx;
  const avisos = [], suspendidas = [], hoy = fechaLocal(ahora);
  const sus = (alerta, motivo) => suspendidas.push({ alerta, motivo });
  if (!carga) {
    sus("Todas", "Aún no hay datos sincronizados desde la terminal local.");
    return { avisos, suspendidas, relevo: "sin_datos", resumen: null };
  }
  const u = carga.umbrales;
  const localActivo = syncEn && (ahora - syncEn) / 60000 < u.local_inactivo_min;
  const syncVencida = !syncEn || horas(ahora, syncEn) > u.sync_max_horas;
  const c = carga.cartera;
  const edadConc = c.hora_conciliacion ? horas(ahora, new Date(c.hora_conciliacion)) : null;
  const conciliada = c.fuente === "portal" && edadConc !== null && edadConc <= u.conciliacion_max_horas;
  const ctx2 = { ...ctx, fx: ctx.fx };

  // 1) Cartera sin sincronizar: un aviso por episodio (la clave es la hora de la última sincronización)
  const diaHabil = Boolean(mercados.XMEX.sesion || mercados.XNYS.sesion);
  if (syncVencida && diaHabil) {   // en días inhábiles no se avisa: se espera a la siguiente sesión
    avisos.push({ clave: `sync_vencida:${syncEn ? syncEn.toISOString() : "nunca"}`, tipo: "sync",
      texto: `⚠️ La terminal no sincroniza desde ${syncEn ? horaLocal(syncEn) : "nunca"} (más de ${u.sync_max_horas} h). `
        + "Se suspenden las recomendaciones de compra o venta basadas en ese saldo hasta una nueva sincronización." });
  }
  if (syncVencida) {
    sus("Compra/venta y variación de la cartera", `última sincronización hace ${syncEn ? horas(ahora, syncEn).toFixed(0) : "∞"} h`);
  }
  if (!conciliada) {
    sus("Condiciones del plan (comprar o vender)", c.fuente !== "portal"
      ? "la cartera es el registro local, no una captura del portal"
      : `la copia del portal es de ${horaLocal(new Date(c.hora_conciliacion))} (más de ${u.conciliacion_max_horas} h)`);
  }
  if (!ctx.fx) sus("Referencias SIC y variación de la cartera", "sin tipo de cambio fiable (FIX de Banxico de los últimos 4 días)");

  // 2) Fallas persistentes de proveedores y de la sincronización
  for (const [nombre, p] of Object.entries(proveedores)) {
    if (p.fallos >= FALLOS_PERSISTENTES) {
      avisos.push({ clave: `datos:${nombre}:${p.desde}`, tipo: "datos",
        texto: `⚠️ ${nombre === "alpaca" ? "Alpaca (IEX)" : "Banxico (FIX)"} falla desde ${horaLocal(new Date(p.desde))} `
          + `(${p.fallos} intentos, último: ${p.estado}). No se emiten señales con esos datos.` });
      sus(nombre === "alpaca" ? "Movimientos SIC" : "Tipo de cambio", `${nombre} sin respuesta válida desde ${horaLocal(new Date(p.desde))}`);
    }
  }

  // 3) Movimientos por posición (solo con el mercado de EE. UU. abierto y datos IEX)
  let estimado = (c.efectivo || 0) + (c.por_liquidar || 0), base = estimado, cubierto = true, sinFuente = [];
  for (const p of c.posiciones) {
    const ref = p.precio_ref != null ? p.titulos * p.precio_ref : null;
    if (ref != null) base += ref;
    const v = precioVivo(p, ctx2);
    if (v.motivo) {
      if (!p.simbolo_eeuu) sinFuente.push(p.clave || p.id);
      if (ref != null) estimado += ref; else cubierto = false;
      continue;
    }
    if (v.split_dudoso) {
      avisos.push({ clave: `split_dudoso:${p.id}:${hoy}`, tipo: "datos",
        texto: `⚠️ ${p.clave || p.id}: el precio cambió como en un split (≈ ${v.split_dudoso}:1) sin split registrado. `
          + "Posible split o error de datos: no se emite señal hasta confirmarlo en la terminal." });
      if (ref != null) estimado += ref;
      continue;
    }
    if (v.ref) estimado += p.titulos * v.factor_titulos * v.ref.precio_mxn; else if (ref != null) estimado += ref;
    const abierto = v.grado === "iex_vivo" || v.grado === "iex_retrasado";
    if (abierto && v.cambio !== null && Math.abs(v.cambio) >= u.movimiento_pct) {
      const nivel = Math.floor(Math.abs(v.cambio) / u.movimiento_pct);
      avisos.push({ clave: `mov:${p.id}:${hoy}:${v.cambio > 0 ? "+" : "-"}${nivel}`, tipo: "movimiento",
        texto: `${v.cambio > 0 ? "📈" : "📉"} ${p.clave || p.id} ${PCT(v.cambio)} frente al cierre previo en EE. UU. `
          + `(${v.precio_usd.toFixed(2)} USD, ${v.etiqueta}, ${horaLocal(new Date(v.hora))} CDMX)`
          + (v.ref ? `; ${v.ref.etiqueta}: ${MXN.format(v.ref.precio_mxn)}` : "; sin tipo de cambio para la referencia en pesos")
          + (v.split_aplicado ? " · cierre previo ajustado por split" : "") + "." });
    }
  }
  if (sinFuente.length) sus("Movimientos BMV y fondos", `sin fuente intradía en la nube (${sinFuente.slice(0, 6).join(", ")}): último cierre sincronizado`);

  // 4) Variación estimada de la cartera frente a la copia sincronizada
  if (!syncVencida && conciliada && ctx.fx && cubierto && base > 0) {
    const chg = estimado / base - 1;
    if (Math.abs(chg) >= u.cartera_pct) {
      const nivel = Math.floor(Math.abs(chg) / u.cartera_pct);
      avisos.push({ clave: `cartera:${hoy}:${chg > 0 ? "+" : "-"}${nivel}`, tipo: "cartera",
        texto: `💼 Valor estimado de la cartera ${PCT(chg)} frente a la copia sincronizada (${MXN.format(estimado)} estimado). `
          + "Estimación con referencias SIC (EE. UU. × FIX) y cierres BMV; el saldo oficial es el del portal." });
    }
  }

  // 5) Condiciones del plan validado
  const plan = carga.plan;
  const edadPlan = plan ? horas(ahora, new Date(plan.calculado_en)) : null;
  const planUtil = plan && plan.vigente && plan.validado && edadPlan <= 30;
  if (!plan) sus("Condiciones del plan", "no hay un plan aprobado sincronizado");
  else if (!planUtil) {
    sus("Condiciones del plan", !plan.vigente || edadPlan > 30 ? `el plan se calculó ${horaLocal(new Date(plan.calculado_en))}: ya no es vigente`
      : `el plan no está validado${plan.motivo_no_validado ? `: ${plan.motivo_no_validado}` : ""}`);
  }
  if (planUtil && conciliada && !syncVencida) {
    for (const o of plan.opciones) {
      if (o.limite_compra == null && o.limite_venta == null) continue;
      const v = precioVivo(o, ctx2);
      if (v.motivo || !v.ref || v.split_dudoso || !(v.grado === "iex_vivo" || v.grado === "iex_retrasado")) continue;
      const px = v.ref.precio_mxn;
      const lado = o.limite_compra != null && px <= o.limite_compra ? "compra" : o.limite_venta != null && px >= o.limite_venta ? "venta" : null;
      if (!lado) continue;
      avisos.push({ clave: `plan:${plan.calculado_en}:${o.id}:${lado}`, tipo: "plan",
        texto: `🎯 ${o.clave || o.id}: se cumple la condición de ${lado} del plan «${plan.nombre}» `
          + `(${v.ref.etiqueta}: ${MXN.format(px)}; límite ${MXN.format(lado === "compra" ? o.limite_compra : o.limite_venta)}). `
          + "Verifique el precio en el portal antes de capturar: la referencia no es una cotización del SIC." });
    }
  }

  // 6) Aviso de prueba solicitado por la terminal (comprueba el envío desde la nube)
  if (carga.prueba) {
    avisos.push({ clave: `prueba:${carga.secuencia}`, tipo: "prueba",
      texto: `✅ Aviso de prueba enviado por el monitor en la nube (Cloudflare Workers) a las ${horaLocal(ahora)} CDMX. `
        + `La terminal local no sincroniza desde ${syncEn ? horaLocal(syncEn) : "—"}: este mensaje no salió de su PC.` });
  }

  // 7) Resumen diario: antes de la apertura de la BMV, una vez por sesión
  let resumen = null;
  const bmv = mercados.XMEX.sesion;
  if (bmv && ahora >= new Date(bmv.apertura.getTime() - 35 * 60000) && ahora < bmv.cierre) {
    resumen = { clave: `resumen:${hoy}`, tipo: "resumen", texto: textoResumen(ctx2, { localActivo, syncVencida, conciliada, planUtil, suspendidas }) };
  }

  // Relevo: con la terminal local activa, ella envía sus alertas; la nube solo registra y no repite
  if (localActivo) sus("Avisos de la nube", "en pausa: la terminal local está activa y envía sus propias alertas");
  return { avisos, suspendidas, relevo: localActivo ? "local" : "nube", resumen };
}

export function textoResumen(ctx, { localActivo, syncVencida, conciliada, planUtil, suspendidas }) {
  const { ahora, carga, syncEn, fx, proveedores = {} } = ctx;
  const c = carga.cartera, out = [];
  out.push(`☁️ Resumen diario del monitor en la nube — ${fechaLocal(ahora)} (CDMX)`);
  out.push(localActivo ? "Terminal local: activa." : `Terminal local: sin sincronizar desde ${syncEn ? horaLocal(syncEn) : "—"}; la nube toma el relevo.`);
  out.push(c.fuente === "portal" && c.hora_conciliacion
    ? `Cartera: copia del portal de ${horaLocal(new Date(c.hora_conciliacion))} — NO es el saldo actual del simulador${conciliada ? "" : " (copia antigua)"}.`
    : "Cartera: registro local, NO conciliado con el portal.");
  out.push(`Efectivo ${MXN.format(c.efectivo)} · por liquidar ${MXN.format(c.por_liquidar)} · valor total en la copia ${MXN.format(c.valor_total)}`);
  for (const p of c.posiciones.slice(0, 12)) {
    const v = precioVivo(p, ctx);
    const precio = !v.motivo && v.ref && !v.split_dudoso
      ? `${MXN.format(v.ref.precio_mxn)} (${v.precio_usd.toFixed(2)} USD, ${v.etiqueta}; referencia SIC, no precio del SIC)`
      : p.precio_ref != null ? `${MXN.format(p.precio_ref)} (${p.fuente_precio || "fuente s/d"}, ${p.fecha_precio || "fecha s/d"})` : "sin precio";
    out.push(`• ${p.clave || p.id}: ${p.titulos} títulos — ${precio}`);
  }
  const plan = carga.plan;
  if (plan) {
    out.push("");
    out.push(`Plan «${plan.nombre}» — puntuación ${plan.puntuacion.toFixed(1)}, calculado ${horaLocal(new Date(plan.calculado_en))}`
      + (planUtil && conciliada && !syncVencida ? "" : " — SUSPENDIDO para comprar o vender (ver abajo)"));
    for (const o of plan.opciones.slice(0, 8)) {
      const v = precioVivo(o, ctx);
      const ref = !v.motivo && v.ref ? `${MXN.format(v.ref.precio_mxn)} (referencia SIC ${horaLocal(new Date(v.hora))})`
        : o.precio_ref != null ? `${MXN.format(o.precio_ref)} (${o.fuente_precio || "s/d"}, ${o.fecha_precio || "s/d"})` : "sin precio";
      out.push(`• ${o.accion.toUpperCase()} ${o.clave || o.id}${o.titulos ? ` ${o.titulos} títulos` : ""} — ref. ${ref}. ${o.condicion}`);
    }
    if (plan.alternativas.length) out.push(`Otras opciones de mayor puntuación: ${plan.alternativas.map((a) => `«${a.nombre}» ${a.puntuacion.toFixed(1)}`).join(" · ")}`);
  }
  out.push("");
  const datos = [];
  datos.push(fx ? `FIX Banxico ${fx.valor.toFixed(4)} del ${fx.fecha}` : "sin tipo de cambio fiable");
  for (const [n, p] of Object.entries(proveedores)) if (p.fallos) datos.push(`${n}: ${p.fallos} fallos seguidos`);
  datos.push("BMV y fondos: último cierre sincronizado (sin fuente intradía en la nube)");
  out.push(`Datos: ${datos.join(" · ")}`);
  const otras = suspendidas.filter((s) => s.alerta !== "Avisos de la nube");
  if (otras.length) out.push("Suspendidas: " + otras.map((s) => `${s.alerta} (${s.motivo})`).join("; "));
  out.push("Solo informativo: no se envían órdenes; cada orden se captura a mano en el simulador.");
  return out.join("\n");
}
