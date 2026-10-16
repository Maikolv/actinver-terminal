"""Indicadores (EMA, MACD, estocástico, SAR), GEX, laboratorio de permutaciones y plan intradía informativo."""
import math
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from fastapi.testclient import TestClient

from terminal import laboratorio, plan_intradia
from terminal.flujo import almacen, calculos, gex, importar_csv, servicio
from terminal.flujo.contratos import Barra, ContratoOpcion, Procedencia
from terminal.seguridad import TOKEN_CSRF

AHORA = datetime.now(UTC)
CSRF = {"X-CSRF-Token": TOKEN_CSRF}


def _nulos(x):
    return sum(v is None for v in x)


# --- Indicadores ---------------------------------------------------------------------------------------------------
def test_ema_semilla_sma_y_calentamiento():
    v = [float(i) for i in range(1, 31)]
    e = calculos.ema(v, 20)
    assert _nulos(e) == 19 and e[19] == pytest.approx(10.5)
    assert e[20] == pytest.approx(21 * 2 / 21 + 10.5 * 19 / 21)          # alfa = 2/(n+1)
    assert calculos.ema([1.0] * 5, 20) == [None] * 5                    # serie corta: nada de relleno


def test_macd_calentamiento_y_tendencias():
    sube = [100 + i for i in range(80)]
    m = calculos.macd(sube)
    assert _nulos(m["macd"]) == 25 and _nulos(m["senal"]) == 33 and _nulos(m["hist"]) == 33
    assert all(x > 0 for x in m["macd"][25:])                           # tendencia alcista sostenida
    cae = calculos.macd([200 - i for i in range(80)])
    assert all(x < 0 for x in cae["macd"][25:])
    assert m["hist"][40] == pytest.approx(m["macd"][40] - m["senal"][40])
    plano = calculos.macd([50.0] * 60)
    assert plano["macd"][30] == pytest.approx(0) and plano["hist"][59] == pytest.approx(0)
    assert calculos.macd([1.0] * 20) == {"macd": [None] * 20, "senal": [None] * 20, "hist": [None] * 20}


def test_estocastico_rangos_series_planas_y_cortas():
    c = [100 + i for i in range(40)]
    h, lo = [x + 0.5 for x in c], [x - 0.5 for x in c]
    e = calculos.estocastico(h, lo, c)
    assert _nulos(e["k"]) == 15 and _nulos(e["d"]) == 17                # 14 + 2 y 14 + 2 + 2 barras de calentamiento
    assert e["k"][20] == pytest.approx(13.5 / 14 * 100)                 # cierre cerca del máximo del rango
    assert all(0 <= x <= 100 for x in e["k"][15:] + e["d"][17:])
    bajista = calculos.estocastico([x + 0.5 for x in c[::-1]], [x - 0.5 for x in c[::-1]], c[::-1])
    assert bajista["k"][20] == pytest.approx(0.5 / 14 * 100)
    plano = calculos.estocastico([10.0] * 30, [10.0] * 30, [10.0] * 30)
    assert plano == {"k": [None] * 30, "d": [None] * 30}                # rango 0: indefinido, no 0 ni 50
    assert calculos.estocastico([1, 2], [0, 1], [1, 2])["k"] == [None, None]


def test_sar_valores_conocidos_giro_y_series_cortas():
    s = calculos.sar_parabolico([10, 11, 12], [9, 10, 11], [9.5, 10.5, 11.5])
    assert s["sar"] == [None, pytest.approx(9.0), pytest.approx(9.0)] and s["alcista"] == [None, True, True]
    # alza prolongada y luego caída fuerte: el SAR cambia de dirección y pasa por encima del precio
    c = [10 + i * 0.5 for i in range(12)] + [16, 12, 9, 7, 6]
    h, lo = [x + 0.3 for x in c], [x - 0.3 for x in c]
    s = calculos.sar_parabolico(h, lo, c)
    assert s["alcista"][5] is True and s["alcista"][-1] is False
    giro = s["alcista"].index(False)
    assert s["sar"][giro] == pytest.approx(max(h[:giro]))               # al girar toma el máximo extremo (EP) previo
    assert s["sar"][giro] > h[giro]
    assert all(v is not None for v in s["sar"][1:])
    plano = calculos.sar_parabolico([5.0] * 10, [5.0] * 10, [5.0] * 10)
    assert plano["sar"][0] is None and set(plano["sar"][1:]) == {5.0}
    assert calculos.sar_parabolico([1], [1], [1]) == {"sar": [None], "alcista": [None]}
    assert all(0 < x for x in calculos.sar_parabolico(h, lo, c)["sar"][1:])


