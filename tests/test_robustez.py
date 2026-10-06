"""Protocolo de robustez: reproducibilidad, sin filtración futura, Monte Carlo en cada combinación, picos aislados y
separación de ventanas del walk-forward."""
import numpy as np
import pandas as pd

from terminal.robustez import calculo, diseno as dz, estabilidad as es, informe, montecarlo as mc, walkforward as wf


def _R(n=760, k=14, semilla=1):
    rng = np.random.default_rng(semilla)
    idx = pd.bdate_range("2023-01-02", periods=n)
    R = pd.DataFrame(rng.normal(0.0004, 0.012, (n, k)), index=idx, columns=[f"SIC:A{i}" for i in range(k)])
    R.iloc[:300, -2:] = np.nan  # dos activos llegan tarde (panel dinámico)
    return R


def _ajustar_combo(combo):
    def ajustar(cols, X):  # modelo determinista sencillo que depende de los parámetros (sin optimizador)
        m = X.mean().clip(lower=0) + 1e-9
        w = (m ** (1 / combo["aversion"])) / (m ** (1 / combo["aversion"])).sum()
        w = w.clip(upper=combo["tope"])
        return w / w.sum()
    return ajustar


def test_montecarlo_reproducible_y_con_el_mismo_numero_de_simulaciones():
    rng = np.random.default_rng(0)
    b, c, g, s = rng.normal(0.0005, 0.01, 400), np.zeros(400), np.zeros(400), np.zeros(400)
    c[::21], g[::21], s[::21] = 0.001, 0.5, 0.2
    a1, a2 = mc.simular(b, c, g, s, 29, 7), mc.simular(b, c, g, s, 29, 7)
    assert a1 == a2 and a1["m"] == dz.M_SIM                                   # misma semilla ⇒ mismo resultado
    assert mc.simular(b, c, g, s, 29, 8)["ret_p50"] != a1["ret_p50"]
    assert a1["ret_p5"] <= a1["ret_p50"] <= a1["ret_p95"] and a1["cvar5"] <= a1["ret_p5"]


def test_sin_filtracion_futura_en_los_pliegues(ajustes):
    R = _R()
    combo = {"aversion": 1.0, "tope": 0.2, "historia": 126}
    for s, cols, Xtr, Xte in calculo.pliegues(R, 126):
        assert Xtr.index[-1] < Xte.index[0] and len(Xtr) == 126               # el entrenamiento termina antes de la prueba
    costos = pd.Series(0.00116, index=R.columns)
    base = calculo.evaluar(combo, "acciones", {}, ajustes, {}, R, costos, set(R.columns), ajustar=_ajustar_combo(combo))
    R2 = R.copy()
    R2.iloc[650:] *= 5                                                         # el futuro cambia por completo…
    alt = calculo.evaluar(combo, "acciones", {}, ajustes, {}, R2, costos, set(R.columns), ajustar=_ajustar_combo(combo))
    antes = [p for s, p in base["pesos"] if s <= 650]
    assert antes == [p for s, p in alt["pesos"] if s <= 650]                  # …y los pesos previos no se enteran
    assert np.allclose(base["bruto"]["estrategia"][:650], alt["bruto"]["estrategia"][:650])


def test_picos_aislados_y_meseta():
    shape = es.forma()
    met = {}
    for i in range(shape[0]):
        for j in range(shape[1]):
            for k in range(shape[2]):
                met[(i, j, k)] = {"R": 0.12 + 0.002 * (i + j + k), "D": -0.1, "V": 0.2, "exceso_1N": 0.03, "w": {"A": 1.0}}
    met[(5, 0, 0)] = {**met[(5, 0, 0)], "R": 0.60}                           # máximo aislado en una esquina
    ana = es.analizar(met)
    assert ana[(5, 0, 0)]["pico_aislado"] and not ana[(5, 0, 0)]["aprobada"]
    ele = es.elegir(met, ana)
    assert ele["veredicto"] == "MESETA" and ele["elegida"] != (5, 0, 0)       # gana la meseta, no el pico
    assert ele["regiones"][0]["tamano"] >= dz.UMBRALES["meseta_min"] and ele["distancia_borde"] >= 1


def test_ventanas_del_walk_forward_separadas_y_tramo_intacto_sin_usar():
    pos = np.arange(800)
    fs = wf.fronteras(pos)
    assert fs and all(f["seleccion"].max() < f["aplicacion"].min() for f in fs)
    rng = np.random.default_rng(3)
    combos = dz.combinaciones()
    n = 1000
    netos = {tuple(c["pos"]): rng.normal(0.0004, 0.01, n) for c in combos}
    netos_1n = {p: rng.normal(0.0003, 0.01, n) for p in netos}
    pesos = {p: [] for p in netos}
    r = wf.anidado(netos, netos_1n, pesos, np.ones(n, dtype=bool), n, (1, 4, 1))
    corte = n - dz.INTACTO
    assert all(t["aplicacion"][1] < corte and t["seleccion"][1] < t["aplicacion"][0] for t in r["tramos"])
    assert r["intacto"]["sesiones"] == dz.INTACTO
    corto = wf.anidado({p: v[:300] for p, v in netos.items()}, {p: v[:300] for p, v in netos_1n.items()}, pesos,
                       np.ones(300, dtype=bool), 300, (1, 4, 1))
    assert corto["evidencia"] == "EVIDENCIA INSUFICIENTE"


