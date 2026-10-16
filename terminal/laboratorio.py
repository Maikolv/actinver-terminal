"""Laboratorio: prueba de permutación de signos por bloques para el exceso medio NETO de una estrategia sobre un
benchmark (rendimientos emparejados por fecha). Es una herramienta de descarte estadístico, no un certificado de alfa.

Hipótesis (unilateral): H0 «el exceso medio neto es ≤ 0» frente a H1 «es > 0». Con d_t = r_estrategia,t − r_benchmark,t,
el estadístico es la media de d_t. Bajo H0 con distribución de d_t simétrica alrededor de 0 (supuesto de simetría /
intercambiabilidad de signos entre bloques), cambiar el signo de bloques contiguos completos no altera la ley de los
datos: se generan B volteos aleatorios de signo por bloque y p = (extremos + 1) / (B + 1), con
extremos = #{media permutada ≥ media observada}. Voltear bloques (no observaciones sueltas) conserva la dependencia
serial dentro del bloque. El supuesto NO es universal: rendimientos asimétricos, heterocedasticidad fuerte o dependencia
más larga que el bloque pueden invalidar el valor p. Con varias estrategias se aplica Holm (control del error de la
familia). Reproducible: misma entrada + misma semilla → mismo resultado.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math

import numpy as np

MIN_N, MAX_N = 20, 5000
MAX_B, MIN_B = 20000, 199
MIN_BLOQUES = 8                      # con menos bloques casi no hay patrones de signo distintos
MAX_ESTRATEGIAS = 20
MAX_COSTO = 200_000_000              # B × bloques × estrategias
MAX_EXPLORADAS = 1000
MAX_CSV = 1_000_000
ADVERTENCIAS = [
    "Un p < 0.05 aislado NO prueba alfa: solo indica que el exceso medio observado sería poco usual bajo H0 y los supuestos de abajo.",
    "Preregistre la hipótesis, la estrategia, el benchmark, los costos, el bloque y el número de variantes ANTES de ver los resultados; "
    "toda variante probada cuenta como hipótesis de la familia (use «hipótesis exploradas»).",
    "Estime parámetros con walk-forward con purga y embargo entre entrenamiento y prueba para no filtrar información; "
    "reserve un tramo de validación final (holdout) que se use una sola vez.",
    "Use rendimientos NETOS de comisiones, impuestos, deslizamiento y costos de financiamiento; un exceso bruto sobreestima el resultado.",
    "Supuesto de simetría/intercambiabilidad de signos: no es una prueba universal; con asimetría marcada, colas gruesas o "
    "dependencia mayor que el bloque, el valor p puede ser engañoso.",
]


def _numeros(valores, nombre: str) -> np.ndarray:
    if not isinstance(valores, (list, tuple)):
        raise ValueError(f"{nombre}: debe ser una lista de rendimientos")
    if len(valores) > MAX_N:
        raise ValueError(f"{nombre}: máximo {MAX_N} observaciones")
    out = []
    for i, v in enumerate(valores, 1):
        if isinstance(v, bool) or v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError(f"{nombre}, observación {i}: valor vacío o inválido")
        try:
            x = float(v)
        except (TypeError, ValueError):
            raise ValueError(f"{nombre}, observación {i}: no es un número") from None
        if not math.isfinite(x):
            raise ValueError(f"{nombre}, observación {i}: no es finito (NaN o infinito)")
        if x <= -1 or x > 10:
            raise ValueError(f"{nombre}, observación {i}: use rendimientos simples en decimal (0.01 = 1 %), entre −1 (exclusivo) y 10")
        out.append(x)
    return np.asarray(out, dtype=float)


def leer_csv(texto: str) -> tuple[list[str], dict[str, list[str]]]:
    """Encabezado obligatorio con columna «benchmark» (o «referencia»); «fecha» se ignora; las demás son estrategias."""
    if len(texto) > MAX_CSV:
        raise ValueError("CSV demasiado grande (máx. 1 MB)")
    try:
        filas = list(csv.reader(io.StringIO(texto.lstrip(chr(0xFEFF)).strip()), strict=True))
    except csv.Error:
        raise ValueError("CSV inválido") from None
    if len(filas) < 2:
        raise ValueError("el CSV necesita un encabezado y al menos una fila")
    enc = [c.strip() for c in filas[0]]
    bajo = [c.lower() for c in enc]
    ib = next((i for i, c in enumerate(bajo) if c in ("benchmark", "referencia")), None)
    if ib is None:
        raise ValueError("el encabezado debe incluir la columna «benchmark» (o «referencia»)")
    cols = [i for i, c in enumerate(bajo) if i != ib and c not in ("fecha", "date")]
    nombres = [enc[i] for i in cols]
    if not cols:
        raise ValueError("hace falta al menos una columna de estrategia")
    if len(set(nombres)) != len(nombres) or any(not n or len(n) > 40 for n in nombres):
        raise ValueError("los nombres de estrategia deben ser únicos, no vacíos y de hasta 40 caracteres")
    datos: dict[str, list[str]] = {n: [] for n in nombres}
    bench: list[str] = []
    for k, f in enumerate(filas[1:], start=2):
        if len(f) != len(enc):
            raise ValueError(f"fila {k}: número de columnas incorrecto")
        bench.append(f[ib])
        for n, i in zip(nombres, cols):
            datos[n].append(f[i])
    return bench, datos


def holm(pvalores: list[float], total: int | None = None) -> list[float]:
    """p ajustados de Holm (paso descendente). `total` ≥ m cuenta hipótesis exploradas no reportadas como p = 1."""
    m = len(pvalores)
    total = max(total or m, m)
    orden = sorted(range(m), key=lambda i: pvalores[i])
    aj, previo = [0.0] * m, 0.0
    for rango, i in enumerate(orden):
        previo = max(previo, min(1.0, (total - rango) * pvalores[i]))
        aj[i] = previo
    return aj


def permutacion(benchmark, estrategias: dict, bloque: int | None = None, B: int = 5000, semilla: int = 12345,
                alpha: float = 0.05, exploradas: int | None = None) -> dict:
    if not isinstance(estrategias, dict) or not estrategias:
        raise ValueError("indique al menos una estrategia")
    if len(estrategias) > MAX_ESTRATEGIAS:
        raise ValueError(f"máximo {MAX_ESTRATEGIAS} estrategias por familia")
    b = _numeros(benchmark, "benchmark")
    n = len(b)
    if n < MIN_N:
        raise ValueError(f"muestra demasiado corta: {n} observaciones (mínimo {MIN_N})")
    try:
        B, semilla = int(B), int(semilla)
        alpha = float(alpha)
        bloque = None if bloque in (None, "") else int(bloque)
        exploradas = None if exploradas in (None, "") else int(exploradas)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("B, semilla, bloque y exploradas deben ser enteros y alpha un número") from None
    if not MIN_B <= B <= MAX_B:
        raise ValueError(f"B (volteos) debe estar entre {MIN_B} y {MAX_B}")
    if not 0 <= semilla < 2**32:
        raise ValueError("semilla: entero entre 0 y 4294967295")
    if not 0 < alpha < 0.5:
        raise ValueError("alpha debe estar entre 0 y 0.5")
    if bloque is None:
        bloque = max(1, min(round(n ** (1 / 3)), n // MIN_BLOQUES))
    if bloque < 1 or math.ceil(n / bloque) < MIN_BLOQUES:
        raise ValueError(f"bloque inválido: con {n} observaciones debe haber al menos {MIN_BLOQUES} bloques (bloque ≤ {n // MIN_BLOQUES})")
    nombres = list(estrategias)
    d = np.empty((len(nombres), n))
    for k, nom in enumerate(nombres):
        if not isinstance(nom, str) or not nom.strip() or len(nom) > 40:
            raise ValueError("nombre de estrategia inválido (1 a 40 caracteres)")
        r = _numeros(estrategias[nom], f"estrategia «{nom}»")
        if len(r) != n:
            raise ValueError(f"estrategia «{nom}»: {len(r)} observaciones frente a {n} del benchmark (deben estar emparejadas por fecha)")
        d[k] = r - b
    nb = math.ceil(n / bloque)
    if B * nb * len(nombres) > MAX_COSTO:
        raise ValueError("costo de cómputo excesivo: reduzca B, el número de estrategias o aumente el bloque")
    if exploradas is not None and not len(nombres) <= exploradas <= MAX_EXPLORADAS:
        raise ValueError(f"hipótesis exploradas: entre {len(nombres)} y {MAX_EXPLORADAS}")
    sumas = np.stack([np.add.reduceat(d[k], np.arange(0, n, bloque)) for k in range(len(nombres))], axis=1)  # (nb, k)
    obs = d.mean(axis=1)
    escala = max(float(np.abs(d).max()), 1e-300)
    tol = 1e-12 * escala
    rng = np.random.default_rng(semilla)
    extremos = np.zeros(len(nombres), dtype=np.int64)
    hecho = 0
    while hecho < B:
        c = min(500, B - hecho)
        signos = rng.integers(0, 2, size=(c, nb), dtype=np.int8) * 2 - 1
        perm = (signos @ sumas) / n
        extremos += (perm >= obs - tol).sum(axis=0)
        hecho += c
    p = [(int(e) + 1) / (B + 1) for e in extremos]
    padj = holm(p, exploradas)
    huella = hashlib.sha256(json.dumps({"b": [round(x, 12) for x in b.tolist()],
                                        "e": {k: [round(x, 12) for x in (d[i] + b).tolist()] for i, k in enumerate(nombres)},
                                        "bloque": bloque, "B": B, "semilla": semilla}, sort_keys=True).encode()).hexdigest()
    filas = []
    for i, nom in enumerate(nombres):
        di = d[i]
        rho = float(np.corrcoef(di[:-1], di[1:])[0, 1]) if np.ptp(di) > 0 else None
        sig = padj[i] <= alpha
        filas.append({"estrategia": nom, "exceso_medio": float(obs[i]), "desv_exceso": float(di.std(ddof=1)),
                      "autocorr_lag1": rho if rho is not None and math.isfinite(rho) else None,
                      "extremos": int(extremos[i]), "p": p[i], "p_holm": padj[i], "supera_alpha_holm": bool(sig),
                      "lectura": ("Evidencia estadística compatible con exceso medio neto > 0 bajo los supuestos. NO es alfa probado: "
                                  "falta preregistro, walk-forward con purga/embargo, holdout y costos reales."
                                  if sig else "Sin evidencia suficiente de exceso medio neto > 0 (no se rechaza H0).")})
    avisos = list(ADVERTENCIAS)
    if any(f["autocorr_lag1"] is not None and abs(f["autocorr_lag1"]) > 0.2 for f in filas) and bloque < 5:
        avisos.append("Hay autocorrelación apreciable en el exceso y el bloque es corto: pruebe bloques más largos.")
    if n < 60:
        avisos.append(f"Muestra corta ({n}): baja potencia; un no rechazo no demuestra ausencia de ventaja.")
    return {"hipotesis": "H0: exceso medio neto ≤ 0 frente a H1: exceso medio neto > 0 (unilateral)",
            "estadistico": "media de (estrategia − benchmark), rendimientos netos simples",
            "metodo": "permutación de signos por bloques contiguos; p = (extremos + 1) / (B + 1)",
            "n": n, "bloque": bloque, "bloques": nb, "B": B, "semilla": semilla, "alpha": alpha,
            "p_minimo": 1 / (B + 1), "familia": len(nombres), "familia_total_holm": max(exploradas or 0, len(nombres)),
            "resultados": filas, "huella_sha256": huella, "advertencias": avisos}
