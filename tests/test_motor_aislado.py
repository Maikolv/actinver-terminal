"""El ciclo en proceso aparte respeta el bloqueo, el interruptor y el contrato de `servicios.ciclo_seguro`."""
import subprocess
import types

from terminal import motor_aislado, servicios


class _Aj(dict):
    es_demo = False


def test_proceso_aparte_con_bloqueo_y_codigo_de_salida(monkeypatch):
    aj = _Aj(app={})
    visto = {}

    def falso(orden, **kw):
        visto.update(orden=orden, bloqueado=servicios.bloqueo.locked(), kw=kw)
        return types.SimpleNamespace(returncode=visto.get("codigo", 0))
    monkeypatch.setattr(subprocess, "run", falso)
    assert motor_aislado.ciclo_seguro(aj, forzar=True, en_vivo=True) == {"proceso": "aparte"}
    assert visto["bloqueado"] and not servicios.bloqueo.locked()         # la API no calcula a la vez; se libera al terminar
    assert visto["orden"][1:] == ["-m", "terminal.motor_aislado", "--forzar", "--en-vivo"]
    visto["codigo"] = 3
    assert motor_aislado.ciclo_seguro(aj) is None                         # hijo ocupado o con falla
    with servicios.bloqueo:
        assert motor_aislado.ciclo_seguro(aj) is None                     # cálculo en curso en el servidor: no lanza otro


def test_demo_o_interruptor_apagado_corren_dentro_del_proceso(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debe lanzar proceso")))
    monkeypatch.setattr(servicios, "ciclo_seguro", lambda aj, f=False, v=False: {"dentro": True})
    assert motor_aislado.ciclo_seguro(_Aj(app={"motor_proceso_aparte": False})) == {"dentro": True}
    demo = _Aj(app={})
    demo.es_demo = True
    assert motor_aislado.ciclo_seguro(demo) == {"dentro": True}
