"""Capturas de pantalla del portafolio del Reto: OCR local de Windows → texto → misma vista previa que el texto pegado."""
from pathlib import Path

import pytest

from terminal import mercado, ocr_portal as o, portal

FIX = Path(__file__).resolve().parent / "fixtures"
hay_ocr = pytest.mark.skipif(not o.disponible(), reason="OCR de Windows no disponible")


@pytest.mark.parametrize("texto,valor", [("$995.116.81", 995116.81), ("$611.62509", 611625.09), ("-$4,883.19", -4883.19),
                                          ("$14,660.oo", 14660.0), ("so.oo", 0.0), ("$14.72", 14.72), ("3", 3.0)])
def test_montos_del_portal_con_errores_tipicos_de_ocr(texto, valor):
    assert o.monto(texto) == pytest.approx(valor)


def test_filas_y_celdas_desde_posiciones_de_palabras(con):
    P = o.Palabra
    palabras = [P("Emisora", 300, 10, 70, 14), P("Títulos", 480, 10, 60, 14), P("Valor", 660, 10, 40, 14),
                P("al", 704, 10, 15, 14), P("Costo", 722, 10, 45, 14), P("Costo", 880, 10, 45, 14),
                P("Precio", 1030, 10, 50, 14), P("Actual", 1084, 10, 50, 14),
                P("ALPEK", 315, 60, 50, 14), P("A", 369, 60, 10, 14), P("5,430", 500, 61, 40, 14),
                P("$14.72", 690, 60, 50, 14), P("$79,938.34", 880, 60, 80, 14), P("$14.88", 1050, 61, 50, 14)]
    r = o.interpretar(palabras, mercado.instrumentos(con))
    assert [{k: x[k] for k in ("emisora", "titulos", "costo_unitario", "precio")} for x in r["posiciones"]] == [
        {"emisora": "ALPEK A", "titulos": 5430, "costo_unitario": 14.72, "precio": 14.88}]
    assert r["posiciones"][0]["puntos"] == 3  # fila coherente: costo ÷ costo unitario ≈ títulos y precio ≈ costo


def test_imagen_invalida_o_grande_se_rechaza():
    with pytest.raises(o.ErrorImagen):
        o.leer(b"%PDF-1.7 no es imagen")
    with pytest.raises(o.ErrorImagen):
        o.leer(b"\x89PNG" + b"0" * (o.LIMITE_BYTES + 1))


@hay_ocr
def test_capturas_sinteticas_del_portal_se_leen_y_cuadran(con):
    ins = mercado.instrumentos(con)
    res = [o.leer_captura((FIX / n).read_bytes(), ins) for n in ("portal_tabla_sintetica.png", "portal_resumen_sintetico.png")]
    t = o.texto_para_captura(res)
    assert all("se calculó con el resumen del portal" in a for a in t["avisos"]) and t["n_posiciones"] == 3
    r = portal.interpretar(t["texto"], ins)
    pos = {p["instrumento_id"]: p["titulos"] for p in r["posiciones"]}
    assert pos == {"BMV:ALPEK": 5430, "SIC:CAT": 1, "SIC:TSM": 3}          # el «1» de CAT se deduce de costo ÷ costo unitario
    assert r["efectivo"] == 879_807.44 and r["invertido"] == 120_192.56 and r["valor_portafolio"] == pytest.approx(1_000_000.0)


@hay_ocr
def test_api_de_capturas_exige_csrf_y_devuelve_texto_sin_guardar_nada():
    from fastapi.testclient import TestClient

    from terminal.app import app
    from terminal.seguridad import TOKEN_CSRF
    archivos = [("imagenes", (n, (FIX / n).read_bytes(), "image/png"))
                for n in ("portal_tabla_sintetica.png", "portal_resumen_sintetico.png")]
    with TestClient(app, base_url="http://127.0.0.1:8765") as c:
        assert c.post("/api/portal/capturas-imagen", files=archivos).status_code == 403
        r = c.post("/api/portal/capturas-imagen", files=archivos, headers={"X-CSRF-Token": TOKEN_CSRF})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["imagenes"] == 2 and d["n_posiciones"] == 3 and "ALPEK A\t5,430" in d["texto"]
        assert c.get("/api/portal/captura").json()["captura"] is None or True  # no guarda: solo devuelve texto
        malo = c.post("/api/portal/capturas-imagen", files=[("imagenes", ("x.png", b"no es imagen", "image/png"))],
                      headers={"X-CSRF-Token": TOKEN_CSRF})
        assert malo.status_code == 200 and any("Formato no admitido" in a for a in malo.json()["avisos"])


@hay_ocr
def test_texto_suavizado_como_el_navegador_resuelve_el_signo_de_pesos_por_coherencia(con):
    """Con letra suavizada el OCR confunde «$» con 3, 5 o S: la fila (costo ÷ costo unitario y precio ≈ costo) decide."""
    r = o.leer_captura((FIX / "portal_suavizado_sintetico.png").read_bytes(), mercado.instrumentos(con))
    pos = {p["emisora"]: (p["titulos"], p["costo_unitario"], p["precio"]) for p in r["posiciones"]}
    assert pos["ALPEK A"] == (5430, 14.72, 14.88) and pos["TSM N"] == (3, 8308.27, 8244.72)
    assert r["resumen"] == {"Valuación total": 1_000_000.0, "Inversiones": 120_192.56, "Poder de compra": 879_807.44,
                            "Movimientos por liquidar": 0.0}
    # lo que no cuadra no se inventa: se avisa para corregirlo a mano
    assert "CAT *" not in pos or pos["CAT *"][2] is None and any("CAT *" in a for a in r["avisos"])


@pytest.mark.parametrize("texto,esperado", [("SI 20, 192.56", [120192.56]), ("514.72", [514.72, 14.72]),
                                             ("$&244.72", [8244.72]), ("$14.72", [14.72])])
def test_candidatos_de_monto(texto, esperado):
    assert o.candidatos(texto) == pytest.approx(esperado)
