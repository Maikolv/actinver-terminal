"""Preregistro con holdout de un solo uso en el laboratorio y perfil experimental del filtro de Skylit."""
import numpy as np
import pytest
from fastapi.testclient import TestClient

from terminal import laboratorio
from terminal.flujo import skylit
from terminal.seguridad import TOKEN_CSRF

PRE = {"nombre": "cruce", "hipotesis": "exceso neto > 0", "benchmark": "NAFTRAC", "costos": "comisión Reto + IVA",
       "fuentes": "cierres EODHD", "walk_forward": "ventana 252 / prueba 21", "estrategias": ["a", "b"],
       "B": 999, "semilla": 7, "alpha": 0.05, "holdout": 0.3, "embargo": 5}


def _datos(n=200, exceso=0.0, semilla=3):
    rng = np.random.default_rng(semilla)
    b = rng.normal(0.0005, 0.01, n)
    return list(b), {"a": list(b + exceso + rng.normal(0, 0.004, n)), "b": list(b + rng.normal(0, 0.004, n))}


def test_preregistro_tramos_y_holdout_de_un_solo_uso(con):
    r = laboratorio.preregistrar(con, PRE)
    b, e = _datos(exceso=0.003)
    v = laboratorio.evaluar(con, r["id"], b, e)
    assert v["tramos"] == {"n": 200, "exploracion": 135, "embargo": 5, "holdout": 60}
    assert v["holdout"]["n"] == 60 and v["exploracion"]["n"] == 135 and v["holdout_ya_usado"] is False
    a = next(x for x in v["holdout"]["resultados"] if x["estrategia"] == "a")
    assert a["p_holm"] < 0.05                                   # exceso fuerte detectado en el holdout
    # Segunda evaluación con OTROS datos: no recalcula, devuelve lo guardado y lo marca.
    b2, e2 = _datos(exceso=-0.01, semilla=9)
    v2 = laboratorio.evaluar(con, r["id"], b2, e2)
    assert v2["holdout_ya_usado"] is True and v2["holdout"]["huella_sha256"] == v["holdout"]["huella_sha256"]
    x = laboratorio.exportar(con, r["id"])
    assert x["huella_preregistro"] == r["huella_preregistro"] and x["resultado"]["preregistro"]["walk_forward"]


def test_preregistro_valida_y_exige_estrategias_declaradas(con):
    with pytest.raises(ValueError, match="walk_forward"):
        laboratorio.preregistrar(con, {**PRE, "walk_forward": ""})
    with pytest.raises(ValueError, match="holdout"):
        laboratorio.preregistrar(con, {**PRE, "holdout": 0.9})
    r = laboratorio.preregistrar(con, PRE)
    b, e = _datos()
    with pytest.raises(ValueError, match="preregistradas"):
        laboratorio.evaluar(con, r["id"], b, {**e, "c": e["a"]})
    with pytest.raises(ValueError, match="insuficiente"):
        laboratorio.evaluar(con, r["id"], b[:40], {k: v[:40] for k, v in e.items()})
    with pytest.raises(LookupError):
        laboratorio.evaluar(con, 999999, b, e)


FILA = {"instante": "2026-10-15T14:30:00Z", "contrato": "MU261120C00250000", "subyacente": "MU", "clase_subyacente": "accion",
        "tipo": "call", "strike": "250", "vencimiento": "2026-11-20", "precio": "5.10", "tamano": "300", "multiplicador": "100",
        "moneda": "USD", "bid": "4.90", "ask": "5.10", "condicion": "I", "patas": "1", "volumen_contrato_dia": "5000",
        "interes_abierto": "400", "fecha_oi": "2026-10-14", "spot": "220"}


def test_skylit_pasa_y_magnitudes_separadas():
    r = skylit.evaluar_fila(FILA)
    assert r["resultado"] == "pasa" and r["prima_usd"] == pytest.approx(153_000)
    assert r["volumen_contrato_dia"] == 5000 and r["interes_abierto"] == 400 and r["volumen_oi"] == 12.5 and r["dte"] == 36


@pytest.mark.parametrize("cambio,criterio,estado", [
    ({"tamano": "100"}, "prima", "no_cumple"),                     # 51 000 USD
    ({"vencimiento": "2027-06-30"}, "vencimiento", "no_cumple"),
    ({"interes_abierto": "600"}, "volumen_oi", "no_cumple"),
    ({"strike": "200"}, "fuera_del_dinero", "no_cumple"),
    ({"clase_subyacente": "etf"}, "accion", "no_cumple"),
    ({"patas": "2"}, "una_pata", "no_cumple"),
    ({"precio": "5.00"}, "en_ask", "no_cumple"),
    ({"bid": "", "ask": ""}, "en_ask", "no_evaluable"),
    ({"condicion": ""}, "una_pata", "no_evaluable"),
    ({"interes_abierto": "0"}, "volumen_oi", "no_evaluable"),
    ({"spot": ""}, "fuera_del_dinero", "no_evaluable"),
    ({"multiplicador": ""}, "prima", "no_evaluable"),
])
def test_skylit_cada_criterio(cambio, criterio, estado):
    r = skylit.evaluar_fila({**FILA, **cambio})
    assert r["criterios"][criterio]["estado"] == estado
    assert r["resultado"] == ("no_pasa" if estado == "no_cumple" else "no_evaluable")


def test_skylit_csv_no_cuenta_filtro_completo_si_faltan_datos():
    filas = [FILA, {**FILA, "bid": "", "ask": ""}]
    csv = skylit.plantilla() + "\n".join(",".join(f[c] for c in skylit.COLUMNAS) for f in filas)
    r = skylit.evaluar_csv(csv)
    assert r["conteo"] == {"pasa": 1, "no_pasa": 0, "no_evaluable": 1}
    assert r["filtro_completo_aplicado"] is False and r["no_evaluables_por_criterio"] == {"en_ask": 1}
    with pytest.raises(ValueError, match="obligatorias"):
        skylit.evaluar_csv("contrato,precio\nX,1")


def test_api_preregistro_y_skylit():
    from terminal import app as modulo
    with TestClient(modulo.app, base_url="http://127.0.0.1:8765") as c:
        h = {"X-CSRF-Token": TOKEN_CSRF}
        assert c.post("/api/laboratorio/preregistro", json=PRE).status_code == 403           # CSRF
        assert c.post("/api/laboratorio/preregistro", json={**PRE, "nombre": ""}, headers=h).status_code == 422
        assert c.post("/api/laboratorio/experimentos/999999/evaluar", json={"csv": "benchmark,a\n0,0"}, headers=h).status_code == 404
        assert c.get("/api/laboratorio/experimentos/999999/exportar").status_code == 404
        assert c.post("/api/flujo/skylit", json={"csv": "x\n1"}, headers=h).status_code == 422
        assert c.get("/api/flujo/skylit/plantilla").text.startswith("instante,contrato")
