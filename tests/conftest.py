import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# La app lee estas variables al importarse: base temporal y modo real (nunca la base del usuario).
_TMP = tempfile.mkdtemp(prefix="terminal-pruebas-")
os.environ["TERMINAL_DATA_DIR"] = _TMP
os.environ["TERMINAL_MODO"] = "real"
os.environ["TERMINAL_SIN_MOTOR"] = "1"  # sin hilo automático ni notificaciones durante las pruebas
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terminal import db, vigencia  # noqa: E402
from terminal.config import cargar_ajustes  # noqa: E402


@pytest.fixture
def ajustes():
    a = cargar_ajustes()
    a.datos["app"]["modo"] = "real"
    return a


@pytest.fixture
def con(tmp_path):
    c = db.conectar(tmp_path / "t.db")
    db.inicializar(c)
    yield c
    c.close()


def sembrar_precios(con, ids, fin=None, sesiones=900, semilla=7, proveedor="prueba", tipo="cierre", con_fx=True):
    """Precios diarios deterministas (tipo 'cierre') que terminan en la última sesión cerrada."""
    fin = pd.Timestamp(fin or vigencia.ultima_sesion_cerrada("XNYS"))
    fechas = vigencia.calendario("XNYS").sessions_in_range(fin - pd.Timedelta(days=int(sesiones * 1.5)), fin)[-sesiones:]
    rng = np.random.default_rng(semilla)
    mercado = rng.normal(0.0003, 0.01, len(fechas))
    filas = []
    for k, iid in enumerate(ids):
        moneda = con.execute("SELECT moneda_referencia FROM instrumentos WHERE id=?", (iid,)).fetchone()[0] or "MXN"
        clase = con.execute("SELECT clase FROM instrumentos WHERE id=?", (iid,)).fetchone()[0]
        vol, beta, mu = (0.002, 0.02, 0.0003) if clase == "fondo_deuda" else (0.015, 0.8, 0.0004 + 0.00005 * (k % 5))
        r = mu + beta * mercado + rng.normal(0, vol, len(fechas))
        p = 100 * np.exp(np.cumsum(r))
        filas += [(iid, f.date().isoformat(), float(x), float(x), 1e6, moneda, proveedor, tipo, None, db.ahora())
                  for f, x in zip(fechas, p)]
    con.executemany("INSERT OR REPLACE INTO precios (instrumento_id, fecha, cierre, cierre_ajustado, volumen, moneda, proveedor, tipo_dato, hora_cotizacion, obtenido_en) VALUES (?,?,?,?,?,?,?,?,?,?)", filas)
    if con_fx:
        con.executemany("INSERT OR REPLACE INTO fx (par, fecha, valor, proveedor, tipo_dato, obtenido_en) VALUES ('USDMXN',?,?,?,?,?)",
                        [(f.date().isoformat(), 17.0 + 0.001 * i, "fred", "fx", db.ahora()) for i, f in enumerate(fechas)])
    con.commit()
    return fechas
