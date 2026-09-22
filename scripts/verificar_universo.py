"""Construye config/universo.csv verificando cada instrumento contra fuentes independientes.

Fuentes (públicas, sin credenciales, descargadas una vez por ejecución):
  * Nasdaq Trader Symbol Directory (nasdaqlisted.txt / otherlisted.txt): existencia del
    listado en EE. UU., bolsa, bandera ETF=Y/N y nombre del valor.
  * BMV «Información de emisoras» (descarga pública XLS del botón de la página): claves
    de emisoras de capitales locales.
  * Fichas públicas de fondos de Actinver (config/fondos_actinver.csv, capturadas a mano
    desde https://actinver.com/<fondo>).

La etiqueta de sección del PDF NO determina la clase: la sección «ETF's» del PDF repite
la lista de acciones y ninguno de esos símbolos figura como ETF en Nasdaq Trader.

Uso:  uv run python scripts/verificar_universo.py [--descargar]
"""
from __future__ import annotations

import csv
import hashlib
import sys
from datetime import date
from pathlib import Path

import httpx
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
REF = RAIZ / "data" / "referencias"
CFG = RAIZ / "config"

URLS = {
    "nasdaqlisted.txt": "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
    "otherlisted.txt": "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
    "bmv_emisoras.dl": (
        "https://www.bmv.com.mx/es/Grupo_BMV/Informacion_de_emisora/_rid/541/_mto/3/_mod/doDownload"
        "?idTipoMercado=&idTipoInstrumento=&idTipoEmpresa=&idSector=&idSubsector=&idRamo=&idSubramo=&random=1"
    ),
}

