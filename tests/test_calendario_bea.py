from datetime import UTC, datetime

from terminal import mesa_datos
from tools.actualizar_calendario_bea import preparar
import json


def test_calendario_bea_deduplica_y_filtra_corte(tmp_path, monkeypatch):
    ahora = datetime(2026, 11, 3, tzinfo=UTC)
    corte = preparar({
        "metadatos": "BEA",
        "Comercio": {"release_dates": [
            "2026-11-02T13:30:00+00:00",
            "2026-11-04T07:30:00-06:00",
            "2026-11-04T13:30:00+00:00",
            "2026-11-10T00:00:00+00:00",
        ]},
    }, ahora)
    (tmp_path / "calendario_bea.json").write_text(json.dumps(corte), encoding="utf-8")
    monkeypatch.setattr(mesa_datos, "CONFIG_DIR", tmp_path)
    assert mesa_datos.calendario_bea(ahora)["eventos"] == [
        {"fecha": "2026-11-04T13:30:00+00:00", "titulo": "Comercio"},
    ]
    assert not mesa_datos.calendario_bea(datetime(2026, 11, 2, tzinfo=UTC))["eventos"]


def test_actualizacion_bea_conserva_corte_si_servidor_pide_pausa(tmp_path, monkeypatch):
    from urllib.error import HTTPError

    import pytest

    from tools import actualizar_calendario_bea as bea

    destino = tmp_path / "calendario_bea.json"
    destino.write_bytes(b"corte anterior")
    llamadas = []

    def responder(url, timeout):
        llamadas.append(url)
        raise HTTPError(url, 503, "Servicio no disponible", {"Retry-After": "120"}, None)

    monkeypatch.setattr(bea, "urlopen", responder)
    with pytest.raises(HTTPError, match="503"):
        bea.actualizar(destino)
    assert llamadas == [bea.FUENTE]
    assert destino.read_bytes() == b"corte anterior"
    assert list(tmp_path.iterdir()) == [destino]
