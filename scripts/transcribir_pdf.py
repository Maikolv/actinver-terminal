"""Transcripción manual (verificada visualmente página por página) de «Datos Actinver.pdf».

El PDF solo contiene capturas de pantalla (sin capa de texto), por lo que la lista se
transcribió leyendo cada página. Se registran símbolo, serie, sección rotulada y página.
Los precios de las capturas NO se transcriben aquí: son históricos y la terminal nunca
los usa como cotización.

Ejecutar:  uv run python scripts/transcribir_pdf.py   -> config/pdf_transcripcion.csv
"""
import csv
from pathlib import Path

# Orden exacto de aparición en la sección «Acciones» (págs. 1-6). Formato "CLAVE SERIE".
ACCIONES = """
AA1 *|AAL *|AAPL *|ABBV *|ABNB *|AC *|ACTINVR B|AFRM *|AGNC *|ALFA A|
ALPEK A|ALSEA *|AMAT *|AMD *|AMX B|AMZN *|ASUR B|AVGO *|AXP *|BA *|
BABA N|BAC *|BBAJIO O|BIMBO A|BMY *|BOLSA A|BRKB *|C *|CAT *|CCL1 N|
CEMEX CPO|CHDRAUI B|CLF *|COST *|CPE *|CRM *|CSCO *|CUERVO *|CVS *|CVX *|
DAL *|DIS *|DVN *|ELEKTRA *|ETSY *|F *|FANG *|FCX *|FDX *|FEMSA UBD|
FIBRAMQ 12|FIBRAPL 14|FSLR *|FUBO *|FUNO 11|GAP B|GCARSO A1|GCC *|GE *|GENTERA *|
GFINBUR O|GFNORTE O|GM *|GME *|GMEXICO B|GOLD N|GOOGL *|GRUMA B|HD *|INTC *|
JNJ *|JPM *|KIMBER A|KO *|KOF UBL|LAB B|LASITE B-1|LCID *|LIVEPOL C-1|LLY *|
LUV *|LVS *|MA *|MARA *|MCD *|MEGA CPO|MELI N|META *|MFRISCO A-1|MRK *|
MRNA *|MRO *|MSFT *|MU *|NCLH N|NFLX *|NKE *|NU N|NVAX *|NVDA *|
OMA B|ORBIA *|ORCL *|OXY1 *|PARA *|PE&OLES *|PEP *|PFE *|PG *|PINFRA *|
PINS *|PLTR *|PYPL *|Q *|QCOM *|R A|RCL *|RIOT *|RIVN *|SBUX *|
SHOP N|SITES1 A-1|SOFI *|SPCE *|T *|TERRA 13|TGT *|TLEVISA CPO|TMO *|TSLA *|
TSM N|TX *|UAL *|UBER *|UNH *|UPST *|V *|VESTA *|VOLAR A|VZ *|
WALMEX *|WFC *|WMT *|XOM *|XYZ *|ZM *
"""
# Páginas donde aparece cada bloque dentro de «Acciones».
PAG_ACCIONES = [(0, 30, 1), (30, 50, 2), (50, 80, 3), (80, 110, 4), (110, 140, 5), (140, 146, 6)]
# La sección rotulada «ETF's» (págs. 6-11) repite exactamente la misma lista.
PAG_ETF = [(0, 20, 6), (20, 50, 7), (50, 80, 8), (80, 110, 9), (110, 140, 10), (140, 146, 11)]

FONDOS = ("ACTDUAL ACTI500 ACTIAI ACTICOB ACTICRE ACTIG+ ACTIG+2 ACTIGOB ACTIMED ACTIPLU "
          "ACTIREN ACTIVAR ALTERN DINAMO ESCALA ESFERA JPMRVUS MAXIMO MAYA OPORT1 ROBOTIK "
          "SALUD TEMATIK").split()


def main() -> None:
    items = [s.strip() for s in ACCIONES.replace("\n", "").split("|") if s.strip()]
    assert len(items) == 146, len(items)
    assert len(set(items)) == len(items), "símbolos duplicados en la transcripción"
    rows = []
    for seccion, paginas in (("Acciones", PAG_ACCIONES), ("ETF's (rótulo del PDF)", PAG_ETF)):
        for a, b, pag in paginas:
            for it in items[a:b]:
                clave, serie = it.rsplit(" ", 1)
                rows.append({"clave_pdf": clave, "serie_pdf": serie, "seccion_pdf": seccion, "pagina": pag})
    for f in FONDOS:
        rows.append({"clave_pdf": f, "serie_pdf": "", "seccion_pdf": "Fondos", "pagina": 11})
    out = Path(__file__).resolve().parents[1] / "config" / "pdf_transcripcion.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["clave_pdf", "serie_pdf", "seccion_pdf", "pagina"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} filas -> {out}")


if __name__ == "__main__":
    main()
