// El QR del reporte solo lleva parámetros del escenario: nunca montos, pesos, títulos ni datos de la cuenta.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const ctx = { window: { addEventListener() {} }, document: { getElementById: () => null, querySelector: () => null }, location: { origin: "https://ejemplo", pathname: "/terminal/", hash: "" },
  btoa, atob, escape, unescape, encodeURIComponent, decodeURIComponent, JSON, Object, setTimeout };
vm.createContext(ctx);
vm.runInContext(readFileSync(new URL("../web/static/reporte.js", import.meta.url), "utf8"), ctx);
const R = ctx.window.HQTReporte;

test("el enlace usa el fragmento #r= y no la consulta", () => {
  const url = R.enlace({ vista: "tab-resumen", fecha: "2026-11-17", demo: true });
  assert.match(url, /^https:\/\/ejemplo\/terminal\/#r=[A-Za-z0-9+/]+$/);
  assert.ok(!url.includes("?"));
});

test("descarta cualquier dato que no sea del escenario", () => {
  const e = R.escenario({ vista: "tab-resumen", fecha: "2026-11-17", efectivo: 379012, posiciones: [{ id: "SIC:XOM", titulos: 10 }], pesos: { a: 1 } });
  assert.deepEqual(Object.keys(e).sort(), ["fecha", "v", "vista"]);
});

test("ida y vuelta conserva el escenario", () => {
  const datos = { v: 1, vista: "tab-resumen", fecha: "2026-11-17", modo_venta: "suave", demo: true };
  assert.deepEqual(JSON.parse(JSON.stringify(R.decodificar(R.codificar(datos)))), datos);
});
