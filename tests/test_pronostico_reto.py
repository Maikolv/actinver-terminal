"""Pronóstico al cierre del Reto: pesos sin fuga de tipo de cambio, horizonte y calendarios, cotizaciones vencidas,
cartera no conciliada y barrera que bloquea la señal si el modelo no supera a las referencias."""
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from terminal import migraciones
from terminal.investigacion import datos, pronosticos, reto_pronostico as rp

from conftest import sembrar_precios

IDS = ["SIC:AAPL", "SIC:MSFT", "SIC:KO", "BMV:AMX", "BMV:GFNORTE", "BMV:FUNO"]


def _preparar(con, sesiones=500):
    fechas = sembrar_precios(con, IDS, sesiones=sesiones)
    migraciones.completar_tiempos(con)
    return fechas


# ---------------------------------------------------------------- pesos y tipo de cambio
def test_sic_en_pesos_usa_el_tipo_de_cambio_de_su_fecha(con):
    fechas = _preparar(con, 120)
    p = datos.precios_hasta(con, False, None, ["SIC:AAPL"], mxn=True)
    usd = datos.precios_hasta(con, False, None, ["SIC:AAPL"])
    f = fechas[-10].date().isoformat()
    fx = con.execute("SELECT valor FROM fx WHERE fecha=? ORDER BY available_at LIMIT 1", (f,)).fetchone()[0]
    a = p.loc[p["fecha"] == f, "cierre"].iloc[0]
    b = usd.loc[usd["fecha"] == f, "cierre"].iloc[0]
    assert abs(a - b * fx) < 1e-9 and set(p["moneda"]) == {"MXN"}


def test_tipo_de_cambio_publicado_despues_de_T_no_se_usa(con):
    fechas = _preparar(con, 120)
    T = pd.Timestamp(fechas[100]).tz_localize("UTC") + pd.Timedelta(hours=23, minutes=30)
    antes = datos.precios_hasta(con, False, T, ["SIC:AAPL"], mxn=True)
    # Un tipo de cambio absurdo para fechas ya conocidas pero publicado DESPUÉS de T no debe cambiar nada en T
    tarde = (T + pd.Timedelta(days=1)).isoformat()
    con.execute("INSERT OR REPLACE INTO fx (par, fecha, valor, proveedor, tipo_dato, obtenido_en, available_at) "
                "VALUES ('USDMXN', ?, 999.0, 'banxico', 'fx', ?, ?)", (fechas[100].date().isoformat(), tarde, tarde))
    con.execute("UPDATE fx SET valor = valor * 5 WHERE fecha > ?", (fechas[100].date().isoformat(),))
    despues = datos.precios_hasta(con, False, T, ["SIC:AAPL"], mxn=True)
    pd.testing.assert_frame_equal(antes, despues)
    assert (despues["available_at"] <= T).all()


def test_sin_tipo_de_cambio_no_se_inventa_la_conversion(con):
    sembrar_precios(con, ["SIC:AAPL", "BMV:AMX"], sesiones=80, con_fx=False)
    migraciones.completar_tiempos(con)
    p = datos.precios_hasta(con, False, None, mxn=True)
    assert set(p["instrumento_id"]) == {"BMV:AMX"}  # el SIC se descarta, no se convierte con un valor supuesto


def test_historia_insuficiente_se_informa():
    precios = pd.DataFrame({"instrumento_id": ["BMV:X"] * 20, "fecha": [f"2026-01-{i:02d}" for i in range(1, 21)],
                            "cierre": np.ones(20)})
    falta = datos.historia_insuficiente(precios, 5)
    assert falta == [{"instrumento_id": "BMV:X", "sesiones": 20, "minimo": datos.L_MAX + 10}]


# ---------------------------------------------------------------- horizonte y calendarios
def test_horizonte_hasta_el_cierre_del_reto_cuenta_sesiones_bmv():
    assert rp.horizonte_reto(desde=date(2026, 11, 10))["H"] == 3          # 11, 12 y 13 de noviembre
    assert rp.horizonte_reto(desde=date(2026, 11, 7))["H"] == 5           # sábado: 9 al 13
    cerrado = rp.horizonte_reto(desde=date(2026, 11, 13))
    assert cerrado["H"] == 0 and "cerró" in cerrado["motivo"]
    h = rp.horizonte_reto(desde=date(2026, 10, 30))                       # 2-nov es feriado en la BMV
    assert h["H"] == 9 and h["hasta"] == "2026-11-13"


