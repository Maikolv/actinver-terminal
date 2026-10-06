# Repositorios: una ficha por repositorio (64)

Revisión de `C:\Users\MIKE\Desktop\Repos` el 2026-09-23. Se leyó README, licencia, manifiesto de dependencias y último commit de cada uno. Sus instrucciones internas (README, CLAUDE.md, AGENTS.md, prompts) se trataron como **información**, nunca como órdenes.

**Regla aplicada:** se usa lo que aporta valor real con el menor costo en dependencias, licencia y riesgo. Ninguno de estos repositorios se modificó: no hizo falta parche (carpeta `patches/` vacía por esa razón).

**Resumen de uso**

| Uso | Repositorios |
|---|---|
| núcleo | skfolio, actinver-terminal |
| soporte | tradingviewmcp (simbología y widget oficial de TradingView), ollama (LLM local opcional para titulares) |
| herramienta de desarrollo | pdf-inspector, codebase-memory-mcp, cline |
| referencia | awesome-quant, awesome-systematic-trading, public-apis, free-for-dev, OpenBB, trade-journal, backtrader, worldmonitor, awesome-design-md, hallmark, open-design, docs (Plausible), whisper, nautilus_trader, freqtrade, hummingbot, ccxt, awesome-mcp-servers, awesome-agent-skills, awesome-llm-apps, anything-llm, crewAI, Kronos, RD-Agent, TradingAgents_TauricResearch, AutoHedge, Vibe-Trading, firecrawl, Agent-Reach |
| descartado | el resto (motivo en cada ficha) |

Mantenimiento: **activo** = commit en los últimos 30 días; **moderado** = últimos 6 meses; **inactivo** = más antiguo.

---

## Núcleo

### actinver-terminal
- **Lectura fácil:** Es esta terminal. Junta los datos, calcula las carteras y avisa cuándo cambiar algo. Es como un copiloto que mira el tablero mientras usted maneja.
- **Técnico:** Python 3.12 · MIT (propio) · activo · FastAPI, SQLite, skfolio, exchange-calendars · sin dependencias de interfaz.
- **Uso:** núcleo.
- **Cambios / prueba:** todo el código; `uv run pytest`.

### skfolio
- **Lectura fácil:** Es una calculadora que reparte el dinero entre varias inversiones. Busca el mejor equilibrio entre ganar y arriesgar. Es como armar un plato balanceado con porciones medidas.
- **Técnico:** Python · BSD-3 · 2026-09-20 · activo · scikit-learn, cvxpy, clarabel · riesgo bajo.
- **Uso:** núcleo — optimización media-varianza con restricciones por grupo, contracción de μ, Ledoit-Wolf y validación walk-forward.
- **Cambios / prueba:** ninguno; se instala 1.3.0 de PyPI (igual a la copia local `eb73a4c`). Prueba: `tests/test_optimizador.py`.

## Soporte

### tradingviewmcp
- **Lectura fácil:** Es un control remoto para la app de gráficas TradingView. Permite leer y mover la gráfica que usted tiene abierta. Es como pedirle a alguien que le lea la pantalla.
- **Técnico:** Node.js · MIT · 2026-09-20 · activo · Chrome DevTools Protocol · riesgo: automatizar la extracción contraviene las condiciones de TradingView.
- **Uso:** soporte — de él se tomó la convención de símbolos `BMV:`, `NASDAQ:`, `NYSE:`, `AMEX:`; las gráficas se muestran con el **widget oficial** embebible de TradingView (página `/grafica/<id>`). El MCP sirve para confirmación visual manual; no alimenta datos.
- **Cambios / prueba:** ninguno. Solo se añadieron configuraciones de arranque en su carpeta `.claude/` (no versionada) para verificar la terminal; se retiran al terminar. Prueba: abrir `/grafica/SIC:MSFT` (captura en `docs/evidencia/grafica-tradingview.png`).

### ollama
- **Lectura fácil:** Permite correr un modelo de lenguaje en su propia computadora. Nada sale a internet. Es como tener un traductor en casa en vez de llamar a uno.
- **Técnico:** Go/C++ · MIT · 2026-09-18 · activo · modelos de varios GB · no está instalado en este PC.
- **Uso:** soporte opcional — si se define `OLLAMA_URL`, los titulares de alto impacto se clasifican con un LLM local (`terminal/fuentes_web.py`); si no, se usa el léxico transparente.
- **Cambios / prueba:** ninguno. Prueba: instalar Ollama, `ollama pull llama3.2`, definir `OLLAMA_URL=http://127.0.0.1:11434`.

