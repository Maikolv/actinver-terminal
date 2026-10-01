"""SEC EDGAR: cliente con identificación y control de consultas, y analizadores de Form 4 y Form 13F.

Fuente oficial y gratuita. Reglas de acceso de la SEC (https://www.sec.gov/about/developer-resources):
- cabecera User-Agent con nombre y correo de contacto (`SEC_USER_AGENT` en .env);
- no más de 10 peticiones por segundo; aquí se usan como máximo 5, con reintentos y espera ante 429/5xx.

Nada de esto es una cotización: son declaraciones públicas con su propia fecha de operación, de corte y de publicación.
"""
from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import httpx

ARCHIVO = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}"
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
TICKERS = "https://www.sec.gov/files/company_tickers.json"


class ErrorSEC(Exception):
    pass


class ClienteSEC:
    """Peticiones a la SEC con ritmo máximo, reintentos con espera creciente y conteo de consultas."""

    def __init__(self, user_agent: str | None, cliente: httpx.Client | None = None, max_por_seg: float = 5.0,
                 reintentos: int = 3, dormir=time.sleep):
        if not user_agent or "@" not in user_agent:
            raise ErrorSEC("SEC_USER_AGENT no definido (nombre y correo de contacto): la SEC exige identificarse")
        self.cli = cliente or httpx.Client(timeout=30, follow_redirects=True)
        self.h = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
        self.intervalo = 1.0 / max_por_seg
        self.reintentos = reintentos
        self.dormir = dormir
        self._ultima = 0.0
        self.consultas = 0

    def get(self, url: str) -> httpx.Response:
        espera = 1.0
        for intento in range(self.reintentos + 1):
            falta = self.intervalo - (time.monotonic() - self._ultima)
            if falta > 0:
                self.dormir(falta)
            self._ultima = time.monotonic()
            self.consultas += 1
            try:
                r = self.cli.get(url, headers=self.h)
            except httpx.HTTPError as e:
                if intento == self.reintentos:
                    raise ErrorSEC(f"sin conexión con la SEC ({type(e).__name__})") from None
                self.dormir(espera)
                espera *= 2
                continue
            if r.status_code == 200:
                return r
            if r.status_code in (429, 500, 502, 503, 504) and intento < self.reintentos:
                self.dormir(min(float(r.headers.get("Retry-After") or espera), 60))
                espera *= 2
                continue
            raise ErrorSEC(f"SEC respondió {r.status_code}")
        raise ErrorSEC("SEC sin respuesta")


def url_documento(cik: int | str, acceso: str, nombre: str) -> str:
    return ARCHIVO.format(cik=int(cik), acc=acceso.replace("-", "")) + f"/{nombre}"


def url_indice(cik: int | str, acceso: str) -> str:
    return ARCHIVO.format(cik=int(cik), acc=acceso.replace("-", "")) + f"/{acceso}-index.htm"


def _sin_ns(raiz: ET.Element) -> ET.Element:
    for e in raiz.iter():
        if isinstance(e.tag, str) and "}" in e.tag:
            e.tag = e.tag.split("}", 1)[1]
    return raiz


def _txt(e: ET.Element | None, ruta: str) -> str | None:
    if e is None:
        return None
    x = e.find(ruta)
    if x is None:
        return None
    v = x.find("value")
    t = (v.text if v is not None else x.text) or ""
    return t.strip() or None


def _num(e, ruta) -> float | None:
    t = _txt(e, ruta)
    try:
        return float(t.replace(",", "")) if t else None
    except ValueError:
        return None


def _verdad(t: str | None) -> bool:
    return (t or "").strip().lower() in ("1", "true")


# ------------------------------------------------------------------------------------------------- Form 4
# Código de transacción (Form 4, instrucciones de la SEC) → (clase, descripción, ¿compra/venta discrecional?)
CODIGOS = {
    "P": ("compra_mercado", "Compra en mercado abierto o privada", True),
    "S": ("venta_mercado", "Venta en mercado abierto o privada", True),
    "A": ("adjudicacion", "Adjudicación o concesión del emisor (no es compra en mercado)", False),
    "M": ("ejercicio", "Ejercicio o conversión de un derivado (opciones)", False),
    "X": ("ejercicio", "Ejercicio de un derivado en dinero o fuera de él", False),
    "C": ("conversion", "Conversión de un derivado", False),
    "O": ("ejercicio", "Ejercicio de un derivado fuera de dinero", False),
    "F": ("retencion_impuestos", "Entrega de acciones para pagar impuestos o el ejercicio", False),
    "G": ("donacion", "Donación (regalo)", False),
    "D": ("disposicion_emisor", "Disposición al emisor (no es venta en mercado)", False),
    "J": ("otra", "Otra adquisición o disposición (ver notas del documento)", False),
    "K": ("swap", "Operación de swap de acciones", False),
    "W": ("herencia", "Adquisición o disposición por testamento o herencia", False),
    "I": ("plan_emisor", "Operación discrecional dentro de un plan del emisor (Rule 16b-3)", False),
    "L": ("pequena", "Adquisición pequeña (Rule 16a-6)", False),
    "Z": ("fideicomiso", "Depósito o retiro de un fideicomiso de voto", False),
    "E": ("vencimiento", "Vencimiento de un derivado corto", False),
    "H": ("vencimiento", "Vencimiento o cancelación de un derivado largo", False),
    "U": ("oferta", "Disposición por oferta de adquisición (cambio de control)", False),
    "V": ("voluntaria", "Operación reportada voluntariamente", False),
}


