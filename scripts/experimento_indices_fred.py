"""Experimento fuera de muestra con datos REALES y públicos: índices diarios de FRED (SP500, NASDAQCOM, DJIA).

Por qué: la base del usuario aún no tiene precios BMV (sin licencia ni claves) y la demo es sintética. Estos índices no
son instrumentos del Reto; sirven para comprobar el pipeline completo (available_at, embargo, purga, walk-forward,
referencias, costos) con series reales. Los datos se guardan en una base temporal ignorada por Git (_renders/) y solo se
publican métricas agregadas (docs/evidencia/experimento_indices_fred.json). Fuente: https://fred.stlouisfed.org
(series con derechos de S&P Dow Jones Indices / Nasdaq: uso de consulta, sin redistribución de datos).

Uso: uv run python scripts/experimento_indices_fred.py
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("TERMINAL_DATA_DIR", str(RAIZ / "_renders" / "experimento"))

from terminal import db, migraciones  # noqa: E402
from terminal.investigacion import backtest, evaluacion  # noqa: E402

SERIES = {"SP500": "S&P 500", "NASDAQCOM": "Nasdaq Composite", "DJIA": "Dow Jones Industrial Average"}


class Disp:  # disponibilidad: FRED publica el cierre del índice al día hábil siguiente (conservador: 24 h)
    def get(self, k, d=None):
        return {"fred": 24} if k == "disponibilidad" else d


def descargar(serie: str) -> list[tuple[str, float]]:
    r = httpx.get("https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": serie, "cosd": "2016-01-01"}, timeout=60)
    r.raise_for_status()
    out = []
    for f in csv.reader(io.StringIO(r.text)):
        if len(f) == 2 and f[0][:1].isdigit():
            try:
                out.append((f[0], float(f[1])))
            except ValueError:
                continue  # «.» = sin dato (festivo)
    return out


def main() -> None:
    ruta = RAIZ / "_renders" / "experimento_fred.db"
    ruta.parent.mkdir(exist_ok=True)
    ruta.unlink(missing_ok=True)
    con = db.conectar(ruta)
    db.inicializar(con)
    ahora = datetime.now(UTC).isoformat(timespec="seconds")
    n = {}
    for s, nombre in SERIES.items():
        filas = descargar(s)
        n[s] = {"observaciones": len(filas), "desde": filas[0][0], "hasta": filas[-1][0]}
        con.execute("INSERT OR REPLACE INTO instrumentos (id, clave, nombre, clase, estado, moneda_referencia, mercado_operable, "
                    "bolsa_referencia) VALUES (?,?,?,?,?,?,?,?)", (f"REF:{s}", s, nombre, "indice", "activo", "USD", "REFERENCIA", "FRED"))
        con.executemany("INSERT OR REPLACE INTO precios (instrumento_id, fecha, cierre, cierre_ajustado, volumen, moneda, proveedor, "
                        "tipo_dato, hora_cotizacion, obtenido_en) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        [(f"REF:{s}", f, v, v, None, "USD", "fred", "cierre", None, ahora) for f, v in filas])
    con.commit()
    migraciones.completar_tiempos(con, Disp())
    res = {"fuente": "FRED (St. Louis Fed)", "series": n, "ejecutado": ahora, "horizontes": {}}
    for H in (1, 5):
        r = evaluacion.investigar(con, False, H, config={"top_k": 1})
        res["horizontes"][H] = {k: r.get(k) for k in ("estado", "mensaje", "cortes", "n_ejemplos", "purgados", "variante_elegida",
                                                      "alfa_por_variante", "validacion_mse", "prueba", "estrategias_referencia",
                                                      "veredicto", "conclusion", "variables_eliminadas_final",
                                                      "diebold_mariano_vs_referencias", "error_menor_sin_significancia",
                                                      "correlacion_activos_entrenamiento", "huella_config", "huella_datos")}
    import pandas as pd
    precios = pd.read_sql_query("SELECT fecha, instrumento_id, cierre FROM precios", con).pivot(
        index="fecha", columns="instrumento_id", values="cierre").dropna()
    precios = precios.iloc[-500:]  # último tramo: suficiente para verificar la contabilidad
    precios = precios / precios.iloc[0] * 100  # base 100 (índices sin unidad negociable)
    res["verificacion_backtest"] = backtest.comparar(precios, cada=5)
    con.close()
    salida = RAIZ / "docs" / "evidencia" / "experimento_indices_fred.json"
    salida.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    for H, r in res["horizontes"].items():
        print(f"\nH={H} {r.get('veredicto')} · {r.get('cortes')}")
        for m in r.get("prueba") or []:
            print(f"  {m['modelo']:30} MAE {m['mae']:.5f} MSE {m['mse']:.7f} dir {m['acierto_direccion']} "
                  f"cob80 {m['cobertura_intervalo_80']:.3f} neto {m['resultado_neto']:+.4f} dd {m['caida_maxima']:+.4f}")
        for e in r.get("estrategias_referencia") or []:
            print(f"  {e['modelo']:30} neto {e['resultado_neto']:+.4f} dd {e['caida_maxima']:+.4f}")
    v = res["verificacion_backtest"]
    print("\nbacktrader vs independiente:", v.get("coinciden"), v.get("diferencia_relativa"))


if __name__ == "__main__":
    main()
