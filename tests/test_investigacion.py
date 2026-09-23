"""Investigación predictiva: sin fuga de información, embargo/purga, filtro de correlación y comparación con referencias."""
import numpy as np
import pandas as pd

from terminal import migraciones
from terminal.investigacion import datos, division, evaluacion, pronosticos
from terminal.investigacion.seleccion import FiltroCorrelacion

from conftest import sembrar_precios

IDS = ["SIC:AAPL", "SIC:MSFT", "SIC:KO", "BMV:AMX", "BMV:GFNORTE", "BMV:FUNO"]


def _preparar(con, sesiones=700):
    fechas = sembrar_precios(con, IDS, sesiones=sesiones)
    migraciones.completar_tiempos(con)
    return fechas


def test_precios_hasta_respeta_available_at(con):
    fechas = _preparar(con, 200)
    T = pd.Timestamp(fechas[150]).tz_localize("UTC") + pd.Timedelta(hours=23)
    p = datos.precios_hasta(con, False, T)
    assert p["available_at"].max() <= T
    assert p["fecha"].max() <= fechas[150].date().isoformat()


def test_sin_fuga_entre_ventanas_modificar_el_futuro_no_cambia_el_pasado(con):
    fechas = _preparar(con, 300)
    T = pd.Timestamp(fechas[250]).tz_localize("UTC") + pd.Timedelta(hours=23)
    antes = datos.etiquetados_hasta(datos.construir_panel(datos.precios_hasta(con, False, T), 5), T)
    con.execute("UPDATE precios SET cierre = cierre * 3 WHERE fecha > ?", (fechas[250].date().isoformat(),))
    despues = datos.etiquetados_hasta(datos.construir_panel(datos.precios_hasta(con, False, T), 5), T)
    pd.testing.assert_frame_equal(antes.reset_index(drop=True), despues.reset_index(drop=True))
    # Ninguna etiqueta usada para entrenar a la hora T se conoció después de T
    assert (antes["disponible_etiqueta"] <= T).all() and (antes["disponible_en"] <= T).all()


def test_division_cronologica_con_embargo_y_purga():
    fechas = [f"2026-01-{d:02d}" for d in range(1, 32)] + [f"2026-02-{d:02d}" for d in range(1, 29)] + \
             [f"2026-03-{d:02d}" for d in range(1, 32)] + [f"2026-04-{d:02d}" for d in range(1, 31)]
    for H in (1, 5):
        c = division.dividir(fechas, H)
        assert c.validacion[0] - c.entrenamiento[1] == H and c.prueba[0] - c.validacion[1] == H
        assert c.entrenamiento[1] <= c.validacion[0] < c.validacion[1] <= c.prueba[0]  # orden cronológico, sin barajar
    # Purga: un ejemplo cuya etiqueta termina en el periodo siguiente (p. ej. por festivos de otro calendario) se elimina
    c = division.dividir(fechas, 5)
    ult_ent = c.fechas[c.entrenamiento[1] - 1]
    panel = pd.DataFrame({"fecha": [ult_ent, ult_ent], "instrumento_id": ["a", "b"],
                          "fecha_fin_etiqueta": [c.fechas[c.entrenamiento[1] + 2], c.fechas[c.validacion[0] + 1]]})
    m = division.mascara(panel, c, "entrenamiento")
    assert m.tolist() == [True, False] and division.purgadas(panel, c, "entrenamiento") == 1


def test_walk_forward_sin_solapamiento(con):
    _preparar(con, 500)
    panel = datos.construir_panel(datos.precios_hasta(con, False), 5)
    fechas = sorted(panel["fecha"].unique())
    pl = division.pliegues_walk_forward(fechas, 5, 4)
    assert len(pl) >= 3
    for p in pl:
        e, v = division.mascaras_pliegue(panel, p)
        assert division.sin_solapamiento(panel, e, v)
        assert panel.loc[e, "fecha"].max() < panel.loc[v, "fecha"].min()


def test_filtro_de_correlacion_se_ajusta_solo_con_entrenamiento():
    rng = np.random.default_rng(1)
    x1 = rng.normal(size=500)
    ent = pd.DataFrame({"a": x1, "b": x1 * 2 + rng.normal(scale=0.01, size=500), "c": rng.normal(size=500)})
    f = FiltroCorrelacion(0.95, ["a", "b", "c"]).fit(ent)
    assert f.columnas_ == ["a", "c"] and f.eliminadas_[0]["variable"] == "b"
    # En validación «b» ya no se parece a «a»: la selección NO cambia (se aprendió en entrenamiento)
    val = pd.DataFrame({"a": rng.normal(size=100), "b": rng.normal(size=100), "c": rng.normal(size=100)})
    assert list(f.transform(val).columns) == ["a", "c"]
    # Y al revés: duplicadas solo en validación no se eliminan
    ent2 = pd.DataFrame({"a": rng.normal(size=500), "b": rng.normal(size=500), "c": rng.normal(size=500)})
    assert FiltroCorrelacion(0.95, ["a", "b", "c"]).fit(ent2).columnas_ == ["a", "b", "c"]
    # Dentro del pipeline, el filtro ve datos ya imputados/escalados con parámetros del entrenamiento
    m = evaluacion.modelo("filtro_correlacion", 1.0, 0.95, 0)
    X = pd.DataFrame(rng.normal(size=(300, len(datos.VARIABLES))), columns=datos.VARIABLES)
    X["r5"] = X["r1"] * 1.0001
    m.fit(X, rng.normal(size=300))
    assert "r5" not in m.named_steps["filtro"].columnas_


def test_experimento_completo_y_registro(con):
    _preparar(con, 700)
    r = evaluacion.investigar(con, False, 1, config={"alfas": [10.0, 1000.0], "pliegues": 3})
    assert r["estado"] == "ok"
    assert {m["modelo"].split(" ")[0] for m in r["prueba"]} == {"modelo", "sin_cambio", "historico_reciente", "regla_simple"}
    assert r["recomendacion_permitida"] == r["supera_referencias"]
    for m in r["prueba"]:
        assert 0 <= m["cobertura_intervalo_80"] <= 1 and m["rebalanceos"] > 0
    # Mismos datos y cortes con OTRA configuración ⇒ la prueba ya se vio: el resultado queda marcado
    r2 = evaluacion.investigar(con, False, 1, config={"alfas": [1.0], "pliegues": 3})
    assert r2["prueba_ya_vista"] is True
    # Reproducible: misma configuración ⇒ mismas métricas
    r3 = evaluacion.investigar(con, False, 1, config={"alfas": [10.0, 1000.0], "pliegues": 3}, guardar=False)
    assert r3["prueba"][0]["mse"] == r["prueba"][0]["mse"]


def test_pronosticos_se_guardan_aparte_y_no_cambian_las_cotizaciones(con):
    _preparar(con, 500)
    n_precios = con.execute("SELECT COUNT(*) FROM precios").fetchone()[0]
    out = pronosticos.emitir(con, False, 5)
    assert out["emitidos"] == len(IDS)
    assert con.execute("SELECT COUNT(*) FROM precios").fetchone()[0] == n_precios
    fila = con.execute("SELECT * FROM pronosticos LIMIT 1").fetchone()
    assert fila["p10"] <= fila["prediccion"] <= fila["p90"] and fila["resultado"] is None
    assert fila["datos_hasta"] <= fila["emitido_en"]
