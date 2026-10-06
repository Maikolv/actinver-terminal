"""Incorpora al universo y al catálogo las acciones que la pestaña «Acciones» del simulador muestra y la terminal no
tenía (PDF del participante del 5-oct-2026, docs/evidencia/simulador/acciones-portal-2026-10-05.pdf).
SIC: nombre y bolsa del Nasdaq Trader Symbol Directory (fuente oficial). BMV: clave y serie del propio portal.

Uso: uv run python scripts/incorporar_acciones_portal.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from incorporar_etf_simulador import LISTA, UNIVERSO, directorio  # noqa: E402

FECHA = "2026-10-05"
ORIGEN = "Pestaña «Acciones» del simulador del Reto (PDF del participante, 5-oct-2026)"
SIC = {"B": "N", "BYND": "*", "ROKU": "*", "TWLO": "*", "WYNN": "*"}  # clave → serie en el portal
BMV = {"SIGMAF": ("A", "SIGMAF A (vista en el portal del simulador; posible sucesora de ALFA, por confirmar)")}


def main() -> None:
    d = directorio()
    filas = list(csv.DictReader(UNIVERSO.open(encoding="utf-8")))
    cols = list(filas[0].keys())
    ids = {f["id"] for f in filas}
    nuevos, faltan = [], []
    for t, serie in SIC.items():
        info = d.get(t)
        if not info or info["etf"] == "Y":
            faltan.append(t)
            continue
        if f"SIC:{t}" not in ids:
            filas.append({"id": f"SIC:{t}", "clave": t, "serie": serie, "clave_operable": f"{t} {serie}",
                          "nombre": info["nombre"][:120], "clase": "accion", "categoria": "", "pais": "",
                          "mercado_operable": "BMV-SIC", "moneda_operable": "MXN", "zona_horaria_operable": "America/Mexico_City",
                          "listado_referencia": t, "moneda_referencia": "USD", "bolsa_referencia": info["bolsa"],
                          "zona_horaria_referencia": "America/New_York", "estado": "activo",
                          "secciones_pdf": "Acciones (portal 2026-10-05)", "fuente_verificacion": "Nasdaq Trader Symbol Directory",
                          "detalle_verificacion": f"ETF=N en directorio de EE. UU. Operable: {ORIGEN}.", "fecha_verificacion": FECHA})
            nuevos.append(t)
    for t, (serie, nombre) in BMV.items():
        if f"BMV:{t}" not in ids:
            filas.append({"id": f"BMV:{t}", "clave": t, "serie": serie, "clave_operable": f"{t} {serie}", "nombre": nombre,
                          "clase": "accion", "categoria": "", "pais": "MX", "mercado_operable": "BMV", "moneda_operable": "MXN",
                          "zona_horaria_operable": "America/Mexico_City", "listado_referencia": f"BMV:{t}",
                          "moneda_referencia": "MXN", "bolsa_referencia": "BMV", "zona_horaria_referencia": "America/Mexico_City",
                          "estado": "activo", "secciones_pdf": "Acciones (portal 2026-10-05)",
                          "fuente_verificacion": "Portal del simulador del Reto",
                          "detalle_verificacion": f"Clave y serie vistas con precio en el portal. Operable: {ORIGEN}.",
                          "fecha_verificacion": FECHA})
            nuevos.append(t)
    with UNIVERSO.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(filas)
    lista = list(csv.DictReader(LISTA.open(encoding="utf-8")))
    vistas = {r["clave"] for r in lista}
    with LISTA.open("a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        for t, serie in SIC.items():
            if t not in faltan and f"{t} {serie}" not in vistas:
                w.writerow([f"{t} {serie}", "accion", ORIGEN])
        for t, (serie, _) in BMV.items():
            if f"{t} {serie}" not in vistas:
                w.writerow([f"{t} {serie}", "accion", ORIGEN])
    print(f"nuevos {len(nuevos)}: {', '.join(nuevos)}")
    print(f"no encontrados como acción en el directorio: {faltan or 'ninguno'}")
    if faltan:
        sys.exit(1)


if __name__ == "__main__":
    main()
