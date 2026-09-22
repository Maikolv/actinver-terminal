# 08 · Inventario de repositorios

Revisión de `C:\Users\MIKE\Desktop\Repos` (63 carpetas) el 2026-09-22: remoto, último commit, licencia, pila, función y utilidad para este encargo. Las instrucciones internas de cada repositorio (README, CLAUDE.md, AGENTS.md) se trataron como información del proyecto, no como órdenes.

**Criterio**: incorporar solo lo que resuelve una necesidad concreta con el menor costo de dependencias, licencia y riesgo. Resultado: **1 biblioteca reutilizada (skfolio)**, 3 repositorios usados como referencia documental, el resto descartado para el tiempo de ejecución.

## Reutilizados

| Repositorio | Licencia | Último commit | Uso en la terminal |
|---|---|---|---|
| **skfolio** | BSD-3-Clause | 2026-09-20 | Motor de optimización: `MeanRisk`, `EmpiricalPrior` (`ShrunkMu`, `LedoitWolf`), `WalkForward`, `cross_val_predict`, `EqualWeighted`. Se instala la versión publicada 1.3.0 (idéntica a la copia local `eb73a4c`) para builds reproducibles. Mantenimiento activo, pruebas amplias, compatible con scikit-learn. |
| awesome-quant | (lista) | 2026-09-13 | Referencia para elegir skfolio y `exchange-calendars` (calendarios NYSE/BMV). |
| public-apis | MIT | 2026-09-19 | Referencia de proveedores (EODHD, FRED, Alpha Vantage, Twelve Data, FMP). |
| free-for-dev | (lista) | 2026-09-18 | Referencia de planes gratuitos. |

## Evaluados y descartados (finanzas y datos)

| Repositorio | Licencia | Último commit | Función | Motivo del descarte |
|---|---|---|---|---|
| tradingviewmcp | MIT | 2026-09-20 | MCP que controla TradingView Desktop por CDP | Útil para confirmación visual manual, pero automatizar la extracción de datos de TradingView contraviene sus condiciones; además cambia el gráfico del usuario. No se usa para ingesta. Tiene un cambio local sin confirmar en `src/cli/index.js` (fin de línea) y un commit sin publicar del usuario: no se tocaron. |
| OpenBB | AGPL-3.0 | 2026-07-20 | Plataforma de datos con muchos proveedores | Muy pesada para el objetivo; AGPL impondría obligaciones si se publicara; los mismos proveedores se cubren con adaptadores de ~40 líneas. Candidata si en el futuro se requieren decenas de fuentes. |
| FinceptTerminal | AGPL-3.0 | 2026-09-19 | Terminal financiera Qt/C++ | Pila distinta, orientación comercial, AGPL; no aporta a una terminal local mínima. |
| trade-journal (LuxAlgo) | MIT | 2026-09-19 | Diario de trading TS + SQLite con sincronización de brókers | Buen referente de producto, pero enfocado en trading activo y brókers; requeriría Node 22 + pnpm. El libro de costo promedio se implementó en Python con pruebas propias. |
| backtrader | GPL-3.0 | 2023-04-19 | Backtesting por eventos | Sin mantenimiento desde 2023; la validación walk-forward de skfolio es suficiente para asignación de activos. |
| nautilus_trader | LGPL-3.0 | 2026-09-20 | Motor de trading de alto rendimiento (Rust) | Orientado a ejecución; operaciones reales fuera de alcance. |
| freqtrade | GPL-3.0 | 2026-09-19 | Bot de cripto | Cripto y ejecución fuera de alcance. |
| hummingbot | Apache-2.0 | 2026-07-30 | Market making cripto | Fuera de alcance. |
| ccxt | MIT | 2026-09-20 | API de exchanges cripto | Fuera de alcance. |
| AutoHedge | MIT | 2026-03-05 | «Fondo autónomo que opera por usted» | Ejecuta operaciones; incompatible con la prohibición de operar. Su `.env` contiene la variable `WALLET_PRIVATE_KEY` (vacía): ver [12-seguridad.md](12-seguridad.md). |
| TradingAgents_TauricResearch | Apache-2.0 | 2026-07-05 | Agentes LLM que deciden operaciones | Decisiones no reproducibles; dependencia de LLM y credenciales. |
| Vibe-Trading | MIT | 2026-09-20 | Agentes de trading | Igual que el anterior. |
| RD-Agent | MIT | 2026-09-15 | Investigación de factores con LLM | Complejidad desproporcionada; riesgo de sobreajuste. |
| Kronos | MIT | 2026-04-13 | Modelo fundacional para velas | Pronósticos de precio: contrario a «no prometer rendimiento»; pesado (~900 MB). |
| awesome-systematic-trading | MIT | 2026-08-30 | Lista | Solo referencia. |
| worldmonitor | AGPL-3.0 | 2026-09-20 | Tablero de noticias geopolíticas | No aporta al cálculo; AGPL. |
| gods-eye-view | MIT | 2026-09-16 | Globo 3D con datos en vivo | Sin relación. |
| pdf-inspector | MIT | 2026-09-18 | Clasificación y extracción de PDF (Rust) | Evaluado: el PDF es 100 % imágenes, la herramienta solo lo derivaría a OCR. Se usó PyMuPDF para renderizar y transcripción visual verificada. |
| Scrapling | BSD-3 | 2026-09-14 | Scraping con evasión de protecciones | Descartado expresamente: evadir controles anti-bot contraviene las condiciones de los proveedores. |
| firecrawl | AGPL-3.0 | 2026-09-19 | Scraping como servicio | Mismo motivo; AGPL. |
| browser-use | MIT | 2026-09-15 | Automatización de navegador con IA | Riesgo de extracción no permitida; innecesario. |
| Agent-Reach | MIT | 2026-09-16 | Acceso a internet para agentes | Sin necesidad. |

