"""Interfaz común de adaptadores de datos de mercado.

Cada adaptador declara: proveedor, tipo de dato que entrega, si requiere credencial, límites
de peticiones y qué instrumentos soporta. Los límites se cuentan en la base local para que
persistan entre reinicios (límite de gasto/peticiones). Las credenciales nunca se incluyen
en mensajes de error ni en registros.
"""
from __future__ import annotations

import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime

import httpx


class ErrorProveedor(Exception):
    pass


class LimiteAlcanzado(ErrorProveedor):
    pass


class SinCredencial(ErrorProveedor):
    pass


@dataclass
class Barra:
    fecha: str
    cierre: float
    cierre_ajustado: float | None = None
    volumen: float | None = None
    dividendo: float = 0.0
    factor_split: float = 1.0


_SECRETO = re.compile(r"(token|api_token|apikey|key)=[^&\s]+", re.I)


def limpiar(msg: str) -> str:
    """Elimina credenciales que pudieran aparecer en URLs de errores."""
    return _SECRETO.sub(r"\1=***", str(msg))


class Adaptador:
    proveedor = "base"
    tipo_dato = "cierre"
    requiere_credencial = False
    descripcion = ""
    uso_permitido = ""

    def __init__(self, con: sqlite3.Connection, ajustes: dict, credencial: str | None = None,
                 cliente: httpx.Client | None = None):
        self.con = con
        self.ajustes = ajustes or {}
        self.credencial = credencial
        self._cliente = cliente

    @property
    def cliente(self) -> httpx.Client:
        """Se crea al primer uso: construir el contexto TLS cuesta decenas de ms y el estado no lo necesita."""
        if self._cliente is None:
            self._cliente = httpx.Client(timeout=30, follow_redirects=True,
                                         headers={"User-Agent": "actinver-terminal/0.1 (uso personal local)"})
        return self._cliente

    # --- capacidades -------------------------------------------------------------------------
    def configurado(self) -> bool:
        return bool(self.ajustes.get("activo", True)) and (not self.requiere_credencial or bool(self.credencial))

    def soporta(self, instr: dict) -> bool:  # pragma: no cover - lo implementan las subclases
        return False

    def historico(self, instr: dict, desde: date, hasta: date) -> list[Barra]:  # pragma: no cover
        raise NotImplementedError

    # --- límites de peticiones ---------------------------------------------------------------
    def _ventanas(self) -> list[tuple[str, int]]:
        ahora = datetime.now(UTC)
        out = []
        if "peticiones_por_dia" in self.ajustes:
            out.append((f"d:{ahora:%Y-%m-%d}", int(self.ajustes["peticiones_por_dia"])))
        if "peticiones_por_hora" in self.ajustes:
            out.append((f"h:{ahora:%Y-%m-%dT%H}", int(self.ajustes["peticiones_por_hora"])))
        return out

    def peticiones_restantes(self) -> int | None:
        restantes = []
        for ventana, limite in self._ventanas():
            fila = self.con.execute("SELECT peticiones FROM uso_proveedor WHERE proveedor=? AND ventana=?",
                                    (self.proveedor, ventana)).fetchone()
            restantes.append(limite - (fila[0] if fila else 0))
        return min(restantes) if restantes else None

    def _consumir(self) -> None:
        r = self.peticiones_restantes()
        if r is not None and r <= 0:
            raise LimiteAlcanzado(f"{self.proveedor}: límite de peticiones alcanzado; se reintentará en la siguiente ventana")
        for ventana, _ in self._ventanas():
            self.con.execute(
                "INSERT INTO uso_proveedor (proveedor, ventana, peticiones) VALUES (?,?,1) "
                "ON CONFLICT(proveedor, ventana) DO UPDATE SET peticiones = peticiones + 1",
                (self.proveedor, ventana))
        self.con.commit()

    # --- HTTP con reintentos -----------------------------------------------------------------
    def _get(self, url: str, *, params: dict | None = None, headers: dict | None = None,
             intentos: int = 3) -> httpx.Response:
        if self.requiere_credencial and not self.credencial:
            raise SinCredencial(f"{self.proveedor}: falta la credencial en variables de entorno")
        espera = 2.0
        ultimo = None
        for i in range(intentos):
            self._consumir()
            try:
                r = self.cliente.get(url, params=params, headers=headers)
            except httpx.HTTPError as e:  # red caída: reintentar (reconexión)
                ultimo = ErrorProveedor(f"{self.proveedor}: error de red: {limpiar(type(e).__name__)}")
            else:
                if r.status_code == 200:
                    return r
                if r.status_code in (401, 403):
                    raise ErrorProveedor(f"{self.proveedor}: credencial rechazada o sin permiso (HTTP {r.status_code})")
                if r.status_code == 404:
                    raise ErrorProveedor(f"{self.proveedor}: símbolo no encontrado (HTTP 404)")
                ultimo = ErrorProveedor(f"{self.proveedor}: HTTP {r.status_code}")
                if r.status_code not in (429, 500, 502, 503, 504):
                    break
            if i < intentos - 1:
                time.sleep(espera)
                espera *= 2
        raise ultimo or ErrorProveedor(f"{self.proveedor}: error desconocido")
