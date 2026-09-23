"""Controles de seguridad HTTP para uso local.

* Solo se aceptan cabeceras Host locales (mitiga DNS rebinding).
* Mutaciones exigen token CSRF (cabecera X-CSRF-Token) y Origin local cuando el navegador lo envía.
* CSP estricta sin scripts ni estilos en línea; cabeceras de endurecimiento en todas las respuestas.
* Límite de tamaño de cuerpo y de peticiones por minuto por ruta.
"""
from __future__ import annotations

import secrets
import threading
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

TOKEN_CSRF = secrets.token_urlsafe(32)
HOSTS_LOCALES = {"127.0.0.1", "localhost", "[::1]"}
MAX_CUERPO = 1_200_000
CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; "
       "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
CABECERAS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Cache-Control": "no-store",
}
LIMITES = {"/api/propuestas/calcular": 6, "/api/datos/actualizar": 4, "/api/importar": 20, "/api/investigacion/calcular": 4,
           "/api/cobertura/verificar": 4}
RUTA_WEBHOOK = "/webhook/tradingview"
MAX_WEBHOOK = 10_000
LIMITE_WEBHOOK = 30
LIMITE_MUTACION = 60


def _host_local(host: str | None) -> bool:
    if not host:
        return False
    h = host.rsplit(":", 1)[0] if not host.startswith("[") else host.split("]")[0] + "]"
    return h in HOSTS_LOCALES


class Seguridad(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._hist: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def _excede(self, clave: str, limite: int) -> bool:
        ahora = time.monotonic()
        with self._lock:
            q = self._hist[clave]
            while q and ahora - q[0] > 60:
                q.popleft()
            if len(q) >= limite:
                return True
            q.append(ahora)
            return False

    async def dispatch(self, request: Request, call_next):
        if request.url.path == RUTA_WEBHOOK:
            return await self._webhook(request, call_next)
        if not _host_local(request.headers.get("host")):
            return JSONResponse({"error": "Host no permitido"}, status_code=400)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origen = request.headers.get("origin")
            if origen and not _host_local(origen.split("://", 1)[-1]):
                return JSONResponse({"error": "Origen no permitido"}, status_code=403)
            if not secrets.compare_digest(request.headers.get("x-csrf-token", ""), TOKEN_CSRF):
                return JSONResponse({"error": "Token CSRF ausente o inválido; recargue la página"}, status_code=403)
            largo = request.headers.get("content-length")
            if largo is None or not largo.isdigit() or int(largo) > MAX_CUERPO:
                return JSONResponse({"error": "Cuerpo ausente o demasiado grande (máx. 1 MB)"}, status_code=413)
            ruta = request.url.path
            if self._excede(ruta, LIMITES.get(ruta, LIMITE_MUTACION)):
                return JSONResponse({"error": "Demasiadas solicitudes; espere un minuto"}, status_code=429)
        elif request.method == "OPTIONS":
            return JSONResponse({"error": "Método no permitido"}, status_code=405)
        respuesta = await call_next(request)
        for k, v in CABECERAS.items():
            respuesta.headers.setdefault(k, v)
        return respuesta

    async def _webhook(self, request: Request, call_next):
        """Webhook de TradingView: sin CSRF (lo envía un servidor externo), autenticado por secreto en el cuerpo.
        Solo POST, cuerpo ≤ 10 KB, 30/min, y Host local o incluido en TRADINGVIEW_WEBHOOK_HOSTS (túnel del usuario)."""
        import os
        permitidos = {h.strip().lower() for h in os.environ.get("TRADINGVIEW_WEBHOOK_HOSTS", "").split(",") if h.strip()}
        host = (request.headers.get("host") or "").lower()
        if not (_host_local(host) or host.split(":")[0] in permitidos):
            return JSONResponse({"error": "Host no permitido"}, status_code=400)
        if request.method != "POST":
            return JSONResponse({"error": "Método no permitido"}, status_code=405)
        largo = request.headers.get("content-length")
        if largo is None or not largo.isdigit() or int(largo) > MAX_WEBHOOK:
            return JSONResponse({"error": "Cuerpo ausente o demasiado grande"}, status_code=413)
        if self._excede(RUTA_WEBHOOK, LIMITE_WEBHOOK):
            return JSONResponse({"error": "Demasiadas solicitudes"}, status_code=429)
        respuesta = await call_next(request)
        for k, v in CABECERAS.items():
            respuesta.headers.setdefault(k, v)
        return respuesta
