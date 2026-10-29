// Guía al inicio de cada sección: qué es, cómo usarla y qué significa lo que muestra. La cargan las cuatro páginas
// (terminal, Oficina, Laboratorio de bots y Cuaderno); tests/guias.test.mjs comprueba que ninguna sección quede sin guía.
export const GUIAS = {
  'panel-resumen': {
    titulo: 'Plan de acción',
    que: 'Lo que conviene revisar hoy con su cuenta del Reto: comprar, vender, mantener o «decisión pendiente» por instrumento, con cantidad, precio de referencia, fuente, motivo e invalidación.',
    pasos: ['Registre primero su cuenta en «Mi portafolio Actinver»; sin captura reciente, todo queda como decisión pendiente.',
      'Lea cada fila: acción, cantidad, precio límite sugerido y por qué.',
      'Verifique el precio en el portal del Reto y capture usted la orden; la terminal no envía nada.',
      'Si algo no le convence, pregunte al Asistente o revise Propuestas y Riesgo.'],
    terminos: [['Decisión pendiente', 'Falta un dato confiable (captura, precio vigente o regla) para proponer algo.'],
      ['Invalidación', 'Condición que anula la sugerencia (p. ej., el precio se movió más de 1 %).'],
      ['Precio de referencia', 'Último precio disponible con su fuente y hora; no es la cotización en vivo de la BMV.']],
  },
  'panel-cartera': {
    titulo: 'Mi portafolio Actinver',
    que: 'Su cuenta del Reto tal como la muestra el portal, más el registro manual de la terminal. Es la base con la que se comparan el plan y las propuestas.',
    pasos: ['En el portal, copie el recuadro de Portafolio y la tabla de Acciones (o suba las capturas de pantalla).',
      'Péguelo o súbalo aquí y revise la vista previa; nada se guarda hasta que confirme.',
      'Use «Registrar una operación» o «Importar desde archivo» solo si quiere llevar un registro propio.'],
    terminos: [['Valuación total', 'Inversiones más poder de compra, según el portal.'],
      ['Poder de compra', 'Efectivo disponible para comprar.'],
      ['Captura vigente', 'La última captura confirmada; si es vieja, el plan compara contra una cartera desactualizada.']],
  },
  'panel-portafolios': {
    titulo: 'Mis portafolios',
    que: 'Generador de portafolios con Markowitz y vistas propias opcionales de Black-Litterman, aparte de su cuenta del Reto. Se recalcula con cada cambio y sugiere mejoras.',
    pasos: ['Elija un perfil (Conservador, Moderado, Crecimiento o Agresivo).',
      'Ajuste qué instrumentos considerar, cuántos y el tope por instrumento; fije los que usted quiera.',
      'Si tiene una hipótesis propia, agregue una vista anual y su confianza; después revise la prueba fuera de muestra frente a 1/N.',
      'Aplique las sugerencias con un clic y revise los supuestos antes de guardar.',
      'Guarde la propuesta con un nombre y, si quiere, descárguela en Excel.'],
    terminos: [['E(r) y σ', 'Rendimiento esperado anual y riesgo (volatilidad anual) estimados con la historia.'],
      ['Sharpe', 'Rendimiento por encima de la tasa libre de riesgo por cada unidad de riesgo.'],
      ['1/N', 'Repartir en partes iguales: la referencia que un optimizador debe superar.'],
      ['Ledoit-Wolf', 'Una estimación de la covarianza menos sensible al ruido de pocos datos.'],
      ['Sector', 'Acciones de EE. UU.: grupo SIC de la SEC. ETF: el sector que declara su nombre oficial. Las emisoras BMV y los ETF amplios no tienen sector todavía (la lista oficial de la BMV no se puede leer de forma automática) y no cuentan para el tope por sector.']],
  },
  'panel-propuestas': {
    titulo: 'Propuestas',
    que: 'Las carteras que calcula la terminal: solo acciones, o acciones con ETF y fondos, cada una con tres lentes.',
    pasos: ['Elija el universo (solo acciones o con ETF y fondos).',
      'Elija la lente: máximo rendimiento, ajuste a su perfil o máxima puntuación.',
      'Compare pesos, riesgo y la diferencia con su cartera; use «Simular cambio» para ver el efecto sin enviar nada.'],
    terminos: [['Máximo rendimiento', 'La más agresiva: busca la mayor ganancia esperada y muestra su riesgo.'],
      ['Ajuste a su perfil', 'Respeta su perfil, horizonte y topes de «Reto y perfil».'],
      ['Máxima puntuación', 'Elige con la primera mitad de la validación y se reporta con la segunda.']],
  },
  'panel-alertas': {
    titulo: 'Alertas',
    que: 'Avisos que la terminal genera cuando se cumple una condición: diferencia con el portal, pérdida del día, datos vencidos o una propuesta que cambió.',
    pasos: ['Revise la lista; las nuevas aparecen arriba y en el contador de la pestaña.',
      'Pulse «Enviar aviso de prueba» para comprobar Telegram o el escritorio.',
      'Vea el estado del monitor en la nube si lo tiene configurado.'],
    terminos: [['Enfriamiento', 'Tiempo de espera antes de repetir una misma alerta.'],
      ['Horario', 'Fuera del horario de la BMV no se notifica.']],
  },
  'panel-perfil': {
    titulo: 'Reto y perfil',
    que: 'Las reglas del Reto y su perfil de inversión. Definen qué es «mejor» para usted en propuestas y plan.',
    pasos: ['Revise las reglas y fechas del Reto.',
      'Elija perfil de riesgo, horizonte, capital, topes por activo y por dólar, y el criterio del plan.',
      'Guarde: las propuestas se recalculan solas.'],
    terminos: [['Peso máximo por activo', 'Tope de una sola emisora en la cartera (el Reto exige ≤ 50 %).'],
      ['Exposición a dólar', 'Parte de la cartera en emisoras del SIC, cotizadas en dólares en su bolsa de origen.']],
  },
  'panel-mercado': {
    titulo: 'Mercado',
    que: 'Panorama con widgets gratuitos de TradingView: índices, divisas, mapas de calor, calendario y noticias. Son datos de TradingView, con su retraso; no alimentan ningún cálculo de la terminal.',
    pasos: ['Abra las secciones plegables que le interesen.',
      'Use la cinta y el resumen para el contexto del día; el calendario, para eventos que mueven precios.',
      'Para una emisora, ábrala en Velas.'],
    terminos: [['Mapa de calor', 'Cada recuadro es un instrumento; su color indica cuánto sube o baja.'],
      ['Sin BMV', 'Los widgets gratuitos no muestran emisoras de la BMV.']],
  },
  'panel-velas': {
    titulo: 'Velas',
    que: 'Gráfica de velas con apertura, máximo, mínimo, cierre y volumen reales, con indicadores descriptivos.',
    pasos: ['Elija el instrumento, el intervalo y el rango.',
      'Pulse «Actualizar desde proveedor» si quiere datos nuevos (Alpaca para el SIC; cripto con el exchange).',
      'Active indicadores (medias, Bollinger, VWAP, MACD, estocástico).',
      'En intervalo de 1 minuto, con el flujo IEX activo, la última vela se actualiza en vivo.'],
    terminos: [['OHLCV', 'Apertura, máximo, mínimo, cierre y volumen de cada periodo.'],
      ['SIP con retraso', 'Datos consolidados de EE. UU. con al menos 15 minutos de retraso.'],
      ['IEX en vivo, volumen parcial', 'Precio en vivo de una sola bolsa (≈ 2–3 % del volumen).']],
  },
  'panel-orderflow': {
    titulo: 'Order Flow',
    que: 'Libro de órdenes, cinta de operaciones, delta de volumen y perfil de volumen por precio (POC, VAH, VAL, TPO), solo con datos reales.',
    pasos: ['Elija el instrumento (SIC con Alpaca o cripto con el exchange).',
      'Actualice libro y operaciones; ajuste minutos y niveles.',
      'Lea el perfil de volumen para ver dónde se negoció más.'],
    terminos: [['Delta', 'Compras agresivas menos ventas agresivas; solo si la fuente informa el lado.'],
      ['POC', 'Precio con más volumen negociado.'],
      ['VAH / VAL', 'Límites superior e inferior del área donde ocurrió ≈ 70 % del volumen.']],
  },
  'panel-optionflow': {
    titulo: 'Option Flow y GEX',
    que: 'Cadena de opciones por vencimiento y strike, volatilidad implícita, modelo de Heston, cinta indicativa y GEX (exposición gamma).',
    pasos: ['Elija el subyacente (emisora del SIC con opciones en EE. UU.).',
      'Con el mercado de EE. UU. abierto, pulse «Preparar GEX»: primero baja el interés abierto y luego la cadena.',
      'Lea el mapa de GEX por strike y vencimiento; cambie entre exposición absoluta y firmada.',
      'Revise la nota de procedencia: fuente, retraso y de dónde salió el precio de la acción.'],
    terminos: [['GEX', 'Gamma × interés abierto × multiplicador × precio² × 1 %: cuánto cambiaría la cobertura de los intermediarios si la acción se mueve 1 %.'],
      ['Absoluta / firmada', 'Absoluta suma calls y puts; firmada resta puts por convención y puede ser errónea.'],
      ['Interés abierto (OI)', 'Contratos abiertos al cierre previo, con su fecha; no es intradía.'],
      ['Spot de la misma referencia', 'Precio de la acción a ≤ 60 s de las cotizaciones de la cadena; sin él no hay GEX.']],
  },
  'panel-riesgo': {
    titulo: 'Riesgo',
    que: 'Riesgo de su cartera actual: exposición, concentración, volatilidad, caídas, VaR, CVaR y escenarios.',
    pasos: ['Revise qué posiciones aportan más riesgo.',
      'Compare VaR y CVaR con lo que está dispuesto a perder.',
      'Lea los supuestos al final.'],
    terminos: [['VaR 95 %', 'Pérdida que no se superaría en 95 de cada 100 días, según la historia.'],
      ['CVaR', 'Pérdida promedio en el 5 % de los peores días.'],
      ['Contribución al riesgo', 'Parte del riesgo total que aporta cada posición.']],
  },
  'panel-asistente': {
    titulo: 'Asistente',
    que: 'Responde con los datos de la terminal, su documentación y sus notas. Usa Claude u Ollama si hay credencial; si no, respuestas locales.',
    pasos: ['Escriba su pregunta («¿cómo va mi cartera?», «¿qué es el GEX?»).',
      'Guarde notas con /nota y bórrelas con /borrar.',
      'Verifique las cifras importantes en su sección.'],
    terminos: [['Motor', 'Quién responde: Claude, Ollama o el motor local.'],
      ['Sin asesoría', 'No da recomendaciones personalizadas ni envía órdenes.']],
  },
  'panel-laboratorio': {
    titulo: 'Laboratorio de alfa',
    que: 'Prueba estadística para descartar estrategias: ¿el exceso medio neto sobre un benchmark es mayor que cero?',
    pasos: ['Cargue los rendimientos de la estrategia y del benchmark por fecha.',
      'Elija tamaño de bloque, permutaciones y semilla.',
      'Lea el valor p; con varias estrategias, use el ajustado por Holm.'],
    terminos: [['Valor p', 'Probabilidad de ver un resultado así de bueno por azar; pequeño no demuestra alfa.'],
      ['Permutación por bloques', 'Cambia el signo de bloques completos para conservar la dependencia entre días.'],
      ['Holm', 'Corrección por probar varias estrategias a la vez.']],
  },
  'panel-tiempo': {
    titulo: 'Boletas e historial',
    que: 'Pasado, presente y futuro separados: hechos observados, boletas listas para capturar a mano y escenarios estimados.',
    pasos: ['Pasado: registre su tesis y la decisión que tomó.',
      'Presente: genere el «Plan del día» y copie cada boleta al portal.',
      'Futuro: revise escenarios y pronósticos, siempre marcados como estimación.'],
    terminos: [['Boleta', 'Orden completa (instrumento, cantidad, precio límite) para capturarla usted; nunca se envía.'],
      ['Estimación', 'Un pronóstico nunca aparece como precio.']],
  },
  'panel-ranking': {
    titulo: 'Ranking',
    que: 'Ordena acciones, ETF y fondos por comportamiento reciente y estabilidad, con su capitalización bursátil.',
    pasos: ['Elija la clase (acciones, ETF o fondos) y el mercado (BMV o SIC).',
      'Ordene por la columna que le interese y revise la vigencia del precio.',
      'Use los primeros lugares como candidatos en Mis portafolios.'],
    terminos: [['Puntuación', '30 % rendimiento 20 sesiones, 30 % rendimiento 60, 20 % estabilidad y 20 % tendencia.'],
      ['Capitalización', 'Acciones en circulación × precio: mega, large, mid, small o micro.']],
  },
  'panel-robustez': {
    titulo: 'Robustez',
    que: 'Comprueba si los parámetros del optimizador funcionan en una región amplia o solo en un punto con suerte.',
    pasos: ['Elija el universo.', 'Revise los mapas y la estabilidad ante cambios pequeños.',
      'Desconfíe de resultados que solo funcionan en un punto.'],
    terminos: [['Walk-forward anidado', 'Estima con un tramo del pasado y evalúa en el siguiente, sin mirar el futuro.'],
      ['Monte Carlo', 'Remuestreo del pasado para ver la dispersión de resultados.']],
  },
  'panel-movimientos': {
    titulo: 'Movimientos públicos',
    que: 'Compras y ventas declaradas por directivos (Form 4) y cambios de cartera de fondos (13F) en la SEC.',
    pasos: ['Filtre por emisora, gestor, tipo y fecha.', 'Pulse «Consultar la SEC ahora» para actualizar.',
      'Abra el documento original para confirmar.'],
    terminos: [['Form 4', 'Declaración de compra o venta de un directivo o accionista relevante.'],
      ['13F', 'Cartera trimestral de un fondo institucional; llega con hasta 45 días de retraso.']],
  },
  'panel-investigacion': {
    titulo: 'Investigación',
    que: 'Fundamentales, economía, energía y contexto, cada registro con su fuente y fecha.',
    pasos: ['Revise los indicadores por fuente.', 'Importe sus notas o datos con la plantilla.',
      'Use esta información como contexto; no cambia las propuestas.'],
    terminos: [['Serie', 'Indicador con fecha (p. ej., inflación, petróleo, ROIC).'],
      ['Importado', 'Dato que usted cargó; se guarda desde el momento en que lo importa.']],
  },
  'panel-modelos': {
    titulo: 'Modelos (opciones)',
    que: 'Calculadora de Black-Scholes-Merton: precio teórico y sensibilidades de una opción europea con sus hipótesis.',
    pasos: ['Ingrese tipo, precio de la acción, strike, días, tasa, dividendos y volatilidad (o la prima).',
      'Calcule y lea precio y griegas.'],
    terminos: [['Delta', 'Cuánto cambia la opción si la acción sube 1 peso.'],
      ['Gamma', 'Cuánto cambia la delta.'],
      ['Theta, vega, rho', 'Cambio por un día, por un punto de volatilidad y por un punto de tasa.']],
  },
  'panel-seguimiento': {
    titulo: 'Seguimiento',
    que: 'Lista de seguimiento con variaciones, RSI y noticias, ficha por emisora y comparación entre instrumentos.',
    pasos: ['Agregue emisoras a su lista.', 'Abra la ficha para ver noticias y estados financieros.',
      'Compare instrumentos con correlación y beta.'],
    terminos: [['RSI', 'Índice de fuerza relativa (0–100); arriba de 70 suele llamarse sobrecompra.'],
      ['Beta', 'Cuánto se mueve el instrumento cuando se mueve su referencia.']],
  },
  'panel-backtesting': {
    titulo: 'Backtesting',
    que: 'Pruebas históricas reproducibles con comisiones, deslizamiento y solo los datos disponibles a cada fecha.',
    pasos: ['Elija estrategia, universo y fechas.', 'Corra la prueba y revise rendimiento, caída y costos.',
      'Compare contra 1/N y revise el registro de la corrida.'],
    terminos: [['Deslizamiento', 'Diferencia entre el precio esperado y el de ejecución.'],
      ['Huella de datos', 'Identificador de los datos usados, para repetir la prueba igual.']],
  },
  'panel-intradia': {
    titulo: 'Plan intradía (informativo)',
    que: 'Contexto y disciplina para el día, separado del plan de acción. No genera órdenes ni cambia su cartera.',
    pasos: ['Revise si hay datos suficientes para hablar de una señal.', 'Respete los límites de pérdida del día.'],
    terminos: [['Inhibido', 'Con datos diarios o retrasados no se muestra señal intradía.']],
  },
  'panel-universo': {
    titulo: 'Datos y fuentes',
    que: 'De dónde viene cada dato: tabla por sección, proveedores, cobertura por instrumento, hoja de fondos Actinver y universo verificado.',
    pasos: ['Revise la tabla de cobertura por sección: dato, fuente, retraso y vigencia.',
      'Revise el estado de cada fuente: configurada, última corrida, último error.',
      'Verifique la cobertura de un instrumento antes de confiar en su precio.',
      'Importe el PDF de fondos si la descarga automática falla.'],
    terminos: [['Vigente / retrasado / vencido', 'Qué tan reciente es el dato frente a la última sesión esperada.'],
      ['Sin uso reciente', 'La fuente lleva más de 7 días sin correr.'],
      ['Cobertura', 'Una fuente se usa para un instrumento solo si una consulta real lo confirmó.']],
  },
  'panel-ayuda': {
    titulo: 'Ayuda',
    que: 'Qué hace la terminal, cómo leer el estado de los datos, sus límites y las referencias con que se construyó.',
    pasos: ['Lea «Qué hace esta terminal» si es su primera vez.', 'Consulte el glosario de estados de datos.',
      'Revise «Referencias y créditos» para las fuentes, librerías y métodos citados.'],
    terminos: [['Simulación', 'Ninguna sección envía órdenes; usted decide y opera en el portal.']],
  },
  '/static/recursos/oficina-inversion.html': {
    titulo: 'Oficina de inversión',
    que: 'Una revisión rápida de un instrumento con seis mesas (Datos, Cuantitativo, Order Flow, Crítico, Riesgo y Coordinación) sobre los datos ya guardados.',
    pasos: ['Elija un instrumento; los que tienen datos guardados aparecen primero. La consulta se hace sola.',
      'Lea cada mesa: dice qué datos hay y qué falta.',
      'Abra el instrumento en Velas, Order Flow u Option Flow (GEX) con los accesos directos.',
      'Descargue el informe o prepare el texto para Claude; nada se envía.'],
    terminos: [['Mesa', 'Una perspectiva de revisión con reglas descriptivas; no es un agente autónomo.'],
      ['Lectura local', 'Velas de 7 días y operaciones de 60 minutos ya guardadas; no consulta proveedores.']],
  },
  '/static/recursos/laboratorio-bots-reel.html': {
    titulo: 'Laboratorio de bots',
    que: 'Proyecto offline de backtesting (backtesting.py) para probar reglas de bots con datos de demostración.',
    pasos: ['Descargue el proyecto y lea la guía.', 'Ejecute la demostración en el entorno aislado.',
      'Sustituya el fixture por datos autorizados solo después de entender los límites.'],
    terminos: [['Fixture', 'Datos de ejemplo para probar el código; no son de mercado.'],
      ['Backtesting', 'Simular una regla sobre el pasado; no garantiza el futuro.']],
  },
  '/static/recursos/practica-proyectos-financieros.html': {
    titulo: 'Cuaderno financiero',
    que: 'Práctica guiada sin conexión: tesis de inversión, valoración por DCF y DCF inverso, y volatilidad, con ejemplos sintéticos.',
    pasos: ['Escriba su tesis y qué la invalidaría.', 'Pruebe la valoración y el crecimiento implícito.',
      'Mida la volatilidad sin confundirla con una señal.'],
    terminos: [['DCF', 'Valor presente de los flujos futuros descontados.'],
      ['DCF inverso', 'Qué crecimiento supone el precio actual.']],
  },
};

