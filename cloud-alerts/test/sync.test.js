// Sincronización: firma, reenvíos, ventana de tiempo, tamaño, validación estricta y secuencia.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { firmar, sha256Hex, canonico, hmacHex } from "../src/firma.js";
import { atender } from "../src/index.js";
import { MAX_BYTES } from "../src/validacion.js";
import { ENV_BASE, carga, d1 } from "./apoyo.js";

const AHORA = new Date("2026-10-01T15:00:00Z");
const TS = String(Math.floor(AHORA / 1000));

async function peticion(env, cuerpoObj, { ts = TS, nonce = "a".repeat(32), secreto = env.SYNC_SECRET, alterar, ruta = "/sync", metodo = "POST" } = {}) {
  const cuerpo = cuerpoObj === undefined ? "" : typeof cuerpoObj === "string" ? cuerpoObj : JSON.stringify(cuerpoObj);
  const firma = await firmar(secreto, { ts, nonce, metodo, ruta, cuerpo });
  const headers = { "X-Marca-Tiempo": ts, "X-Nonce": nonce, "X-Firma": firma, "Content-Length": String(new TextEncoder().encode(cuerpo).length) };
  const req = new Request(`https://monitor.test${ruta}`, { method: metodo, headers, body: metodo === "POST" ? (alterar ? alterar(cuerpo) : cuerpo) : undefined });
  return atender(req, env, AHORA);
}

test("vector de firma compartido con la terminal (Python)", async () => {
  const v = JSON.parse(readFileSync(new URL("./vector_firma.json", import.meta.url), "utf8"));
  assert.equal(await sha256Hex(v.cuerpo), v.hash_cuerpo);
  assert.equal(canonico({ ...v, hashCuerpo: v.hash_cuerpo }), v.canonico);
  assert.equal(await hmacHex(v.secreto, v.canonico), v.firma);
});

test("sincronización válida se guarda y una repetida (mismo nonce) se rechaza", async () => {
  const env = { ...ENV_BASE, DB: d1() };
  const r = await peticion(env, carga());
  assert.equal(r.status, 200);
  const otra = await peticion(env, carga());
  assert.equal(otra.status, 401);
  assert.equal((await otra.json()).motivo, "petición repetida");
});

test("firma inválida, secreto equivocado o cuerpo alterado ⇒ 401 sin guardar", async () => {
  const env = { ...ENV_BASE, DB: d1() };
  assert.equal((await peticion(env, carga(), { secreto: "x".repeat(43), nonce: "b".repeat(32) })).status, 401);
  const alterado = await peticion(env, carga(), { nonce: "c".repeat(32), alterar: (c) => c.replace("200000", "900000") });
  assert.equal(alterado.status, 401);
  assert.equal(await env.DB.prepare("SELECT valor FROM estado WHERE clave='carga'").first(), null);
});

test("marca de tiempo vieja (reenvío tardío) ⇒ 401", async () => {
  const env = { ...ENV_BASE, DB: d1() };
  const r = await peticion(env, carga(), { ts: String(Number(TS) - 600), nonce: "d".repeat(32) });
  assert.equal(r.status, 401);
  assert.match((await r.json()).motivo, /ventana/);
});

test("secuencia anterior o igual ⇒ 409 aunque la firma sea nueva", async () => {
  const env = { ...ENV_BASE, DB: d1() };
  assert.equal((await peticion(env, carga({ secuencia: 2000 }), { nonce: "e".repeat(32) })).status, 200);
  assert.equal((await peticion(env, carga({ secuencia: 1999 }), { nonce: "f".repeat(32) })).status, 409);
});

test("validación estricta: campos extra, tipos y tamaño", async () => {
  const env = { ...ENV_BASE, DB: d1() };
  const extra = carga();
  extra.cartera.contrasena = "x";
  const r = await peticion(env, extra, { nonce: "1".repeat(32) });
  assert.equal(r.status, 400);
  assert.match((await r.json()).error, /no permitido/);
  const mala = carga();
  mala.cartera.posiciones[0].titulos = -5;
  assert.equal((await peticion(env, mala, { nonce: "2".repeat(32) })).status, 400);
  const grande = carga({ calendario: [] });
  grande.plan.nombre = "x".repeat(MAX_BYTES);
  assert.equal((await peticion(env, grande, { nonce: "3".repeat(32) })).status, 413);
});

test("sin secreto configurado no acepta nada; /estado exige firma y no expone textos", async () => {
  const sin = { ...ENV_BASE, SYNC_SECRET: undefined, DB: d1() };
  assert.equal((await peticion(sin, carga(), { secreto: "s".repeat(43) })).status, 401);
  const env = { ...ENV_BASE, DB: d1() };
  const anon = await atender(new Request("https://monitor.test/estado"), env, AHORA);
  assert.equal(anon.status, 401);
  const r = await peticion(env, undefined, { ruta: "/estado", metodo: "GET", nonce: "9".repeat(32) });
  assert.equal(r.status, 200);
  const d = await r.json();
  assert.equal(d.monitor, "activo");
  assert.ok(!JSON.stringify(d).includes(ENV_BASE.TELEGRAM_BOT_TOKEN));
  const raiz = await atender(new Request("https://monitor.test/"), env, AHORA);
  assert.match(await raiz.text(), /Sin datos públicos/);
});
