"""Servicios con costo: nada de pago se usa sin aprobación; alerta mientras falte la decisión."""
import pytest
from fastapi.testclient import TestClient

from terminal import app as modulo
from terminal import bot_telegram, costos


def _claude(monkeypatch, presente: bool):
    monkeypatch.setattr(bot_telegram, "credencial_claude", lambda: presente)


def test_sin_credencial_no_hay_nada_que_aprobar(con, monkeypatch):
    _claude(monkeypatch, False)
    e = {s["id"]: s for s in costos.estado(con)["servicios"]}
    assert e["claude_api"]["estado"].startswith("bloqueado") and not e["claude_api"]["requiere_decision"]
    assert e["cloudflare"]["estado"] == "gratis"
    assert not any(c.activa for c in costos.reglas_costos(con))


def test_credencial_detectada_queda_pendiente_alerta_y_no_se_usa(con, monkeypatch):
    monkeypatch.setattr(costos, "_solo_gratuitos", lambda: False)  # Flujo histórico simulado, sin consultas externas.
    _claude(monkeypatch, True)
    e = {s["id"]: s for s in costos.estado(con)["servicios"]}
    assert e["claude_api"]["requiere_decision"] and "pendiente" in e["claude_api"]["estado"]
    [alerta] = [c for c in costos.reglas_costos(con) if c.activa]
    assert alerta.severidad == "alta" and "aprobación" in alerta.titulo and alerta.clave == "claude_api"


def test_aprobar_y_desistir(con, monkeypatch):
    monkeypatch.setattr(costos, "_solo_gratuitos", lambda: False)  # Flujo histórico simulado, sin consultas externas.
    _claude(monkeypatch, True)
    costos.decidir(con, "claude_api", "aprobado")
    assert costos.decision(con, "claude_api") == "aprobado"
    assert not any(c.activa for c in costos.reglas_costos(con))
    costos.decidir(con, "claude_api", "desistido")
    assert "desistido" in {s["id"]: s for s in costos.estado(con)["servicios"]}["claude_api"]["estado"]
    for servicio, valor in [("claude_api", "tal vez"), ("tiingo", "aprobado"), ("x", "aprobado")]:
        with pytest.raises(ValueError):
            costos.decidir(con, servicio, valor)


def test_api_costos_exige_csrf():
    with TestClient(modulo.app, base_url="http://127.0.0.1:8765") as c:
        respuesta = c.get("/api/costos")
        assert respuesta.status_code == 200
        [finviz] = [s for s in respuesta.json()["servicios"] if s["id"] == "finviz_elite"]
        assert finviz["estado"].startswith("bloqueado")
        assert not finviz["puede_decidir"] and not finviz["requiere_decision"]
        assert c.post("/api/costos", json={"servicio": "claude_api", "decision": "aprobado"}).status_code == 403
