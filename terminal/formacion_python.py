"""Práctica propia de series: inspirada en los temas de python-training (JPMorgan).

No copia código upstream. Solo acepta observaciones con procedencia explícita.
No conecta proveedores ni modifica los modelos de producción.
"""
from datetime import date
from decimal import Decimal, InvalidOperation
from statistics import stdev


def resumen_cierres(filas: list[dict]) -> dict:
    """Estadísticas entre observaciones, sin asumir frecuencia ni anualizar."""
    if len(filas) < 3:
        raise ValueError('Se requieren al menos tres cierres fechados.')
    precios, fechas, procedencias = [], [], set()
    for f in filas:
        if not all(isinstance(f.get(k), str) and f[k].strip() for k in ('fuente', 'tipo_dato')):
            raise ValueError('Cada observación requiere fuente y tipo_dato.')
        procedencias.add((f['fuente'], f['tipo_dato']))
        fechas.append(date.fromisoformat(f['fecha']))
        try:
            if isinstance(f['cierre'], bool):
                raise ValueError('Un booleano no es un cierre.')
            p = Decimal(str(f['cierre']))
        except (InvalidOperation, TypeError) as exc:
            raise ValueError('Cierre inválido.') from exc
        if not p.is_finite() or p <= 0:
            raise ValueError('Los cierres deben ser finitos y positivos.')
        precios.append(p)
    if any(a >= b for a, b in zip(fechas, fechas[1:])):
        raise ValueError('Fechas duplicadas o fuera de orden; no se ordenan ni rellenan silenciosamente.')
    if len(procedencias) != 1:
        raise ValueError('No se mezclan fuentes o tipos de dato sin conciliación explícita.')
    cambios = [float(b / a - 1) for a, b in zip(precios, precios[1:])]
    pico, caida = precios[0], Decimal(0)
    for p in precios:
        pico = max(pico, p)
        caida = min(caida, p / pico - 1)
    fuente, tipo = next(iter(procedencias))
    return dict(observaciones=len(filas), desde=fechas[0].isoformat(), hasta=fechas[-1].isoformat(),
                fuente=fuente, tipo_dato=tipo, rendimiento_tramo=float(precios[-1] / precios[0] - 1),
                volatilidad_entre_observaciones=stdev(cambios), caida_maxima=float(caida),
                nota='Estudio descriptivo; sin anualización, interpolación ni ventaja demostrada.')