const clave = (k) => `guia:${k}`;

export function nodoGuia(doc, k) {
  const g = GUIAS[k];
  if (!g) return null;
  const el = (tag, props = {}, ...hijos) => { const n = doc.createElement(tag); Object.assign(n, props); n.append(...hijos); return n; };
  const det = el('details', { className: 'guia' });
  let abierta = true;
  try { abierta = localStorage.getItem(clave(k)) !== 'cerrada'; } catch { /* sin almacenamiento */ }
  det.open = abierta;
  det.addEventListener?.('toggle', () => { try { localStorage.setItem(clave(k), det.open ? 'abierta' : 'cerrada'); } catch { /* sin almacenamiento */ } });
  det.append(el('summary', {}, `Guía: cómo usar «${g.titulo}»`),
    el('p', {}, el('strong', {}, 'Qué es: '), g.que),
    el('p', {}, el('strong', {}, 'Cómo usarla:')),
    el('ol', {}, ...g.pasos.map((p) => el('li', {}, p))),
    el('p', {}, el('strong', {}, 'Qué significa:')),
    el('dl', { className: 'guia__terminos' }, ...g.terminos.flatMap(([t, d]) => [el('dt', {}, t), el('dd', {}, d)])));
  return det;
}

export function montarGuias(doc) {
  const insertar = (cont, k) => {
    if (!cont || cont.querySelector(':scope > .guia')) return;
    const n = nodoGuia(doc, k);
    if (!n) return;
    let ancla = cont.querySelector('h1');  // la guía va tras el bloque del título, como hijo directo del contenedor
    while (ancla && ancla.parentElement !== cont) ancla = ancla.parentElement;
    if (ancla) ancla.after(n); else cont.prepend(n);
  };
  doc.querySelectorAll('[role="tabpanel"]').forEach((p) => insertar(p, p.id));
  if (GUIAS[doc.location?.pathname]) insertar(doc.querySelector('main'), doc.location.pathname);
}

