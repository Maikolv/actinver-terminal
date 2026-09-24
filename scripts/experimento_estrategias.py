"""Banco de estrategias simples sobre índices REALES de FRED (requiere haber corrido experimento_indices_fred.py).

Guarda métricas agregadas en docs/evidencia/experimento_estrategias.json y registra el experimento en la base temporal.
Uso: uv run python scripts/experimento_estrategias.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from terminal.investigacion import estrategias  # noqa: E402


def main() -> None:
    ruta = RAIZ / "_renders" / "experimento_fred.db"
    if not ruta.exists():
        sys.exit("Ejecute primero: uv run python scripts/experimento_indices_fred.py")
    con = sqlite3.connect(ruta)
    df = pd.read_sql_query("SELECT fecha, instrumento_id, cierre FROM precios", con)
    precios = df.pivot(index="fecha", columns="instrumento_id", values="cierre").dropna()
    precios.index = pd.to_datetime(precios.index)
    res = estrategias.experimento(precios, k=2)
    res["fuente"] = "FRED: S&P 500, Nasdaq Composite, Dow Jones (índices; no son instrumentos del Reto)"
    res["ejecutado"] = datetime.now(UTC).isoformat(timespec="seconds")
    con.execute("CREATE TABLE IF NOT EXISTS experimentos_estrategias (ts TEXT, resultado TEXT)")
    con.execute("INSERT INTO experimentos_estrategias VALUES (?,?)", (res["ejecutado"], json.dumps(res, default=str)))
    con.commit()
    (RAIZ / "docs" / "evidencia" / "experimento_estrategias.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"Entrenamiento {res['entrenamiento']} · prueba {res['prueba']} · elegidos {res['parametros_elegidos_con_entrenamiento']}")
    print(f"{'estrategia':20} {'neto':>8} {'neto 0.5%':>9} {'sharpe':>7} {'caída':>7} {'rot':>6} {'años>PI':>8} {'p':>6}  veredicto")
    for r in res["resumen"]:
        p = r["p_bootstrap_vs_pesos_iguales"]
        print(f"{r['estrategia']:20} {r['neto_prueba']:+8.2%} {r['neto_desliz_0.5%']:+9.2%} {r['sharpe']:7.2f} "
              f"{r['caida_maxima']:+7.2%} {r['rotacion']:6.1f} {r['subperiodos_ganados_vs_pesos_iguales']:>8} "
              f"{'—' if p is None else f'{p:.3f}':>6}  {r['veredicto']}")
    print(f"\n{len(res['configuraciones_registradas'])} configuraciones registradas · veredicto global: {res['veredicto_global']}")


if __name__ == "__main__":
    main()
