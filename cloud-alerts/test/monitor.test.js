// Ejecución programada: datos vencidos, proveedores caídos, MXN/USD, splits, calendario, duplicados, 429 y relevo.
import assert from "node:assert/strict";
import { test } from "node:test";
import * as alm from "../src/almacen.js";
import { estadoMercado, proximaRevision, sesion, utcDe } from "../src/calendario.js";
import { ejecutar } from "../src/monitor.js";
import { ENV_BASE, alpaca, banxico, carga, d1, fetchFalso } from "./apoyo.js";

const AHORA = new Date("2026-10-01T16:00:00Z");          // 10:00 CDMX, BMV y NYSE abiertas
const nada = async () => {};

async function preparar({ c = carga(), syncEn = new Date(AHORA - 60 * 60000) } = {}) {
  const env = { ...ENV_BASE, DB: d1() };
  if (c) await alm.guardar(env.DB, "carga", c);
  if (syncEn) await alm.guardar(env.DB, "sync_en", syncEn.toISOString());
  return env;
}

function red({ precio = 104, previo = 100, hora = "2026-10-01T15:58:00Z", fechaPrev = "2026-09-30", alpacaStatus = 200, tg = [] } = {}) {
  const respuestasTg = [...tg];
  const f = fetchFalso([
    ["https://data.alpaca.markets/", () => ({ status: alpacaStatus, body: alpacaStatus === 200 ? alpaca(precio, previo, hora, fechaPrev) : {} })],
    ["https://www.banxico.org.mx/", () => ({ body: banxico() })],
    ["https://api.telegram.org/", () => respuestasTg.shift() || { status: 200, body: { ok: true } }],
  ]);
  f.mensajes = () => f.llamadas.filter((l) => l.url.startsWith("https://api.telegram.org/")).map((l) => JSON.parse(l.init.body).text);
  return f;
}

test("movimiento SIC: referencia en pesos = USD × FIX, etiquetada como referencia y no como precio del SIC", async () => {
  const env = await preparar();
  const f = red();
  const r = await ejecutar(env, { ahora: AHORA, fetchFn: f, dormir: nada });
  assert.equal(r.relevo, "nube");
  const [alertas, resumen] = f.mensajes();
  assert.match(alertas, /MU \* \+4\.0 %/);
  assert.match(alertas, /referencia SIC = EE\. UU\. × FIX 18\.0000/);
  assert.match(alertas, /\$1,872\.00/);                       // 104 USD × 18
  assert.match(alertas, /no es precio del SIC/);
  assert.match(alertas, /condición de compra/);                // 1,872 ≤ límite 1,950 del plan validado
  assert.match(resumen, /copia del portal de 01-10 08:45 — NO es el saldo actual/);
  assert.match(resumen, /BMV y fondos: último cierre sincronizado/);
  // Alpaca: una sola petición para todos los símbolos; Banxico una vez
  assert.equal(f.llamadas.filter((l) => l.url.includes("alpaca")).length, 1);
});

test("duplicados: la misma alerta no se repite en ejecuciones siguientes; un nivel nuevo sí", async () => {
  const env = await preparar();
  await ejecutar(env, { ahora: AHORA, fetchFn: red(), dormir: nada });
  const f2 = red();
  await ejecutar(env, { ahora: new Date(AHORA.getTime() + 15 * 60000), fetchFn: f2, dormir: nada });
  assert.equal(f2.mensajes().length, 0);
  const f3 = red({ precio: 107 });                             // +7 % ⇒ nivel 2
  await ejecutar(env, { ahora: new Date(AHORA.getTime() + 30 * 60000), fetchFn: f3, dormir: nada });
  assert.equal(f3.mensajes().length, 1);
  assert.match(f3.mensajes()[0], /\+7\.0 %/);
});

test("cartera sin sincronizar: avisa una vez y suspende compra/venta basadas en ese saldo", async () => {
  const env = await preparar({ syncEn: new Date(AHORA - 30 * 3600000) });
  const f = red();
  await ejecutar(env, { ahora: AHORA, fetchFn: f, dormir: nada });
  const txt = f.mensajes().join("\n");
  assert.match(txt, /no sincroniza desde/);
  assert.match(txt, /Se suspenden las recomendaciones/);
  assert.doesNotMatch(txt, /condición de compra/);
  const ult = await alm.leer(env.DB, "ultima_ejecucion");
  assert.ok(ult.suspendidas.some((s) => /Compra\/venta/.test(s.alerta)));
  const f2 = red();
  await ejecutar(env, { ahora: new Date(AHORA.getTime() + 15 * 60000), fetchFn: f2, dormir: nada });
  assert.ok(!f2.mensajes().some((m) => /no sincroniza/.test(m)));
});

