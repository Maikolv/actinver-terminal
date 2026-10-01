// Ejecución programada: lee el último estado sincronizado, consulta lo mínimo (Alpaca 1 petición, Banxico ≤ 1 por hora,
// y solo si la nube tiene el relevo y el mercado está en horario), evalúa reglas y envía por Telegram sin duplicar.
import * as alm from "./almacen.js";
import { estadoMercado, proximaRevision } from "./calendario.js";
import { ErrorProveedor, alpacaSnapshots, banxicoFix } from "./precios.js";
import { FALLOS_PERSISTENTES, evaluar, fxUtil } from "./reglas.js";
import { PAUSA_MS, enviar } from "./telegram.js";

const FX_CADA_MIN = 60;
const MAX_SIMBOLOS = 50;

function simbolosDe(carga) {
  const s = new Set();
  for (const p of carga.cartera.posiciones) if (p.simbolo_eeuu) s.add(p.simbolo_eeuu);
  for (const o of carga.plan?.opciones || []) if (o.simbolo_eeuu) s.add(o.simbolo_eeuu);
  return [...s].sort().slice(0, MAX_SIMBOLOS);
}

function registrarFallo(prov, nombre, ahora, estado) {
  const p = prov[nombre] || { fallos: 0 };
  prov[nombre] = { fallos: p.fallos + 1, desde: p.desde || ahora.toISOString(), estado, alertado: p.alertado || false };
}

export async function ejecutar(env, { ahora = new Date(), fetchFn = fetch, dormir } = {}) {
  const db = env.DB;
  const id = await alm.iniciarEjecucion(db, ahora);
  const resultado = { relevo: null, consultas: [], nuevos: 0, enviados: 0, estado_envio: null };
  try {
    const carga = await alm.leer(db, "carga");
    const syncTxt = await alm.leer(db, "sync_en");
    const syncEn = syncTxt ? new Date(syncTxt) : null;
    const cal = carga?.calendario || [];
    const mercados = { XMEX: estadoMercado(cal, "XMEX", ahora), XNYS: estadoMercado(cal, "XNYS", ahora) };
    const prov = (await alm.leer(db, "proveedores")) || {};
    const localActivo = carga && syncEn && (ahora - syncEn) / 60000 < carga.umbrales.local_inactivo_min;
    const nyse = mercados.XNYS.sesion;
    const enHorario = nyse && ahora >= new Date(nyse.apertura - 40 * 60000) && ahora <= new Date(nyse.cierre.getTime() + 20 * 60000);
    const recuperados = [];
    let precios = {};
    if (carga && !localActivo && enHorario) {
      const simbolos = simbolosDe(carga);
      if (simbolos.length) {
        resultado.consultas.push("alpaca");
        try {
          precios = await alpacaSnapshots(simbolos, env, fetchFn);
          if (prov.alpaca?.alertado) recuperados.push(["alpaca", prov.alpaca.desde]);
          prov.alpaca = { fallos: 0 };
        } catch (e) {
          if (!(e instanceof ErrorProveedor)) throw e;
          registrarFallo(prov, "alpaca", ahora, e.estado);
        }
      }
    }
    let fxB = await alm.leer(db, "fx_banxico");
    const fxViejo = !fxB || (ahora - new Date(fxB.consultado_en)) / 60000 >= FX_CADA_MIN;
    if (carga && !localActivo && enHorario && fxViejo) {
      resultado.consultas.push("banxico");
      try {
        fxB = { ...(await banxicoFix(env, fetchFn)), consultado_en: ahora.toISOString() };
        await alm.guardar(db, "fx_banxico", fxB, ahora);
        if (prov.banxico?.alertado) recuperados.push(["banxico", prov.banxico.desde]);
        prov.banxico = { fallos: 0 };
      } catch (e) {
        if (!(e instanceof ErrorProveedor)) throw e;
        registrarFallo(prov, "banxico", ahora, e.estado);
      }
    }
    const fx = fxUtil(fxB, carga?.fx, ahora);
    const ev = evaluar({ ahora, carga, syncEn, precios, fx, proveedores: prov, mercados });
    resultado.relevo = ev.relevo;
    if (ev.relevo === "nube") {
      const nuevos = [...ev.avisos, ...(ev.resumen ? [ev.resumen] : []),
        ...recuperados.map(([n, desde]) => ({ clave: `datos_ok:${n}:${desde}`, tipo: "datos",
          texto: `✅ ${n === "alpaca" ? "Alpaca (IEX)" : "Banxico (FIX)"} vuelve a responder.` }))];
      for (const a of nuevos) if (await alm.registrarAviso(db, a, ahora)) resultado.nuevos++;
      for (const [n, p] of Object.entries(prov)) if (p.fallos >= FALLOS_PERSISTENTES) p.alertado = true;
    }
    await alm.guardar(db, "proveedores", prov, ahora);
    const envio = await despachar(env, db, ahora, { fetchFn, dormir });
    Object.assign(resultado, envio);
    await alm.guardar(db, "ultima_ejecucion", {
      inicio: ahora.toISOString(), relevo: ev.relevo, suspendidas: ev.suspendidas, consultas: resultado.consultas,
      nuevos: resultado.nuevos, enviados: resultado.enviados, estado_envio: resultado.estado_envio,
      fx: fx ? { valor: fx.valor, fecha: fx.fecha, fuente: fx.fuente } : null,
      precios: Object.fromEntries(Object.entries(precios).map(([s, q]) => [s, { hora: q.hora }])),
      proveedores: prov, proxima_revision: proximaRevision(ahora)?.toISOString() ?? null,
    }, ahora);
    await alm.depurar(db, ahora);
  } catch (e) {
    resultado.error = e?.name || "error";
    console.error("ejecución fallida:", resultado.error);  // sin detalles: podrían incluir datos de la cartera
  } finally {
    await alm.cerrarEjecucion(db, id, resultado);
  }
  return resultado;
}

