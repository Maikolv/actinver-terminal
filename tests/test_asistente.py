"""Asistente dentro de la terminal: notas del usuario, búsqueda en la documentación y respaldo local sin LLM."""
import pytest
from fastapi.testclient import TestClient

from terminal import asistente, bot_telegram
from terminal.seguridad import TOKEN_CSRF


@pytest.fixture
def bot(ajustes, monkeypatch):
    b = bot_telegram.Chatbot(ajustes)
    monkeypatch.setattr(b, "motor", lambda: "local")      # sin Claude ni Ollama: lo que ve el usuario hoy
    return b


def test_notas_agregar_listar_borrar(con, ajustes, bot):
    r = asistente.responder(con, ajustes, "/nota Mi horizonte es el 13-nov y no quiero apalancamiento.", bot)
    assert r["motor"] == "notas" and "#1" in r["respuesta"]
    assert "horizonte" in asistente.responder(con, ajustes, "/notas", bot)["respuesta"]
    assert "borrada" in asistente.responder(con, ajustes, "/olvidar 1", bot)["respuesta"]
    assert asistente.notas(con) == []
    with pytest.raises(ValueError):
        asistente.responder(con, ajustes, "/nota   ", bot)
    with pytest.raises(ValueError):
        asistente.responder(con, ajustes, "/olvidar x", bot)
    with pytest.raises(ValueError):
        asistente.agregar_nota(con, "x" * (asistente.MAX_NOTA + 1))


def test_duda_se_responde_con_documentacion_y_notas(con, ajustes, bot):
    asistente.agregar_nota(con, "La palabra clave zafiroquetzal identifica mi estrategia de prueba.")
    r = asistente.responder(con, ajustes, "¿qué es zafiroquetzal?", bot)
    assert r["motor"] == "documentacion" and "nota #" in r["respuesta"] and "no verificada" in r["respuesta"]
    r = asistente.responder(con, ajustes, "¿cómo funciona el preregistro y el holdout del laboratorio?", bot)
    assert r["motor"] == "documentacion" and any("docs/" in f["origen"] for f in r["fuentes"])


def test_comandos_y_ayuda(con, ajustes, bot):
    r = asistente.responder(con, ajustes, "/ayuda", bot)
    assert r["motor"] == "comando" and "/nota" in r["respuesta"]
    with pytest.raises(ValueError):
        asistente.responder(con, ajustes, "   ", bot)


def test_contexto_extra_llega_al_llm(con, ajustes, monkeypatch):
    visto = {}
    b = bot_telegram.Chatbot(ajustes)
    monkeypatch.setattr(b, "motor", lambda: "claude")
    monkeypatch.setattr(bot_telegram, "contexto", lambda con, aj, em: {"base": 1})
    monkeypatch.setattr(b, "_preguntar_claude", lambda p, ctx: visto.update(ctx) or "respuesta del modelo")
    r = asistente.responder(con, ajustes, "¿qué es el VaR?", b)
    assert r["respuesta"] == "respuesta del modelo" and "documentacion_y_notas" in visto and visto["base"] == 1


def test_api_asistente():
    from terminal import app as modulo
    with TestClient(modulo.app, base_url="http://127.0.0.1:8765") as c:
        assert c.post("/api/asistente", json={"texto": "/ayuda"}).status_code == 403          # CSRF
        assert c.post("/api/asistente", json={"texto": ""}, headers={"X-CSRF-Token": TOKEN_CSRF}).status_code == 422
        assert "notas" in c.get("/api/asistente/notas").json()