// «Referencias y créditos» en Ayuda: datos en /static/referencias.json (tests/test_referencias.py verifica cobertura).
export async function montarReferencias(doc) {
  const cont = doc.getElementById('referencias-lista');
  if (!cont) return;
  try {
    const d = await (await fetch('/static/referencias.json', { cache: 'no-store' })).json();
    const el = (tag, props = {}, ...hijos) => { const n = doc.createElement(tag); Object.assign(n, props); n.append(...hijos); return n; };
    cont.replaceChildren(el('p', { className: 'ayuda' }, d.aviso), ...d.grupos.map((g) => el('details', { className: 'referencias__grupo', open: true },
      el('summary', {}, `${g.titulo} (${g.items.length})`),
      el('ul', { className: 'referencias__lista' }, ...g.items.map((i) => el('li', {},
        i.url ? el('a', { href: i.url, rel: 'noopener noreferrer', target: '_blank' }, i.nombre) : el('strong', {}, i.nombre),
        i.uso ? ` — ${i.uso}` : '', i.condiciones ? el('span', { className: 'suave' }, ` ${i.condiciones}`) : ''))))));
  } catch { cont.textContent = 'No se pudieron cargar las referencias.'; }
}

if (typeof document !== 'undefined') { montarGuias(document); montarReferencias(document); }
