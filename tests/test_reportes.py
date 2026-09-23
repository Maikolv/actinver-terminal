"""Los reportes nunca inventan datos: base vacía y propuestas suspendidas se dicen tal cual."""
import json
from datetime import UTC, datetime

import pytest

from terminal import db, reportes

AHORA = datetime(2026, 10, 13, 14, 0, tzinfo=UTC)


@pytest.mark.parametrize("tipo", ["preapertura", "cierre", "semanal"])
def test_reporte_con_base_vacia_no_inventa_nada(con, ajustes, tipo):
    txt = reportes.generar(con, ajustes, tipo, AHORA)
    assert reportes.TIPOS[tipo] in txt
    assert "Sin operaciones registradas" in txt
    assert "sin calcular" in txt
    assert "no envía órdenes" in txt
    assert "Ninguna." in txt  # sin alertas


def test_propuesta_suspendida_no_emite_recomendacion(con, ajustes):
    p = {"clave": "acciones_ajuste", "tipo": "acciones", "lente": "ajuste", "nombre": "Solo acciones · Ajuste",
         "estado": "suspendida", "motivos": ["sin precios vigentes"], "calculado_en": db.ahora()}
    with db.transaccion(con):
        con.execute("INSERT INTO propuestas (tipo, creado_en, parametros, resultado) VALUES (?,?,?,?)",
                    ("acciones_ajuste", p["calculado_en"], "{}", json.dumps(p)))
    txt = reportes.generar(con, ajustes, "cierre", AHORA)
    assert "SUSPENDIDA — sin precios vigentes. No se emite recomendación." in txt


def test_tipo_desconocido_falla(con, ajustes):
    with pytest.raises(ValueError):
        reportes.generar(con, ajustes, "diario", AHORA)


def test_guardar_escribe_un_archivo_por_dia_y_tipo(tmp_path):
    ruta = reportes.guardar("# hola\n", "cierre", AHORA, carpeta=tmp_path)
    assert ruta.name.endswith("_cierre.md") and ruta.read_text(encoding="utf-8") == "# hola\n"
    assert reportes.guardar("# otra vez\n", "cierre", AHORA, carpeta=tmp_path) == ruta  # sobrescribe el del día


def test_reportes_demo_van_a_la_carpeta_demo(monkeypatch):
    from terminal import config
    monkeypatch.setattr(config, "_MODO", {"activo": "demo"})
    assert reportes.data_dir() == config.DATA_DIR / "demo"
