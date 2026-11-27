// Guion y notas para exponer el proyecto del concurso «Finanzas en la era de la IA», con las cifras reales del informe.
// Datos: data/medios/informe/datos.json, fundamentales_mu.json, data/medios/propuesta/idoneo.json y equipo.json (privados).
//   node scripts/guion_exposicion.cjs   → entregables/Guion_Exposicion_Lynx_Market.docx
"use strict";
const fs = require("node:fs"), path = require("node:path");
const { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  AlignmentType, LevelFormat, PageBreak } = require("docx");

const RAIZ = path.resolve(__dirname, "..");
const MED = path.join(RAIZ, "data", "medios");
const leer = (...p) => JSON.parse(fs.readFileSync(path.join(MED, ...p), "utf8"));
const d = leer("informe", "datos.json"), fm = leer("informe", "fundamentales_mu.json"), id = leer("propuesta", "idoneo.json");
const eq = fs.existsSync(path.join(MED, "equipo.json")) ? leer("equipo.json") : {};
const [MIGUEL, DANIELA, VALERIA, CAMILA] = ["Miguel", "Daniela", "Valeria", "Camila"];
const EQUIPO = eq.equipo || "Lynx Market";
const SALIDA = path.join(RAIZ, "entregables", "Guion_Exposicion_Lynx_Market.docx");

