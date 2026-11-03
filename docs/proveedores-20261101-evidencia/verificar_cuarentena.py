"""Verificación de solo lectura contra el respaldo, sin publicar valores de precios."""
import hashlib
import json
from pathlib import Path
import sqlite3

RAIZ = Path(__file__).resolve().parents[2]
COPIA = RAIZ / "data/respaldos/terminal-20261102-200048-615000.db"


def abrir(ruta):
    con = sqlite3.connect(ruta.as_uri() + "?mode=ro", uri=True)
    con.execute("PRAGMA query_only=ON")
    return con


def huellas(con):
    cursor = con.execute("SELECT * FROM precios")
    nombres = [c[0] for c in cursor.description]
    resultado = set()
    for fila in cursor:
        texto = json.dumps(dict(zip(nombres, fila)), ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False)
        resultado.add(hashlib.sha256(texto.encode()).hexdigest())
    return resultado


with abrir(COPIA) as anterior, abrir(RAIZ / "data/terminal.db") as actual:
    antes, despues = huellas(anterior), huellas(actual)
    archivo = actual.execute("SELECT huella,datos_originales FROM precios_cuarentena").fetchall()
    archivadas = {huella for huella, _ in archivo}
    assert all(hashlib.sha256(texto.encode()).hexdigest() == huella for huella, texto in archivo)
    assert antes - despues == archivadas and len(archivadas) == 136
    assert not despues - antes
    tablas = [f[0] for f in anterior.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    otras = [t for t in tablas if t != "precios"]
    for tabla in otras:
        nombre = '"' + tabla.replace('"', '""') + '"'
        assert anterior.execute("SELECT COUNT(*) FROM " + nombre).fetchone() == actual.execute(
            "SELECT COUNT(*) FROM " + nombre).fetchone()
    resultado = {"filas_originales_archivadas_exactas": len(archivadas),
                 "filas_restantes_identicas": len(despues), "filas_nuevas_en_precios": 0,
                 "otras_tablas_con_recuento_conservado": len(otras),
                 "limite": "Los recuentos no certifican igualdad de contenido de otras tablas; no se leyeron sus valores."}
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