def test_api_velas_incluye_indicadores_con_nulos_en_calentamiento(con, ajustes):
    base = AHORA.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=70)
    barras = []
    for i in range(60):
        c = 100 + i * 0.4 + (i % 5) * 0.2
        barras.append(Barra("SIC:MU", "1Day", (base + timedelta(days=i)).isoformat(), c - 0.1, c + 0.5, c - 0.5, c, 1000 + i))
    almacen.guardar_barras(con, barras, Procedencia("prueba", "propia", "EE. UU."))
    con.commit()
    b = servicio.velas(con, ajustes, "SIC:MU", "1Day", 90)["barras"]
    assert len(b) == 60
    assert b[0]["ema20"] is None and b[19]["ema20"] is not None and b[48]["ema50"] is None and b[49]["ema50"] is not None
    assert b[24]["macd"] is None and b[25]["macd"] is not None and b[32]["macd_senal"] is None and b[33]["macd_senal"] is not None
    assert b[14]["estoc_k"] is None and b[15]["estoc_k"] is not None and b[0]["sar"] is None and b[1]["sar"] is not None


# --- GEX -----------------------------------------------------------------------------------------------------------
def _opc(strike, tipo, venc="2026-11-20", gamma=0.02, oi=100, mult=100, spot=50.0, moneda="USD", inst="2026-10-16T15:00:00+00:00"):
    return {"contrato": f"{tipo}{strike}{venc}", "vencimiento": venc, "strike": strike, "tipo": tipo, "gamma": gamma,
            "interes_abierto": oi, "multiplicador": mult, "spot": spot, "moneda": moneda, "instante": inst}


def test_gex_formula_exacta_absoluta_y_firmada_separadas():
    r = gex.calcular([_opc(50, "call"), _opc(50, "put", oi=40), _opc(55, "call", venc="2026-12-18", mult=10)])
    assert r["disponible"] and r["contratos_usados"] == 3
    c = next(x for x in r["celdas"] if x["strike"] == 50)
    assert c["calls"] == pytest.approx(0.02 * 100 * 100 * 50 ** 2 * 0.01)       # 5 000
    assert c["puts"] == pytest.approx(0.02 * 40 * 100 * 50 ** 2 * 0.01)         # 2 000
    assert c["absoluta"] == pytest.approx(7000) and c["firmada"] == pytest.approx(3000)
    otro = next(x for x in r["celdas"] if x["strike"] == 55)
    assert otro["calls"] == pytest.approx(0.02 * 100 * 10 * 2500 * 0.01)        # multiplicador 10 respetado, no 100
    assert r["totales"]["absoluta"] == pytest.approx(r["totales"]["calls"] + r["totales"]["puts"])
    assert "CONVENCIÓN" in r["convencion"] and "no es" in r["convencion"].lower()


def test_gex_no_supone_multiplicador_ni_spot_y_dice_que_falta():
    sin_mult = gex.calcular([_opc(50, "call", mult=None), _opc(50, "put", mult=None)])
    assert not sin_mult["disponible"] and sin_mult["descartados"] == {"sin multiplicador": 2}
    assert "2 sin multiplicador" in sin_mult["motivo"] and "multiplicador" in sin_mult["requisito"]
    assert not gex.calcular([_opc(50, "call", spot=None)])["disponible"]
    assert gex.calcular([_opc(50, "call", oi=None)])["descartados"] == {"sin interés abierto": 1}
    assert gex.calcular([_opc(50, "call", gamma=-1)])["descartados"] == {"sin gamma válida": 1}
    assert gex.calcular([_opc(50, "call", moneda=None)])["descartados"] == {"sin moneda del spot/contrato": 1}
    assert gex.calcular([_opc(50, "call", oi=float("nan"))])["descartados"] == {"sin interés abierto": 1}
    vacio = gex.calcular([])
    assert not vacio["disponible"] and "No hay cadena" in vacio["motivo"]


def test_gex_no_mezcla_referencias_de_spot_ni_monedas():
    r = gex.calcular([_opc(50, "call"), _opc(50, "put", spot=48.0, inst="2026-10-15T15:00:00+00:00"),
                      _opc(60, "call", moneda="MXN", spot=900.0, inst="2026-10-14T15:00:00+00:00")])
    assert r["contratos_usados"] == 1 and r["moneda"] == "USD" and r["spot"] == 50.0
    assert r["descartados"] == {"otra referencia de instante/spot/moneda": 2} and "Cobertura parcial" in r["aviso"]