const FUENTE = "Century Gothic", ROJO = "B3261E", GRIS = "4A505A";
const pct = (x, n = 1) => `${(x * 100).toFixed(n)} %`;
const mxn = (x) => `$${Number(x).toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const sym = (s) => s.split(":")[1];
const t = d.tecnico_mu, r = d.riesgo, fin = d.final, oct = d.corte_octubre, bm = d.benchmark;
const oos = id.fuera_de_muestra, m = id.metricas, n1 = id.metricas_1n;
const pesosId = [...id.activos].filter((a) => a.peso > 0.0005).sort((a, b) => b.peso - a.peso);

const p = (texto, o = {}) => new Paragraph({ spacing: { after: 100 }, alignment: AlignmentType.JUSTIFIED,
  children: (Array.isArray(texto) ? texto : [texto]).map((x) => typeof x === "string" ? new TextRun(x) : x), ...o });
const b = (x) => new TextRun({ text: x, bold: true });
const i = (x) => new TextRun({ text: x, italics: true, color: GRIS });
const h1 = (x) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(x)] });
const h2 = (x) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(x)] });
const v = (texto) => new Paragraph({ numbering: { reference: "v", level: 0 }, spacing: { after: 60 },
  children: (Array.isArray(texto) ? texto : [texto]).map((x) => typeof x === "string" ? new TextRun(x) : x) });
const dice = (quien, texto) => new Paragraph({ spacing: { after: 120 }, indent: { left: 360 },
  border: { left: { style: BorderStyle.SINGLE, size: 18, color: ROJO, space: 8 } },
  children: [new TextRun({ text: `${quien}: `, bold: true, color: ROJO }), new TextRun({ text: `«${texto}»` })] });
const ANCHO = 9360;
function tabla(cab, filas, anchos) {
  const borde = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
  const bordes = { top: borde, bottom: borde, left: borde, right: borde };
  const celda = (x, k, fondo) => new TableCell({ width: { size: anchos[k], type: WidthType.DXA }, borders: bordes,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    shading: fondo ? { fill: "1F2229", type: ShadingType.CLEAR, color: "auto" } : undefined,
    children: [new Paragraph({ children: [new TextRun({ text: x, size: 18, bold: !!fondo, color: fondo ? "FFFFFF" : undefined })] })] });
  return new Table({ width: { size: ANCHO, type: WidthType.DXA }, columnWidths: anchos, rows: [
    new TableRow({ tableHeader: true, children: cab.map((x, k) => celda(x, k, true)) }),
    ...filas.map((f) => new TableRow({ cantSplit: true, children: f.map((x, k) => celda(String(x), k)) }))] });
}

// Bloques de la exposición: minuto, quién, qué decir, qué mostrar y notas para responder.
const BLOQUES = [
  { tit: "1. Apertura y objetivo", min: "0:00–1:00", quien: MIGUEL,
    dice: `Somos el equipo ${EQUIPO}. En el Reto Actinver 2026 administramos un millón de pesos simulados del 5 de octubre al 12 de noviembre. Nuestro objetivo fue decidir con datos y no con corazonadas, y para eso construimos con inteligencia artificial nuestra propia herramienta: Actinver Terminal.`,
    muestra: "Portada del informe y, en la terminal, la barra superior con «Operaciones reales: deshabilitadas».",
    notas: ["Aclarar desde el inicio: proyecto escolar, no afiliado a Grupo Actinver; la terminal solo informa y simula, no envía órdenes.",
      "Mencionar la estructura: plan inicial, seguimiento, análisis, resultado y propuesta final."] },
  { tit: "2. Cómo usamos la IA", min: "1:00–2:30", quien: DANIELA,
    dice: "La IA fue nuestra herramienta, no la autora. Con los asistentes Claude y Codex programamos la terminal: descarga datos de fuentes gratuitas y legales, calcula indicadores, optimiza portafolios con Markowitz y mide el riesgo. Nosotros definimos el perfil, elegimos las emisoras, decidimos cada compra y venta y las capturamos a mano en el simulador.",
    muestra: "Datos y fuentes: cada proveedor (Banxico, SEC, EODHD, Tiingo, Alpaca) con su retraso y vigencia.",
    notas: ["Si preguntan qué hizo la IA: escribió y probó el código, ordenó datos y redacción. Qué hizo el equipo: criterios, decisiones, captura y revisión de cada cifra.",
      "Ninguna orden la ejecutó una IA; las cifras del informe se comprobaron contra las capturas del portal."] },
  { tit: "3. Plan de inversión inicial (Entregable 1)", min: "2:30–3:45", quien: VALERIA,
    dice: `Elegimos seis instrumentos de tres sectores: semiconductores (Micron, AMD y Applied Materials), el ETF del Nasdaq y dos emisoras mexicanas, Grupo México y Alpek. Nuestro perfil fue agresivo, con horizonte de seis semanas. Micron pesaba ${pct(d.inicial.posiciones[0].peso)}, casi en el tope del Reto de 50 % por emisora.`,
    muestra: "Figura de distribución inicial y «Mis portafolios» con el perfil Agresivo.",
    notas: [`Distribución: ${d.inicial.posiciones.map((x) => `${sym(x.instrumento)} ${pct(x.peso)}`).join(", ")}.`,
      "Justificación: auge de la memoria para IA (MU), exposición al cobre en dólares (GMEXICO) y diversificación con ETF.",
      "Reconocer la debilidad: la concentración en tecnología fue la decisión de mayor riesgo."] },
  { tit: "4. Seguimiento intermedio (Entregable 2)", min: "3:45–4:45", quien: DANIELA,
    dice: `Registramos ${d.capturas} capturas del portal. Entre el 6 y el 31 de octubre hicimos ${d.movimientos_octubre.length} movimientos: entraron NVIDIA, Exxon y Novavax, y salieron el ETF y Applied Materials. Al 30 de octubre la cartera valía ${mxn(oct.valor)}, ${pct(oct.rend, 2)}.`,
    muestra: "Tabla de movimientos del informe (sección 3.1).", notas: ["Cada movimiento se dedujo comparando capturas consecutivas; no hay operaciones inventadas."] },
  { tit: "5. Análisis fundamental y técnico de Micron", min: "4:45–6:15", quien: VALERIA,
    dice: `Micron tenía liquidez holgada, con razón circulante de ${fm.razon_circulante.toFixed(2)}; poco apalancamiento, ${fm.pasivo_capital.toFixed(2)} de pasivo por peso de capital; margen neto de ${pct(fm.margen_neto)} y ROE de ${pct(fm.roe)}. Su P/E era de ${(t.cierre / fm.bpa_diluido_usd).toFixed(1)} veces. Pero técnicamente el precio, ${t.cierre.toFixed(2)} dólares, cayó debajo de sus medias de 20 y 50 días, el MACD quedó bajo su señal y el RSI en ${t.rsi14.toFixed(0)}: tendencia bajista sin sobreventa.`,
    muestra: "En la terminal: Ficha técnica de MU (análisis técnico con medias, RSI, MACD y Bollinger) y la figura técnica del informe.",
    notas: ["Mensaje clave: la empresa era excelente, el problema fue el precio y la concentración (negocio cíclico en su punto alto).",
      "Fuente fundamental: 10-K de la SEC (EDGAR); técnico: cierres diarios guardados por la terminal."] },
  { tit: "6. Riesgo y resultado final (Entregable 3)", min: "6:15–7:30", quien: CAMILA,
    dice: `El portafolio cerró en ${mxn(fin.valor)}, ${pct(fin.rend, 2)}, mientras el NAFTRAC subió ${pct(bm.rendimiento, 2)}. La desviación estándar diaria fue ${pct(r.desv_diaria, 2)} y el VaR histórico al 95 % de ${pct(r.var95_historico_diario, 2)}: en 19 de cada 20 días la pérdida no pasó de ese porcentaje. La volatilidad venía de concentrar casi la mitad del dinero en una acción.`,
    muestra: "Figura de evolución frente a NAFTRAC; en la terminal, Propuestas con escenarios y caída máxima.",
    notas: [`Peor día: ${pct(r.peor_dia, 2)}. Diferencia contra el mercado: ${((fin.rend - bm.rendimiento) * 100).toFixed(2)} puntos.`,
      "El VaR usa solo 25 rendimientos diarios: es aproximado y así lo decimos."] },
  { tit: "7. Portafolio idóneo con la plantilla de Markowitz", min: "7:30–9:00", quien: MIGUEL,
    dice: `Con el último registro hicimos lo que habríamos hecho desde el inicio: el generador de la terminal tomó nuestros 12 instrumentos, los completó con los mejores del Ranking que no se mueven igual y el Solver de Markowitz buscó el máximo Sharpe con un tope de ${pct(id.especificacion.peso_max, 0)} por emisora. El riesgo anual baja a ${pct(m.riesgo)} frente a ${pct(n1.riesgo)} de repartir en partes iguales.`,
    muestra: "Mis portafolios → «Portafolio idóneo» (id 7): Solver, frontera eficiente y prueba fuera de muestra; Excel con Solver cargado.",
    notas: [`Pesos: ${pesosId.map((a) => `${sym(a.id)} ${pct(a.peso)}`).join(", ")}.`,
      `Fuera de muestra (${oos.inicio} a ${oos.fin}): rindió ${pct(oos.propuesta.rend_total)} contra ${pct(oos["1/N"].rend_total)} de 1/N, pero con Sharpe ${oos.propuesta.sharpe.toFixed(2)} contra ${oos["1/N"].sharpe.toFixed(2)}. Decirlo con honestidad: la ventaja no está demostrada.`,
      "Se probaron 36 configuraciones; por eso el resultado elegido es algo optimista (sesgo de selección)."] },
  { tit: "8. Seguimiento con Telegram", min: "9:00–9:45", quien: MIGUEL,
    dice: "No tenemos que vigilar la pantalla todo el día: la terminal nos avisa por Telegram cuando hay un movimiento significativo, como una caída fuerte de una posición, o cuando el plan indica que algo debe cambiar. Solo avisa; la decisión siempre es nuestra.",
    muestra: "Alertas: umbrales (deriva ≥ 5 pp, stop −8 %, toma de utilidad +15 %, caída desde máximo −10 %), canal de Telegram configurado y monitor en la nube activo.",
    notas: ["Si marcan el portafolio idóneo como principal, el plan de acción y Telegram comparan contra sus pesos."] },
  { tit: "9. Reflexión y cierre", min: "9:45–11:00", quien: CAMILA,
    dice: "Aprendimos que el riesgo de concentración se mide antes de buscar rendimiento, que siempre hay que comparar contra una referencia simple y que la IA acelera el análisis pero no adivina el futuro. Ningún modelo superó con claridad a repartir el dinero en partes iguales, y lo declaramos.",
    muestra: "Video del proyecto (4 min) si hay tiempo, o su versión corta; enlace en el anexo F.",
    notas: ["Errores: tope por emisora demasiado alto, reacción tardía a la caída del sector, posiciones pequeñas sin valor informativo (SLV, ACTDUAL, PFE).",
      "Cerrar con el aviso: no es asesoría de inversión."] },
];

const PREGUNTAS = [
  ["¿Por qué perdieron si usaron IA?", "Porque la decisión de concentrar casi 50 % en Micron fue nuestra y el sector cayó. La IA midió ese riesgo; no lo evitamos a tiempo. Por eso la propuesta final limita cada emisora a 10 %."],
  ["¿Qué es el Sharpe?", "Rendimiento por encima de la tasa libre de riesgo (CETES 28) por cada unidad de riesgo (desviación estándar). Markowitz busca el portafolio con el Sharpe más alto: el tangente."],
  ["¿Qué significa el VaR de 5.27 %?", "Con 95 % de confianza, la pérdida de un día no superó 5.27 % del valor del portafolio, según la historia del Reto."],
  ["¿Qué es 1/N y por qué compararse con él?", "Repartir el dinero en partes iguales. Es la referencia que un optimizador debe superar fuera de muestra (DeMiguel, Garlappi y Uppal, 2009)."],
  ["¿Qué es la prueba fuera de muestra?", "Calcular los pesos solo con datos previos y medir el resultado en meses que el modelo no vio, rebalanceando cada mes con comisiones."],
  ["¿Qué hace la terminal con Telegram?", "Envía avisos (pérdida del día, deriva de pesos, stop, toma de utilidad, cambios del plan). No ejecuta operaciones."],
  ["¿Las cifras son reales?", "Sí: salen de 34 capturas del portal del Reto, de la SEC (10-K de Micron), de Banxico (FIX y CETES) y de cierres de mercado guardados por la terminal."],
  ["¿Por qué Ledoit-Wolf no es la elegida?", "La plantilla de Excel usa covarianza muestral; elegimos el mismo cálculo para que el Solver del Excel y la terminal coincidan. Ledoit-Wolf queda como comparación."],
];

const RUBRICA = [
  ["Portada, índice y resumen ejecutivo", "Informe, portada y sección 1"],
  ["Plan inicial: 5+ acciones, sector, perfil, horizonte, distribución", "Sección 2 (tabla, gráfica circular, capturas)"],
  ["Seguimiento 6–31 oct: movimientos, valor, rentabilidad", "Sección 3.1"],
  ["Análisis fundamental (liquidez, apalancamiento, operatividad, rentabilidad, P/E)", "Sección 3.2 (10-K de la SEC)"],
  ["Análisis técnico (velas/líneas 3 meses, RSI, medias, MACD)", "Sección 3.3"],
  ["Resultado final, riesgo (desviación y VaR) y comparación contra el mercado", "Sección 4.1 (NAFTRAC)"],
  ["Resultados por acción y capturas con evidencia", "Secciones 4.2 y 4.3; anexos A y C"],
  ["Reflexión y aprendizaje con IA", "Secciones 4.4 y 4.5"],
  ["Propuesta de mejora con Teoría Moderna de Portafolios", "Sección 4.6 y Excel con Solver"],
  ["Referencias APA (mínimo 3)", "Sección 5 (8 fuentes)"],
  ["Anexos: capturas, códigos, cursos, video", "Anexos A–F"],
];

const cont = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [new TextRun({ text: "Guion y notas para la exposición", bold: true, size: 40, color: ROJO })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [new TextRun({ text: `Equipo ${EQUIPO} · Concurso «Finanzas en la era de la IA» · Reto Actinver 2026`, size: 22, color: GRIS })] }),
  h1("Cómo usar este guion"),
  v("Duración sugerida: 11 minutos más 4 de preguntas. Cada bloque dice quién habla, qué decir, qué mostrar y notas para responder."),
  v("Antes de exponer: abrir Actinver Terminal (start.bat, http://127.0.0.1:8765) en las pestañas Mis portafolios, Ficha técnica (MU), Propuestas y Alertas; tener el PDF del informe y el video listos."),
  v("Plan B: si la terminal o la red fallan, usar el video (muestra las mismas pantallas grabadas en la terminal) y las figuras del informe."),
  v("Hablar con cifras exactas: las de este documento salen del archivo del Reto y de la terminal, igual que el informe."),
  h1("Cifras clave (tarjeta de apoyo)"),
  tabla(["Concepto", "Valor"], [
    ["Capital simulado", "$1,000,000.00 (5-oct al 12-nov-2026)"],
    ["Valor al 30-oct", `${mxn(oct.valor)} (${pct(oct.rend, 2)})`],
    ["Valor final", `${mxn(fin.valor)} (${pct(fin.rend, 2)})`],
    ["NAFTRAC (mercado mexicano)", pct(bm.rendimiento, 2)],
    ["Desviación diaria / VaR 95 % 1 día", `${pct(r.desv_diaria, 2)} / ${pct(r.var95_historico_diario, 2)}`],
    ["Peor día", pct(r.peor_dia, 2)],
    ["Micron: cierre, SMA 20/50, RSI", `${t.cierre.toFixed(2)} USD, ${t.sma20.toFixed(0)}/${t.sma50.toFixed(0)}, ${t.rsi14.toFixed(1)}`],
    ["Portafolio idóneo: σ anual, Sharpe", `${pct(m.riesgo)}, ${m.sharpe.toFixed(2)}`],
    ["Fuera de muestra: idóneo vs 1/N (Sharpe)", `${oos.propuesta.sharpe.toFixed(2)} vs ${oos["1/N"].sharpe.toFixed(2)}`],
    ["CETES 28 (tasa libre de riesgo)", pct(d.cetes28.valor, 2)]], [4300, 5060]),
  new Paragraph({ children: [new PageBreak()] }),
  h1("Guion por bloque"),
  ...BLOQUES.flatMap((x) => [h2(`${x.tit} · ${x.min} · ${x.quien}`), dice(x.quien, x.dice),
    p([b("Mostrar: "), x.muestra]), ...x.notas.map((n) => v([i("Nota: "), n]))]),
  new Paragraph({ children: [new PageBreak()] }),
  h1("Cómo usamos la IA para construir los portafolios"),
  p("Explicación para la exposición y para preguntas. Resume el proceso de principio a fin:"),
  v([b("1. Construcción de la herramienta. "), "Con Claude y Codex programamos Actinver Terminal (FastAPI, SQLite y una interfaz web local). El código tiene pruebas automáticas y corre solo en nuestra computadora (127.0.0.1)."]),
  v([b("2. Datos con procedencia. "), "La terminal descarga cierres y datos de fuentes gratuitas y legales (Banxico, SEC EDGAR, EODHD, Tiingo, Alpaca, FRED) y marca cada precio como vigente, retrasado o sin dato; nunca inventa un precio."]),
  v([b("3. Selección de candidatos. "), "El Ranking ordena el universo por rendimiento ajustado, estabilidad, liquidez y capitalización; el generador evita instrumentos que se mueven casi igual (correlación ≤ 0.85)."]),
  v([b("4. Optimización de Markowitz. "), "Con rendimientos y covarianzas de 252 sesiones, el Solver busca el máximo Sharpe (portafolio tangente) usando CETES 28 como tasa libre, con topes por emisora. Es el mismo cálculo que el Excel con Solver."]),
  v([b("5. Validación honesta. "), "Prueba fuera de muestra frente a 1/N con rebalanceo mensual y comisiones; si no hay ventaja demostrada, la terminal lo dice."]),
  v([b("6. Riesgo y seguimiento. "), "VaR, CVaR, desviación, caída máxima y contribución al riesgo por emisora; avisos por Telegram ante movimientos significativos."]),
  v([b("7. Decisión humana. "), "El equipo decide y captura cada operación a mano en el simulador del Reto; la terminal nunca envía órdenes."]),
  h2("Teoría que conviene dominar"),
  v([b("Teoría Moderna de Portafolios (Markowitz, 1952): "), "combinar activos poco correlacionados reduce el riesgo para un mismo rendimiento esperado; la frontera eficiente reúne los mejores portafolios posibles."]),
  v([b("Índice de Sharpe: "), "(E(r) − r_f) / σ. El portafolio tangente maximiza el Sharpe; la línea de asignación de capital une r_f con ese portafolio."]),
  v([b("Diversificación ingenua 1/N: "), "referencia difícil de superar porque no depende de estimar rendimientos (DeMiguel et al., 2009)."]),
  v([b("Ledoit-Wolf: "), "estimación de la covarianza menos sensible al ruido cuando hay pocos datos."]),
  v([b("VaR histórico: "), "percentil 5 de los rendimientos diarios: la pérdida que no se supera 19 de cada 20 días."]),
  h2("Ética y límites"),
  v("La IA no sustituye el criterio: sus resultados se verifican contra fuentes oficiales."),
  v("Un año excepcional para estas emisoras infla los rendimientos esperados: son extrapolaciones, no pronósticos."),
  v("No es asesoría de inversión; es un proyecto escolar independiente, sin afiliación con Grupo Actinver."),
  new Paragraph({ children: [new PageBreak()] }),
  h1("Preguntas probables y respuestas"),
  tabla(["Pregunta", "Respuesta breve"], PREGUNTAS, [3200, 6160]),
  h1("Lista de verificación contra la plantilla"),
  tabla(["Requisito", "Dónde está"], RUBRICA, [5200, 4160]),
  h1("Antes de entregar"),
  v("Subir los dos videos MP4 a la carpeta «Videos del proyecto» de Google Drive (y, si se desea, a YouTube y TikTok)."),
  v("Enviar a la docente el enlace de la carpeta de Drive con el informe (Docs y PDF), el Excel, el guion del video, las constancias y los videos."),
  v("Ensayar una vez con cronómetro; cada integrante debe poder explicar el Sharpe, el VaR y la prueba fuera de muestra."),
];

const doc = new Document({
  creator: `Equipo ${EQUIPO}`, title: "Guion y notas para la exposición",
  styles: { default: { document: { run: { font: FUENTE, size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 30, bold: true, color: ROJO, font: FUENTE }, paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 24, bold: true, color: "15171C", font: FUENTE }, paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } }] },
  numbering: { config: [{ reference: "v", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1300, right: 1440, bottom: 1300, left: 1440 } } }, children: cont }],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(SALIDA, buf); console.log(SALIDA); });
