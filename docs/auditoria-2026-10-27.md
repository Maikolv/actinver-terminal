# Auditoría 27-oct-2026: capitalización, GEX, constructor Markowitz y fuentes de datos

Encargo del usuario (27-oct):
1. Clasificar el ranking por capitalización bursátil.
2. Asegurar el GEX.
3. Crear un constructor de portafolios ilimitados con Markowitz y descarga en Excel, apoyado en los materiales de Acelera Academy.
4. Auditar la terminal y proponer datos y API alternativas.

Límites que no cambian: la terminal no envía órdenes, no contrata nada, los secretos solo viven en `.env`, solo se sirve en 127.0.0.1 y no presenta datos retrasados como tiempo real.

## 1. Qué se incorporó

### Capitalización en el Ranking

Archivos: `terminal/capitalizacion.py`, `terminal/ranking.py` y `web/static/app.js`.

- Nueva columna «Capitalización» y un filtro con las categorías Mega, Large, Mid, Small, Micro y «Sin dato».
- Un panel explica qué significa cada categoría. Los cortes en USD son ≥ 200 000 M, 10 000 M, 2 000 M, 300 M y < 300 M.

Fuentes de las acciones en circulación:

- **Emisoras de EE. UU.** Se toma de la SEC, del concepto `dei:EntityCommonStockSharesOutstanding` en su último 10-K o 10-Q. Es una API oficial, gratuita y usa `SEC_USER_AGENT`.
- **Empresas con varias series** (Berkshire, Visa, Alphabet, Meta…). La SEC solo publica sin series un dato antiguo. Por eso:
  - se descartan los datos con más de 18 meses;
  - si acciones × precio queda por debajo del 60 % del capital flotante del 10-K (`dei:EntityPublicFloat`), se usa ese flotante y la fila se marca «aprox.».
- **ADR de emisores extranjeros** (20-F; p. ej. TSM, BABA). No se clasifican, porque la SEC reporta acciones ordinarias y la conversión a ADR distorsionaría el tamaño.
- **BMV.** No hay una API gratuita con acciones en circulación. Se leen de `config/capitalizacion_bmv.csv`, que el usuario llena con una fuente oficial; mientras no se llene, aparecen como «sin dato».

Medición del 27-oct sobre 140 acciones con historia:

| Estado | Mega | Large | Mid | Small | Total |
|---|---|---|---|---|---|
| Verificadas | 31 | 35 | 8 | 2 | 76 |
| Aproximadas | 8 | 9 | 4 | — | 21 |

- 4 emisoras son ADR.
- 39 quedan sin dato, en su mayoría de la BMV.
- Es correcto, por ejemplo, que NVDA, MU y AMD sean mega, y que NVAX y SPCE sean small.

### GEX

El GEX ya existía en Option Flow (`terminal/flujo/gex.py`). No mostraba nada porque no había cadena de opciones guardada.

- Se activó `contratos_oi = true` en `config/local.toml`. Es un GET de solo lectura en Paper, autorizado el 18-oct y ratificado hoy.
- Se descargaron cadenas de NVDA (900 contratos) y MU (1 918), y el interés abierto de Paper fechado al 23-oct.
- Por diseño anti-fuga, el interés abierto solo se une a una cadena cuyo instante sea posterior a la consulta del OI. Fuera de horario, la cadena conserva las cotizaciones del cierre, anteriores al OI, así que hoy el GEX dice «no calculable», correctamente.
- Nuevo botón **«Preparar GEX: OI y luego cadena»**: hace las dos consultas en el orden correcto. Úselo con el mercado de EE. UU. abierto.

### Constructor «Mis portafolios (Markowitz)»

Archivos: `terminal/markowitz.py`, pestaña en Mi cuenta.

- Permite crear, abrir, editar, duplicar y eliminar portafolios ilimitados, aparte de la cuenta del Reto. Se guardan en la tabla `portafolios_usuario`.
- **Objetivos por la pirámide de Maslow**, del compilado de Acelera: seguridad, pertenencia, estima y autorrealización. Cada objetivo propone método, tope por activo, aversión y número mínimo de activos.
- **Seis métodos:**
  - máximo Sharpe (tangente);
  - mínima varianza;
  - rendimiento objetivo;
  - riesgo objetivo;
  - utilidad U = E − ½Aσ²;
  - 1/N.
