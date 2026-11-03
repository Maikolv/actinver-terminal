"""Mesa comparte la lista local y exige las mismas defensas que la terminal principal."""
from fastapi.testclient import TestClient

from terminal import app as modulo
from terminal.seguridad import TOKEN_CSRF


def test_mesa_entrega_control_csrf_sin_cache():
    with TestClient(modulo.app, base_url="http://127.0.0.1:8765") as c:
        r = c.get("/static/mesa.html")
        assert r.status_code == 200
        assert r.headers["cache-control"] == "no-store"
        assert f'content="{TOKEN_CSRF}"' in r.text
        assert "__CSRF__" not in r.text
        assert 'id="mesa-agregar-seguimiento"' in r.text


def test_seguimiento_desde_mesa_rechaza_sin_csrf_y_origen_externo(con):
    modulo.app.dependency_overrides[modulo.con_db] = lambda: con
    try:
        with TestClient(modulo.app, base_url="http://127.0.0.1:8765") as c:
            assert c.post("/api/seguimiento", json={"instrumento_id": "SIC:NVDA"}).status_code == 403
            assert c.post("/api/seguimiento", json={"instrumento_id": "SIC:NVDA"}, headers={
                "X-CSRF-Token": TOKEN_CSRF, "Origin": "https://externo.test"}).status_code == 403
        assert con.execute("SELECT COUNT(*) FROM seguimiento").fetchone()[0] == 0
    finally:
        modulo.app.dependency_overrides.pop(modulo.con_db, None)


def test_agregar_desde_mesa_reutiliza_lista_y_no_borra_nota(con):
    modulo.app.dependency_overrides[modulo.con_db] = lambda: con
    try:
        with TestClient(modulo.app, base_url="http://127.0.0.1:8765") as c:
            headers = {"X-CSRF-Token": TOKEN_CSRF, "Origin": "http://127.0.0.1:8765"}
            assert c.post("/api/seguimiento", json={"instrumento_id": "SIC:NVDA", "nota": "Conservar"}, headers=headers).status_code == 200
            assert c.post("/api/seguimiento", json={"instrumento_id": "SIC:NVDA"}, headers=headers).status_code == 200
        filas = con.execute("SELECT instrumento_id, nota FROM seguimiento").fetchall()
        assert [(f["instrumento_id"], f["nota"]) for f in filas] == [("SIC:NVDA", "Conservar")]
    finally:
        modulo.app.dependency_overrides.pop(modulo.con_db, None)
