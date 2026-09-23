from .base import Adaptador, Barra, ErrorProveedor, LimiteAlcanzado, SinCredencial
from .proveedores import FX_USDMXN, Archivo, Banxico, Barchart, Eodhd, Fred, Tiingo

CLASES = {"fred": Fred, "banxico": Banxico, "tiingo": Tiingo, "barchart": Barchart, "eodhd": Eodhd, "archivo": Archivo}

__all__ = ["Adaptador", "Barra", "ErrorProveedor", "LimiteAlcanzado", "SinCredencial", "CLASES", "FX_USDMXN",
           "Fred", "Banxico", "Tiingo", "Barchart", "Eodhd", "Archivo"]
