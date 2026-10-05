"""Incorpora al universo y al catálogo del simulador los ETF vistos en la pestaña «ETF's» del simulador del Reto
(capturas del participante del 5-oct-2026). Nombres y bolsa: Nasdaq Trader Symbol Directory (fuente oficial).
Los apalancados e inversos quedan registrados con estado «excluido» (regla de la terminal: sin apalancamiento).

Uso: uv run python scripts/incorporar_etf_simulador.py
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[1]
UNIVERSO = RAIZ / "config" / "universo.csv"
LISTA = RAIZ / "config" / "simulador_etf.csv"
FECHA = "2026-10-05"
ORIGEN = "Pestaña «ETF's» del simulador del Reto (capturas del participante, 5-oct-2026)"

# clave del simulador → categoría (las «apalancado_*»/«inverso_*» se excluyen)
ETF = {
    "AAXJ": "renta_variable_asia", "ACWI": "renta_variable_global", "BIL": "deuda_usd_corto", "BOTZ": "tematico_robotica",
    "DIA": "renta_variable_eeuu", "EEM": "renta_variable_emergentes", "EWZ": "renta_variable_brasil",
    "FAS": "apalancado_3x", "FAZ": "inverso_3x", "GDX": "mineras_oro", "GLD": "materias_primas_oro",
    "IAU": "materias_primas_oro", "ICLN": "tematico_energia_limpia", "INDA": "renta_variable_india",
    "IVV": "renta_variable_eeuu", "KWEB": "renta_variable_china", "LIT": "tematico_litio", "MCHI": "renta_variable_china",
    "PSQ": "inverso_1x", "QCLN": "tematico_energia_limpia", "QLD": "apalancado_2x", "QQQ": "renta_variable_eeuu",
    "SHV": "deuda_usd_corto", "SHY": "deuda_usd_corto", "SLV": "materias_primas_plata", "SOXL": "apalancado_3x",
    "SOXS": "inverso_3x", "SOXX": "sectorial_semiconductores", "SPXL": "apalancado_3x", "SPXS": "inverso_3x",
    "SPY": "renta_variable_eeuu", "SPYM": "renta_variable_eeuu", "SQQQ": "inverso_3x", "TAN": "tematico_solar",
    "TECL": "apalancado_3x", "TECS": "inverso_3x", "TLT": "deuda_usd_largo", "TNA": "apalancado_3x", "TQQQ": "apalancado_3x",
    "TZA": "inverso_3x", "USO": "materias_primas_petroleo", "VEA": "renta_variable_desarrollados",
    "VGT": "sectorial_tecnologia", "VNQ": "bienes_raices_eeuu", "VOO": "renta_variable_eeuu", "VT": "renta_variable_global",
    "VTI": "renta_variable_eeuu", "VWO": "renta_variable_emergentes", "VYM": "dividendos_eeuu", "XLE": "sectorial_energia",
    "XLF": "sectorial_financiero", "XLK": "sectorial_tecnologia", "XLV": "sectorial_salud",
}
BMV = {"NAFTRAC": ("ISHRS", "iShares NAFTRAC (réplica del S&P/BMV IPC)", "renta_variable_mx"),
       "ANGELD": ("10", None, None), "DIABLOI": ("10", None, None)}
BOLSAS = {"Q": "NASDAQ", "P": "NYSE Arca", "N": "NYSE", "Z": "Cboe BZX", "A": "NYSE American", "V": "IEX"}


def directorio() -> dict[str, dict]:
    h = {"User-Agent": "actinver-terminal (uso personal; verificacion de simbolos)"}
    out = {}
    for url, sym, bolsa in (("https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt", "Symbol", None),
                            ("https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt", "ACT Symbol", "Exchange")):
        txt = httpx.get(url, headers=h, timeout=60).text
        for r in csv.DictReader(io.StringIO(txt), delimiter="|"):
            s = (r.get(sym) or "").strip()
            if s and not s.startswith("File Creation"):
                out[s] = {"nombre": r.get("Security Name", "").strip(), "etf": r.get("ETF", "").strip(),
                          "bolsa": BOLSAS.get((r.get(bolsa) or "Q").strip(), "NASDAQ") if bolsa else "NASDAQ"}
    return out


def main() -> None:
    d = directorio()
    filas = list(csv.DictReader(UNIVERSO.open(encoding="utf-8")))
    cols = list(filas[0].keys())
    por_id = {f["id"]: f for f in filas}
    nuevos, actualizados, faltan = [], [], []
    for t, cat in ETF.items():
        info = d.get(t)
        if not info:
            faltan.append(t)
            continue
        excl = cat.startswith(("apalancado", "inverso"))
        fila = {"id": f"SIC:{t}", "clave": t, "serie": "*", "clave_operable": f"{t} *",
                "nombre": info["nombre"][:120] + (" — excluido: apalancado o inverso" if excl else ""), "clase": "etf",
                "categoria": cat, "pais": "", "mercado_operable": "BMV-SIC", "moneda_operable": "MXN",
                "zona_horaria_operable": "America/Mexico_City", "listado_referencia": t, "moneda_referencia": "USD",
                "bolsa_referencia": info["bolsa"], "zona_horaria_referencia": "America/New_York",
                "estado": "excluido" if excl else "activo", "secciones_pdf": "ETF (portal 2026-10-05)",
                "fuente_verificacion": "Nasdaq Trader Symbol Directory",
                "detalle_verificacion": f"ETF={info['etf'] or '?'} en directorio de EE. UU. Operable: {ORIGEN}.",
                "fecha_verificacion": FECHA}
        if fila["id"] in por_id:
            por_id[fila["id"]].update({k: fila[k] for k in ("estado", "secciones_pdf", "detalle_verificacion", "fecha_verificacion",
                                                             "categoria")})
            actualizados.append(t)
        else:
            filas.append(fila)
            por_id[fila["id"]] = fila
            nuevos.append(t)
    for t, (serie, nombre, cat) in BMV.items():
        i = f"BMV:{t}"
        if i in por_id:
            por_id[i].update({"serie": serie, "clave_operable": f"{t} {serie}", "secciones_pdf": "ETF (portal 2026-10-05)"})
            actualizados.append(t)
        else:
            filas.append({"id": i, "clave": t, "serie": serie, "clave_operable": f"{t} {serie}", "nombre": nombre, "clase": "etf",
                          "categoria": cat, "pais": "MX", "mercado_operable": "BMV", "moneda_operable": "MXN",
                          "zona_horaria_operable": "America/Mexico_City", "listado_referencia": i, "moneda_referencia": "MXN",
                          "bolsa_referencia": "BMV", "zona_horaria_referencia": "America/Mexico_City", "estado": "activo",
                          "secciones_pdf": "ETF (portal 2026-10-05)", "fuente_verificacion": "BlackRock México (iShares NAFTRAC)",
                          "detalle_verificacion": f"Tracker listado en la BMV. Operable: {ORIGEN}.", "fecha_verificacion": FECHA})
            nuevos.append(t)
    with UNIVERSO.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(filas)
    with LISTA.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["clave", "tipo", "fuente"])
        for t in ETF:
            if t not in faltan:
                w.writerow([f"{t} *", "etf", ORIGEN])
        for t, (serie, _, _) in BMV.items():
            w.writerow([f"{t} {serie}", "etf", ORIGEN])
    print(f"nuevos {len(nuevos)}: {', '.join(nuevos)}")
    print(f"actualizados {len(actualizados)}: {', '.join(actualizados)}")
    print(f"no encontrados en el directorio: {faltan or 'ninguno'}")
    if faltan:
        sys.exit(1)


if __name__ == "__main__":
    main()
