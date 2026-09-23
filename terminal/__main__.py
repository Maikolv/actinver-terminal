"""Línea de comandos: iniciar | actualizar | respaldar | reporte | demo.

  uv run terminal iniciar        # abre la terminal en http://127.0.0.1:8765
  uv run terminal actualizar     # consulta proveedores configurados (respeta límites)
  uv run terminal respaldar      # copia verificada de la base de datos local
  uv run terminal reporte cierre # genera data/reportes/AAAA-MM-DD_cierre.md (preapertura | cierre | semanal)
  uv run terminal telegram       # detecta su chat de Telegram, lo guarda en .env y envía un aviso de prueba
  uv run terminal alpaca         # comprueba las claves de Alpaca (solo datos) y muestra un precio de prueba
"""
from __future__ import annotations

import argparse
import logging
import logging.handlers
import os
import sqlite3
import sys
import webbrowser
from datetime import datetime
from pathlib import Path


def _logs() -> None:
    from .config import DATA_DIR
    d = Path(DATA_DIR) / "logs"
    d.mkdir(parents=True, exist_ok=True)
    h = logging.handlers.RotatingFileHandler(d / "terminal.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[h, logging.StreamHandler()])
    logging.getLogger("httpx").setLevel(logging.WARNING)  # nunca registrar URLs con credenciales


def iniciar(args) -> None:
    import uvicorn

    from .config import cargar_ajustes
    a = cargar_ajustes()
    host = a["app"]["host"]
    if host not in ("127.0.0.1", "localhost", "::1"):
        sys.exit("Por seguridad la terminal solo escucha en la máquina local (host 127.0.0.1). "
                 "Vea docs/12-seguridad.md antes de exponerla en red.")
    url = f"http://127.0.0.1:{a['app']['puerto']}/"
    print(f"Terminal disponible en {url}  (modo: {a.modo}). Ctrl+C para detener.")
    if not args.sin_navegador:
        webbrowser.open(url)
    uvicorn.run("terminal.app:app", host=host, port=int(a["app"]["puerto"]), log_level="warning",
                server_header=False, proxy_headers=False)


def actualizar(_args) -> None:
    from . import db, ingesta
    from .config import cargar_ajustes
    a = cargar_ajustes()
    con = db.conectar()
    db.inicializar(con)
    print(ingesta.actualizar_todo(con, a))


def respaldar(args) -> None:
    from . import db
    origen = db.ruta_db()
    destino_dir = origen.parent / "respaldos"
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / f"terminal-{datetime.now():%Y%m%d-%H%M%S}.db"
    src = sqlite3.connect(origen)
    dst = sqlite3.connect(destino)
    with dst:
        src.backup(dst)
    ok = dst.execute("PRAGMA integrity_check").fetchone()[0]
    n = dst.execute("SELECT COUNT(*) FROM transacciones").fetchone()[0]
    src.close()
    dst.close()
    if ok != "ok":
        destino.unlink(missing_ok=True)
        sys.exit(f"Respaldo inválido ({ok}); no se conservó")
    copias = sorted(destino_dir.glob("terminal-*.db"))
    for viejo in copias[: max(len(copias) - args.conservar, 0)]:
        viejo.unlink()
    print(f"Respaldo verificado: {destino} (integridad ok, {n} operaciones)")


def reporte(args) -> None:
    from . import db, reportes
    from .config import cargar_ajustes
    con = db.conectar()
    db.inicializar(con)
    try:
        print(reportes.ejecutar(con, cargar_ajustes(), args.tipo, actualizar=not args.sin_actualizar))
    finally:
        con.close()


def _fijar_env(clave: str, valor: str) -> None:
    """Escribe o reemplaza una línea CLAVE=valor en .env (no versionado) sin tocar las demás."""
    from .config import RAIZ
    ruta = RAIZ / ".env"
    lineas = ruta.read_text(encoding="utf-8").splitlines() if ruta.exists() else []
    nuevas = [ln for ln in lineas if not ln.strip().startswith(f"{clave}=")]
    nuevas.append(f"{clave}={valor}")
    ruta.write_text("\n".join(nuevas) + "\n", encoding="utf-8")


def telegram(_args) -> None:
    from . import notificador
    from .config import cargar_ajustes
    cargar_ajustes()  # carga .env
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        sys.exit("Falta TELEGRAM_BOT_TOKEN en .env.\n"
                 "1) En Telegram abra @BotFather y envíe /newbot; copie el token que le da.\n"
                 "2) Péguelo en .env como TELEGRAM_BOT_TOKEN=...\n"
                 "3) Abra su bot nuevo, envíele «hola» y vuelva a ejecutar: uv run terminal telegram")
    bot, chats = notificador.telegram_chats(token)
    if not bot:
        sys.exit("Telegram rechazó el token (revise TELEGRAM_BOT_TOKEN en .env). El token no se muestra por seguridad.")
    print(f"Bot: @{bot}")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not chat:
        if not chats:
            sys.exit(f"Aún no hay mensajes. Abra https://t.me/{bot}, pulse Iniciar o envíe «hola» y repita el comando.")
        if len(chats) > 1:
            print("Varios chats le escribieron al bot:")
            for c in chats:
                print(f"  {c['id']}  {c['nombre']}")
            sys.exit("Copie el id del suyo en .env como TELEGRAM_CHAT_ID=... y repita el comando.")
        chat = str(chats[0]["id"])
        _fijar_env("TELEGRAM_CHAT_ID", chat)
        os.environ["TELEGRAM_CHAT_ID"] = chat
        print(f"Chat detectado ({chats[0]['nombre']}) y guardado en .env como TELEGRAM_CHAT_ID.")
    r = notificador.telegram("Actinver Terminal — Telegram conectado",
                             "Desde ahora recibirá aquí las alertas con su motivo y la acción sugerida "
                             "(en horario de la BMV). Solo informativo: no se envían órdenes.")
    print("Mensaje de prueba enviado." if r == "enviada" else f"No se pudo enviar el mensaje de prueba ({r}).")
    if r == "enviada":
        print("Reinicie la terminal (Ctrl+C y start.bat) para que el servidor use la configuración nueva.")


def alpaca(_args) -> None:
    from datetime import date, timedelta

    from . import db
    from .adaptadores import Alpaca, ErrorProveedor
    from .config import cargar_ajustes, credencial, secreto
    a = cargar_ajustes()
    if not (credencial("alpaca") and secreto("alpaca")):
        sys.exit("Faltan ALPACA_API_KEY_ID y ALPACA_API_SECRET_KEY en .env.\n"
                 "Cree una cuenta gratuita en https://alpaca.markets, entre al panel de Paper Trading "
                 "(dinero ficticio) y genere las claves en «API Keys». La terminal solo usa la API de datos.")
    con = db.conectar()
    db.inicializar(con)
    ad = Alpaca(con, a["proveedores"].get("alpaca", {}), credencial("alpaca"), secreto=secreto("alpaca"))
    try:
        barras = ad.historico({"listado_referencia": "AAPL"}, date.today() - timedelta(days=10), date.today())
    except ErrorProveedor as e:
        sys.exit(f"Alpaca no respondió bien: {e}")
    finally:
        con.close()
    if not barras:
        sys.exit("Alpaca respondió sin datos para AAPL.")
    b = barras[-1]
    print(f"Claves válidas. AAPL cierre {b.fecha}: {b.cierre:.2f} USD ({len(barras)} sesiones recibidas).")
    print("Al iniciar la terminal, en horario de EE. UU. se abrirá el flujo en vivo (IEX, hasta 30 símbolos).")


def main() -> None:
    p = argparse.ArgumentParser(prog="terminal", description="Terminal local de análisis de portafolios")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("iniciar", help="inicia el servidor local y abre el navegador")
    s.add_argument("--sin-navegador", action="store_true")
    s.set_defaults(fn=iniciar)
    sub.add_parser("actualizar", help="actualiza datos de mercado").set_defaults(fn=actualizar)
    r = sub.add_parser("respaldar", help="crea un respaldo verificado de la base local")
    r.add_argument("--conservar", type=int, default=14)
    r.set_defaults(fn=respaldar)
    g = sub.add_parser("reporte", help="genera un reporte en Markdown (preapertura, cierre o semanal)")
    g.add_argument("tipo", choices=["preapertura", "cierre", "semanal"])
    g.add_argument("--sin-actualizar", action="store_true", help="no consulta proveedores antes de reportar")
    g.set_defaults(fn=reporte)
    sub.add_parser("telegram", help="configura y prueba los avisos por Telegram").set_defaults(fn=telegram)
    sub.add_parser("alpaca", help="comprueba las claves de Alpaca (solo datos de mercado)").set_defaults(fn=alpaca)
    d = sub.add_parser("demo", help="inicia con datos SINTÉTICOS etiquetados (sin credenciales)")
    d.add_argument("--sin-navegador", action="store_true")
    d.set_defaults(fn=iniciar)
    args = p.parse_args()
    if args.cmd == "demo":  # base separada: los datos sintéticos nunca se mezclan con los reales
        # Se fija antes de importar .config, que lee estas variables al cargarse.
        os.environ["TERMINAL_MODO"] = "demo"  # la base se separa sola en data/demo (config.data_dir)
    _logs()
    args.fn(args)


if __name__ == "__main__":
    main()
