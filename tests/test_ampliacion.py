"""Ampliación integral: controles que DEBEN fallar ante datos mal etiquetados, escenarios de estrés, reglas versionadas,
órdenes pendientes, bitácora, clasificación de instrumentos y verificación cruzada de backtest."""
import sqlite3
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from terminal import alertas, clasificacion, cotizaciones as cz, escenarios, migraciones, registro, reto
from terminal.alertas import Condicion
from terminal.investigacion import backtest, datos, kronos_candidato

from conftest import sembrar_precios


def _ins(con):
    return {r["id"]: dict(r) for r in con.execute("SELECT * FROM instrumentos")}


# --- Controles que fallan deliberadamente -------------------------------------------------------------------------
def test_noticia_futura_no_puede_entrar_al_pasado(con):
    # Una noticia marcada como «disponible» antes de publicarse viola la temporalidad: la base la rechaza.
    with pytest.raises(sqlite3.IntegrityError, match="temporalidad"):
        con.execute("INSERT INTO noticias (id, titulo, publicado, fuente, obtenido_en, event_time, available_at) "
                    "VALUES ('n1','t','2026-09-22T10:00:00+00:00','rss','2026-09-22T11:00:00+00:00',"
                    "'2026-09-22T10:00:00+00:00','2026-09-21T10:00:00+00:00')")
    # Y una noticia conocida DESPUÉS de T no entra a las variables de un ejemplo en T.
    sembrar_precios(con, ["SIC:AAPL"], sesiones=120)
    migraciones.completar_tiempos(con)
    precios = datos.precios_hasta(con, False)
    fecha_t = precios["fecha"].iloc[100]
    disp_t = precios["available_at"].iloc[100]
    con.execute("INSERT INTO noticias (id, instrumento_id, titulo, publicado, fuente, impacto, obtenido_en) VALUES "
                "('n2','SIC:AAPL','x',?, 'rss','alto', ?)", ((disp_t + pd.Timedelta(hours=2)).isoformat(),
                                                           (disp_t + pd.Timedelta(hours=3)).isoformat()))
    migraciones.completar_tiempos(con)
    panel = datos.construir_panel(precios, 1, datos.noticias_hasta(con))
    fila = panel[panel["fecha"] == fecha_t]
    assert float(fila["noticias_5d"].iloc[0]) == 0.0      # se conoció después: no cuenta en t
    siguiente = panel[panel["fecha"] > fecha_t].iloc[0]
    assert siguiente["noticias_5d"] == 1.0                 # sí cuenta en cuanto estuvo disponible


def test_precio_estadounidense_no_puede_ser_serie_sic(con):
    q = cz.Cotizacion("x", "AAPL", "SIC:AAPL", "SIC:AAPL", "SIC", "BMV", 230.0, "USD",
                      "2026-09-22T15:00:00Z", "2026-09-22T15:00:02Z", None, "REAL_TIME")
    with pytest.raises(sqlite3.IntegrityError, match="MXN"):
        cz.registrar(con, q)


def test_dato_eod_no_puede_etiquetarse_tiempo_real(con):
    q = cz.Cotizacion("x", "AMX B", "BMV:AMX", "BMV:AMX", "local", "BMV", 17.0, "MXN",
                      "2026-09-21T20:00:00Z", "2026-09-22T15:00:00Z", None, "REAL_TIME")
    with pytest.raises(sqlite3.IntegrityError, match="REAL_TIME"):
        cz.registrar(con, q)
    assert cz.clasificar_latencia("2026-09-21T20:00:00Z", "2026-09-22T15:00:00Z", es_cierre=True) == "EOD"


# --- Clasificación: CFD y cripto nunca valúan el Reto ---------------------------------------------------------------
@pytest.mark.parametrize("simbolo,tipo", [("AAPL.US/USD CFD", "cfd"), ("DUKASCOPY:AAPLUSUSD", "cfd"), ("BTC/USDT", "cripto"),
                                          ("ETH/USDT:USDT", "cripto"), ("BINANCE:BTCUSDT", "cripto"), ("BMV:AMX", "valor"),
                                          ("NASDAQ:AAPL", "valor"), ("WALMEX *", "valor")])
def test_clasificacion_de_series(simbolo, tipo):
    assert clasificacion.clasificar_serie(simbolo) == tipo


def test_cfd_y_cripto_rechazados_en_normalizacion(con):
    ins = _ins(con)
    for s in ("BTC/USDT", "DUKASCOPY:AAPLUSUSD", "AAPL CFD"):
        with pytest.raises(clasificacion.InstrumentoNoElegible):
            cz.normalizar_simbolo(s, ins)


