# Auditoría 28-oct-2026: diseño unificado, generador de portafolios, Excel con marca y widgets

Medido el miércoles 28-oct-2026 entre las 12:40 y las 13:20 (CDMX), con la terminal real en `127.0.0.1:8765` y el
mercado de EE. UU. abierto. El prompt para cerrar lo pendiente está en `docs/prompt-pendientes-2026-10-28.md`.

## 1. Qué se cambió hoy

| Pedido | Qué se hizo | Cómo se verificó |
|---|---|---|
| Logo y colores iguales en toda la terminal | Un solo logo (el del ícono de la pestaña: cuadro azul `#1f5f8b` con línea de precio blanca) en la terminal, Oficina, Laboratorio de bots, Cuaderno, página 404 y páginas de gráficas de TradingView. Antes había tres versiones y el Laboratorio de bots no tenía logo. El color del logo es fijo (`--marca`) en claro y oscuro. Títulos de pestaña con el formato «Sección · Actinver Terminal» | Capturas de las cinco páginas y la 404 en el navegador interno |
| Excel con el diseño de la terminal | Logo en cada hoja, tipografía Segoe UI, colores de `app.css` (azul claro = usted escribe, verde = resultado principal), encabezados como las tablas de la terminal, gráficas con la paleta de la terminal, paneles inmovilizados. «Léeme» pasó a «Guía»: pasos numerados con las celdas exactas de cada libro (incluido Solver) | Fórmulas evaluadas con el motor `formulas` de Python: 0 errores en la plantilla; el libro de un portafolio da E 59.60 %, σ 15.50 %, Sharpe 3.392, igual que la terminal. **No se pudo abrir en Excel**: la automatización de Excel no responde hoy ni con un libro vacío de prueba |
| Portafolios sin «Maslow» y con generador en tiempo real | Perfiles Conservador, Moderado, Crecimiento y Agresivo. Generador de propuestas: cada cambio (perfil, clase, mercado, capitalización, número de instrumentos, tope, método, tasa, historia) recalcula la mejor propuesta en 0.5 s de pausa. La terminal completa con los mejores del Ranking que no se mueven igual, explica por qué eligió cada uno y sugiere mejoras con un botón para aplicarlas (quitar lo que no recibe peso, subir el tope, cambiar de método, quitar pares redundantes) y otros candidatos listos | Recorrido en el navegador: Crecimiento → Conservador → «Usar máximo Sharpe» → fijar AMX; cada paso recalculó. En celular (375 px) sin desbordamiento. 2 pruebas nuevas |
| Quitar «Aprender y recursos» | Se retiró la pestaña, su panel, el acceso del Plan de acción y el destino del selector; el grupo «Investigar y aprender» pasó a «Investigar». Se conservan `config/aprendizaje.json`, `terminal/aprendizaje.py` y `/api/aprendizaje` (otra sesión tiene cambios sin commitear en ese archivo y los datos no se borran) | Pruebas de navegación de Node (9) |
| Más widgets como los de TradingView | Seis widgets gratuitos más en Mercado: cotizaciones por grupo (índices, dólar y euro, bonos de EE. UU., materias primas), acciones de EE. UU. que más suben/bajan/se operan, mapa de ETF, tipos de cambio cruzados, mapa de divisas y mapa de cripto (fuera del Reto). Todos los widgets y la gráfica siguen el modo claro u oscuro del sistema | Los seis scripts existen en TradingView (HTTP 200). Las páginas responden 200. **No se vio el dibujo**: el navegador interno bloquea scripts externos |

## 2. Estado medido

| Elemento | Medición | Lectura |
|---|---|---|
| Vigencia de precios | 180 vigentes, 31 vencidos, 2 retrasados, 1 sin datos (214) | Igual que el 27-oct: los vencidos son BMV por el cupo de EODHD |
| Motor | Último ciclo 12:55 CDMX, 723 s, sin datos nuevos | Funciona; tarda 12 min |
| Tiempo real | Alpaca IEX conectado, 30 símbolos | Parcial (≈ 2–3 % del volumen) y así se etiqueta |
| Tipo de cambio | Banxico FIX 18.6525 del 27-oct, vigente | Bien |
| `/api/ranking` | 5.3 s (tibio) | Sigue siendo lo más lento; el generador ya guarda sus filas 5 min |
| Generador | 25 s la primera vez (Ranking en frío), 1.6–3.7 s después | Aceptable para tiempo real con pausa de 0.5 s |
| Generador durante el ciclo del motor | Una consulta esperó más de 2 min mientras el motor terminaba su ciclo de 12 min; al terminar, 1.6 s | Hallazgo nuevo (punto 3.2) |
| GEX con mercado abierto | OI de Paper (2 680 registros) y cadena (902) descargados a las 13:15; **GEX no calculable**: 615 contratos sin spot de la misma referencia, 168 sin gamma, 119 sin OI | Hallazgo nuevo (punto 3.1) |
| Base de datos | 231 MB (215 MB el 27-oct) | Crece ≈ 16 MB al día con el flujo en vivo |
| Pruebas | 688 aprobadas (`uv run pytest tests`, 13 min 51 s) y 9 de Node | Bien |

