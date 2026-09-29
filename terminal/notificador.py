"""Canales de notificación. Solo envían si el usuario los activa y configura (.env); nunca incluyen credenciales."""
from __future__ import annotations

import base64
import logging
import os
import smtplib
import subprocess
import sys
from datetime import datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo
from xml.sax.saxutils import escape

import httpx

log = logging.getLogger("terminal.notificador")
APP_ID = r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"


def escritorio(titulo: str, texto: str) -> str:
    """Notificación nativa de Windows (toast) sin dependencias. El contenido viaja en base64 (sin inyección)."""
    if sys.platform != "win32":
        return "no_disponible"
    xml = (f"<toast><visual><binding template='ToastGeneric'><text>{escape(titulo[:120])}</text>"
           f"<text>{escape(texto[:300])}</text></binding></visual></toast>")
    b64 = base64.b64encode(xml.encode("utf-8")).decode()
    script = (
        "$ErrorActionPreference='Stop';"
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null;"
        "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null;"
        f"$x=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{b64}'));"
        "$d=New-Object Windows.Data.Xml.Dom.XmlDocument; $d.LoadXml($x);"
        f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{APP_ID}')"
        ".Show([Windows.UI.Notifications.ToastNotification]::new($d))"
    )
    cod = base64.b64encode(script.encode("utf-16-le")).decode()
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", cod],
                           capture_output=True, timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return "enviada" if r.returncode == 0 else "error"
    except (OSError, subprocess.TimeoutExpired):
        return "error"


def correo(titulo: str, texto: str) -> str:
    host, destino = os.environ.get("SMTP_HOST"), os.environ.get("ALERTAS_CORREO_DESTINO")
    if not host or not destino:
        return "no_configurado"
    m = EmailMessage()
    m["Subject"], m["From"], m["To"] = titulo[:150], os.environ.get("SMTP_USER", destino), destino
    m.set_content(texto[:4000])
    try:
        with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587")), timeout=20) as s:
            s.starttls()
            if os.environ.get("SMTP_USER"):
                s.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASS", ""))
            s.send_message(m)
        return "enviada"
    except (OSError, smtplib.SMTPException):
        return "error"


ICONOS = {"critica": "🔴", "aviso": "🟠", "info": "🔵"}


def detalle(alertas: list[dict]) -> str:
    """Texto completo para canales móviles: motivo y acción sugerida de cada alerta (máx. 5)."""
    partes = []
    for a in alertas[:5]:
        linea = f"{ICONOS.get(a.get('severidad'), '•')} {a.get('titulo', '')}"
        if a.get("motivo"):
            linea += f"\n{a['motivo']}"
        if a.get("accion"):
            linea += f"\n→ {a['accion']}"
        pie = []
        if a.get("ts"):
            try:
                pie.append("detectada " + datetime.fromisoformat(a["ts"]).astimezone(ZoneInfo("America/Mexico_City"))
                           .strftime("%d-%m-%Y %H:%M") + " (CDMX)")
            except ValueError:
                pass
        if a.get("fuente"):
            pie.append(f"fuente: {a['fuente']}")
        if pie:
            linea += "\n" + " · ".join(pie)
        partes.append(linea)
    if len(alertas) > 5:
        partes.append(f"… y {len(alertas) - 5} más en la terminal.")
    partes.append("Solo informativo: revise y simule en la terminal; las órdenes se capturan a mano en el simulador.")
    return "\n\n".join(partes)


def configurados() -> dict:
    """Qué canales tienen sus variables en .env (sin exponer valores)."""
    return {"escritorio": sys.platform == "win32",
            "telegram": bool(os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID")),
            "correo": bool(os.environ.get("SMTP_HOST") and os.environ.get("ALERTAS_CORREO_DESTINO"))}


def telegram(titulo: str, texto: str) -> str:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return "no_configurado"
    try:
        r = httpx.post(f"https://api.telegram.org/bot{token}/sendMessage", timeout=20,
                       data={"chat_id": chat, "text": f"{titulo}\n{texto}"[:4000]})
        return "enviada" if r.status_code == 200 else "error"
    except httpx.HTTPError:
        return "error"  # el mensaje de error no se registra: la URL contiene el token


def enviar(titulo: str, texto: str, cfg: dict, detalle: str | None = None) -> dict:
    """El escritorio recibe el resumen; correo y Telegram, el detalle completo (motivo y acción)."""
    res = {}
    if cfg.get("notificar_escritorio", True):
        res["escritorio"] = escritorio(titulo, texto)
    if cfg.get("notificar_correo"):
        res["correo"] = correo(titulo, detalle or texto)
    if cfg.get("notificar_telegram"):
        res["telegram"] = telegram(titulo, detalle or texto)
    return res


# --- configuración asistida de Telegram (comando `terminal telegram`) -------------------------------------------
def telegram_chats(token: str) -> tuple[str | None, list[dict]]:
    """Nombre del bot y chats que le han escrito. El token solo viaja a api.telegram.org."""
    try:
        yo = httpx.get(f"https://api.telegram.org/bot{token}/getMe", timeout=20)
        if yo.status_code != 200:
            return None, []
        act = httpx.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=20).json().get("result") or []
    except (httpx.HTTPError, ValueError):
        return None, []  # el mensaje de error no se muestra: la URL contiene el token
    chats = {}
    for u in act:
        m = u.get("message") or u.get("my_chat_member") or {}
        c = m.get("chat") or {}
        if c.get("id") is not None:
            chats[c["id"]] = {"id": c["id"], "nombre": c.get("title") or c.get("first_name") or c.get("username") or ""}
    return yo.json()["result"].get("username"), list(chats.values())
