"""Procedencia y temporalidad declaradas para cada sección de la terminal."""
from __future__ import annotations
import re
from pathlib import Path

# Clave = id de pestaña en navegacion.json. Una sección nueva exige una declaración aquí.
# «Vigencia» describe el criterio visible, no promete que el dato esté actualizado.
SECCIONES = {
    "tab-resumen": ("Plan y precios de cartera", "Captura manual del Reto; cierres BMV y referencia de origen", "Según cada precio y captura", "Se bloquea sin captura o precio confiable"),
    "tab-cartera": ("Posiciones y valuación", "Captura manual del portal; precios con proveedor", "Según última captura y precio", "Fecha y estado por posición"),
    "tab-portafolios": ("Historias y propuesta simulada", "Precios guardados; Ranking; CETES Banxico o respaldo declarado", "Cierres diarios; tasa semanal", "Ventana y fechas de entrenamiento visibles"),
    "tab-propuestas": ("Carteras comparadas", "Precios guardados y perfil local", "Según proveedor de cada precio", "Fecha, fuente y estado por dato"),
    "tab-alertas": ("Condiciones informativas", "Precios guardados y reglas locales", "Según proveedor de cada precio", "Solo con datos confiables"),
    "tab-perfil": ("Reglas y preferencias", "Captura manual del Reto y configuración local", "Según última captura", "Fecha de captura visible"),
    "tab-mercado": ("Índices y mapas", "TradingView externo; precios locales con proveedor", "Retraso propio del widget; no alimenta cálculos", "Cada precio local muestra su estado"),
    "tab-velas": ("Barras e indicadores", "Alpaca, EODHD o historia guardada; IEX parcial", "SIP diferido; IEX parcial", "Hora y tipo de dato visibles"),
    "tab-orderflow": ("Operaciones y perfiles", "Alpaca SIP o flujo IEX parcial", "SIP diferido; IEX parcial", "Solo sesiones y operaciones observadas"),
    "tab-optionflow": ("Cadena y GEX indicativo", "Alpaca opciones y contratos Paper de solo lectura", "Cadena indicativa; OI de cierre previo", "Spot de misma referencia a ≤ 60 s o sin GEX"),
    "tab-riesgo": ("VaR y exposición", "Posiciones manuales y cierres guardados", "Cierres diarios", "Ventana histórica y precios fechados"),
    "tab-asistente": ("Respuestas sobre datos locales", "Base local y notas del usuario; modelo opcional", "Hereda fecha de cada dato", "No genera cotización vigente"),
    "tab-tiempo": ("Operaciones y boletas", "Registro manual local y captura del Reto", "Según fecha de registro", "Estado de ejecución declarado"),
    "tab-ranking": ("Clasificación del universo", "Cierres guardados, SEC y capitalización BMV disponible", "Cierres diarios; caché fechada", "Tipo y estado por fila"),
    "tab-robustez": ("Pruebas fuera de muestra", "Series históricas guardadas", "Cierres históricos", "Tramo intacto y costos visibles"),
    "tab-movimientos": ("Insiders y posiciones públicas", "SEC EDGAR Form 4 y 13F", "Publicación regulatoria", "Fecha de presentación visible"),
    "tab-investigacion": ("Noticias y macro", "Fuentes públicas configuradas", "Según fuente y publicación", "Fecha y disponibilidad por registro"),
    "tab-modelos": ("Pronósticos experimentales", "Historias guardadas y experimentos locales", "Datos disponibles al corte", "Pronóstico separado de cotización"),
    "tab-seguimiento": ("Evolución de cartera", "Operaciones manuales y cierres guardados", "Cierres diarios", "Fechas y fuente de precios visibles"),
    "tab-backtesting": ("Pruebas históricas", "Series guardadas", "Cierres históricos", "Huella y periodo de la corrida"),
    "tab-intradia": ("Contexto informativo", "Datos IEX parciales o barras disponibles", "Según feed; IEX parcial", "Sin señal con dato diario o diferido"),
    "tab-universo": ("Cobertura y procedencia", "Registro de proveedores y catálogo local", "Según última consulta", "Vigencia por instrumento"),
    "tab-ayuda": ("Guías y referencias", "Documentación local", "Según versión de la terminal", "No contiene cotizaciones"),
}


def tabla() -> list[dict[str, str]]:
    return [{"seccion": clave, "dato": dato, "fuente": fuente, "retraso": retraso, "vigencia": vigencia}
            for clave, (dato, fuente, retraso, vigencia) in SECCIONES.items()] + tabla_mesa()


def tabla_mesa() -> list[dict[str, str]]:
    """Familias de Mesa derivadas de su catálogo real, sin mantener otra lista de paneles."""
    src = (Path(__file__).resolve().parents[1] / "web/static/mesa.mjs").read_text(encoding="utf-8")
    bloque = src.split("export const CATALOGO = [", 1)[1].split("];", 1)[0]
    paneles = re.findall(r"\['([^']+)','([^']+)','([^']+)'", bloque)
    familias = [
        ("externos", lambda t: t not in ("link", "risk"), "TradingView externo, no alimenta modelos", "Propio del proveedor, puede ser indicativo o retrasado", "HTTP 200 solo verifica el marco; contenido y vigencia externos sin verificar"),
        ("accesos locales", lambda t: t == "link", "Sección nativa y sus fuentes declaradas", "Hereda el retraso de la sección de destino", "No añade datos; comprobar fecha y estado en destino"),
        ("calculadora manual", lambda t: t == "risk", "Entradas manuales de estudio, solo NQ", "No recibe cotizaciones", "Sin precio conectado ni señal; tope del escenario, no del fill real"),
    ]
    return [{"seccion": f"Mesa · {nombre} ({len(filas)})", "dato": ", ".join(f[1] for f in filas),
             "fuente": fuente, "retraso": retraso, "vigencia": vigencia}
            for nombre, filtro, fuente, retraso, vigencia in familias
            for filas in [[f for f in paneles if filtro(f[2])]]]
