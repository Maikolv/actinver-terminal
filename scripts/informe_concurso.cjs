// Informe escrito del Concurso Finanzas IA (formato UVM) con datos REALES del archivo del Reto Actinver 2026.
// Cifras: data/medios/informe/datos.json (scripts/informe_concurso_datos.py). Encabezado y pie: los de la plantilla
// original (logos UVM). Lo que no existe en el archivo queda como «PENDIENTE: dato — fuente».
//   node scripts/informe_concurso.cjs [4|2]   → entregables/Informe_Concurso_Finanzas_IA[_4_integrantes|_2_integrantes].docx
//   (4 o 2: el anexo F solo lleva los videos de esa versión de voz)
"use strict";
const fs = require("node:fs"), path = require("node:path");
const JSZip = require("jszip");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, AlignmentType, ImageRun,
  ShadingType, BorderStyle, PageBreak, TableOfContents, Header, Footer, LevelFormat, PageNumber, ExternalHyperlink,
} = require("docx");

const RAIZ = path.resolve(__dirname, "..");
const INF = path.join(RAIZ, "data", "medios", "informe");
const PLANTILLA = path.join(RAIZ, "data", "medios", "plantilla", "plantilla.docx");
const VERSION = { 4: "Equipo completo", 2: "Versión de 2" }[process.argv[2]];
const SALIDA = path.join(RAIZ, "entregables", `Informe_Concurso_Finanzas_IA${VERSION ? `_${process.argv[2]}_integrantes` : ""}.docx`);
const d = JSON.parse(fs.readFileSync(path.join(INF, "datos.json"), "utf8"));
// Datos personales del equipo: archivo privado fuera del repositorio (data/medios/equipo.json).
const RUTA_EQ = path.join(RAIZ, "data", "medios", "equipo.json");
const eq = fs.existsSync(RUTA_EQ) ? JSON.parse(fs.readFileSync(RUTA_EQ, "utf8")) : {};

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

// Capturas originales del portal: extraídas de la «Cronología integral» del equipo (data/medios/informe/portal).
const captura = (archivo, pie, ancho = 560) => {
  const buf = fs.readFileSync(path.join(INF, "portal", archivo));
  const w = buf.readUInt32BE(16), hh = buf.readUInt32BE(20);
  return [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 }, keepNext: true,
    children: [new ImageRun({ type: "png", data: buf, transformation: { width: ancho, height: Math.round(hh * ancho / w) } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: [new TextRun({ text: pie, italics: true, size: 16, color: GRIS })] })];
};
// Constancias en cuadrícula de dos columnas: celdas iguales, imagen y pie centrados; la última fila impar ocupa ambas columnas.
const cuadricula = (items) => {
  const sin = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  const celda = ([archivo, pie], span = 1) => new TableCell({ columnSpan: span, width: { size: ANCHO / 2 * span, type: WidthType.DXA },
    borders: { top: sin, bottom: sin, left: sin, right: sin }, margins: { top: 80, bottom: 80, left: 60, right: 60 },
    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new ImageRun({ type: "png",
      data: fs.readFileSync(path.join(INF, "constancias", archivo)), transformation: { width: 270, height: 209 } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 40 }, children: [new TextRun({ text: pie, italics: true, size: 15, color: GRIS })] })] });
  const filas = [];
  for (let i = 0; i < items.length; i += 2)
    filas.push(new TableRow({ cantSplit: true, children: i + 1 < items.length ? [celda(items[i]), celda(items[i + 1])] : [celda(items[i], 2)] }));
  return new Table({ width: { size: ANCHO, type: WidthType.DXA }, columnWidths: [ANCHO / 2, ANCHO / 2], alignment: AlignmentType.CENTER, rows: filas });
};
// Videos publicados (YouTube no listado, TikTok privado): enlaces en el archivo privado, no en el repositorio.
const VIDEOS = (eq.videos || []).filter(([v]) => !VERSION || v.startsWith(VERSION));
const qr = (url) => { const q = require("qrcode-generator")(0, "M"); q.addData(url); q.make();
  return Buffer.from(q.createDataURL(4, 8).split(",")[1], "base64"); };
