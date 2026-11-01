"""El mensaje de las alertas del indicador Pine debe ser aceptado por el receptor oficial del webhook."""
import re
from datetime import UTC, datetime
from pathlib import Path

from terminal import webhook_tv

PINE = Path(__file__).resolve().parent.parent / "tradingview" / "actinver_cruce_nivel.pine"


def _mensajes() -> list[str]:
    return re.findall(r"'(\{.*?\})'\)", PINE.read_text(encoding="utf-8"))


def test_mensajes_pine_los_acepta_el_receptor(con):
    mensajes = _mensajes()
    assert len(mensajes) == 2
    rx = webhook_tv.TradingViewAlertReceiver(con, {"TRADINGVIEW_WEBHOOK_SECRETO": "s3creto"})  # pragma: allowlist secret
    hora = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    for i, m in enumerate(mensajes):
        # TradingView sustituye los marcadores; el usuario reemplaza <SECRETO> al crear la alerta
        cuerpo = (m.replace("<SECRETO>", "s3creto").replace("{{exchange}}", "BMV").replace("{{ticker}}", "AMX")
                  .replace("{{close}}", f"17.{25 + i}").replace("{{timenow}}", hora))
        r = rx.recibir(cuerpo.encode())
        assert r["duplicado"] is False and r["instrumento_id"] == "BMV:AMX"


def test_pine_no_contiene_secretos():
    assert "<SECRETO>" in PINE.read_text(encoding="utf-8")
