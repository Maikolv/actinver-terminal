"""Auditoría 28-oct: el motor guarda inicio y etapas, avisa si no hay ciclo con el mercado abierto y las escrituras
breves reintentan ante «database is locked»."""
import sqlite3
import time
from datetime import UTC, datetime, timedelta

import pytest

from terminal import alertas, db, ingesta, servicios


def _sin_red(monkeypatch):
    monkeypatch.setattr(ingesta, "actualizar_todo", lambda *a, **k: {"nuevos": 0})
    monkeypatch.setattr(servicios, "calcular_propuestas", lambda *a, **k: {})


def test_el_ciclo_guarda_etapas_y_queda_cerrado(con, ajustes, monkeypatch):
    _sin_red(monkeypatch)
    monkeypatch.setattr(alertas, "evaluar", lambda *a, **k: [])
    servicios.ciclo(con, ajustes, forzar=True, notificar=False)
    m = servicios.estado_motor(con)
    nombres = [e["etapa"] for e in m["etapas"]]
    assert nombres[0] == "cartera" and "ingesta" in nombres and nombres[-1] == "alertas"
    assert not m["en_curso"] and m["ultimo_ciclo"] and all("s" in e for e in m["etapas"])


def test_un_ciclo_fallido_no_queda_en_curso(con, ajustes, monkeypatch):
    _sin_red(monkeypatch)
    monkeypatch.setattr(alertas, "evaluar", lambda *a, **k: 1 / 0)
    with pytest.raises(ZeroDivisionError):
        servicios.ciclo(con, ajustes, forzar=True, notificar=False)
    m = servicios.estado_motor(con)
    assert not m["en_curso"] and "ZeroDivisionError" in m["ultimo_error"] and m["etapas"][-1]["etapa"] == "alertas"


def test_aviso_sin_ciclo_con_mercado_abierto(con):
    abierto = datetime(2026, 10, 28, 17, 0, tzinfo=UTC)   # miércoles 13:00 en Nueva York
    servicios._marcar_motor(con, ultimo_ciclo=(abierto - timedelta(hours=3)).isoformat())
    m = servicios.estado_motor(con, abierto)
    assert m["aviso"] == "Motor sin ciclo terminado" and m["sin_ciclo_desde"].startswith("2026-10-28T14:00")
    servicios._marcar_motor(con, en_curso=True, ciclo_inicio=(abierto - timedelta(minutes=5)).isoformat())
    assert "aviso" not in servicios.estado_motor(con, abierto)            # un ciclo recién iniciado ya lo atiende
    servicios._marcar_motor(con, en_curso=False)
    servicios._marcar_motor(con, ultimo_ciclo=(abierto - timedelta(minutes=30)).isoformat())
    assert "aviso" not in servicios.estado_motor(con, abierto)
    cerrado = datetime(2026, 11, 1, 17, 0, tzinfo=UTC)    # domingo
    servicios._marcar_motor(con, ultimo_ciclo=(cerrado - timedelta(days=2)).isoformat())
    assert "aviso" not in servicios.estado_motor(con, cerrado)


class _Ocupada:
    """Conexión que responde «database is locked» las primeras `fallas` veces."""
    def __init__(self, fallas):
        self.fallas, self.ejecutadas = fallas, 0

    def execute(self, *_):
        if self.fallas:
            self.fallas -= 1
            raise sqlite3.OperationalError("database is locked")
        self.ejecutadas += 1

    def commit(self):
        pass

    def rollback(self):
        pass


def test_escribir_reintenta_si_la_base_esta_ocupada():
    c = _Ocupada(2)
    db.escribir(c, "UPDATE x SET y=1", espera_s=0)
    assert c.ejecutadas == 1
    with pytest.raises(sqlite3.OperationalError):
        db.escribir(_Ocupada(5), "UPDATE x SET y=1", intentos=3, espera_s=0)


def test_cola_incluye_portafolios_guardados_despues_de_las_propuestas(con):
    import json
    with db.transaccion(con):
        con.execute("INSERT INTO portafolios_usuario (nombre, especificacion, resultado, creado_en, actualizado_en) "
                    "VALUES ('p', ?, NULL, 'x', 'x')", (json.dumps({"activos": ["SIC:NVDA", "BMV:WALMEX"]}),))
    props = {"acciones_ajuste": {"pesos": [{"id": "BMV:AMX", "peso": 1.0}]}}
    assert servicios.ids_propuestas(props, con) == ["BMV:AMX", "SIC:NVDA", "BMV:WALMEX"]
    assert servicios.ids_propuestas(props) == ["BMV:AMX"]


def test_proveedores_con_antiguedad_del_error_y_sin_uso_reciente(con, ajustes):
    hoy = datetime(2026, 10, 28, 12, tzinfo=UTC)
    with db.transaccion(con):
        con.execute("INSERT INTO ingestas (proveedor, inicio, fin, estado, registros, mensaje) VALUES "
                    "('fred', 'x', '2026-09-24T06:00:00+00:00', 'error', 0, 'HTTP 500')")
    fred = next(p for p in ingesta.estado_proveedores(con, ajustes, hoy) if p["proveedor"] == "fred")
    assert fred["ultimo_error"]["dias"] == 34 and fred["dias_sin_correr"] == 34
    assert fred["sin_uso_reciente"] == fred["configurado"]   # solo se marca si está configurado y no corre


def test_vacuum_mensual_una_vez_y_respeta_la_marca(tmp_path):
    ruta = tmp_path / "t.db"
    c = db.conectar(ruta)
    db.inicializar(c)
    c.close()
    assert db.vacuum_mensual(ruta) and (tmp_path / "respaldos" / ".ultimo_vacuum").exists()
    assert not db.vacuum_mensual(ruta)                                   # antes de 30 días no repite
    assert db.vacuum_mensual(ruta, ahora=time.time() + 31 * 86400)


def test_cola_rota_por_intento_y_no_se_atasca_en_emisoras_sin_datos_nuevos(con):
    from datetime import date
    with db.transaccion(con):
        for iid, f in (("BMV:TERRA", "2026-10-05"), ("BMV:WALMEX", "2026-10-07"), ("BMV:AMX", "2026-10-08")):
            con.execute("INSERT INTO precios (instrumento_id, fecha, cierre, moneda, proveedor, tipo_dato, obtenido_en) "
                        "VALUES (?, ?, 1, 'MXN', 'eodhd', 'cierre', 'x')", (iid, f))
    instrs = [{"id": i} for i in ("BMV:TERRA", "BMV:WALMEX", "BMV:AMX", "BMV:SMARTRC", "BMV:GCC")]
    hoy = date.today()
    # Antes de intentar: el dato más viejo primero; el nunca cargado conserva su reserva
    assert [i["id"] for i in ingesta.orden_cola(con, instrs, reserva_nuevos=1)][:2] == ["BMV:GCC", "BMV:TERRA"]
    ingesta._intento(con, "BMV:TERRA", "eodhd", 0, hoy)       # el proveedor no trajo nada nuevo
    ingesta._intento(con, "BMV:GCC", "eodhd", 0, hoy)         # nunca cargado y sin datos: pierde la reserva
    orden = [i["id"] for i in ingesta.orden_cola(con, instrs, reserva_nuevos=1)]
    assert orden[:3] == ["BMV:SMARTRC", "BMV:WALMEX", "BMV:AMX"]  # avanzan los que no se han intentado
    assert orden.index("BMV:TERRA") > orden.index("BMV:AMX")