## Herramientas de desarrollo

### pdf-inspector
- **Lectura fácil:** Revisa un PDF y dice si tiene texto o solo fotos. Así sabe uno si hay que leerlo a mano. Es como hojear un libro para ver si viene escrito o dibujado.
- **Técnico:** Rust con bindings Python · MIT · 2026-09-18 · activo · riesgo bajo.
- **Uso:** herramienta de desarrollo — confirmó que «Datos Actinver.pdf» es `image_based` (11/11 páginas requieren OCR, confianza 0.8); por eso se transcribió visualmente y se verificó cada clave contra fuentes oficiales.
- **Cambios / prueba:** ninguno. `uv run --with pdf-inspector python -c "import pdf_inspector as p; print(p.classify_pdf(r'C:\Users\MIKE\Desktop\Datos Actinver.pdf'))"`.

### codebase-memory-mcp
- **Lectura fácil:** Hace un mapa del código para encontrar cosas rápido. Es como el índice al final de un libro.
- **Técnico:** MIT · 2026-09-20 · activo · servidor MCP.
- **Uso:** herramienta de desarrollo (disponible para el asistente); no forma parte de la terminal.
- **Cambios:** ninguno.

### cline
- **Lectura fácil:** Es un asistente de programación dentro del editor. Escribe y corrige código a petición. Es como un copiloto para programar.
- **Técnico:** TypeScript · Apache-2.0 · 2026-09-19 · activo.
- **Uso:** herramienta de desarrollo opcional para mantener el código; no es dependencia.
- **Cambios:** ninguno.

## Referencia (se consultaron; no se ejecutan)

### awesome-quant
- **Lectura fácil:** Es una lista de herramientas para finanzas cuantitativas. Ayuda a elegir sin reinventar. Es como la guía de restaurantes de una ciudad.
- **Técnico:** lista · 2026-09-13 · activo.
- **Uso:** referencia — de aquí salieron skfolio y exchange-calendars (calendarios NYSE/BMV).
- **Cambios:** ninguno.

### awesome-systematic-trading
- **Lectura fácil:** Otra lista de herramientas, enfocada en estrategias automáticas. Sirve para comparar opciones.
- **Técnico:** lista · MIT · 2026-08-30 · activo.
- **Uso:** referencia — confirma que no hace falta un motor de backtesting de órdenes para asignación de cartera.
- **Cambios:** ninguno.

### public-apis
- **Lectura fácil:** Es un directorio de servicios con datos en internet. Dice cuáles piden clave. Es como un directorio telefónico de datos.
- **Técnico:** lista · MIT · 2026-09-19 · activo.
- **Uso:** referencia — candidatos EODHD, FRED, Alpha Vantage, Twelve Data, FMP; se eligieron FRED, Banxico, Tiingo, EODHD y Barchart.
- **Cambios:** ninguno.

### free-for-dev
- **Lectura fácil:** Lista de servicios con plan gratuito. Ayuda a no pagar de más.
- **Técnico:** lista · 2026-09-18 · activo.
- **Uso:** referencia para planes gratuitos de datos y notificaciones.
- **Cambios:** ninguno.

### OpenBB
- **Lectura fácil:** Es una plataforma con muchas fuentes de datos financieros juntas. Es muy completa y pesada. Es como una biblioteca entera cuando solo necesita tres libros.
- **Técnico:** Python · AGPL-3.0 · 2026-07-20 · moderado · decenas de dependencias · AGPL obliga a publicar el código si se ofrece en red.
- **Uso:** referencia — los mismos proveedores se cubren con adaptadores pequeños; candidato si en el futuro se necesitan decenas de fuentes.
- **Cambios:** ninguno.

### trade-journal
- **Lectura fácil:** Es un diario para anotar operaciones y ver qué funciona. Es como una libreta de gastos, pero de inversiones.
- **Técnico:** TypeScript + SQLite · MIT · 2026-09-19 · activo · Node 22 + pnpm.
- **Uso:** referencia — inspiró el libro inmutable con auditoría; el cálculo de costo promedio se escribió en Python con pruebas.
- **Cambios:** ninguno.

