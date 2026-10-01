// Monitor de alertas del Reto Actinver en Cloudflare Workers (plan Free). Solo informa: no coloca órdenes.
//   POST /sync    carga mínima firmada desde la terminal local (HMAC, ventana de 5 min, nonce de un solo uso)
//   GET  /estado  estado del monitor (firmado; sin textos ni montos)
//   cron          */15 12-21 * * 1-5 (UTC): vigila precios y envía avisos por Telegram
import * as alm from "./almacen.js";
import { proximaRevision } from "./calendario.js";
import { verificar } from "./firma.js";
import { ejecutar } from "./monitor.js";
import { MAX_BYTES, validar } from "./validacion.js";

const json = (cuerpo, status = 200) => new Response(JSON.stringify(cuerpo), {
  status, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" },
});

async function autenticar(request, env, ruta, cuerpo, ahora) {
  const h = request.headers;
  return verificar({
    secreto: env.SYNC_SECRET, ts: h.get("X-Marca-Tiempo"), nonce: h.get("X-Nonce"), firma: h.get("X-Firma"),
    metodo: request.method, ruta, cuerpo, ahoraSeg: Math.floor(ahora / 1000),
    nonceUsado: (n, ts) => alm.nonceUsado(env.DB, n, ts),
  });
}

export async function atender(request, env, ahora = new Date()) {
  const url = new URL(request.url);
  if (request.method === "GET" && url.pathname === "/") {
    return new Response("Monitor de alertas del Reto: activo. Sin datos públicos.", { headers: { "Content-Type": "text/plain; charset=utf-8" } });
  }
  if (request.method === "POST" && url.pathname === "/sync") {
    const largo = Number(request.headers.get("Content-Length"));
    if (!Number.isFinite(largo) || largo <= 0) return json({ ok: false, error: "falta Content-Length" }, 411);
    if (largo > MAX_BYTES) return json({ ok: false, error: "carga demasiado grande" }, 413);
    const cuerpo = await request.text();
    if (new TextEncoder().encode(cuerpo).length > MAX_BYTES) return json({ ok: false, error: "carga demasiado grande" }, 413);
    const a = await autenticar(request, env, "/sync", cuerpo, ahora);
    if (!a.ok) return json({ ok: false, error: "no autorizado", motivo: a.motivo }, 401);
    let obj;
    try { obj = JSON.parse(cuerpo); } catch { return json({ ok: false, error: "JSON inválido" }, 400); }
    const v = validar(obj);
    if (!v.ok) return json({ ok: false, error: v.error }, 400);
    const previa = await alm.leer(env.DB, "secuencia");
    if (previa !== null && v.datos.secuencia <= previa) return json({ ok: false, error: "secuencia repetida o anterior" }, 409);
    await alm.guardar(env.DB, "carga", v.datos, ahora);
    await alm.guardar(env.DB, "sync_en", ahora.toISOString(), ahora);
    await alm.guardar(env.DB, "secuencia", v.datos.secuencia, ahora);
    return json({ ok: true, recibido_en: ahora.toISOString(), proxima_revision: proximaRevision(ahora)?.toISOString() ?? null });
  }
  if (request.method === "GET" && url.pathname === "/estado") {
    const a = await autenticar(request, env, "/estado", "", ahora);
    if (!a.ok) return json({ ok: false, error: "no autorizado", motivo: a.motivo }, 401);
    const [ult, sync, sec, avisos] = await Promise.all([alm.leer(env.DB, "ultima_ejecucion"), alm.leer(env.DB, "sync_en"),
      alm.leer(env.DB, "secuencia"), alm.recientes(env.DB, 10)]);
    return json({
      ok: true, monitor: "activo", ahora: ahora.toISOString(), ultima_sincronizacion: sync, secuencia: sec,
      ultima_ejecucion: ult ? { inicio: ult.inicio, relevo: ult.relevo, consultas: ult.consultas, enviados: ult.enviados,
        estado_envio: ult.estado_envio, fx: ult.fx, proveedores: ult.proveedores, precios: ult.precios } : null,
      suspendidas: ult?.suspendidas || [], proxima_revision: proximaRevision(ahora)?.toISOString() ?? null,
      telegram_configurado: Boolean(env.TELEGRAM_BOT_TOKEN && env.TELEGRAM_CHAT_ID),
      fuentes_configuradas: { alpaca: Boolean(env.ALPACA_API_KEY_ID && env.ALPACA_API_SECRET_KEY), banxico: Boolean(env.BANXICO_TOKEN) },
      avisos_recientes: avisos,
    });
  }
  return json({ ok: false, error: "no encontrado" }, 404);
}

export default {
  fetch: (request, env) => atender(request, env),
  scheduled: (controller, env, ctx) => { ctx.waitUntil(ejecutar(env, { ahora: new Date(controller.scheduledTime) })); },
};