const tablaVideos = () => {
  const borde = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
  const bordes = { top: borde, bottom: borde, left: borde, right: borde };
  const anchos = [2300, 4738, 1800];
  const txt = (t, o = {}) => new Paragraph({ children: [new TextRun({ text: t, size: 17, ...o })] });
  const celda = (hijos, i, fondo) => new TableCell({ width: { size: anchos[i], type: WidthType.DXA }, borders: bordes,
    verticalAlign: "center", margins: { top: 60, bottom: 60, left: 90, right: 90 },
    shading: fondo ? { fill: "1F2229", type: ShadingType.CLEAR, color: "auto" } : undefined, children: hijos });
  return new Table({ width: { size: ANCHO, type: WidthType.DXA }, columnWidths: anchos, alignment: AlignmentType.CENTER, rows: [
    new TableRow({ tableHeader: true, children: ["Versión", "Plataforma y enlace", "Código QR"].map((t, i) => celda([txt(t, { bold: true, color: "FFFFFF" })], i, true)) }),
    ...VIDEOS.map(([v, pl, url]) => new TableRow({ cantSplit: true, children: [
      celda([txt(v, { bold: true })], 0),
      celda([txt(pl), new Paragraph({ children: [new ExternalHyperlink({ link: url, children: [new TextRun({ text: url, size: 15, style: "Hyperlink" })] })] })], 1),
      celda([new Paragraph({ alignment: AlignmentType.CENTER, children: [new ImageRun({ type: "gif", data: qr(url), transformation: { width: 96, height: 96 } })] })], 2)] }))] });
};
const fm = JSON.parse(fs.readFileSync(path.join(INF, "fundamentales_mu.json"), "utf8"));
const usd = (x) => `${(x / 1e9).toLocaleString("es-MX", { maximumFractionDigits: 1 })} mil millones USD`;
const ini = d.inicial, oct = d.corte_octubre, fin = d.final, r = d.riesgo, bm = d.benchmark, t = d.tecnico_mu;
const ARGUMENTO = {
  "SIC:MU": "Líder en memoria (DRAM/HBM) para centros de datos de IA; mayor rendimiento esperado del ranking de la terminal en la fecha de elección.",
  "BMV:GMEXICO": "Emisora mexicana de cobre con flujo en dólares; diversifica fuera de tecnología y aporta exposición a materias primas.",
  "SIC:AMD": "Semiconductores para IA y servidores; segunda apuesta tecnológica con menor peso que MU.",
  "SIC:QQQ": "ETF del Nasdaq-100: diversificación amplia dentro de tecnología con un solo instrumento.",
  "BMV:ALPEK": "Química y plásticos mexicana; posición pequeña de valor con baja correlación con tecnología.",
  "SIC:AMAT": "Equipo para fabricar semiconductores; complementa la tesis de la cadena de chips.",
};

const CONCLUSION = {
  "BMV:FEMSA": "Mantener: consumo defensivo con flujo estable; entró en la rotación final y cerró casi sin cambio.",
  "BMV:KOF": "Mantener: embotelladora con demanda estable; ligera pérdida de corto plazo, sin cambio de tesis.",
  "SIC:TGT": "Mantener: comercio minorista de EE. UU. para diversificar el consumo; cerró plana.",
  "SIC:MRK": "Mantener: farmacéutica defensiva; ganancia moderada en la última semana.",
  "BMV:AC": "Mantener: la mejor de consumo mexicano (+2 %); flujo estable y baja correlación con tecnología.",
  "SIC:CVX": "Mantener: energía como cobertura frente a inflación y tecnología; ganancia de 1.6 %.",
  "SIC:LLY": "Mantener: salud con crecimiento propio (fármacos para obesidad); cerró sin cambio.",
  "SIC:XOM": "Mantener: la mejor posición del portafolio (+7.5 %); energía diversificó fuera de tecnología.",
  "SIC:NVAX": "Revisar: la peor posición (−19.3 %); apuesta especulativa de biotecnología que no debió crecer.",
  "SIC:ABBV": "Mantener: farmacéutica de dividendos; pequeña y estable.",
  "SIC:MRNA": "Revisar: biotecnología volátil (−8.1 %); poco peso, pero sin catalizador claro.",
  "SIC:PFE": "Vender en una cartera real: 2 títulos sin peso informativo; solo suma comisiones.",
};
const VENTA = {
  "SIC:QQQ": "Se cambió el ETF por acciones individuales (NVDA) para elevar el rendimiento esperado; salió casi a costo.",
  "SIC:AMAT": "Se sustituyó por NVDA, XOM y NVAX al día siguiente del inicio; salió con pérdida menor.",
  "SIC:SLV": "Cobertura con plata de una semana; no aportó y se cerró.",
  "FONDO:ACTDUAL": "Fondo de 1 título sin peso en la cartera; se liquidó para simplificar.",
  "SIC:MU": "Tendencia bajista (precio bajo medias de 20 y 50 días, MACD negativo) y casi 50 % del portafolio: se vendió para cortar la concentración, con la mayor pérdida (−29.5 %).",
  "BMV:GMEXICO": "Se vendió para financiar la rotación a consumo; salió con pérdida menor (−3.3 %).",
  "SIC:AMD": "Misma tesis de semiconductores que MU; se cerró con −16.2 % al reducir tecnología.",
  "SIC:NVDA": "Entró el 6-oct como apuesta de IA; la corrección del sector la llevó a −27.6 % y se vendió.",
  "BMV:ALPEK": "Química con resultados débiles; se vendió con −14.0 % para concentrar el efectivo en consumo.",
};