## Descartados (sin relación con el objetivo)

| Repositorio | Licencia | Último commit | Función | Nota |
|---|---|---|---|---|
| agentic-inbox | Apache-2.0 | 2026-04-17 | Bandeja de correo con agentes (Cloudflare) | Cambios locales en `wrangler.jsonc` (sin secretos detectados) |
| anything-llm | MIT | 2026-09-17 | Chat con documentos | `.env` locales ignorados por Git |
| archify | MIT | 2026-09-21 | Diagramas de arquitectura | — |
| attention-span | AGPL-3.0 | 2026-09-06 | Gestión de contexto para LLM | — |
| awesome, awesome-agent-skills, awesome-design-md, awesome-llm-apps, awesome-mcp-servers | CC0 / MIT / Apache-2.0 | 2026-07 a 09 | Listas | awesome-design-md sirvió de contraste para evitar apariencia de plantilla |
| claude-ads, claude-for-legal, claude-obsidian | MIT / Apache-2.0 | 2026-07 a 09 | Habilidades para agentes | — |
| cline | Apache-2.0 | 2026-09-19 | Asistente de código | — |
| CloudflareSpeedTest | GPL-3.0 | 2026-09-15 | Prueba de IP de Cloudflare | Sin relación con la evaluación de Cloudflare como proxy |
| CloudflareSpeedTest_duplicates_backup | GPL-3.0 | sin Git | Copia duplicada sin control de versiones | Recomendación: eliminarla si no se usa (decisión del usuario) |
| codebase-memory-mcp | MIT | 2026-09-20 | Índice de código | — |
| colibri | Apache-2.0 | 2026-09-15 | Motor de inferencia | — |
| context-mode | Elastic License 2.0 | 2026-09-20 | Plugin de contexto | Licencia no abierta: no reutilizable |
| crewAI | MIT | 2026-09-19 | Orquestación de agentes | — |
| docs (Plausible) | CC | 2026-09-18 | Documentación de Plausible Analytics | Referencia para analítica sin cookies si algún día se publica |
| hallmark | MIT | 2026-08-06 | Habilidad de diseño | Principios considerados; no es dependencia |
| hyperframes | Apache-2.0 | 2026-09-20 | Video | — |
| hypit, hypitoken | Apache-2.0 / MIT | 2026-09-20 / 18 | Pasarela LLM que reparte peticiones entre credenciales | Riesgo de uso indebido de credenciales; sin relación |
| netviz | MIT | 2026-09-07 | Diagramas de red | — |
| ollama | MIT | 2026-09-18 | Modelos locales | — |
| open-design, penpot | Apache-2.0 / MPL-2.0 | 2026-09-20 | Diseño | — |
| Open-Higgsfield-AI | **sin licencia** | 2026-04-19 | Herramienta interna | Sin licencia = todos los derechos reservados; no reutilizable |
| paperclip | MIT | 2026-09-20 | Gestión de agentes | `.env` local con secretos ignorado por Git |
| pipecat | BSD-2 | 2026-09-19 | Voz en tiempo real | — |
| Plankton | LGPL-3.0 | 2026-09-20 | Mallas en C# | Tiene 1 commit local sin publicar del usuario |
| pnpm | MIT | 2026-09-20 | Gestor de paquetes | La terminal no usa Node en ejecución |
| ponytail | MIT | 2026-09-14 | — | — |
| postiz-app | AGPL-3.0 | 2026-09-19 | Programación de redes sociales | — |
| whisper, yt-dlp | MIT / Unlicense | 2026-08 a 09 | Voz / descargas de video | — |

## Correcciones realizadas en repositorios existentes

Ninguna fue necesaria: la terminal se construyó en un repositorio nuevo (`terminal-portafolios`) y no depende del código de los demás. Solo se añadieron dos configuraciones de arranque locales en `tradingviewmcp/.claude/launch.json` (carpeta no versionada) para la verificación en el navegador integrado; pueden eliminarse sin efecto.