# --- Escenarios de estrés ----------------------------------------------------------------------------------------
def test_estres_de_volatilidad_y_spread():
    r = np.random.default_rng(0).normal(0.0005, 0.01, 500)
    e = escenarios.estres_volatilidad(r, 2.0)
    assert e["var_estres"] > e["var_base"] and abs(e["vol_estres"] / e["vol_base"] - 2) < 1e-9
    s = escenarios.estres_spread(1_000_000, 0.004)
    assert s["costo_base"] == 1160.0 and s["costo_spread"] == 2000.0 and s["multiplo_vs_base"] > 2


def _stop(iid):
    return Condicion("stop_loss", iid, True, "critica", titulo=f"Stop {iid}", accion="REVISAR")


def test_precio_retrasado_suspension_y_falta_sic_inhiben_direccionales(con):
    # Precio retrasado (obsoleto), emisora suspendida (sin cotización) y SIC sin serie en MXN: todos «sin precio».
    provs = cz.construir(con, False, entorno={})
    ins = _ins(con)
    viejo = (datetime.now(UTC) - timedelta(days=10)).date().isoformat()
    con.execute("INSERT INTO precios (instrumento_id, fecha, cierre, moneda, proveedor, tipo_dato, obtenido_en) VALUES "
                "('BMV:AMX', ?, 17.0, 'MXN', 'archivo', 'cierre', ?)", (viejo, datetime.now(UTC).isoformat()))
    migraciones.completar_tiempos(con)
    sin_precio = {i for i in ("BMV:AMX", "BMV:GFNORTE", "SIC:AAPL")
                  if cz.precio_confiable(con, provs, ins[i])["estado"] != "confiable"}
    assert sin_precio == {"BMV:AMX", "BMV:GFNORTE", "SIC:AAPL"}
    conds = alertas.inhibir_direccionales([_stop("BMV:AMX"), _stop("SIC:AAPL")], sin_precio, set())
    assert not any(c.activa for c in conds if c.regla == "stop_loss")
    datos_alerta = [c for c in conds if c.regla == "datos_inciertos"]
    assert datos_alerta and datos_alerta[0].activa and "sin precio confiable" in datos_alerta[0].motivo


def test_noticias_contradictorias_inhiben(con):
    ahora = datetime.now(UTC)
    for k, s in enumerate((2.0, -2.0)):
        con.execute("INSERT INTO noticias (id, instrumento_id, titulo, publicado, fuente, impacto, sentimiento, obtenido_en) "
                    "VALUES (?, 'SIC:KO', 't', ?, 'rss', 'alto', ?, ?)",
                    (f"c{k}", (ahora - timedelta(hours=2)).isoformat(), s, (ahora - timedelta(hours=1)).isoformat()))
    dudosas = alertas.contradictorias(con, {"SIC:KO"}, ahora)
    assert dudosas == {"SIC:KO"}
    conds = alertas.inhibir_direccionales([_stop("SIC:KO")], set(), dudosas)
    assert not conds[0].activa and "noticias contradictorias" in conds[-1].motivo


def test_ficha_de_revision_sin_boton_de_operar():
    f = alertas.ficha_revision({"regla": "stop_loss", "titulo": "REVISAR: x", "motivo": "cayó", "fuente": "archivo",
                                "ts": "2026-10-06T15:00:00+00:00", "accion": "REVISAR la posición",
                                "datos": {"calculo": "a/b-1", "incertidumbre": "baja"}, "simulacion": [{"id": "BMV:AMX", "monto": -100000}]})
    assert {"que_ocurrio", "cuando", "datos_que_lo_sustentan", "falta_confirmar", "costos", "riesgos", "opciones_para_revisar",
            "impacto_en_portafolio_mxn", "prioridad", "caduca_en"} <= set(f)
    assert f["costos"]["total"] == 116.0
    assert not any("comprar" in o.lower() or "vender" in o.lower() for o in f["opciones_para_revisar"])


# --- Reglas versionadas, órdenes pendientes y bitácora -------------------------------------------------------------
def test_reglas_versionadas_y_aviso_de_discrepancia(con, tmp_path, monkeypatch):
    e1 = registro.estado_reglas(con)
    assert e1["version"] == 1 and not e1["discrepancia"]
    nuevo = tmp_path / "reto.yaml"
    nuevo.write_text((registro.CONFIG_DIR / "reto.yaml").read_text(encoding="utf-8").replace("comision_pct: 0.0010",
                                                                                            "comision_pct: 0.0015"), encoding="utf-8")
    monkeypatch.setattr(registro, "CONFIG_DIR", tmp_path)
    e2 = registro.registrar_version_reglas(con)
    assert e2["version"] == 2 and e2["discrepancia"] and "cambiaron" in e2["aviso"]
    assert len(e2["historial"]) == 2                    # la versión anterior se conserva
    registro.marcar_reglas_revisadas(con, 2)
    assert not registro.estado_reglas(con)["discrepancia"]


