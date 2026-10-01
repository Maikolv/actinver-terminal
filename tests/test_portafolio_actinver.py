"""«Mi portafolio Actinver»: captura con el formato del portal del Reto (poder de compra, inversiones, movimientos por
liquidar), vista previa con diferencias, errores, duplicados y confirmación."""
from terminal import mercado, portal, servicios

TEXTO = ("TU INVERSIÓN\n"
         "Valuación Total Ahora\t$995,116.81\n"
         "Inversiones\t$611,625.09\n"
         "Poder de compra\t$229,883.38\n"
         "Movimientos por liquidar\t$153,608.34\n"
         "Emisora\tSerie\tTítulos\tCosto promedio\tPrecio actual\tValor de mercado\n"
         "ALPEK\tA\t20,000\t14.90\t14.78\t295,600.00\n"
         "MU\t*\t16\t19,600.00\t19,751.56\t316,025.09\n")


def test_reconoce_las_etiquetas_del_portal_y_cuadra_con_lo_por_liquidar(con):
    r = portal.interpretar(TEXTO, mercado.instrumentos(con))
    assert r["valor_portafolio"] == 995_116.81 and r["efectivo"] == 229_883.38
    assert r["por_liquidar"] == 153_608.34 and r["invertido"] == 611_625.09
    assert {p["instrumento_id"] for p in r["posiciones"]} == {"BMV:ALPEK", "SIC:MU"}
    assert not any("no cuadran" in a for a in r["advertencias"])


def test_vista_previa_no_guarda_y_muestra_diferencias_frente_al_registro_local(con, ajustes):
    r = portal.guardar(con, TEXTO, "2026-09-30T14:45", mercado.instrumentos(con), confirmar=False)
    assert not r["errores"] and not r["confirmado"] and portal.captura(con) is None
    d = portal.diferencias(con, ajustes, r)
    assert any("Primera captura" in x for x in d["frente_a_captura_anterior"])
    assert any("efectivo" in x.lower() for x in d["frente_al_registro_local"])


def test_confirmar_guarda_la_cuenta_y_la_cartera_incluye_lo_por_liquidar(con, ajustes):
    r = portal.guardar(con, TEXTO, "2026-09-30T14:45", mercado.instrumentos(con), confirmar=True)
    assert r["confirmado"] and not r["errores"]
    c = servicios.cartera_actual(con, ajustes)
    assert c["fuente"] == "portal" and c["efectivo"] == 229_883.38 and c["por_liquidar"] == 153_608.34
    assert c["captura"]["por_liquidar"] == 153_608.34


def test_duplicado_y_hora_anterior_se_rechazan(con):
    ins = mercado.instrumentos(con)
    assert portal.guardar(con, TEXTO, "2026-09-30T14:45", ins, confirmar=True)["confirmado"]
    dup = portal.guardar(con, TEXTO, "2026-09-30T14:45", ins, confirmar=True)
    assert not dup["confirmado"] and any("ya estaba registrada" in e for e in dup["errores"])
    previa = portal.guardar(con, TEXTO, "2026-09-30T14:45", ins, confirmar=False)
    assert any("ya está guardada" in a for a in previa["advertencias"])
    viejo = portal.guardar(con, TEXTO.replace("16\t", "17\t"), "2026-09-30T09:00", ins, confirmar=True)
    assert any("anterior a la última" in e for e in viejo["errores"])


def test_errores_claros_si_no_cuadra_o_hay_emisoras_desconocidas(con):
    ins = mercado.instrumentos(con)
    mal = TEXTO.replace("Movimientos por liquidar\t$153,608.34\n", "")
    r = portal.guardar(con, mal, "2026-09-30T14:45", ins, confirmar=True)
    assert not r["confirmado"] and any("no cuadran" in e for e in r["errores"])
    r2 = portal.guardar(con, TEXTO + "ZZZZ9\tX\t10\t1\t1\t10\n", "2026-09-30T14:45", ins, confirmar=True)
    assert not r2["confirmado"] and any("sin reconocer" in e for e in r2["errores"])


TABLA_PORTAL = ("Fav\tInformación\tEmisora\tTítulos\tValor al Costo\tCosto\tPrecio Actual\tPlusvalía / Minusvalía\t% de variación\n"
                "\tVer Detalle\tALPEK A\t5,430\t$14.72\t$79,938.34\t$14.88\t$860.056\t1.07%\n"
                "\tVer Detalle\tCAT *\t1\t$14,727.06\t$14,727.06\t$14,660.00\t-$67.064\t-0.45%\n"
                "Valuación total\t$94,512.40\nInversiones\t$95,458.80\nPoder de compra\t$-946.40\nMovimientos por liquidar\t$0.00\n")


def test_tabla_real_del_portal_valor_al_costo_es_el_costo_unitario(con):
    r = portal.interpretar(TABLA_PORTAL, mercado.instrumentos(con))
    alpek = next(p for p in r["posiciones"] if p["instrumento_id"] == "BMV:ALPEK")
    assert alpek["titulos"] == 5430 and alpek["costo_promedio"] == 14.72 and alpek["precio"] == 14.88
    assert alpek["valor"] == round(5430 * 14.88, 2)            # valor de mercado = títulos × precio actual


def test_posiciones_que_no_suman_las_inversiones_del_portal_no_se_guardan(con):
    """Un título o precio mal leído (p. ej. por OCR) no debe guardarse aunque el total se haya calculado de las filas."""
    mal = TEXTO.replace("ALPEK\tA\t20,000\t14.90\t14.78\t295,600.00", "ALPEK\tA\t3\t14.90\t14.78\t44.34")
    r = portal.guardar(con, mal, "2026-09-30T14:45", mercado.instrumentos(con), confirmar=True)
    assert not r["confirmado"] and any("«Inversiones»" in e for e in r["errores"])
