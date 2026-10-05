"""Plan del día estable: la propuesta de referencia no salta entre carteras por diferencias de ruido en las estimaciones
(5-oct-2026: con precios en vivo, +0.9 % vs +1.3 % de escenario central cambiaba toda la cartera del plan)."""
import json
from datetime import date

from terminal import resumen, servicios, vigencia


def _prop(ajustes, perfil, clave, central, punt):
    return {"clave": clave, "nombre": clave, "estado": "calculada", "perfil": perfil, "huella_calculo": servicios.huella_calculo(ajustes),
            "datos_hasta": vigencia.ultima_sesion_cerrada("XNYS").isoformat(), "puntuacion": {"total": punt},
            "escenarios": {"central_p50": central}, "pesos": []}


def _guardar(con, p) -> int:
    cur = con.execute("INSERT INTO propuestas (tipo, resultado, creado_en, parametros) VALUES (?, ?, ?, '{}')",
                      (p["clave"], json.dumps(p), "2026-10-05T13:00:00+00:00"))
    con.commit()
    return cur.lastrowid


def _out(con, ajustes, perfil, filas):
    out = {}
    for clave, central, punt in filas:
        p = _prop(ajustes, perfil, clave, central, punt)
        out[clave] = {**p, "id_registro": _guardar(con, p)}
    return out


def test_plan_fijo_en_la_sesion_y_con_margen_entre_sesiones(con, ajustes, monkeypatch):
    perfil = {"criterio_plan": "plusvalia"}
    sesion = {"d": date(2026, 10, 5)}
    monkeypatch.setattr(resumen, "sesion_objetivo", lambda ahora: sesion["d"])
    # 7:02: «rendimiento» tiene el mayor escenario central ⇒ se fija
    out = _out(con, ajustes, perfil, [("acciones_rendimiento", 0.036, 66), ("acciones_puntuacion", 0.013, 89)])
    assert servicios._fijar_referencia(con, ajustes, perfil, out) == "acciones_rendimiento"
    # 7:31: con precios en vivo «puntuación» queda arriba por ruido ⇒ el plan del día NO cambia (misma versión)
    out = _out(con, ajustes, perfil, [("acciones_rendimiento", 0.009, 66), ("acciones_puntuacion", 0.013, 89)])
    assert servicios._fijar_referencia(con, ajustes, perfil, out) == "acciones_rendimiento"
    assert out["acciones_rendimiento"]["escenarios"]["central_p50"] == 0.036       # la versión fijada al inicio
    assert resumen.propuesta_referencia(out)["clave"] == "acciones_rendimiento"
    # Sesión siguiente: una mejora < 2 puntos no cambia la propuesta; ≥ 2 puntos sí
    sesion["d"] = date(2026, 10, 6)
    out = _out(con, ajustes, perfil, [("acciones_rendimiento", 0.010, 66), ("acciones_puntuacion", 0.025, 89)])
    assert servicios._fijar_referencia(con, ajustes, perfil, out) == "acciones_rendimiento"
    sesion["d"] = date(2026, 10, 7)
    out = _out(con, ajustes, perfil, [("acciones_rendimiento", 0.010, 66), ("acciones_puntuacion", 0.035, 89)])
    assert servicios._fijar_referencia(con, ajustes, perfil, out) == "acciones_puntuacion"


def test_cambiar_el_criterio_del_perfil_vuelve_a_elegir(con, ajustes, monkeypatch):
    monkeypatch.setattr(resumen, "sesion_objetivo", lambda ahora: date(2026, 10, 5))
    plus = {"criterio_plan": "plusvalia"}
    out = _out(con, ajustes, plus, [("acciones_rendimiento", 0.036, 66), ("acciones_puntuacion", 0.013, 89)])
    assert servicios._fijar_referencia(con, ajustes, plus, out) == "acciones_rendimiento"
    punt = {"criterio_plan": "puntuacion"}
    out = _out(con, ajustes, punt, [("acciones_rendimiento", 0.036, 66), ("acciones_puntuacion", 0.013, 89)])
    assert servicios._fijar_referencia(con, ajustes, punt, out) == "acciones_puntuacion"


def test_si_la_fijada_deja_de_ser_valida_se_elige_otra(con, ajustes, monkeypatch):
    monkeypatch.setattr(resumen, "sesion_objetivo", lambda ahora: date(2026, 10, 5))
    perfil = {"criterio_plan": "plusvalia"}
    out = _out(con, ajustes, perfil, [("acciones_rendimiento", 0.036, 66), ("acciones_puntuacion", 0.013, 89)])
    servicios._fijar_referencia(con, ajustes, perfil, out)
    con.execute("UPDATE propuestas SET resultado = json_set(resultado, '$.estado', 'suspendida') WHERE tipo='acciones_rendimiento'")
    out = _out(con, ajustes, perfil, [("acciones_puntuacion", 0.013, 89)])
    assert servicios._fijar_referencia(con, ajustes, perfil, out) == "acciones_puntuacion"


def test_misma_sesion_si_la_version_fijada_caduca_se_conserva_la_misma_propuesta(con, ajustes, monkeypatch):
    """Un recálculo (p. ej. cambio de código) invalida la versión fijada: se usa la versión nueva de la MISMA propuesta."""
    monkeypatch.setattr(resumen, "sesion_objetivo", lambda ahora: date(2026, 10, 5))
    perfil = {"criterio_plan": "plusvalia"}
    out = _out(con, ajustes, perfil, [("acciones_rendimiento", 0.036, 66), ("acciones_puntuacion", 0.013, 89)])
    servicios._fijar_referencia(con, ajustes, perfil, out)
    con.execute("UPDATE propuestas SET resultado = json_set(resultado, '$.huella_calculo', 'vieja') WHERE tipo='acciones_rendimiento'")
    out = _out(con, ajustes, perfil, [("acciones_rendimiento", 0.009, 66), ("acciones_puntuacion", 0.013, 89)])
    assert servicios._fijar_referencia(con, ajustes, perfil, out) == "acciones_rendimiento"
    assert out["acciones_rendimiento"]["escenarios"]["central_p50"] == 0.009


def test_mientras_la_fijada_se_recalcula_no_se_salta_a_otra(con, ajustes, monkeypatch):
    monkeypatch.setattr(resumen, "sesion_objetivo", lambda ahora: date(2026, 10, 5))
    perfil = {"criterio_plan": "plusvalia"}
    out = _out(con, ajustes, perfil, [("acciones_rendimiento", 0.036, 66), ("acciones_puntuacion", 0.013, 89)])
    servicios._fijar_referencia(con, ajustes, perfil, out)
    con.execute("UPDATE propuestas SET resultado = json_set(resultado, '$.huella_calculo', 'vieja')")
    out = _out(con, ajustes, perfil, [("acciones_puntuacion", 0.013, 89)])     # «puntuación» ya se recalculó…
    pendiente = _prop(ajustes, perfil, "acciones_rendimiento", 0.036, 66)
    out["acciones_rendimiento"] = servicios.revalidar({**pendiente, "huella_calculo": "vieja"}, perfil, ajustes)  # …«rendimiento» aún no
    assert servicios._fijar_referencia(con, ajustes, perfil, out) is None
    assert json.loads(con.execute("SELECT valor FROM ajustes_usuario WHERE clave='referencia_plan'").fetchone()[0])["clave"] == "acciones_rendimiento"
