from .base import Adaptador, Barra, ErrorProveedor, LimiteAlcanzado, SinCredencial
from .proveedores import FX_USDMXN, Archivo, Banxico, Eodhd, Fred, Tiingo

CLASES = {"fred": Fred, "banxico": Banxico, "tiingo": Tiingo, "eodhd": Eodhd, "archivo": Archivo}

__all__ = ["Adaptador", "Barra", "ErrorProveedor", "LimiteAlcanzado", "SinCredencial", "CLASES", "FX_USDMXN",
           "Fred", "Banxico", "Tiingo", "Eodhd", "Archivo"]