### backtrader
- **Lectura fácil:** Es una máquina del tiempo para probar ideas de inversión con precios viejos. Dice qué habría pasado.
- **Técnico:** Python · GPL-3.0 · 2023-04-19 · inactivo.
- **Uso:** referencia — la validación se hace con el walk-forward de skfolio (más adecuado para carteras y mantenido).
- **Cambios:** ninguno.

### nautilus_trader
- **Lectura fácil:** Es un motor profesional para probar y ejecutar estrategias de trading. Muy rápido y complejo.
- **Técnico:** Rust/Python · LGPL-3.0 · 2026-09-20 · activo · pesado.
- **Uso:** referencia — su modo de backtest no aporta a asignación de cartera; la ejecución está prohibida en este proyecto.
- **Cambios:** ninguno.

### freqtrade
- **Lectura fácil:** Es un robot que compra y vende criptomonedas solo. Aquí no se usa porque no se opera.
- **Técnico:** Python · GPL-3.0 · 2026-09-19 · activo.
- **Uso:** referencia — ideas de gestión de límites de peticiones; sin trading.
- **Cambios:** ninguno.

### hummingbot
- **Lectura fácil:** Es un robot que pone precios de compra y venta en casas de cambio cripto. Fuera del alcance.
- **Técnico:** Python · Apache-2.0 · 2026-07-30 · moderado.
- **Uso:** referencia — reconexión y reintentos; sin trading.
- **Cambios:** ninguno.

### ccxt
- **Lectura fácil:** Es un traductor para hablar con cien casas de cambio de criptomonedas. No aplica a la BMV.
- **Técnico:** JS/Python · MIT · 2026-09-20 · activo.
- **Uso:** referencia — patrón de adaptadores con interfaz común; sin trading.
- **Cambios:** ninguno.

### worldmonitor
- **Lectura fácil:** Es un tablero de noticias del mundo en tiempo real. Junta muchas fuentes. Es como un noticiero con muchas pantallas.
- **Técnico:** TypeScript · AGPL-3.0 · 2026-09-20 · activo.
- **Uso:** referencia — la terminal usa solo el calendario macro de ForexFactory y titulares por emisora; un tablero geopolítico no mejora las propuestas.
- **Cambios:** ninguno.

### awesome-design-md
- **Lectura fácil:** Colección de guías de diseño en texto. Ayuda a mantener un estilo coherente.
- **Técnico:** lista · MIT · 2026-07-31.
- **Uso:** referencia para evitar apariencia de plantilla.
- **Cambios:** ninguno.

### hallmark
- **Lectura fácil:** Es una guía para que las interfaces no parezcan hechas en serie. Da reglas de tipografía y espacio.
- **Técnico:** MIT · 2026-08-06.
- **Uso:** referencia de principios (paleta reducida, jerarquía tipográfica, sin adornos).
- **Cambios:** ninguno.

### open-design
- **Lectura fácil:** Es una herramienta abierta para diseñar pantallas con ayuda de IA.
- **Técnico:** TypeScript · Apache-2.0 · 2026-09-20 · activo.
- **Uso:** referencia; la interfaz se construyó directamente en HTML/CSS.
- **Cambios:** ninguno.

### docs (Plausible)
- **Lectura fácil:** Es el manual de una analítica web que respeta la privacidad.
- **Técnico:** Docusaurus · CC · 2026-09-18.
- **Uso:** referencia — opción de medición sin cookies si algún día se publica (ver `docs/matriz.md`).
- **Cambios:** ninguno.

### whisper
- **Lectura fácil:** Convierte audio en texto. Sirve para transcribir charlas.
- **Técnico:** Python · MIT · 2026-08-31 · modelos pesados.
- **Uso:** referencia — útil para transcribir webinars del Reto por cuenta del usuario (`whisper charla.mp3 --language Spanish`); no se integra en la terminal.
- **Cambios:** ninguno.

### awesome-mcp-servers · awesome-agent-skills · awesome-llm-apps
- **Lectura fácil:** Listas de complementos y ejemplos para asistentes de IA. Sirven para descubrir herramientas.
- **Técnico:** listas · MIT/Apache-2.0 · activos.
- **Uso:** referencia; ninguna herramienta listada era necesaria.
- **Cambios:** ninguno.

### anything-llm
- **Lectura fácil:** Es un chat que conversa con sus documentos. Puede usar un modelo local.
- **Técnico:** Node · MIT · 2026-09-17 · activo · tiene `.env` locales con secretos (ignorados por Git).
- **Uso:** referencia — para resumir titulares basta Ollama directo; no se añade un servidor más.
- **Cambios:** ninguno.

