"""Actualiza la copia pública del calendario BEA sin credenciales."""
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

FUENTE = "https://apps.bea.gov/API/signup/release_dates.json"
DESTINO = Path(__file__).resolve().parents[1] / "config" / "calendario_bea.json"


def preparar(datos: dict, ahora: datetime) -> dict:
    eventos = set()
    for titulo, serie in datos.items():
        if not isinstance(serie, dict) or "release_dates" not in serie:
            continue
        for fecha in serie["release_dates"]:
            instante = datetime.fromisoformat(fecha)
            if instante.tzinfo is None:
                raise ValueError("Fecha BEA sin zona horaria")
            if instante.year >= ahora.year:
                eventos.add((instante.astimezone(UTC).isoformat(), titulo))
    if not eventos:
        raise ValueError("La fuente BEA no devolvió fechas del año en curso o posteriores")
    return {
        "fuente": FUENTE,
        "consultado_en": ahora.isoformat(timespec="seconds"),
        "eventos": [{"fecha": fecha, "titulo": titulo} for fecha, titulo in sorted(eventos)],
    }


def actualizar(destino: Path = DESTINO) -> int:
    with urlopen(FUENTE, timeout=10) as respuesta:
        corte = preparar(json.load(respuesta), datetime.now(UTC))
    temporal = destino.with_suffix(".tmp")
    temporal.write_text(json.dumps(corte, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporal.replace(destino)
    return len(corte["eventos"])


if __name__ == "__main__":
    print(f"Calendario BEA: {actualizar()} fechas únicas.")
