"""Índice de contexto para ahorrar tokens (política en docs/token-budget.md).

- `construir`: índice de archivos del proyecto (código, docs, config) con sha256, fecha, líneas y títulos/funciones.
- `buscar "consulta"`: devuelve SOLO los fragmentos mínimos pertinentes (ruta:línea + ≤ 8 líneas), ordenados por
  coincidencias; nunca resume ni recorta cifras, monedas, horas, fuentes o reglas: cita el texto original.
- Caché de respuestas en _renders/contexto_cache.json, invalidada automáticamente si cambia el hash de algún archivo
  citado. Reporta tokens estimados (≈ caracteres / 4) de la respuesta frente a leer los archivos completos.

Uso:
  uv run python scripts/indice_contexto.py construir
  uv run python scripts/indice_contexto.py buscar "regla del 50 %" [--max 5]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
INDICE = RAIZ / "_renders" / "contexto_indice.json"
CACHE = RAIZ / "_renders" / "contexto_cache.json"
INCLUIR = ("terminal/**/*.py", "tests/*.py", "scripts/*.py", "docs/**/*.md", "config/*.toml", "config/*.yaml", "web/**/*.js",
           "web/*.html", "README.md", "CLAUDE.md", "CHANGELOG.md")
EXCLUIR = {"evaluar_busqueda.py"}  # contiene las preguntas de evaluación: indexarlo contaminaría la medición
MARCAS = re.compile(r"^\s*(#{1,4} .+|def \w+|class \w+|async function \w+|function \w+|\[[\w.]+\])")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def construir() -> dict:
    archivos = {}
    for patron in INCLUIR:
        for p in RAIZ.glob(patron):
            if not p.is_file() or "_renders" in p.parts or p.name in EXCLUIR:
                continue
            texto = p.read_text(encoding="utf-8", errors="ignore")
            lineas = texto.splitlines()
            rel = p.relative_to(RAIZ).as_posix()
            archivos[rel] = {"sha256": _sha(p), "modificado": datetime.fromtimestamp(p.stat().st_mtime, UTC).isoformat(timespec="seconds"),
                             "lineas": len(lineas), "caracteres": len(texto),
                             "marcas": [{"linea": i + 1, "texto": l.strip()[:100]} for i, l in enumerate(lineas) if MARCAS.match(l)][:200]}
    idx = {"creado": datetime.now(UTC).isoformat(timespec="seconds"), "archivos": archivos}
    INDICE.parent.mkdir(exist_ok=True)
    INDICE.write_text(json.dumps(idx, ensure_ascii=False), encoding="utf-8")
    return idx


def _cargar() -> dict:
    if not INDICE.exists():
        return construir()
    idx = json.loads(INDICE.read_text(encoding="utf-8"))
    cambiados = [r for r, a in idx["archivos"].items() if not (RAIZ / r).exists() or _sha(RAIZ / r) != a["sha256"]]
    return construir() if cambiados else idx


def buscar_conteo(consulta: str, maximo: int = 5, contexto: int = 3) -> dict:
    """Búsqueda anterior (conteo de términos por línea): 4/15 en scripts/evaluar_busqueda.py. Se conserva para comparar."""
    idx = _cargar()
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    clave = f"conteo|{consulta}|{maximo}"
    c = cache.get(clave)
    if c and all((RAIZ / r).exists() and _sha(RAIZ / r) == h for r, h in c["hashes"].items()):
        return {**c["respuesta"], "cache": True}
    terminos = [t for t in re.findall(r"\w+", consulta.lower()) if len(t) > 2]
    hallazgos = []
    for rel in idx["archivos"]:
        lineas = (RAIZ / rel).read_text(encoding="utf-8", errors="ignore").splitlines()
        for i, l in enumerate(lineas):
            b = l.lower()
            puntos = sum(t in b for t in terminos)
            if puntos:
                hallazgos.append((puntos, rel, i))
    hallazgos.sort(key=lambda x: (-x[0], x[1], x[2]))
    fragmentos, usados = [], set()
    for puntos, rel, i in hallazgos:
        if len(fragmentos) >= maximo or any(r == rel and abs(i - j) <= contexto * 2 for r, j in usados):
            continue
        lineas = (RAIZ / rel).read_text(encoding="utf-8", errors="ignore").splitlines()
        a, b = max(i - contexto, 0), min(i + contexto + 1, len(lineas))
        fragmentos.append({"ruta": f"{rel}:{i + 1}", "coincidencias": puntos, "texto": "\n".join(lineas[a:b])})
        usados.add((rel, i))
    citados = {f["ruta"].rsplit(":", 1)[0] for f in fragmentos}
    tokens_resp = sum(len(f["texto"]) for f in fragmentos) // 4
    tokens_completos = sum(idx["archivos"][r]["caracteres"] for r in citados) // 4
    resp = {"consulta": consulta, "fragmentos": fragmentos, "tokens_estimados": tokens_resp,
            "tokens_si_se_leyeran_completos": tokens_completos, "cache": False}
    cache[clave] = {"respuesta": resp, "hashes": {r: idx["archivos"][r]["sha256"] for r in citados}}
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return resp


VACIAS = set("""a al algo ante como con cual cuál cuando cuándo de del desde donde el ella en entre es esta este esto
fue ha hay la las le lo los me mi mis más no o para pero por qué que se si sí sin sobre su sus te tiene tu un una uno y ya
""".split())  # palabras vacías genéricas del español
DOCUMENTOS = ("docs/**/*.md", "config/*.yaml", "README.md", "CLAUDE.md", "CHANGELOG.md")


def _tokens(t: str) -> list[str]:
    import unicodedata
    t = unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()
    return [w for w in re.findall(r"[a-z0-9&+]+", t) if len(w) > 1 and w not in VACIAS]


def secciones() -> list[dict]:
    """Fragmentos de la documentación por encabezado (≤ 1,500 caracteres), con archivo, línea y fecha del archivo."""
    out = []
    for patron in DOCUMENTOS:
        for p in sorted(RAIZ.glob(patron)):
            if not p.is_file():
                continue
            lineas = p.read_text(encoding="utf-8", errors="ignore").splitlines()
            fecha = datetime.fromtimestamp(p.stat().st_mtime, UTC).date().isoformat()
            ini, buf = 0, []
            for i, l in enumerate(lineas + ["# fin"]):
                if (re.match(r"^#{1,4} ", l) or sum(map(len, buf)) > 1500) and buf:
                    out.append({"ruta": p.relative_to(RAIZ).as_posix(), "linea": ini + 1, "fecha": fecha, "texto": "\n".join(buf)})
                    ini, buf = i, []
                buf.append(l)
    return out


def bm25(consulta: str, docs: list[dict], k1: float = 1.5, b: float = 0.75) -> list[tuple[float, dict]]:
    import math
    from collections import Counter
    toks = [Counter(_tokens(d["texto"])) for d in docs]
    largo = [sum(t.values()) for t in toks]
    prom = sum(largo) / max(len(largo), 1)
    df = Counter(w for t in toks for w in t)
    q = _tokens(consulta)
    puntos = [sum(math.log(1 + (len(docs) - df[w] + 0.5) / (df[w] + 0.5)) * t[w] * (k1 + 1) / (t[w] + k1 * (1 - b + b * n / prom))
                  for w in q if w in t) for t, n in zip(toks, largo, strict=True)]
    return sorted(((s, d) for s, d in zip(puntos, docs, strict=True) if s > 0), key=lambda x: -x[0])


def buscar(consulta: str, maximo: int = 5, contexto: int = 3) -> dict:
    """BM25 por sección de la documentación (13/15 frente a 4/15 del conteo en scripts/evaluar_busqueda.py).
    Cita archivo:línea y fecha; el texto se cita tal cual (máx. 8 líneas por fragmento)."""
    fragmentos = []
    for s, d in bm25(consulta, secciones())[:maximo]:
        lineas = d["texto"].splitlines()
        fragmentos.append({"ruta": f"{d['ruta']}:{d['linea']}", "fecha": d["fecha"], "coincidencias": round(s, 2),
                           "texto": "\n".join(lineas[:8])})
    citados = {f["ruta"].rsplit(":", 1)[0] for f in fragmentos}
    return {"consulta": consulta, "fragmentos": fragmentos, "tokens_estimados": sum(len(f["texto"]) for f in fragmentos) // 4,
            "tokens_si_se_leyeran_completos": sum(len((RAIZ / r).read_text(encoding="utf-8", errors="ignore")) for r in citados) // 4,
            "cache": False}


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("construir")
    b = sub.add_parser("buscar")
    b.add_argument("consulta")
    b.add_argument("--max", type=int, default=5)
    a = p.parse_args()
    if a.cmd == "construir":
        idx = construir()
        print(f"{len(idx['archivos'])} archivos indexados en {INDICE.relative_to(RAIZ)}")
    else:
        r = buscar(a.consulta, a.max)
        sys.stdout.reconfigure(encoding="utf-8")
        for f in r["fragmentos"]:
            print(f"--- {f['ruta']} ({f.get('fecha', 'sin fecha')}, puntaje {f['coincidencias']})\n{f['texto']}")
        print(f"\n≈{r['tokens_estimados']} tokens (vs ≈{r['tokens_si_se_leyeran_completos']} leyendo los archivos completos)"
              f"{' · desde caché' if r['cache'] else ''}")


if __name__ == "__main__":
    main()