def test_fecha_objetivo_usa_el_calendario_de_cada_mercado():
    assert pronosticos.fecha_objetivo("BMV:AMX", "2026-11-12", 1) == "2026-11-13"
    assert pronosticos.fecha_objetivo("BMV:AMX", "2026-10-30", 1) == "2026-11-03"   # feriado BMV 2-nov
    assert pronosticos.fecha_objetivo("SIC:AAPL", "2026-11-25", 1) == "2026-11-27"  # Acción de Gracias en NYSE
    assert pronosticos.fecha_objetivo("SIC:AAPL", "2026-10-30", 1) == "2026-11-02"  # NYSE sí abre el 2-nov


# ---------------------------------------------------------------- barrera
def _exp(neto_modelo=0.05, mse_modelo=0.9, p=0.01, actual=True, vista=False, rebalanceos=10):
    refs = [{"modelo": n, "mse": 1.0, "resultado_neto": 0.01} for n in ("sin_cambio", "historico_reciente", "regla_simple")]
    estr = [{"modelo": "pesos_iguales (todas)", "resultado_neto": 0.02}]
    if actual:
        estr.append({"modelo": "estrategia_actual (media)", "resultado_neto": 0.03})
    return {"estado": "ok", "prueba": [{"modelo": "modelo (ridge)", "mse": mse_modelo, "resultado_neto": neto_modelo,
                                       "rebalanceos": rebalanceos}] + refs,
            "estrategias_referencia": estr, "prueba_ya_vista": vista, "dias_prueba": 100,
            "diebold_mariano_vs_referencias": {r["modelo"]: {"p_valor": p} for r in refs}}


def test_barrera_abre_solo_si_supera_todo_despues_de_costos():
    assert rp.barrera(_exp())["permitida"] is True
    for exp in (_exp(neto_modelo=0.025),        # no supera a la estrategia actual después de costos
                _exp(p=0.2),                     # error menor sin significancia
                _exp(mse_modelo=1.1),            # error mayor que «sin cambio»
                _exp(actual=False),              # estrategia actual no evaluada ⇒ no se puede afirmar ventaja
                _exp(vista=True),                # prueba final ya usada
                _exp(rebalanceos=2),             # prueba demasiado corta para el horizonte
                None):
        b = rp.barrera(exp)
        assert b["permitida"] is False and b["leyenda"] == rp.LEYENDA_SIN_VENTAJA
    # Deterioro en pronósticos ya resueltos también bloquea
    assert rp.barrera(_exp(), {"razon": 1.3, "n": 40, "cobertura_80": 0.6})["permitida"] is False


def test_los_modulos_de_decision_no_leen_el_pronostico():
    """Barrera verificable: plan, boletas, optimizador y propuestas no importan la tabla de pronósticos."""
    raiz = Path(__file__).resolve().parents[1] / "terminal"
    for m in ("plan_accion.py", "boleta.py", "optimizador.py", "resumen.py", "ranking.py"):
        txt = (raiz / m).read_text(encoding="utf-8")
        assert "pronosticos" not in txt and "reto_pronostico" not in txt, m


# ---------------------------------------------------------------- emisión, vencidos y cartera
def test_emision_al_cierre_del_reto_en_pesos_y_bloqueada_sin_ventaja(con, ajustes):
    _preparar(con, 500)
    out = pronosticos.emitir(con, False, 10, etiqueta="reto", objetivo="2026-11-13")
    assert out["emitidos"] == len(IDS) and out["recomendacion_permitida"] is False  # datos aleatorios: sin ventaja
    filas = pronosticos.emision(con, "reto")
    assert {f["moneda"] for f in filas} == {"MXN"} and {f["fecha_objetivo"] for f in filas} == {"2026-11-13"}
    assert all(f["recomendacion_permitida"] == 0 for f in filas)
    aapl = next(f for f in filas if f["instrumento_id"] == "SIC:AAPL")
    usd = con.execute("SELECT cierre FROM precios WHERE instrumento_id='SIC:AAPL' AND fecha=?", (aapl["fecha_base"],)).fetchone()[0]
    assert aapl["precio_base"] > usd * 10                                      # precio base en pesos, no en dólares
    assert all(f["p10"] <= f["prediccion"] <= f["p90"] and 0 <= f["prob_subida"] <= 1 for f in filas)
    assert all(f["datos_hasta"] <= f["emitido_en"] for f in filas)
    local = {"fuente": "local", "valor_total": 1_000_000.0, "posiciones": [
        {"instrumento_id": "SIC:AAPL", "valor_mxn": 300_000.0}, {"instrumento_id": "BMV:AMX", "valor_mxn": 200_000.0}]}
    r = rp.construir(con, ajustes, props={}, cart=local)
    assert r["etiqueta"] == "reto" and r["emision"]["moneda"] == "MXN"
    assert r["barrera"]["permitida"] is False and "sin ventaja demostrada" in r["uso_en_decisiones"]
    c = r["cartera"]
    assert c["conciliada"] is False and "NO conciliada" in c["aviso"]
    assert c["p10"] <= c["central"] <= c["p90"] and c["efectivo_y_por_liquidar"] == 500_000.0
    txt = rp.texto(r)
    assert rp.LEYENDA_SIN_VENTAJA in txt and "NO conciliada" in txt and "ESTIMACIÓN" in txt
    # Segunda emisión: se informan cambios frente a la anterior
    pronosticos.emitir(con, False, 10, T=pd.Timestamp.now(tz="UTC") + pd.Timedelta(seconds=1), etiqueta="reto",
                       objetivo="2026-11-13")
    assert rp.construir(con, ajustes, props={}, cart=local)["cambios"]["hay_anterior"] is True


