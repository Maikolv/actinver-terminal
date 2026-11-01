"""APIs oficiales para contexto de investigación. No escriben precios ni emiten órdenes."""
from __future__ import annotations

import math
import time
from datetime import UTC, datetime

import httpx

from .adaptadores.base import Adaptador, ErrorProveedor


def numero(valor):
    try:
        n = float(valor)
    except (TypeError, ValueError):
        return None
    return n if math.isfinite(n) else None


def observacion(serie, periodo, valor, unidad, titulo, simbolo="", texto="", hora_fuente=None):
    return {"serie": serie, "periodo": periodo, "valor": numero(valor), "unidad": unidad,
            "titulo": titulo, "simbolo": simbolo, "texto": texto, "hora_fuente": hora_fuente}


class ContextoAPI(Adaptador):
    requiere_credencial = True

    def json(self, url, params=None, headers=None):
        r = self._get(url, params=params, headers=headers, intentos=1)
        try:
            datos = r.json()
        except ValueError:
            raise ErrorProveedor("La fuente no devolvió JSON válido") from None
        if not isinstance(datos, dict):
            raise ErrorProveedor("Formato de respuesta no reconocido")
        return datos

    def cerrar(self):
        if self._cliente is not None:
            self._cliente.close()


class FredMacro(ContextoAPI):
    proveedor = "fred_macro"
    SERIES = {
        "DGS10": ("%", "Tasa del Tesoro de EE. UU. a 10 años"),
        "DGS2": ("%", "Tasa del Tesoro de EE. UU. a 2 años"),
        "FEDFUNDS": ("%", "Tasa efectiva de fondos federales"),
        "INDPRO": ("índice 2017=100", "Producción industrial de EE. UU."),
    }

    def consultar(self, ahora):
        out = []
        for serie, (unidad, titulo) in self.SERIES.items():
            datos = self.json("https://api.stlouisfed.org/fred/series/observations", {
                "series_id": serie, "api_key": self.credencial, "file_type": "json", "sort_order": "desc",
                "limit": 24, "observation_end": ahora.date().isoformat(),
            })
            if "error_code" in datos or "observations" not in datos:
                raise ErrorProveedor("FRED no entregó observaciones")
            out += [observacion(serie, o["date"], o.get("value"), unidad, titulo)
                    for o in datos["observations"] if numero(o.get("value")) is not None]
        return out


class AlphaVantage(ContextoAPI):
    proveedor = "alpha_vantage"
    # OVERVIEW requiere suscripción premium. INCOME_STATEMENT respondió con una clave gratuita el 12-oct-2026.
    METRICAS = {"totalRevenue": ("Ingresos", "USD"), "netIncome": ("Beneficio neto", "USD"),
                "operatingIncome": ("Beneficio operativo", "USD")}

    def consultar(self, ahora):
        """Un símbolo por petición, con pausa entre ellas (el plan gratuito limita la ráfaga). Guarda los símbolos que
        respondan: un aviso de límite en uno ya no anula a los demás. Si ninguno responde, propaga el primer error."""
        out, errores = [], []
        simbolos = self.ajustes.get("simbolos", ["MU", "AMD", "NVDA", "XOM"])
        pausa = float(self.ajustes.get("pausa_s", 1.2))
        for i, simbolo in enumerate(simbolos):
            if i and pausa > 0:
                time.sleep(pausa)
            try:
                out += self._simbolo(simbolo)
            except ErrorProveedor as e:
                errores.append(e)
                if "límite" in str(e):
                    break  # cupo o ráfaga agotados: no gastar más peticiones en esta ventana
        if not out and errores:
            raise errores[0]
        return out

    def _simbolo(self, simbolo):
        out = []
        datos = self.json("https://www.alphavantage.co/query", {
            "function": "INCOME_STATEMENT", "symbol": simbolo, "apikey": self.credencial,
        })
        if any(k in datos for k in ("Information", "Note")):
            raise ErrorProveedor("Alpha Vantage: límite de peticiones o función no incluida en el plan")
        if "Error Message" in datos:
            raise ErrorProveedor("Alpha Vantage: símbolo no disponible")
        if datos.get("symbol") != simbolo:
            raise ErrorProveedor("Alpha Vantage no confirmó el símbolo solicitado")
        informes = datos.get("annualReports") or []
        if not informes or not isinstance(informes[0], dict):
            raise ErrorProveedor("Alpha Vantage no entregó estados financieros anuales")
        informe = informes[0]
        periodo = informe.get("fiscalDateEnding")
        if not isinstance(periodo, str) or len(periodo) != 10:
            raise ErrorProveedor("Alpha Vantage no informó el período fiscal")
        moneda = informe.get("reportedCurrency") or "moneda no indicada"
        nota = f"Informe anual terminado el {periodo}; moneda reportada: {moneda}. No es cotización ni dato TTM."
        out += [observacion(k, periodo, informe.get(k), unidad if moneda == "USD" else moneda,
                            titulo, simbolo, nota)
                for k, (titulo, unidad) in self.METRICAS.items() if numero(informe.get(k)) is not None]
        ingresos = numero(informe.get("totalRevenue"))
        for campo, serie, titulo in (("netIncome", "net_margin", "Margen neto anual"),
                                     ("operatingIncome", "operating_margin", "Margen operativo anual")):
            valor = numero(informe.get(campo))
            if ingresos and ingresos > 0 and valor is not None:
                out.append(observacion(serie, periodo, valor / ingresos, "fracción", titulo, simbolo, nota))
        return out