def test_gex_servicio_alpaca_sin_oi_no_es_fiable_y_csv_si(con, ajustes):
    t = (AHORA - timedelta(hours=1)).isoformat()
    almacen.guardar_opciones(con, [ContratoOpcion("A1", "SIC:MU", "2026-11-20", 100, "call", t, gamma=0.01, iv=0.4)],
                             Procedencia("alpaca", "x", "EE. UU.", feed="indicative"))
    con.commit()
    r = servicio.gex(con, ajustes, "SIC:MU")
    assert not r["disponible"] and r["descartados"] == {"sin interés abierto": 1} and "OPRA" in r["requisito"]
    cab = ",".join(importar_csv.COLUMNAS["opciones"] + importar_csv.EXTRA_OPCIONES)
    fila = f"B1,SIC:MU,OPRA,2026-11-20,100,put,{t},1,1.1,1,50,5,0.4,-0.4,0.01,,,x,y,100,98.5,USD"
    assert importar_csv.importar(con, "opciones", f"{cab}\n{fila}\n".encode())["guardados"] == 1
    r = servicio.gex(con, ajustes, "SIC:MU")
    assert r["disponible"] and r["contratos_usados"] == 1 and r["totales"]["puts"] == pytest.approx(0.01 * 5 * 100 * 98.5 ** 2 * 0.01)
    assert r["totales"]["firmada"] < 0
    # formato anterior (sin las tres columnas) sigue aceptado
    base = ",".join(importar_csv.COLUMNAS["opciones"])
    assert importar_csv.importar(con, "opciones", f"{base}\nC1,SIC:MU,OPRA,2026-11-20,105,call,{t},1,1.1,1,50,5,0.4,0.4,0.01,,,x,y\n".encode())["guardados"] == 1
    with pytest.raises(ValueError, match="multiplicador"):
        importar_csv.importar(con, "opciones", f"{cab}\n{fila.replace(',100,98.5,USD', ',-1,98.5,USD')}\n".encode())


def test_almacen_migra_bases_anteriores_sin_columnas_gex(tmp_path):
    import sqlite3
    c = sqlite3.connect(tmp_path / "v.db")
    almacen.inicializar(c)
    for col in ("multiplicador", "spot", "moneda"):         # base anterior a GEX
        c.execute(f"ALTER TABLE flujo_opciones DROP COLUMN {col}")
    almacen.inicializar(c)
    assert {"multiplicador", "spot", "moneda"} <= {r[1] for r in c.execute("PRAGMA table_info(flujo_opciones)")}
    c.close()


# --- Laboratorio de permutaciones ----------------------------------------------------------------------------------
def _par(n=250, mu=0.0, sigma=0.01, semilla=3):
    rng = np.random.default_rng(semilla)
    b = rng.normal(0.0003, 0.01, n)
    return b.tolist(), (b + rng.normal(mu, sigma, n)).tolist()


def test_permutacion_nulo_no_rechaza_y_formula_de_p():
    b, e = _par(mu=0.0)
    r = laboratorio.permutacion(b, {"nula": e}, bloque=5, B=999, semilla=1)
    f = r["resultados"][0]
    assert f["p"] == pytest.approx((f["extremos"] + 1) / 1000) and f["p"] > 0.05 and not f["supera_alpha_holm"]
    assert r["p_minimo"] == pytest.approx(1 / 1000) and r["bloques"] == 50 and "NO es alfa probado" not in f["lectura"]
    assert any("p < 0.05 aislado NO prueba alfa" in a for a in r["advertencias"])
    assert any("walk-forward" in a and "holdout" in a for a in r["advertencias"])


def test_permutacion_muestra_favorable_rechaza_pero_no_dice_alfa_probado():
    b, e = _par(mu=0.004, semilla=4)
    r = laboratorio.permutacion(b, {"favorable": e}, bloque=5, B=2000, semilla=7)
    f = r["resultados"][0]
    assert f["exceso_medio"] > 0.003 and f["p"] < 0.01 and f["supera_alpha_holm"]
    assert "NO es alfa probado" in f["lectura"]
    peor = laboratorio.permutacion(b, {"mala": [x - 0.02 for x in e]}, bloque=5, B=500, semilla=7)["resultados"][0]
    assert peor["p"] > 0.95                                              # exceso negativo: la cola superior no se rechaza


