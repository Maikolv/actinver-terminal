"""Experimento Kronos (NeoQuasar/Kronos-mini, shiyu-coder/Kronos) con los mismos cortes, fechas de prueba y referencias
que el experimento de índices reales de FRED (scripts/experimento_indices_fred.py debe ejecutarse antes).

- Sin fuga: para cada fecha t el contexto termina en el cierre de t (conocido en t); se pronostican 5 pasos y se
  toman el 1.º (H=1) y el 5.º (H=5).
- Series de solo cierre: open=high=low=close (insumo degradado para Kronos; se reporta).
- Intervalos calibrados con residuos de las últimas N fechas de validación (conformal por partición).
- Mismo veredicto que el modelo lineal: error menor Y significativo (Diebold-Mariano, p < 0.05) frente a las tres
  referencias Y mejor resultado neto que referencias y estrategias; si no: SIN VENTAJA DEMOSTRADA.

Uso: uv run --group kronos python scripts/experimento_kronos.py [--muestras 5] [--contexto 400] [--validacion 100]
     [--lote 8] [--max-fechas N]

Memoria (6-oct-2026): con todas las series en un solo lote, 5 muestras y contexto 400, el equipo de 5.9 GB se quedó sin
memoria. `--lote` parte cada fecha en lotes pequeños; `--max-fechas` corre solo las primeras N fechas para medir
memoria y tiempo antes del experimento completo. Se reporta el pico de memoria del proceso.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from terminal import db  # noqa: E402
from terminal.investigacion import datos, division, evaluacion, kronos_candidato  # noqa: E402


def pico_mb() -> float:
    """Pico de memoria del proceso (Windows: PeakWorkingSetSize; otros: ru_maxrss)."""
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]
        c = PMC()
        c.cb = ctypes.sizeof(PMC)
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.GetCurrentProcess.restype = wintypes.HANDLE  # en 64 bits el seudo-handle no cabe en un int de 32
        k32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        if not k32.K32GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb):
            return float("nan")
        return c.PeakWorkingSetSize / 2**20
    except Exception:  # noqa: BLE001
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("--muestras", type=int, default=5)
    a.add_argument("--contexto", type=int, default=400)
    a.add_argument("--validacion", type=int, default=100)
    a.add_argument("--lote", type=int, default=8, help="series por llamada a Kronos (memoria acotada)")
    a.add_argument("--max-fechas", type=int, default=0, help="solo las primeras N fechas (medición de recursos)")
    args = a.parse_args()
    ruta = RAIZ / "_renders" / "experimento_fred.db"
    if not ruta.exists():
        sys.exit("Ejecute primero: uv run python scripts/experimento_indices_fred.py")
    import torch
    torch.manual_seed(20261113)
    np.random.seed(20261113)
    predictor = kronos_candidato.cargar("cpu")
    con = db.conectar(ruta)
    precios = datos.precios_hasta(con, False)
    series = {i: g.set_index(pd.to_datetime(g["fecha"]))["cierre"].sort_index() for i, g in precios.groupby("instrumento_id")}
    conjuntos, fechas_necesarias = {}, set()
    for H in (1, 5):
        panel = datos.etiquetados_hasta(datos.construir_panel(precios, H, datos.noticias_hasta(con)), None)
        cortes = division.dividir(panel["fecha"].tolist(), H)
        pru = panel[division.mascara(panel, cortes, "prueba")].copy()
        val = panel[division.mascara(panel, cortes, "validacion")].copy()
        val = val[val["fecha"].isin(sorted(val["fecha"].unique())[-args.validacion:])]
        conjuntos[H] = (pru, val, cortes)
        fechas_necesarias |= set(pru["fecha"]) | set(val["fecha"])
    fechas = sorted(fechas_necesarias)
    total_fechas = len(fechas)
    if args.max_fechas:
        fechas = fechas[:args.max_fechas]
    pred: dict[tuple[str, str], np.ndarray] = {}
    t0 = time.time()
    for k, f in enumerate(fechas):
        ids, dfs, xs, ys, ult = [], [], [], [], []
        for iid, s in series.items():
            hist = s.loc[:pd.Timestamp(f)].iloc[-args.contexto:]
            if len(hist) < args.contexto or hist.index[-1] != pd.Timestamp(f):
                continue
            ids.append(iid)
            v = hist.to_numpy(dtype=float)
            dfs.append(pd.DataFrame({"open": v, "high": v, "low": v, "close": v}))
            xs.append(pd.Series(hist.index))
            ys.append(pd.Series(pd.bdate_range(hist.index[-1] + pd.offsets.BDay(1), periods=5)))
            ult.append(v[-1])
        if not ids:
            continue
        out = []
        for j in range(0, len(dfs), max(args.lote, 1)):  # lotes pequeños: memoria acotada
            out += predictor.predict_batch(dfs[j:j + args.lote], xs[j:j + args.lote], ys[j:j + args.lote], pred_len=5,
                                           T=1.0, top_p=0.9, sample_count=args.muestras, verbose=False)
        for iid, o, u in zip(ids, out, ult, strict=True):
            pred[(iid, f)] = np.log(o["close"].to_numpy(dtype=float) / u)
        if k % 25 == 0 or args.max_fechas:
            print(f"{k + 1}/{len(fechas)} fechas · {time.time() - t0:.0f} s · pico {pico_mb():.0f} MB", flush=True)
    if args.max_fechas:
        seg = time.time() - t0
        print(f"MEDICIÓN: {len(fechas)} fechas en {seg:.0f} s ({seg / max(len(fechas), 1):.1f} s/fecha) · pico {pico_mb():.0f} MB · "
              f"estimado para {total_fechas} fechas: {seg / max(len(fechas), 1) * total_fechas / 60:.0f} min", flush=True)
        return
    res = {"lote": args.lote, "pico_memoria_mb": round(pico_mb()), "modelo": kronos_candidato.MODELO, "tokenizador": kronos_candidato.TOKENIZADOR, "muestras": args.muestras,
           "contexto": args.contexto, "insumo": "solo cierre (open=high=low=close)", "ejecutado": datetime.now(UTC).isoformat(),
           "segundos": round(time.time() - t0), "horizontes": {}}
    costo = 0.00116
    for H, (pru, val, cortes) in conjuntos.items():
        paso = H - 1
        m_p = np.array([(i, f) in pred for i, f in zip(pru["instrumento_id"], pru["fecha"], strict=True)])
        m_v = np.array([(i, f) in pred for i, f in zip(val["instrumento_id"], val["fecha"], strict=True)])
        pru, val = pru[m_p], val[m_v]
        pk = np.array([pred[(i, f)][paso] for i, f in zip(pru["instrumento_id"], pru["fecha"], strict=True)])
        vk = np.array([pred[(i, f)][paso] for i, f in zip(val["instrumento_id"], val["fecha"], strict=True)])
        refs_p, refs_v = evaluacion.referencias(pru, H), evaluacion.referencias(val, H)
        tabla = [evaluacion.metricas(pru, pk, val["y"].to_numpy() - vk, H, 1, costo, "Kronos-mini")]
        for n, pr in refs_p.items():
            tabla.append(evaluacion.metricas(pru, pr, val["y"].to_numpy() - refs_v[n], H, 1, costo, n))
        estr = [{"modelo": "pesos_iguales", **evaluacion.estrategia(pru, np.zeros(len(pru)), H, 1, costo, iguales=True)}]
        dm = {n: evaluacion.diebold_mariano(pru, pk, pr, H) for n, pr in refs_p.items()}
        signif = all(v["p_valor"] is not None and v["p_valor"] < 0.05 for v in dm.values())
        err = tabla[0]["mse"] < min(r["mse"] for r in tabla[1:])
        neto = tabla[0]["resultado_neto"] > max([r["resultado_neto"] for r in tabla[1:]] + [e["resultado_neto"] for e in estr])
        res["horizontes"][H] = {"cortes": cortes.a_dict(), "n_prueba": int(len(pru)), "n_validacion": int(len(val)),
                                "prueba": tabla, "estrategias_referencia": estr, "diebold_mariano": dm,
                                "veredicto": "VENTAJA FUERA DE MUESTRA" if (err and signif and neto) else evaluacion.SIN_VENTAJA}
    con.close()
    salida = RAIZ / "docs" / "evidencia" / "experimento_kronos.json"
    salida.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    for H, r in res["horizontes"].items():
        print(f"\nH={H} {r['veredicto']} (n={r['n_prueba']})")
        for m in r["prueba"]:
            d = m["acierto_direccion"]
            print(f"  {m['modelo']:20} MSE {m['mse']:.7f} MAE {m['mae']:.5f} dir {d if d is None else round(d, 3)} "
                  f"cob80 {m['cobertura_intervalo_80']:.3f} neto {m['resultado_neto']:+.4f} dd {m['caida_maxima']:+.4f}")
        print("  DM:", {k: v["p_valor"] for k, v in r["diebold_mariano"].items()})


if __name__ == "__main__":
    main()