# Emisoras locales de la BMV presentes en el PDF. Clase según estructura jurídica:
# las FIBRA emiten CBFI (certificados de fideicomiso), no acciones.
LOCALES_MX = {
    "AC": "accion", "ACTINVR": "accion", "ALFA": "accion", "ALPEK": "accion", "ALSEA": "accion",
    "AMX": "accion", "ASUR": "accion", "BBAJIO": "accion", "BIMBO": "accion", "BOLSA": "accion",
    "CEMEX": "accion", "CHDRAUI": "accion", "CUERVO": "accion", "ELEKTRA": "accion", "FEMSA": "accion",
    "GAP": "accion", "GCARSO": "accion", "GCC": "accion", "GENTERA": "accion", "GFINBUR": "accion",
    "GFNORTE": "accion", "GMEXICO": "accion", "GRUMA": "accion", "KIMBER": "accion", "KOF": "accion",
    "LAB": "accion", "LASITE": "accion", "LIVEPOL": "accion", "MEGA": "accion", "MFRISCO": "accion",
    "OMA": "accion", "ORBIA": "accion", "PE&OLES": "accion", "PINFRA": "accion", "Q": "accion",
    "R": "accion", "SITES1": "accion", "TLEVISA": "accion", "VESTA": "accion", "VOLAR": "accion",
    "WALMEX": "accion",
    "FIBRAMQ": "fibra", "FIBRAPL": "fibra", "FUNO": "fibra", "TERRA": "fibra",
}
# Clave en el SIC -> símbolo del listado primario en EE. UU.
SIC_A_EEUU = {"AA1": "AA", "CCL1": "CCL", "OXY1": "OXY", "BRKB": "BRK.B"}
# Eventos corporativos conocidos que explican un símbolo ausente del directorio actual.
# Se reportan como «deslistado/cambio de clave» solo si el directorio lo confirma (ausencia).
EVENTOS = {
    "CPE": "Callon Petroleum fue adquirida por APA Corp. (2024).",
    "MRO": "Marathon Oil fue adquirida por ConocoPhillips (2024).",
    "PARA": "Paramount Global se fusionó con Skydance (2025); nueva clave PSKY.",
    "GOLD": "Barrick cambió su clave en NYSE de GOLD a B (2025).",
}
# Palabra clave del emisor esperado: detecta claves reasignadas a otra empresa.
EMISOR_ESPERADO = {
    "AA": "alcoa", "AAL": "american airlines", "AAPL": "apple", "ABBV": "abbvie", "ABNB": "airbnb",
    "AFRM": "affirm", "AGNC": "agnc", "AMAT": "applied materials", "AMD": "advanced micro", "AMZN": "amazon",
    "AVGO": "broadcom", "AXP": "american express", "BA": "boeing", "BABA": "alibaba", "BAC": "bank of america",
    "BMY": "bristol", "BRK.B": "berkshire", "C": "citigroup", "CAT": "caterpillar", "CCL": "carnival",
    "CLF": "cleveland", "COST": "costco", "CPE": "callon", "CRM": "salesforce", "CSCO": "cisco", "CVS": "cvs",
    "CVX": "chevron", "DAL": "delta", "DIS": "disney", "DVN": "devon", "ETSY": "etsy", "F": "ford",
    "FANG": "diamondback", "FCX": "freeport", "FDX": "fedex", "FSLR": "first solar", "FUBO": "fubo",
    "GE": "ge aerospace|general electric", "GM": "general motors", "GME": "gamestop", "GOLD": "barrick",
    "GOOGL": "alphabet", "HD": "home depot", "INTC": "intel", "JNJ": "johnson", "JPM": "jpmorgan|jp morgan",
    "KO": "coca-cola", "LCID": "lucid", "LLY": "lilly", "LUV": "southwest", "LVS": "las vegas sands",
    "MA": "mastercard", "MARA": "mara", "MCD": "mcdonald", "MELI": "mercadolibre", "META": "meta platforms",
    "MRK": "merck", "MRNA": "moderna", "MRO": "marathon oil", "MSFT": "microsoft", "MU": "micron",
    "NCLH": "norwegian", "NFLX": "netflix", "NKE": "nike", "NU": "nu holdings", "NVAX": "novavax",
    "NVDA": "nvidia", "ORCL": "oracle", "OXY": "occidental", "PARA": "paramount", "PEP": "pepsico",
    "PFE": "pfizer", "PG": "procter", "PINS": "pinterest", "PLTR": "palantir", "PYPL": "paypal",
    "QCOM": "qualcomm", "RCL": "royal caribbean", "RIOT": "riot", "RIVN": "rivian", "SBUX": "starbucks",
    "SHOP": "shopify", "SOFI": "sofi", "SPCE": "virgin galactic", "T": "at&t", "TGT": "target",
    "TMO": "thermo fisher", "TSLA": "tesla", "TSM": "taiwan semiconductor", "TX": "ternium", "UAL": "united airlines",
    "UBER": "uber", "UNH": "unitedhealth", "UPST": "upstart", "V": "visa", "VZ": "verizon", "WFC": "wells fargo",
    "WMT": "walmart", "XOM": "exxon", "XYZ": "block", "ZM": "zoom",
    "IVV": "ishares core s&p 500", "VOO": "vanguard s&p 500", "QQQ": "invesco qqq", "VEA": "developed markets",
    "VWO": "emerging markets", "AGG": "aggregate bond", "IEF": "7-10 year", "SHV": "treasury",
    "IAU": "gold trust", "VNQ": "real estate",
}
EVENTOS_MX = {
    "ALFA": ("El XLS vigente de la BMV no contiene ALFA y sí SIGMAF (Sigma Foods): probable cambio de clave "
             "tras la reorganización de Alfa. Confirmar antes de usar."),
    "ELEKTRA": "No figura en el XLS vigente de emisoras de la BMV: revisar suspensión o desliste.",
}


def coincide(ref: str, nombre: str) -> bool:
    kw = EMISOR_ESPERADO.get(ref)
    return kw is None or any(k in nombre.lower() for k in kw.split("|"))


BOLSAS = {"N": "NYSE", "A": "NYSE American", "P": "NYSE Arca", "Z": "Cboe BZX", "V": "IEX", "Q": "NASDAQ"}


def descargar() -> None:
    REF.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=60, follow_redirects=True) as c:
        for nombre, url in URLS.items():
            r = c.get(url)
            r.raise_for_status()
            (REF / nombre).write_bytes(r.content)
            print(f"descargado {nombre} ({len(r.content)} bytes)")