def test_permutacion_serie_identica_o_constante_da_p_uno():
    b, _ = _par()
    f = laboratorio.permutacion(b, {"igual": list(b)}, B=300, semilla=1)["resultados"][0]
    assert f["exceso_medio"] == 0 and f["p"] == 1.0 and math.isfinite(f["desv_exceso"]) and f["autocorr_lag1"] is None


def test_permutacion_reproducible_y_sensible_a_la_semilla():
    b, e = _par(mu=0.001)
    a1 = laboratorio.permutacion(b, {"x": e}, bloque=4, B=700, semilla=99)
    a2 = laboratorio.permutacion(b, {"x": e}, bloque=4, B=700, semilla=99)
    assert a1 == a2 and a1["huella_sha256"] == a2["huella_sha256"]
    otra = laboratorio.permutacion(b, {"x": e}, bloque=4, B=700, semilla=100)
    assert otra["huella_sha256"] != a1["huella_sha256"] and 0 < otra["resultados"][0]["p"] <= 1


def test_holm_familia_y_exploradas():
    assert laboratorio.holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert laboratorio.holm([0.4]) == [0.4]
    assert laboratorio.holm([0.01], total=5) == pytest.approx([0.05])
    b, e = _par(mu=0.003, semilla=8)
    r = laboratorio.permutacion(b, {"a": e, "b": _par(mu=0.0, semilla=9)[1]}, bloque=5, B=500, semilla=2)
    pa, pb = (x["p"] for x in r["resultados"])
    assert r["resultados"][0]["p_holm"] >= pa and r["familia"] == 2
    assert all(x["p_holm"] <= 1 for x in r["resultados"]) and r["resultados"][1]["p_holm"] >= pb
    ex = laboratorio.permutacion(b, {"a": e}, bloque=5, B=500, semilla=2, exploradas=10)
    assert ex["resultados"][0]["p_holm"] == pytest.approx(min(1, 10 * ex["resultados"][0]["p"]))


@pytest.mark.parametrize("cambio,mensaje", [
    (lambda b, e: (b, {"x": e[:-1]}, {}), "emparejadas"),
    (lambda b, e: (b[:10], {"x": e[:10]}, {}), "muestra demasiado corta"),
    (lambda b, e: (b, {"x": e[:-1] + [float("nan")]}, {}), "no es finito"),
    (lambda b, e: (b, {"x": e[:-1] + [float("inf")]}, {}), "no es finito"),
    (lambda b, e: (b, {"x": e[:-1] + ["abc"]}, {}), "no es un número"),
    (lambda b, e: (b, {"x": e[:-1] + [None]}, {}), "vacío"),
    (lambda b, e: (b, {"x": e[:-1] + [-1.5]}, {}), "decimal"),
    (lambda b, e: (b, {}, {}), "al menos una"),
    (lambda b, e: (b, {"x": e}, {"B": 10**6}), "B (volteos)"),
    (lambda b, e: (b, {"x": e}, {"B": 50}), "B (volteos)"),
    (lambda b, e: (b, {"x": e}, {"bloque": 200}), "bloque inválido"),
    (lambda b, e: (b, {"x": e}, {"alpha": 0.9}), "alpha"),
    (lambda b, e: (b, {"x": e}, {"semilla": -1}), "semilla"),
    (lambda b, e: (b, {f"e{i}": e for i in range(21)}, {}), "máximo 20"),
    (lambda b, e: (b + [0.0] * 6000, {"x": e + [0.0] * 6000}, {}), "máximo 5000"),
    (lambda b, e: (b, {"x": e}, {"hipotesis_exploradas": 0}), "exploradas"),
])
def test_permutacion_rechaza_datos_malos(cambio, mensaje):
    b, e = _par(n=60)
    bench, ests, extra = cambio(b, e)
    args = {"B": 300, "semilla": 1, "bloque": 3, **extra}
    exploradas = args.pop("hipotesis_exploradas", None)
    with pytest.raises(ValueError, match=mensaje.replace("(", r"\(").replace(")", r"\)")):
        laboratorio.permutacion(bench, ests, exploradas=exploradas, **args)


