"""Historia larga entregada por el usuario (Excel «Benchmarks_time_series»): verificación e incorporación.

El archivo es una matriz de precios diarios (1962 → 9-oct-2025) de 226 instrumentos del universo del Reto, con
claves al estilo Yahoo Finance (`GMEXICOB.MX`, `BRK-B`), más tres series índice («Conservador», «Moderado»,
«Agresivo», base 100 el 5-ene-2004) cuya construcción no viene documentada.

Reglas:
- No se escribe en la tabla `precios`: es historia de referencia hasta el 9-oct-2025, nunca un precio vigente.
- Cada columna se VERIFICA contra las series que ya tiene la terminal (Tiingo/Alpaca/EODHD) en las fechas comunes y,
  para emisoras BMV con ADR, contra el ADR en MXN (fuente independiente). Solo las aceptadas extienden RENDIMIENTOS
  hacia atrás, antes del primer dato local, igual que el proxy ADR (terminal/proxy_adr.py).
- Sin solape no hay verificación: esas columnas (fondos, sobre todo) se informan y no se usan.
- Los perfiles índice se reportan como referencia histórica; no se usan para decidir.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import config, mercado

PERFILES = ("Conservador", "Moderado", "Agresivo")
MIN_SOLAPE = 10            # sesiones comunes mínimas para verificar una columna
MIN_CORRELACION = 0.98     # mismo instrumento, misma fuente de mercado: los rendimientos deben coincidir casi exacto
MAX_DIF_MEDIANA = 0.002    # diferencia diaria mediana tolerada (0.2 pp)
# Homónimos conocidos: la clave sin sufijo .MX es otra emisora de EE. UU.
HOMONIMOS = {"AC": "«AC» sin .MX es Associated Capital Group (NYSE), no Arca Continental (AC.MX): no se usa"}


def carpeta() -> Path:
    return config.data_dir() / "referencias" / "historia_externa"


# ---------------------------------------------------------------------------------------------- importación
def importar(ruta_xlsx: Path, destino: Path | None = None) -> dict:
    """Lee el Excel (requiere openpyxl) y guarda la matriz en CSV comprimido con su procedencia (sha256)."""
    d = destino or carpeta()
    d.mkdir(parents=True, exist_ok=True)
    df = pd.read_excel(ruta_xlsx, index_col=0)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index().dropna(how="all")
    with gzip.open(d / "precios.csv.gz", "wt", encoding="utf-8", newline="") as f:
        df.to_csv(f, float_format="%.6g")
    proc = {"archivo": Path(ruta_xlsx).name, "sha256": hashlib.sha256(Path(ruta_xlsx).read_bytes()).hexdigest(),
            "filas": int(len(df)), "columnas": int(df.shape[1]), "desde": str(df.index.min().date()),
            "hasta": str(df.index.max().date())}
    (d / "procedencia.json").write_text(json.dumps(proc, ensure_ascii=False, indent=1), encoding="utf-8")
    return proc


def cargar(base: Path | None = None) -> pd.DataFrame:
    f = (base or carpeta()) / "precios.csv.gz"
    if not f.exists():
        return pd.DataFrame()
    df = pd.read_csv(f, index_col=0, parse_dates=True)
    return df.sort_index()


# ---------------------------------------------------------------------------------------------- mapeo
def mapear(con, columnas) -> dict[str, dict]:
    """columna del Excel → {"id": instrumento o None, "motivo"}."""
    ins = [dict(r) for r in con.execute("SELECT id, clave, serie, clase, mercado_operable, listado_referencia, "
                                        "moneda_referencia FROM instrumentos")]
    ids = {i["id"] for i in ins}
    bmv = {(i["clave"] + (i["serie"] or "").replace("*", "")).replace(" ", "").upper(): i["id"]
           for i in ins if i["mercado_operable"] == "BMV"}
    usd = {(i["listado_referencia"] or "").upper(): i["id"] for i in ins if i["moneda_referencia"] == "USD"}
    out = {}
    for c in columnas:
        if c in PERFILES:
            out[c] = {"id": None, "motivo": "perfil índice (construcción no documentada)"}
        elif c in HOMONIMOS:
            out[c] = {"id": None, "motivo": HOMONIMOS[c]}
        elif c.upper().endswith(".MX"):
            base = c[:-3].upper()
            fondo = f"FONDO:{base[:-1]}" if base.endswith("B") else None
            if fondo in ids:
                out[c] = {"id": fondo, "motivo": ""}
            elif base in bmv:
                out[c] = {"id": bmv[base], "motivo": ""}
            else:
                out[c] = {"id": None, "motivo": "no está en el catálogo del simulador"}
        else:
            iid = usd.get(c.upper().replace("-", "."))
            out[c] = {"id": iid, "motivo": "" if iid else "no está en el catálogo del simulador"}
    return out


# ---------------------------------------------------------------------------------------------- verificación
def _local(con, iid: str) -> pd.DataFrame:
    filas = con.execute("SELECT fecha, cierre, cierre_ajustado, proveedor, moneda FROM precios WHERE instrumento_id=? "
                        "AND proveedor NOT IN ('demo_sintetico','alpaca_vivo','finviz_vivo','archivo')", (iid,)).fetchall()
    df = pd.DataFrame([tuple(f) for f in filas], columns=["fecha", "cierre", "aj", "proveedor", "moneda"])
    if df.empty:
        return df
    df["prio"] = df["proveedor"].map(mercado.prioridad_fuente)
    df = df.sort_values(["fecha", "prio"]).drop_duplicates("fecha").set_index("fecha")
    df.index = pd.to_datetime(df.index)
    return df


def _comparar(x: pd.Series, y: pd.Series) -> dict:
    """Rendimientos diarios de dos series de precios en las fechas consecutivas comunes."""
    comun = x.dropna().index.intersection(y.dropna().index)
    if len(comun) < MIN_SOLAPE + 1:
        return {"n": max(len(comun) - 1, 0)}
    rx, ry = x.loc[comun].pct_change().iloc[1:], y.loc[comun].pct_change().iloc[1:]
    d = (rx - ry).abs()
    return {"n": int(len(d)), "correlacion": round(float(np.corrcoef(rx, ry)[0, 1]), 4),
            "dif_mediana": round(float(d.median()), 5), "dif_max": round(float(d.max()), 4),
            "fecha_dif_max": str(d.idxmax().date()), "desde": str(comun[0].date()), "hasta": str(comun[-1].date())}


def _calidad(s: pd.Series) -> dict:
    s = s.dropna()
    r = s.pct_change().dropna()
    plano = 0
    for v in s.iloc[::-1]:  # sesiones finales con el mismo valor (dato que dejó de actualizarse)
        if v != s.iloc[-1]:
            break
        plano += 1
    return {"desde": str(s.index[0].date()), "hasta": str(s.index[-1].date()), "sesiones": int(len(s)),
            "saltos_50pct": int((r.abs() > 0.5).sum()), "final_sin_cambio": plano - 1}


def verificar(con, df: pd.DataFrame | None = None, adr_base: Path | None = None) -> dict:
    """Informe por columna: calidad interna, comparación con la serie local y, en BMV, con el ADR en MXN."""
    from . import proxy_adr as pa
    df = cargar() if df is None else df
    mapa = mapear(con, df.columns)
    fx = None
    filas = []
    for c in df.columns:
        m = mapa[c]
        fila = {"columna": c, "id": m["id"], "motivo": m["motivo"], **_calidad(df[c])}
        if m["id"]:
            loc = _local(con, m["id"])
            if loc.empty:
                fila.update(estado="sin verificar", motivo="la terminal no tiene serie local para comparar")
            else:
                aj = loc["aj"].where(loc["aj"].notna(), loc["cierre"])
                vs_aj, vs_cierre = _comparar(df[c], aj), _comparar(df[c], loc["cierre"])
                fila["vs_local"] = {"proveedores": sorted(loc["proveedor"].unique()), "ajustado": vs_aj,
                                    "cierre": vs_cierre}
                mejor = max((vs_aj, vs_cierre), key=lambda v: v.get("correlacion", -1))
                if mejor.get("n", 0) < MIN_SOLAPE:
                    fila.update(estado="sin verificar", motivo=f"solo {mejor.get('n', 0)} sesiones en común con la serie local")
                elif mejor["correlacion"] >= MIN_CORRELACION and mejor["dif_mediana"] <= MAX_DIF_MEDIANA:
                    fila.update(estado="verificada", motivo="")
                else:
                    fila.update(estado="rechazada", motivo=f"no coincide con la serie local (correlación "
                                                          f"{mejor['correlacion']:.2f}, dif. mediana {mejor['dif_mediana']:.2%})")
                if m["id"] in pa.MAPA:  # verificación independiente de BMV: ADR en MXN, historia larga
                    if fx is None:
                        from .config import cargar_ajustes
                        fx = mercado.fx_serie(con, cargar_ajustes())
                    prox = pa.retornos_mxn(pa.MAPA[m["id"]], fx, adr_base)
                    if not prox.empty:
                        v = pa.validar(df[c].pct_change(fill_method=None).dropna(), prox)
                        fila["vs_adr"] = {"adr": pa.MAPA[m["id"]], **v}
        else:
            fila["estado"] = "no usada"
        filas.append(fila)
    cuenta = {}
    for f in filas:
        cuenta[f["estado"]] = cuenta.get(f["estado"], 0) + 1
    return {"filas": filas, "resumen": cuenta, "perfiles": perfiles(df)}


def aceptadas(informe: dict) -> dict[str, str]:
    """columna → id de las verificadas (las que pueden extender historia)."""
    return {f["columna"]: f["id"] for f in informe["filas"] if f.get("estado") == "verificada"}


# ---------------------------------------------------------------------------------------------- perfiles
def perfiles(df: pd.DataFrame) -> dict:
    out = {}
    for p in PERFILES:
        if p not in df.columns:
            continue
        s = df[p].dropna()
        r = s.pct_change().dropna()
        anios = (s.index[-1] - s.index[0]).days / 365.25
        acum = s / s.cummax() - 1
        por_anio = s.resample("YE").last()
        out[p] = {"desde": str(s.index[0].date()), "hasta": str(s.index[-1].date()),
                  "rend_anual": round(float((s.iloc[-1] / s.iloc[0]) ** (1 / anios) - 1), 4),
                  "vol_anual": round(float(r.std() * np.sqrt(252)), 4), "max_caida": round(float(acum.min()), 4),
                  "anios": {str(i.year): round(float(v), 4) for i, v in por_anio.pct_change().dropna().items()}}
    return out


# ---------------------------------------------------------------------------------------------- extensión
def retornos_mxn(con, ajustes, df: pd.DataFrame, cols: dict[str, str]) -> pd.DataFrame:
    """Rendimientos diarios en MXN de las columnas aceptadas, con columnas = id de instrumento."""
    monedas = {r[0]: r[1] for r in con.execute("SELECT id, moneda_referencia FROM instrumentos")}
    P = df[list(cols)].rename(columns=cols)
    P = P.loc[:, ~P.columns.duplicated()]
    usd = [c for c in P.columns if monedas.get(c) == "USD"]
    if usd:
        fx = mercado.fx_serie(con, ajustes)
        fx_al = fx.reindex(P.index.union(fx.index)).ffill(limit=3).reindex(P.index)
        P[usd] = P[usd].mul(fx_al, axis=0)
    return P.ffill(limit=3).pct_change(fill_method=None)


def extender(con, ajustes, R: pd.DataFrame, informe: dict | None = None, df: pd.DataFrame | None = None
             ) -> tuple[pd.DataFrame, list[dict]]:
    """Agrega, antes del primer dato local de cada instrumento, los rendimientos MXN de la historia externa
    VERIFICADA. El índice de R se amplía con las sesiones anteriores. Devuelve (R extendida, informe por id)."""
    df = cargar() if df is None else df
    informe = informe or verificar(con, df)
    cols = {c: i for c, i in aceptadas(informe).items() if i in R.columns}
    if not cols:
        return R, []
    X = retornos_mxn(con, ajustes, df, cols)
    idx = R.index.union(X.index[X.index < R.index.min()])
    R2 = R.reindex(idx)
    salida = []
    for iid in X.columns:
        primero = R[iid].first_valid_index()
        if primero is None:
            continue
        antes = X[iid].loc[X.index < primero].dropna()
        antes = antes.loc[antes.index.isin(idx)]
        R2.loc[antes.index, iid] = antes
        salida.append({"id": iid, "sesiones_agregadas": int(len(antes)),
                       "desde": str(antes.index[0].date()) if len(antes) else None})
    return R2, salida