class CoinGecko(ContextoAPI):
    proveedor = "coingecko"

    def consultar(self, ahora):
        datos = self.json("https://api.coingecko.com/api/v3/simple/price", {
            "ids": "bitcoin,ethereum", "vs_currencies": "usd", "include_market_cap": "true",
            "include_24hr_change": "true", "include_last_updated_at": "true",
        }, {"x-cg-demo-api-key": self.credencial})
        out = []
        for moneda, simbolo in (("bitcoin", "BTC"), ("ethereum", "ETH")):
            fila = datos.get(moneda) or {}
            try:
                hora = datetime.fromtimestamp(int(fila["last_updated_at"]), UTC)
            except (KeyError, TypeError, ValueError, OverflowError, OSError):
                raise ErrorProveedor("CoinGecko no informó la hora del dato") from None
            if hora > ahora:
                raise ErrorProveedor("CoinGecko devolvió una hora futura")
            for campo, unidad, titulo in (("usd", "USD", "Referencia cripto"), ("usd_24h_change", "%", "Cambio de 24 horas"),
                                         ("usd_market_cap", "USD", "Capitalización cripto")):
                if numero(fila.get(campo)) is not None:
                    out.append(observacion(campo, hora.date().isoformat(), fila[campo], unidad, titulo, simbolo,
                                           "Solo contexto; no elegible para el Reto. No es precio BMV/SIC.", hora.isoformat()))
        return out


class EIA(ContextoAPI):
    proveedor = "eia"
    SERIES = {"PET.RWTC.D": ("WTI", "USD/barril", "Petróleo WTI"),
              "PET.RBRTE.D": ("BRENT", "USD/barril", "Petróleo Brent"),
              "PET.WCESTUS1.W": ("CRUDE_STOCKS", "miles de barriles", "Existencias comerciales de crudo de EE. UU.")}

    def consultar(self, ahora):
        out = []
        for sid, (serie, unidad, titulo) in self.SERIES.items():
            datos = self.json("https://api.eia.gov/v2/seriesid/" + sid, {
                "api_key": self.credencial, "length": 30, "sort[0][column]": "period", "sort[0][direction]": "desc",
            })
            filas = (datos.get("response") or {}).get("data")
            if not isinstance(filas, list):
                raise ErrorProveedor("EIA no entregó la serie solicitada")
            out += [observacion(serie, f["period"], f.get("value"), f.get("unit") or unidad, titulo,
                                texto="Referencia energética; no es precio de XOM.")
                    for f in filas if numero(f.get("value")) is not None]
        return out


class BLS(ContextoAPI):
    proveedor = "bls"
    requiere_credencial = False
    SERIES = {"CUSR0000SA0": ("índice 1982-84=100", "CPI general desestacionalizado"),
              "LNS14000000": ("%", "Tasa de desempleo de EE. UU."),
              "CES0000000001": ("miles de empleos", "Nóminas no agrícolas de EE. UU.")}

    def consultar(self, ahora):
        cuerpo = {"seriesid": list(self.SERIES), "startyear": str(ahora.year - 2), "endyear": str(ahora.year)}
        if self.credencial:
            cuerpo["registrationkey"] = self.credencial
        self._consumir()
        try:
            r = self.cliente.post("https://api.bls.gov/publicAPI/v2/timeseries/data/", json=cuerpo)
        except httpx.HTTPError:
            raise ErrorProveedor("BLS: error de conexión") from None
        if r.status_code != 200:
            raise ErrorProveedor(f"BLS: HTTP {r.status_code}")
        try:
            datos = r.json()
        except ValueError:
            raise ErrorProveedor("BLS: respuesta no reconocida") from None
        if not isinstance(datos, dict) or datos.get("status") != "REQUEST_SUCCEEDED":
            raise ErrorProveedor("BLS: petición rechazada o cupo agotado")
        out = []
        vistas = set()
        for fila in (datos.get("Results") or {}).get("series", []):
            sid = fila.get("seriesID")
            if sid not in self.SERIES:
                continue
            vistas.add(sid)
            unidad, titulo = self.SERIES[sid]
            for o in fila.get("data", []):
                p = o.get("period", "")
                if not (len(p) == 3 and p.startswith("M") and p[1:].isdigit() and 1 <= int(p[1:]) <= 12):
                    continue  # M13 = promedio anual, no un mes
                if numero(o.get("value")) is None:
                    continue
                periodo = f"{o['year']}-{p[1:]}"
                notas = "; ".join(str(n.get("text", "")) for n in o.get("footnotes", []) if n.get("text"))
                out.append(observacion(sid, periodo, o["value"], unidad, titulo, texto=notas))
        if vistas != set(self.SERIES):
            raise ErrorProveedor("BLS: cobertura incompleta de las series solicitadas")
        # Solo comparación descriptiva de dos observaciones obtenidas ahora, no sorpresa frente a consenso.
        cpi = {o["periodo"]: o["valor"] for o in out if o["serie"] == "CUSR0000SA0"}
        for periodo, valor in cpi.items():
            anterior = cpi.get(f"{int(periodo[:4])-1}{periodo[4:]}")
            if anterior and anterior > 0:
                out.append(observacion("CPI_YOY", periodo, (valor/anterior - 1)*100, "%", "Cambio interanual del CPI",
                                       texto="Calculado con CPI desestacionalizado descargado hoy; puede revisarse."))
        return out


CONECTORES = {"alpha_vantage": AlphaVantage, "fred_macro": FredMacro, "coingecko": CoinGecko, "eia": EIA, "bls": BLS}
