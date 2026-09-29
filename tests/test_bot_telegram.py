"""Bot de Telegram: comandos, emisoras mencionadas, respuestas con y sin Claude, tope de consultas."""
from types import SimpleNamespace

from terminal import bot_telegram as bt
from terminal import mercado

from conftest import sembrar_precios


def test_comandos_basicos(con, ajustes):
    cb = bt.Chatbot(ajustes, cliente_claude=None)
    assert "/boletas" in bt.atender(con, ajustes, "/ayuda", cb)
    assert "Registro LOCAL" in bt.atender(con, ajustes, "/cartera", cb) or "Cuenta del Reto" in bt.atender(con, ajustes, "/cartera", cb)
    assert "¿En qué puedo confiar hoy?" in bt.atender(con, ajustes, "/estado", cb)
    assert bt.atender(con, ajustes, "/desconocido", cb) == bt.AYUDA


def test_emisoras_mencionadas(con):
    ins = mercado.instrumentos(con)
    assert "BMV:AMX" in bt.emisoras_en("¿por qué AMX está en el plan?", ins)
    assert bt.emisoras_en("¿qué hay hoy en el plan?", ins) == []


def test_pregunta_sin_llm_responde_con_la_ficha(con, ajustes, monkeypatch):
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    sembrar_precios(con, ["BMV:AMX"], sesiones=30)
    cb = bt.Chatbot(ajustes)
    cb._claude_probado, cb._claude = True, None                      # sin SDK ni credencial
    r = cb.responder(con, "¿cómo va AMX?")
    assert r.startswith("AMX") and "Precio:" in r and "plan del día" in r


class _Claude:
    def __init__(self, texto="Respuesta de prueba", stop="end_turn"):
        self.llamadas = []
        self.texto, self.stop = texto, stop
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **k):
        self.llamadas.append(k)
        return SimpleNamespace(stop_reason=self.stop, content=[SimpleNamespace(type="text", text=self.texto)])


def test_pregunta_con_claude_usa_contexto_de_solo_lectura_y_tope(con, ajustes):
    falso = _Claude()
    cb = bt.Chatbot(ajustes, cliente_claude=falso)
    cb.max_hora = 1
    assert cb.responder(con, "¿qué debo revisar hoy?") == "Respuesta de prueba"
    k = falso.llamadas[0]
    assert k["model"] == "claude-opus-5-5" and k["fallbacks"] == "default" and "<terminal>" in k["messages"][0]["content"]
    assert "Nunca digas que ejecutaste" in k["system"]
    assert "No tengo una respuesta directa" in cb.responder(con, "¿qué debo revisar hoy?")  # tope alcanzado: sin Claude
    assert len(falso.llamadas) == 1


def test_negativa_de_claude(con, ajustes):
    cb = bt.Chatbot(ajustes, cliente_claude=_Claude(stop="refusal"))
    assert "No puedo responder" in cb.responder(con, "pregunta")


def test_sin_credencial_no_se_activa_claude(ajustes, monkeypatch, tmp_path):
    for v in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE", "OLLAMA_URL"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    assert not bt.credencial_claude() and bt.Chatbot(ajustes).motor() == "local"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-prueba")
    assert bt.credencial_claude() and bt.Chatbot(ajustes).motor() == "claude"