def test_permutacion_limite_de_costo():
    b, _ = _par(n=5000)
    with pytest.raises(ValueError, match="costo de cómputo"):
        laboratorio.permutacion(b, {f"e{i}": b for i in range(20)}, bloque=1, B=20000)


def test_leer_csv_formato_y_errores():
    bench, ests = laboratorio.leer_csv("fecha,estrategia,benchmark\n2026-01-01,0.01,0.005\n2026-01-02,-0.002,0.001\n")
    assert bench == ["0.005", "0.001"] and ests == {"estrategia": ["0.01", "-0.002"]}
    for malo, texto in [("sin encabezado de benchmark", "a,b\n1,2\n"), ("columnas", "e,benchmark\n1\n"),
                        ("únicos", "e,e,benchmark\n1,2,3\n"), ("al menos una columna", "benchmark\n1\n")]:
        with pytest.raises(ValueError):
            laboratorio.leer_csv(texto)


# --- API: protegida con los controles existentes -------------------------------------------------------------------
@pytest.fixture(scope="module")
def cliente():
    from terminal.app import app
    with TestClient(app, base_url="http://127.0.0.1:8765") as c:
        yield c


def test_api_laboratorio_seguridad_y_resultados(cliente):
    b, e = _par(n=120, mu=0.003, semilla=11)
    cuerpo = {"benchmark": b, "estrategias": {"s": e}, "bloque": 4, "B": 400, "semilla": 5}
    assert cliente.post("/api/laboratorio/permutacion", json=cuerpo).status_code == 403                    # sin CSRF
    assert cliente.post("/api/laboratorio/permutacion", json=cuerpo, headers={**CSRF, "Origin": "http://evil.example"}).status_code == 403
    r = cliente.post("/api/laboratorio/permutacion", json=cuerpo, headers=CSRF)
    assert r.status_code == 200 and r.json()["resultados"][0]["p"] <= 0.2 and r.json()["semilla"] == 5
    assert r.json() == cliente.post("/api/laboratorio/permutacion", json=cuerpo, headers=CSRF).json()
    csv_txt = "benchmark,s\n" + "\n".join(f"{x:.6f},{y:.6f}" for x, y in zip(b, e))
    assert cliente.post("/api/laboratorio/permutacion", json={"csv": csv_txt, "B": 300}, headers=CSRF).status_code == 200
    malo = cliente.post("/api/laboratorio/permutacion", json={**cuerpo, "estrategias": {"s": e[:-1] + ["nan"]}}, headers=CSRF)
    assert malo.status_code in (422, 400)
    assert cliente.post("/api/laboratorio/permutacion", json={"csv": "x"}, headers=CSRF).status_code == 422
    assert cliente.post("/api/laboratorio/permutacion", content=b"x" * 1_300_000,
                        headers={**CSRF, "content-type": "application/json"}).status_code == 413           # tamaño acotado
    assert cliente.post("/api/laboratorio/permutacion", json=cuerpo, headers=CSRF, extensions={}).status_code == 200
    assert "/api/laboratorio/permutacion" in __import__("terminal.seguridad", fromlist=["x"]).LIMITES


def test_api_laboratorio_limite_por_minuto():
    from terminal import seguridad
    from terminal.app import app
    lim = seguridad.LIMITES["/api/laboratorio/permutacion"]
    with TestClient(app, base_url="http://127.0.0.1:8765") as c:
        codigos = [c.post("/api/laboratorio/permutacion", json={"csv": "x"}, headers=CSRF).status_code for _ in range(lim + 2)]
    assert 429 in codigos


def test_api_gex_y_velas_y_plan_intradia(cliente):
    g = cliente.get("/api/flujo/gex", params={"subyacente": "SIC:NOEXISTE"}).json()
    assert g["disponible"] is False and "No hay cadena" in g["motivo"] and g["requisito"]
    p = cliente.get("/api/plan-intradia").json()
    assert p["modo"] == "informativo" and p["ordenes"] == [] and p["senal_ejecutable"] is False and p["inhibida"] is True
    assert cliente.get("/api/plan-intradia", params={"perdida_dia_mxn": -5}).status_code == 422
    assert cliente.post("/api/plan-intradia", headers=CSRF).status_code == 405