### crewAI
- **Lectura fácil:** Organiza varios agentes de IA que trabajan en equipo.
- **Técnico:** Python · MIT · 2026-09-19 · activo.
- **Uso:** referencia — un análisis multiagente de noticias añadiría costo y no reproducibilidad; la clasificación de titulares es un léxico explicable (+ LLM local opcional).
- **Cambios:** ninguno.

### Kronos
- **Lectura fácil:** Es un modelo que intenta adivinar precios futuros a partir de velas. Aquí no se usa para no prometer rendimientos.
- **Técnico:** Python/PyTorch · MIT · 2026-04-13 · moderado · ~900 MB.
- **Uso:** referencia — pronósticos puntuales de precio contradicen «no prometer rendimiento»; la incertidumbre se muestra con escenarios.
- **Cambios:** ninguno.

### RD-Agent
- **Lectura fácil:** Un asistente de IA que busca «factores» que expliquen los precios. Es investigación avanzada.
- **Técnico:** Python · MIT · 2026-09-15 · activo · requiere LLM y mucho cómputo.
- **Uso:** referencia — alto riesgo de sobreajuste en 7 semanas de Reto.
- **Cambios:** ninguno.

### TradingAgents_TauricResearch · AutoHedge · Vibe-Trading
- **Lectura fácil:** Agentes de IA que deciden compras y ventas. Aquí solo se permite explicar, nunca ordenar.
- **Técnico:** Python · Apache-2.0/MIT · 2026-03 a 09 · dependen de LLM de pago · AutoHedge «opera por usted» y su `.env` define `WALLET_PRIVATE_KEY` (vacía).
- **Uso:** referencia — decisiones no reproducibles y orientadas a ejecutar; incompatibles con la prohibición de operar.
- **Cambios:** ninguno.

### firecrawl · Agent-Reach
- **Lectura fácil:** Herramientas para leer páginas web de forma automática.
- **Técnico:** AGPL-3.0 / MIT · activos.
- **Uso:** referencia — las fuentes se consumen por feed/API oficial; no se extraen páginas.
- **Cambios:** ninguno.

## Descartados

### Scrapling
- **Lectura fácil:** Lee páginas web aunque intenten bloquear robots. Eso rompería las reglas de los sitios.
- **Técnico:** Python · BSD-3 · 2026-09-14.
- **Uso:** descartado — evadir protecciones anti-bot (p. ej. Stooq) está prohibido.

### browser-use
- **Lectura fácil:** Una IA que maneja el navegador sola. Aquí no hace falta y podría violar condiciones de uso.
- **Técnico:** Python · MIT · 2026-09-15 · `.env` con valor de ejemplo.
- **Uso:** descartado.

### FinceptTerminal
- **Lectura fácil:** Otra terminal financiera completa, en C++. Es grande y con edición comercial.
- **Técnico:** C++/Qt · AGPL-3.0 · 2026-09-19.
- **Uso:** descartado — otra pila y licencia copyleft; no aporta a una terminal mínima.

### gods-eye-view
- **Lectura fácil:** Un globo terráqueo 3D con aviones y barcos en vivo. Muy vistoso, sin relación con carteras.
- **Técnico:** TypeScript · MIT · 2026-09-16.
- **Uso:** descartado.

### CloudflareSpeedTest
- **Lectura fácil:** Mide qué servidores de Cloudflare responden más rápido. Sirve para redes, no para bolsa.
- **Técnico:** Go · GPL-3.0 · 2026-09-15.
- **Uso:** descartado — mide IP de Cloudflare, no la latencia de las fuentes; la terminal mide el retraso real de cada dato («retraso» en la pestaña Datos).

### CloudflareSpeedTest_duplicates_backup
- **Lectura fácil:** Es una copia repetida de la carpeta anterior. No tiene nada nuevo.
- **Técnico:** sin Git · GPL-3.0.
- **Uso:** descartado — **duplicado verificado**: sus 28 archivos son idénticos byte a byte a los de CloudflareSpeedTest (solo cambia el sufijo « (2)» en el nombre).
- **Eliminado el 6-oct-2026 por orden del usuario** («Elíminalo»). Antes se volvió a verificar: 28/28 archivos idénticos. Respaldo: `Desktop/Repos/_respaldos/CloudflareSpeedTest_duplicates_backup_2026-10-06.zip` (28 entradas). La carpeta se envió a la Papelera de reciclaje de Windows, así que se puede restaurar.