/** Envía la cola: avisos agrupados en un mensaje y el resumen diario aparte; respeta 1 mensaje/s y 429. */
export async function despachar(env, db, ahora, { fetchFn = fetch, dormir } = {}) {
  const cola = await alm.pendientes(db, ahora, 12);
  const grupos = [];
  const alertas = cola.filter((a) => a.tipo !== "resumen");
  if (alertas.length) grupos.push({ claves: alertas.slice(0, 8).map((a) => a.clave),
    texto: ["☁️ Monitor en la nube (Reto Actinver) — solo informativo, no envía órdenes",
      ...alertas.slice(0, 8).map((a) => a.texto)].join("\n\n") });
  for (const r of cola.filter((a) => a.tipo === "resumen")) grupos.push({ claves: [r.clave], texto: r.texto });
  const out = { enviados: 0, estado_envio: grupos.length ? null : "nada_que_enviar" };
  for (let i = 0; i < grupos.length; i++) {
    if (i > 0) await (dormir || ((ms) => new Promise((r) => setTimeout(r, ms))))(PAUSA_MS);
    const g = grupos[i];
    const r = await enviar(env, g.texto, { fetchFn, ...(dormir ? { dormir } : {}) });
    out.estado_envio = r.estado;
    if (r.estado === "enviado") {
      await alm.marcar(db, g.claves, "enviado", ahora);
      out.enviados += g.claves.length;
    } else if (r.estado === "limite") {
      const hasta = new Date(ahora.getTime() + r.retry_after * 1000).toISOString();
      await alm.marcar(db, g.claves, "error", ahora, hasta);
      // Telegram pidió esperar: nada más sale antes de ese momento (el resto queda para la siguiente ejecución)
      for (const resto of grupos.slice(i + 1)) await alm.posponer(db, resto.claves, hasta);
      break;
    } else {
      await alm.marcar(db, g.claves, "error", ahora, new Date(ahora.getTime() + 5 * 60000).toISOString());
    }
  }
  return out;
}
