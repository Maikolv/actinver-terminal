# Movimientos públicos (13F institucional y Form 4 de insiders)

Módulo `terminal/movimientos/`, inspirado en la utilidad de Dataroma, con fuente oficial **SEC EDGAR**. Es contexto de
investigación: **no** crea órdenes, boletas ni recomendaciones automáticas, y **no** entra a la puntuación de las propuestas.

## Fuentes evaluadas (1-oct-2026)

| Fuente | Qué ofrece | API documentada | Costo y licencia | Decisión |
|---|---|---|---|---|
| **SEC EDGAR** ([recursos](https://www.sec.gov/about/developer-resources), [13F](https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets), [insiders](https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets)) | Documentos originales (13F-HR y /A, Form 4 y 4/A), `data.sec.gov/submissions`, conjuntos masivos trimestrales | Sí (REST JSON y XML de cada documento) | Gratuita y oficial; exige User-Agent con contacto y ≤ 10 peticiones/s | **Conectada** |
| Dataroma | ~83 «superinversionistas» (13F) y compras de insiders ≥ 50 000 USD | No (solo RSS) | Sitio público; sus términos no autorizan extracción automatizada | Solo referencia humana |
| WhaleWisdom | 13F histórico, comparaciones entre trimestres | Sí (claves compartida y secreta; 20 peticiones/min) | Sin suscripción: solo 8 trimestres, sin el actual | Requiere suscripción: no conectada |
| Quiver Quantitative | Insiders, fondos, Congreso y datos alternativos | Sí | De pago, «desde 30 USD/mes» | Requiere pago: no conectada |
| GuruFocus | Carteras de «gurús» e insiders | Anunciada | Su página devolvió 403 a la consulta automatizada: no se pudo verificar | No conectada |
| HedgeFollow | 13F de más de 10 000 fondos e insiders | No documentada | No publicada | No conectada |

No se incorporó código de otros repositorios. Los analizadores se escribieron para el XML oficial de la SEC.

## Qué distingue

**Form 4 (insiders)**
- **Qué se registra:** el emisor (CIK y símbolo) y cada declarante (CIK, nombre y relación: consejero, directivo con cargo, tenedor de ≥ 10 % u otro). Por cada operación:
  - fecha de operación, código y su naturaleza;
  - títulos, precio, si fue adquisición o disposición y titularidad (directa o indirecta, con su naturaleza);
  - títulos que posee después de la operación;
  - notas al pie y si se hizo bajo un plan 10b5-1.
- **Compra o venta discrecional:** solo los códigos `P` y `S` sin plan 10b5-1. Una venta del mismo día que un ejercicio de opciones se marca «tras ejercicio» y no cuenta como señal material.
- **Lo que no equivale a compra o venta discrecional:** adjudicación (`A`), ejercicio o conversión (`M`, `X`, `C`, `O`), retención de impuestos (`F`), donación (`G`), disposición al emisor (`D`), planes 10b5-1 y otras.
- **Correcciones 4/A:** si una 4/A repite exactamente una operación (mismo emisor, declarantes, fecha, código, títulos, precio y titularidad), se muestra una sola fila con ambas evidencias. Si la corrige, el original queda marcado «corregido por» la 4/A, que indica la fecha del original (`dateOfOriginalSubmission`).

**13F (institucionales)**
- **Qué se registra:** gestor (CIK), periodo de corte, fecha y hora de publicación, documento original, CUSIP, emisor, clase, títulos y valor.
- **Cálculo del cambio:** se compara con el periodo anterior y se clasifica como nueva, aumento, reducción, salida o sin cambio (menos de 1 %). **El cambio se infiere de dos fotografías trimestrales: no es una operación con fecha conocida.**
- **Enmiendas:** `RESTATEMENT` reemplaza la cartera del periodo y `NEW HOLDINGS` añade posiciones. Cada una cuenta solo desde su hora de aceptación.
- **Splits:** los títulos del periodo previo se ajustan con los splits que la terminal conoce (`eventos_corporativos`). Sin split registrado, si el precio implícito cae ≈ k veces (k = 2, 3, 4, 5, 10…), la fila queda **«no comparable (posible split)»** y nunca «aumento».
- **Escala del valor:** desde el 3-ene-2023 VALUE va en dólares. Si un gestor sigue declarando en miles (precio implícito mediano < 1 USD), la terminal reescala ×1000 y lo anota. Le ocurre hoy a Baupost y a Duquesne.
- **Opciones y deuda:** las filas put, call y PRN no cuentan como posición en acciones.

**Identificadores y procedencia**
- **Claves estables:** CIK (gestor, emisor, declarante), número de acceso (documento) y CUSIP (13F). Cada documento se procesa una sola vez.
- **CUSIP → símbolo:** se busca por el nombre del emisor en la lista oficial de la SEC (`company_tickers.json`), normalizado. Si el emisor tiene **varias clases** (LEN/LEN-B, GOOGL/GOOG), queda «sin identificar (varias clases)» y no se atribuye. Los CUSIP verificados a mano van en `config/cusip.csv` (`cusip,simbolo,fuente`).
- **Cobertura del mapeo** (1-oct): 210 de 297 CUSIP resueltos, 53 ambiguos y 34 sin coincidencia (ETF y nombres truncados).

**Cuatro fechas separadas** en cada fila:
1. **Operación** (Form 4) o **corte de la cartera** (13F);
2. **Publicación**: fecha de presentación y hora de aceptación de la SEC;
3. **Conocido por la terminal**: cuándo lo guardó.

Ninguna se presenta como cotización en tiempo real. Las consultas «a una fecha» solo usan documentos aceptados hasta esa hora.

## En la terminal

- **Sección «Movimientos públicos»** (en «Más»):
  - estado de cada fuente: vigente, antigua o con error, con la explicación;
  - filtros por emisora, gestor, tipo y fecha;
  - lista de seguimiento;
  - tablas de Form 4 y 13F con el documento original, el índice del expediente y una explicación breve de sus límites.
- **Grupos:** cartera (captura del portal), propuesta, seguimiento, operable en el Reto (catálogo del simulador), fuera del catálogo y sin identificar.
- **Referencias del SIC:** el precio del Form 4 es el de EE. UU. en USD. Su equivalente en pesos se etiqueta «referencia EE. UU. × tipo de cambio; no es cotización del SIC».
- **Alertas (Telegram y escritorio):** solo nuevas y materiales, en emisoras de su cartera, propuestas o seguimiento:
  - compra discrecional ≥ 100 000 USD;
  - venta discrecional ≥ 1 000 000 USD;
  - nueva posición o salida en 13F recientes.

  Una clave por fila del documento evita los duplicados (`estado_alertas`). El texto aclara que es contexto y no una recomendación.
- **Reporte diario:** sección «Movimientos públicos» fechada; `/movimientos` en Telegram.
- **Línea de comandos:** `uv run terminal movimientos actualizar`, `uv run terminal movimientos resumen`.
- **API:** `GET /api/movimientos`, `POST /api/movimientos/actualizar`, `POST/DELETE /api/seguimiento`.

## Consultas a la SEC

- **Ritmo:**
  - como máximo 5 peticiones/s;
  - reintentos con espera ante 429 o 5xx (respeta `Retry-After`);
  - Form 4 cada 6 h y 13F cada 24 h, dentro del ciclo de la terminal.
- **Primera carga (1-oct):** 614 consultas en 2 min 48 s. Trajo 501 Form 4 de 29 emisoras (90 días) y 25 13F de 8 gestores.
- **Pasadas siguientes:** 37 consultas, solo los índices.
- **Privacidad:** a la SEC solo viajan peticiones públicas por CIK. Nunca se envía su cartera a terceros.
- **Fuente anterior:** la consulta de Form 4 de `fuentes_web.SecEdgar` queda sustituida por este módulo, para no duplicar peticiones.

## Gestores iniciales (CIK verificados el 1-oct-2026)

| Gestor | CIK | Estado |
|---|---|---|
| Berkshire Hathaway | 1067983 | vigente |
| Appaloosa | 1656456 | vigente |
| Baupost | 1061768 | vigente |
| Duquesne Family Office | 1536411 | vigente |
| Himalaya | 1709323 | vigente |
| Third Point | 1040273 | vigente |
| Akre | 1112520 | vigente |
| Scion | 1649339 | último 13F del 30-sep-2025: «ANTIGUO», nunca alerta |

- **Descartados:** Pershing Square (su último documento es un 13F-NT) y Greenlight (sin 13F desde 2023).
- **Cambiar la lista:** `[movimientos] gestores` en la configuración.

## Puntuación de propuestas: no se añadió (peso 0)

No se encontró evidencia fuera de muestra de que estos movimientos aporten información incremental para el horizonte del Reto (5-oct a 13-nov-2026):
- **13F:** llega hasta 45 días después del corte; el último disponible es el del 30-jun-2026.
- **Q3-2026 fuera de plazo:** el 13F del 30-sep-2026 vence el **16-nov-2026**, después del cierre del Reto.
- **Form 4:** hay pocas compras discrecionales materiales en las emisoras del catálogo.

Por eso `en_puntuacion = false` y una prueba verifica que el plan, las boletas, el optimizador, el resumen y el ranking no usan este módulo. Una evaluación futura debe usar las consultas «a una fecha» (`hasta`), que solo ven documentos aceptados antes de cada fecha.

## Documentos reales de prueba (`tests/fixtures/sec/`)

**13F**
- **13F corregido NEW HOLDINGS** (Berkshire, corte 31-mar-2025, publicado el 14-ago-2025): añade D.R. Horton, Lennar A y Nucor, y suma más Lennar B. [Documento](https://www.sec.gov/Archives/edgar/data/1067983/000095012325008361/primary_doc.xml). Sirve también como caso de **publicación posterior** al periodo: antes del 14-ago esas posiciones no se usan.
- **Split** (Appaloosa, NVIDIA): 442 000 acciones en el 1T-2024 y 690 000 en el 2T-2024. Con el split 10:1 del 10-jun-2024 es una reducción. [1T](https://www.sec.gov/Archives/edgar/data/1656456/000165645624000002/) y [2T](https://www.sec.gov/Archives/edgar/data/1656456/000165645624000003/).
- **Símbolo ambiguo:** Lennar CL A y CL B (LEN y LEN-B en la lista oficial de la SEC).

**Form 4**
- **No discrecional:** [adjudicación (A) de AAPL](https://www.sec.gov/Archives/edgar/data/320193/000114036126038028/).
- **Plan 10b5-1:** [venta programada de KO](https://www.sec.gov/Archives/edgar/data/21344/000002134426000156/form4.xml).
- **Ejercicio y venta el mismo día:** [KO](https://www.sec.gov/Archives/edgar/data/21344/000002134426000167/form4.xml).
- **Compra en mercado abierto:** [consejero de KO](https://www.sec.gov/Archives/edgar/data/21344/000002134425000075/form4.xml).
- **4/A que corrige al original:** J&J y JJDC sobre CVRx. [Original](https://www.sec.gov/Archives/edgar/data/200406/000119312525303876/ownership.xml) y [4/A](https://www.sec.gov/Archives/edgar/data/200406/000119312526007679/ownership.xml).

## Limitaciones vigentes

- **13F:**
  - incluye solo posiciones largas en valores 13(f) de EE. UU.;
  - no informa cortos ni la fecha de cada operación;
  - el gestor pudo comprar y vender dentro del trimestre.
- **CUSIP sin resolver:** un CUSIP sin símbolo único no se relaciona con su cartera; se puede fijar en `config/cusip.csv`.
- **Form 4 con declarante que también es emisor vigilado:** el índice de un emisor vigilado (por ejemplo BRK) incluye Form 4 que esa empresa presenta como inversionista en otras. Se muestran bajo la emisora real (por ejemplo, las compras de LEN por Berkshire a fines de septiembre de 2026).
- **BMV:** no hay equivalente oficial de 13F ni de Form 4 para las emisoras de la BMV en este módulo.
- **Sin tiempo real:** no son cotizaciones; los datos tienen el retraso legal de cada formulario.
