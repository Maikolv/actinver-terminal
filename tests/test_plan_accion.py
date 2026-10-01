"""Plan de acción: con y sin saldo confirmado, cotización confiable frente a referencia SIC y efectivo limitado."""
from datetime import UTC, datetime, timedelta

import pandas as pd

from terminal import cartera, mercado, migraciones, plan_accion, portal, servicios, vigencia

from conftest import sembrar_precios

PROP = {"clave": "acciones_puntuacion", "nombre": "Acciones · Máxima puntuación", "estado": "calculada", "avisos": [],
        "puntuacion": {"total": 73.0, "criterios": []}, "datos_hasta": "2026-09-29",
        "pesos": [{"id": "BMV:AMX", "peso": 0.3}, {"id": "SIC:AAPL", "peso": 0.2}],
        "cambios": {"filas": [
            {"id": "BMV:AMX", "clave_operable": "AMX B", "peso_actual": 0.0175, "peso_objetivo": 0.3, "delta_pp": 28.3,
             "monto_mxn": 282_500.0, "accion": "comprar"},
            {"id": "SIC:AAPL", "clave_operable": "AAPL *", "peso_actual": 0.0, "peso_objetivo": 0.2, "delta_pp": 20.0,
             "monto_mxn": 200_000.0, "accion": "comprar"}]}}


def _base(con):
    sembrar_precios(con, ["BMV:AMX", "BMV:WALMEX"], fin=vigencia.ultima_sesion_cerrada("XMEX"), sesiones=300, proveedor="archivo",
                    con_fx=False)
    sembrar_precios(con, ["SIC:AAPL"], fin=vigencia.ultima_sesion_cerrada("XNYS"), sesiones=300, proveedor="tiingo")
    migraciones.completar_tiempos(con)
    con.executemany("INSERT INTO universo_simulador VALUES (?,?,?)", [("BMV:AMX", "AMX B", "x"), ("SIC:AAPL", "AAPL *", "x"),
                                                                  ("BMV:WALMEX", "WALMEX *", "x")])
    t = cartera.validar({"fecha": "2026-09-28", "tipo": "aportacion", "monto": 1_000_000, "moneda": "MXN", "tipo_cambio": 1},
                        mercado.instrumentos(con))
    cartera.registrar(con, t, "prueba")
    con.commit()


