"""Ejemplos SINTÉTICOS: perfiles descriptivos sin interpolación ni datos externos."""
import pytest

from terminal.flujo.calculos import area_valor, perfil_tpo, resumen_operaciones


def nivel(precio, volumen):
    return {"desde": precio, "hasta": precio + 1, "volumen": volumen}


def barra(inicio, precios=(10, 14, 10, 12), intervalo="5Min"):
    return dict(zip(("apertura", "maximo", "minimo", "cierre"), precios), inicio=inicio, intervalo=intervalo)


def test_area_conocida_y_empates():
    r = area_valor([nivel(10, 10), nivel(11, 40), nivel(12, 30), nivel(13, 20)], 4)
    assert r["poc"] == 11.5
    assert (r["val"], r["vah"]) == (11, 13)
    assert r["fraccion_observada"] == pytest.approx(.7)
    # Empate de vecinos: ambos; empate de POC: precio menor.
    r = area_valor([nivel(10, 30), nivel(11, 40), nivel(12, 30)])
    assert (r["val"], r["vah"]) == (10, 13)
    assert area_valor([nivel(10, 40), nivel(11, 40)])["poc"] == 10.5


def test_area_sin_datos_y_volumen_invalido():
    assert area_valor([]) is None
    assert area_valor([nivel(10, 100)], 1) is None
    for volumen in (0, -1, float("nan"), float("inf")):
        assert area_valor([nivel(10, volumen), nivel(11, volumen)]) is None
    assert resumen_operaciones([])["area_valor"] is None
    assert resumen_operaciones([{"precio": 10, "tamano": 100}])["area_valor"] is None


def test_resumen_reutiliza_perfil_de_volumen():
    ops = [{"precio": 10, "tamano": 10}, {"precio": 11, "tamano": 40},
           {"precio": 12, "tamano": 30}, {"precio": 14, "tamano": 20}]
    r = resumen_operaciones(ops, cubetas=4)
    assert r["area_valor"]["poc"] == 11.5
    assert r["area_valor"]["volumen_total"] == 100


def test_tpo_30min_observados_sin_rellenar_y_sin_duplicar():
    bs = [barra("2026-10-16T13:30:00Z"), barra("2026-10-16T13:35:00Z"),
          barra("2026-10-16T14:30:00Z", (12, 14, 12, 14))]
    r = perfil_tpo(bs, cubetas=4)
    assert r["zona_horaria"] == "America/New_York"
    s = r["sesiones"][0]
    assert s["inicio"] == "2026-10-16T09:30:00-04:00"
    assert [p["indice"] for p in s["periodos"]] == [0, 2]
    assert [(p["desde"], p["tpo"]) for p in s["perfil"]] == [(10, 1), (12, 2), (13, 2)]
    assert s["perfil"][-1]["periodos"] == [0, 2]


def test_tpo_pocos_datos_diarias_y_cruce_de_periodo():
    assert perfil_tpo([])["sesiones"] == []
    assert perfil_tpo([barra("2026-10-16T13:30:00Z", intervalo="1Day")])["sesiones"] == []
    s = perfil_tpo([barra("2026-10-16T13:30:00Z")])["sesiones"][0]
    assert s["perfil"] is None
    assert perfil_tpo([barra("2026-10-16T13:59:00Z")])["sesiones"] == []
    assert perfil_tpo([barra("2026-10-16T20:00:00Z")])["sesiones"] == []
    assert perfil_tpo([barra("2026-10-16T09:30:00")])["sesiones"] == []


def test_tpo_separa_sesiones_y_cambia_desfase_por_horario_estacional():
    bs = [barra("2026-10-16T13:30:00Z"), barra("2026-10-16T14:00:00Z"),
          barra("2026-11-02T14:30:00Z"), barra("2026-11-02T15:00:00Z")]
    ss = perfil_tpo(bs)["sesiones"]
    assert len(ss) == 2
    assert ss[0]["inicio"].endswith("-04:00")
    assert ss[1]["inicio"].endswith("-05:00")
    assert all(s["barras"] == 2 for s in ss)


def test_tpo_valida_configuracion():
    with pytest.raises(ValueError):
        perfil_tpo([], apertura="16:00", cierre="09:30")
    with pytest.raises(ValueError):
        perfil_tpo([], cubetas=0)


def test_tpo_cripto_incluye_ultima_barra_hasta_medianoche_siguiente():
    bs = [barra("2026-10-16T23:25:00Z"), barra("2026-10-16T23:55:00Z")]
    s = perfil_tpo(bs, zona_horaria="UTC", apertura="00:00", cierre="24:00")["sesiones"][0]
    assert s["fin"] == "2026-10-17T00:00:00+00:00"
    assert s["barras"] == 2 and s["perfil"] is not None
    assert [p["indice"] for p in s["periodos"]] == [46, 47]
