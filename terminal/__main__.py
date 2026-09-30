"""Línea de comandos: iniciar | actualizar | respaldar | reporte | demo.

  uv run terminal iniciar        # abre la terminal en http://127.0.0.1:8765
  uv run terminal actualizar     # consulta proveedores configurados (respeta límites)
  uv run terminal respaldar      # copia verificada de la base de datos local
  uv run terminal reporte cierre # genera data/reportes/AAAA-MM-DD_cierre.md (preapertura | cierre | semanal)
  uv run terminal telegram       # detecta su chat de Telegram, lo guarda en .env y envía un aviso de prueba
  uv run terminal comparar-modelos  # walk-forward: modelo vigente vs HRP, CVaR, paridad de riesgo
  uv run terminal alpaca         # comprueba las claves de Alpaca (solo datos) y muestra un precio de prueba
  uv run terminal investigar     # experimento walk-forward → validación → prueba y pronósticos (H = 1 y 5)
  uv run terminal cobertura      # verifica cobertura por símbolo y proveedor; escribe docs/cobertura.md
  uv run terminal webhook-secreto  # genera TRADINGVIEW_WEBHOOK_SECRETO en .env (sin mostrarlo completo)
  uv run terminal fondos         # importa la hoja oficial de precios de los fondos Actinver (o --archivo PDF descargado)
  uv run terminal cobertura-twelvedata  # verifica símbolo por símbolo la cobertura BMV de Twelve Data (lista pública)
  uv run terminal claude         # comprueba la credencial de Claude del chatbot de Telegram (una consulta mínima)
  uv run terminal catalogo-simulador  # limita el universo del Reto a lo que muestra su simulador (transcripción del PDF)
  uv run terminal boletas        # boletas del plan del día (o --propuesta CLAVE; --telegram para enviarlas) para captura manual
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


def comparar_modelos(args) -> None:
    from . import comparador_modelos, db
    from .config import cargar_ajustes
    a = cargar_ajustes()
    con = db.conectar()
    db.inicializar(con)
    try:
        res = comparador_modelos.comparar(con, a, {**a["perfil"], "capital": 100000}, args.tipo, args.lente)
    finally:
        con.close()
    if res["estado"] != "calculada":
        sys.exit("; ".join(res["motivos"]))
    for f in res["ranking"]:
        if "error" in f:
            print(f"  {f['modelo']:<26} ERROR {f['error']}")
        else:
            print(f"  {f['modelo']:<26} Sharpe {f['sharpe']:.2f}  rend {f['rend_anual']:+.1%}  vol {f['volatilidad']:.1%}  "
                  f"caída {f['max_caida']:.1%}  giro {f['giro_medio']:.2f}")
    print(res["aviso"] or f"Ganador fuera de muestra: {res['ganador']}")
    print(f"Guardado en {comparador_modelos.guardar(res)}")


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


def investigar(args) -> None:
    import json

    from . import db
    from .config import cargar_ajustes
    from .investigacion import pronosticos
    a = cargar_ajustes()
    con = db.conectar()
    db.inicializar(con, a)
    try:
        for H in args.horizontes:
            r = pronosticos.emitir(con, a.es_demo, H)
            print(json.dumps({k: v for k, v in r.items() if not k.startswith("_")}, ensure_ascii=False, indent=1, default=str))
        from .investigacion import evaluacion
        for H in args.horizontes:
            e = evaluacion.ultimo(con, H, a.es_demo)
            if not e or e.get("estado") != "ok":
                continue
            print(f"\nH={H} · {e['datos']} · cortes {e['cortes']['entrenamiento']} | {e['cortes']['validacion']} | "
                  f"{e['cortes']['prueba']} · embargo {e['cortes']['embargo_sesiones']} · variante {e['variante_elegida']}")
            print(f"{'modelo':32} {'MSE':>10} {'dir.':>6} {'cob80':>6} {'neto':>8} {'rot':>6}")
            for m in e["prueba"]:
                d = m["acierto_direccion"]
                print(f"{m['modelo']:32} {m['mse']:10.6f} {(f'{d:.3f}' if d is not None else '—'):>6} "
                      f"{m['cobertura_intervalo_80']:6.3f} {m['resultado_neto']:8.4f} {m['rotacion_media']:6.3f}")
            print(e["conclusion"] + (" (prueba ya vista: no válida para elegir)" if e.get("prueba_ya_vista") else ""))
    finally:
        con.close()


def fondos(args) -> None:
    """Precios por fondo y serie con la fecha de valuación que declara el propio documento de Actinver."""
    from pathlib import Path
    from . import db, fondos_actinver as fa
    con = db.conectar()
    db.inicializar(con)
    try:
        if args.archivo:
            rep = fa.importar(con, Path(args.archivo).read_bytes(), Path(args.archivo).name)
        else:
            import httpx
            r = httpx.get(fa.URL, timeout=60, follow_redirects=True,
                          headers={"User-Agent": "actinver-terminal/uso-personal (lectura de la hoja publica)"})
            if r.status_code != 200:
                sys.exit(f"No se pudo descargar la hoja (HTTP {r.status_code}); descárguela en actinver.com/fondos y use --archivo.")
            rep = fa.importar(con, r.content, fa.URL)
    except fa.ErrorHoja as e:
        sys.exit(f"Hoja rechazada: {e}")
    print(f"Valuación al {rep['fecha_valuacion']} · {rep['asignados']} fondos con precio · documento sha256 {rep['sha256'][:16]}…")
    for p in rep["precios"]:
        print(f"  {p['id']:<16} {p['precio']:>14,.6f} MXN")
    if rep["sin_serie_en_documento"]:
        print("Sin la serie del universo en el documento (no se asigna por aproximación):", ", ".join(rep["sin_serie_en_documento"]))


def catalogo_simulador(args) -> None:
    """Catálogo operable del simulador a partir de la transcripción de sus capturas (config/pdf_transcripcion.csv).

    Solo secciones «Acciones» y «Fondos» (la sección «ETF's» del PDF repite las acciones: no prueba que haya ETF).
    Sin --confirmar solo muestra la vista previa; con --confirmar reemplaza universo_simulador (queda en auditoría)."""
    import csv
    import io
    from . import db, importar, mercado
    origen = Path(args.transcripcion)
    filas = [r for r in csv.DictReader(origen.open(encoding="utf-8")) if r["seccion_pdf"] in ("Acciones", "Fondos")]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["clave", "tipo", "nombre"])
    vistos: set[str] = set()
    for r in filas:
        clave = f"{r['clave_pdf']} {r['serie_pdf']}".strip()
        if clave not in vistos:
            vistos.add(clave)
            w.writerow([clave, "fondo" if r["seccion_pdf"] == "Fondos" else "accion", f"{args.fuente}"])
    con = db.conectar()
    db.inicializar(con)
    ins = mercado.instrumentos(con)
    rep = importar.importar(con, buf.getvalue().encode("utf-8"), "catalogo_simulador.csv", "universo", ins,
                            confirmar=args.confirmar)
    print(f"{rep['filas']} claves del simulador · {rep['aceptables']} coinciden con el universo · {rep['rechazadas']} rechazadas")
    for d in rep["detalle"]:
        if d["estado"] == "rechazada":
            print(f"  línea {d['linea']}:", "; ".join(d["errores"]))
    fuera = sorted(i for i, v in ins.items() if v["estado"] == "activo" and i not in set(rep.get("ids", [])))
    if fuera:
        print("Activos del universo que NO aparecen en el simulador (se excluyen de las propuestas del Reto):", ", ".join(fuera))
    print("Catálogo aplicado." if args.confirmar else "Vista previa: repita con --confirmar para aplicarlo.")


def cobertura_twelvedata(_args) -> None:
    """Compara el universo BMV con la lista pública de Twelve Data (sin clave) y guarda los símbolos exactos verificados."""
    import json
    from datetime import date
    import httpx
    from . import db, mercado
    from .adaptadores.proveedores import TwelveData
    r = httpx.get("https://api.twelvedata.com/stocks", params={"exchange": "BMV"}, timeout=60)
    lista = {x["symbol"]: x for x in (r.json().get("data") or [])} if r.status_code == 200 else {}
    etf = httpx.get("https://api.twelvedata.com/etfs", params={"exchange": "BMV"}, timeout=60)
    if etf.status_code == 200:
        lista.update({x["symbol"]: x for x in (etf.json().get("data") or [])})
    if not lista:
        sys.exit(f"No se pudo leer la lista pública de Twelve Data (HTTP {r.status_code}).")
    con = db.conectar()
    ins = mercado.instrumentos(con)
    bmv = sorted(i for i, v in ins.items() if v["estado"] == "activo" and v["mercado_operable"] == "BMV" and v["clase"] in ("accion", "fibra", "etf"))
    verificados, filas = [], []
    for i in bmv:
        s = TwelveData.simbolo(ins[i])
        ok = s in lista and lista[s].get("currency") == "MXN"
        verificados += [i] if ok else []
        filas.append((i, s, "sí" if ok else "no"))
    TwelveData.MAPA.parent.mkdir(parents=True, exist_ok=True)
    TwelveData.MAPA.write_text(json.dumps({"fuente": "https://api.twelvedata.com/stocks?exchange=BMV (+ /etfs)",
                                           "verificado_en": date.today().isoformat(), "plan_requerido": "Pro (XMEX, EOD)",
                                           "verificados": verificados}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(verificados)} de {len(bmv)} instrumentos BMV con símbolo exacto en Twelve Data (plan Pro, cierre diario).")
    for i, s, ok in filas:
        if ok == "no":
            print(f"  sin cobertura verificada: {i} (símbolo {s})")


def claude(_args) -> None:
    """Una consulta mínima para confirmar que el chatbot puede usar Claude. La clave nunca se muestra."""
    from .config import _cargar_env_local
    from .bot_telegram import credencial_claude
    _cargar_env_local()
    if not credencial_claude():
        sys.exit("Falta ANTHROPIC_API_KEY en .env (créela en console.anthropic.com, sección API Keys). No se muestra ni se registra.")
    try:
        import anthropic
    except ImportError:
        sys.exit("Falta el SDK: uv add anthropic")
    try:
        r = anthropic.Anthropic(max_retries=1, timeout=60.0).messages.create(
            model="claude-opus-5-5", max_tokens=200, output_config={"effort": "low"},
            messages=[{"role": "user", "content": "Responde solo: OK"}])
    except anthropic.AuthenticationError:
        sys.exit("Claude rechazó la clave (HTTP 401): revise ANTHROPIC_API_KEY en .env.")
    except anthropic.PermissionDeniedError:
        sys.exit("La clave no tiene permiso para este modelo (HTTP 403).")
    except anthropic.APIStatusError as e:
        sys.exit(f"Claude respondió HTTP {e.status_code}; intente más tarde o revise su saldo en console.anthropic.com.")
    except anthropic.APIConnectionError:
        sys.exit("Sin conexión con la API de Claude.")
    texto = "".join(b.text for b in r.content if b.type == "text").strip()
    print(f"Claude activo ({r.model}): respondió «{texto[:40]}». Reinicie la terminal para que el bot lo use.")


def _hora_mx(iso: str) -> str:
    import pandas as pd
    return pd.Timestamp(iso).tz_convert("America/Mexico_City").strftime("%d-%m %H:%M") + " (CDMX)"


def boletas(args) -> None:
    """Imprime las boletas generadas. Ninguna se envía: cada orden se captura a mano en el simulador del Reto."""
    from . import boleta, db
    from .config import cargar_ajustes
    con = db.conectar()
    db.inicializar(con)
    try:
        r = boleta.generar(con, cargar_ajustes(), args.propuesta)
    except ValueError as e:
        sys.exit(f"No se generaron boletas: {e}")
    res, filas = r[0], r[1:]
    print(f"Boletas de «{res['nombre_propuesta']}» ({res['puntuacion']:.1f}/100): {res['numero_ordenes']} órdenes, "
          f"{res['por_investigar']} por investigar; costo estimado ${res['costo_total']:,.2f}."
          + (f" Se reemplazaron {res['reemplazadas']} boletas anteriores." if res.get("reemplazadas") else ""))
    for b in filas:
        lado = (b.get("lado") or "—").upper()
        cant = f"{int(b['cantidad']):,}" if b.get("cantidad") else "—"
        lim = f"${b['precio_limite']:,.2f}" if b.get("precio_limite") else "precio del portal"
        r = b.get("referencia_condicional")
        if r:  # sin cotización confiable: guía condicional, no orden
            lado, cant = f"({r['lado_sugerido'][:6]})", f"≈{r['titulos_aprox']:,}"
            lim = f"solo si el portal está en ${r['precio_min']:,.2f}–${r['precio_max']:,.2f} ({r['fuente']} {r['fecha']})"
        print(f"  #{b['id']:>4}  {b['tipo']:<18} {lado:<7} {cant:>7} {b.get('emisora_serie') or b['instrumento_id']:<12} "
              f"límite {lim}  vence {_hora_mx(b['caduca_en'])}")
    print("Solo informativo: capture cada orden a mano en el simulador del Reto. La terminal no envía órdenes.")
    if args.telegram:
        from .config import cargar_ajustes as _c
        print("Telegram:", boleta.enviar_telegram(con, _c())["resultado"].get("telegram"))


def cobertura(_args) -> None:
    from . import cotizaciones, db
    from .config import RAIZ, cargar_ajustes
    a = cargar_ajustes()
    con = db.conectar()
    db.inicializar(con, a)
    try:
        provs = cotizaciones.construir(con, a.es_demo)
        cotizaciones.verificar_cobertura(con, provs, cotizaciones.catalogo(con))
        tabla = cotizaciones.tabla_cobertura(con, provs)
        lat = cotizaciones.latencias_medidas(con)
        importado = bool(con.execute("SELECT 1 FROM universo_simulador LIMIT 1").fetchone())
        estados = [p.estado() for p in provs.values()]
        from . import registro
        registro.poblar_correspondencia(con)
        mapa = [dict(r) for r in con.execute("SELECT * FROM correspondencia_simbolos ORDER BY mercado, instrumento_id")]
        ultimos = {r[0]: (r[1], r[2]) for r in con.execute(
            "SELECT instrumento_id, MAX(fecha), proveedor FROM precios WHERE proveedor <> 'demo_sintetico' GROUP BY instrumento_id")}
        cob = {}
        for r in con.execute("SELECT instrumento_id, proveedor, estado, latencia_mediana_s FROM cobertura WHERE estado='verificado'"):
            cob.setdefault(r[0], []).append(f"{r[1]} ({r[3]} s)")
    finally:
        con.close()
    filas_m = ["# Matriz por instrumento", "",
               f"Generada por `uv run terminal cobertura` el {datetime.now():%Y-%m-%d %H:%M}. ISIN: no disponible en las fuentes "
               "usadas (se llenará con el catálogo del simulador o un proveedor licenciado). Un listado SIC en MXN y su acción de "
               "origen en USD son series distintas.", "",
               "| Símbolo Actinver | Emisor | Serie | ISIN | MIC · mercado | Moneda | Símbolo BMV | Origen (MIC · moneda) | "
               "Proveedor verificado (latencia) | Último dato válido | Elegibilidad / causa de discrepancia |",
               "|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in mapa:
        u = ultimos.get(m["instrumento_id"])
        origen = f"{m['simbolo_origen']} ({m['mic_origen']} · {m['moneda_origen']})" if m["simbolo_origen"] else "—"
        causa = m["elegible"] + ("" if cob.get(m["instrumento_id"]) else "; SIN PRECIO CONFIABLE: ningún proveedor BMV verificado")
        filas_m.append(f"| {m['simbolo_actinver']} | {(m['emisor'] or '').strip()[:40]} | {m['serie'] or ''} | {m['isin'] or 'n/d'} | "
                       f"{m['mic']} · {m['mercado']} | {m['moneda']} | {m['simbolo_bmv'] or '—'} | {origen} | "
                       f"{', '.join(cob.get(m['instrumento_id'], [])) or 'ninguno'} | "
                       f"{(u[0] + ' (' + u[1] + ')') if u and u[0] else '—'} | {causa} |")
    (RAIZ / "docs" / "instrument-matrix.md").write_text(chr(10).join(filas_m) + chr(10), encoding="utf-8")
    lineas = ["# Cobertura por símbolo y proveedor", "",
              f"Generado por `uv run terminal cobertura` el {datetime.now():%Y-%m-%d %H:%M} (hora local).",
              "Estados: `verificado` (consulta real con instrumento, moneda y mercado exactos), `pendiente` (falta contrato, "
              "especificación o credencial), `no_cubierto`, `no_coincide`, `no_aplica`, `sin_verificar`.",
              "", ("Catálogo: **lista del simulador importada**." if importado else
                   "Catálogo: **la lista del simulador aún no se importa**; se usa el universo verificado (PDF + fuentes oficiales)."),
              "", "## Proveedores", ""]
    for e in estados:
        lineas.append(f"- **{e['proveedor']}** — {e['descripcion']}. " + (
            "Configurado." if e["configurado"] else "Pendiente: " + "; ".join(e["pendientes"])))
    lineas += ["", "## Latencia medida", ""]
    lineas += [f"- {x['proveedor']}: mediana {x['mediana_s']} s, p90 {x['p90_s']} s (n={x['n']})" for x in lat] or [
        "- Sin cotizaciones registradas: ninguna latencia verificada todavía."]
    cols = ["instrumento_id", "clave_operable", "mercado", "moneda"] + cotizaciones.PRIORIDAD
    lineas += ["", "## Tabla", "", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lineas += ["| " + " | ".join(str(f.get(c) or "") for c in cols) + " |" for f in tabla]
    (RAIZ / "docs" / "cobertura.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    verificados = sum(1 for f in tabla for c in cotizaciones.PRIORIDAD if f[c] == "verificado")
    print(f"{len(tabla)} instrumentos; {verificados} coberturas verificadas. Detalle en docs/cobertura.md")


def webhook_secreto(_args) -> None:
    import secrets as _s
    valor = _s.token_urlsafe(32)
    _fijar_env("TRADINGVIEW_WEBHOOK_SECRETO", valor)
    print(f"Secreto guardado en .env (termina en …{valor[-4:]}). Cópielo desde .env al mensaje de su alerta de TradingView.")


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
    c = sub.add_parser("comparar-modelos", help="walk-forward de HRP, CVaR, paridad de riesgo y el modelo vigente")
    c.add_argument("--tipo", choices=["acciones", "mixta"], default="acciones")
    c.add_argument("--lente", choices=["ajuste", "rendimiento"], default="ajuste")
    c.set_defaults(fn=comparar_modelos)
    inv = sub.add_parser("investigar", help="experimento sin fuga de información y pronósticos (FUTURO)")
    inv.add_argument("--horizontes", type=int, nargs="+", default=[1, 5])
    inv.set_defaults(fn=investigar)
    sub.add_parser("cobertura", help="verifica cobertura por símbolo y proveedor (docs/cobertura.md)").set_defaults(fn=cobertura)
    sub.add_parser("webhook-secreto", help="genera el secreto del webhook de TradingView en .env").set_defaults(fn=webhook_secreto)
    fo = sub.add_parser("fondos", help="importa la hoja oficial de precios de los fondos Actinver (PDF)")
    fo.add_argument("--archivo", help="PDF descargado a mano de actinver.com/fondos (si se omite, se descarga)")
    fo.set_defaults(fn=fondos)
    sub.add_parser("cobertura-twelvedata", help="verifica la cobertura BMV de Twelve Data símbolo por símbolo").set_defaults(
        fn=cobertura_twelvedata)
    sub.add_parser("claude", help="comprueba la credencial de Claude del chatbot (una consulta mínima)").set_defaults(fn=claude)
    cs = sub.add_parser("catalogo-simulador", help="limita el universo del Reto a lo que muestra su simulador")
    cs.add_argument("--transcripcion", default="config/pdf_transcripcion.csv")
    cs.add_argument("--fuente", default="Datos Actinver.pdf (capturas del simulador, 22-sep-2026)")
    cs.add_argument("--confirmar", action="store_true")
    cs.set_defaults(fn=catalogo_simulador)
    bo = sub.add_parser("boletas", help="genera las boletas del plan del día (captura manual en el simulador)")
    bo.add_argument("--propuesta", default="plan_del_dia", help="clave de la propuesta (por omisión, la del plan del día)")
    bo.add_argument("--telegram", action="store_true", help="además, enviarlas por Telegram")
    bo.set_defaults(fn=boletas)
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