# --- Plan intradía -------------------------------------------------------------------------------------------------
def test_plan_intradia_inhibe_con_datos_diarios_o_retrasados(con, ajustes):
    iid = "SIC:MU"
    d = plan_intradia._dato_intradia(con, iid, AHORA, 60)
    assert not d["apto"] and d["tipo"] == "diario"
    ini = (AHORA - timedelta(minutes=6)).replace(second=0, microsecond=0)
    almacen.guardar_barras(con, [Barra(iid, "5Min", ini.isoformat(), 10, 11, 9, 10, 5)],
                           Procedencia("x", "y", "z", retraso_s=900))
    con.commit()
    assert "retrasado 900" in plan_intradia._dato_intradia(con, iid, AHORA, 60)["motivo"]
    almacen.guardar_barras(con, [Barra(iid, "5Min", (ini + timedelta(minutes=5)).isoformat(), 10, 11, 9, 10, 5)],
                           Procedencia("x2", "y", "z", retraso_s=None))
    con.commit()
    assert plan_intradia._dato_intradia(con, iid, AHORA, 60)["motivo"] == "retraso desconocido"
    almacen.guardar_barras(con, [Barra(iid, "1Min", (AHORA - timedelta(minutes=1)).isoformat(), 10, 11, 9, 10, 5)],
                           Procedencia("x3", "y", "z", retraso_s=2))
    con.commit()
    assert plan_intradia._dato_intradia(con, iid, AHORA, 60)["apto"] is True


def test_plan_intradia_reglas_pausa_costos_y_sin_futuros(con, ajustes):
    r = plan_intradia.calcular(con, ajustes, perdida_dia_mxn=None)
    assert r["senal_ejecutable"] is False and r["ordenes"] == [] and r["pausa"]["estado"] == "no_informado"
    texto = " ".join(r["reglas"]) + r["aviso"]
    assert "No promediar pérdidas" in texto and "Pausa tras la pérdida límite" in texto
    assert "futuros no son elegibles" in texto and "recomienda" not in texto.replace("no se recomiendan", "")
    assert r["costos"]["ida_y_vuelta_pct"] is None or r["costos"]["ida_y_vuelta_pct"] == pytest.approx(2 * r["costos"]["por_operacion_pct"])
    assert any(x["dato"].startswith("Barras intradía") and x["estado"] == "falta" for x in r["disponibilidad"])
    assert plan_intradia.calcular(con, ajustes, 0.0)["pausa"]["estado"] in ("no_informado", "dentro_del_limite")


def test_plan_intradia_pausa_con_perdida_limite(con, ajustes, monkeypatch):
    cart = {"fuente": "portal", "valor_total": 1_000_000.0, "posiciones": [
        {"instrumento_id": "SIC:MU", "clave_operable": "MU", "cantidad": 10, "peso": 0.6, "no_realizado_pct": -0.05},
        {"instrumento_id": "SIC:AMD", "clave_operable": "AMD", "cantidad": 5, "peso": 0.4, "no_realizado_pct": 0.02}]}
    monkeypatch.setattr(plan_intradia.servicios, "cartera_actual", lambda *a, **k: cart)
    ok = plan_intradia.calcular(con, ajustes, 5_000.0)
    assert ok["pausa"]["estado"] == "dentro_del_limite" and not ok["pausa"]["activa"]
    r = plan_intradia.calcular(con, ajustes, 10_000.0)                       # 1 % de 1 000 000
    assert r["pausa"]["activa"] and "PAUSA" in r["pausa"]["mensaje"] and "Pausa por pérdida límite del día." in r["motivos_inhibicion"]
    assert [x["clave"] for x in r["no_promediar"]["posiciones_en_perdida"]] == ["MU"]
    assert r["concentracion"]["excede"] and r["concentracion"]["mayor"] == "MU"
    assert r["presupuesto_perdida"]["perdida_diaria_mxn"] == pytest.approx(10_000)
    assert r["senal_ejecutable"] is False


def test_permutacion_parametro_infinito_rechazado():
    with pytest.raises(ValueError, match="enteros"):
        laboratorio.permutacion([0.0] * 40, {"estrategia": [0.01] * 40}, B=float("inf"))


def test_plan_intradia_no_acepta_barras_sinteticas(con):
    almacen.guardar_barras(con, [Barra("SIC:MU", "1Min", (AHORA - timedelta(minutes=1)).isoformat(), 10, 11, 9, 10, 5)],
                           Procedencia("prueba", "fixture", "XNAS", calidad="sintetico", retraso_s=0))
    con.commit()
    d = plan_intradia._dato_intradia(con, "SIC:MU", AHORA, 60)
    assert not d["apto"] and "sintética" in d["motivo"]
