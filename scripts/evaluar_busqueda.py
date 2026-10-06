"""¿Hace falta recuperación semántica? Mide la búsqueda existente (scripts/indice_contexto.py, léxica) con preguntas
redactadas como las reales de las sesiones con el usuario. Cada una trae el archivo que la responde.

Métrica: acierto@3 = el archivo esperado aparece entre los 3 primeros fragmentos. Si es alto, no se agrega una capa
semántica (más memoria y complejidad) sin una mejora demostrable.

Uso: uv run python scripts/evaluar_busqueda.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import indice_contexto as ic  # noqa: E402

PREGUNTAS = [
    ("¿Me penalizan por comprar ETF o fondos?", ["docs/actinver-rules.md", "config/reto.yaml"]),
    ("¿Cuál es la comisión por operación en el Reto?", ["docs/actinver-rules.md", "config/reto.yaml"]),
    ("¿Cuántas emisoras mínimo debo tener en el portafolio?", ["docs/actinver-rules.md", "config/reto.yaml"]),
    ("¿Qué decidí sobre el criterio del plan: mayor ganancia o puntuación?", ["docs/decisiones.md"]),
    ("¿Por qué el plan dice que no cambie nada frente a mantener la cartera?", ["docs/decisiones.md"]),
    ("¿Qué fuente de precios BMV con licencia me recomiendas contratar?", ["docs/bmv-licencia.md"]),
    ("¿La probabilidad de subida está calibrada?", ["docs/pronostico-reto.md", "docs/model-card.md"]),
    ("¿Qué es la alternativa C con NVIDIA?", ["docs/alternativa-nvda-2026-10-05.md"]),
    ("¿A qué hora abre y cierra la bolsa durante el Reto?", ["docs/actinver-rules.md", "config/reto.yaml"]),
    ("¿El precio del SIC es en tiempo real?", ["docs/fuentes.md", "docs/guia-rapida.md"]),
    ("¿Cómo copio mi portafolio del portal a la terminal?", ["docs/guia-rapida.md"]),
    ("¿Cuándo termina la competencia del Reto?", ["docs/actinver-rules.md", "config/reto.yaml"]),
    ("¿Qué hace la terminal con las compras de insiders y los 13F?", ["docs/movimientos-publicos.md"]),
    ("¿Por qué la validación fuera de muestra tenía tan pocas sesiones?", ["docs/historia-y-horizonte.md"]),
    ("¿Qué límites tiene el mandato de autonomía?", ["docs/mandato-autonomia.md", "docs/mandato-autonomia.txt"]),
]


def evaluar(nombre: str, buscar_fn) -> dict:
    filas, aciertos, t0 = [], 0, time.perf_counter()
    for q, esperados in PREGUNTAS:
        rutas = []
        for r in buscar_fn(q):  # top-3 archivos distintos
            if r not in rutas:
                rutas.append(r)
            if len(rutas) == 3:
                break
        ok = any(e in rutas for e in esperados)
        aciertos += ok
        filas.append({"pregunta": q, "esperado": esperados, "top3": rutas, "acierto": ok})
    seg = (time.perf_counter() - t0) / len(PREGUNTAS)
    print(f"{nombre:<34} acierto@3 {aciertos}/{len(PREGUNTAS)} · {seg:.2f} s por consulta", flush=True)
    return {"metodo": nombre, "acierto_a_3": aciertos / len(PREGUNTAS), "segundos_por_consulta": round(seg, 3), "filas": filas}


def semantica(docs: list[dict], modelo: str = "intfloat/multilingual-e5-small"):
    """Recuperación semántica pequeña: embeddings e5 (prefijos «query:»/«passage:»), similitud coseno."""
    from sentence_transformers import SentenceTransformer
    t = time.perf_counter()
    m = SentenceTransformer(modelo, device="cpu")
    emb = m.encode(["passage: " + d["texto"][:1500] for d in docs], batch_size=16, normalize_embeddings=True)
    preparar = time.perf_counter() - t

    def buscar(q):
        v = m.encode(["query: " + q], normalize_embeddings=True)[0]
        orden = (emb @ v).argsort()[::-1]
        return [docs[i]["ruta"] for i in orden[:30]]
    return buscar, preparar


def main() -> None:
    ic.construir()
    if ic.CACHE.exists():
        ic.CACHE.unlink()  # medir sin caché
    filas, aciertos = [], 0
    for q, esperados in PREGUNTAS:
        t = time.perf_counter()
        r = ic.buscar_conteo(q, maximo=3)
        seg = time.perf_counter() - t
        rutas = [f["ruta"].rsplit(":", 1)[0] for f in r["fragmentos"]]
        ok = any(e in rutas for e in esperados)
        aciertos += ok
        filas.append({"pregunta": q, "esperado": esperados, "top3": rutas, "acierto": ok, "segundos": round(seg, 2)})
        print(("✔" if ok else "✘"), q, "→", rutas, f"({seg:.1f} s)")
    docs = ic.secciones()
    metodos = [{"metodo": "conteo de términos (anterior)", "acierto_a_3": aciertos / len(PREGUNTAS), "filas": filas},
               evaluar("BM25 por sección (vigente)", lambda q: [d["ruta"] for _, d in ic.bm25(q, docs)[:30]])]
    if "--semantica" in sys.argv:
        buscar_sem, preparar = semantica(docs)
        r = evaluar("semántica e5-small", buscar_sem)
        r["segundos_indexar"] = round(preparar, 1)
        metodos.append(r)
    res = {"n": len(PREGUNTAS), "secciones": len(docs), "metodos": metodos}
    (RAIZ / "docs" / "evidencia" / "busqueda_eval.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"conteo anterior: acierto@3 = {aciertos}/{len(PREGUNTAS)}")


if __name__ == "__main__":
    main()
