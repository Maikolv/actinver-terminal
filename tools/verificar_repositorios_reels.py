"""Verifica config/repositorios-20261031.json contra los clones locales: ruta, remoto, commit y licencia. Solo lectura (git rev-parse /
remote get-url); no hace fetch ni red, no ejecuta código de los repositorios.

  python tools/verificar_repositorios_reels.py [--json salida.json]
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LICENCIAS = {  # huella mínima del texto del archivo; "desconocida" si no coincide: no se adivina
    "MIT": r"\bMIT License\b|Permission is hereby granted, free of charge",
    "Apache-2.0": r"Apache License\s+Version 2\.0",
    "AGPL-3.0": r"GNU AFFERO GENERAL PUBLIC LICENSE",
    "GPL-3.0": r"GNU GENERAL PUBLIC LICENSE\s+Version 3",
    "BSD": r"Redistribution and use in source and binary forms",
    "ISC": r"Permission to use, copy, modify, and/or distribute this software",
    "Unlicense": r"This is free and unencumbered software",
}


def git(ruta, *args):
    r = subprocess.run(["git", "-C", str(ruta), *args], capture_output=True, text=True, timeout=30)
    return r.stdout.strip() if r.returncode == 0 else None


def licencia(ruta, archivos):
    res = []
    for a in archivos or []:
        p = Path(ruta) / a
        if not p.is_file():
            res.append((a, "archivo ausente"))
            continue
        t = p.read_text(encoding="utf-8", errors="ignore")[:6000]
        res.append((a, next((k for k, rx in LICENCIAS.items() if re.search(rx, t, re.I)), "desconocida")))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    a = ap.parse_args()
    inv = json.loads((RAIZ / "config" / "repositorios-20261031.json").read_text(encoding="utf-8"))
    filas = []
    for r in inv:
        ruta = Path(r["path"])
        fila = dict(nombre=r["nombre"], path=r["path"], existe=ruta.is_dir(), problemas=[])
        if not fila["existe"]:
            fila["problemas"].append("ruta ausente")
        elif r.get("tipo") == "skill":
            skill = ruta / "SKILL.md"
            if not skill.is_file() or hashlib.sha256(skill.read_bytes()).hexdigest() != r.get("sha256_skill"):
                fila["problemas"].append("skill ausente o huella distinta")
            if r.get("skill_origen_verificado") is not True:
                fila["problemas"].append("procedencia de la versión instalada no verificada; no heredar licencia por el nombre")
            origen = Path(r.get("licencia_origen_local", ""))
            fila["licencias"] = licencia(origen.parent, [origen.name]) if origen.is_file() else []
            fila["tipo"] = "skill; no se exige repositorio Git en la instalación"
            if not fila["licencias"] or any(lic in ("archivo ausente", "desconocida") for _, lic in fila["licencias"]):
                fila["problemas"].append("licencia de origen no verificada")
        else:
            head = git(ruta, "rev-parse", "HEAD")
            remoto = git(ruta, "remote", "get-url", "origin")
            sucio = git(ruta, "status", "--porcelain")
            fila.update(head=head, remoto=remoto, commit_inventario=r.get("commit"), remoto_inventario=r.get("remote"),
                        licencias=licencia(ruta, r.get("licencia_archivos")), cambios_locales=bool(sucio))
            if head is None:
                fila["problemas"].append("no es un repositorio git legible")
            elif r.get("commit") and head != r["commit"]:
                fila["problemas"].append(f"HEAD {head[:10]} distinto del commit inventariado {r['commit'][:10]}")
            if remoto and r.get("remote") and remoto.rstrip("/").removesuffix(".git").lower() != r["remote"].rstrip("/").removesuffix(".git").lower():
                fila["problemas"].append(f"remoto {remoto} distinto del inventariado")
            if not r.get("licencia_archivos"):
                fila["problemas"].append("sin archivo de licencia inventariado")
            for arch, lic in fila["licencias"]:
                if lic in ("archivo ausente", "desconocida"):
                    fila["problemas"].append(f"licencia {arch}: {lic}")
        filas.append(fila)
    ok = sum(not f["problemas"] for f in filas)
    print(f"{len(filas)} repositorios; {ok} sin problemas; {len(filas) - ok} con observaciones")
    for f in filas:
        lic = ",".join(l for _, l in f.get("licencias", [])) or "-"
        print(("OK  " if not f["problemas"] else "OBS ") + f"{f['nombre']:<28} {lic:<14} {'; '.join(f['problemas'])}")
    if a.json:
        Path(a.json).write_text(json.dumps(filas, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
