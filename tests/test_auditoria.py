"""Auditoría 29-sep: cola de precios por prioridad, titulares sin emisoras, bloqueo por captura incompleta, plan de
propuesta nocturno, cambio de etapa y panel «¿En qué puedo confiar hoy?»."""
from datetime import UTC, datetime

import pytest

from terminal import alertas, boleta, estado_info, fuentes_web, ingesta, mercado, notificador, portal, reto, servicios

from conftest import sembrar_precios

TEXTO = ("Emisora\tSerie\tTítulos\tCosto promedio\tPrecio actual\tValor de mercado\n"
         "AMX\tB\t5,000\t17.20\t17.55\t87,750.00\n"
         "Efectivo disponible:\t$912,250.00\nValor del portafolio:\t$1,000,000.00\n")


def test_cola_de_precios_por_prioridad(con):
    sembrar_precios(con, ["BMV:WALMEX", "BMV:AMX"], sesiones=30)
    con.execute("DELETE FROM precios WHERE instrumento_id='BMV:AMX' AND fecha > (SELECT MIN(fecha) FROM precios)")
    instrs = [{"id": i} for i in ("BMV:ZZZ", "BMV:WALMEX", "BMV:AMX", "SIC:AAPL", "BMV:GMEXICO")]
    orden = [i["id"] for i in ingesta.orden_cola(con, instrs, ["SIC:AAPL"], ["BMV:GMEXICO"])]
    # cartera → propuesta → con datos (el más atrasado primero) → nunca cargados
    assert orden == ["SIC:AAPL", "BMV:GMEXICO", "BMV:AMX", "BMV:WALMEX", "BMV:ZZZ"]


def test_titulares_sin_emisoras_no_se_reportan_como_ok(con):
    r = fuentes_web.actualizar_noticias(con, {"seekingalpha_rss": {}}, [])
    assert r["estado"] == "sin_emisoras"


def test_captura_con_posicion_sin_precio_bloquea_propuestas_y_boletas(con, ajustes):
    portal.guardar(con, TEXTO, "2026-09-28T14:05", mercado.instrumentos(con), confirmar=True)
    con.execute("UPDATE posiciones_portal SET precio=NULL, valor=NULL")  # sin precio de la terminal ni del portal
    con.commit()
    actual = servicios.cartera_actual(con, ajustes)
    assert actual["fuente"] == "portal" and not actual["completa"]
    assert "sin precio" in servicios.bloqueo_cartera(actual)
    ids = [r[0] for r in con.execute("SELECT id FROM instrumentos WHERE id LIKE 'BMV:%' AND id <> 'BMV:AMX' AND clase='accion' AND estado='activo' LIMIT 8")]
    sembrar_precios(con, ids, sesiones=300)
    servicios.calcular_propuestas(con, ajustes)
    props = servicios.propuestas_guardadas(con, ajustes, servicios.perfil_actual(con, ajustes))
    assert all(any("Bloqueada" in a for a in p["avisos"]) for p in props.values() if p)
    with pytest.raises(ValueError, match="No se generan boletas"):
        boleta.generar(con, ajustes, "acciones_ajuste")


def test_plan_de_propuesta_de_noche_queda_para_el_plan_del_dia(con, monkeypatch):
    enviados = []
    monkeypatch.setattr(notificador, "enviar", lambda *a, **k: enviados.append(a) or {})
    prop = {"x": {"clave": "x", "nombre": "X", "estado": "calculada", "avisos": [], "puntuacion": {"total": 80},
                  "cambios": {"filas": [{"id": "BMV:AMX", "accion": "comprar", "monto_mxn": 1000.0, "delta_pp": 3.0}]}}}
    noche = datetime(2026, 9, 29, 9, 50, tzinfo=UTC)                                     # 03:50 CDMX
    cfg = {"enfriamiento_horas": 6, "silenciar_fuera_de_horario": True}
    alertas.procesar(con, alertas.reglas_plan_propuesta({"fuente": "local"}, prop), cfg, noche)
    assert enviados == []
    assert con.execute("SELECT notificada FROM alertas").fetchone()[0] == "incluida_en_plan_del_dia"


def test_cambio_de_etapa_deja_de_usar_la_captura_de_practica(con, ajustes, monkeypatch):
    portal.guardar(con, TEXTO, "2026-09-28T14:05", mercado.instrumentos(con), confirmar=True)
    assert servicios.captura_vigente(con) is not None
    monkeypatch.setattr(reto, "etapa_operativa", lambda *a, **k: "competencia")
    assert servicios.captura_vigente(con) is None
    assert servicios.cartera_actual(con, ajustes)["fuente"] == "local"


def test_estado_informacion_no_presenta_el_saldo_local_como_confirmado(con, ajustes):
    e = estado_info.calcular(con, ajustes)
    cuenta = next(i for i in e["items"] if i["tema"] == "Cuenta del Reto")
    assert cuenta["nivel"] == "falta" and "LOCAL" in cuenta["texto"]
    precios = next(i for i in e["items"] if i["tema"] == "Precios")
    assert "no tiempo real" in precios["texto"]
    portal.guardar(con, TEXTO, "2026-09-28T14:05", mercado.instrumentos(con), confirmar=True)
    cuenta = next(i for i in estado_info.calcular(con, ajustes)["items"] if i["tema"] == "Cuenta del Reto")
    assert cuenta["nivel"] == "confirmado"
