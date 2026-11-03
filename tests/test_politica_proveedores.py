"""Una credencial o aprobación antigua no habilita gasto bajo la política gratuita."""
import pytest

from terminal import bot_telegram as bt, ingesta


@pytest.mark.parametrize("proveedor", ["twelvedata", "barchart"])
def test_clave_y_activacion_local_no_habilitan_proveedor_de_pago(con, ajustes, monkeypatch, proveedor):
    ajustes.datos["proveedores"][proveedor]["activo"] = True
    monkeypatch.setattr(ingesta, "credencial", lambda n: "ficticia" if n == proveedor else None)
    adaptadores = ingesta.construir_adaptadores(con, ajustes)
    assert not adaptadores[proveedor].configurado()
    assert ajustes["proveedores"][proveedor]["activo"] is True  # No altera la configuración recibida.


def test_politica_gratuita_bloquea_incluso_cliente_claude_inyectado(ajustes, monkeypatch):
    class ClienteProhibido:
        def __getattr__(self, nombre):
            pytest.fail("No se debe consultar un cliente de pago bajo la política gratuita")

    monkeypatch.delenv("OLLAMA_URL", raising=False)
    monkeypatch.setattr(bt, "costo_aprobado", lambda n: True)
    assert bt.Chatbot(ajustes, cliente_claude=ClienteProhibido()).motor() == "local"


def test_diagnostico_cli_no_consulta_api_de_pago(ajustes, monkeypatch):
    from terminal import __main__ as cli, config

    monkeypatch.setattr(config, "cargar_ajustes", lambda: ajustes)
    monkeypatch.setattr(bt, "credencial_claude", lambda: pytest.fail("No inspeccionar credenciales ni crear cliente de pago"))
    with pytest.raises(SystemExit, match="solo recursos gratuitos"):
        cli.claude(None)


def test_costos_no_ofrece_aprobar_ni_activa_alerta_de_pago(con, monkeypatch):
    from terminal import costos

    monkeypatch.setattr(bt, "credencial_claude", lambda: True)
    con.execute("INSERT OR REPLACE INTO ajustes_usuario (clave,valor,actualizado_en) VALUES (?,?,?)",
                ("costo_claude_api", "aprobado", "2026-11-02T00:00:00+00:00"))
    estado = {x["id"]: x for x in costos.estado(con)["servicios"]}
    for identificador in ["claude_api", "twelvedata_bmv", "barchart"]:
        assert estado[identificador]["estado"].startswith("bloqueado")
        assert not estado[identificador]["puede_decidir"]
        assert not estado[identificador]["requiere_decision"]
    assert estado["claude_api"]["decision"] == "aprobado"  # Historial conservado, sin efecto sobre el bloqueo.
    assert not any(x.activa for x in costos.reglas_costos(con))
    with pytest.raises(ValueError, match="solo recursos gratuitos"):
        costos.decidir(con, "claude_api", "aprobado")
