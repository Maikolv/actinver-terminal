// Guiones del video en Word, generados desde docs/video/guiones-tiktok.md (una sola fuente).
//   node scripts/guiones_word.cjs   → docs/video/Guion_Video_Actinver_Terminal.docx
"use strict";
const fs = require("node:fs"), path = require("node:path");
const { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ShadingType,
  BorderStyle, AlignmentType, LevelFormat, PageOrientation, Footer, PageNumber } = require("docx");

const RAIZ = path.resolve(__dirname, "..");
// Uso: node scripts/guiones_word.cjs  — solo la versión de los 4 integrantes (la de 2 se retiró el 27-nov-2026).
const DOS = false;
let MD = fs.readFileSync(path.join(RAIZ, "docs", "video", "guiones-tiktok.md"), "utf8");
if (DOS) MD = MD.replace(/Miguel, Daniela, Valeria y Camila/g, "Miguel y Daniela")
  .replace(/\| Valeria \|/g, "| Miguel |").replace(/\| Camila \|/g, "| Daniela |");
const SALIDA = path.join(RAIZ, "docs", "video", DOS ? "Guion_Video_Miguel_y_Daniela.docx" : "Guion_Video_4_integrantes.docx");
const FUENTE = "Century Gothic", ROJO = "B3261E", ANCHO = 13958; // carta horizontal, márgenes de 0.7"

// Negritas y código en línea de Markdown → TextRun.
const runs = (t, extra = {}) => t.split(/(\*\*[^*]+\*\*|`[^`]+`)/).filter(Boolean).map((s) =>
  s.startsWith("**") ? new TextRun({ text: s.slice(2, -2), bold: true, ...extra })
    : s.startsWith("`") ? new TextRun({ text: s.slice(1, -1), font: "Consolas", ...extra }) : new TextRun({ text: s, ...extra }));

function tabla(filas) {
  const [cab, ...cuerpo] = filas;
  const n = cab.length;
  // La columna del texto hablado es la más ancha; el resto se reparte.
  const iTexto = cab.findIndex((c) => /^Texto|Lo que dice|Dónde lo cubre/.test(c));
  const anchos = cab.map((_, i) => (i === iTexto ? 0.38 : 0.62 / (n - (iTexto >= 0 ? 1 : 0))) * ANCHO).map(Math.floor);
  anchos[anchos.length - 1] += ANCHO - anchos.reduce((a, b) => a + b, 0);
  const borde = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
  const celda = (t, i, cabecera) => new TableCell({
    width: { size: anchos[i], type: WidthType.DXA }, borders: { top: borde, bottom: borde, left: borde, right: borde },
    margins: { top: 60, bottom: 60, left: 90, right: 90 },
    shading: cabecera ? { fill: "1F2229", type: ShadingType.CLEAR, color: "auto" } : i === iTexto ? { fill: "FFF4F3", type: ShadingType.CLEAR, color: "auto" } : undefined,
    children: [new Paragraph({ children: runs(t, { size: i === iTexto && !cabecera ? 21 : 18, color: cabecera ? "FFFFFF" : undefined, bold: cabecera || undefined }) })] });
  return new Table({ width: { size: ANCHO, type: WidthType.DXA }, columnWidths: anchos,
    rows: [new TableRow({ tableHeader: true, children: cab.map((t, i) => celda(t, i, true)) }),
      ...cuerpo.map((f) => new TableRow({ cantSplit: true, children: f.map((t, i) => celda(t, i, false)) }))] });
}

const hijos = [];
const lineas = MD.split(/\r?\n/);
for (let i = 0; i < lineas.length; i++) {
  const l = lineas[i];
  if (l.startsWith("|")) {
    const filas = [];
    while (i < lineas.length && lineas[i].startsWith("|")) {
      if (!/^\|[-| ]+\|$/.test(lineas[i].trim())) filas.push(lineas[i].trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim()));
      i++;
    }
    i--;
    hijos.push(tabla(filas), new Paragraph({ spacing: { after: 120 }, children: [] }));
  } else if (l.startsWith("# ")) hijos.push(new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun(l.slice(2))] }));
  else if (l.startsWith("## ")) hijos.push(new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: /^## Versión/.test(l), children: [new TextRun(l.slice(3))] }));
  else if (/^- \[ \] /.test(l)) hijos.push(new Paragraph({ spacing: { after: 60 }, children: [new TextRun("☐ "), ...runs(l.slice(6))] }));
  else if (/^\d+\. /.test(l)) hijos.push(new Paragraph({ numbering: { reference: "numeros", level: 0 }, spacing: { after: 60 }, children: runs(l.replace(/^\d+\. /, "")) }));
  else if (/^- /.test(l)) hijos.push(new Paragraph({ numbering: { reference: "vinetas", level: 0 }, spacing: { after: 60 }, children: runs(l.slice(2)) }));
  else if (/^ {2}- /.test(l)) hijos.push(new Paragraph({ numbering: { reference: "vinetas", level: 1 }, spacing: { after: 60 }, children: runs(l.trim().slice(2)) }));
  else if (/^-{3,}$/.test(l.trim())) continue;  // separador de Markdown
  else if (/^ {2}\S/.test(l)) hijos.push(new Paragraph({ indent: { left: 540 }, spacing: { after: 60 }, children: runs(l.trim()) }));  // continuación de viñeta
  else if (l.trim()) hijos.push(new Paragraph({ spacing: { after: 120 }, children: runs(l) }));
}

const doc = new Document({
  creator: "Equipo Actinver Terminal", title: "Guiones del video — Actinver Terminal",
  styles: { default: { document: { run: { font: FUENTE, size: 20 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", run: { font: FUENTE, size: 40, bold: true, color: ROJO }, paragraph: { spacing: { before: 0, after: 240 } } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FUENTE, size: 28, bold: true, color: ROJO }, paragraph: { spacing: { before: 240, after: 120 }, keepNext: true, outlineLevel: 0 } }] },
  numbering: { config: [
    { reference: "vinetas", levels: [0, 1].map((n) => ({ level: n, format: LevelFormat.BULLET, text: n ? "–" : "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540 + n * 360, hanging: 270 } } } })) },
    { reference: "numeros", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] }] },
  sections: [{ properties: { page: { size: { width: 12240, height: 15840, orientation: PageOrientation.LANDSCAPE }, margin: { top: 1008, bottom: 1008, left: 1008, right: 1008 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "Actinver Terminal · proyecto escolar independiente, no afiliado a Grupo Actinver · página ", size: 16, color: "6B7280" }), new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "6B7280" })] })] }) },
    children: hijos }],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(SALIDA, b); console.log(SALIDA); });