def test_monte_carlo_en_cada_combinacion_y_corrida_reproducible(ajustes, tmp_path, monkeypatch):
    R = _R()
    real = calculo.evaluar
    monkeypatch.setattr(informe.calculo, "evaluar", lambda c, t, p, a, el, R_, co, u: real(c, t, p, a, el, R_, co, u,
                                                                                           ajustar=_ajustar_combo(c)))
    pre = dz.preregistro("acciones", [{"id": c} for c in R.columns], R, {}, {"sesiones": 29}, [], {}, {}, {})
    pre["excluidos"] = 0
    monkeypatch.setattr(informe, "preparar", lambda con, a, tipo: {
        "perfil": {}, "el": {}, "R": R, "costos": pd.Series(0.00116, index=R.columns), "sic": set(R.columns), "pre": pre})
    llamadas = []
    original = informe.mc.simular
    monkeypatch.setattr(informe.mc, "simular", lambda *a, **k: llamadas.append(1) or original(*a, **k))
    r1 = informe.ejecutar(None, ajustes, "acciones", base=tmp_path)
    assert r1["estado"] == "ok" and r1["combinaciones"] == len(dz.combinaciones()) == len(llamadas)
    assert r1["simulaciones_por_combinacion"] == [dz.M_SIM] and all(c["montecarlo"]["m"] == dz.M_SIM for c in r1["combos"])
    r2 = informe.ejecutar(None, ajustes, "acciones", base=tmp_path)            # reanuda: no recalcula nada
    assert r2["lote"]["calculadas"] == 0 and r2["lote"]["reutilizadas"] == len(dz.combinaciones())
    clave = ("spp", "elegida", "walk_forward", "pct_aprobadas")
    assert {k: r1[k] for k in clave} == {k: r2[k] for k in clave}             # mismos datos + semillas ⇒ mismo resultado


def test_una_propuesta_fragil_no_es_la_referencia_si_hay_alternativa(monkeypatch):
    from terminal import resumen
    def p(clave, central, estado):
        return {"clave": clave, "nombre": clave, "estado": "calculada", "puntuacion": {"total": 90},
                "perfil": {"criterio_plan": "plusvalia"}, "escenarios": {"central_p50": central}, "robustez": {"estado": estado}}
    props = {"acciones_rendimiento": p("acciones_rendimiento", 0.30, "frágil"),   # backtest sobresaliente pero frágil
             "acciones_puntuacion": p("acciones_puntuacion", 0.05, "robusta")}
    assert resumen.propuesta_referencia(props)["clave"] == "acciones_puntuacion"
    props["acciones_puntuacion"]["robustez"]["estado"] = "frágil"               # si todas son frágiles, no se queda sin plan
    assert resumen.propuesta_referencia(props)["clave"] == "acciones_rendimiento"


def test_estado_de_una_propuesta_por_su_combinacion_mas_cercana(monkeypatch):
    fichas = [{"params": {"aversion": 0.5, "tope": 0.2, "historia": 252}, "aprobada": False, "motivos_rechazo": ["estabilidad"],
               "criterios": {"estabilidad": False}, "pico_aislado": True, "S": 0.4, "oos": {"R": 0.9},
               "montecarlo": {"prob_perdida": 0.42, "ret_p5": -0.2, "caida_p5": -0.3}},
              {"params": {"aversion": 4.0, "tope": 0.12, "historia": 252}, "aprobada": False, "motivos_rechazo": ["caida_p5"],
               "criterios": {"estabilidad": True, "caida_p5": False}, "pico_aislado": False, "S": 0.7, "oos": {"R": 0.3},
               "montecarlo": {"prob_perdida": 0.3, "ret_p5": -0.1, "caida_p5": -0.22}}]
    monkeypatch.setattr(informe, "_resumen_vigente", lambda tipo: {"estado": "ok", "combos": fichas, "huella": "x", "creado_en": "hoy"})
    prop = {"tipo": "acciones", "lente": "rendimiento", "reproducibilidad": {"aversion_riesgo_lambda": 0.5,
                                                                           "ventana_estimacion": {"sesiones": 255}}}
    e = informe.estado_propuesta(prop)
    assert e["estado"] == "frágil" and e["combinacion"] == {"aversion": 0.5, "tope": 0.2, "historia": 252}
    assert informe.estado_propuesta({**prop, "mercado_variante": "nacionales"})["estado"] == "sin evaluar"
    ajuste = {"tipo": "acciones", "lente": "ajuste", "perfil_efectivo": {"max_peso_activo": 0.12},
              "reproducibilidad": {"aversion_riesgo_lambda": 4.0, "ventana_estimacion": {"sesiones": 255}}}
    e2 = informe.estado_propuesta(ajuste)        # estable pero con cola de riesgo: «no aprobada», no «frágil»
    assert e2["estado"] == "no aprobada" and informe.motivos_sencillos(e2["motivos"])[0].startswith("en la simulación")
