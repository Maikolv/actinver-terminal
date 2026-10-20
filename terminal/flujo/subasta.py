"""Auction Market Theory descriptiva, sin órdenes ni inferencia de volumen por precio.

TPO = una marca por precio OHLC observado y bloque de 30 min. Es una cota inferior,
no un perfil completo de ticks. Rejilla fija, anclada en cero; no cambia con el rango.
"""
from collections import defaultdict
from datetime import UTC, datetime, time, timedelta
from math import floor, isfinite
from zoneinfo import ZoneInfo

VERSION = "amt-1.0"
INTERVALOS = {"1Min": 60, "5Min": 300, "15Min": 900}


def area_tpo(marcas, paso):
    """Expansión contigua de una fila por lado; empate incluye ambos; POC menor en empate."""
    if not marcas:
        return None
    lo, hi = min(marcas), max(marcas)
    if hi - lo > 20000:
        raise ValueError("Más de 20000 niveles: aumente el paso de precio")
    pesos = {k: len(v) for k, v in marcas.items()}
    poc = min(pesos, key=lambda k: (-pesos[k], k))
    a = b = poc
    total = sum(pesos.values())
    incluido = pesos[poc]
    while incluido < .7 * total:
        abajo = pesos.get(a-1, 0) if a > lo else -1
        arriba = pesos.get(b+1, 0) if b < hi else -1
        if abajo >= arriba and a > lo:
            a -= 1
            incluido += pesos.get(a, 0)
        if arriba >= abajo and b < hi:
            b += 1
            incluido += pesos.get(b, 0)
    return {"poc": (poc+.5)*paso, "val": a*paso, "vah": (b+1)*paso,
            "fraccion": incluido/total, "tpo": total, "niveles_observados": len(marcas)}


def contexto(cierres, maximo, minimo, referencia, aceptacion=2):
    """Hipótesis por cierre frente al valor PREVIO, nunca al perfil final de hoy."""
    if not referencia or not cierres:
        return "sin_referencia"
    val, vah = referencia["val"], referencia["vah"]
    if len(cierres) >= aceptacion and all(c > vah for c in cierres[-aceptacion:]):
        return "aceptacion_alcista"
    if len(cierres) >= aceptacion and all(c < val for c in cierres[-aceptacion:]):
        return "aceptacion_bajista"
    if val <= cierres[-1] <= vah:
        if maximo > vah and minimo < val:
            return "rechazo_ambos_extremos"
        if maximo > vah:
            return "rechazo_superior"
        if minimo < val:
            return "rechazo_inferior"
        return "rotacion_en_valor"
    return "exploracion_fuera_de_valor"


def analizar(barras, *, paso=.25, zona="America/New_York", apertura="09:30", cierre="16:00", ahora=None):
    if not isfinite(paso) or paso <= 0:
        raise ValueError("Paso de precio positivo y finito requerido")
    ahora = ahora or datetime.now(UTC)
    if ahora.tzinfo is None:
        raise ValueError("ahora debe incluir zona horaria")
    tz = ZoneInfo(zona)
    abre = time.fromisoformat(apertura)
    cierra = time(0) if cierre == "24:00" else time.fromisoformat(cierre)
    if cierre != "24:00" and abre >= cierra:
        raise ValueError("Sesión inválida; nocturna requiere un adaptador explícito")
    grupos = defaultdict(dict)
    omitidas = 0
    for b in barras:
        try:
            segundos = INTERVALOS[b["intervalo"]]
            t = datetime.fromisoformat(b["inicio"].replace("Z", "+00:00"))
            if t.tzinfo is None:
                raise ValueError()
            t = t.astimezone(tz)
            fin_barra = t + timedelta(seconds=segundos)
            disponible = datetime.fromisoformat(b.get("disponible_desde", fin_barra.isoformat()).replace("Z", "+00:00"))
            if disponible.tzinfo is None or disponible > ahora or fin_barra > ahora:
                raise ValueError()
            inicio = datetime.combine(t.date(), abre, tz)
            fin = datetime.combine(t.date()+timedelta(days=cierre == "24:00"), cierra, tz)
            offset = (t-inicio).total_seconds()
            precios = [float(b[k]) for k in ("apertura", "maximo", "minimo", "cierre")]
            o, h, l, c = precios
            if not all(isfinite(x) and x > 0 for x in precios) or not l <= min(o,c) <= max(o,c) <= h:
                raise ValueError()
            if offset < 0 or fin_barra > fin or offset % segundos:
                raise ValueError()
            # Intervalos duplicados no suman TPO ni cobertura; mezclados se rechazan abajo.
            grupos[t.date().isoformat()][t] = (b, segundos, precios, inicio, fin)
        except (KeyError, TypeError, ValueError, OverflowError):
            omitidas += 1
    sesiones = []
    referencia = None
    for fecha, filas in sorted(grupos.items()):
        orden = sorted(filas.items())
        pasos = {r[1][1] for r in orden}
        if len(pasos) != 1:
            omitidas += len(orden)
            continue
        seg = next(iter(pasos))
        inicio, fin = orden[0][1][3:5]
        marcas = defaultdict(set)
        for t, (_, _, precios, _, _) in orden:
            periodo = int((t-inicio).total_seconds() // 1800)
            for precio in precios:
                marcas[floor(precio/paso + 1e-9)].add(periodo)
        perfil = area_tpo(marcas, paso)
        esperadas = int((fin-inicio).total_seconds()/seg)
        completa = len(orden) == esperadas and fin <= ahora
        cobertura = len(orden)/esperadas
        ib_filas = [(t,r) for t,r in orden if t < inicio+timedelta(hours=1)]
        ib_completo = ahora >= inicio+timedelta(hours=1) and len(ib_filas) == 3600//seg
        ib = {"alto": max(r[2][1] for _,r in ib_filas), "bajo": min(r[2][2] for _,r in ib_filas)} if ib_completo else None
        cierres = []
        anterior_t = None
        for t, r in orden:
            if anterior_t is not None and (t-anterior_t).total_seconds() != seg:
                cierres = []
            cierres.append(r[2][3])
            anterior_t = t
        ultima = orden[-1][1][2]
        estado = contexto(cierres, ultima[1], ultima[2], referencia)
        sesiones.append({"fecha":fecha,"barras":len(orden),"cobertura":cobertura,"completa_observada":completa,
                         "perfil_tpo_observado":perfil,"referencia":referencia,"ib":ib,
                         "ib_estado":"completo_observado" if ib else "pendiente_o_incompleto",
                         "estado":estado,"ultimo_cierre":cierres[-1],
                         "conocido_hasta":(orden[-1][0]+timedelta(seconds=seg)).isoformat(),
                         "operable":False})
        # Una sesión parcial nunca se convierte en referencia. Tampoco arrastrar una vieja sobre un día incompleto.
        referencia = {**perfil,"fecha":fecha} if completa else None
    return {"version":VERSION,"paso_precio":paso,"zona":zona,"sesion":f"{apertura}–{cierre}",
            "sesiones":sesiones,"barras_omitidas":omitidas,"operable":False,
            "nota":"Contexto AMT educativo. TPO observado de OHLC: cota inferior, no volumen por precio. "
                   "IB requiere todas las barras de la primera hora; referencia sólo de sesión previa completa observada. "
                   "Sin calendario de festivos verificado ni comprobación de feed en tiempo real: no genera órdenes ni demuestra alfa."}