// 4.6 Propuesta de Markowitz: resultado de markowitz.guardar (data/medios/propuesta/resultado.json, privado).
function propuesta() {
  const ruta = path.join(RAIZ, "data", "medios", "propuesta", "resultado.json");
  if (!fs.existsSync(ruta)) return [];
  const pr = JSON.parse(fs.readFileSync(ruta, "utf8")), m = pr.metricas, n1 = pr.metricas_1n, s = pr.especificacion;
  const oos = pr.fuera_de_muestra, py = pr.proyeccion.elegido;
  const antes = Object.fromEntries(fin.posiciones.map((x) => [x.instrumento, x.peso]));
  const filas = [...pr.activos].sort((a, b) => b.peso - a.peso);
  return [h2("4.6 Propuesta del mejor portafolio con la plantilla de Markowitz"),
    p(`Con el último registro confirmado (captura del 12-nov-2026, valor ${mxn(fin.valor)}) repartimos los mismos ${filas.length} instrumentos con la plantilla de Markowitz de la terminal (Teoría Moderna de Portafolios): máximo Sharpe, covarianza muestral de ${pr.datos.sesiones} sesiones (${pr.datos.inicio} a ${pr.datos.fin}), tasa libre de riesgo CETES 28 de Banxico (${pct(s.rf)}) y tope de ${pct(s.peso_max, 0)} por emisora (perfil agresivo del equipo). Es el mismo cálculo que hace Solver en el Excel entregado (Propuesta_Markowitz_Lynx_Market.xlsx) y queda guardado en «Mis portafolios» de Actinver Terminal.`),
    imagen("propuesta_markowitz.png", 520, 303),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: [new TextRun({ text: "Figura 10. Pesos del último registro frente a la propuesta de Markowitz.", italics: true, size: 16, color: GRIS })] }),
    tabla(["Instrumento", "Peso 12-nov", "Peso propuesto", "Títulos", "Monto", "E(r) anual", "σ anual"],
      filas.map((a) => [a.id.split(":")[1], pct(antes[a.id], 1), pct(a.peso, 1), String(a.titulos), mxn(a.invertido), pct(a.rend, 1), pct(a.riesgo, 1)]),
      [1250, 1150, 1300, 900, 1538, 1350, 1350]),
    fuente(`Actinver Terminal, «Mis portafolios» (portafolio «${s.nombre}»); precios MXN ajustados; capital ${mxn(s.capital)}; efectivo sin invertir por títulos enteros ${mxn(pr.efectivo_restante)}.`),
    tabla(["Métrica (ventana de 1 año)", "Propuesta (máx. Sharpe)", "Mínima varianza", "1/N (referencia)"],
      [["Rendimiento esperado anual", pct(m.rend, 1), pct(pr.min_varianza.rend, 1), pct(n1.rend, 1)],
       ["Riesgo (σ anual)", pct(m.riesgo, 1), pct(pr.min_varianza.riesgo, 1), pct(n1.riesgo, 1)],
       ["Sharpe", m.sharpe.toFixed(2), pr.min_varianza.sharpe.toFixed(2), n1.sharpe.toFixed(2)]],
      [3238, 2000, 1800, 1800]),
    fuente("estimación con la historia de un año; no es un pronóstico."),
    vineta([b("Qué cambia: "), "sube Target, Arca Continental, Chevron y Exxon (más rendimiento por unidad de riesgo y baja correlación entre sí) y baja FEMSA, Novavax y Eli Lilly; Merck y Pfizer quedan en cero porque, con estos datos, no mejoran el portafolio."]),
    vineta([b("Riesgo: "), `σ anual de ${pct(m.riesgo, 1)} frente a ${pct(n1.riesgo, 1)} de repartir en partes iguales; caída máxima en la ventana ${pct(pr.caida_maxima, 1)} y peor día ${pct(pr.peor_dia, 1)}. Moderna aporta ${pct(filas.find((a) => a.id === "SIC:MRNA")?.contribucion_riesgo ?? 0, 0)} del riesgo con solo ${pct(filas.find((a) => a.id === "SIC:MRNA")?.peso ?? 0, 1)} del dinero: es la posición a vigilar.`]),
    vineta([b("Prueba fuera de muestra (honestidad): "), `de ${oos.inicio} a ${oos.fin}, rebalanceando cada mes, la propuesta rindió ${pct(oos.propuesta.rend_total, 1)} contra ${pct(oos["1/N"].rend_total, 1)} de 1/N, pero con más riesgo: su Sharpe fue ${oos.propuesta.sharpe.toFixed(2)} contra ${oos["1/N"].sharpe.toFixed(2)} de 1/N. Un solo periodo no demuestra ventaja.`]),
    vineta([b("Proyección a un año: "), `con capital de ${mxn(s.capital)}, valor esperado ${mxn(py.valor)} y rango del 90 % de ${mxn(py.valor_bajo)} a ${mxn(py.valor_alto)}. Los rendimientos de un año tan bueno para estas emisoras no se repiten necesariamente: es una extrapolación, no una promesa.`]),
    p("Conclusión: si el Reto continuara, esta sería nuestra cartera de partida, por el mejor rendimiento por unidad de riesgo con los mismos instrumentos. La mantendríamos junto a la referencia 1/N y la revisaríamos cada mes, porque la evidencia fuera de muestra aún no la favorece en riesgo. No es asesoría de inversión.")];
}