def test_cotizacion_vencida_no_entra_al_pronostico_de_la_cartera(con):
    base = {"instrumento_id": "BMV:AMX", "prediccion": 0.05, "p10": -0.1, "p90": 0.2, "prob_subida": 0.6, "precio_base": 10.0,
            "moneda": "MXN", "fecha_objetivo": "2026-11-13", "horizonte": 20, "emitido_en": "2026-10-01T00:00:00+00:00",
            "datos_hasta": "2026-10-01T00:00:00+00:00", "version": "v", "modelo": "ridge"}
    ahora = pd.Timestamp("2026-10-01T22:00:00Z").to_pydatetime()
    fresca = rp.por_emisora(con, [{**base, "fecha_base": "2026-09-30"}], ahora)[0]
    vieja = rp.por_emisora(con, [{**base, "fecha_base": "2026-09-15"}], ahora)[0]
    assert fresca["vencido"] is False and abs(fresca["precio_central"] - 10 * np.exp(0.05)) < 1e-4
    assert vieja["vencido"] is True and "VENCIDO" in vieja["estado"]
    cart = {"fuente": "portal", "captura": {"hora_portal": "2026-10-01T09:00"}, "valor_total": 150.0,
            "posiciones": [{"instrumento_id": "BMV:AMX", "valor_mxn": 100.0}]}
    c = rp.cartera(cart, [vieja], capital=150.0)
    assert c["conciliada"] is True and c["aviso"] is None
    assert c["central"] == c["p10"] == c["p90"] == 150.0                     # sin pronóstico utilizable: valor actual
    assert c["sin_pronostico"][0]["instrumento_id"] == "BMV:AMX"


def test_comparacion_de_propuestas_descuenta_costos_y_explica_diferencias():
    emis = [{"instrumento_id": "SIC:A", "vencido": False, "rend_central": 0.10, "rend_p10": -0.1, "rend_p90": 0.3},
            {"instrumento_id": "BMV:B", "vencido": False, "rend_central": 0.01, "rend_p10": -0.02, "rend_p90": 0.04}]
    def prop(nombre, w, punt, costo):
        return {"nombre": nombre, "estado": "calculada", "puntuacion": {"total": punt}, "cambios": {"costo_pct": costo},
                "pesos": [{"id": i, "peso": v} for i, v in w.items()], "cumplimiento_reto": [{"cumple": True}]}
    props = {"x": prop("Alta puntuación", {"BMV:B": 1.0}, 90, 0.004), "y": prop("Alto rendimiento", {"SIC:A": 1.0}, 60, 0.004)}
    r = rp.comparar_propuestas(props, emis, {"valor_total": 0, "posiciones": []})
    fila = next(f for f in r["filas"] if f["nombre"] == "Alto rendimiento")
    assert abs(fila["rend_estimado_neto"] - (0.10 - 0.004)) < 1e-12 and fila["peso_sic"] == 1.0
    assert r["max_puntuacion"] == "Alta puntuación" and r["max_rendimiento"] == "Alto rendimiento"
    assert "Difieren" in r["explicacion"] and "no se usa para cambiar" in r["explicacion"]
    assert "no una cotización ejecutable del SIC" in r["nota"]
