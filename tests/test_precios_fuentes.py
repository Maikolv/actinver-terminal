"""Cobertura de precios: símbolos EODHD, reserva de cupo, hoja oficial de fondos Actinver, prioridad entre fuentes,
Twelve Data solo con cobertura verificada y fondos con precio confiable en boletas."""
from datetime import UTC, datetime

import httpx
import pytest

from terminal import cotizaciones as cz, fondos_actinver as fa, ingesta, mercado
from terminal.adaptadores.proveedores import Eodhd, TwelveData

HOJA = """martes, 29 de septiembre de 2026
ACTIGOB
Personas Físicas
B 7.025596 -2.73% 3.23% 4.07%
Personas Morales
M-1 7.439646 -2.51% 3.46%
ACTIG+
Personas Físicas
B 1.769663 -1.0% 2.0%
ACTIG+2 -Morningstar Inc. Todos los derechos reservados.
Personas Físicas
B 1.660545 -8.27% 4.43%
ACTICOB
Personas Físicas
B; USD 1.347333 6.10% -0.28%
B; MXN 24.177216 12,694.77% 100.29%
JPMRVUS
Personas Físicas
B-1; MXN 1.344672 0.88% 5.88%
-Rendimientos netos anualizados calculados con precios de valuación al 28/09/26.
"""


def test_simbolos_eodhd_conservan_ampersand_y_guion():
    assert Eodhd.simbolo({"clave": "PE&OLES", "serie": "*"}) == "PE&OLES"
    assert Eodhd.simbolo({"clave": "LASITE", "serie": "B-1"}) == "LASITEB-1"
    assert Eodhd.simbolo({"clave": "GFNORTE", "serie": "O"}) == "GFNORTEO"
    assert TwelveData.simbolo({"clave": "LIVEPOL", "serie": "C-1"}) == "LIVEPOLC.1"


def test_eodhd_codifica_el_ampersand_en_la_url(con):
    urls = []
    cli = httpx.Client(transport=httpx.MockTransport(lambda r: urls.append(str(r.url)) or httpx.Response(200, json=[])))
    Eodhd(con, {}, "clave", cliente=cli).historico({"clave": "PE&OLES", "serie": "*"}, datetime(2026, 9, 1).date(),
                                                    datetime(2026, 9, 28).date())
    assert "/eod/PE%26OLES.MX" in urls[0]


def test_la_reserva_de_cupo_pone_primero_a_los_nunca_cargados(con):
    from conftest import sembrar_precios
    sembrar_precios(con, ["BMV:AMX"], sesiones=10)
    instrs = [{"id": i} for i in ("BMV:AMX", "BMV:GCC", "BMV:VESTA")]
    assert [i["id"] for i in ingesta.orden_cola(con, instrs, reserva_nuevos=1)] == ["BMV:GCC", "BMV:AMX", "BMV:VESTA"]


def test_hoja_de_fondos_fecha_series_y_pie_pegado():
    h = fa.interpretar(HOJA)
    assert h["fecha_valuacion"] == "2026-09-28"
    k = {(f["fondo"], f["serie"], f["moneda"]): f["precio"] for f in h["filas"]}
    assert k[("ACTIG+", "B", "MXN")] == 1.769663 and k[("ACTIG+2", "B", "MXN")] == 1.660545   # no se mezclan
    assert k[("ACTICOB", "B", "MXN")] == 24.177216 and k[("ACTICOB", "B", "USD")] == 1.347333
    with pytest.raises(fa.ErrorHoja):
        fa.interpretar(HOJA.replace("precios de valuación al 28/09/26", "sin fecha"))


def test_importar_hoja_asigna_serie_exacta_y_verifica_cobertura(con, monkeypatch):
    monkeypatch.setattr(fa, "texto_pdf", lambda b: HOJA)
    r = fa.importar(con, b"%PDF-1.7 prueba", "hoja.pdf")
    precios = {p["id"]: p["precio"] for p in r["precios"]}
    assert precios["FONDO:ACTIGOB"] == 7.025596 and precios["FONDO:ACTICOB"] == 24.177216        # MXN, no USD
    assert "FONDO:JPMRVUS" in r["sin_serie_en_documento"]                                          # B-1 ≠ B
    fila = con.execute("SELECT tipo_dato, moneda, fecha FROM precios WHERE instrumento_id='FONDO:ACTIGOB'").fetchone()
    assert tuple(fila) == ("nav", "MXN", "2026-09-28")
    assert cz.cobertura_verificada(con, "actinver_pdf", "FONDO:ACTIGOB")
    with pytest.raises(fa.ErrorHoja):
        fa.importar(con, b"no es pdf", "x.txt")