const portada = [
  new Paragraph({ spacing: { before: 1400, after: 300 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Concurso Finanzas IA — Reto Actinver 2026", bold: true, size: 40, color: ROJO })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 }, children: [new TextRun({ text: "Informe escrito", size: 30 })] }),
  ...[["Nombre del concurso", "Reto Actinver 2026 — Concurso Finanzas IA"],
    ["Nombre del equipo", eq.equipo],
    ["Nombres completos de los integrantes", eq.integrantes && eq.integrantes.join(", ").replace(/, ([^,]+)$/, " y $1")],
    ["Carrera", eq.carrera], ["Matrículas", eq.matriculas && Object.entries(eq.matriculas).map(([n, m]) => `${n}: ${m}`).join("; ")],
    ["Campus", eq.campus], ["Fecha de entrega", eq.fecha_entrega],
    ["Nombre del docente", eq.docente], ["Asignatura", eq.asignatura]].map(([k, v]) =>
    new Paragraph({ spacing: { after: 140 }, children: [b(`${k}: `), v ? new TextRun(v) : pend("completar (dato del equipo; no se inventa)")] })),
  new Paragraph({ children: [new PageBreak()] }),
];

const indice = [h1("Índice"), new TableOfContents("Índice", { hyperlink: true, headingStyleRange: "1-2" }),
  new Paragraph({ children: [new PageBreak()] })];

const resumen = [h1("1. Resumen ejecutivo"),
  p(`Este informe documenta la participación del equipo ${eq.equipo || ""} en el Reto Actinver 2026 (5 de octubre al 13 de noviembre), en el simulador de la plataforma Reto Actinver, con ${mxn(d.capital_inicial)} simulados. La estrategia fue de crecimiento agresivo: semiconductores e inteligencia artificial (Micron, AMD, AMAT y el ETF QQQ) más Grupo México y Alpek. Las decisiones se apoyaron en Actinver Terminal, una herramienta propia construida con IA que optimiza con Markowitz y mide el riesgo; no envía órdenes.`),
  p(`Hallazgos: el portafolio cerró en ${mxn(fin.valor)} (${pct(fin.rend)}) mientras el NAFTRAC subió ${pct(bm?.rendimiento)}. La pérdida se explica por la concentración en tecnología, con MU cerca de la mitad de la cartera durante la corrección del sector. La rotación a consumo y salud llegó tarde. Lección: medir y limitar la concentración antes de buscar rendimiento.`),
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
  p("Capturas iniciales del portal del Reto (primer día de la competencia):"),
  ...captura("p068_0.png", "Figura 1. Portafolio al 5-oct-2026, 15:08: valuación $999,136.55 (corte O07, evidencia E012)."),
  ...captura("p069_0.png", "Figura 2. Detalle de posiciones al 5-oct-2026 (corte O07, evidencia E013)."),
  p(`Observaciones: en el primer día el portafolio pasó de ${mxn(ini.valor)} a ${mxn(d.serie[1]?.valor)}; MU concentraba ${pct(ini.posiciones[0].peso, 1)} del valor, cerca del tope de 50 % del Reto. El 6 y 7 de octubre se vendieron QQQ y AMAT y se compraron NVIDIA, Exxon Mobil y Novavax para ajustar la tesis.`),
  new Paragraph({ children: [new PageBreak()] })];

const seg = [h1("3. Informe de seguimiento intermedio (Entregable 2)"),
  h2("3.1 Resumen del desempeño de la cartera"),
  p("Movimientos realizados entre el 6 y el 31 de octubre (cambios de títulos entre capturas consecutivas del portal):"),
  tabla(["Fecha", "Instrumento", "Operación", "Títulos antes → después"], d.movimientos_octubre.map((m) => [m.fecha, sym(m.instrumento), m.tipo, `${num(m.de)} → ${num(m.a)}`]), [1800, 2000, 1800, 3238]),
  p([b("Valor de la cartera al corte: "), `${mxn(oct.valor)} (${fecha(oct.hora)}). `, b("Rentabilidad acumulada: "), pct(oct.rend), "."]),
  tabla(["Instrumento", "Títulos", "Costo prom.", "Precio", "Valor", "Rend."], oct.posiciones.map((x) => [sym(x.instrumento), num(x.titulos), mxn(x.costo_promedio), mxn(x.precio), mxn(x.valor), pct(x.rend, 1)]), [1300, 1000, 1550, 1550, 1838, 1600]),
  fuente("captura del portal del 30-oct-2026 registrada en la terminal (precios en MXN; SIC convertido por el portal)."),
  ...captura("p114_0.png", "Figura 3. Portafolio al 30-oct-2026, 14:00 (corte O32, evidencia E058)."),
  ...captura("p115_0.png", "Figura 4. Posiciones al 30-oct-2026 (corte O32, evidencia E059)."),
  h2("3.2 Análisis fundamental — Micron Technology (MU)"),
  p(`Se eligió MU por ser la mayor posición. Las razones se calcularon con el reporte anual 10-K del ejercicio terminado el ${fm.ejercicio} (presentado ante la SEC el ${fm.presentado}): ventas de ${usd(fm.ventas)} y utilidad neta de ${usd(fm.utilidad_neta)}.`),
  tabla(["Indicador", "Valor", "Cálculo"], [
    ["Liquidez (razón circulante)", `${fm.razon_circulante.toFixed(2)} veces`, `activo circulante ${usd(fm.activo_circulante)} ÷ pasivo circulante ${usd(fm.pasivo_circulante)}`],
    ["Apalancamiento (pasivo/capital)", `${fm.pasivo_capital.toFixed(2)} veces`, `pasivo total ${usd(fm.pasivos)} ÷ capital contable ${usd(fm.capital)}; deuda de largo plazo ${usd(fm.deuda_largo_plazo)}`],
    ["Operatividad (rotación de activos)", `${fm.rotacion_activos.toFixed(2)} veces`, "ventas ÷ activo total promedio de los dos últimos cierres"],
    ["Rentabilidad: margen neto", pct(fm.margen_neto, 1), "utilidad neta ÷ ventas"],
    ["Rentabilidad: ROE", pct(fm.roe, 1), "utilidad neta ÷ capital contable promedio"],
    ["P/E", `${(t.cierre / fm.bpa_diluido_usd).toFixed(1)} veces`, `cierre de ${num(t.cierre)} USD (${t.hasta}) ÷ utilidad diluida por acción de ${num(fm.bpa_diluido_usd)} USD`],
    ["Crecimiento en ventas", pct(fm.crec_ventas, 1), `ejercicio ${fm.ejercicio.slice(0, 4)} frente a ${fm.ejercicio_anterior.slice(0, 4)}`],
    ["Crecimiento en utilidad neta", pct(fm.crec_utilidad, 1), `de ${usd(fm.utilidad_anterior)} a ${usd(fm.utilidad_neta)}`],
    ["Relación costo-beneficio", pct(fm.bpa_diluido_usd / t.cierre, 1), `rendimiento por utilidades (1 ÷ P/E): por cada peso pagado por la acción, la empresa generó ${(fm.bpa_diluido_usd / t.cierre).toFixed(2)} de utilidad; CETES 28 pagaban ${d.cetes28 ? pct(d.cetes28.valor) : "—"} sin riesgo`]], [2700, 1500, 4638]),
  fuente(`${fm.fuente}, número de acceso ${fm.accn}; cierre de MU guardado por Actinver Terminal (Tiingo/Alpaca).`),
  p("Interpretación: Micron tenía liquidez holgada (más de tres dólares de activo circulante por cada dólar de deuda de corto plazo), apalancamiento bajo y una rentabilidad excepcional por el auge de la memoria para inteligencia artificial; con un P/E cercano a 10 veces, la acción no se veía cara por utilidades. El problema no fue la empresa sino el precio: un negocio cíclico en su punto más alto de utilidades suele cotizar con múltiplos bajos justo antes de una corrección, y la cartera dependía demasiado de esa sola acción."),
  h2("3.3 Análisis técnico — MU, últimos 3 meses"),
  imagen("tecnico_mu.png", 560, 420),
  fuente(`${t.fuente}; ${t.desde} a ${t.hasta}.`),
  tabla(["Indicador", "Valor al " + t.hasta, "Lectura"], [
    ["Cierre", `${num(t.cierre)} USD`, `Variación de 3 meses: ${pct(t.variacion_3m, 1)}`],
    ["Media móvil 20 / 50", `${num(t.sma20)} / ${num(t.sma50)} USD`, t.cierre < t.sma20 && t.sma20 < t.sma50 ? "Precio debajo de ambas medias y la de 20 bajo la de 50: tendencia bajista" : "Tendencia mixta"],
    ["RSI 14 (Wilder)", num(t.rsi14), t.rsi14 < 30 ? "Sobreventa" : t.rsi14 > 70 ? "Sobrecompra" : "Zona neutral, sin sobreventa"],
    ["MACD (12-26-9)", `${num(t.macd)} / señal ${num(t.senal)}`, t.macd < t.senal ? "MACD bajo su señal: impulso negativo" : "MACD sobre su señal: impulso positivo"]], [2600, 2600, 3638]),
  p("La ficha de Actinver (TechRules) del 13-nov-2026 coincide con esta lectura: tendencia de corto y mediano plazo «muy bajista», riesgo «extremo», volatilidad de 73.74 %, beta de 1.80 frente al índice de mercados desarrollados, VaR a una semana de −15.60 % y un retroceso de −32.11 % desde el máximo anual."),
  fuente("Catálogo de fichas Actinver / TechRules, recopilación del 18-nov-2026 (ficha de MU, datos al cierre del 13-nov-2026)."),
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
  ...(d.fx ? [p(`Riesgo cambiario: las emisoras del SIC cotizan en pesos, pero su valor sigue al dólar. Del ${d.fx.inicio[0]} al ${d.fx.fin[0]} el tipo de cambio FIX pasó de ${d.fx.inicio[1].toFixed(4)} a ${d.fx.fin[1].toFixed(4)} pesos por dólar (${pct(d.fx.variacion)}). La depreciación del peso amortiguó en esa proporción la caída en dólares de MU, AMD y NVDA; sin ella, la pérdida del portafolio habría sido mayor. Es la ventaja de diversificar en otra moneda: protege cuando el peso se debilita y resta cuando se fortalece.`), fuente("Banxico, tipo de cambio FIX (SIE), guardado por Actinver Terminal.")] : []),
  imagen("evolucion.png", 560, 252),
  fuente("capturas del portal (34) y cierres EOD de NAFTRAC (EODHD) guardados en Actinver Terminal."),
  h2("4.2 Análisis de resultados por acción"),
  p("Posiciones al cierre: se mantuvieron hasta el final del Reto. La justificación y la conclusión de cada una:"),
  tabla(["Instrumento", "Costo prom.", "Precio final", "Rend.", "Justificación y conclusión"], fin.posiciones.map((x) => [sym(x.instrumento), mxn(x.costo_promedio), mxn(x.precio), pct(x.rend, 1), CONCLUSION[x.instrumento] || "Mantener: posición pequeña de la última semana."]), [1100, 1300, 1300, 900, 4238]),
  fuente("captura final del portal (12-nov-2026)."),
  p("Posiciones vendidas durante el concurso. El precio es el de la última captura en que aparecían, no el de la venta exacta:"),
  tabla(["Instrumento", "Salida", "Costo prom.", "Último precio", "Rend.", "Justificación de la venta"], d.cerradas.map((x) => [sym(x.instrumento), x.salida || "—", mxn(x.costo_promedio), mxn(x.precio), x.rend != null && Math.abs(x.rend) < 5 ? pct(x.rend, 1) : "s/d", VENTA[x.instrumento] || "—"]), [1100, 1100, 1250, 1250, 800, 3338]),
  fuente("capturas del portal registradas en Actinver Terminal; s/d: el costo registrado del fondo (1 título) no es consistente."),
  p(`Posiciones cerradas durante el concurso: ${cerradas.map(sym).join(", ")}. La salida de MU, NVDA, AMD y Grupo México del 10 y 11 de noviembre liberó efectivo que se reinvirtió en consumo básico (FEMSA, KOF, Arca Continental, Target) y salud (Merck, Eli Lilly, AbbVie, Moderna), con Chevron y Exxon en energía.`),
  vineta([b("Ganadoras: "), "Exxon Mobil (+7.5 % sobre costo), Arca Continental y Chevron (≈ +2 %)."]),
  vineta([b("Perdedoras: "), "Novavax (−19.3 %) y Moderna (−8.1 %). En tecnología, MU era la posición de mayor peso cuando cayó el sector (ver la caída del 3 al 5 de noviembre en la serie del anexo C)."]),
  h2("4.3 Capturas y evidencias"),
  ...captura("p131_0.png", "Figura 5. Portafolio final al 12-nov-2026, 22:54: valuación $784,440.07, −21.56 % (corte O40, evidencia E075)."),
  ...captura("p132_0.png", "Figura 6. Posiciones finales al 12-nov-2026 (corte O40, evidencia E076)."),
  ...captura("p133_0.png", "Figura 7. Continuación de las posiciones finales (corte O40, evidencia E077)."),
  ...captura("p124_0.png", "Figura 8. Portafolio el 10-nov-2026 tras iniciar la rotación (corte O37, evidencia E068)."),
  ...captura("p126_0.png", "Figura 9. Portafolio el 11-nov-2026, 10:36 (corte O38, evidencia E070)."),
  p("Nota: las pantallas del portal no muestran el nombre del equipo; el código y el nickname se anotan en el anexo B."),
  p("La gráfica general del comportamiento del portafolio está en la sección 4.1. El video del proyecto, en sus cuatro versiones, está en el anexo F con enlace y código QR."),
  h2("4.4 Reflexión final"),
  vineta([b("Decisiones clave: "), "concentrar casi 50 % en MU al inicio (mayor impacto negativo) y rotar a consumo y salud en la última semana (redujo la volatilidad, pero tarde)."]),
  vineta([b("Errores: "), "no limitar el peso por emisora por debajo del tope del Reto; reaccionar a la caída del sector después y no antes; tomar posiciones pequeñas de bajo valor informativo (SLV, ACTDUAL, PFE)."]),
  vineta([b("Lecciones: "), "el riesgo de concentración se mide antes de buscar rendimiento; comparar siempre contra una referencia simple (1/N o el índice); un modelo sin ventaja demostrada fuera de muestra no debe decidir solo."]),
  vineta([b("Aprendizaje con IA: "), "construimos Actinver Terminal con asistentes de IA (Claude y Codex): optimización de Markowitz, VaR/CVaR, validación fuera de muestra y registro de cada captura. La IA aceleró el análisis, pero también mostró sus límites: ningún modelo superó a la cartera equiponderada fuera de muestra, y así lo declaramos."]),
  ...(eq.constancias ? [vineta([b("Formación: "), `durante el Reto completamos ${eq.constancias.cursos.length} cursos de ${eq.constancias.emisor} (análisis técnico, ETFs, fondos, portafolios y planeación financiera); las constancias están en el anexo D.`])] : []),
  h2("4.5 Nota sobre el uso de la inteligencia artificial"),
  p("La inteligencia artificial fue una herramienta de apoyo, no la autora del trabajo. El equipo definió el perfil de inversión, eligió las emisoras, decidió cada compra y venta, y la capturó a mano en el simulador del Reto; ninguna operación la ejecutó una IA. Los asistentes (Claude y Codex) nos ayudaron a programar Actinver Terminal, a calcular indicadores y a ordenar los datos y la redacción."),
  p("Todas las cifras de este informe se comprobaron contra las capturas del portal y fuentes oficiales (SEC EDGAR, Banxico y la ficha de Actinver), y las interpretaciones, conclusiones y errores son responsabilidad del equipo. Usamos la IA para trabajar más rápido y con más orden, no para sustituir nuestro criterio."),
  ...propuesta(),
  new Paragraph({ children: [new PageBreak()] })];

// APA 7: orden alfabético, sangría francesa y cursivas marcadas con *…*.
const refs = [h1("5. Referencias"),
  ...["Actinver. (2026). *Reto Actinver 2026: bases y mecánica*. https://www.retoactinver.com/web/reto-actinver/bases-y-mecanica",
    "DeMiguel, V., Garlappi, L., & Uppal, R. (2009). Optimal versus naive diversification: How inefficient is the 1/N portfolio strategy? *The Review of Financial Studies, 22*(5), 1915–1953. https://doi.org/10.1093/rfs/hhm075",
    "Ledoit, O., & Wolf, M. (2004). Honey, I shrunk the sample covariance matrix. *The Journal of Portfolio Management, 30*(4), 110–119. https://doi.org/10.3905/jpm.2004.110",
    "Markowitz, H. (1952). Portfolio selection. *The Journal of Finance, 7*(1), 77–91. https://doi.org/10.2307/2975974",
    "Micron Technology, Inc. (2026). *Form 10-K for the fiscal year ended September 3, 2026*. U.S. Securities and Exchange Commission. https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000723125",
    "TechRules & Actinver. (2026). *Ficha de análisis de Micron Technology (MU), datos al cierre del 13 de noviembre de 2026* [Ficha de instrumento]. Catálogo de instrumentos del Reto Actinver.",
    "U.S. Securities and Exchange Commission. (2026). *EDGAR: Company filings*. https://www.sec.gov/edgar",
    "Wilder, J. W. (1978). *New concepts in technical trading systems*. Trend Research."]
    .map((x) => new Paragraph({ spacing: { after: 120 }, indent: { left: 720, hanging: 720 },
      children: x.split("*").map((t, k) => new TextRun({ text: t, italics: k % 2 === 1 })) })),
  new Paragraph({ children: [new PageBreak()] })];

const anexos = [h1("Anexos"),
  h2("A. Capturas completas de la plataforma Actinver"),
  p("El expediente completo está en la «Cronología integral de mi portafolio» (277 páginas): 40 cortes fechados del 30-sep al 12-nov-2026, con 77 imágenes originales del portal (evidencias E001 a E077), el calendario diario y las fichas de los 31 instrumentos. Aquí se incluyen las capturas del 12-nov por la mañana, antes del cierre final."),
  ...captura("p128_0.png", "Figura A1. Portafolio al 12-nov-2026, 09:15 (corte O39, evidencia E072)."),
  ...captura("p129_0.png", "Figura A2. Posiciones al 12-nov-2026, 09:15 (corte O39, evidencia E073)."),
  ...captura("p130_0.png", "Figura A3. Continuación de las posiciones al 12-nov-2026, 09:15 (corte O39, evidencia E074)."),
  h2("B. Códigos de equipo y nickname"),
  p([b("Nombre del equipo: "), eq.equipo || pend("nombre del equipo")]),
  p([b("Nickname en el Reto: "), eq.nickname || pend("nickname del Reto")]),
  p([b("Código del equipo: "), eq.codigo || pend("código del equipo en el Reto")]),
  ...(eq.matriculas ? [tabla(["Integrante", "Matrícula"], Object.entries(eq.matriculas), [5838, 3000])] : []),
  h2("C. Serie del valor del portafolio (última captura de cada día)"),
  tabla(["Fecha", "Valor (MXN)", "Rend. acumulado"], d.serie.map((x) => [x.fecha, mxn(x.valor), pct(x.valor / d.capital_inicial - 1)]), [2800, 3200, 2838]),
  fuente("capturas del portal registradas en Actinver Terminal (data/archivo/reto-actinver-2026-20261117.db)."),
  h2("D. Evidencias de asesorías y cursos"), ...(eq.constancias ? [
    p(`Durante el Reto el equipo tomó cursos de ${eq.constancias.emisor}. ${eq.constancias.titular} obtuvo ${eq.constancias.cursos.length} constancias:`),
    tabla(["#", "Curso", "Certificado n.º"], eq.constancias.cursos.map(([c, n], i) => [String(i + 1), c, `n.º ${n}`]), [600, 6238, 2000]),
    fuente(`constancias en PDF emitidas por ${eq.constancias.emisor}; no muestran la fecha de emisión.`),
    cuadricula(eq.constancias.cursos.map(([c], k) => [`c${k}.png`, `${k + 1}. ${c}`]))]
    : [p("Sección opcional según el formato; el equipo no incluye evidencias de asesorías.")]),
  h2("E. Herramienta de apoyo"), p("Actinver Terminal (proyecto independiente, sin afiliación con Grupo Actinver): https://github.com/Maikolv/help-quote-terminal. Solo informa y simula; no envía órdenes."),
  ...(VIDEOS.length ? [h2("F. Videos del proyecto"),
  p(`El video presenta el proyecto con la estética de la terminal: grabaciones de Actinver Terminal en la computadora del equipo (solo lectura) y las gráficas del informe (datos reales del Reto). ${VERSION ? "Esta versión del informe enlaza el video" + (process.argv[2] === "4" ? " con las voces de los cuatro integrantes" : " narrado por dos integrantes") + ", en formato horizontal para YouTube y vertical para TikTok." : "Hay dos versiones de voz, cada una en formato horizontal para YouTube y vertical para TikTok."} Escanea el código QR o abre el enlace.`),
  tablaVideos(),
  fuente(`YouTube «no listado»: lo ve cualquier persona con el enlace. TikTok «privado»: solo lo ve la cuenta que lo publicó; los archivos MP4 también están en ${eq.drive ? `la carpeta de Google Drive del equipo: ${eq.drive}` : "el ZIP"}.`)] : [])];

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
