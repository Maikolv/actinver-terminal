from .base import Adaptador, Barra, ErrorProveedor, LimiteAlcanzado, SinCredencial
from .proveedores import FX_USDMXN, Alpaca, Archivo, Banxico, Barchart, Eodhd, Fred, Tiingo

CLASES = {"fred": Fred, "banxico": Banxico, "tiingo": Tiingo, "alpaca": Alpaca, "barchart": Barchart, "eodhd": Eodhd, "archivo": Archivo}

__all__ = ["Adaptador", "Barra", "ErrorProveedor", "LimiteAlcanzado", "SinCredencial", "CLASES", "FX_USDMXN",
           "Fred", "Banxico", "Tiingo", "Alpaca", "Barchart", "Eodhd", "Archivo"]
