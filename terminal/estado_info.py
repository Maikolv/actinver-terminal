"""«¿En qué puedo confiar hoy?»: lista para personas sin conocimientos técnicos.

Cada punto tiene un nivel y, si hace falta, la acción concreta:
  confirmado  → dato que usted copió del portal del Reto o fuente oficial vigente
  estimado    → cálculo de la terminal (precios de cierre, propuestas, valuaciones)
  vencido     → dato que existe pero ya no está al día
  falta       → no hay dato; la acción dice cómo conseguirlo
Nunca llama «tiempo real» a un cierre diario.
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter

import pandas as pd

from . import mercado, notificador, portal, reto, servicios

ZONA = "America/Mexico_City"


def _hora(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        return pd.Timestamp(iso).tz_convert(ZONA).strftime("%d-%m-%Y %H:%M")
    except (ValueError, TypeError):
        return str(iso)


def calcular(con: sqlite3.Connection, ajustes) -> dict:
    items = []

    def item(tema, nivel, texto, accion=""):
        items.append({"tema": tema, "nivel": nivel, "texto": texto, "accion": accion})

    # 1. Cuenta del Reto
    c = portal.captura(con)
    vig = servicios.captura_vigente(con)
    etapa = reto.etapa_operativa() if reto.activo() else None
    if vig:
        item("Cuenta del Reto", "confirmado",
             f"Saldo {vig['valor_portafolio']:,.2f}, efectivo {(vig['efectivo'] or 0):,.2f} y {vig['n_posiciones']} posiciones "
             f"copiadas del portal (hora del portal {_hora(vig['hora_portal'])}).",
             "Actualícela después de cada operación o al cierre del día.")
    elif c:
        item("Cuenta del Reto", "vencido",
             f"La última captura ({_hora(c['hora_portal'])}) ya no se usa: cambió la etapa del Reto o registró operaciones "
             "a mano después.", "Pegue una captura nueva en «Mi portafolio Actinver» → «Actualizar desde el portal».")
    else:
        item("Cuenta del Reto", "falta",
             "No hay datos de su cuenta del Reto. El millón que ve la terminal es un registro LOCAL (aportación capturada "
             "a mano), no un saldo confirmado del portal.",
             "Copie la tabla de su cuenta en el portal y péguela en «Mi portafolio Actinver» → «Actualizar desde el portal».")
    # 2. Precios
    ins = mercado.instrumentos(con)
    ids = [i for i, v in ins.items() if v["estado"] == "activo"]
    cot = mercado.cotizaciones(con, ajustes, ids)
    cuenta = Counter(q.get("estado") for q in cot.values())
    fondos_sin = [i for i in ids if str(ins[i]["clase"]).startswith("fondo") and cot[i].get("estado") == "sin_datos"]
    bmv_sin = [i for i in ids if ins[i]["mercado_operable"] == "BMV" and cot[i].get("estado") == "sin_datos"]
    sic_venc = [i for i in ids if ins[i]["mercado_operable"] == "BMV-SIC" and cot[i].get("estado") == "vencido"]
    nivel = "estimado" if cuenta.get("vigente") else "falta"
    item("Precios", nivel,
         f"{cuenta.get('vigente', 0)} vigentes, {cuenta.get('retrasado', 0)} retrasados (cierre de la sesión anterior), "
         f"{cuenta.get('vencido', 0)} vencidos y {cuenta.get('sin_datos', 0)} sin datos de "
         f"{len(ids)}. Son CIERRES DIARIOS, no tiempo real. Los del SIC son el precio de la bolsa de origen convertido a pesos "
         "(referencia, no la cotización del SIC).",
         "Para tiempo real hace falta un contrato de datos (Infosel) o claves de Alpaca (referencia EE. UU.).")
    if bmv_sin:
        from .ingesta import RESERVA_HISTORIA_NUEVA
        dias = -(-len(bmv_sin) // max(RESERVA_HISTORIA_NUEVA, 1))
        item("Emisoras BMV sin precio", "falta",
             f"{len(bmv_sin)} emisoras sin historia. Recuperación programada: {RESERVA_HISTORIA_NUEVA} por día con EODHD "
             f"(≈ {dias} sesiones); TERRA 13 y SMARTRC no están en EODHD. Con el plan gratuito (20 consultas/día) solo "
             "~18 emisoras BMV pueden actualizarse cada día: el resto rota y puede quedar retrasado.",
             "Para cubrir todas a diario: plan de pago de EODHD, o Twelve Data Pro (TWELVEDATA_API_KEY; cubre 37 de 44).")
    if sic_venc:
        item("Emisoras SIC atrasadas", "vencido",
             f"{len(sic_venc)} con cierre atrasado (Tiingo limita consultas por hora). Se ponen al día solas.")
    if fondos_sin:
        item("Fondos Actinver", "falta",
             f"{len(fondos_sin)} fondos sin valor por unidad ({', '.join(f.split(':')[1] for f in fondos_sin[:5])}). La hoja "
             "oficial de Actinver se importa sola cada día; un fondo cuya serie no aparece en ella no se asigna por "
             "aproximación.",
             "Confirme en el simulador qué serie opera; si es otra, importe su precio en «Datos» o avísenos para ajustar la serie.")
    # 3. Tipo de cambio
    fx = mercado.ultimo_fx(con, ajustes)
    item("Tipo de cambio", "confirmado" if fx.get("estado") == "vigente" else "vencido",
         f"USD/MXN {fx.get('valor') or '—'} del {fx.get('fecha') or '—'} ({fx.get('proveedor') or 'sin fuente'}).")
    # 4. Propuesta de referencia
    from . import resumen
    perfil = servicios.perfil_actual(con, ajustes)
    props = servicios.propuestas_guardadas(con, ajustes, perfil)
    ref = resumen.propuesta_referencia(props)
    bloqueadas = [p for p in props.values() if p and p.get("avisos")]
    if ref:
        ses = ((ref.get("comparacion") or [{}])[0]).get("sesiones")
        item("Propuesta", "estimado",
             f"«{ref['nombre']}» {ref['puntuacion']['total']:.1f}/100, datos al {ref.get('datos_hasta')}; validada con "
             f"{ses or '—'} sesiones fuera de muestra" + (" (pocas: puntuación poco confiable)" if ses and ses < 126 else "")
             + ". Es una estimación, no una promesa.",
             "Revise «Propuestas» y genere boletas; usted captura cada orden a mano.")
    else:
        item("Propuesta", "falta", "No hay una propuesta vigente para recomendar hoy.",
             "; ".join(sorted({a for p in bloqueadas for a in p["avisos"]}))[:300] or "Espere al siguiente cálculo.")
    # 5. Alertas
    canales = notificador.configurados()
    activos = [k for k, v in canales.items() if v]
    f = con.execute("SELECT valor FROM ajustes_usuario WHERE clave='resumen_matutino'").fetchone()
    ultimo = json.loads(f["valor"]) if f else None
    item("Alertas", "confirmado" if canales.get("telegram") else "falta",
         f"Canales activos: {', '.join(activos) or 'ninguno'}. Plan del día por Telegram a las "
         f"{ajustes['alertas'].get('resumen_matutino_hora', '07:00')} (último envío: "
         f"{_hora(ultimo.get('enviado_en')) if ultimo else 'aún no'}).",
         "" if canales.get("correo") else "Correo: agregue SMTP_HOST, SMTP_USER, SMTP_PASS y ALERTAS_CORREO_DESTINO en .env.")
    # 6. Seeking Alpha
    n_not = con.execute("SELECT COUNT(*), MAX(obtenido_en) FROM noticias WHERE fuente='seekingalpha_rss'").fetchone()
    n_cal = con.execute("SELECT COUNT(DISTINCT instrumento_id), MAX(importado_en) FROM calificaciones").fetchone()
    item("Seeking Alpha", "estimado" if n_not[0] else "falta",
         f"{n_not[0]} titulares del RSS público (último {_hora(n_not[1])}); {n_cal[0]} emisoras con calificaciones "
         f"importadas (último {_hora(n_cal[1])}). Titulares y calificaciones son contexto, no señales.",
         "" if n_cal[0] else "Opcional: exporte calificaciones de su cuenta y súbalas en «Datos» (Calificaciones de Seeking Alpha).")
    return {"items": items, "etapa_reto": etapa,
            "leyenda": {"confirmado": "Copiado del portal del Reto o de una fuente oficial vigente",
                        "estimado": "Cálculo de la terminal con cierres diarios; puede diferir del portal",
                        "vencido": "Existe pero no está al día", "falta": "No hay dato: siga la acción indicada"}}
