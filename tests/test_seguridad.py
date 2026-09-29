"""Controles HTTP locales, ausencia de rutas de órdenes y de secretos en el repositorio."""
import re
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from terminal.app import app
from terminal.seguridad import TOKEN_CSRF

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app, base_url="http://127.0.0.1:8765") as c:
        yield c


def test_cabeceras_de_seguridad(cliente):
    r = cliente.get("/")
    assert r.status_code == 200
    csp = r.headers["content-security-policy"]
    assert "script-src 'self'" in csp and "unsafe-inline" not in csp and "frame-ancestors 'none'" in csp
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["referrer-policy"] == "no-referrer"
    assert "server" not in {k.lower() for k in r.headers} or "uvicorn" not in r.headers.get("server", "")


def test_host_no_local_rechazado(cliente):
    assert cliente.get("/salud", headers={"host": "atacante.example"}).status_code == 400


def test_mutaciones_exigen_csrf_y_origen_local(cliente):
    assert cliente.put("/api/perfil", json={}).status_code == 403
    r = cliente.put("/api/perfil", json={}, headers={"X-CSRF-Token": TOKEN_CSRF, "Origin": "https://evil.example"})
    assert r.status_code == 403
    r = cliente.put("/api/perfil", json={"riesgo": "x"}, headers={"X-CSRF-Token": TOKEN_CSRF})
    assert r.status_code == 422 and r.json()["errores"]


def test_documentacion_y_rutas_de_prueba_desactivadas(cliente):
    for ruta in ("/docs", "/redoc", "/openapi.json"):
        assert cliente.get(ruta).status_code == 404


def test_404_personalizada(cliente):
    r = cliente.get("/no-existe")
    assert r.status_code == 404 and "Esta página no existe" in r.text
    assert cliente.get("/api/no-existe").json()["error"] == "Ruta no encontrada"


def test_no_existen_rutas_de_ordenes_reales():
    rutas = " ".join(getattr(r, "path", "") for r in app.routes).lower()
    assert not re.search(r"orden|order|broker|trade|ejecutar", rutas)


def test_subida_restringida(cliente):
    h = {"X-CSRF-Token": TOKEN_CSRF}
    r = cliente.post("/api/importar", headers=h, data={"tipo": "transacciones"}, files={"archivo": ("x.exe", b"MZ", "application/octet-stream")})
    assert r.status_code == 422
    grande = b"fecha,tipo\n" + b"2024-01-01,aportacion\n" * 70000
    r = cliente.post("/api/importar", headers=h, data={"tipo": "transacciones"}, files={"archivo": ("g.csv", grande, "text/csv")})
    assert r.status_code in (413, 422)


def test_xss_en_nota_se_guarda_como_texto(cliente):
    h = {"X-CSRF-Token": TOKEN_CSRF}
    carga = "<img src=x onerror=alert(1)>"
    r = cliente.post("/api/transacciones", headers=h, json={"fecha": "2024-01-02", "tipo": "aportacion", "monto": 1, "nota": carga})
    assert r.status_code == 200
    js = (RAIZ / "web" / "static" / "app.js").read_text(encoding="utf-8")
    assert "innerHTML" not in js and "insertAdjacentHTML" not in js and "eval(" not in js


def test_inyeccion_sql_en_parametros(cliente):
    r = cliente.get("/api/auditoria", params={"limite": "1; DROP TABLE transacciones"})
    assert r.status_code == 422
    assert cliente.get("/api/transacciones").status_code == 200


PATRONES = re.compile(r"(AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{40,}|xox[bp]-\d{8,}|"
                      r"AIza[0-9A-Za-z_-]{35}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(api_?key|token|secret)\s*[=:]\s*['\"][A-Za-z0-9]{16,})", re.I)


def test_sin_secretos_en_archivos_versionados():
    r = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=RAIZ,
                       capture_output=True, text=True, check=True)
    hallazgos = []
    for f in r.stdout.splitlines():
        p = RAIZ / f
        if p.suffix in (".png", ".db", ".lock") or not p.is_file():
            continue
        if PATRONES.search(p.read_text(encoding="utf-8", errors="ignore")):
            hallazgos.append(f)
    assert hallazgos == []


def test_env_ignorado_por_git():
    r = subprocess.run(["git", "check-ignore", ".env", "data/terminal.db", "_privado/x", "config/local.toml"], cwd=RAIZ,
                       capture_output=True, text=True)
    assert len(r.stdout.split()) == 4


def test_cambio_de_modo_separa_bases_y_actualiza(cliente, monkeypatch):
    from terminal import config, db, ingesta
    llamadas = []
    monkeypatch.setattr(ingesta, "actualizar_todo", lambda con, aj, prio=None, cliente=None: llamadas.append(aj.modo) or {"ok": 1})
    h = {"X-CSRF-Token": TOKEN_CSRF}
    assert cliente.post("/api/modo", headers=h, json={"modo": "otro"}).status_code == 422
    assert cliente.post("/api/modo", json={"modo": "real"}).status_code == 403  # exige CSRF
    r = cliente.post("/api/modo", headers=h, json={"modo": "demo"})
    assert r.status_code == 200 and cliente.get("/api/estado").json()["modo"] == "demo"
    assert db.ruta_db().parent.name == "demo"
    r = cliente.post("/api/modo", headers=h, json={"modo": "real"})
    assert r.status_code == 200 and r.json()["actualizacion"] == {"ok": 1} and llamadas[-1] == "real"
    assert db.ruta_db().parent == config.DATA_DIR


HOST_TS = "mi-pc.tail1234.ts.net"


def test_acceso_remoto_solo_por_tailscale_serve(monkeypatch):
    monkeypatch.setenv("TERMINAL_HOSTS_REMOTOS", HOST_TS)
    monkeypatch.delenv("TERMINAL_USUARIOS_REMOTOS", raising=False)
    with TestClient(app, base_url=f"https://{HOST_TS}") as c:
        assert c.get("/", headers={"Tailscale-User-Login": "yo@ejemplo.com"}).status_code == 200      # red privada
        assert c.get("/").status_code == 400                        # sin identidad (p. ej. Funnel / público)
        ok = c.post("/api/notificaciones/prueba", json={}, headers={"Tailscale-User-Login": "yo@ejemplo.com",
                    "X-CSRF-Token": "x", "Origin": "https://otro.example"})
        assert ok.status_code == 403                                 # origen ajeno
    with TestClient(app, base_url="https://otra-pc.tail1234.ts.net") as c:
        assert c.get("/", headers={"Tailscale-User-Login": "yo@ejemplo.com"}).status_code == 400   # host no autorizado
    monkeypatch.setenv("TERMINAL_USUARIOS_REMOTOS", "yo@ejemplo.com")
    with TestClient(app, base_url=f"https://{HOST_TS}") as c:
        assert c.get("/", headers={"Tailscale-User-Login": "intruso@ejemplo.com"}).status_code == 400
        assert c.get("/", headers={"Tailscale-User-Login": "yo@ejemplo.com"}).status_code == 200


def test_un_nombre_publico_nunca_se_acepta_aunque_se_configure(monkeypatch):
    monkeypatch.setenv("TERMINAL_HOSTS_REMOTOS", "algo.trycloudflare.com")
    with TestClient(app, base_url="https://algo.trycloudflare.com") as c:
        assert c.get("/", headers={"Tailscale-User-Login": "yo@ejemplo.com"}).status_code == 400
