// Reporte ejecutivo generado desde el modelo (como los entregables de COATL): las cifras salen del motor
// (terminal.escenario_referencia) y del historial (docs/versiones.json), nunca escritas a mano. El PDF se compone con
// Chromium (Edge) desde la plantilla, con la paleta de la terminal y un QR a la versión estática en GitHub Pages.
//   node scripts/reporte_ejecutivo.cjs   → docs/reporte-ejecutivo/reporte-ejecutivo.{html,pdf}
"use strict";
const { execFileSync } = require("node:child_process");
const fs = require("node:fs"), path = require("node:path");
const { chromium } = require("playwright");
const qrcode = require("qrcode-generator");

const RAIZ = path.resolve(__dirname, "..");
const DIR = path.join(RAIZ, "docs", "reporte-ejecutivo");
const URL_TERMINAL = "https://maikolv.github.io/actinver-terminal/terminal/";
const pct = (x, d = 2) => `${(x * 100).toFixed(d)} %`;

function cifrasMotor() {
  const salida = execFileSync("uv", ["run", "python", "-m", "terminal.escenario_referencia"], { cwd: RAIZ, encoding: "utf8" });
  return JSON.parse(salida.trim().split("\n").pop());
}

function escenarioHtml(c) {
  const filas = Object.keys(c.pesos_demo).map((id) =>
    `<tr><td>${id}</td><td>${pct(c.pesos_demo[id], 1)}</td><td>${pct(c.max_sharpe[id], 1)}</td></tr>`).join("");
  return `<table><tr><th>Métrica (cartera demo)</th><th>Valor</th></tr>
<tr><td>Rendimiento esperado anual</td><td>${pct(c.rend_esperado)}</td></tr>
<tr><td>Volatilidad anual (Ledoit-Wolf)</td><td>${pct(c.volatilidad)}</td></tr>
<tr><td>VaR 95 % a 1 día (histórico)</td><td>${pct(c.var95_1d)}</td></tr>
<tr><td>CVaR 95 % a 1 día</td><td>${pct(c.cvar95_1d)}</td></tr>
<tr><td>Tasa libre de riesgo usada</td><td>${pct(c.rf, 1)}</td></tr></table>
<table><tr><th>Instrumento</th><th>Peso demo</th><th>Máximo Sharpe</th></tr>${filas}</table>`;
}

(async () => {
  const c = cifrasMotor();
  const v = JSON.parse(fs.readFileSync(path.join(RAIZ, "docs", "versiones.json"), "utf8")).versiones[0];
  const cif = v.cifras || {};
  const qr = qrcode(0, "M");
  qr.addData(URL_TERMINAL);
  qr.make();
  const fecha = new Date().toLocaleDateString("es-MX", { day: "numeric", month: "long", year: "numeric", timeZone: "America/Mexico_City" });
  const html = fs.readFileSync(path.join(DIR, "plantilla.html"), "utf8")
    .replace("{{fecha}}", fecha)
    .replace("{{version}}", `${v.version} (${v.fecha})`)
    .replace("{{qr}}", qr.createSvgTag({ cellSize: 3, margin: 0, scalable: true }))
    .replace("{{escenario}}", escenarioHtml(c))
    .replace("{{pruebas}}", `Pruebas automáticas en la última versión: Python ${cif.pytest ?? "—"}, interfaz ${cif.node ?? "—"}`)
    .replace("{{capturas}}", "../capturas/");
  const destino = path.join(DIR, "reporte-ejecutivo.html");
  fs.writeFileSync(destino, html);
  const b = await chromium.launch({ channel: process.env.CANAL || "msedge", headless: true });
  const p = await b.newPage();
  await p.goto("file:///" + destino.replace(/\\/g, "/"), { waitUntil: "load" });
  await p.pdf({ path: path.join(DIR, "reporte-ejecutivo.pdf"), format: "Letter", printBackground: true,
    margin: { top: "18mm", bottom: "18mm", left: "16mm", right: "16mm" } });
  await b.close();
  console.log("docs/reporte-ejecutivo/reporte-ejecutivo.{html,pdf}");
})().catch((e) => { console.error(e); process.exit(1); });
