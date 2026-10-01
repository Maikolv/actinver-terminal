"""Sincronización con el monitor en la nube: firma compatible con el Worker, carga mínima sin secretos, validación por
el propio validador del Worker, cartera no conciliada y estado comprensible en la terminal."""
import json
import shutil
import subprocess
from pathlib import Path

import httpx
import pytest

from terminal import nube

RAIZ = Path(__file__).resolve().parents[1]
VECTOR = json.loads((RAIZ / "cloud-alerts" / "test" / "vector_firma.json").read_text(encoding="utf-8"))
PROHIBIDAS = ("secret", "token", "password", "contrasena", "api_key", "costo_promedio", "telegram", "sqlite")


def test_firma_identica_a_la_del_worker():
    v = VECTOR
    assert nube.firmar(v["secreto"], v["ts"], v["nonce"], v["metodo"], v["ruta"], v["cuerpo"].encode("utf-8")) == v["firma"]


def test_carga_minima_sin_secretos_y_registro_local_no_conciliado(con, ajustes, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:NO-DEBE-VIAJAR")
    c = nube.construir_carga(con, ajustes, plan=False)
    texto = json.dumps(c, ensure_ascii=False).lower()
    assert not any(p in texto for p in PROHIBIDAS) and "no-debe-viajar" not in texto
    assert set(c) == {"version", "secuencia", "generado_en", "cartera", "umbrales", "plan", "calendario", "fx", "splits"}
    assert c["cartera"]["fuente"] == "local" and c["cartera"]["hora_conciliacion"] is None  # sin captura del portal
    assert {s["mercado"] for s in c["calendario"]} == {"XMEX", "XNYS"}
    assert len(json.dumps(c).encode()) < nube.MAX_BYTES
    assert nube.construir_carga(con, ajustes, plan=False, prueba=True)["prueba"] is True


@pytest.mark.skipif(not shutil.which("node"), reason="Node.js no disponible")
def test_la_carga_de_la_terminal_pasa_el_validador_del_worker(con, ajustes, tmp_path):
    c = nube.construir_carga(con, ajustes)
    archivo = tmp_path / "carga.json"
    archivo.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    js = ("import('./src/validacion.js').then(m=>{const v=m.validar(JSON.parse(require('fs').readFileSync(process.argv[1],'utf8')));"
          "console.log(JSON.stringify(v.ok?{ok:true}:{ok:false,error:v.error}))})")
    r = subprocess.run(["node", "-e", js, str(archivo)], cwd=RAIZ / "cloud-alerts", capture_output=True, text=True, timeout=60)
    assert json.loads(r.stdout.strip().splitlines()[-1]) == {"ok": True}, r.stdout + r.stderr


def test_secuencia_siempre_creciente(con, ajustes):
    nube._registrar(con, {"secuencia": 10 ** 15})  # reloj atrasado: igual crece
    assert nube.construir_carga(con, ajustes, plan=False)["secuencia"] == 10 ** 15 + 1


def test_sincronizar_firma_y_registra_sin_exponer_el_secreto(con, ajustes, monkeypatch):
    secreto = "z" * 43
    monkeypatch.setenv("CLOUD_ALERTS_URL", "https://monitor.test")
    monkeypatch.setenv("CLOUD_ALERTS_SECRET", secreto)
    vistos = {}

    def manejar(req: httpx.Request) -> httpx.Response:
        h = req.headers
        vistos["ok"] = h["X-Firma"] == nube.firmar(secreto, h["X-Marca-Tiempo"], h["X-Nonce"], "POST", "/sync", req.content)
        vistos["cuerpo"] = req.content.decode()
        return httpx.Response(200, json={"ok": True, "recibido_en": "2026-10-01T15:00:00Z", "proxima_revision": "2026-10-01T15:15:00Z"})

    r = nube.sincronizar(con, ajustes, cliente=httpx.Client(transport=httpx.MockTransport(manejar)))
    assert r["ok"] and vistos["ok"] and secreto not in vistos["cuerpo"]
    local = json.loads(con.execute("SELECT valor FROM ajustes_usuario WHERE clave='nube'").fetchone()[0])
    assert local["ultimo_estado"] == "ok" and secreto not in json.dumps(local)


def test_sin_configurar_no_envia_nada(con, ajustes, monkeypatch):
    monkeypatch.delenv("CLOUD_ALERTS_URL", raising=False)
    assert nube.sincronizar(con, ajustes) == {"ok": False, "error": "no_configurado"}
    e = nube.estado(con, ajustes)
    assert e["configurado"] is False and "no configurado" in e["mensaje"]


def test_estado_comprensible_con_relevo_y_suspendidas(con, ajustes, monkeypatch):
    monkeypatch.setenv("CLOUD_ALERTS_URL", "https://monitor.test")
    monkeypatch.setenv("CLOUD_ALERTS_SECRET", "z" * 43)
    remoto = {"ok": True, "ultima_sincronizacion": "2026-10-01T15:00:00Z", "proxima_revision": "2026-10-01T15:15:00Z",
              "ultima_ejecucion": {"inicio": "2020-01-01T15:00:00Z", "relevo": "nube"},
              "suspendidas": [{"alerta": "Condiciones del plan", "motivo": "la copia del portal es antigua"}],
              "avisos_recientes": [{"clave": "mov:SIC:MU", "tipo": "movimiento", "estado": "enviado", "creado_en": "x", "enviado_en": "y"}]}
    monkeypatch.setattr(nube, "_en_ventana", lambda ahora=None: True)
    e = nube.estado(con, ajustes, remoto)
    assert e["activo"] is False and "no se ha ejecutado" in e["mensaje"]          # última ejecución muy antigua
    assert e["relevo_texto"].startswith("la nube envía") and e["suspendidas"][0]["motivo"] == "la copia del portal es antigua"
    assert "clave" not in e["avisos_recientes"][0]                                 # sin detalles innecesarios
    assert e["ultima_sincronizacion"] == "01-10-2026 09:00"                        # hora de la Ciudad de México
