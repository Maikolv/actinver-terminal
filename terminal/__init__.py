"""Terminal local de análisis de portafolios (solo informativa; no envía órdenes)."""
from importlib.metadata import PackageNotFoundError, version

try:  # una sola fuente: pyproject.toml (también sella backtests y evaluaciones)
    __version__ = version("actinver-terminal")
except PackageNotFoundError:
    __version__ = "desconocida"
