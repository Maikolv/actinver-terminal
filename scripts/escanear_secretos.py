"""Escanea el árbol y TODO el historial de Git en busca de secretos. Imprime rutas/commits, nunca valores.

Uso:  uv run python scripts/escanear_secretos.py
Complementa a `detect-secrets scan` (árbol actual) revisando cada versión de cada archivo en el historial.
"""
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PATRONES = {
    "aws": r"AKIA[0-9A-Z]{16}",
    "github": r"gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{50,}",
    "anthropic": r"sk-ant-[A-Za-z0-9_-]{20,}",
    "openai": r"sk-(proj-)?[A-Za-z0-9]{40,}",
    "slack": r"xox[baprs]-[0-9A-Za-z-]{10,}",
    "google": r"AIza[0-9A-Za-z_-]{35}",
    "llave_privada": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "telegram": r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b",
    "asignacion": r"(?i)(api_?key|token|secret|password|passwd)\s*[=:]\s*['\"][A-Za-z0-9/+_\-]{16,}['\"]",
}
EXPR = re.compile("|".join(f"(?P<{k}>{v})" for k, v in PATRONES.items()))


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8",
                          errors="ignore", check=True).stdout


def main() -> int:
    hallazgos = []
    commits = git("rev-list", "--all").split()
    for c in commits:
        for ruta in git("ls-tree", "-r", "--name-only", c).splitlines():
            if ruta.endswith((".png", ".lock", ".db", ".ico")):
                continue
            contenido = git("show", f"{c}:{ruta}")
            for m in EXPR.finditer(contenido):
                hallazgos.append((c[:8], ruta, m.lastgroup))
    for c, ruta, tipo in sorted(set(hallazgos)):
        print(f"{c}  {ruta}  [{tipo}]")
    print(f"{len(commits)} commits revisados; {len(set(hallazgos))} hallazgos")
    return 1 if hallazgos else 0


if __name__ == "__main__":
    sys.exit(main())