def huella(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def cargar_eeuu() -> dict[str, dict]:
    out: dict[str, dict] = {}
    nl = pd.read_csv(REF / "nasdaqlisted.txt", sep="|", dtype=str).iloc[:-1]
    for _, r in nl.iterrows():
        out[r["Symbol"]] = {"nombre": r["Security Name"], "bolsa": "NASDAQ", "etf": r["ETF"] == "Y",
                            "prueba": r["Test Issue"] == "Y"}
    ol = pd.read_csv(REF / "otherlisted.txt", sep="|", dtype=str).iloc[:-1]
    for _, r in ol.iterrows():
        out[r["ACT Symbol"]] = {"nombre": r["Security Name"], "bolsa": BOLSAS.get(r["Exchange"], r["Exchange"]),
                                "etf": r["ETF"] == "Y", "prueba": r["Test Issue"] == "Y"}
    return out


def cargar_bmv() -> dict[str, str]:
    x = pd.read_excel(REF / "bmv_emisoras.dl", engine="xlrd", header=None, dtype=str)
    return {str(k).strip().upper(): str(v).strip() for k, v in x.iloc[1:].values}


def main() -> None:
    if "--descargar" in sys.argv or not (REF / "otherlisted.txt").exists():
        descargar()
    hoy = date.today().isoformat()
    ee = cargar_eeuu()
    bmv = cargar_bmv()
    fuente_ee = f"Nasdaq Trader Symbol Directory (sha256 {huella(REF / 'otherlisted.txt')}/{huella(REF / 'nasdaqlisted.txt')})"
    fuente_bmv = f"BMV Información de emisoras XLS (sha256 {huella(REF / 'bmv_emisoras.dl')})"

    pdf = list(csv.DictReader((CFG / "pdf_transcripcion.csv").open(encoding="utf-8")))
    secciones: dict[str, set[str]] = {}
    series: dict[str, str] = {}
    for r in pdf:
        secciones.setdefault(r["clave_pdf"], set()).add(r["seccion_pdf"])
        series.setdefault(r["clave_pdf"], r["serie_pdf"])

    filas = []
    for clave, secs in secciones.items():
        if "Fondos" in secs:
            continue
        serie = series[clave]
        base = {"clave": clave, "serie": serie, "clave_operable": f"{clave} {serie}".strip(),
                "secciones_pdf": "; ".join(sorted(secs)), "fecha_verificacion": hoy,
                "moneda_operable": "MXN", "zona_horaria_operable": "America/Mexico_City"}
        if clave in LOCALES_MX:
            clase = LOCALES_MX[clave]
            en_bmv = clave.upper() in bmv or clave.rstrip("1").upper() in bmv
            nombre = bmv.get(clave.upper()) or bmv.get(clave.rstrip("1").upper()) or ""
            if clase == "fibra":
                estado, det = "activo", ("CBFI de FIBRA inmobiliaria; la lista XLS de capitales de la BMV no "
                                         "incluye FIBRA, clase asignada por estructura jurídica (fideicomiso).")
            elif en_bmv:
                estado, det = "activo", "Clave presente en el listado de emisoras de la BMV."
            else:
                estado, det = "por_confirmar", EVENTOS_MX.get(clave, "Clave no encontrada en el XLS de emisoras de la BMV.")
            filas.append({**base, "id": f"BMV:{clave}", "nombre": nombre, "clase": clase, "pais": "MX",
                          "mercado_operable": "BMV", "listado_referencia": f"BMV:{clave}",
                          "moneda_referencia": "MXN", "bolsa_referencia": "BMV",
                          "zona_horaria_referencia": "America/Mexico_City", "estado": estado,
                          "fuente_verificacion": fuente_bmv, "detalle_verificacion": det})
            continue
        ref = SIC_A_EEUU.get(clave, clave)
        info = ee.get(ref)
        fila = {**base, "id": f"SIC:{clave}", "mercado_operable": "BMV-SIC", "listado_referencia": ref,
                "moneda_referencia": "USD", "zona_horaria_referencia": "America/New_York",
                "fuente_verificacion": fuente_ee, "pais": ""}
        if info is None:
            fila.update(nombre="", clase="accion", bolsa_referencia="", estado="deslistado_o_cambio",
                        detalle_verificacion=("Símbolo ausente del directorio de EE. UU. vigente. "
                                              + EVENTOS.get(ref, "Revisar evento corporativo.")))
        elif not coincide(ref, info["nombre"]):
            fila.update(nombre="", clase="accion", bolsa_referencia="", estado="clave_reasignada",
                        detalle_verificacion=(f"La clave {ref} hoy corresponde a «{info['nombre'].strip()}», no al "
                                              f"emisor esperado ({EMISOR_ESPERADO[ref]}). " + EVENTOS.get(ref, "")))
        else:
            clase = "etf" if info["etf"] else ("reit" if "AGNC" == ref else "accion")
            nm = info["nombre"]
            if not info["etf"] and ("ADR" in nm.upper() or "American Depositary" in nm or " ADS" in nm):
                clase_det = "Acción (ADR/ADS de emisora extranjera)."
            else:
                clase_det = "Acción ordinaria." if clase == "accion" else ""
            fila.update(nombre=nm, clase=clase, bolsa_referencia=info["bolsa"], estado="activo",
                        detalle_verificacion=f"ETF={'Y' if info['etf'] else 'N'} en directorio. {clase_det}".strip())
        filas.append(fila)

    for r in csv.DictReader((CFG / "etf_candidatos.csv").open(encoding="utf-8")):
        ref = r["listado_referencia"]
        info = ee.get(ref) if ref else None
        estado = "excluido" if r["disponibilidad_actinver"] == "excluido" else "activo"
        if ref:
            ok = bool(info and info["etf"] and coincide(ref, info["nombre"]))
            det = ("ETF=Y en directorio de EE. UU." if ok else "NO figura como ETF en el directorio.")
            det += " Disponibilidad en el SIC vía Actinver: por confirmar por el usuario."
            if not ok:
                estado = "por_confirmar"
            filas.append({"id": f"SIC:{r['clave']}", "clave": r["clave"], "serie": "*", "clave_operable": f"{r['clave']} *",
                          "nombre": info["nombre"] if info else "", "clase": "etf", "pais": "",
                          "mercado_operable": "BMV-SIC", "moneda_operable": "MXN",
                          "zona_horaria_operable": "America/Mexico_City", "listado_referencia": ref,
                          "moneda_referencia": "USD", "bolsa_referencia": info["bolsa"] if info else "",
                          "zona_horaria_referencia": "America/New_York", "estado": estado,
                          "secciones_pdf": "", "fuente_verificacion": fuente_ee, "detalle_verificacion": det,
                          "fecha_verificacion": hoy, "categoria": r["categoria"]})
        else:
            filas.append({"id": f"BMV:{r['clave']}", "clave": r["clave"], "serie": "", "clave_operable": r["clave"],
                          "nombre": r["motivo_candidato"], "clase": "etf", "pais": "MX", "mercado_operable": "BMV",
                          "moneda_operable": "MXN", "zona_horaria_operable": "America/Mexico_City",
                          "listado_referencia": f"BMV:{r['clave']}", "moneda_referencia": "MXN",
                          "bolsa_referencia": "BMV", "zona_horaria_referencia": "America/Mexico_City",
                          "estado": estado, "secciones_pdf": "", "fuente_verificacion": r["fuente_url"],
                          "detalle_verificacion": "Tracker listado por Actinver en su página de ETF/Trackers.",
                          "fecha_verificacion": hoy, "categoria": r["categoria"]})

    for r in csv.DictReader((CFG / "fondos_actinver.csv").open(encoding="utf-8")):
        filas.append({"id": f"FONDO:{r['clave']}", "clave": r["clave"], "serie": "B", "clave_operable": f"{r['clave']} B",
                      "nombre": r["descripcion"], "clase": r["clase"], "pais": "MX", "mercado_operable": "Fondos Actinver",
                      "moneda_operable": "MXN", "zona_horaria_operable": "America/Mexico_City",
                      "listado_referencia": r["id_vector_precios"], "moneda_referencia": "MXN",
                      "bolsa_referencia": "Operadora Actinver", "zona_horaria_referencia": "America/Mexico_City",
                      "estado": "activo", "secciones_pdf": "Fondos", "fuente_verificacion": r["fuente_url"],
                      "detalle_verificacion": f"{r['categoria_actinver']}; compra {r['ventana_compra']}, venta "
                                              f"{r['ventana_venta']}, liquidación {r['liquidacion']}.",
                      "fecha_verificacion": hoy, "categoria": r["categoria_actinver"]})

    campos = ["id", "clave", "serie", "clave_operable", "nombre", "clase", "categoria", "pais", "mercado_operable",
              "moneda_operable", "zona_horaria_operable", "listado_referencia", "moneda_referencia",
              "bolsa_referencia", "zona_horaria_referencia", "estado", "secciones_pdf", "fuente_verificacion",
              "detalle_verificacion", "fecha_verificacion"]
    with (CFG / "universo.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)

    df = pd.DataFrame(filas)
    print(df.groupby(["clase", "estado"]).size().to_string())
    etf_rot = [f for f in filas if "ETF's (rótulo del PDF)" in f.get("secciones_pdf", "")]
    print(f"\nInstrumentos bajo el rótulo «ETF's» del PDF: {len(etf_rot)}; "
          f"de ellos con ETF=Y verificado: {sum(1 for f in etf_rot if f['clase'] == 'etf')}")
    print("\nNo activos:")
    for f in filas:
        if f["estado"] != "activo":
            print(f"  {f['id']:<16} {f['estado']:<20} {f['detalle_verificacion']}")


if __name__ == "__main__":
    main()
