"""Razones financieras de Micron (MU) para el informe del concurso, desde los datos XBRL oficiales de SEC EDGAR.

Fuente gratuita y legal (companyfacts). Exige SEC_USER_AGENT en .env; el valor nunca se imprime.
Escribe data/medios/informe/fundamentales_mu.json (carpeta privada, fuera del repositorio).

    uv run python scripts/informe_fundamentales_mu.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from terminal.config import _cargar_env_local  # noqa: E402  (lee .env sin imprimirlo)
SALIDA = RAIZ / "data" / "medios" / "informe" / "fundamentales_mu.json"
CIK = 723125  # Micron Technology, Inc.
URL = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK:010d}.json"


def anual(facts: dict, concepto: str, unidad: str = "USD") -> list[dict]:
    """Valores de los 10-K (FY) por fecha de cierre, el último registrado gana."""
    filas = facts.get("us-gaap", {}).get(concepto, {}).get("units", {}).get(unidad, [])
    por_fin: dict[str, dict] = {}
    for f in filas:
        if f.get("form") == "10-K" and f.get("fp") == "FY":
            # Flujos: periodo de ~1 año; saldos: sin «start».
            if "start" in f:
                dias = (int(f["end"][:4]) - int(f["start"][:4])) * 365 + (int(f["end"][5:7]) - int(f["start"][5:7])) * 30
                if not 330 <= dias <= 400:
                    continue
            por_fin[f["end"]] = f
    return [por_fin[k] for k in sorted(por_fin)]


def ultimo(facts, *conceptos, unidad="USD", n=1):
    for c in conceptos:
        v = anual(facts, c, unidad)
        if v:
            return v[-n:]
    return []


def main() -> int:
    _cargar_env_local()
    ua = os.environ.get("SEC_USER_AGENT", "")
    if not ua:
        print("Falta SEC_USER_AGENT en .env")
        return 1
    r = httpx.get(URL, headers={"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}, timeout=30)
    r.raise_for_status()
    facts = r.json()["facts"]

    ventas = ultimo(facts, "RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", n=2)
    utilidad = ultimo(facts, "NetIncomeLoss", n=2)
    ac = ultimo(facts, "AssetsCurrent")[-1]
    pc = ultimo(facts, "LiabilitiesCurrent")[-1]
    activos = ultimo(facts, "Assets", n=2)
    pasivos = ultimo(facts, "Liabilities")[-1]
    capital = ultimo(facts, "StockholdersEquity", n=2)
    deuda_lp = ultimo(facts, "LongTermDebtNoncurrent")
    bpa = ultimo(facts, "EarningsPerShareDiluted", unidad="USD/shares")[-1]

    v1, v0 = ventas[-1]["val"], ventas[-2]["val"]
    u1, u0 = utilidad[-1]["val"], utilidad[-2]["val"]
    act_prom = (activos[-1]["val"] + activos[-2]["val"]) / 2
    cap_prom = (capital[-1]["val"] + capital[-2]["val"]) / 2
    datos = {
        "fuente": "SEC EDGAR, XBRL companyfacts (10-K) de Micron Technology, CIK 0000723125",
        "ejercicio": ventas[-1]["end"], "ejercicio_anterior": ventas[-2]["end"],
        "presentado": ventas[-1].get("filed"), "accn": ventas[-1].get("accn"),
        "ventas": v1, "ventas_anterior": v0, "utilidad_neta": u1, "utilidad_anterior": u0,
        "activo_circulante": ac["val"], "pasivo_circulante": pc["val"],
        "activos": activos[-1]["val"], "pasivos": pasivos["val"], "capital": capital[-1]["val"],
        "deuda_largo_plazo": deuda_lp[-1]["val"] if deuda_lp else None,
        "bpa_diluido_usd": bpa["val"],
        "razon_circulante": ac["val"] / pc["val"],
        "pasivo_capital": pasivos["val"] / capital[-1]["val"],
        "rotacion_activos": v1 / act_prom,
        "margen_neto": u1 / v1, "roe": u1 / cap_prom,
        "crec_ventas": v1 / v0 - 1, "crec_utilidad": u1 / u0 - 1 if u0 else None,
    }
    SALIDA.write_text(json.dumps(datos, indent=1, ensure_ascii=False), encoding="utf-8")
    json.dump({k: v for k, v in datos.items()}, sys.stdout, indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
