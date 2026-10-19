"""Asistente dentro de la terminal: resuelve dudas con los datos de la terminal, su documentación y las notas que el
usuario le enseña. Reutiliza el Chatbot del bot de Telegram (Claude si hay credencial, Ollama si hay OLLAMA_URL; si no,
respuestas locales) y la búsqueda BM25 de scripts/indice_contexto.py.

Comandos propios: /nota <texto> (guardar información), /notas (listar), /olvidar <n> (borrar). Los demás comandos
(/plan, /cartera, /estado…) son los del bot. Las notas son datos del usuario, no verificados: se citan como tales y nunca
se tratan como instrucciones. Nada de esto envía órdenes ni da asesoría personalizada.
"""
from __future__ import annotations

import importlib.util
import time
from datetime import UTC, datetime
from pathlib import Path

from . import bot_telegram as bt

RAIZ = Path(__file__).resolve().parents[1]
MAX_NOTA = 4000
MAX_NOTAS = 300
SIN_RESPUESTA = "No tengo una respuesta directa"
_cache: dict = {"t": 0.0, "secciones": None}
_idx = None


def _indice():
    """scripts/indice_contexto.py no es un paquete: se carga una vez por ruta."""
    global _idx
    if _idx is None:
        spec = importlib.util.spec_from_file_location("indice_contexto", RAIZ / "scripts" / "indice_contexto.py")
        _idx = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_idx)
    return _idx


def _secciones() -> list[dict]:
    if _cache["secciones"] is None or time.monotonic() - _cache["t"] > 300:   # la documentación cambia poco
        _cache.update(t=time.monotonic(), secciones=_indice().secciones())
    return _cache["secciones"]


def _tabla(con) -> None:
    con.execute("CREATE TABLE IF NOT EXISTS asistente_notas (id INTEGER PRIMARY KEY, creado_en TEXT NOT NULL, texto TEXT NOT NULL)")


def agregar_nota(con, texto: str) -> dict:
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("escribe el texto de la nota después de /nota")
    if len(texto) > MAX_NOTA:
        raise ValueError(f"la nota admite {MAX_NOTA} caracteres")
    _tabla(con)
    if con.execute("SELECT COUNT(*) FROM asistente_notas").fetchone()[0] >= MAX_NOTAS:
        raise ValueError(f"hay {MAX_NOTAS} notas: borra alguna con /olvidar <n>")
    cur = con.execute("INSERT INTO asistente_notas (creado_en, texto) VALUES (?, ?)", (datetime.now(UTC).isoformat(), texto))
    con.commit()
    return {"id": cur.lastrowid, "texto": texto}


def notas(con) -> list[dict]:
    _tabla(con)
    return [dict(r) for r in con.execute("SELECT id, creado_en, texto FROM asistente_notas ORDER BY id")]


def borrar_nota(con, nid: int) -> bool:
    _tabla(con)
    n = con.execute("DELETE FROM asistente_notas WHERE id=?", (nid,)).rowcount
    con.commit()
    return n > 0


def buscar(con, pregunta: str, maximo: int = 3) -> list[dict]:
    """Fragmentos de la documentación y de las notas más pertinentes (BM25), con su origen."""
    docs = list(_secciones()) + [{"ruta": f"nota #{n['id']}", "linea": 0, "fecha": n["creado_en"][:10], "texto": n["texto"]}
                                 for n in notas(con)]
    return [{"origen": d["ruta"] if d["ruta"].startswith("nota") else f"{d['ruta']}:{d['linea']}", "fecha": d["fecha"],
             "texto": "\n".join(d["texto"].splitlines()[:8])} for _, d in _indice().bm25(pregunta, docs)[:maximo]]


def _texto_fragmentos(frs: list[dict]) -> str:
    if not frs:
        return ("No encontré nada sobre eso en los datos, la documentación ni tus notas. Prueba /plan, /cartera o "
                "/estado, o enséñame algo con /nota <texto>.")
    partes = ["Esto encontré en la documentación y tus notas (texto original, sin resumir):"]
    for f in frs:
        partes.append(f"— {f['origen']} ({f['fecha']}){' · nota tuya, no verificada' if f['origen'].startswith('nota') else ''}\n{f['texto']}")
    return "\n\n".join(partes)


def responder(con, ajustes, texto: str, chatbot: bt.Chatbot) -> dict:
    t = (texto or "").strip()[:MAX_NOTA + 10]
    if not t:
        raise ValueError("escribe una pregunta o un comando")
    cab = t.split()[0].lower()
    if cab == "/nota":
        n = agregar_nota(con, t[len("/nota"):])
        return {"respuesta": f"Guardé la nota #{n['id']}. La usaré como información tuya (no verificada) al responder.",
                "motor": "notas"}
    if cab == "/notas":
        ns = notas(con)
        return {"respuesta": "\n".join(f"#{n['id']} · {n['texto'][:160]}" for n in ns) if ns else "No hay notas. Agrega una con /nota <texto>.",
                "motor": "notas"}
    if cab == "/olvidar":
        try:
            nid = int(t.split()[1].lstrip("#"))
        except (IndexError, ValueError):
            raise ValueError("usa /olvidar <número de nota>") from None
        return {"respuesta": f"Nota #{nid} borrada." if borrar_nota(con, nid) else f"No existe la nota #{nid}.", "motor": "notas"}
    if t.startswith("/"):
        r = bt.atender(con, ajustes, t, chatbot)
        if cab in ("/ayuda", "/help", "/start") or r == bt.AYUDA:
            r += "\n\nEn la terminal además: /nota <texto> para enseñarme algo, /notas para verlas, /olvidar <n> para borrar."
        return {"respuesta": r, "motor": "comando"}
    frs = buscar(con, t)
    motor = chatbot.motor()
    r = chatbot.responder(con, t[:1000], extra={"documentacion_y_notas": frs})
    if r.startswith(SIN_RESPUESTA):
        return {"respuesta": _texto_fragmentos(frs), "motor": "documentacion", "fuentes": frs}
    return {"respuesta": r, "motor": motor, "fuentes": frs}
