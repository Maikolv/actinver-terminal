"""Auditoría de las series del catálogo del simulador: saltos (splits sin ajustar o errores), mezcla de divisas,
claves reasignadas y huecos. Solo informa; las correcciones se hacen en la fuente (eventos_corporativos, universo).

Uso: uv run python scripts/calidad_series.py [--salida docs/evidencia/calidad_series.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from terminal import db, mercado  # noqa: E402
from terminal.config import cargar_ajustes  # noqa: E402

SALTO = 0.30          # |rendimiento diario| que se revisa a mano
HUECO = 5             # sesiones seguidas sin dato dentro de la serie


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="docs/evidencia/calidad_series.json")
    args = ap.parse_args()
    ajustes = cargar_ajustes()
    con = db.conectar()
    db.inicializar(con, ajustes)
    ins = mercado.instrumentos(con)
    ids = [r[0] for r in con.execute("SELECT id FROM universo_simulador ORDER BY id")]
    precios = mercado.precios_mxn(con, ajustes, ids, ajustados="splits")
    saltos, huecos = [], []
    for c in precios.columns:
        s = precios[c].loc[precios[c].first_valid_index():precios[c].last_valid_index()] if precios[c].notna().any() else None
        if s is None:
            continue
        r = s.ffill(limit=3).pct_change(fill_method=None)
        for f, v in r[r.abs() > SALTO].items():
            saltos.append({"id": c, "fecha": str(f.date()), "rend": round(float(v), 4)})
        nulos = s.isna().astype(int)
        corrida = nulos.groupby((nulos == 0).cumsum()).sum()
        if (corrida > HUECO).any():
            huecos.append({"id": c, "huecos_mayores": int((corrida > HUECO).sum()), "max_sesiones": int(corrida.max())})
    divisas = [{"id": r[0], "monedas": r[1]} for r in con.execute(
        "SELECT instrumento_id, GROUP_CONCAT(DISTINCT moneda) FROM precios WHERE proveedor NOT IN ('demo_sintetico') "
        "GROUP BY instrumento_id HAVING COUNT(DISTINCT moneda) > 1")]
    claves = [{"id": i, "estado": ins[i]["estado"], "detalle": (ins[i].get("detalle_verificacion") or "")[:160]}
              for i in ids if i in ins and ins[i]["estado"] not in ("activo", "excluido")]
    sin_precio = [i for i in ids if i not in precios.columns or precios[i].notna().sum() == 0]
    res = {"instrumentos": len(ids), "saltos_mayores_30pct": saltos, "huecos_mayores_5_sesiones": huecos,
           "mezcla_de_divisas": divisas, "claves_por_revisar": claves, "sin_precio": sin_precio}
    Path(args.salida).write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(ids)} instrumentos · saltos > {SALTO:.0%}: {len(saltos)} · huecos > {HUECO}: {len(huecos)} · "
          f"divisas mezcladas: {len(divisas)} · claves por revisar: {len(claves)} · sin precio: {len(sin_precio)}")


if __name__ == "__main__":
    main()