def clasificar_f4(codigo: str | None, adq_disp: str | None, plan_10b5_1: bool) -> tuple[str, str, bool]:
    clase, desc, discrecional = CODIGOS.get((codigo or "").upper(), ("desconocida", f"Código «{codigo}» no reconocido", False))
    if clase == "venta_mercado" and plan_10b5_1:
        return "venta_plan_10b5_1", "Venta bajo un plan 10b5-1 (programada de antemano)", False
    if clase == "compra_mercado" and plan_10b5_1:
        return "compra_plan_10b5_1", "Compra bajo un plan 10b5-1 (programada de antemano)", False
    if clase in ("compra_mercado", "venta_mercado") and adq_disp and \
            ((clase == "compra_mercado") != (adq_disp.upper() == "A")):
        return "otra", f"{desc} con signo inconsistente: revise el documento", False
    return clase, desc, discrecional


@dataclass
class Form4:
    tipo: str                       # «4» o «4/A»
    periodo: str | None             # fecha del evento más antiguo que obliga a presentar
    fecha_original: str | None      # en una 4/A: fecha de presentación del original
    emisor_cik: str
    emisor: str
    simbolo: str | None
    declarantes: list[dict]
    plan_10b5_1: bool
    transacciones: list[dict] = field(default_factory=list)


def parsear_form4(contenido: bytes | str) -> Form4:
    raiz = _sin_ns(ET.fromstring(contenido.encode() if isinstance(contenido, str) else contenido))
    notas = {n.get("id"): " ".join((n.text or "").split()) for n in raiz.iter("footnote")}
    declarantes = []
    for o in raiz.findall("reportingOwner"):
        rel = o.find("reportingOwnerRelationship")
        roles = []
        if rel is not None:
            if _verdad(rel.findtext("isDirector")):
                roles.append("consejero")
            if _verdad(rel.findtext("isOfficer")):
                roles.append(f"directivo ({(rel.findtext('officerTitle') or '').strip()})".replace(" ()", ""))
            if _verdad(rel.findtext("isTenPercentOwner")):
                roles.append("tenedor de ≥10 %")
            if _verdad(rel.findtext("isOther")):
                roles.append(f"otro ({(rel.findtext('otherText') or '').strip()})".replace(" ()", ""))
        declarantes.append({"cik": (o.findtext("reportingOwnerId/rptOwnerCik") or "").strip().lstrip("0"),
                            "nombre": " ".join((o.findtext("reportingOwnerId/rptOwnerName") or "").split()),
                            "relacion": ", ".join(roles) or "no indicada"})
    plan = _verdad(raiz.findtext("aff10b5One"))
    f = Form4(tipo=(raiz.findtext("documentType") or "4").strip(), periodo=(raiz.findtext("periodOfReport") or "").strip() or None,
              fecha_original=(raiz.findtext("dateOfOriginalSubmission") or "").strip() or None,
              emisor_cik=(raiz.findtext("issuer/issuerCik") or "").strip().lstrip("0"),
              emisor=" ".join((raiz.findtext("issuer/issuerName") or "").split()),
              simbolo=((raiz.findtext("issuer/issuerTradingSymbol") or "").strip().upper() or None),
              declarantes=declarantes, plan_10b5_1=plan)
    for tabla, ruta in (("no_derivado", "nonDerivativeTable/nonDerivativeTransaction"),
                        ("derivado", "derivativeTable/derivativeTransaction")):
        for i, t in enumerate(raiz.findall(ruta)):
            codigo = (t.findtext("transactionCoding/transactionCode") or "").strip()
            refs = [r.get("id") for r in t.iter("footnoteId")]
            texto_notas = " ".join(notas.get(r, "") for r in refs)
            plan_fila = plan or bool(re.search(r"10b5-1", texto_notas, re.I))
            adq = _txt(t, "transactionAmounts/transactionAcquiredDisposedCode")
            clase, desc, discrecional = clasificar_f4(codigo, adq, plan_fila)
            f.transacciones.append({
                "tabla": tabla, "fila": i, "titulo_valor": _txt(t, "securityTitle"),
                "fecha_operacion": (_txt(t, "transactionDate") or "")[:10] or None, "codigo": codigo,
                "adquirido_dispuesto": adq, "titulos": _num(t, "transactionAmounts/transactionShares"),
                "precio": _num(t, "transactionAmounts/transactionPricePerShare"),
                "posee_despues": _num(t, "postTransactionAmounts/sharesOwnedFollowingTransaction"),
                "titularidad": _txt(t, "ownershipNature/directOrIndirectOwnership"),
                "naturaleza": _txt(t, "ownershipNature/natureOfOwnership"),
                "clasificacion": clase, "descripcion": desc, "discrecional": discrecional, "plan_10b5_1": plan_fila,
                "notas": texto_notas[:500] or None})
    return f


