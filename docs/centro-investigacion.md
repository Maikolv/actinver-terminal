# Centro de investigación — fuentes cuantitativas y herramientas

Implementado el 11-oct-2026 en `actinver-terminal`. Abra **Más → Investigación**.

## Uso

1. **Actualizar investigación** consulta las fuentes con acceso disponible. BLS admite la consulta básica sin clave. Las demás APIs necesitan una clave propia en `.env`; reinicie la terminal tras configurarla. El motor también refresca este contexto durante sus ciclos completos, respetando caché y cupos.
2. **Filtrar** por símbolo de origen (`MU`, `AMD`, `NVDA`, `XOM`) muestra sus observaciones y el contexto macro/energético común. Los símbolos identifican la referencia; no certifican equivalencia con el SIC ni elegibilidad.
3. **Herramientas y acceso** explica la aplicación de cada servicio, su vía de integración, documentación y acceso.
4. **Importar hallazgos** acepta datos o notas que usted haya obtenido con su acceso autorizado. Descargue la plantilla vacía; una fila por indicador o nota. Las exportaciones originales de los proveedores deben adaptarse a esta plantilla, no se interpretan automáticamente.
5. **Descargar registros** exporta el contexto con fuente, método de obtención, período, momento en que se conoció aquí y última comprobación. La pantalla muestra primero el último indicador de cada serie; active **Mostrar historial de registros** para ver los períodos anteriores. Cada consulta presenta hasta 1000 observaciones recientes; el histórico completo permanece en SQLite.

## Qué se conectó

