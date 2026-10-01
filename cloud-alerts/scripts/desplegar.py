"""Despliegue reproducible del monitor en Cloudflare Workers (plan Free), sin mostrar ningún secreto.

Uso (desde la raíz del repositorio, con `npx wrangler login` hecho una vez):
    uv run python cloud-alerts/scripts/desplegar.py            # todo: D1, migraciones, secretos, despliegue y URL
    uv run python cloud-alerts/scripts/desplegar.py --secretos # solo vuelve a cargar los secretos desde .env
    uv run python cloud-alerts/scripts/desplegar.py --desactivar   # quita el disparador programado (deja de avisar)

Los secretos se leen de `.env` y se pasan a `wrangler secret put` por la entrada estándar: nunca se imprimen ni se
escriben en archivos versionados. `CLOUD_ALERTS_SECRET` se genera si falta y se carga en Cloudflare como SYNC_SECRET.
"""
from __future__ import annotations

import argparse
import json
import re
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parents[1]
RAIZ = DIR.parent
ENV = RAIZ / ".env"
WRANGLER_CFG = DIR / "wrangler.jsonc"
SECRETOS = {  # nombre en Cloudflare ← variable en .env
    "SYNC_SECRET": "CLOUD_ALERTS_SECRET", "TELEGRAM_BOT_TOKEN": "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID": "TELEGRAM_CHAT_ID",
    "ALPACA_API_KEY_ID": "ALPACA_API_KEY_ID", "ALPACA_API_SECRET_KEY": "ALPACA_API_SECRET_KEY", "BANXICO_TOKEN": "BANXICO_TOKEN",
}
SIN_ID = "00000000-0000-0000-0000-000000000000"


def npx() -> str:
    return shutil.which("npx.cmd") or shutil.which("npx") or "npx"


def wrangler(*args: str, entrada: str | None = None, mostrar: bool = True) -> subprocess.CompletedProcess:
    r = subprocess.run([npx(), "wrangler", *args], cwd=DIR, input=entrada, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=600)
    if mostrar:
        salida = (r.stdout + r.stderr).strip()
        print("\n".join(salida.splitlines()[-12:]))
    return r


def leer_env() -> dict[str, str]:
    d = {}
    for ln in ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []:
        if "=" in ln and not ln.lstrip().startswith("#"):
            k, v = ln.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def fijar_env(clave: str, valor: str) -> None:
    lineas = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    lineas = [ln for ln in lineas if not ln.strip().startswith(f"{clave}=")] + [f"{clave}={valor}"]
    ENV.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def sesion() -> bool:
    r = wrangler("whoami", mostrar=False)
    if "not authenticated" in (r.stdout + r.stderr).lower():
        print("Wrangler no tiene sesión. Ejecute una vez:  cd cloud-alerts  y  npx wrangler login  (se abre el navegador).")
        return False
    return True


def base_d1() -> None:
    txt = WRANGLER_CFG.read_text(encoding="utf-8")
    if SIN_ID not in txt:
        print("D1: ya configurada.")
        return
    r = wrangler("d1", "create", "actinver-alertas")
    m = re.search(r'"database_id"\s*:\s*"([0-9a-f-]{36})"', r.stdout + r.stderr) or \
        re.search(r"database_id\s*=\s*\"([0-9a-f-]{36})\"", r.stdout + r.stderr)
    if not m:  # ya existía: se busca en la lista
        lista = wrangler("d1", "list", "--json", mostrar=False)
        try:
            m2 = next(d["uuid"] for d in json.loads(lista.stdout) if d.get("name") == "actinver-alertas")
        except (ValueError, StopIteration, KeyError):
            sys.exit("No se pudo crear ni encontrar la base D1 «actinver-alertas».")
        uid = m2
    else:
        uid = m.group(1)
    WRANGLER_CFG.write_text(txt.replace(SIN_ID, uid), encoding="utf-8")
    print("D1: creada y anotada en wrangler.jsonc (el id de la base no es un secreto).")


def cargar_secretos() -> None:
    env = leer_env()
    if len(env.get("CLOUD_ALERTS_SECRET", "")) < 32:
        fijar_env("CLOUD_ALERTS_SECRET", secrets.token_urlsafe(32))
        env = leer_env()
        print("CLOUD_ALERTS_SECRET generado en .env.")
    for nombre, var in SECRETOS.items():
        valor = env.get(var, "")
        if not valor:
            print(f"  {nombre}: falta {var} en .env (se omite)")
            continue
        r = wrangler("secret", "put", nombre, entrada=valor, mostrar=False)
        print(f"  {nombre}: {'cargado' if r.returncode == 0 else 'ERROR (vea «npx wrangler secret list»)'}")


def desplegar() -> None:
    wrangler("d1", "migrations", "apply", "actinver-alertas", "--remote")
    r = wrangler("deploy")
    if r.returncode != 0:
        sys.exit("El despliegue falló (vea el mensaje de wrangler arriba).")
    m = re.search(r"https://[a-z0-9.-]+\.workers\.dev", r.stdout + r.stderr)
    if m:
        fijar_env("CLOUD_ALERTS_URL", m.group(0))
        print(f"URL del monitor guardada en .env como CLOUD_ALERTS_URL: {m.group(0)}")


def desactivar() -> None:
    txt = WRANGLER_CFG.read_text(encoding="utf-8")
    nuevo = re.sub(r'"crons":\s*\[[^\]]*\]', '"crons": []', txt)
    WRANGLER_CFG.write_text(nuevo, encoding="utf-8")
    wrangler("deploy")
    print("Disparador programado eliminado: el monitor ya no se ejecuta solo. Para borrarlo del todo: npx wrangler delete")


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--secretos", action="store_true", help="solo cargar los secretos")
    a.add_argument("--desactivar", action="store_true", help="quitar el disparador programado")
    args = a.parse_args()
    if not sesion():
        sys.exit(1)
    if args.desactivar:
        return desactivar()
    if args.secretos:
        return cargar_secretos()
    base_d1()
    desplegar()
    cargar_secretos()
    print("Listo. Compruebe con:  uv run terminal nube prueba  (y deje la terminal cerrada ≥ 20 min en horario de mercado).")


if __name__ == "__main__":
    main()
