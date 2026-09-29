"""Configuración: archivo TOML sin secretos + variables de entorno para credenciales.

Orden de carga: config/ajustes.ejemplo.toml (valores por defecto versionados) y, si existe,
config/local.toml (no versionado). Las claves API se leen SOLO de variables de entorno o de
un archivo .env local (no versionado); nunca se envían al navegador ni se registran.
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_DIR = RAIZ / "config"
DATA_DIR = Path(os.environ.get("TERMINAL_DATA_DIR", RAIZ / "data"))
MODOS = ("real", "demo")
_MODO = {"activo": None}  # modo elegido en caliente desde la interfaz (tiene prioridad)


def fijar_modo(modo: str) -> None:
    if modo not in MODOS:
        raise ValueError("modo no válido")
    _MODO["activo"] = modo


def modo_activo(predeterminado: str = "real") -> str:
    return _MODO["activo"] or os.environ.get("TERMINAL_MODO") or predeterminado


def data_dir(modo: str | None = None) -> Path:
    """Base separada por modo: los datos sintéticos nunca se mezclan con los reales."""
    return DATA_DIR / "demo" if (modo or modo_activo()) == "demo" else DATA_DIR

# Nombres de variables de entorno aceptadas para credenciales (nunca sus valores en código).
VARIABLES_CREDENCIALES = {
    "tiingo": "TIINGO_API_KEY",
    "eodhd": "EODHD_API_KEY",
    "twelvedata": "TWELVEDATA_API_KEY",
    "banxico": "BANXICO_TOKEN",
    "barchart": "BARCHART_API_KEY",
    "sec_edgar": "SEC_USER_AGENT",
    "alpaca": "ALPACA_API_KEY_ID",
}
# Proveedores que además de la clave usan un secreto (se leen aparte y nunca se exponen).
VARIABLES_SECRETOS = {"alpaca": "ALPACA_API_SECRET_KEY"}


def _cargar_env_local() -> None:
    """Carga .env (KEY=VALUE) sin sobrescribir variables ya definidas. Sin dependencias."""
    ruta = RAIZ / ".env"
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        k, v = linea.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _fusionar(base: dict, extra: dict) -> dict:
    out = dict(base)
    for k, v in extra.items():
        out[k] = _fusionar(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


@dataclass
class Ajustes:
    datos: dict = field(default_factory=dict)

    def __getitem__(self, k):
        return self.datos[k]

    def get(self, k, d=None):
        return self.datos.get(k, d)

    @property
    def modo(self) -> str:
        return modo_activo(self.datos["app"].get("modo", "real"))

    @property
    def es_demo(self) -> bool:
        return self.modo == "demo"


def credencial(proveedor: str) -> str | None:
    var = VARIABLES_CREDENCIALES.get(proveedor)
    val = os.environ.get(var) if var else None
    return val or None


def secreto(proveedor: str) -> str | None:
    var = VARIABLES_SECRETOS.get(proveedor)
    return (os.environ.get(var) if var else None) or None


def cargar_ajustes() -> Ajustes:
    _cargar_env_local()
    with (CONFIG_DIR / "ajustes.ejemplo.toml").open("rb") as fh:
        datos = tomllib.load(fh)
    local = CONFIG_DIR / "local.toml"
    if local.exists():
        with local.open("rb") as fh:
            datos = _fusionar(datos, tomllib.load(fh))
    return Ajustes(datos)
