// Informe escrito del Concurso Finanzas IA (formato UVM) con datos REALES del archivo del Reto Actinver 2026.
// Cifras: data/medios/informe/datos.json (scripts/informe_concurso_datos.py). Encabezado y pie: los de la plantilla
// original (logos UVM). Lo que no existe en el archivo queda como «PENDIENTE: dato — fuente».
//   node scripts/informe_concurso.cjs   → entregables/Informe_Concurso_Finanzas_IA.docx
"use strict";
const fs = require("node:fs"), path = require("node:path");
const JSZip = require("jszip");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, AlignmentType, ImageRun,
  ShadingType, BorderStyle, PageBreak, TableOfContents, Header, Footer, LevelFormat, PageNumber,
} = require("docx");

const RAIZ = path.resolve(__dirname, "..");
const INF = path.join(RAIZ, "data", "medios", "informe");
const PLANTILLA = path.join(RAIZ, "data", "medios", "plantilla", "plantilla.docx");
const SALIDA = path.join(RAIZ, "entregables", "Informe_Concurso_Finanzas_IA.docx");
const d = JSON.parse(fs.readFileSync(path.join(INF, "datos.json"), "utf8"));

const FUENTE = "Century Gothic", ROJO = "B3261E", GRIS = "4A505A";
const mxn = (x) => x == null ? "—" : `$${Number(x).toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const pct = (x, dd = 2) => x == null ? "—" : `${(x * 100).toFixed(dd)} %`;
const num = (x) => Number(x).toLocaleString("es-MX", { maximumFractionDigits: 2 });
const fecha = (iso) => new Date(iso).toLocaleString("es-MX", { timeZone: "America/Mexico_City", day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
const sym = (id) => id.split(":")[1];

const p = (texto, o = {}) => new Paragraph({ spacing: { after: 120 }, alignment: o.centrar ? AlignmentType.CENTER : AlignmentType.JUSTIFIED,
  children: [].concat(texto).map((t) => typeof t === "string" ? new TextRun({ text: t, ...o.run }) : t) });
const b = (t) => new TextRun({ text: t, bold: true });
const pend = (t) => new TextRun({ text: `PENDIENTE: ${t}`, bold: true, color: ROJO });
const vineta = (texto) => new Paragraph({ numbering: { reference: "vinetas", level: 0 }, spacing: { after: 60 },
  children: [].concat(texto).map((t) => typeof t === "string" ? new TextRun(t) : t) });
const h1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const h2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const fuente = (t) => new Paragraph({ spacing: { after: 160 }, children: [new TextRun({ text: `Fuente: ${t}`, italics: true, size: 16, color: GRIS })] });

const ANCHO = 8838; // carta con márgenes de la plantilla (1701 DXA por lado)
function tabla(cab, filas, anchos) {
  const borde = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
  const bordes = { top: borde, bottom: borde, left: borde, right: borde };
  const celda = (t, i, encabezado) => new TableCell({
    width: { size: anchos[i], type: WidthType.DXA }, borders: bordes, margins: { top: 60, bottom: 60, left: 90, right: 90 },
    shading: encabezado ? { fill: "1F2229", type: ShadingType.CLEAR, color: "auto" } : undefined,
    children: [new Paragraph({ alignment: i > 0 && !encabezado && /^[-$\d.,% ]/.test(String(t)) ? AlignmentType.RIGHT : AlignmentType.LEFT,
      children: [new TextRun({ text: String(t), size: 17, bold: encabezado, color: encabezado ? "FFFFFF" : undefined })] })] });
  return new Table({ width: { size: ANCHO, type: WidthType.DXA }, columnWidths: anchos,
    rows: [new TableRow({ tableHeader: true, children: cab.map((t, i) => celda(t, i, true)) }),
      ...filas.map((f) => new TableRow({ children: f.map((t, i) => celda(t, i, false)) }))] });
}
const imagen = (archivo, ancho, alto) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
  children: [new ImageRun({ type: "png", data: fs.readFileSync(path.join(INF, archivo)), transformation: { width: ancho, height: alto } })] });

const ini = d.inicial, oct = d.corte_octubre, fin = d.final, r = d.riesgo, bm = d.benchmark, t = d.tecnico_mu;
const ARGUMENTO = {
  "SIC:MU": "Líder en memoria (DRAM/HBM) para centros de datos de IA; mayor rendimiento esperado del ranking de la terminal en la fecha de elección.",
  "BMV:GMEXICO": "Emisora mexicana de cobre con flujo en dólares; diversifica fuera de tecnología y aporta exposición a materias primas.",
  "SIC:AMD": "Semiconductores para IA y servidores; segunda apuesta tecnológica con menor peso que MU.",
  "SIC:QQQ": "ETF del Nasdaq-100: diversificación amplia dentro de tecnología con un solo instrumento.",
  "BMV:ALPEK": "Química y plásticos mexicana; posición pequeña de valor con baja correlación con tecnología.",
  "SIC:AMAT": "Equipo para fabricar semiconductores; complementa la tesis de la cadena de chips.",
};

const portada = [
  new Paragraph({ spacing: { before: 1400, after: 300 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Concurso Finanzas IA — Reto Actinver 2026", bold: true, size: 40, color: ROJO })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 }, children: [new TextRun({ text: "Informe escrito", size: 30 })] }),
  ...[["Nombre del concurso", "Reto Actinver 2026 — Concurso Finanzas IA"],
    ["Nombre del equipo", null], ["Nombres completos de los integrantes", null], ["Matrículas y carrera", null],
    ["Campus", null], ["Fecha de entrega", null], ["Nombre del docente", null], ["Asignatura", null]].map(([k, v]) =>
    new Paragraph({ spacing: { after: 140 }, children: [b(`${k}: `), v ? new TextRun(v) : pend("completar (dato del equipo; no se inventa)")] })),
  new Paragraph({ children: [new PageBreak()] }),
];

const indice = [h1("Índice"), new TableOfContents("Índice", { hyperlink: true, headingStyleRange: "1-2" }),
  p([new TextRun({ text: "Al abrir en Word: clic derecho en el índice → Actualizar campo → Actualizar toda la tabla, para ver los números de página.", italics: true, size: 16, color: GRIS })]),
  new Paragraph({ children: [new PageBreak()] })];

const resumen = [h1("1. Resumen ejecutivo"),
  p(`Este informe documenta la participación del equipo en el Reto Actinver 2026 (competencia del 5 de octubre al 13 de noviembre de 2026) con un capital simulado de ${mxn(d.capital_inicial)}. La estrategia fue de crecimiento agresivo, concentrada al inicio en semiconductores e inteligencia artificial (Micron, AMD, AMAT y el ETF QQQ) con dos emisoras mexicanas (Grupo México y Alpek) para diversificar. Las decisiones se apoyaron en una terminal propia de análisis, Actinver Terminal, que calcula portafolios con Markowitz, mide el riesgo y registra cada captura del portal; la terminal solo informa y simula: las órdenes se capturaron a mano en el simulador.`),
  p(`Resultado: el portafolio cerró en ${mxn(fin.valor)} (${pct(fin.rend)} frente al capital inicial), mientras el NAFTRAC, réplica del IPC, subió ${pct(bm?.rendimiento)} en el mismo periodo. La concentración en tecnología explicó la pérdida: la corrección del sector a finales de octubre y principios de noviembre pesó sobre MU, que llegó a representar casi la mitad de la cartera. En la última semana se rotó hacia consumo básico y salud. La principal lección es que el riesgo de concentración debe medirse y limitarse antes de buscar rendimiento.`),
  new Paragraph({ children: [new PageBreak()] })];

const plan = [h1("2. Plan de inversión inicial (Entregable 1)"),
  h2("2.1 Justificación de la selección de acciones"),
  p(`Cartera registrada en la primera captura de la competencia (${fecha(ini.hora)}).`),
  tabla(["Instrumento", "Sector", "Argumento clave"], ini.posiciones.map((x) => [sym(x.instrumento), x.sector, ARGUMENTO[x.instrumento] || "PENDIENTE: argumento"]), [1300, 2300, 5238]),
  fuente("captura del portal del Reto registrada en Actinver Terminal; sector de SEC EDGAR (SIC) para emisoras de EE. UU."),
  h2("2.2 Estrategia general de inversión"),
  vineta([b("Perfil: "), "agresivo (máximo rendimiento esperado, aceptando riesgo de cola)."]),
  vineta([b("Horizonte y tolerancia: "), "seis semanas de competencia; tolerancia alta a la volatilidad, con la regla del Reto de un máximo de 50 % por emisora."]),
  vineta([b("Diversificación: "), "seis instrumentos (el Reto exigía al menos cinco), dos mercados (BMV y SIC) y tres sectores; la concentración en semiconductores fue la decisión de mayor riesgo."]),
  h2("2.3 Distribución del capital"),
  tabla(["Instrumento", "Títulos", "Valor (MXN)", "Peso"], ini.posiciones.map((x) => [sym(x.instrumento), num(x.titulos), mxn(x.valor), pct(x.peso, 1)]), [2400, 1600, 2638, 2200]),
  p(`Monto base simulado: ${mxn(d.capital_inicial)} (actipesos). Valor del portafolio en la captura: ${mxn(ini.valor)}; efectivo sin invertir: ${mxn(ini.efectivo)}.`),
  imagen("distribucion_inicial.png", 400, 277),
  fuente("captura del portal del 5-oct-2026; gráfica generada por la terminal."),
  h2("2.4 Simulación y monitoreo"),
  p([pend("capturas de pantalla iniciales de la plataforma Actinver — insertar aquí las imágenes del portal del 5-oct-2026 que el equipo tomó (la terminal guardó el texto de la captura, no la imagen).")]),
  p(`Observaciones: en el primer día el portafolio pasó de ${mxn(ini.valor)} a ${mxn(d.serie[1]?.valor)}; MU concentraba ${pct(ini.posiciones[0].peso, 1)} del valor, cerca del tope de 50 % del Reto. El 6 y 7 de octubre se vendieron QQQ y AMAT y se compraron NVIDIA, Exxon Mobil y Novavax para ajustar la tesis.`),
  new Paragraph({ children: [new PageBreak()] })];

const seg = [h1("3. Informe de seguimiento intermedio (Entregable 2)"),
  h2("3.1 Resumen del desempeño de la cartera"),
  p("Movimientos realizados entre el 6 y el 31 de octubre (cambios de títulos entre capturas consecutivas del portal):"),
  tabla(["Fecha", "Instrumento", "Operación", "Títulos antes → después"], d.movimientos_octubre.map((m) => [m.fecha, sym(m.instrumento), m.tipo, `${num(m.de)} → ${num(m.a)}`]), [1800, 2000, 1800, 3238]),
  p([b("Valor de la cartera al corte: "), `${mxn(oct.valor)} (${fecha(oct.hora)}). `, b("Rentabilidad acumulada: "), pct(oct.rend), "."]),
  tabla(["Instrumento", "Títulos", "Costo prom.", "Precio", "Valor", "Rend."], oct.posiciones.map((x) => [sym(x.instrumento), num(x.titulos), mxn(x.costo_promedio), mxn(x.precio), mxn(x.valor), pct(x.rend, 1)]), [1300, 1000, 1550, 1550, 1838, 1600]),
  fuente("captura del portal del 30-oct-2026 registrada en la terminal (precios en MXN; SIC convertido por el portal)."),
  h2("3.2 Análisis fundamental — Micron Technology (MU)"),
  p("Se eligió MU por ser la mayor posición. Indicadores solicitados:"),
  tabla(["Indicador", "Valor", "Fuente"], [
    ["Liquidez (razón circulante)", "PENDIENTE", "10-K/10-Q de MU en SEC EDGAR"],
    ["Apalancamiento (deuda/capital)", "PENDIENTE", "10-K/10-Q de MU en SEC EDGAR"],
    ["Operatividad (rotación de activos)", "PENDIENTE", "10-K/10-Q de MU en SEC EDGAR"],
    ["Rentabilidad (margen neto, ROE)", "PENDIENTE", "10-K/10-Q de MU en SEC EDGAR"],
    ["P/E", "PENDIENTE", "precio ÷ utilidad por acción de 12 meses (SEC + cierre)"],
    ["Crecimiento en ventas y utilidades", "PENDIENTE", "comparar los dos últimos 10-K"]], [3200, 1800, 3838]),
  p([pend("estos valores no se guardaron en la terminal; obtenerlos del último 10-K de Micron (sec.gov/edgar, CIK 0000723125) y anotar fecha y fórmula. No se inventan.")]),
  h2("3.3 Análisis técnico — MU, últimos 3 meses"),
  imagen("tecnico_mu.png", 560, 420),
  fuente(`${t.fuente}; ${t.desde} a ${t.hasta}.`),
  tabla(["Indicador", "Valor al " + t.hasta, "Lectura"], [
    ["Cierre", `${num(t.cierre)} USD`, `Variación de 3 meses: ${pct(t.variacion_3m, 1)}`],
    ["Media móvil 20 / 50", `${num(t.sma20)} / ${num(t.sma50)} USD`, t.cierre < t.sma20 && t.sma20 < t.sma50 ? "Precio debajo de ambas medias y la de 20 bajo la de 50: tendencia bajista" : "Tendencia mixta"],
    ["RSI 14 (Wilder)", num(t.rsi14), t.rsi14 < 30 ? "Sobreventa" : t.rsi14 > 70 ? "Sobrecompra" : "Zona neutral, sin sobreventa"],
    ["MACD (12-26-9)", `${num(t.macd)} / señal ${num(t.senal)}`, t.macd < t.senal ? "MACD bajo su señal: impulso negativo" : "MACD sobre su señal: impulso positivo"]], [2600, 2600, 3638]),
  p("Interpretación: a mediados de noviembre MU seguía en tendencia bajista (precio bajo sus medias y MACD negativo), sin señal de sobreventa extrema; técnicamente no había razón para aumentar la posición, lo que respalda la decisión de reducir la concentración en tecnología."),
  new Paragraph({ children: [new PageBreak()] })];

const cerradas = [...new Set(d.movimientos_todos.filter((m) => m.a === 0).map((m) => m.instrumento))];
const final = [h1("4. Informe final (Entregable 3)"),
  h2("4.1 Resumen final del portafolio"),
  tabla(["Concepto", "Valor"], [
    ["Valor final del portafolio", `${mxn(fin.valor)} (${fecha(fin.hora)})`],
    ["Rentabilidad total", `${pct(fin.rend)} sobre ${mxn(d.capital_inicial)}`],
    ["Desviación estándar diaria (anualizada)", `${pct(r.desv_diaria)} (${pct(r.desv_anual, 1)})`],
    ["VaR histórico 95 % a un día", `${pct(r.var95_historico_diario)}: en 19 de cada 20 días la pérdida no superó este porcentaje`],
    ["Peor día / mejor día", `${pct(r.peor_dia)} / ${pct(r.mejor_dia)}`],
    ["Benchmark: " + (bm?.instrumento || "—"), `${pct(bm?.rendimiento)} del ${bm?.inicio} al ${bm?.fin}`]], [3600, 5238]),
  p(`Las métricas de riesgo usan ${r.observaciones} rendimientos diarios calculados con la última captura de cada día; es una muestra corta, por lo que el VaR es aproximado. Frente al mercado mexicano, el portafolio quedó ${pct(fin.rend - (bm?.rendimiento || 0))} por debajo del NAFTRAC.`),
  imagen("evolucion.png", 560, 252),
  fuente("capturas del portal (34) y cierres EOD de NAFTRAC (EODHD) guardados en Actinver Terminal."),
  h2("4.2 Análisis de resultados por acción"),
  tabla(["Instrumento", "Títulos", "Costo prom.", "Precio final", "Rend.", "Decisión"], fin.posiciones.map((x) => [sym(x.instrumento), num(x.titulos), mxn(x.costo_promedio), mxn(x.precio), pct(x.rend, 1), "Mantener al cierre"]), [1300, 1000, 1550, 1550, 1200, 2238]),
  p(`Posiciones cerradas durante el concurso: ${cerradas.map(sym).join(", ")}. La salida de MU, NVDA, AMD y Grupo México del 10 y 11 de noviembre liberó efectivo que se reinvirtió en consumo básico (FEMSA, KOF, Arca Continental, Target) y salud (Merck, Eli Lilly, AbbVie, Moderna), con Chevron y Exxon en energía.`),
  vineta([b("Ganadoras: "), "Exxon Mobil (+7.5 % sobre costo), Arca Continental y Chevron (≈ +2 %)."]),
  vineta([b("Perdedoras: "), "Novavax (−19.3 %) y Moderna (−8.1 %). En tecnología, MU era la posición de mayor peso cuando cayó el sector (ver la caída del 3 al 5 de noviembre en la serie del anexo C)."]),
  h2("4.3 Capturas y evidencias"),
  p([pend("evidencia del portafolio final con nombre visible del equipo y capturas clave de operaciones — insertar las imágenes del portal del 12-nov-2026 y de las operaciones del 10–12 de noviembre.")]),
  p("La gráfica general del comportamiento del portafolio está en la sección 4.1."),
  h2("4.4 Reflexión final"),
  vineta([b("Decisiones clave: "), "concentrar casi 50 % en MU al inicio (mayor impacto negativo) y rotar a consumo y salud en la última semana (redujo la volatilidad, pero tarde)."]),
  vineta([b("Errores: "), "no limitar el peso por emisora por debajo del tope del Reto; reaccionar a la caída del sector después y no antes; tomar posiciones pequeñas de bajo valor informativo (SLV, ACTDUAL, PFE)."]),
  vineta([b("Lecciones: "), "el riesgo de concentración se mide antes de buscar rendimiento; comparar siempre contra una referencia simple (1/N o el índice); un modelo sin ventaja demostrada fuera de muestra no debe decidir solo."]),
  vineta([b("Aprendizaje con IA: "), "construimos Actinver Terminal con asistentes de IA (Claude y Codex): optimización de Markowitz, VaR/CVaR, validación fuera de muestra y registro de cada captura. La IA aceleró el análisis, pero también mostró sus límites: ningún modelo superó a la cartera equiponderada fuera de muestra, y así lo declaramos."]),
  new Paragraph({ children: [new PageBreak()] })];

const refs = [h1("5. Referencias"),
  ...["Actinver. (2026). Reto Actinver 2026: bases y mecánica. https://www.retoactinver.com/web/reto-actinver/bases-y-mecanica",
    "Markowitz, H. (1952). Portfolio selection. The Journal of Finance, 7(1), 77–91. https://doi.org/10.2307/2975974",
    "Ledoit, O., & Wolf, M. (2004). Honey, I shrunk the sample covariance matrix. The Journal of Portfolio Management, 30(4), 110–119. https://doi.org/10.3905/jpm.2004.110",
    "DeMiguel, V., Garlappi, L., & Uppal, R. (2009). Optimal versus naive diversification: How inefficient is the 1/N portfolio strategy? The Review of Financial Studies, 22(5), 1915–1953. https://doi.org/10.1093/rfs/hhm075",
    "Wilder, J. W. (1978). New concepts in technical trading systems. Trend Research.",
    "U.S. Securities and Exchange Commission. (2026). EDGAR full-text search and company filings. https://www.sec.gov/edgar"]
    .map((x) => new Paragraph({ spacing: { after: 120 }, indent: { left: 720, hanging: 720 }, children: [new TextRun(x)] })),
  new Paragraph({ children: [new PageBreak()] })];

const anexos = [h1("Anexos"),
  h2("A. Capturas completas de la plataforma Actinver"), p([pend("insertar las capturas del portal (el archivo de la terminal tiene 34 registros de texto del 30-sep al 12-nov-2026).")]),
  h2("B. Códigos de equipo y nickname"), p([pend("código del equipo y nickname en el Reto.")]),
  h2("C. Serie del valor del portafolio (última captura de cada día)"),
  tabla(["Fecha", "Valor (MXN)", "Rend. acumulado"], d.serie.map((x) => [x.fecha, mxn(x.valor), pct(x.valor / d.capital_inicial - 1)]), [2800, 3200, 2838]),
  fuente("capturas del portal registradas en Actinver Terminal (data/archivo/reto-actinver-2026-20261117.db)."),
  h2("D. Evidencias de asesorías"), p([pend("opcional: evidencias de asesorías, si el equipo las tuvo.")]),
  h2("E. Herramienta de apoyo"), p("Actinver Terminal (proyecto independiente, sin afiliación con Grupo Actinver): https://github.com/Maikolv/help-quote-terminal. Solo informa y simula; no envía órdenes.")];

const doc = new Document({
  creator: "Equipo Reto Actinver 2026", title: "Informe escrito — Concurso Finanzas IA",
  styles: { default: { document: { run: { font: FUENTE, size: 20 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FUENTE, size: 28, bold: true, color: ROJO }, paragraph: { spacing: { before: 240, after: 160 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FUENTE, size: 23, bold: true, color: "1F2229" }, paragraph: { spacing: { before: 200, after: 100 }, keepNext: true, outlineLevel: 1 } }] },
  numbering: { config: [{ reference: "vinetas", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1417, right: 1701, bottom: 1417, left: 1701, header: 708, footer: 708 } } },
    headers: { default: new Header({ children: [new Paragraph("ENCABEZADO")] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ children: [PageNumber.CURRENT] })] })] }) },
    children: [...portada, ...indice, ...resumen, ...plan, ...seg, ...final, ...refs, ...anexos] }],
});

(async () => {
  // El encabezado y el pie se reemplazan por los de la plantilla UVM (logos anclados), sin tocar el cuerpo.
  const gen = await JSZip.loadAsync(await Packer.toBuffer(doc));
  const pla = await JSZip.loadAsync(fs.readFileSync(PLANTILLA));
  const rels = await gen.file("word/_rels/document.xml.rels").async("string");
  const objetivo = (tipo) => rels.match(new RegExp(`Type="[^"]+/${tipo}" Target="([^"]+)"`))[1];
  const hdr = objetivo("header"), ftr = objetivo("footer");
  gen.file(`word/${hdr}`, await pla.file("word/header1.xml").async("string"));
  gen.file(`word/_rels/${hdr}.rels`, (await pla.file("word/_rels/header1.xml.rels").async("string")).replace(/media\/image(\d)\.png/g, "media/uvm$1.png"));
  gen.file(`word/${ftr}`, await pla.file("word/footer1.xml").async("string"));
  gen.file(`word/_rels/${ftr}.rels`, (await pla.file("word/_rels/footer1.xml.rels").async("string")).replace(/media\/image(\d)\.png/g, "media/uvm$1.png"));
  for (const i of [1, 2, 3]) gen.file(`word/media/uvm${i}.png`, await pla.file(`word/media/image${i}.png`).async("nodebuffer"));
  let tipos = await gen.file("[Content_Types].xml").async("string");
  if (!tipos.includes('Extension="png"')) tipos = tipos.replace("<Types ", "<Types ").replace(/(<Types[^>]*>)/, '$1<Default Extension="png" ContentType="image/png"/>');
  gen.file("[Content_Types].xml", tipos);
  fs.mkdirSync(path.dirname(SALIDA), { recursive: true });
  fs.writeFileSync(SALIDA, await gen.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
  console.log(SALIDA);
})().catch((e) => { console.error(e); process.exit(1); });