test("copia del portal antigua o registro local: el plan no dispara compras ni ventas", async () => {
  const c = carga();
  c.cartera.hora_conciliacion = "2026-09-28T20:00:00Z";
  const env = await preparar({ c });
  const f = red();
  await ejecutar(env, { ahora: AHORA, fetchFn: f, dormir: nada });
  assert.doesNotMatch(f.mensajes().join("\n"), /condición de compra/);
  assert.match(f.mensajes().join("\n"), /SUSPENDIDO para comprar o vender/);
});

test("precio IEX vencido o sin tipo de cambio: no se inventa la señal", async () => {
  const env = await preparar({ c: carga({ fx: null }) });
  const f = fetchFalso([
    ["https://data.alpaca.markets/", () => ({ body: alpaca(104, 100, "2026-09-20T15:00:00Z") })],
    ["https://www.banxico.org.mx/", () => ({ status: 503 })],
    ["https://api.telegram.org/", () => ({ status: 200, body: { ok: true } })],
  ]);
  await ejecutar(env, { ahora: AHORA, fetchFn: f, dormir: nada });
  const txt = f.llamadas.filter((l) => l.url.includes("telegram")).map((l) => JSON.parse(l.init.body).text).join("\n");
  assert.doesNotMatch(txt, /📈|📉/);
  const ult = await alm.leer(env.DB, "ultima_ejecucion");
  assert.ok(ult.suspendidas.some((s) => /sin tipo de cambio fiable/.test(s.motivo)));
});

test("caída de un proveedor: un aviso tras 3 fallos seguidos, sin repetir, y aviso de recuperación", async () => {
  const env = await preparar();
  const msgs = [];
  for (let i = 0; i < 5; i++) {
    const f = red({ alpacaStatus: 500 });
    await ejecutar(env, { ahora: new Date(AHORA.getTime() + i * 15 * 60000), fetchFn: f, dormir: nada });
    msgs.push(...f.mensajes());
  }
  assert.equal(msgs.filter((m) => /Alpaca \(IEX\) falla desde/.test(m)).length, 1);
  const ok = red();
  await ejecutar(env, { ahora: new Date(AHORA.getTime() + 5 * 15 * 60000), fetchFn: ok, dormir: nada });
  assert.ok(ok.mensajes().some((m) => /vuelve a responder/.test(m)));
});

test("splits: con split registrado se ajusta el cierre previo; sin registrar se marca como dudoso", async () => {
  const conSplit = carga({ splits: [{ id: "SIC:MU", fecha: "2026-10-01", factor: 4 }] });
  const env = await preparar({ c: conSplit });
  const f = red({ precio: 25.5, previo: 100 });               // 4:1 ⇒ previo ajustado 25 ⇒ +2 % (sin alerta)
  await ejecutar(env, { ahora: AHORA, fetchFn: f, dormir: nada });
  assert.ok(!f.mensajes().some((m) => /📈|📉|split/.test(m)));
  const env2 = await preparar();
  const f2 = red({ precio: 25.5, previo: 100 });
  await ejecutar(env2, { ahora: AHORA, fetchFn: f2, dormir: nada });
  const txt = f2.mensajes().join("\n");
  assert.match(txt, /Posible split o error de datos/);
  assert.doesNotMatch(txt, /📉/);
});

test("Telegram 429: espera corta ⇒ reintento; espera larga ⇒ queda en cola y sale en la siguiente ejecución", async () => {
  const env = await preparar();
  const corto = red({ tg: [{ status: 429, body: { ok: false, parameters: { retry_after: 1 } } }] });
  const esperas = [];
  await ejecutar(env, { ahora: AHORA, fetchFn: corto, dormir: async (ms) => { esperas.push(ms); } });
  assert.ok(esperas.includes(1000));
  assert.equal((await alm.pendientes(env.DB, AHORA)).length, 0);

  const env2 = await preparar();
  const largo = red({ tg: [{ status: 429, body: { ok: false, parameters: { retry_after: 120 } } }] });
  const r = await ejecutar(env2, { ahora: AHORA, fetchFn: largo, dormir: nada });
  assert.equal(r.estado_envio, "limite");
  assert.equal((await alm.pendientes(env2.DB, AHORA)).length, 0);              // aún no toca
  const despues = new Date(AHORA.getTime() + 15 * 60000);
  assert.ok((await alm.pendientes(env2.DB, despues)).length > 0);
  const f3 = red();
  await ejecutar(env2, { ahora: despues, fetchFn: f3, dormir: nada });
  assert.ok(f3.mensajes().some((m) => /\+4\.0 %/.test(m)));
});