| Fuente | Aplicación concreta | Acceso | Implementación |
|---|---|---|---|
| [Alpha Vantage](https://www.alphavantage.co/documentation/) | Ingresos, beneficio y márgenes **anuales** de MU, AMD, NVDA y XOM | `ALPHAVANTAGE_API_KEY` | API gratuita `INCOME_STATEMENT`; 4 consultas por actualización, separadas 1.2 s; guarda los símbolos que respondan y se detiene ante un aviso de límite; 24 h de caché; máximo local 20/día por defecto, nunca más de 25/día. `OVERVIEW` exige plan premium y no se consulta |
| [FRED](https://fred.stlouisfed.org/docs/api/fred/series_observations.html) | DGS2, DGS10, FEDFUNDS, INDPRO | `FRED_API_KEY` gratuita | API oficial; 24 observaciones por serie; 24 h de caché. Se conserva la conexión FX existente |
| [CoinGecko](https://docs.coingecko.com/demo/reference/simple-price) | Referencia BTC/ETH, variación de 24 h y capitalización | `COINGECKO_DEMO_API_KEY` | API Demo; una consulta/hora; retiene hora del dato y marca referencias atrasadas |
| [EIA](https://www.eia.gov/opendata/documentation.php) | WTI, Brent, existencias comerciales de crudo | `EIA_API_KEY` gratuita | API v2 `seriesid`; tres series, hasta 30 observaciones por serie; 24 h de caché |
| [BLS](https://www.bls.gov/developers/api_signature_v2.htm) | CPI desestacionalizado, desempleo, nóminas; cambio interanual descriptivo del CPI | Sin clave; `BLS_API_KEY` opcional | API pública; 3 series en una consulta, últimos 3 años; 24 h de caché, cupo local 4/día; excluye M13 |

La implementación se comprobó con respuestas controladas. Una clave presente no prueba acceso válido: la pantalla informa el resultado de la última consulta real. No se crean cuentas ni se contratan servicios.

Las claves FRED y EIA proporcionadas el 12-oct-2026 respondieron a consultas oficiales de prueba; EIA devolvió una observación WTI. La clave gratuita de Alpha Vantage respondió a `INCOME_STATEMENT`; `OVERVIEW` devolvió aviso de función premium, por lo que se cambió el conector. Las tres claves están configuradas en el archivo `.env` local, excluido de Git. Las claves nunca se incluyen en este documento.

## Herramientas aplicadas mediante consulta e importación

| Herramienta | Hallazgos que guardar | Vía y requisito |
|---|---|---|
| [Finviz](https://elite.finviz.com/elite.ashx) | Selecciones, sector, valuaciones, volumen | Se conserva el conector Elite existente (`FINVIZ_AUTH_TOKEN`); este centro también recibe notas/CSV. API y exportación requieren Elite |
| [Fiscal.ai](https://docs.fiscal.ai/docs/api-reference) | Ingresos por segmento, márgenes, fundamentales | Consulta/importación; API oficial disponible con acceso propio, sin nuevo conector automático en esta entrega |
| [InvestingPro](https://pro.investing-support.com/hc/en-us) | Valuación, salud financiera, estimaciones | Consulta/importación manual según su suscripción; no se usa API privada |
| [ROIC.ai](https://www.roic.ai/api/docs/getting-started) | ROIC, deuda, flujo libre, comparables | Consulta/importación; API oficial v3 por plan, sin conector automático en esta entrega |
| [Webull](https://www.webull.com/open-api) | Referencias de mercado y notas de contraste | Consulta/importación; OpenAPI existe, pero no se conecta una cuenta de bróker |
| [StockCharts](https://help.stockcharts.com/data-and-ticker-symbols/data-availability/historical-data/how-do-i-download-data-to-excel) | Tendencia, fuerza relativa, amplitud | Consulta/importación; descargas históricas según plan |
| [SpotGamma](https://support.spotgamma.com/hc/en-us/articles/50266085426195-Does-SpotGamma-have-an-API-Can-I-export-data) | Niveles, exposición gamma, interés abierto | Adaptar exportación EquityHub a la plantilla; sin API pública según el soporte consultado |
| [Quartr](https://quartr.com/docs/api-reference/events/list-events) | Guidance, notas de conferencias, resultados | Consulta/importación; API oficial con acceso propio, sin conector automático en esta entrega |
| [Capitol Trades](https://www.capitoltrades.com/about-us) | Operación divulgada, fechas y rango de importe | Consulta/importación manual; no se confirmó API pública. No interpretar rangos divulgados como importe exacto ni señal actual |
| [MacroMicro](https://support.macromicro.me/en/faq/152) | Ciclo, liquidez, contrastes macro | Consulta/importación cuando el contrato lo permite; API/datos brutos empresariales. Prime/Max no incluyen CSV según soporte |
| [SSRN](https://papers.ssrn.com/) | Literatura sobre microestructura, flujo de órdenes y opciones; hipótesis con referencia y fecha | Búsqueda y registro manual de notas/enlaces. Los working papers requieren evaluación crítica; no alimentan señales de trading |

`FISCAL_AI_API_KEY`, `ROIC_AI_API_KEY`, `QUARTR_API_KEY` y `MACROMICRO_API_KEY` se identifican como requisitos futuros en el catálogo; poner una clave no crea un conector para estos servicios.

## Plantilla de hallazgos

Encabezados exactos:

```csv
fuente,simbolo,serie,titulo,periodo,valor,unidad,texto,url
```

Use el **identificador** mostrado junto a cada herramienta (`roic_ai`, `spotgamma`, `quartr`, etc.). El período admite `YYYY-MM-DD`, `YYYY-MM`, `YYYY-Qn` o `YYYY`. Para valores indique unidad y punto decimal; para notas puede dejar valor/unidad vacíos. El enlace debe pertenecer al dominio oficial de la herramienta. Para SSRN use `fuente=ssrn`, `serie=tesis` o un tema concreto, `periodo` igual a la fecha de publicación conocida, `texto` con la hipótesis y limitaciones, y la URL oficial del trabajo. No se descarga el enlace importado. Máximo 1000 filas/1 MB, UTF-8.

La importación valida todo el archivo antes de guardarlo. Rechaza números no finitos, períodos futuros, fuentes desconocidas, enlaces externos o con credenciales. Guarda un registro de auditoría con conteos. La exportación neutraliza fórmulas de hojas de cálculo.

## Aplicación a proyectos cuantitativos

Interpreto «Quant projects» como el grupo de proyectos que se pueden construir con las cinco fuentes listadas, no como un servicio identificado por URL.

1. **Entorno macro y sensibilidad de la cartera.** Comparar tasas FRED, inflación y empleo BLS con la evolución de las posiciones. Los datos recolectados desde ahora permiten comenzar un histórico de disponibilidad; todavía no hay un modelo validado que cambie las propuestas.
2. **Energía y XOM.** Registrar WTI, Brent e inventarios EIA junto a tesis sobre XOM. Evaluar más adelante sensibilidad a variaciones, con fechas de publicación y disponibilidad. No asumir que el precio del petróleo equivale al rendimiento de la acción.
3. **Calidad de resultados.** Contrastar los ingresos y márgenes anuales de Alpha Vantage con ROIC.ai/Fiscal.ai/InvestingPro mediante notas o exportaciones autorizadas. La clave gratuita no habilita P/E, P/B ni ROE de `OVERVIEW`.
4. **Diario de eventos.** Registrar guidance Quartr, niveles SpotGamma, tendencia StockCharts y divulgaciones Capitol Trades. Separar lo que ocurrió de cuándo se supo; registrar una hipótesis antes de medir su resultado.
5. **Contexto de riesgo externo.** Observar BTC/ETH de CoinGecko junto a notas de MacroMicro y Webull, sin incorporar cripto al universo del Reto.

## Disponibilidad y límites de interpretación

- `periodo` describe el período económico/reportado; no es la fecha de publicación.
- `disponible_desde` es el momento de ingestión aquí, usado de forma conservadora. No se fabrican fechas históricas de disponibilidad ni se promete cobertura point-in-time/ALFRED.
- `confirmado_en` señala la última comprobación del mismo contenido. Se conservan versiones cuando cambia el valor, incluso si una revisión vuelve a un valor anterior.
- `hora_fuente` solo se almacena cuando la API la entrega (CoinGecko). La pantalla separa edad de la comprobación y referencia atrasada.
- Las importaciones se rotulan **manuales**. El centro no verifica independientemente que el usuario haya transcrito bien el contenido.
- Estas tablas no modifican `precios`, `fx`, `instrumentos`, posiciones, puntuaciones ni boletas. No envían órdenes ni notificaciones a terceros.

## Configuración opcional

Las claves se guardan únicamente en `.env`, ignorado por Git. La interfaz solo muestra si hay clave; no su valor.

Puede ajustar `config/local.toml` sin secretos:

```toml
[centro_investigacion]
auto_actualizar = true

[centro_investigacion.alpha_vantage]
activo = true
simbolos = ["MU", "AMD", "NVDA", "XOM"]
intervalo_horas = 24
peticiones_por_dia = 20

[centro_investigacion.bls]
activo = true
intervalo_horas = 24
peticiones_por_dia = 4
```

Mismos campos `activo`, `intervalo_horas`, `peticiones_por_dia` para `fred_macro`, `coingecko` y `eia`. Las consultas fallidas esperan al menos una hora; no se ignoran límites desde el botón. Desactive una fuente con `activo=false`, o el refresco automático con `auto_actualizar=false`. En modo demostración no se consultan APIs ni se permiten importaciones reales.

## Verificación

**150 pruebas relevantes superadas**: centro de investigación, adaptadores, seguridad, monitor y compilación. La batería completa se inició y se interrumpió para concentrar la comprobación en los módulos afectados; no se afirma haber ejecutado toda la suite hasta el final. Solo quedó un aviso de deprecación de una dependencia de pruebas.

**Consulta real:** BLS respondió y se guardaron 115 observaciones; antes y después se verificaron los conteos de precios, FX, instrumentos y transacciones, sin cambios. Se creó previamente un respaldo consistente de la base. Alpha Vantage, FRED macro, CoinGecko y EIA quedaron pendientes por ausencia de sus claves en la configuración; sus parsers se comprobaron con respuestas controladas, no con una sesión real del proveedor.

**Interfaz:** revisión en Edge, escritorio (1440 px) y móvil (390 px). Se comprobaron 15 herramientas antes de añadir SSRN; la tarjeta y el flujo de importación de SSRN se verifican por separado, 4 indicadores recientes, 115 observaciones históricas, filtro por símbolo y enlace de exportación, sin errores JavaScript. También pasó la comprobación de sintaxis JavaScript y de formato del diff.

No se contrató ningún servicio ni se crearon cuentas. No se publicó, hizo commit ni push de estos cambios. Se conservaron los cambios previos de TradingView y CHANGELOG que ya estaban presentes al iniciar la sesión.
