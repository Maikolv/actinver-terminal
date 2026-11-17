"""Historial único de versiones (como data/versiones.json de COATL).

`docs/versiones.json` es la fuente. De ella salen, sin perder texto:
- `CHANGELOG.md` (texto completo de cada entrada, tal cual);
- `docs/VERSIONES.md` (tabla: versión, fecha, commit, título y cifras de referencia).

Uso:
  uv run python scripts/versiones.py importar   # una sola vez: CHANGELOG.md → docs/versiones.json
  uv run python scripts/versiones.py generar    # docs/versiones.json → CHANGELOG.md y docs/VERSIONES.md
Nueva entrada: agréguela al inicio de "versiones" en el JSON y ejecute «generar».
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FUENTE = RAIZ / "docs" / "versiones.json"
CHANGELOG = RAIZ / "CHANGELOG.md"
RESUMEN = RAIZ / "docs" / "VERSIONES.md"
ENCABEZADO = re.compile(r"^## (.+)$", re.M)


def importar(texto: str) -> dict:
    """Parte el CHANGELOG en preámbulo + entradas; cada entrada guarda su texto exacto."""
    marcas = list(ENCABEZADO.finditer(texto))
    preambulo = texto[: marcas[0].start()] if marcas else texto
    versiones = []
    for i, m in enumerate(marcas):
        fin = marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)
        titulo = m.group(1).strip()
        fecha, _, resto = titulo.partition(" — ")
        versiones.append({"version": f"{len(marcas) - i}", "fecha": fecha.strip(), "titulo": resto.strip() or titulo,
                          "commit": None, "cifras": {}, "texto": texto[m.start():fin]})
    return {"preambulo": preambulo, "versiones": versiones}


def changelog(datos: dict) -> str:
    return datos["preambulo"] + "".join(v["texto"] for v in datos["versiones"])


def resumen(datos: dict) -> str:
    filas = ["# Versiones", "", "Generado por `scripts/versiones.py` desde `docs/versiones.json`; no lo edite a mano.", "",
             "| Versión | Fecha | Commit | Cambios | Cifras de referencia |", "|---|---|---|---|---|"]
    for v in datos["versiones"]:
        cifras = " · ".join(f"{k}: {x}" for k, x in (v.get("cifras") or {}).items()) or "—"
        filas.append(f"| {v['version']} | {v['fecha']} | {v.get('commit') or '—'} | {v['titulo']} | {cifras} |")
    return "\n".join(filas) + "\n"


def main(orden: str) -> None:
    if orden == "importar":
        if FUENTE.exists():
            sys.exit(f"{FUENTE.name} ya existe: edítelo y use «generar».")
        FUENTE.write_text(json.dumps(importar(CHANGELOG.read_bytes().decode("utf-8")), ensure_ascii=False, indent=1) + "\n",
                          encoding="utf-8")
    datos = json.loads(FUENTE.read_text(encoding="utf-8"))
    CHANGELOG.write_text(changelog(datos), encoding="utf-8", newline="")
    RESUMEN.write_text(resumen(datos), encoding="utf-8")
    print(f"{len(datos['versiones'])} versiones -> CHANGELOG.md y docs/VERSIONES.md")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "generar")
