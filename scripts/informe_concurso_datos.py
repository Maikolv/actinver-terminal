"""Datos y gráficas del informe del Concurso Finanzas IA, leídos SOLO del archivo del Reto (capturas reales del portal).

Uso: uv run --with matplotlib python scripts/informe_concurso_datos.py [ruta_archivo.db]
Salida: data/medios/informe/datos.json y gráficas PNG. Nada se estima ni se inventa: lo que no está en el archivo
queda marcado como PENDIENTE en el informe (scripts/informe_concurso.cjs).
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVO = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "data" / "archivo" / "reto-actinver-2026-20261117.db"
SALIDA = RAIZ / "data" / "medios" / "informe"
CAPITAL = 1_000_000.0  # actipesos del Reto (config/reto.yaml, reglamento §1)
GRIS, ROJO, TEXTO = "#4a505a", "#b3261e", "#15171c"
SECTOR_BMV = {"BMV:GMEXICO": "Minería y metales (Grupo México)", "BMV:ALPEK": "Químicos y plásticos (Alpek)",
              "BMV:FEMSA": "Bebidas y comercio (FEMSA)", "BMV:KOF": "Bebidas (Coca-Cola FEMSA)", "BMV:AC": "Bebidas (Arca Continental)"}
SECTOR_ES = {"Semiconductors & Related Devices": "Semiconductores", "Pharmaceutical Preparations": "Farmacéutico",
             "Petroleum Refining": "Petróleo y refinación", "Retail-Variety Stores": "Comercio minorista",
             "Biological Products, (No Diagnostic Substances)": "Biotecnología"}


def sectores() -> dict:
    df = pd.read_csv(RAIZ / "config" / "sectores.csv")
    out = {r.id: SECTOR_ES.get(r.sector, r.sector) for r in df.itertuples() if isinstance(r.sector, str) and r.sector}
    out.update(SECTOR_BMV)
    out["SIC:QQQ"] = "ETF Nasdaq-100 (tecnología, diversificado)"
    return out


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f"file:{ARCHIVO}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    caps = [dict(r) for r in con.execute("SELECT * FROM capturas_portal WHERE etapa='competencia' ORDER BY hora_portal")]
    pos = {c["id"]: [dict(r) for r in con.execute(
        "SELECT instrumento_id, texto, titulos, costo_promedio, precio, valor FROM posiciones_portal WHERE captura_id=? "
        "ORDER BY valor DESC", (c["id"],))] for c in caps}
    sec = sectores()
    inicial, final = caps[0], caps[-1]

    # Serie diaria: la última captura de cada día (hora del portal, CDMX).
    s = pd.Series({pd.Timestamp(c["hora_portal"][:10]): c["valor_portafolio"] for c in caps}).sort_index()
    r = s.pct_change().dropna()
    var95 = float(-np.quantile(r, 0.05))
    riesgo = {"observaciones": int(len(r)), "desv_diaria": float(r.std()), "desv_anual": float(r.std() * np.sqrt(252)),
              "var95_historico_diario": var95, "peor_dia": float(r.min()), "mejor_dia": float(r.max())}

    # Benchmark: NAFTRAC (réplica del IPC) en el mismo periodo, cierres EOD guardados por la terminal.
    naf = pd.Series({pd.Timestamp(f): p for f, p in con.execute(
        "SELECT fecha, cierre FROM precios WHERE instrumento_id='BMV:NAFTRAC' AND fecha BETWEEN ? AND ? ORDER BY fecha",
        (s.index[0].date().isoformat(), s.index[-1].date().isoformat()))})
    bench = {"instrumento": "NAFTRAC (iShares, réplica del S&P/BMV IPC)", "fuente": "EODHD, cierres diarios",
             "inicio": naf.index[0].date().isoformat(), "fin": naf.index[-1].date().isoformat(),
             "rendimiento": float(naf.iloc[-1] / naf.iloc[0] - 1)} if len(naf) > 1 else None

    # Movimientos entre el 6 y el 31 de octubre: cambios de títulos entre capturas consecutivas.
    movs, todos, previo = [], [], {p["instrumento_id"]: p["titulos"] for p in pos[inicial["id"]]}
    for c in caps[1:]:
        actual = {p["instrumento_id"]: p["titulos"] for p in pos[c["id"]]}
        fecha = c["hora_portal"][:10]
        for iid in sorted(set(previo) | set(actual)):
            a, b = previo.get(iid, 0), actual.get(iid, 0)
            if abs(a - b) > 1e-9:
                todos.append({"fecha": fecha, "instrumento": iid, "de": a, "a": b, "tipo": "compra" if b > a else "venta"})
                if "2026-10-06" <= fecha <= "2026-10-31":
                    movs.append(todos[-1])
        previo = actual

    def tabla(cid):
        total = sum(p["valor"] for p in pos[cid])
        return [{"instrumento": p["instrumento_id"], "sector": sec.get(p["instrumento_id"], "PENDIENTE: sector"),
                 "titulos": p["titulos"], "costo_promedio": p["costo_promedio"], "precio": p["precio"], "valor": p["valor"],
                 "peso": p["valor"] / total if total else 0,
                 "rend": (p["precio"] / p["costo_promedio"] - 1) if p.get("precio") and p.get("costo_promedio") else None}
                for p in pos[cid]]

    corte_oct = max((c for c in caps if c["hora_portal"][:10] <= "2026-10-31"), key=lambda c: c["hora_portal"])
    datos = {"archivo": ARCHIVO.name, "capital_inicial": CAPITAL, "capturas": len(caps),
             "inicial": {"hora": inicial["hora_portal"], "valor": inicial["valor_portafolio"], "efectivo": inicial["efectivo"],
                         "posiciones": tabla(inicial["id"])},
             "corte_octubre": {"hora": corte_oct["hora_portal"], "valor": corte_oct["valor_portafolio"],
                               "efectivo": corte_oct["efectivo"], "rend": corte_oct["valor_portafolio"] / CAPITAL - 1,
                               "posiciones": tabla(corte_oct["id"])},
             "final": {"hora": final["hora_portal"], "valor": final["valor_portafolio"], "efectivo": final["efectivo"],
                       "rend": final["valor_portafolio"] / CAPITAL - 1, "posiciones": tabla(final["id"])},
             "movimientos_octubre": movs, "movimientos_todos": todos, "riesgo": riesgo, "benchmark": bench,
             "serie": [{"fecha": d.date().isoformat(), "valor": float(v)} for d, v in s.items()]}

    # Gráfica 1: evolución del portafolio frente a NAFTRAC (base 100).
    fig, ax = plt.subplots(figsize=(8, 3.6), dpi=150)
    ax.plot(s.index, s / CAPITAL * 100, color=ROJO, lw=2, label="Portafolio (capturas del portal)")
    if len(naf) > 1:
        ax.plot(naf.index, naf / naf.iloc[0] * 100, color=GRIS, lw=1.6, ls="--", label="NAFTRAC (base 100)")
    ax.axhline(100, color="#999", lw=.8)
    ax.set_ylabel("Base 100"); ax.legend(frameon=False, fontsize=8); ax.grid(alpha=.25)
    ax.set_title("Evolución del portafolio — Reto Actinver 2026", fontsize=10, color=TEXTO)
    fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(SALIDA / "evolucion.png"); plt.close(fig)

    # Gráfica 2: distribución inicial (5-oct).
    t = datos["inicial"]["posiciones"]
    fig, ax = plt.subplots(figsize=(5.2, 3.6), dpi=150)
    ax.pie([x["valor"] for x in t], labels=[x["instrumento"].split(":")[1] for x in t], autopct="%1.1f %%",
           colors=["#b3261e", "#4a505a", "#7d828c", "#a9b0bb", "#d9d7d1", "#15171c"], textprops={"fontsize": 8})
    ax.set_title("Distribución inicial del capital invertido (5-oct-2026)", fontsize=9)
    fig.tight_layout(); fig.savefig(SALIDA / "distribucion_inicial.png"); plt.close(fig)

    # Gráfica 3: análisis técnico de MU (3 meses), cierres de la terminal; SMA20/50, RSI14 (Wilder) y MACD 12-26-9.
    mu = pd.Series({pd.Timestamp(f): p for f, p in con.execute(
        "SELECT fecha, cierre FROM precios WHERE instrumento_id='SIC:MU' AND fecha BETWEEN '2026-05-01' AND '2026-11-13' "
        "AND tipo_dato='cierre' ORDER BY fecha")}).groupby(level=0).last()
    d = mu.diff(); up = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi = 100 - 100 / (1 + up / dn)
    macd = mu.ewm(span=12, adjust=False).mean() - mu.ewm(span=26, adjust=False).mean(); senal = macd.ewm(span=9, adjust=False).mean()
    v = mu.index >= mu.index[-1] - pd.Timedelta(days=92)
    fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(8, 6), dpi=150, sharex=True, gridspec_kw={"height_ratios": [3, 1, 1]})
    a1.plot(mu[v].index, mu[v], color=TEXTO, lw=1.6, label="Cierre (USD)")
    a1.plot(mu[v].index, mu.rolling(20).mean()[v], color=ROJO, lw=1, label="SMA 20")
    a1.plot(mu[v].index, mu.rolling(50).mean()[v], color=GRIS, lw=1, label="SMA 50")
    a1.legend(frameon=False, fontsize=7); a1.set_title("Micron Technology (MU) — últimos 3 meses", fontsize=10); a1.grid(alpha=.25)
    a2.plot(rsi[v].index, rsi[v], color=ROJO, lw=1); a2.axhline(70, color="#999", lw=.7); a2.axhline(30, color="#999", lw=.7)
    a2.set_ylabel("RSI 14", fontsize=8); a2.grid(alpha=.25)
    a3.plot(macd[v].index, macd[v], color=TEXTO, lw=1, label="MACD"); a3.plot(senal[v].index, senal[v], color=ROJO, lw=1, label="Señal")
    a3.bar(macd[v].index, (macd - senal)[v], color="#a9b0bb"); a3.legend(frameon=False, fontsize=7); a3.grid(alpha=.25)
    fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(SALIDA / "tecnico_mu.png"); plt.close(fig)
    datos["tecnico_mu"] = {"fuente": "Tiingo/Alpaca, cierres diarios en USD guardados por la terminal",
                          "desde": mu[v].index[0].date().isoformat(), "hasta": mu.index[-1].date().isoformat(),
                          "cierre": float(mu.iloc[-1]), "sma20": float(mu.rolling(20).mean().iloc[-1]),
                          "sma50": float(mu.rolling(50).mean().iloc[-1]), "rsi14": float(rsi.iloc[-1]),
                          "macd": float(macd.iloc[-1]), "senal": float(senal.iloc[-1]),
                          "variacion_3m": float(mu.iloc[-1] / mu[v].iloc[0] - 1)}
    (SALIDA / "datos.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: datos[k] for k in ("capturas", "riesgo", "benchmark", "tecnico_mu")}, ensure_ascii=False, indent=1))
    print("movimientos oct:", len(movs), "| inicial", datos["inicial"]["valor"], "| corte oct", corte_oct["valor_portafolio"],
          "| final", final["valor_portafolio"])


if __name__ == "__main__":
    main()
