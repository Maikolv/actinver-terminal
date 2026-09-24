"""`TradingViewAlertReceiver`: recibe alertas que el participante configura VOLUNTARIAMENTE en TradingView (webhook).

Son EVENTOS («el precio cruzó X»), no una API de precios: no se consultan continuamente ni alimentan la valuación.
Cada evento se valida:
- autenticidad: secreto compartido en el cuerpo (`TRADINGVIEW_WEBHOOK_SECRETO`; TradingView no permite cabeceras
  personalizadas), comparado en tiempo constante; opcionalmente IPs de origen de TradingView;
- símbolo: debe normalizarse a un instrumento del catálogo (y del simulador si se importó); moneda coherente;
- marca temporal: ni futura (> 60 s) ni más antigua que la tolerancia (300 s por defecto);
- duplicados: huella (id de la alerta o símbolo + hora + precio + nombre) única;
- valores: precio finito y positivo; si se aleja > 30 % de la última referencia se acepta como evento «atípico».
El precio recibido se registra con estado de latencia UNKNOWN: TradingView no declara el retraso del dato de la BMV
según el plan del usuario, y `timenow` es la hora de la alerta, no la del evento de mercado.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import secrets
import sqlite3
from datetime import UTC, datetime

import pandas as pd

from . import cotizaciones as cz

TOLERANCIA_S = 300
FUTURO_MAX_S = 60
DESVIO_ATIPICO = 0.30
# IPs de origen publicadas por TradingView para webhooks (verifique la lista vigente en su documentación).
IPS_TRADINGVIEW = {"52.89.214.238", "34.212.75.30", "54.218.53.128", "52.32.178.7"}


class WebhookRechazado(ValueError):
    def __init__(self, motivo: str, codigo: int = 422):
        super().__init__(motivo)
        self.codigo = codigo


class TradingViewAlertReceiver:
    def __init__(self, con: sqlite3.Connection, entorno: dict | None = None, tolerancia_s: int = TOLERANCIA_S,
                 verificar_ip: bool = False):
        self.con = con
        self.env = entorno if entorno is not None else os.environ
        self.tolerancia_s = tolerancia_s
        self.verificar_ip = verificar_ip

    def configurado(self) -> bool:
        return bool(self.env.get("TRADINGVIEW_WEBHOOK_SECRETO"))

    def recibir(self, cuerpo: bytes, ip: str | None = None, ahora: datetime | None = None) -> dict:
        ahora = ahora or datetime.now(UTC)
        if not self.configurado():
            raise WebhookRechazado("Receptor desactivado: defina TRADINGVIEW_WEBHOOK_SECRETO en .env", 503)
        if self.verificar_ip and ip not in IPS_TRADINGVIEW:
            raise WebhookRechazado("IP de origen no pertenece a TradingView", 403)
        try:
            d = json.loads(cuerpo.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise WebhookRechazado("El mensaje de la alerta debe ser JSON (ver docs/proveedores.md)") from None
        if not isinstance(d, dict):
            raise WebhookRechazado("JSON inválido")
        if not secrets.compare_digest(str(d.get("secreto", "")), self.env["TRADINGVIEW_WEBHOOK_SECRETO"]):
            raise WebhookRechazado("Secreto inválido", 401)
        instrumentos = {r["id"]: dict(r) for r in self.con.execute("SELECT * FROM instrumentos")}
        from .clasificacion import InstrumentoNoElegible
        try:
            norm = cz.normalizar_simbolo(str(d.get("simbolo", "")), instrumentos)
        except InstrumentoNoElegible as e:
            raise WebhookRechazado(str(e)) from None
        if not norm:
            raise WebhookRechazado(f"Símbolo fuera del catálogo: {str(d.get('simbolo'))[:40]}")
        sim = {r[0] for r in self.con.execute("SELECT id FROM universo_simulador")}
        if sim and norm["instrumento_id"] not in sim:
            raise WebhookRechazado(f"{norm['instrumento_id']} no está en el catálogo del simulador")
        try:
            precio = float(d.get("precio"))
        except (TypeError, ValueError):
            raise WebhookRechazado("Precio no numérico") from None
        if not math.isfinite(precio) or precio <= 0:
            raise WebhookRechazado("Precio no positivo o no finito")
        moneda = str(d.get("moneda") or norm["moneda"]).upper()
        if moneda != norm["moneda"]:
            raise WebhookRechazado(f"Moneda {moneda} no corresponde a {norm['simbolo_normalizado']} ({norm['moneda']})")
        try:
            hora = pd.Timestamp(str(d.get("hora")))
            hora = hora.tz_localize("UTC") if hora.tzinfo is None else hora.tz_convert("UTC")
        except (ValueError, TypeError):
            raise WebhookRechazado("Hora ausente o inválida (use {{timenow}})") from None
        edad = (pd.Timestamp(ahora).tz_convert("UTC") - hora).total_seconds()
        if edad < -FUTURO_MAX_S:
            raise WebhookRechazado("Marca temporal en el futuro")
        if edad > self.tolerancia_s:
            raise WebhookRechazado(f"Alerta demasiado antigua ({edad:.0f} s > {self.tolerancia_s} s)")
        alerta = str(d.get("alerta") or "")[:120]
        base = d.get("id") or f"{norm['simbolo_normalizado']}|{hora.isoformat()}|{precio:.6f}|{alerta}"
        huella = hashlib.sha256(str(base).encode()).hexdigest()
        if self.con.execute("SELECT 1 FROM eventos_webhook WHERE huella=?", (huella,)).fetchone():
            return {"duplicado": True, "huella": huella[:12]}
        ref = self.con.execute("SELECT cierre FROM precios WHERE instrumento_id=? AND moneda=? ORDER BY fecha DESC LIMIT 1",
                               (norm["instrumento_id"], moneda)).fetchone()
        atipico = bool(ref and ref[0] and abs(precio / ref[0] - 1) > DESVIO_ATIPICO)
        recepcion = datetime.now(UTC).isoformat()
        estado = "atipico" if atipico else "aceptado"
        self.con.execute("INSERT INTO eventos_webhook (huella, recibido_en, simbolo_origen, instrumento_id, precio, moneda, "
                         "hora_evento, alerta, estado, motivo) VALUES (?,?,?,?,?,?,?,?,?,?)",
                         (huella, recepcion, str(d.get("simbolo"))[:40], norm["instrumento_id"], precio, moneda,
                          hora.isoformat(), alerta, estado,
                          f"Se aleja {abs(precio / ref[0] - 1):.0%} de la última referencia" if atipico else ""))
        cz.registrar(self.con, cz.Cotizacion("tradingview_webhook", str(d.get("simbolo"))[:40], norm["simbolo_normalizado"],
                                             norm["instrumento_id"], norm["mercado"], norm["bolsa"], precio, moneda,
                                             hora.isoformat(), recepcion, None, "UNKNOWN",
                                             detalle="Evento de alerta de TradingView; retraso del dato no declarado"))
        self.con.commit()
        return {"duplicado": False, "estado": estado, "instrumento_id": norm["instrumento_id"], "huella": huella[:12]}


def plantilla_mensaje() -> str:
    """Mensaje JSON que el participante pega en la alerta de TradingView (el secreto lo escribe él mismo)."""
    return json.dumps({"secreto": "<TRADINGVIEW_WEBHOOK_SECRETO>", "simbolo": "{{exchange}}:{{ticker}}",
                       "precio": "{{close}}", "hora": "{{timenow}}", "alerta": "<nombre de su alerta>"},
                      ensure_ascii=False, indent=2).replace('"{{close}}"', "{{close}}")
