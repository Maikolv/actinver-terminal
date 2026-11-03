"""Lecturas guardadas de investigación, sin importar ni entrenar modelos."""
from __future__ import annotations

import json
import sqlite3


def ultimo(con: sqlite3.Connection, H: int, demo: bool) -> dict | None:
    for (txt,) in con.execute("SELECT resultados FROM experimentos ORDER BY id DESC LIMIT 50"):
        r = json.loads(txt)
        if r.get("H") == H and r.get("demo") == demo:
            return r
    return None