## 3. Hallazgos (mayor impacto primero)

1. **El GEX está en la terminal pero no se puede calcular con datos gratuitos.** La regla anti-fuga exige que el spot
   del subyacente venga de la misma referencia que la cadena; el feed indicativo de opciones de Alpaca no lo trae, y
   la gamma falta en el 19 % de los contratos. Opciones: (a) unir el spot de acciones de Alpaca con el mismo retraso
   (15 min) y la misma hora, declarando la procedencia, o (b) una fuente con griegas, OI y spot juntos (Tradier
   sandbox gratuito con cuenta, o de pago). La (a) es código; la (b), decisión del usuario.
2. **Bloqueo durante el ciclo del motor.** Con el motor corriendo, una consulta del generador quedó en espera más de
   2 minutos; la misma consulta sin motor tarda 2.4 s. Probable espera por escritura de SQLite. Es el mismo síntoma
   del «database is locked» del 20-oct.
3. **Cobertura BMV**: 31 vencidos por las 20 consultas diarias de EODHD (pendiente desde el 20-oct).
4. **Ranking lento** en frío (10–30 s, 5 s tibio): caché por fecha del último precio (pendiente del 27-oct).
5. **Tasa libre de riesgo fija** (7 %) en el generador: tomar CETES de Banxico SIE (pendiente del 27-oct).
6. **Sin prueba fuera de muestra** de los portafolios del generador frente a 1/N (pendiente del 27-oct).
7. **Excel sin verificación en Excel** hoy (la automatización no responde); las fórmulas sí se evaluaron.
8. **Widgets nuevos sin verificación visual** en este navegador; falta verlos en Chrome.
9. **La carpeta `tools/`** de otra sesión rompe `uv run pytest` sin ruta (un archivo de prueba sin dependencias).
   Correr `uv run pytest tests` o agregar `testpaths = ["tests"]` en `pyproject.toml`.
10. **Base de 231 MB** creciendo ≈ 16 MB al día: `VACUUM` mensual tras el respaldo (pendiente del 27-oct).

## 4. Pendientes de auditorías anteriores (siguen abiertos)

| Origen | Pendiente | Quién |
|---|---|---|
| 18-oct | Fuentes de pago (Finviz, EODHD, Databento); 9 propuestas de revisión del mandato; referencia del plan frente a 1/N | Usuario |
| 19-oct | Estilos `.accesos--relacionados` sin uso | Código |
| 20-oct | Energía de Windows para no suspender en horario de mercado; una sola terminal con motor; SMTP opcional; clave de Anthropic u Ollama para el asistente | Usuario |
| 20-oct | `database is locked` esporádico (ver 3.2) | Código |
| 25-oct | Registro del inicio de cada ciclo del motor; rotación de `data/terminal_*.log`; estado de proveedores con antigüedad (FRED); última vela en vivo con IEX (SSE); cola priorizada de EODHD | Código |
| 27-oct | Caché del Ranking; CETES de Banxico como r_f; GEX programado; Markowitz robusto (Ledoit-Wolf, CAPM o Black-Litterman, restricciones por sector y moneda); prueba fuera de muestra frente a 1/N; `VACUUM` | Código |
| 27-oct | `config/capitalizacion_bmv.csv` vacío: capitalización BMV | Usuario (o EODHD Fundamentals, de pago) |

## 5. Widgets: qué más se puede incrustar

- **Agregados hoy (gratis, sin cuenta):** cotizaciones por grupo, destacados de EE. UU., mapa de ETF, tipos de cambio
  cruzados, mapa de divisas y mapa de cripto.
- **Ya estaban:** cinta, resumen de mercados, mapa de acciones, calendario económico, filtro, noticias y, por emisora,
  precio, panorama, perfil, fundamentales, noticias y resumen técnico; gráfica avanzada en Velas.
- **Disponibles y no agregados:** `mini-symbol-overview`, `single-quote` y `tickers` repiten lo que ya muestran
  `symbol-info` y la cinta. El filtro de cripto (`crypto-mkt-screener`) ya no existe en TradingView (HTTP 403).
- **Límite:** los widgets gratuitos no muestran emisoras de la BMV (comprobado el 25-oct). Sus datos son de
  TradingView, con su retraso; no alimentan ningún cálculo de la terminal.

## 6. Decisiones del usuario (no se hacen sin su aprobación)

- Fuente para el GEX con griegas y OI (Tradier sandbox requiere abrir una cuenta).
- EODHD All World (≈ 20 USD al mes) para cerrar la cobertura BMV, o capturas manuales del portal.
- Llenar `config/capitalizacion_bmv.csv` con las acciones en circulación de las emisoras BMV.
- Energía de Windows y arranque de la terminal al iniciar sesión.
- Subir a GitHub esta entrega.