# ------------------------------------------------------------------------------------------------- Form 13F
@dataclass
class Portada13F:
    periodo: str               # fecha de corte de la cartera (AAAA-MM-DD)
    es_enmienda: bool
    tipo_enmienda: str | None  # «RESTATEMENT» (reemplaza) o «NEW HOLDINGS» (añade)
    numero_enmienda: int | None
    tipo_reporte: str
    filas: int | None
    valor_total: float | None
    gestor: str


def _fecha_mdy(t: str | None) -> str | None:
    m = re.match(r"(\d{2})-(\d{2})-(\d{4})", (t or "").strip())
    return f"{m.group(3)}-{m.group(1)}-{m.group(2)}" if m else ((t or "").strip()[:10] or None)


def parsear_portada_13f(contenido: bytes | str) -> Portada13F:
    raiz = _sin_ns(ET.fromstring(contenido.encode() if isinstance(contenido, str) else contenido))
    tipo = (raiz.findtext(".//amendmentInfo/amendmentType") or "").strip().upper() or None
    num = (raiz.findtext(".//coverPage/amendmentNo") or "").strip()
    return Portada13F(
        periodo=_fecha_mdy(raiz.findtext(".//coverPage/reportCalendarOrQuarter") or raiz.findtext(".//periodOfReport")),
        es_enmienda=_verdad(raiz.findtext(".//coverPage/isAmendment")), tipo_enmienda=tipo,
        numero_enmienda=int(num) if num.isdigit() else None,
        tipo_reporte=(raiz.findtext(".//coverPage/reportType") or "").strip(),
        filas=int(raiz.findtext(".//summaryPage/tableEntryTotal") or 0) or None,
        valor_total=float(raiz.findtext(".//summaryPage/tableValueTotal") or 0) or None,
        gestor=" ".join((raiz.findtext(".//coverPage/filingManager/name") or "").split()))


def parsear_tabla_13f(contenido: bytes | str) -> list[dict]:
    raiz = _sin_ns(ET.fromstring(contenido.encode() if isinstance(contenido, str) else contenido))
    out = []
    for t in raiz.findall("infoTable"):
        out.append({"emisor": " ".join((t.findtext("nameOfIssuer") or "").split()),
                    "clase": " ".join((t.findtext("titleOfClass") or "").split()),
                    "cusip": (t.findtext("cusip") or "").strip().upper(),
                    "valor": float(t.findtext("value") or 0),
                    "titulos": float(t.findtext("shrsOrPrnAmt/sshPrnamt") or 0),
                    "tipo_titulos": (t.findtext("shrsOrPrnAmt/sshPrnamtType") or "SH").strip(),
                    "put_call": ((t.findtext("putCall") or "").strip().upper() or None)})
    return out


def valor_usd(valor: float, fecha_presentacion: str) -> float:
    """Desde el 3-ene-2023 la columna VALUE se reporta en dólares; antes, en miles de dólares."""
    return valor if fecha_presentacion >= "2023-01-03" else valor * 1000.0


def escala_valor(filas: list[dict], fecha_presentacion: str) -> tuple[float, str | None]:
    """Algunos gestores siguen declarando VALUE en miles después de 2023 (p. ej. Duquesne, 2T-2026). Si el precio
    implícito mediano de sus acciones es < 1 USD, el documento se reescala ×1000 y se anota."""
    precios = sorted(valor_usd(f["valor"], fecha_presentacion) / f["titulos"] for f in filas
                     if not f["put_call"] and f["tipo_titulos"] == "SH" and f["titulos"] > 0 and f["valor"] > 0)
    if len(precios) >= 3 and precios[len(precios) // 2] < 1.0:
        return 1000.0, ("El documento declara VALUE en miles de dólares (precio implícito mediano "
                        f"{precios[len(precios) // 2]:.3f} USD): la terminal lo multiplicó por 1000.")
    return 1.0, None


def agregar_tabla(filas: list[dict], fecha_presentacion: str) -> dict[tuple[str, str], dict]:
    """Suma las filas de un mismo CUSIP (varias discreciones u otros gestores). Las opciones (put/call) van aparte y
    no cuentan como posición en acciones; los montos de principal (PRN, deuda) tampoco."""
    escala, _ = escala_valor(filas, fecha_presentacion)
    out: dict[tuple[str, str], dict] = {}
    for f in filas:
        clave = (f["cusip"], f["put_call"] or ("PRN" if f["tipo_titulos"] == "PRN" else "SH"))
        a = out.setdefault(clave, {"cusip": f["cusip"], "emisor": f["emisor"], "clase": f["clase"], "titulos": 0.0,
                                   "valor_usd": 0.0, "instrumento": clave[1]})
        a["titulos"] += f["titulos"]
        a["valor_usd"] += valor_usd(f["valor"], fecha_presentacion) * escala
    return out
