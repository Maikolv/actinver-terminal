"""Genera docs/repository-adoption-matrix.md a partir de la inspección real de cada repositorio local
(remoto git, commit, fecha, licencia; ver _renders/inventario.py) y del uso documentado aquí.

Uso: uv run python scripts/matriz_repositorios.py   (requiere los clones en ../<nombre>)
"""
from __future__ import annotations

import re
import subprocess
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BASE = RAIZ.parent
HOY = date(2026, 9, 23)

# nombre: (finalidad comprobada, dependencia que introduce, función en el proyecto, archivo/documento, validación, estado)
USO = {
 # --- A. Núcleo cuantitativo
 "awesome-quant": ("Lista curada de bibliotecas cuantitativas (sin archivo de licencia; contenido de terceros)", "ninguna",
   "Selección de candidatos de backtest y asignación", "docs/quant-methodology.md §Selección",
   "Evaluados: zipline (inactivo), zipline-reloaded (pesado, datos US), backtrader (elegido para verificación cruzada), "
   "skfolio (núcleo). Resultado: backtrader→`terminal/investigacion/backtest.py`", "USADO EN EVALUACIÓN"),
 "awesome-systematic-trading": ("Lista de recursos de trading sistemático (MIT)", "ninguna",
   "Requisitos medibles: sesgo temporal, costos, validación", "docs/quant-methodology.md",
   "Evaluados: backtesting.py (alternativa ligera), gobacktest (Go, no aplica), sección de sesgos → requisitos de purga/embargo y costos",
   "USADO EN EVALUACIÓN"),
 "backtrader": ("Motor de backtesting por eventos en Python (GPL-3.0; último commit 2023: inactivo)", "ninguna en el proyecto (herramienta externa desde el clon local; GPL separado del código MIT)",
   "Verificación cruzada de la contabilidad del backtest (títulos enteros, costos, efectivo)", "terminal/investigacion/backtest.py; tests/test_ampliacion.py",
   "Coincidencia exacta con el cálculo independiente: sintético (72 operaciones, $1,161,000.24) y FRED real (diferencia 0.0)", "INTEGRADO (verificación)"),
 "skfolio": ("Construcción y validación de portafolios sobre scikit-learn (BSD-3)", "skfolio 1.3 (PyPI)",
   "Asignación media-varianza con restricciones del Reto + 6 candidatos (1/N, inversa de volatilidad, CVaR, paridad de riesgo, HRP)",
   "terminal/optimizador.py; terminal/comparador_modelos.py", "tests/test_optimizador.py, tests/test_comparador_modelos.py", "INTEGRADO (núcleo)"),
 "nautilus_trader": ("Plataforma de trading/backtest por eventos de alta fidelidad (LGPL; Rust+Python)", "ninguna",
   "Comparación de conceptos de fidelidad (modelos de llenado y latencia) frente a backtrader", "docs/quant-methodology.md §Backtest",
   "Leídos docs/concepts/backtesting (fill-models, execution-flow); no se instala: su ejecución real no aporta sobre un simulador con precio BMV y sin libro", "USADO EN EVALUACIÓN"),
 "OpenBB": ("Plataforma de investigación con proveedores de datos (AGPL-3.0)", "ninguna",
   "Verificación de cobertura BMV de sus proveedores", "docs/source-matrix.md",
   "git grep: solo `openbb_intrinio/utils/references.py` lista `xmex` (Intrinio, de pago); fred/tiingo/sec/seeking_alpha ya se usan directo. OpenBB no es fuente BMV",
   "USADO EN EVALUACIÓN"),
 "FinceptTerminal": ("Terminal financiera de escritorio (AGPL-3.0, C++/Qt)", "ninguna",
   "Comparación de presentación y conectores", "docs/initial-audit.md §Comparación",
   "git grep: BMV solo como sufijo Yahoo `.MX` (RelationshipMapScreen.cpp:44, CommandBar_Assets.cpp:93) → sin feed BMV licenciado; AGPL impide copiar componentes",
   "USADO EN EVALUACIÓN"),
 "Kronos": ("Modelo fundacional de velas financieras shiyu-coder/Kronos (MIT); identidad verificada en README/model", "ninguna hasta autorizar torch y pesos",
   "Candidato experimental con contexto ≤ t", "terminal/investigacion/kronos_candidato.py; tests/test_ampliacion.py",
   "Interfaz y protocolo sin fuga probados con predictor simulado; ejecución real PENDIENTE de autorizar descarga de torch y NeoQuasar/Kronos-mini", "EVALUACIÓN PENDIENTE DE RECURSOS"),
 "RD-Agent": ("Agente de I+D de Microsoft para factores/modelos (MIT; integra Qlib)", "ninguna",
   "Protocolo de experimentos: registro de intentos y búsqueda solo en entrenamiento", "tabla `experimentos`; docs/quant-methodology.md",
   "Leído README/docs (qlib, factor loop); adoptado el principio de registrar todos los intentos (`prueba_ya_vista`), no su motor (requiere LLM y Docker)",
   "USADO EN EVALUACIÓN"),
 "TradingAgents_TauricResearch": ("FORK vongchu/TradingAgents_TauricResearch del original TauricResearch/TradingAgents (Apache-2.0): agentes LLM que debaten tesis", "ninguna",
   "Contraste de tesis con fuentes y marcas temporales", "docs/repository-adoption-matrix.md (nota de identidad)",
   "git grep: 36 archivos dependen de yfinance/finnhub/alpha_vantage; no se integra (fabricaría contexto sin available_at y sus datos no son BMV). Identidad: fork, no original",
   "USADO EN EVALUACIÓN"),
 "AutoHedge": ("Enjambre de agentes para análisis y ejecución (MIT)", "ninguna",
   "Revisión de controles de riesgo", "docs/quant-methodology.md §Agentes",
   "git grep: módulos de ejecución de órdenes (autohedge/main.py) → no se ejecuta; la terminal no tiene rutas de órdenes (test_no_existen_rutas_de_ordenes_reales)", "NO ADOPTADO"),
 "Vibe-Trading": ("Generación de estrategias con LLM y backtests (MIT)", "ninguna",
   "Comparación de metodología", "docs/quant-methodology.md",
   "Revisado: backtests sin embargo/purga documentados como requisito; se rechaza como fuente de estrategias", "NO ADOPTADO"),
 "trade-journal": ("LuxAlgo/trade-journal: bitácora de operaciones (MIT)", "ninguna",
   "Modelo de bitácora: tesis, entrada/salida confirmada, errores, lecciones, versiones", "terminal/registro.py (bitacora_decisiones); pestaña PASADO",
   "tests/test_ampliacion.py::test_bitacora_exige_decision_humana", "ADOPTADO (método)"),
 "freqtrade": ("Bot de trading cripto (GPL-3.0)", "ninguna",
   "Comparación de controles de sesgo", "docs/quant-methodology.md",
   "Leídos docs/lookahead-analysis.md y backtesting.md: análisis de look-ahead y recursivo → equivalente propio: disparadores available_at y prueba de fuga", "USADO EN EVALUACIÓN"),
 "hummingbot": ("Framework de market making y conectores cripto (Apache-2.0)", "ninguna",
   "Comparación de arquitectura de conectores", "docs/source-matrix.md",
   "Listados 30+ conectores en hummingbot/connector/exchange (binance, kraken, okx…): ninguno de valores ni BMV; no se instala", "USADO EN EVALUACIÓN"),
 "ccxt": ("Biblioteca unificada de exchanges cripto (MIT)", "ninguna",
   "Diferenciar cripto de valores BMV", "terminal/clasificacion.py",
   "Formato unificado BASE/QUOTE[:SETTLE] (ccxt/python/ccxt/base/exchange.py) → PATRON_CRIPTO; tests rechazan BTC/USDT y BINANCE:BTCUSDT", "INTEGRADO (control)"),
 "awesome": ("sindresorhus/awesome: lista de listas (CC0)", "ninguna",
   "Criterios de selección de listas", "docs/repository-adoption-matrix.md",
   "Evaluados: awesome-python, awesome-python-data-science, awesome-python-scientific-audio → criterio: activo, licencia clara, mantenimiento; ningún componente", "USADO EN EVALUACIÓN"),
 # --- B. Agentes, memoria, tokens
 "agentic-inbox": ("Bandeja de correo con agentes sobre Cloudflare (Apache-2.0)", "ninguna",
   "Evaluación como canal de alertas", "docs/token-budget.md §Canales",
   "Requiere cuenta Cloudflare, Email Routing y Durable Objects; sin ventaja frente a correo/Telegram ya implementados", "NO ADOPTADO"),
 "Agent-Reach": ("Panniantong/Agent-Reach: acceso de agentes a sitios públicos (MIT; README en chino)", "ninguna",
   "Investigación de noticias públicas", "docs/sources/seekingalpha.md",
   "Revisado: instala accesos a plataformas sociales; no se usa para Seeking Alpha (se usa su RSS público con enlace)", "NO ADOPTADO"),
 "anything-llm": ("Aplicación RAG local (MIT)", "ninguna",
   "Prototipo de consulta sobre docs", "docs/token-budget.md",
   "Se prefirió el índice local con hashes (scripts/indice_contexto.py) por no requerir servidor ni embeddings", "USADO EN EVALUACIÓN"),
 "awesome-agent-skills": ("Catálogo de habilidades para agentes (MIT)", "ninguna",
   "Selección de habilidades de desarrollo", "docs/token-budget.md",
   "Evaluados: anthropics/pdf, anthropics/webapp-testing, serpapi/agent-usability-test; usada la habilidad de pruebas web (verificación en navegador)", "USADO EN EVALUACIÓN"),
 "awesome-llm-apps": ("Colección de apps LLM (Apache-2.0)", "ninguna",
   "Patrones RAG/evaluación", "docs/token-budget.md",
   "Evaluados: Openwork (automatización de navegador), agente de dictado, patrón RAG con citas → adoptado: respuesta con ruta:línea y cita", "USADO EN EVALUACIÓN"),
 "awesome-mcp-servers": ("Catálogo de servidores MCP (MIT)", "ninguna",
   "Superficie de permisos de conectores", "docs/token-budget.md",
   "Evaluados: aimarket-plugins, modelmarket.dev, creative-claw-marketplace → ninguno de datos BMV; política: no activar MCP sin revisar claves y procedencia", "USADO EN EVALUACIÓN"),
 "codebase-memory-mcp": ("Índice de grafo de código vía MCP (MIT)", "ninguna (herramienta del asistente)",
   "Recuperación de símbolos sin releer archivos", "docs/token-budget.md",
   "Indexado actinver-terminal: 1,193 nodos / 4,837 aristas; búsqueda «precio confiable» devolvió 5 funciones con líneas (~200 tokens vs ~8,000)", "HERRAMIENTA DE DESARROLLO"),
 "context-mode": ("mksglu/context-mode: reducción de contexto para agentes (Elastic License)", "ninguna",
   "Política de ahorro de tokens", "docs/token-budget.md; scripts/indice_contexto.py",
   "Adoptado el método (salida mínima + recuperación puntual), no el código (Elastic License restringe redistribución)", "ADOPTADO (método)"),
 "crewAI": ("Framework multiagente (MIT)", "ninguna",
   "Separación investigación/verificación/auditoría", "docs/quant-methodology.md §Agentes",
   "No mejora frente al flujo determinista (pipeline con pruebas); añadiría LLM en el camino crítico", "NO ADOPTADO"),
 "cline": ("Agente de código para editor (Apache-2.0)", "ninguna",
   "Mantenimiento desde el editor", "README.md §Mantenimiento",
   "Documentado: abrir el proyecto y ejecutar `uv run pytest`; las instrucciones del proyecto están en CLAUDE.md", "HERRAMIENTA DE DESARROLLO"),
 "ollama": ("Modelos LLM locales (MIT)", "opcional (OLLAMA_URL)",
   "Clasificación local de titulares", "terminal/fuentes_web.py",
   "Opcional; Ollama no está instalado en este equipo: se usa el léxico transparente (comparación de calidad pendiente de instalar)", "INTEGRADO (opcional, inactivo)"),
 "colibri": ("JustVugg/colibri: motor de inferencia en C para modelos MoE gigantes (Apache-2.0)", "ninguna",
   "Evaluación de inferencia local", "docs/token-budget.md",
   "README: modelos de 744B–2.8T parámetros en hardware de consumo → recursos excesivos para clasificar titulares; fuera del camino crítico", "NO ADOPTADO"),
 "claude-obsidian": ("Bóveda de notas Markdown para Claude (MIT)", "ninguna",
   "Exportar bitácora/tesis a Markdown", "docs/token-budget.md",
   "La bitácora vive en SQLite con API; exportación Markdown documentada como opción, no implementada", "USADO EN EVALUACIÓN"),
 "docs": ("AMBIGUO: el clon local es plausible/docs (documentación de Plausible Analytics, Docusaurus)", "ninguna",
   "Referencia de medición sin cookies", "docs/matriz.md",
   "Leído: Plausible no aplica (terminal local sin analítica). Nombre «docs» ambiguo: se documenta el clon verificado", "USADO EN EVALUACIÓN"),
 "attention-span": ("alexgreensh/attention-span: estilos de salida concisos para Claude Code (AGPL-3.0)", "ninguna",
   "Resúmenes diarios breves con enlaces", "docs/token-budget.md",
   "Adoptado el criterio «primero la respuesta, lenguaje claro»; no se copia (AGPL)", "ADOPTADO (método)"),
 "hypit": ("hypit-ai/hypit: agentes que crean video (Apache-2.0)", "ninguna",
   "Ninguna función financiera", "docs/repository-adoption-matrix.md",
   "Leído README: edición de video; no se convierte en motor financiero", "NO APLICA"),
 "hypitoken": ("hypit-ai/hypitoken: gateway multiinquilino de API LLM (MIT)", "ninguna",
   "Gestión de tokens/costos de LLM", "docs/token-budget.md",
   "Requiere servidor y credenciales de terceros; el proyecto no usa LLM en el camino crítico", "NO ADOPTADO"),
 "paperclip": ("paperclipai/paperclip: orquestación de equipos de agentes (MIT)", "ninguna",
   "Coordinación de agentes", "docs/repository-adoption-matrix.md", "Leído README; sin necesidad de orquestación en un monitor local", "NO APLICA"),
 "ponytail": ("DietrichGebert/ponytail: estilo de simplificación de código para agentes (MIT)", "ninguna",
   "Criterio de revisión de código", "docs/token-budget.md", "Adoptado como criterio: preferir menos líneas verificables", "ADOPTADO (método)"),
 "Plankton": ("meshmash/Plankton: biblioteca C# de mallas half-edge (LGPL)", "ninguna",
   "Ninguna (geometría)", "docs/repository-adoption-matrix.md", "Leído README: sin relación con finanzas", "NO APLICA"),
 "hyperframes": ("heygen-com/hyperframes: composición de video/HTML (Apache-2.0)", "ninguna",
   "Material visual de presentación", "docs/repository-adoption-matrix.md", "Su estudio se probó localmente en sesiones previas (launch.json de tradingviewmcp); no se usa en el monitor", "NO APLICA"),
 "gods-eye-view": ("bilawalsidhu/gods-eye-view: globo 3D con datos públicos (MIT)", "ninguna",
   "Contexto geográfico", "docs/repository-adoption-matrix.md", "Leído README; no aporta a valuación ni alertas", "NO APLICA"),
 # --- C. Ingesta, revisión y documentos
 "browser-use": ("Automatización de navegador con LLM (MIT)", "ninguna",
   "Pruebas de navegación de páginas de demostración", "docs/13-evidencia.md",
   "Requiere clave de LLM; las pruebas de interfaz se hicieron con el navegador integrado sobre la instancia local. Nunca sobre el portal Actinver", "NO ADOPTADO"),
 "firecrawl": ("Rastreo web como servicio (AGPL-3.0)", "ninguna",
   "Evaluación de extracción autorizada", "docs/sources/seekingalpha.md",
   "Requiere API key de pago o autoalojamiento con Docker; no se usa (Seeking Alpha vía RSS público)", "USADO EN EVALUACIÓN"),
 "Scrapling": ("Framework de scraping adaptable (BSD-3)", "ninguna (entorno aislado uv --with)",
   "Evaluación sobre página pública de práctica", "_renders/prueba_scrapling.py (evidencia en docs/repository-adoption-matrix.md)",
   "quotes.toscrape.com: robots permite, HTTP 200, 1.85 s, 10 citas con su parser. Su evasión anti-bot NO se adopta (prohibido evadir controles)", "USADO EN EVALUACIÓN"),
 "pdf-inspector": ("firecrawl/pdf-inspector: clasificación y extracción de PDF (MIT)", "ninguna (uv --with)",
   "Verificación del PDF de origen", "docs/09-auditoria-pdf.md", "Clasificó «Datos Actinver.pdf» como image_based (11/11 páginas OCR)", "HERRAMIENTA DE DESARROLLO"),
 "whisper": ("openai/whisper: reconocimiento de voz (MIT)", "ninguna",
   "Transcripción de conferencias autorizadas", "docs/repository-adoption-matrix.md",
   "Requiere torch (descarga grande, pendiente de autorización); no ejecutado", "EVALUACIÓN PENDIENTE DE RECURSOS"),
 "yt-dlp": ("Descargador de audio/video (Unlicense)", "ninguna",
   "Descarga de material cuyo acceso esté permitido", "docs/repository-adoption-matrix.md",
   "Documentado; no se descargó material (no hay recurso autorizado identificado)", "USADO EN EVALUACIÓN"),
 "public-apis": ("Lista de APIs públicas (MIT)", "ninguna",
   "Búsqueda de proveedores candidatos", "docs/source-matrix.md",
   "Evaluados: StockData, Real Time Finance, Yahoo Finance (no oficial), entrada «Mex…»: ninguno con licencia BMV verificable", "USADO EN EVALUACIÓN"),
 "claude-for-legal": ("anthropics/claude-for-legal: agentes y habilidades legales (Apache-2.0)", "ninguna",
   "Apoyo documental sobre términos y licencias", "docs/actinver-rules.md; docs/sources/*.md",
   "Usado como lista de verificación (licencia, derechos de uso, redistribución); no sustituye bases oficiales", "USADO EN EVALUACIÓN"),
 "CloudflareSpeedTest": ("XIU2/CloudflareSpeedTest: prueba de IPs/latencia de Cloudflare (GPL-3.0)", "ninguna",
   "Diagnóstico de conectividad (no latencia de mercado)", "docs/repository-adoption-matrix.md",
   "Inspeccionado; no se ejecutó un escaneo de red (no aporta a la latencia de datos bursátiles)", "USADO EN EVALUACIÓN"),
 "CloudflareSpeedTest_duplicates_backup": ("Copia local SIN remoto git del anterior", "ninguna",
   "Ninguna", "docs/repository-adoption-matrix.md",
   "28/28 archivos idénticos por contenido (nombres con « (2)»); faltan CloudflareST.exe, cfst.js y result.csv → respaldo parcial, no fork", "DUPLICADO"),
 # --- D. Diseño, visualización, comunicación, infraestructura
 "archify": ("tt-a1i/archify: diagramas de arquitectura (MIT)", "ninguna",
   "Diagrama de flujo y límites de confianza", "docs/arquitectura.md",
   "Adoptado el enfoque; el diagrama se versiona en Mermaid (texto verificable en GitHub)", "ADOPTADO (método)"),
 "awesome-design-md": ("Colección de archivos DESIGN.md (MIT)", "ninguna",
   "Sistema visual", "DESIGN.md", "Evaluados: formato DESIGN.md de Google Stitch, ejemplos de la colección → creado DESIGN.md", "ADOPTADO (método)"),
 "hallmark": ("Nutlope/hallmark: habilidad de diseño (MIT)", "ninguna",
   "Criterios de panel accesible", "DESIGN.md", "Adoptado: evitar estética genérica; contraste AA verificado con Lighthouse", "ADOPTADO (método)"),
 "open-design": ("nexu-io/open-design: editor de diseño con IA (Apache-2.0)", "ninguna",
   "Prototipo de panel", "DESIGN.md", "Requiere servicio de modelos de pago; no usado", "NO ADOPTADO"),
 "penpot": ("Herramienta de diseño abierta (MPL-2.0)", "ninguna",
   "Prototipo de panel", "DESIGN.md", "No necesario: el panel se prototipa directamente en HTML accesible", "NO ADOPTADO"),
 "netviz": ("ShadowArcanist/netviz: animación de arquitecturas de red (MIT)", "ninguna",
   "Red de fuentes e instrumentos", "docs/arquitectura.md", "Se usa Mermaid para la red de fuentes; netviz sirve para presentaciones", "USADO EN EVALUACIÓN"),
 "worldmonitor": ("koala73/worldmonitor: tablero de noticias globales (AGPL-3.0)", "ninguna",
   "Contexto geopolítico con fuente y fecha", "docs/source-matrix.md", "No se convierte un titular en rendimiento esperado; sin integración (AGPL, servicio propio)", "USADO EN EVALUACIÓN"),
 "pipecat": ("Framework de agentes de voz (BSD-2)", "ninguna",
   "Consulta por voz del estado", "docs/repository-adoption-matrix.md", "Desactivado por defecto; requiere servicios STT/TTS externos", "NO ADOPTADO"),
 "postiz-app": ("Publicación en redes sociales (AGPL-3.0)", "ninguna",
   "Resumen privado", "docs/repository-adoption-matrix.md", "No se publican posiciones ni datos del usuario", "NO ADOPTADO"),
 "claude-ads": ("AgriciDaniel/claude-ads: operaciones de medios pagados (MIT)", "ninguna",
   "Comunicación del proyecto", "docs/repository-adoption-matrix.md", "Publicidad no es variable de mercado; no se conectan cuentas", "NO APLICA"),
 "Open-Higgsfield-AI": ("AMBIGUO: el clon es ClabstreamTeam/Open-Higgsfield-AI, README «Clabstream AI Studio — herramienta interna»; sin licencia", "ninguna",
   "Ninguna", "docs/repository-adoption-matrix.md", "Sin licencia ni propósito de entrenamiento verificable; no se ejecuta", "IDENTIDAD PENDIENTE"),
 "pnpm": ("Gestor de paquetes JavaScript (MIT)", "ninguna",
   "Lockfile reproducible si hubiera componente JS", "README.md", "La interfaz es JavaScript sin dependencias ni build: no hay paquetes que fijar; Python se fija con uv.lock", "NO APLICA"),
 "free-for-dev": ("Lista de planes gratuitos (sin archivo de licencia)", "ninguna",
   "Opciones de alojamiento de un prototipo", "docs/token-budget.md §Costos",
   "Evaluados: Cloudflare Tunnel/Quick Tunnels (para el webhook), Netlify, Render → no se despliega nada sin instrucción del usuario", "USADO EN EVALUACIÓN"),
 "tradingviewmcp": ("deonmenezes/tradingviewmcp: control de TradingView Desktop por CDP (MIT)", "ninguna",
   "Simbología BMV:/NASDAQ: y confirmación visual manual", "terminal/app.py (widget oficial)",
   "Solo convención de símbolos; la extracción automatizada contraviene condiciones de TradingView", "USADO (convención)"),
}
ORDEN = list(USO)


