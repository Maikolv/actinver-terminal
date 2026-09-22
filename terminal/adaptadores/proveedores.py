"""Adaptadores concretos. Cada uno puede sustituirse sin cambiar el resto del sistema."""
from __future__ import annotations

import csv
import io
from datetime import date

from .base import Adaptador, Barra, ErrorProveedor


class Fred(Adaptador):
    """FRED (Reserva Federal de St. Louis), serie DEXMXUS: pesos por dólar, mediodía NY.
    Descarga CSV pública sin clave; publicación diaria con rezago de varios días."""
    proveedor = "fred"
    tipo_dato = "fx"
    descripcion = "Tipo de cambio USD/MXN de referencia (DEXMXUS), diario con rezago"
    uso_permitido = "Datos públicos; FRED permite descarga. Citar la fuente."
    URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"

    def soporta(self, instr: dict) -> bool:
        return instr.get("id") == "FX:USDMXN"

    def historico(self, instr: dict, desde: date, hasta: date) -> list[Barra]:
        r = self._get(self.URL, params={"id": "DEXMXUS", "cosd": desde.isoformat(), "coed": hasta.isoformat()})
        out = []
        for fila in csv.reader(io.StringIO(r.text)):
            if len(fila) != 2 or not fila[0][:1].isdigit():
                continue
            try:
                v = float(fila[1])
            except ValueError:  # "." = sin dato ese día (festivo)
                continue
            out.append(Barra(fecha=fila[0], cierre=v))
        return out


class Banxico(Adaptador):
    """Banco de México SIE API, serie SF43718 (tipo de cambio FIX). Requiere token gratuito."""
    proveedor = "banxico"
    tipo_dato = "fx"
    requiere_credencial = True
    descripcion = "Tipo de cambio FIX oficial (SF43718)"
    uso_permitido = "API pública con token personal gratuito; respetar límites del SIE."
    URL = "https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF43718/datos/{d}/{h}"

    def soporta(self, instr: dict) -> bool:
        return instr.get("id") == "FX:USDMXN"

    def historico(self, instr: dict, desde: date, hasta: date) -> list[Barra]:
        r = self._get(self.URL.format(d=desde.isoformat(), h=hasta.isoformat()),
                      headers={"Bmx-Token": self.credencial, "Accept": "application/json"})
        datos = r.json()["bmx"]["series"][0].get("datos", [])
        out = []
        for d in datos:
            dd, mm, aa = d["fecha"].split("/")
            try:
                out.append(Barra(fecha=f"{aa}-{mm}-{dd}", cierre=float(d["dato"].replace(",", ""))))
            except ValueError:
                continue
        return out


class Tiingo(Adaptador):
    """Tiingo EOD: cierres diarios de acciones y ETF de EE. UU., con ajuste por dividendos y splits."""
    proveedor = "tiingo"
    tipo_dato = "cierre"
    requiere_credencial = True
    descripcion = "Cierres diarios de EE. UU. (listado de referencia de emisoras del SIC y ETF)"
    uso_permitido = "Plan gratuito para uso personal; sin redistribución. Límites por hora y día."
    URL = "https://api.tiingo.com/tiingo/daily/{t}/prices"

    def soporta(self, instr: dict) -> bool:
        return instr.get("moneda_referencia") == "USD" and bool(instr.get("listado_referencia"))

    def historico(self, instr: dict, desde: date, hasta: date) -> list[Barra]:
        t = instr["listado_referencia"].replace(".", "-").lower()
        r = self._get(self.URL.format(t=t), params={"startDate": desde.isoformat(), "endDate": hasta.isoformat()},
                      headers={"Authorization": f"Token {self.credencial}", "Content-Type": "application/json"})
        out = []
        for d in r.json():
            out.append(Barra(fecha=d["date"][:10], cierre=float(d["close"]), cierre_ajustado=float(d["adjClose"]),
                             volumen=float(d.get("volume") or 0), dividendo=float(d.get("divCash") or 0),
                             factor_split=float(d.get("splitFactor") or 1)))
        return out


class Eodhd(Adaptador):
    """EODHD: cierres diarios de la BMV (sufijo .MX)."""
    proveedor = "eodhd"
    tipo_dato = "cierre"
    requiere_credencial = True
    descripcion = "Cierres diarios de emisoras de la BMV"
    uso_permitido = "Plan gratuito limitado (20 peticiones/día); planes de pago para más cobertura."
    URL = "https://eodhd.com/api/eod/{t}.MX"

    def soporta(self, instr: dict) -> bool:
        return instr.get("mercado_operable") == "BMV" and instr.get("clase") in ("accion", "fibra", "etf")

    def historico(self, instr: dict, desde: date, hasta: date) -> list[Barra]:
        clave = instr["clave"] + (instr.get("serie") or "").replace("*", "").replace(" ", "")
        r = self._get(self.URL.format(t=clave.replace("&", "")),
                      params={"api_token": self.credencial, "fmt": "json", "from": desde.isoformat(),
                              "to": hasta.isoformat()})
        out = []
        for d in r.json():
            if d.get("close") is None:
                continue
            out.append(Barra(fecha=d["date"], cierre=float(d["close"]),
                             cierre_ajustado=float(d.get("adjusted_close") or d["close"]),
                             volumen=float(d.get("volume") or 0)))
        return out


class Archivo(Adaptador):
    """Precios o valor liquidativo (NAV) importados por el usuario desde un CSV validado.
    No hace peticiones de red; la ingesta la realiza el módulo de importación."""
    proveedor = "archivo"
    tipo_dato = "cierre"
    descripcion = "CSV local importado por el usuario (p. ej. NAV de fondos exportado de su casa de bolsa)"
    uso_permitido = "Datos que el propio usuario obtiene legítimamente."

    def soporta(self, instr: dict) -> bool:
        return True

    def historico(self, instr: dict, desde: date, hasta: date) -> list[Barra]:
        raise ErrorProveedor("archivo: los precios se cargan desde la sección Importar")


FX_USDMXN = {"id": "FX:USDMXN", "moneda_referencia": "MXN"}
