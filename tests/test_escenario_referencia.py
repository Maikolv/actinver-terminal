"""Escenario de referencia (como el de COATL): cifras exactas de una cartera demo con rendimientos fijos.

Si cambia el modelo (estimación, optimizador o VaR/CVaR), esta prueba falla a propósito: actualice las cifras SOLO
después de documentar el porqué en CHANGELOG/docs/versiones.json. Los rendimientos son sintéticos y fijos (semilla
2026), no dependen de la fecha ni de proveedores.
"""
import pytest

from terminal.escenario_referencia import cifras

# Fijadas el 17-nov-2026 (versión 101). Cartera demo 40/35/10/15 %; tope 60 % por instrumento; rf 10 %.
REFERENCIA = {"rend_esperado": 0.17307860090327534, "volatilidad": 0.1026155081899454,
              "var95_1d": 0.010191967596089401, "cvar95_1d": 0.01259104901434681,
              "max_sharpe": {"SIC:IVV": 0.6, "FONDO:ACTIGOB": 0.2661, "BMV:WALMEX": 0.0, "SIC:MSFT": 0.1339}}


def test_escenario_de_referencia():
    c = cifras()
    for k, v in REFERENCIA.items():
        if k == "max_sharpe":
            assert c[k] == pytest.approx(v, abs=2e-3), "Cambió el optimizador: documente el porqué antes de fijar cifras nuevas."
        else:
            assert c[k] == pytest.approx(v, rel=1e-6), f"Cambió {k}: documente el porqué antes de fijar cifras nuevas."