### agentic-inbox
- **Lectura fácil:** Un buzón de correo atendido por IA.
- **Técnico:** TypeScript · Apache-2.0 · 2026-04-17 · cambios locales en `wrangler.jsonc` (sin secretos).
- **Uso:** descartado — las alertas por correo usan SMTP estándar configurado por el usuario.

### archify
- **Lectura fácil:** Dibuja diagramas de arquitectura a partir de una descripción.
- **Técnico:** MIT · 2026-09-21.
- **Uso:** descartado — los diagramas de la documentación son texto.

### attention-span
- **Lectura fácil:** Estilos de respuesta para asistentes de IA más breves.
- **Técnico:** AGPL-3.0 · 2026-09-06.
- **Uso:** descartado (no es parte del producto).

### awesome
- **Lectura fácil:** La lista madre de listas «awesome».
- **Técnico:** CC0.
- **Uso:** descartado.

### claude-ads · claude-for-legal · claude-obsidian
- **Lectura fácil:** Habilidades de IA para publicidad, temas legales y notas.
- **Técnico:** MIT/Apache-2.0 · activos.
- **Uso:** descartado — fuera del dominio.

### colibri
- **Lectura fácil:** Motor para correr modelos de IA gigantes en equipos normales.
- **Técnico:** C · Apache-2.0 · 2026-09-15.
- **Uso:** descartado — Ollama cubre el LLM local opcional.

### context-mode
- **Lectura fácil:** Complemento que administra el contexto de un asistente de IA.
- **Técnico:** Elastic License 2.0 (no abierta) · 2026-09-20.
- **Uso:** descartado — licencia no reutilizable.

### hyperframes · hypit
- **Lectura fácil:** Herramientas para crear videos con código o con agentes.
- **Técnico:** Apache-2.0 · 2026-09-20.
- **Uso:** descartado.

### hypitoken
- **Lectura fácil:** Pasarela que reparte peticiones de IA entre muchas cuentas.
- **Técnico:** Go · MIT · 2026-09-18 · riesgo de uso indebido de credenciales.
- **Uso:** descartado.

### netviz
- **Lectura fácil:** Dibuja y anima diagramas de redes.
- **Técnico:** MIT · 2026-09-07.
- **Uso:** descartado.

### Open-Higgsfield-AI
- **Lectura fácil:** Herramienta interna de un estudio de video.
- **Técnico:** sin licencia (todos los derechos reservados) · 2026-04-19.
- **Uso:** descartado — sin licencia no se puede reutilizar.

### paperclip
- **Lectura fácil:** Administrador de agentes de IA para el trabajo.
- **Técnico:** TypeScript · MIT · 2026-09-20 · `.env` local con secretos (ignorado por Git; ver `docs/seguridad.md`).
- **Uso:** descartado.

### penpot
- **Lectura fácil:** Programa abierto de diseño, parecido a Figma.
- **Técnico:** Clojure · MPL-2.0 · 2026-09-20.
- **Uso:** descartado — no se necesitó un archivo de diseño aparte.

### pipecat
- **Lectura fácil:** Marco para asistentes de voz en tiempo real.
- **Técnico:** Python · BSD-2 · 2026-09-19.
- **Uso:** descartado.

### Plankton
- **Lectura fácil:** Biblioteca de geometría 3D para C#.
- **Técnico:** C# · LGPL-3.0 · 2026-09-20 · 1 commit local sin publicar del usuario.
- **Uso:** descartado.

### pnpm
- **Lectura fácil:** Instalador de paquetes de JavaScript.
- **Técnico:** MIT · 2026-09-20.
- **Uso:** descartado — la terminal no usa Node en ejecución.

### ponytail
- **Lectura fácil:** Habilidad que hace que un asistente de IA escriba menos código y más simple.
- **Técnico:** MIT · 2026-09-14.
- **Uso:** descartado como dependencia; su idea (lo mínimo necesario) guió el diseño.

### postiz-app
- **Lectura fácil:** Programa publicaciones en redes sociales.
- **Técnico:** AGPL-3.0 · 2026-09-19.
- **Uso:** descartado — la terminal no publica nada.

### yt-dlp
- **Lectura fácil:** Descarga videos de internet.
- **Técnico:** Python · Unlicense · 2026-09-16.
- **Uso:** descartado — descargar webinars queda a decisión y responsabilidad del usuario según los términos de cada plataforma.
