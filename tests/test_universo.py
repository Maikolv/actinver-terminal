"""Las clases se verifican con fuente independiente; la etiqueta del PDF no determina la clase."""
import csv
from pathlib import Path

CFG = Path(__file__).resolve().parents[1] / "config"


def filas():
    return list(csv.DictReader((CFG / "universo.csv").open(encoding="utf-8")))


def test_seccion_etf_del_pdf_no_contiene_etf_verificados():
    rotulados = [f for f in filas() if "ETF's" in f["secciones_pdf"]]
    assert len(rotulados) == 146
    assert not [f for f in rotulados if f["clase"] == "etf"]


def test_transcripcion_pdf_completa():
    t = list(csv.DictReader((CFG / "pdf_transcripcion.csv").open(encoding="utf-8")))
    acciones = [x for x in t if x["seccion_pdf"] == "Acciones"]
    etf = [x for x in t if x["seccion_pdf"].startswith("ETF")]
    fondos = [x for x in t if x["seccion_pdf"] == "Fondos"]
    assert len(acciones) == 146 and len(fondos) == 23
    assert [x["clave_pdf"] for x in acciones] == [x["clave_pdf"] for x in etf]  # la sección «ETF's» duplica la de acciones


def test_claves_reasignadas_y_deslistadas_no_estan_activas():
    est = {f["id"]: f["estado"] for f in filas()}
    assert est["SIC:GOLD"] == "clave_reasignada" and est["SIC:PARA"] == "clave_reasignada"
    assert est["SIC:CPE"] == "deslistado_o_cambio" and est["SIC:MRO"] == "deslistado_o_cambio"
    assert est["BMV:ANGELD"] == "excluido" and est["BMV:DIABLOI"] == "excluido"


def test_fibras_y_fondos_clasificados():
    cl = {f["id"]: f["clase"] for f in filas()}
    assert all(cl[f"BMV:{k}"] == "fibra" for k in ("FUNO", "FIBRAMQ", "FIBRAPL", "TERRA"))
    assert cl["FONDO:ACTIGOB"] == "fondo_deuda" and cl["FONDO:ACTI500"] == "fondo_renta_variable"
    assert cl["SIC:IVV"] == "etf" and cl["SIC:AAPL"] == "accion"


def test_etf_del_portal_del_simulador():
    """56 ETF vistos en la pestaña «ETF's» del simulador (5-oct-2026); los apalancados e inversos quedan excluidos."""
    portal = [f for f in filas() if f["secciones_pdf"] == "ETF (portal 2026-10-05)"]
    assert len(portal) == 56 and all(f["clase"] == "etf" for f in portal)
    excluidos = {f["clave"] for f in portal if f["estado"] == "excluido"}
    assert excluidos == {"FAS", "FAZ", "PSQ", "QLD", "SOXL", "SOXS", "SPXL", "SPXS", "SQQQ", "TECL", "TECS", "TNA", "TQQQ", "TZA",
                         "ANGELD", "DIABLOI"}
    lista = list(csv.DictReader((CFG / "simulador_etf.csv").open(encoding="utf-8")))
    assert len(lista) == 56 and {"QQQ *", "NAFTRAC ISHRS", "SPY *", "SOXX *"} <= {x["clave"] for x in lista}
