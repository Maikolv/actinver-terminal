"""Historia externa del usuario (Excel «Benchmarks_time_series»): importar, verificar y validar con historia larga.

  uv run --with openpyxl python scripts/historia_externa.py importar <archivo.xlsx>
  uv run python scripts/historia_externa.py verificar      → docs/evidencia/historia_externa.json
  uv run python scripts/historia_externa.py validar        → data/referencias/historia_externa/validacion.json

`validar` repite la validación V1 (walk-forward 168/21, panel dinámico, costos del Reto, referencia 1/N) con la
historia local EXTENDIDA hacia atrás por las columnas verificadas, desde el 2-ene-2004. Regla preregistrada en
docs/historia-externa.md antes de correr: las propuestas solo cambian si una lente supera a 1/N con el IC 90 % del
exceso entero por encima de cero.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from terminal import db, servicios  # noqa: E402
from terminal import historia_externa as hx  # noqa: E402
from terminal import optimizador as op  # noqa: E402
from terminal import validacion_extendida as ve  # noqa: E402
from terminal.config import RAIZ, cargar_ajustes  # noqa: E402

INICIO = "2004-01-02"
COMBOS = [("acciones", "rendimiento"), ("acciones", "ajuste"), ("mixta", "rendimiento"), ("mixta", "ajuste")]
EVIDENCIA = RAIZ / "docs" / "evidencia" / "historia_externa.json"


def _sin_series(inf: dict) -> dict:
    """Informe apto para el repositorio: solo estadísticas, ningún precio."""
    return {"procedencia": json.loads((hx.carpeta() / "procedencia.json").read_text(encoding="utf-8")), **inf}


def verificar(con) -> dict:
    inf = hx.verificar(con)
    EVIDENCIA.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCIA.write_text(json.dumps(_sin_series(inf), ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(inf["resumen"])
    return inf


def subperiodos(est: pd.Series, ig: pd.Series) -> list[dict]:
    out = []
    for inicio in range(2004, 2027, 5):
        a, b = est.loc[str(inicio):str(inicio + 4)], ig.loc[str(inicio):str(inicio + 4)]
        if len(a) > 21:
            out.append({"periodo": f"{inicio}–{min(inicio + 4, 2026)}", "sesiones": len(a),
                        "estrategia": ve.metricas(a)["rend_anual"], "iguales": ve.metricas(b)["rend_anual"]})
    return out


def validar(con, ajustes) -> dict:
    inf = json.loads(EVIDENCIA.read_text(encoding="utf-8")) if EVIDENCIA.exists() else hx.verificar(con)
    perfil = op.perfil_efectivo(servicios.perfil_actual(con, ajustes))
    banda = float(ajustes["optimizacion"]["banda_rebalanceo_pp"]) / 100
    df = hx.cargar()
    res = {"preregistro": "docs/historia-externa.md", "inicio": INICIO, "filas": []}
    for tipo, lente in COMBOS:
        t0 = time.time()
        el_l, _, precios = op.universo(con, ajustes, perfil, tipo, None)
        el = {e["id"]: e for e in el_l}
        ids = list(el)
        R = precios[ids].ffill(limit=3).pct_change(fill_method=None)
        R, ext = hx.extender(con, ajustes, R, inf, df)
        R = R.loc[INICIO:]
        R = R.loc[R.notna().sum(axis=1) >= ve.MIN_ACTIVOS_PLIEGUE]
        costos = pd.Series({c: op.costo_unitario(el[c], ajustes) for c in ids})

        def ajustar(cols, Xtr, tipo=tipo, lente=lente, el=el):
            m = op._modelo(tipo, perfil, ajustes, [el[c] for c in cols], {}, lente=lente).fit(Xtr)
            o = m.named_steps["optimizacion"]
            return pd.Series(o.weights_, index=list(o.feature_names_in_))
        wf = ve.walk_forward(ajustar, R, costos, banda)
        r = ve.resumen(wf)
        if r is None:
            res["filas"].append({"combo": f"{tipo}_{lente}", "estado": "sin pliegues"})
            continue
        r.update(combo=f"{tipo}_{lente}", instrumentos=len(ids), extendidos=len(ext),
                 subperiodos=subperiodos(wf["estrategia"], wf["iguales"]), segundos=round(time.time() - t0))
        res["filas"].append(r)
        print(f"{tipo}_{lente:<12} ses {r['estrategia']['sesiones']:>5} pl {r['pliegues']:>3} ({r['pliegues_gana_1N']} ganan) "
              f"rend {r['estrategia']['rend_anual']:+.1%} 1/N {r['iguales']['rend_anual']:+.1%} exceso "
              f"{r['exceso_anual']:+.1%} IC [{r['exceso_ic90'][0]:+.1%}, {r['exceso_ic90'][1]:+.1%}] caída "
              f"{r['estrategia']['max_caida']:.0%} (1/N {r['iguales']['max_caida']:.0%}) {r['segundos']} s", flush=True)
    salida = hx.carpeta() / "validacion.json"
    salida.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("guardado en", salida)
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("accion", choices=["importar", "verificar", "validar"])
    ap.add_argument("archivo", nargs="?")
    a = ap.parse_args()
    ajustes = cargar_ajustes()
    con = db.conectar()
    db.inicializar(con, ajustes)
    if a.accion == "importar":
        print(hx.importar(Path(a.archivo)))
        verificar(con)
    elif a.accion == "verificar":
        verificar(con)
    else:
        validar(con, ajustes)


if __name__ == "__main__":
    main()