- **Fórmulas del taller de Acelera:**
  - rendimientos diarios simples, con promedio × 252 y covarianza × 252;
  - optimización SLSQP con suma = 1 y topes;
  - frontera eficiente de 25 puntos;
  - línea de asignación de capital (CAL);
  - y* = (E − r_f)/(Aσ²).
- **Ayuda para construir:**
  - buscador de todo el universo;
  - «Sugerir instrumentos», que toma lo mejor del Ranking y descarta los pares con correlación > 0.85, con filtros por clase, mercado y capitalización;
  - avisos si hay pocos activos con peso o la ventana es corta.
- **Resultados:**
  - indicadores clave: E, σ, Sharpe, caída máxima, peor día e y*;
  - comparación con la tangente, la mínima varianza y 1/N;
  - gráfica de la frontera;
  - pesos, aporte al riesgo, montos y títulos;
  - matriz de correlaciones;
  - revisión informativa de las reglas del Reto.

### Excel de Markowitz con fórmulas vivas

Archivo: `terminal/excel_markowitz.py`.

- **Plantilla** (`/api/markowitz/plantilla.xlsx`):
  - el ejercicio paramétrico de Acelera (IPC, S&P 500 y Treasury MXN), con matrices ρ → cov y la tabla de dos activos con ρ = +1, 0, −1;
  - corrige las 90 fórmulas `#REF!` del archivo original;
  - una hoja histórica vacía para pegar precios.
- **Portafolios guardados** (uno o todos):
  - precios y rendimientos;
  - E y σ (`AVERAGE`, `STDEV.S`), covarianzas (`COVARIANCE.S` × 252) y correlaciones;
  - pesos editables, resultados, frontera y gráfica;
  - instrucciones para Solver.
- Verificado al abrir los libros en Excel: 0 errores de fórmula. El libro da E = 64.27 %, σ = 15.57 % y Sharpe = 3.678, idénticos al cálculo de la terminal.

### Pruebas

- `tests/test_markowitz.py`: 10 pruebas que cubren:
  - categorías y lectura de la SEC;
  - el uso del flotante;
  - que los métodos respeten restricciones y teoría (la tangente ≥ Sharpe de 1/N; la mínima varianza ≤ σ de 1/N; frontera monótona; se alcanza el rendimiento objetivo);
  - las validaciones;
  - la persistencia, el Excel sin `#REF!` y la API con CSRF.
- `tests/navegacion.test.mjs`: 3 de 3 aprobadas. Resultado de la suite completa: ver CHANGELOG.

## 2. Estado medido

| Elemento | Medición | Lectura |
|---|---|---|
| Vigencia de precios | 182 vigentes, 30 vencidos, 1 retrasado, 1 sin datos | Los vencidos son BMV: EODHD dejó 32 emisoras pendientes por el límite de 20 consultas al día |
| FRED | Última corrida en error el 24-sep (ReadTimeout) | El FX lo cubre Banxico (al día); el estado viejo confunde en la cabecera |
| `/api/ranking` | 10 a 30 s (en frío) | Es la vista más lenta; recalcula precios, cotizaciones y percentiles en cada consulta y se refresca cada minuto |
| `/api/estado`, `/api/cartera`, `/api/universo` | 0.2 a 0.5 s | Bien |
| Base `data/terminal.db` | 215 MB | Hay respaldo diario; conviene `VACUUM` mensual |
| GEX | Calculable solo con una cadena intradía posterior al OI | Ver mejora 4 |
| Capitalización BMV | 0 de ~60 emisoras | Requiere el archivo del usuario o un proveedor de pago |

## 3. Mejoras recomendadas (mayor impacto primero)

1. **Cola de actualización priorizada para EODHD.** Hoy 30 instrumentos BMV están vencidos. Conviene ordenar el cupo de 20 consultas diarias así: posiciones de la cuenta, luego activos de los portafolios guardados y propuestas, y al final el resto.
2. **Caché del Ranking por fecha del último precio.** Si no hay precio nuevo, devolver el cálculo anterior: bajaría de 10 a 30 s a menos de 1 s. Igual para «Sugerir instrumentos», que usa el Ranking.
3. **Tasa libre de riesgo automática.** Tomar CETES a 28 días de Banxico SIE con el token que ya existe en `.env`, en lugar del 7 % por defecto. Antes, confirmar la clave de la serie en el catálogo SIE.
4. **GEX programado y opcional.** Una tarea del motor que consulte el OI de Paper antes de la apertura (8:45 NY) y la cadena a las 10:00 y 14:00 NY, solo para los subyacentes en cartera (hoy MU, NVDA, AMD, XOM, PFE, NVAX).
5. **Markowitz más robusto, sin perder la versión del taller:**
   - covarianza con contracción de Ledoit-Wolf (skfolio ya está instalado);
   - rendimientos esperados por CAPM (beta contra IPC o S&P 500, como la Tarea 9 del taller), o Black-Litterman con las opiniones del usuario;
   - restricciones por sector, por moneda (USD máximo) y por capitalización.
