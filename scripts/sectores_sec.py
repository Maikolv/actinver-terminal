"""Genera config/sectores.csv con la clasificación industrial SIC que la SEC publica para cada emisora de EE. UU. del SIC.

Fuente: https://data.sec.gov/submissions/CIK##########.json («sicDescription»), API pública, ≤ 10 peticiones/s y
SEC_USER_AGENT en .env. Los ETF y las emisoras BMV no tienen SIC en la SEC: agréguelas a mano con fuente.
Uso: uv run python scripts/sectores_sec.py
"""
from __future__ import annotations

import csv
import os
import time
from pathlib import Path

import httpx

from terminal import db, mercado
from terminal.capitalizacion import CLASES_ACCION, TICKERS_SEC
from terminal.config import cargar_ajustes

ARCHIVO = Path(__file__).resolve().parent.parent / "config" / "sectores.csv"
URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"


def main() -> None:
    cargar_ajustes()
    ua = os.environ.get("SEC_USER_AGENT")
    if not ua:
        raise SystemExit("Defina SEC_USER_AGENT (nombre y correo) en .env")
    previos = {}
    if ARCHIVO.exists():
        with ARCHIVO.open(encoding="utf-8") as f:
            previos = {r["id"]: r for r in csv.DictReader(f)}
    con = db.conectar()
    ins = mercado.instrumentos(con)
    pendientes = [(i, v) for i, v in ins.items() if v["mercado_operable"] == "BMV-SIC" and v["clase"] in CLASES_ACCION
                  and v.get("moneda_referencia") == "USD" and i not in previos]
    with httpx.Client(timeout=20, headers={"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}) as c:
        mapa = {v["ticker"].upper(): int(v["cik_str"]) for v in c.get(TICKERS_SEC).raise_for_status().json().values()}
        for i, v in pendientes:
            cik = mapa.get((v.get("listado_referencia") or v["clave"]).replace(".", "-").upper())
            if cik is None:
                continue
            time.sleep(0.12)
            r = c.get(URL.format(cik=cik))
            if r.status_code == 200 and r.json().get("sicDescription"):
                d = r.json()
                previos[i] = {"id": i, "sector": d["sicDescription"].strip(), "codigo_sic": d.get("sic") or "",
                              "grupo": f"SIC {(d.get('sic') or '')[:2]}" if d.get("sic") else "",
                              "fuente": "SEC EDGAR submissions (sicDescription)", "fecha": time.strftime("%Y-%m-%d")}
    with ARCHIVO.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "sector", "codigo_sic", "grupo", "fuente", "fecha"])
        w.writeheader()
        w.writerows(sorted(previos.values(), key=lambda r: r["id"]))
    print(f"{len(previos)} instrumentos con sector en {ARCHIVO.name}")


if __name__ == "__main__":
    main()
