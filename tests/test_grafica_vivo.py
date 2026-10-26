"""Gráfica de TradingView incrustable en Velas: intervalo validado y enmarcable solo por el mismo origen."""
from fastapi.testclient import TestClient

from terminal import app as modulo


def test_grafica_intervalo_y_enmarcado():
    with TestClient(modulo.app, base_url="http://127.0.0.1:8765") as c:
        r = c.get("/grafica/SIC:MU?intervalo=1")
        assert r.status_code == 200
        assert '"interval": "1"' in r.text and 'target="_top"' in r.text
        assert r.headers["x-frame-options"] == "SAMEORIGIN"
        assert "frame-ancestors 'self'" in r.headers["content-security-policy"]
        assert c.get("/grafica/SIC:MU?intervalo=7").status_code == 422
        assert c.get("/grafica/SIC:MU").status_code == 200  # diario por omisión
        assert c.get("/api/flujo/velas?simbolo=SIC:MU&intervalo=1Day&dias=5").json()["grafica"] is True


def test_widgets_tradingview():
    with TestClient(modulo.app, base_url="http://127.0.0.1:8765") as c:
        for tipo in ("cinta", "resumen", "mapa", "calendario", "filtro", "noticias"):
            r = c.get(f"/widget/{tipo}")
            assert r.status_code == 200 and "embed-widget-" in r.text, tipo
            assert r.headers["x-frame-options"] == "SAMEORIGIN"
        for tipo in ("info", "panorama", "perfil", "finanzas", "noticias-emisora", "tecnico"):
            assert c.get(f"/widget/{tipo}?simbolo=SIC:MU").status_code == 200, tipo
            assert c.get(f"/widget/{tipo}").status_code == 404, tipo  # sin símbolo
        assert '"dataSource": "SPX500"' in c.get("/widget/mapa?mapa=SPX500").text
        assert c.get("/widget/mapa?mapa=OTRO").status_code == 422
        assert c.get("/widget/filtro?filtro=japan").status_code == 422
        assert c.get("/widget/desconocido").status_code == 422