6. **Prueba fuera de muestra de cada portafolio guardado frente a 1/N.** Walk-forward con costos (comisión del Reto) y rebalanceo mensual. Sin esto no hay ventaja demostrada, y la interfaz ya lo advierte.
7. **Estado de proveedores con antigüedad.** Mostrar «error hace 33 días» y reintentar FRED; hoy aparece como un error vigente.
8. **Motor resistente a suspensiones.** Guardar el avance por etapa, no solo al final. Además, la tarea pendiente del 25-oct: rotación de `data/terminal_*.log` y reintento ante «database is locked».
9. **`VACUUM` mensual de la base**, después del respaldo.
10. **Pendientes de la auditoría del 25-oct**: SSE de la última vela con IEX. La brecha 3 de CLAUDE.md, que citaba el
    16-oct, se corrigió hoy.

## 4. Alternativas de datos y API para que la terminal funcione al 100 %

Precios y condiciones vigentes a la fecha de la búsqueda; confirme en cada sitio. **Nada se contrató.** Requieren su decisión, según la sección 7 del mandato.

| Necesidad | Hoy | Gratuita | De pago (referencia) | Nota |
|---|---|---|---|---|
| Cierres BMV completos | EODHD gratis: 20 consultas/día | Captura e importación propias (CSV) | EODHD «EOD All World» ≈ 19.99 USD/mes, 100 000 consultas/día | La de mayor impacto: elimina los 30 vencidos y da historia larga |
| Intradía BMV | — | — | EODHD «EOD+Intraday Extended» ≈ 29.99 USD/mes | Retrasado; para BMV en tiempo real hace falta DataBMV o un vendor con licencia |
| Capitalización y fundamentales BMV | — | Reportes trimestrales de bmv.com.mx (manual) | EODHD Fundamentals ≈ 59.99 USD/mes (cada consulta consume 10) | Llenaría `config/capitalizacion_bmv.csv` automáticamente |
| Capitalización EE. UU. | SEC (oficial) | SEC; Finnhub `profile2` (clave gratuita) | — | La SEC basta; Finnhub serviría de contraste para empresas con varias series |
| Tiempo real EE. UU. | Alpaca IEX (≈ 2-3 % del volumen) | Finnhub WebSocket de operaciones (clave gratuita, uso personal) | Alpaca SIP de pago | Sigue siendo parcial: se etiqueta como tal, nunca como consolidado |
| Opciones (GEX): OI y griegas | Alpaca indicativo + OI de Paper | Tradier sandbox (retrasado 15 min, incluye griegas y OI; requiere cuenta) | Market Data de Tradier (≈ 10 USD/mes, según terceros); OPRA vía proveedor | Con Tradier, el GEX se calcularía en una sola consulta |
| Tasa libre de riesgo MX | Supuesto 7 % | Banxico SIE (token gratuito, ya configurado) | — | Mejora 3 |
| Macro EE. UU. | FRED, BLS, EIA | Igual | — | Reintentar FRED |

Recomendación técnica (la decisión es suya):

- **Sin gastar:** Banxico SIE para r_f, la cola priorizada de EODHD, la caché del Ranking y el GEX programado.
- **Con un solo gasto:** EODHD All World (≈ 20 USD/mes) es el que más eleva la cobertura de la BMV.

Fuentes consultadas:

- [EODHD pricing](https://eodhd.com/pricing?via=kmg)
- [apis.io: planes de EODHD](https://apis.io/plans/eodhd/eodhd-plans-pricing/)
- [fitgap: EODHD](https://us.fitgap.com/products/eodhd-financial-data-apis)
- [Banxico SIE API](https://www.banxico.org.mx/SieAPIRest/service/v1/?locale=en)
- [Comparativa de API de opciones 2026](https://flashalpha.com/articles/options-api-comparison-flashalpha-tradier-polygon-intrinio)
- [Tradier: documentación](https://documentation.tradier.com/brokerage-api/table-of-contents)
- [Finnhub: documentación](https://www.finnhub.io/docs/api)