def test_orden_pendiente_no_cambia_tenencia(con):
    from terminal import cartera
    antes = cartera.calcular(cartera.listar(con), {})
    oid = registro.registrar_orden_pendiente(con, "BMV:AMX", "compra", "limitada", 1000, 17.5)
    assert cartera.calcular(cartera.listar(con), {}) == antes      # la orden pendiente no toca posiciones ni efectivo
    registro.cerrar_orden(con, oid, "cancelada")
    assert registro.ordenes(con) == []
    with pytest.raises(ValueError):
        registro.registrar_orden_pendiente(con, "BMV:AMX", "corto", "mercado", 1)


def test_bitacora_exige_decision_humana(con):
    with pytest.raises(ValueError):
        registro.registrar_decision(con, "tesis", "   ")
    i = registro.registrar_decision(con, "tesis", "Decido esperar a confirmar en el portal", "BMV:AMX",
                                    tesis="Momento positivo", fuentes=["https://www.bmv.com.mx"])
    b = registro.bitacora(con)[0]
    assert b["id"] == i and b["version_reglas"] == 1 and b["fuentes"] == ["https://www.bmv.com.mx"]


def test_correspondencia_distingue_sic_origen_y_local(con):
    f = {r["instrumento_id"]: dict(r) for r in con.execute("SELECT * FROM correspondencia_simbolos")}
    assert f["SIC:AAPL"]["mic"] == "XMEX" and f["SIC:AAPL"]["mercado"] == "SIC" and f["SIC:AAPL"]["moneda"] == "MXN"
    assert f["SIC:AAPL"]["simbolo_origen"] == "AAPL" and f["SIC:AAPL"]["moneda_origen"] == "USD"
    assert f["BMV:AMX"]["mercado"] == "local" and f["BMV:AMX"]["simbolo_origen"] is None
    assert "pendiente" in f["BMV:AMX"]["elegible"]         # sin catálogo del simulador importado


# --- Reglas del Reto: límites ---------------------------------------------------------------------------------------
def test_fechas_del_reto_y_zona_horaria():
    c = reto.config()
    assert c["zona_horaria"] == "America/Mexico_City" and c["capital"] == 1_000_000
    mx = reto.MX
    assert reto.etapa(datetime(2026, 9, 28, 0, 0, tzinfo=mx)) == "practica"
    assert reto.etapa(datetime(2026, 10, 2, 23, 59, tzinfo=mx)) == "practica"
    assert reto.etapa(datetime(2026, 10, 3, 12, 0, tzinfo=mx)) == "previa_competencia"
    assert reto.etapa(datetime(2026, 10, 5, 0, 0, tzinfo=mx)) == "competencia"
    assert reto.etapa(datetime(2026, 11, 13, 15, 0, tzinfo=mx)) == "competencia"
    assert reto.etapa(datetime(2026, 11, 13, 15, 1, tzinfo=mx)) == "concluido"
    assert reto.etapa_de_fecha("2026-10-02") == "practica" and reto.etapa_de_fecha("2026-10-05") == "competencia"
    assert reto.etapa_de_fecha("2026-10-03") is None


# --- Verificación cruzada de backtest y candidato Kronos ------------------------------------------------------------
@pytest.mark.skipif(not backtest.backtrader_disponible(), reason="backtrader no disponible")
def test_backtrader_coincide_con_calculo_independiente():
    rng = np.random.default_rng(7)
    idx = pd.bdate_range("2025-01-01", periods=90)
    p = pd.DataFrame({k: 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.02, 90))) for k in "ABCD"}, index=idx)
    r = backtest.comparar(p, cada=10)
    assert r["coinciden"] and r["titulos_iguales"]
    assert r["referencia"]["costos"] > 0 and r["referencia"]["efectivo"] >= 0     # títulos enteros y efectivo remanente


def test_kronos_reporta_pendientes_y_no_filtra_futuro():
    e = kronos_candidato.estado()
    assert e["identidad"].startswith("shiyu-coder/Kronos")
    if not e["disponible"]:
        assert any("torch" in x for x in e["pendiente"])

    class Falso:  # predictor de prueba: devuelve el último cierre del contexto que recibió
        vistos = []

        def predict(self, df, x_timestamp, y_timestamp, pred_len, **k):
            Falso.vistos.append(x_timestamp.iloc[-1])
            return pd.DataFrame({"close": [df["close"].iloc[-1]] * pred_len})
    s = pd.Series(np.linspace(100, 200, 100), index=pd.bdate_range("2025-01-01", periods=100))
    fechas = list(s.index[50:55])
    out = kronos_candidato.pronosticos_rodantes(s, fechas, 5, Falso())
    assert len(out) == 5 and all(abs(v) < 1e-12 for v in out)
    assert all(v <= t for v, t in zip(Falso.vistos, fechas, strict=True))    # el contexto nunca pasa de t