def test_hoja_ambigua_no_asigna(con, monkeypatch):
    monkeypatch.setattr(fa, "texto_pdf", lambda b: HOJA + "ACTIGOB\nPersonas Físicas\nB 9.999999 1%\n")
    r = fa.importar(con, b"%PDF-1.7", "hoja.pdf", confirmar=False)
    assert "FONDO:ACTIGOB" in r["sin_serie_en_documento"]


def test_fondo_con_precio_de_la_hoja_es_confiable_al_dia_siguiente(con, monkeypatch):
    monkeypatch.setattr(fa, "texto_pdf", lambda b: HOJA)
    fa.importar(con, b"%PDF-1.7", "hoja.pdf")
    ins = mercado.instrumentos(con)["FONDO:ACTIGOB"]
    provs = cz.construir(con, False, entorno={})
    r = cz.precio_confiable(con, provs, ins, datetime(2026, 9, 29, 21, 0, tzinfo=UTC))   # 29-sep después del cierre
    assert r["estado"] == "confiable" and r["cotizacion"]["proveedor"] == "actinver_pdf"
    assert r["calidad"] == "EOD"
    tarde = cz.precio_confiable(con, provs, ins, datetime(2026, 10, 1, 21, 0, tzinfo=UTC))  # dos sesiones después
    assert tarde["estado"] == cz.SIN_PRECIO


def test_misma_fecha_gana_la_fuente_prioritaria(con, ajustes):
    ts = "2026-09-29T00:00:00+00:00"
    con.executemany("INSERT INTO precios (instrumento_id, fecha, cierre, cierre_ajustado, volumen, moneda, proveedor, tipo_dato, "
                    "hora_cotizacion, obtenido_en) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    [("BMV:AMX", "2026-09-28", 17.0, 17.0, 0, "MXN", "archivo", "cierre", None, ts),
                     ("BMV:AMX", "2026-09-28", 17.5, 17.5, 0, "MXN", "eodhd", "cierre", None, ts),
                     ("BMV:AMX", "2026-09-25", 99.0, 99.0, 0, "MXN", "bmv_licenciado", "cierre", None, ts)])
    con.commit()
    q = mercado.cotizaciones(con, ajustes, ["BMV:AMX"])["BMV:AMX"]
    assert q["precio"] == 17.5 and q["proveedor"] == "eodhd"            # la fecha más reciente; en empate, EODHD
    assert mercado.precios_mxn(con, ajustes, ["BMV:AMX"], ajustados=False)["BMV:AMX"].iloc[-1] == 17.5


def test_twelvedata_solo_con_simbolo_verificado_y_explica_el_plan(con, tmp_path, monkeypatch):
    mapa = tmp_path / "td.json"
    mapa.write_text('{"verificados": ["BMV:GCC"]}', encoding="utf-8")
    monkeypatch.setattr(TwelveData, "MAPA", mapa)
    cli = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={
        "status": "error", "code": 403, "message": "This symbol is available starting with Pro"})))
    td = TwelveData(con, {}, "clave", cliente=cli)
    assert td.soporta({"id": "BMV:GCC", "mercado_operable": "BMV"}) and not td.soporta({"id": "BMV:KOF", "mercado_operable": "BMV"})
    from terminal.adaptadores.base import ErrorProveedor
    with pytest.raises(ErrorProveedor, match="Pro"):
        td.historico({"id": "BMV:GCC", "clave": "GCC", "serie": "*"}, datetime(2026, 9, 1).date(), datetime(2026, 9, 28).date())
    assert not TwelveData(con, {}, None).configurado()                 # sin clave, nunca se usa
