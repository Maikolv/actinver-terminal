"""El seguimiento calcula correctamente posiciones y rendimientos a partir de operaciones conocidas."""
import pandas as pd
import pytest

from terminal import cartera, importar, mercado

T = [
    {"fecha": "2024-01-02", "tipo": "aportacion", "monto": 100000},
    {"fecha": "2024-01-03", "tipo": "compra", "instrumento_id": "SIC:IVV", "cantidad": 10, "precio": 1000, "comision": 29},
    {"fecha": "2024-02-01", "tipo": "compra", "instrumento_id": "SIC:IVV", "cantidad": 10, "precio": 1200, "comision": 35},
    {"fecha": "2024-03-01", "tipo": "venta", "instrumento_id": "SIC:IVV", "cantidad": 5, "precio": 1500, "comision": 20, "impuesto": 10},
    {"fecha": "2024-04-01", "tipo": "dividendo", "instrumento_id": "SIC:IVV", "monto": 100, "impuesto": 10},
    {"fecha": "2024-05-01", "tipo": "retiro", "monto": 1000},
    {"fecha": "2024-06-01", "tipo": "split", "instrumento_id": "SIC:IVV", "cantidad": 2},
    {"fecha": "2024-06-02", "tipo": "comision", "monto": 50},
]


def normalizar(con, filas):
    ins = mercado.instrumentos(con)
    return [{**cartera.validar(t, ins), "id": i} for i, t in enumerate(filas, 1)]


def test_costo_promedio_realizado_no_realizado(con):
    tx = normalizar(con, T)
    r = cartera.calcular(tx, {"SIC:IVV": 700.0})
    p = r["posiciones"][0]
    # costo tras compras: 10*1000+29 + 10*1200+35 = 22064 ; promedio 1103.2
    # venta 5: costo salida 5516 ; ingreso neto 7500-20-10 = 7470 ; realizado 1954
    assert p["realizado"] == pytest.approx(1954.0)
    # quedan 15 títulos con costo 16548; split 2:1 -> 30 títulos, costo total igual
    assert p["cantidad"] == pytest.approx(30)
    assert p["costo_total"] == pytest.approx(16548.0)
    assert p["costo_promedio"] == pytest.approx(16548 / 30)
    assert p["valor_mxn"] == pytest.approx(21000.0)
    assert p["no_realizado"] == pytest.approx(21000 - 16548)
    assert p["dividendos"] == pytest.approx(90.0)
    # efectivo: 100000 -10029 -12035 +7470 +90 -1000 -50
    assert r["efectivo"] == pytest.approx(84446.0)
    assert r["comisiones"] == pytest.approx(29 + 35 + 20 + 50)
    assert r["impuestos"] == pytest.approx(10 + 10)
    assert r["aportacion_neta"] == pytest.approx(99000.0)
    assert r["valor_total"] == pytest.approx(84446 + 21000)
    assert r["resultado_total"] == pytest.approx(84446 + 21000 - 99000)


def test_venta_mayor_a_posicion_se_rechaza(con):
    tx = normalizar(con, T[:2] + [{"fecha": "2024-01-04", "tipo": "venta", "instrumento_id": "SIC:IVV", "cantidad": 11, "precio": 1}])
    with pytest.raises(cartera.ErrorValidacion):
        cartera.calcular(tx, {})


def test_moneda_usd_con_tipo_de_cambio(con):
    tx = normalizar(con, [{"fecha": "2024-01-02", "tipo": "aportacion", "monto": 1000, "moneda": "USD", "tipo_cambio": 17},
                          {"fecha": "2024-01-03", "tipo": "compra", "instrumento_id": "SIC:IVV", "cantidad": 1, "precio": 500,
                           "moneda": "USD", "tipo_cambio": 17}])
    r = cartera.calcular(tx, {"SIC:IVV": 9000.0})
    assert r["efectivo"] == pytest.approx(500 * 17)
    assert r["posiciones"][0]["costo_total"] == pytest.approx(8500)


def test_validacion_mensajes_claros(con):
    ins = mercado.instrumentos(con)
    with pytest.raises(cartera.ErrorValidacion) as e:
        cartera.validar({"fecha": "02/01/2024", "tipo": "compra", "instrumento_id": "NOEXISTE", "cantidad": -1}, ins)
    txt = " ".join(e.value.errores)
    assert "AAAA-MM-DD" in txt and "universo verificado" in txt and "cantidad" in txt
    # tolerante con formato: clave corta, mayúsculas, comas de miles
    t = cartera.validar({"fecha": "2024-01-03", "tipo": " Compra ", "instrumento_id": "ivv", "cantidad": "1,000",
                         "precio": "10"}, ins)
    assert t["instrumento_id"] == "SIC:IVV" and t["cantidad"] == 1000


def test_duplicados_anulacion_y_correccion_auditadas(con):
    ins = mercado.instrumentos(con)
    a = cartera.validar(T[0], ins)
    assert cartera.registrar(con, a, "manual") is not None
    assert cartera.registrar(con, a, "manual") is None  # duplicado exacto
    c = cartera.validar(T[1], ins)
    cid = cartera.registrar(con, c, "manual")
    con.commit()
    nid = cartera.corregir(con, cid, {"precio": 990}, ins, "precio mal capturado")
    filas = {f["id"]: f for f in cartera.listar(con, incluir_anuladas=True)}
    assert filas[cid]["anulada"] == 1 and filas[nid]["reemplaza_id"] == cid and filas[nid]["precio"] == 990
    acciones = [r["accion"] for r in con.execute("SELECT accion FROM auditoria ORDER BY id")]
    assert acciones.count("alta") == 2 and "correccion" in acciones
    cartera.anular(con, nid, "prueba")
    assert all(f["id"] != nid for f in cartera.listar(con))


def test_serie_historica_twr_con_flujos():
    fechas = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])
    precios = pd.DataFrame({"X": [100.0, 110.0, 121.0]}, index=fechas)
    tx = [{"id": 1, "fecha": "2024-01-02", "tipo": "aportacion", "monto": 1000, "tipo_cambio": 1},
          {"id": 2, "fecha": "2024-01-02", "tipo": "compra", "instrumento_id": "X", "cantidad": 10, "precio": 100,
           "comision": 0, "impuesto": 0, "tipo_cambio": 1},
          {"id": 3, "fecha": "2024-01-03", "tipo": "aportacion", "monto": 5000, "tipo_cambio": 1}]
    s = cartera.serie_historica(tx, precios)
    # la aportación del día 2 no debe contar como rendimiento: 10 % + 10 % sobre la parte invertida
    assert s["valor"].iloc[-1] == pytest.approx(5000 + 1210)
    assert s["rend_diario"].iloc[1] == pytest.approx(0.10)
    assert s["twr_acumulado"].iloc[-1] == pytest.approx((1.10 * (1 + 110 / 6100)) - 1)


def test_importar_posiciones_iniciales(con):
    csv = b"fecha,instrumento_id,cantidad,costo_promedio\n2024-01-02,FONDO:ACTIGOB,1000,5.5\n"
    rep = importar.importar(con, csv, "pos.csv", "posiciones", mercado.instrumentos(con), confirmar=True)
    assert rep["aceptadas"] == 1
    r = cartera.calcular(cartera.listar(con), {"FONDO:ACTIGOB": 6.0})
    assert r["efectivo"] == pytest.approx(0) and r["no_realizado"] == pytest.approx(500)