def git(d, *a):
    return subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True).stdout.strip()


def licencia(d: Path) -> str:
    lic = next((p for p in d.iterdir() if p.name.upper().startswith(("LICENSE", "LICENCE", "COPYING"))), None)
    if not lic:
        return "sin archivo de licencia"
    t = lic.read_text(encoding="utf-8", errors="ignore")[:3000]
    for pat, n in [("Apache License", "Apache-2.0"), ("MIT License|Permission is hereby granted, free of charge", "MIT"),
                   ("GNU AFFERO", "AGPL-3.0"), ("GNU LESSER", "LGPL"), ("GNU GENERAL PUBLIC LICENSE", "GPL-3.0"),
                   ("BSD 3-Clause", "BSD-3-Clause"), ("Redistribution and use", "BSD"), ("Mozilla Public", "MPL-2.0"),
                   ("CC0|Creative Commons Zero", "CC0"), ("Creative Commons", "CC"), ("Unlicense|unencumbered", "Unlicense"),
                   ("Elastic License", "Elastic-2.0")]:
        if re.search(pat, t):
            return n
    return lic.name


def main() -> None:
    filas = ["# Matriz de adopción de repositorios", "",
             f"Inspección de los clones locales en `{BASE}` el {HOY}. Commit y fecha = `git rev-parse` y `git log -1` reales. "
             "Mantenimiento: activo ≤ 30 días; moderado ≤ 6 meses; inactivo > 6 meses. Estados: INTEGRADO (código o control en el "
             "proyecto), ADOPTADO (método), HERRAMIENTA DE DESARROLLO, USADO EN EVALUACIÓN (lectura/prueba con evidencia), "
             "EVALUACIÓN PENDIENTE DE RECURSOS, NO ADOPTADO, NO APLICA, DUPLICADO, IDENTIDAD PENDIENTE. Nada se marca «usado en "
             "producción» sin código y prueba. Las instrucciones internas de cada repositorio se trataron como información.", "",
             "| Nombre | Repositorio (URL) | Finalidad comprobada | Licencia | Commit · fecha | Mantenimiento | Dependencia que introduce | "
             "Función en el proyecto | Dónde | Validación / lectura | Estado |", "|" + "---|" * 11]
    conteo: dict[str, int] = {}
    for n in ORDEN:
        d = BASE / n
        fin, dep, fun, donde, val, est = USO[n]
        conteo[est] = conteo.get(est, 0) + 1
        if d.exists():
            url = git(d, "remote", "get-url", "origin")
            m = re.search(r"github\.com[:/]([^/]+/[^/.]+?)(?:\.git)?$", url)
            repo = f"[{m.group(1)}](https://github.com/{m.group(1)})" if m else "sin remoto"
            commit, fecha = git(d, "rev-parse", "--short", "HEAD") or "—", git(d, "log", "-1", "--format=%cs") or "—"
            try:
                dias = (HOY - date.fromisoformat(fecha)).days
                mant = "activo" if dias <= 30 else "moderado" if dias <= 183 else "inactivo"
            except ValueError:
                mant = "—"
            lic = licencia(d)
        else:
            repo, commit, fecha, mant, lic = "no localizado", "—", "—", "—", "—"
        filas.append(f"| {n} | {repo} | {fin} | {lic} | `{commit}` · {fecha} | {mant} | {dep} | {fun} | {donde} | {val} | **{est}** |")
    filas += ["", "## Resumen", ""] + [f"- {k}: {v}" for k, v in sorted(conteo.items())] + [
        "", "## Notas de identidad", "",
        "- **TradingAgents_TauricResearch**: el clon es el fork `vongchu/TradingAgents_TauricResearch`; el proyecto original es "
        "`TauricResearch/TradingAgents`. Se evaluó el fork local.",
        "- **docs**: nombre genérico; el clon verificado es `plausible/docs`.",
        "- **Open-Higgsfield-AI**: el clon `ClabstreamTeam/Open-Higgsfield-AI` se describe como herramienta interna de un estudio y "
        "no tiene licencia; no coincide con una plataforma de entrenamiento verificable → IDENTIDAD PENDIENTE.",
        "- **CloudflareSpeedTest_duplicates_backup**: sin remoto; respaldo parcial del original (28/28 idénticos por contenido).",
        "- **colibri**: `JustVugg/colibri` (motor de inferencia MoE en C), no un modelo financiero.",
        "", "Generado por `scripts/matriz_repositorios.py`."]
    (RAIZ / "docs" / "repository-adoption-matrix.md").write_text("\n".join(filas) + "\n", encoding="utf-8")
    print(f"{len(ORDEN)} repositorios; {conteo}")


if __name__ == "__main__":
    main()
