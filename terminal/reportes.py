"""Reportes automáticos en Markdown: pre-apertura (08:00), cierre (15:15) y semanal del Reto.

Solo leen lo que ya calcula la terminal; nunca inventan un dato. Cada cifra lleva su fecha y su vigencia, y si una
propuesta está suspendida o desactualizada el reporte lo dice en lugar de mostrarla como actual.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from . import alertas, reto, servicios
from .config import Ajustes, data_dir

log = logging.getLogger("terminal.reportes")
TIPOS = {"preapertura": "Reporte de pre-apertura", "cierre": "Reporte de cierre", "semanal": "Reporte semanal del Reto"}
_MX = "America/Mexico_City"


def _pct(x, dec=1) -> str:
    return "s/d" if x is None else f"{x * 100:+.{dec}f} %"


def _mxn(x) -> str:
    return "s/d" if x is None else f"{x:,.0f} MXN"


def _hora_mx(iso: str) -> str:
    try:
        from zoneinfo import ZoneInfo
        return datetime.fromisoformat(iso).astimezone(ZoneInfo(_MX)).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return iso or "s/d"


def _seccion_reto() -> list[str]:
    r = reto.resumen()
    if not r.get("activo"):
        return []
    f = r.get("fechas") or {}
    out = ["## Reto Actinver 2026", f"- Etapa: **{r['etapa']}** · sesiones de la BMV restantes: {r['sesiones_restantes']}",
           f"- Capital: {_mxn(r.get('capital'))} · costo por operación: {_pct(r.get('costo_operacion'), 3)}"]
    if f:
        out.append("- Fechas: " + " · ".join(f"{k}: {v}" for k, v in f.items()))
    if r.get("sin_confirmar"):
        out.append("- ⚠ Reglas sin confirmar: " + "; ".join(r["sin_confirmar"]))
    return out + [""]


def _seccion_cartera(cart: dict) -> list[str]:
    out = ["## Cartera registrada"]
    if not cart.get("n_operaciones"):
        return out + ["Sin operaciones registradas todavía.", ""]
    out.append(f"- Valor total: **{_mxn(cart.get('valor_total'))}** · efectivo: {_mxn(cart.get('efectivo'))} · "
               f"vigencia del conjunto: **{cart.get('vigencia')}**")
    if not cart.get("completa", True):
        out.append("- ⚠ Hay posiciones sin precio: el valor total es parcial.")
    if cart.get("posiciones"):
        out += ["", "| Emisora | Peso | Valor | Vigencia | Precio al |", "|---|---:|---:|---|---|"]
        for p in sorted(cart["posiciones"], key=lambda p: -(p.get("peso") or 0)):
            out.append(f"| {p.get('clave_operable') or p['instrumento_id']} | {(p.get('peso') or 0):.1%} | "
                       f"{_mxn(p.get('valor_mxn'))} | {p.get('etiqueta_vigencia') or p.get('vigencia') or 's/d'} | "
                       f"{p.get('fecha_precio') or 's/d'} |")
    for c in cart.get("cumplimiento_reto", []):
        out.append(f"- {'✔' if c['cumple'] else '✘'} {c['regla']}: {c['detalle']}")
    return out + [""]


def _seccion_propuestas(props: dict, detalle: bool) -> list[str]:
    out = ["## Propuestas"]
    for clave, p in props.items():
        if not p:
            out.append(f"- **{clave}**: sin calcular.")
            continue
        estado = p.get("estado")
        if estado not in ("calculada", "demostracion"):
            motivo = "; ".join(p.get("motivos") or p.get("avisos") or []) or estado
            out.append(f"- **{p.get('nombre', clave)}**: {estado.upper()} — {motivo}. No se emite recomendación.")
            continue
        m = p.get("mejora_esperada") or {}
        out.append(f"- **{p['nombre']}** (puntuación {p['puntuacion']['total']:.0f}, datos al {p.get('datos_hasta')}): "
                   f"ESTIMACIÓN: mejora esperada neta {_pct(m.get('neta'))} — incierta, no es una promesa.")
        v, rb = p.get("validacion_extendida") or {}, p.get("robustez") or {}
        if v.get("estrategia"):
            out.append(f"  - HISTÓRICO fuera de muestra ({v['estrategia']['sesiones']} sesiones): {_pct(v['estrategia']['rend_anual'])}/año "
                       f"vs 1/N {_pct(v['iguales']['rend_anual'])} — {v['veredicto'].lower()}.")
        if rb.get("estado") in ("robusta", "no aprobada", "frágil"):
            out.append(f"  - SIMULACIÓN (Monte Carlo, remuestreo del pasado): prob. de pérdida al cierre "
                       f"{rb['simulacion_prob_perdida']:.0%}; robustez {rb['estado'].upper()}"
                       + (f" ({', '.join(rb['motivos'])})" if rb.get("motivos") else "") + ".")
        for a in p.get("avisos", []):
            out.append(f"  - ⚠ {a}")
        if detalle:
            for a in (p.get("pesos") or [])[:8]:
                out.append(f"  - {a['clave_operable']} {a['peso']:.1%} ({a.get('vigencia')}): {'; '.join(a.get('motivos') or [])[:140]}")
            for f in ((p.get("cambios") or {}).get("filas") or [])[:5]:
                out.append(f"  - cambio: {f.get('accion')} {f['id']} {f.get('delta_pp', 0):+.1f} pp (≈ {_mxn(f.get('monto_mxn'))})")
    return out + [""]


def _seccion_alertas(con: sqlite3.Connection, horas: int) -> list[str]:
    desde = (datetime.now(UTC) - timedelta(hours=horas)).isoformat()
    filas = [a for a in alertas.listar(con, 500) if a["ts"] >= desde]
    out = [f"## Alertas de las últimas {horas} h ({len(filas)})"]
    if not filas:
        return out + ["Ninguna.", ""]
    for a in filas[:15]:
        out.append(f"- [{a['severidad']}] {_hora_mx(a['ts'])} — {a['titulo']}: {a['motivo']} (fuente: {a.get('fuente') or 'terminal'})")
    if len(filas) > 15:
        out.append(f"- … y {len(filas) - 15} más en la pestaña Alertas.")
    return out + [""]


def _seccion_seguimiento(seg: dict) -> list[str]:
    out = ["## Seguimiento"]
    if seg.get("twr_acumulado") is None:
        return out + ["Sin historia suficiente para medir rendimiento.", ""]
    out.append(f"- Rendimiento ponderado por tiempo: **{_pct(seg['twr_acumulado'], 2)}** · máxima caída: {_pct(seg.get('max_caida'), 2)}")
    for r in seg.get("referencias", []):
        out.append(f"- vs {r['nombre']}: " + (_pct(r["rend_acumulado"], 2) if r.get("rend_acumulado") is not None else r.get("nota", "s/d")))
    return out + [""]


def _seccion_motor(con) -> list[str]:
    m = servicios.estado_motor(con)
    if not m:
        return ["## Motor automático", "Aún no ha corrido ningún ciclo: los datos pueden no estar actualizados.", ""]
    ctx = ", ".join(f"{k}: {v}" for k, v in (m.get("contexto") or {}).items()) or "s/d"
    return ["## Motor automático", f"- Último ciclo: {_hora_mx(m['ultimo_ciclo'])} (recálculo: {m.get('recalculo')}; datos nuevos: "
            f"{m.get('nuevos_datos')}) · fuentes de contexto → {ctx}", ""]


def _seccion_movimientos(con, ajustes: Ajustes) -> list[str]:
    from .movimientos import servicio
    try:
        return servicio.texto_reporte(con, ajustes)
    except Exception:  # noqa: BLE001 - el reporte nunca se detiene por esta fuente
        return ["## Movimientos públicos (SEC EDGAR)", "No se pudo construir esta sección (ver registro de errores).", ""]


def _seccion_pronostico(con, ajustes: Ajustes, props: dict, cart: dict) -> list[str]:
    from .investigacion import reto_pronostico
    try:
        r = reto_pronostico.construir(con, ajustes, props=props, cart=cart)
    except Exception:  # noqa: BLE001 - el reporte nunca se detiene por la investigación
        return ["## Pronóstico", "No se pudo construir el pronóstico (ver registro de errores).", ""]
    return ["## Pronóstico (ESTIMACIÓN, no cotización)", "", "```", reto_pronostico.texto(r), "```", ""]


def generar(con: sqlite3.Connection, ajustes: Ajustes, tipo: str, ahora: datetime | None = None) -> str:
    """Devuelve el reporte en Markdown. No escribe nada ni envía nada."""
    if tipo not in TIPOS:
        raise ValueError(f"tipo de reporte desconocido: {tipo}")
    ahora = ahora or datetime.now(UTC)
    perfil = servicios.perfil_actual(con, ajustes)
    props = servicios.propuestas_guardadas(con, ajustes, perfil)
    cart = servicios.cartera_actual(con, ajustes)
    semanal = tipo == "semanal"
    modo = "DEMOSTRACIÓN (datos sintéticos)" if ajustes.es_demo else "datos reales"
    out = [f"# {TIPOS[tipo]} — {_hora_mx(ahora.isoformat())} (CDMX)", "",
           f"_Generado por la terminal local · modo: {modo}. Solo informa; no envía órdenes. Los rendimientos pasados "
           "no garantizan resultados futuros._", ""]
    out += _seccion_reto() + _seccion_motor(con) + _seccion_cartera(cart)
    if semanal:
        out += _seccion_seguimiento(servicios.seguimiento(con, ajustes))
    out += _seccion_propuestas(props, detalle=tipo != "cierre")
    out += _seccion_pronostico(con, ajustes, props, cart)
    out += _seccion_movimientos(con, ajustes)
    out += _seccion_alertas(con, 24 * 7 if semanal else 24)
    return "\n".join(out).rstrip() + "\n"


def guardar(texto: str, tipo: str, ahora: datetime | None = None, carpeta: Path | None = None) -> Path:
    ahora = ahora or datetime.now(UTC)
    d = Path(carpeta or data_dir() / "reportes")
    d.mkdir(parents=True, exist_ok=True)
    ruta = d / f"{ahora.astimezone():%Y-%m-%d}_{tipo}.md"
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def ejecutar(con: sqlite3.Connection, ajustes: Ajustes, tipo: str, actualizar: bool = True) -> Path:
    """Refresca datos con un ciclo del motor (si se pide) y guarda el reporte del día."""
    if actualizar:
        try:
            servicios.ciclo(con, ajustes, notificar=False)
        except Exception:  # noqa: BLE001 — un fallo de fuente no debe impedir el reporte; el reporte lo dirá
            log.exception("el ciclo previo al reporte falló; se reporta con los datos disponibles")
    ruta = guardar(generar(con, ajustes, tipo), tipo)
    log.info("reporte %s guardado en %s", tipo, ruta)
    return ruta

