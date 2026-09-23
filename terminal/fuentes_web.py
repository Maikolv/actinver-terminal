"""Fuentes de contexto (no de precios): calendario macro, noticias por emisora e insiders.

Vías legales usadas:
  * ForexFactory: feed de exportación del calendario (nfs.faireconomy.media), el mismo que enlaza su sitio.
    Se consulta como máximo una vez por hora (el feed cambia poco y penaliza consultas frecuentes).
  * Seeking Alpha: feed RSS público por emisora (/api/sa/combined/<TICKER>.xml; no bloqueado en robots.txt).
    Solo titulares y enlaces; el artículo se lee en su sitio.
  * SEC EDGAR (Formulario 4): fuente oficial de operaciones de insiders. La SEC exige una cabecera User-Agent con
    contacto: variable SEC_USER_AGENT en .env. Sin ella, la fuente queda «requiere configuración».
Ninguna de estas fuentes genera órdenes: alimentan alertas y contexto.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime

import httpx

from .adaptadores.base import Adaptador, ErrorProveedor, SinCredencial
from .db import ahora, transaccion

# ---------------------------------------------------------------------------------------------------------------
# Clasificación de titulares (léxico transparente; opcionalmente LLM local vía Ollama si OLLAMA_URL está definido)
ALTO_IMPACTO = re.compile(r"\b(earnings (beat|miss)\w*|(beats?|miss(es)?) (estimates|expectations)|guidance|downgrad\w*|upgrad\w*|"
                          r"fda|sec\b|lawsuit|investigation|probe|merger|acqui\w+|"
                          r"bankrupt\w*|chapter 11|ceo|resign\w*|recall|dividend (cut|suspend\w*)|delist\w*|halt\w*|"
                          r"fraud|restat\w*|layoffs?|default|tariff\w*|sanction\w*)\b", re.I)
NEGATIVO = re.compile(r"\b(downgrad\w*|miss\w*|cut\w*|lawsuit|probe|investigation|recall|bankrupt\w*|plunge\w*|slump\w*|"
                      r"fraud|delist\w*|halt\w*|warn\w*|layoffs?|default|falls?|drops?|sinks?|weak\w*|loss(es)?|"
                      r"illusor\w*|overvalued|bubble|risks?|concerns?|slow\w*|decline\w*)\b", re.I)
POSITIVO = re.compile(r"\b(upgrad\w*|beats?|raises?|record|buyback|approv\w*|surg\w*|jumps?|soars?|strong|growth|outperform\w*)\b", re.I)


def clasificar_titular(titulo: str) -> dict:
    neg, pos = len(NEGATIVO.findall(titulo)), len(POSITIVO.findall(titulo))
    sent = 0.0 if neg == pos else (1.0 if pos > neg else -1.0)
    impacto = "alto" if ALTO_IMPACTO.search(titulo) else "normal"
    motivo = "léxico: " + ", ".join(sorted({m.group(0).lower() for m in ALTO_IMPACTO.finditer(titulo)})) if impacto == "alto" else ""
    res = {"impacto": impacto, "sentimiento": sent, "motivo": motivo}
    url = os.environ.get("OLLAMA_URL")
    if url and impacto == "alto":
        try:  # LLM local: el titular no sale del equipo
            r = httpx.post(f"{url.rstrip('/')}/api/generate", timeout=20, json={
                "model": os.environ.get("OLLAMA_MODELO", "llama3.2"), "stream": False, "format": "json",
                "prompt": "Clasifica el sentimiento del titular financiero como número entre -1 y 1 y explica en 10 "
                          f"palabras. Responde JSON {{\"sentimiento\": n, \"motivo\": \"...\"}}. Titular: {titulo}"})
            d = json.loads(r.json()["response"])
            res.update(sentimiento=max(-1.0, min(1.0, float(d["sentimiento"]))), motivo=f"LLM local: {d['motivo'][:120]}")
        except Exception:  # noqa: BLE001 - si el LLM local falla se conserva el léxico
            pass
    return res


# ---------------------------------------------------------------------------------------------------------------
class ForexFactory(Adaptador):
    proveedor = "forexfactory"
    tipo_dato = "calendario"
    descripcion = "Calendario económico semanal (impacto alto/medio/bajo) — feed oficial de exportación"
    uso_permitido = "Feed de exportación enlazado por ForexFactory; como máximo 1 consulta por hora"
    URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

    def eventos(self) -> list[dict]:
        r = self._get(self.URL)
        out = []
        for e in r.json():
            ident = hashlib.sha1(f"{e.get('title')}|{e.get('country')}|{e.get('date')}".encode()).hexdigest()[:16]
            out.append({"id": ident, "fecha": e.get("date"), "pais": e.get("country"), "titulo": e.get("title"),
                        "impacto": e.get("impact"), "pronostico": e.get("forecast"), "previo": e.get("previous")})
        return out


class SeekingAlphaRSS(Adaptador):
    proveedor = "seekingalpha_rss"
    tipo_dato = "noticias"
    descripcion = "Titulares por emisora (RSS público) para emisoras de EE. UU. en cartera"
    uso_permitido = "RSS público para uso personal; solo titular y enlace; sin acceso tras inicio de sesión"
    URL = "https://seekingalpha.com/api/sa/combined/{t}.xml"

    def titulares(self, ticker: str) -> list[dict]:
        r = self._get(self.URL.format(t=ticker.replace(".", "-").upper()))
        raiz = ET.fromstring(r.content)
        out = []
        for it in raiz.iter("item"):
            titulo = (it.findtext("title") or "").strip()
            enlace = (it.findtext("link") or "").strip()
            pub = it.findtext("pubDate")
            try:
                fecha = parsedate_to_datetime(pub).astimezone(UTC).isoformat() if pub else None
            except (TypeError, ValueError):
                fecha = None
            if titulo and enlace.startswith("https://"):
                out.append({"titulo": titulo[:300], "enlace": enlace[:500], "publicado": fecha})
        return out


class SecEdgar(Adaptador):
    proveedor = "sec_edgar"
    tipo_dato = "insiders"
    requiere_credencial = True
    descripcion = "Formulario 4 (operaciones de insiders) de emisoras de EE. UU. en cartera"
    uso_permitido = "API oficial; exige User-Agent con contacto y ≤ 10 peticiones/s"
    TICKERS = "https://www.sec.gov/files/company_tickers.json"
    SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"

    def _h(self) -> dict:
        return {"User-Agent": self.credencial, "Accept-Encoding": "gzip, deflate"}

    def cik(self, ticker: str) -> int | None:
        if not hasattr(self, "_mapa"):
            r = self._get(self.TICKERS, headers=self._h())
            self._mapa = {v["ticker"].upper(): int(v["cik_str"]) for v in r.json().values()}
        return self._mapa.get(ticker.replace(".", "-").upper())

    def formularios4(self, ticker: str, dias: int = 30, maximo: int = 8) -> list[dict]:
        if not self.credencial:
            raise SinCredencial("sec_edgar: defina SEC_USER_AGENT (nombre y correo de contacto) en .env")
        cik = self.cik(ticker)
        if cik is None:
            return []
        rec = self._get(self.SUBMISSIONS.format(cik=cik), headers=self._h()).json()["filings"]["recent"]
        limite = (datetime.now(UTC) - timedelta(days=dias)).date().isoformat()
        out = []
        for forma, acc, doc, fecha in zip(rec["form"], rec["accessionNumber"], rec["primaryDocument"], rec["filingDate"]):
            if forma != "4" or fecha < limite or len(out) >= maximo:
                continue
            xml_doc = doc.split("/")[-1]
            url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{xml_doc}"
            time.sleep(0.15)  # respeta el límite de la SEC
            try:
                out += self._parsear_f4(self._get(url, headers=self._h()).content, url, fecha)
            except (ErrorProveedor, ET.ParseError):
                continue
        return out

    @staticmethod
    def _parsear_f4(contenido: bytes, url: str, fecha_presentacion: str) -> list[dict]:
        raiz = ET.fromstring(contenido)
        nombre = raiz.findtext(".//reportingOwner/reportingOwnerId/rptOwnerName") or ""
        rel = raiz.find(".//reportingOwner/reportingOwnerRelationship")
        cargo = ""
        if rel is not None:
            cargo = rel.findtext("officerTitle") or ("Director" if (rel.findtext("isDirector") or "") in ("1", "true") else "")
        out = []
        for t in raiz.findall(".//nonDerivativeTable/nonDerivativeTransaction"):
            codigo = t.findtext("transactionCoding/transactionCode") or ""
            acc = float(t.findtext("transactionAmounts/transactionShares/value") or 0)
            precio = float(t.findtext("transactionAmounts/transactionPricePerShare/value") or 0)
            fecha = t.findtext("transactionDate/value") or fecha_presentacion
            out.append({"fecha": fecha[:10], "nombre": nombre[:120], "cargo": cargo[:80], "codigo": codigo,
                        "acciones": acc, "precio": precio, "valor": acc * precio, "enlace": url})
        return out


# ---------------------------------------------------------------------------------------------------------------
# Funciones de actualización (guardan en la base; toleran fallos de fuente)
def _reciente(con, tabla: str, fuente: str, minutos: int, filtro: str = "", params: tuple = ()) -> bool:
    fila = con.execute(f"SELECT MAX(obtenido_en) FROM {tabla} WHERE fuente=? {filtro}", (fuente, *params)).fetchone()  # noqa: S608
    if not fila or not fila[0]:
        return False
    return datetime.fromisoformat(fila[0]) > datetime.now(UTC) - timedelta(minutes=minutos)


def actualizar_macro(con: sqlite3.Connection, ajustes: dict, cliente=None, forzar: bool = False) -> dict:
    a = ForexFactory(con, ajustes.get("forexfactory", {}), cliente=cliente)
    if not a.configurado():
        return {"estado": "desactivado"}
    if not forzar and _reciente(con, "eventos_macro", "forexfactory", 60):
        return {"estado": "al_dia"}
    try:
        ev = a.eventos()
    except ErrorProveedor as e:
        return {"estado": "error", "mensaje": str(e)}
    ts = ahora()
    with transaccion(con):
        con.executemany("INSERT OR REPLACE INTO eventos_macro (id, fecha, pais, titulo, impacto, pronostico, previo, fuente, obtenido_en) VALUES (?,?,?,?,?,?,?,?,?)",
                        [(e["id"], e["fecha"], e["pais"], e["titulo"], e["impacto"], e["pronostico"], e["previo"],
                          "forexfactory", ts) for e in ev])
    return {"estado": "ok", "registros": len(ev)}


def actualizar_noticias(con: sqlite3.Connection, ajustes: dict, instrumentos: list[dict], cliente=None) -> dict:
    a = SeekingAlphaRSS(con, ajustes.get("seekingalpha_rss", {}), cliente=cliente)
    if not a.configurado():
        return {"estado": "desactivado"}
    n, errores = 0, []
    for ins in instrumentos:
        if ins.get("moneda_referencia") != "USD" or not ins.get("listado_referencia"):
            continue  # el feed cubre emisoras de EE. UU. (emisoras del SIC)
        if _reciente(con, "noticias", "seekingalpha_rss", 30, "AND instrumento_id=?", (ins["id"],)):
            continue
        try:
            items = a.titulares(ins["listado_referencia"])
        except ErrorProveedor as e:
            errores.append(f"{ins['id']}: {e}")
            continue
        ts = ahora()
        filas = []
        for it in items[:20]:
            c = clasificar_titular(it["titulo"])
            ident = hashlib.sha1(it["enlace"].encode()).hexdigest()[:16]
            filas.append((ident, ins["id"], it["titulo"], it["enlace"], it["publicado"], "seekingalpha_rss",
                          c["impacto"], c["sentimiento"], c["motivo"], ts))
        with transaccion(con):
            con.executemany("INSERT OR REPLACE INTO noticias (id, instrumento_id, titulo, enlace, publicado, fuente, impacto, sentimiento, motivo, obtenido_en) VALUES (?,?,?,?,?,?,?,?,?,?)", filas)
        n += len(filas)
    return {"estado": "ok" if not errores else "parcial", "registros": n, "errores": errores[:5]}


def actualizar_insiders(con: sqlite3.Connection, ajustes: dict, instrumentos: list[dict], cliente=None) -> dict:
    a = SecEdgar(con, ajustes.get("sec_edgar", {}), os.environ.get("SEC_USER_AGENT") or None, cliente=cliente)
    if not a.configurado():
        return {"estado": "requiere_configuracion", "mensaje": "Defina SEC_USER_AGENT en .env"}
    n, errores = 0, []
    for ins in instrumentos:
        if ins.get("moneda_referencia") != "USD" or not ins.get("listado_referencia") or ins.get("clase") == "etf":
            continue
        if _reciente(con, "insiders", "sec_edgar", 12 * 60, "AND instrumento_id=?", (ins["id"],)):
            continue
        try:
            ops = a.formularios4(ins["listado_referencia"])
        except ErrorProveedor as e:
            errores.append(f"{ins['id']}: {e}")
            continue
        ts = ahora()
        with transaccion(con):
            con.executemany("INSERT OR REPLACE INTO insiders (id, instrumento_id, fecha, nombre, cargo, codigo, acciones, precio, valor, enlace, fuente, obtenido_en) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", [
                (hashlib.sha1(f"{o['enlace']}|{o['fecha']}|{o['acciones']}|{o['codigo']}".encode()).hexdigest()[:16],
                 ins["id"], o["fecha"], o["nombre"], o["cargo"], o["codigo"], o["acciones"], o["precio"], o["valor"],
                 o["enlace"], "sec_edgar", ts) for o in ops])
        n += len(ops)
    return {"estado": "ok" if not errores else "parcial", "registros": n, "errores": errores[:5]}