def _capturar(con, efectivo):
    hora = (pd.Timestamp.now(tz="America/Mexico_City") - timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M")
    texto = (f"Emisora\tSerie\tTítulos\tPrecio actual\tValor de mercado\nAMX\tB\t1,000\t17.50\t17,500.00\n"
             f"Poder de compra\t${efectivo:,.2f}\nValuación Total Ahora\t${efectivo + 17_500:,.2f}\n")
    r = portal.guardar(con, texto, hora, mercado.instrumentos(con), confirmar=True)
    assert r["confirmado"], r["errores"]


def test_sin_saldo_confirmado_todo_queda_pendiente(con, ajustes):
    _base(con)
    plan = plan_accion.calcular(con, ajustes, propuesta=PROP)
    assert not plan["cuenta"]["confirmada"] and plan["faltan"][0].startswith("Saldo confirmado")
    assert plan["acciones"] and all(a["decision"] == "pendiente" and a["cantidad"] is None for a in plan["acciones"])
    assert all("Saldo confirmado" in a["falta"][0] for a in plan["acciones"])


def test_con_saldo_confirmado_compra_bmv_y_sic_queda_pendiente_con_referencia(con, ajustes):
    _base(con)
    _capturar(con, 982_500.0)
    plan = plan_accion.calcular(con, ajustes, propuesta=PROP)
    assert plan["cuenta"]["confirmada"]
    amx, aapl = plan["acciones"]
    assert amx["instrumento_id"] == "BMV:AMX" and amx["prioridad"] == 1
    assert amx["decision"] == "comprar" and amx["cantidad"] > 0 and amx["precio_limite"] and amx["invalidacion"]
    assert aapl["decision"] == "pendiente" and aapl["cantidad"] is None and aapl["precio"]["es_referencia"]
    assert any("confiable" in f for f in aapl["falta"])
    assert plan["reglas"]["activo"] and plan["reglas"]["catalogo"] == 3


def test_las_compras_no_exceden_el_efectivo_confirmado(con, ajustes):
    _base(con)
    _capturar(con, 300_000.0)  # valor 317,500: cada compra de 155,000 (49 %) cabe en la regla, las dos juntas no en el efectivo
    filas = [{"id": i, "clave_operable": c, "peso_actual": 0.0, "peso_objetivo": 0.47, "delta_pp": d, "monto_mxn": 155_000.0,
              "accion": "comprar"} for i, c, d in (("BMV:AMX", "AMX B", 47.0), ("BMV:WALMEX", "WALMEX *", 46.0))]
    p = {**PROP, "pesos": [{"id": "BMV:AMX", "peso": 0.47}, {"id": "BMV:WALMEX", "peso": 0.46}], "cambios": {"filas": filas}}
    plan = plan_accion.calcular(con, ajustes, propuesta=p)
    compras = [a for a in plan["acciones"] if a["decision"] == "comprar"]
    gasto = sum(a["monto"] * 1.00116 for a in compras)

    assert len(compras) == 2 and gasto <= 300_000.0 + 0.01 and "reducida" in compras[1]["motivo"]
    assert plan["cuenta"]["efectivo_tras_compras"] >= -0.01


def test_propuesta_fuera_del_catalogo_es_error_de_reglas(con, ajustes):
    _base(con)
    p = {**PROP, "pesos": PROP["pesos"] + [{"id": "SIC:QQQ", "peso": 0.1}]}
    plan = plan_accion.calcular(con, ajustes, propuesta=p)
    assert any("fuera del catálogo" in e for e in plan["reglas"]["errores"]) and any("SIC:QQQ" in f for f in plan["faltan"])


def test_telegram_y_plan_de_accion_coinciden(con, ajustes):
    """El mensaje del plan del día se arma con el MISMO plan de acción que muestra la interfaz (/api/plan-accion)."""
    from terminal import resumen
    _base(con)
    local = pd.Timestamp.now(tz="America/Mexico_City")
    plan = plan_accion.calcular(con, ajustes, propuesta=PROP)
    cart = servicios.cartera_actual(con, ajustes)
    _, texto, _ = resumen.construir(PROP, cart, None, local, plan=plan, props={"x": PROP})
    assert f"Decisión pendiente ({plan['resumen']['pendiente']})" in texto and "🟢 Comprar" not in texto
    _capturar(con, 982_500.0)
    plan = plan_accion.calcular(con, ajustes, propuesta=PROP)
    cart = servicios.cartera_actual(con, ajustes)
    _, texto, _ = resumen.construir(PROP, cart, None, local, plan=plan, props={"x": PROP})
    amx = plan["acciones"][0]
    assert f"🟢 Comprar AMX B: {amx['cantidad']:,} títulos, límite ${amx['precio_limite']:,.2f}" in texto
    assert f"{plan['resumen']['comprar']} compra(s)" in texto and "✅ confirmada" in texto


def test_venta_total_sic_pendiente_indica_todos_los_titulos(con, ajustes):
    _base(con)
    hora = (pd.Timestamp.now(tz="America/Mexico_City") - timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M")
    precio = float(mercado.cotizaciones(con, ajustes, ["SIC:AAPL"])["SIC:AAPL"]["precio_mxn"])
    texto = (f"Emisora\tSerie\tTítulos\tPrecio actual\tValor de mercado\nAAPL\t*\t1\t{precio:.2f}\t{precio:.2f}\n"
             f"Poder de compra\t$500,000.00\nValuación Total Ahora\t${500_000 + precio:,.2f}\n")
    assert portal.guardar(con, texto, hora, mercado.instrumentos(con), confirmar=True)["confirmado"]
    p = {**PROP, "pesos": [{"id": "BMV:AMX", "peso": 0.3}], "cambios": {"filas": [
        {"id": "SIC:AAPL", "clave_operable": "AAPL *", "peso_actual": 0.01, "peso_objetivo": 0.0, "delta_pp": -1.0,
         "monto_mxn": -precio, "accion": "vender"}]}}
    a = plan_accion.calcular(con, ajustes, propuesta=p)["acciones"][0]
    assert a["decision"] == "pendiente" and a["referencia"]["titulos_aprox"] == 1 and "todos sus títulos" in a["referencia"]["nota"]