test("convivencia: con la terminal local activa la nube no consulta ni envía (relevo)", async () => {
  const env = await preparar({ syncEn: new Date(AHORA - 5 * 60000) });
  const f = red();
  const r = await ejecutar(env, { ahora: AHORA, fetchFn: f, dormir: nada });
  assert.equal(r.relevo, "local");
  assert.equal(f.llamadas.length, 0);
  const ult = await alm.leer(env.DB, "ultima_ejecucion");
  assert.ok(ult.suspendidas.some((s) => /terminal local está activa/.test(s.motivo)));
  // 25 min sin sincronizar ⇒ la nube toma el relevo
  const f2 = red();
  assert.equal((await ejecutar(env, { ahora: new Date(AHORA.getTime() + 25 * 60000), fetchFn: f2, dormir: nada })).relevo, "nube");
  assert.ok(f2.mensajes().length > 0);
});

test("aviso de prueba: solo sale de la nube cuando la terminal local dejó de sincronizar", async () => {
  const env = await preparar({ c: carga({ prueba: true, umbrales: { local_inactivo_min: 5 } }), syncEn: new Date(AHORA - 6 * 60000) });
  const f = red();
  await ejecutar(env, { ahora: AHORA, fetchFn: f, dormir: nada });
  assert.ok(f.mensajes().some((m) => /Aviso de prueba enviado por el monitor en la nube/.test(m)));
});

test("fin de semana y festivos: sin consultas; horario de EE. UU. con y sin horario de verano", async () => {
  const env = await preparar({ c: carga({ calendario: [] }) });
  const sabado = new Date("2026-10-03T16:00:00Z");
  const f = red();
  await ejecutar(env, { ahora: sabado, fetchFn: f, dormir: nada });
  assert.equal(f.llamadas.length, 0);
  assert.equal(sesion([], "XMEX", "2026-11-02"), null);                    // Día de Muertos: BMV cerrada
  assert.ok(sesion([], "XNYS", "2026-11-02"));                             // NYSE sí abre
  assert.equal(sesion([], "XNYS", "2026-10-30").apertura.toISOString(), "2026-10-30T13:30:00.000Z");   // EDT
  assert.equal(sesion([], "XNYS", "2026-11-02").apertura.toISOString(), "2026-11-02T14:30:00.000Z");   // EST
  assert.equal(sesion([], "XNYS", "2026-11-26"), null);                    // Acción de Gracias
  assert.equal(utcDe("2026-11-03", "08:30", "America/Mexico_City").toISOString(), "2026-11-03T14:30:00.000Z");
  // El calendario sincronizado manda sobre el supuesto (p. ej. un cierre anticipado)
  const cal = [{ mercado: "XNYS", fecha: "2026-11-27", apertura: "2026-11-27T14:30:00Z", cierre: "2026-11-27T18:00:00Z" }];
  assert.equal(estadoMercado(cal, "XNYS", new Date("2026-11-27T19:00:00Z")).abierto, false);
  assert.equal(proximaRevision(new Date("2026-10-02T21:50:00Z")).toISOString(), "2026-10-05T12:00:00.000Z");
});

test("resumen diario: una vez por sesión, desde 35 min antes de la apertura de la BMV", async () => {
  const env = await preparar({ syncEn: new Date("2026-10-01T11:00:00Z") });
  const temprano = red();
  await ejecutar(env, { ahora: new Date("2026-10-01T12:45:00Z"), fetchFn: temprano, dormir: nada });
  assert.ok(!temprano.mensajes().some((m) => /Resumen diario/.test(m)));
  const f = red();
  await ejecutar(env, { ahora: new Date("2026-10-01T13:00:00Z"), fetchFn: f, dormir: nada });
  const resumen = f.mensajes().find((m) => /Resumen diario/.test(m));
  assert.ok(resumen);
  assert.match(resumen, /Plan «Acciones · Máxima puntuación» — puntuación 87\.4/);
  assert.match(resumen, /COMPRAR MU \* 5 títulos/);
  assert.match(resumen, /Comprar si la referencia baja/);
  assert.match(resumen, /Mixta · Máxima puntuación» 84\.3/);
  const f2 = red();
  await ejecutar(env, { ahora: new Date("2026-10-01T13:15:00Z"), fetchFn: f2, dormir: nada });
  assert.ok(!f2.mensajes().some((m) => /Resumen diario/.test(m)));
});
