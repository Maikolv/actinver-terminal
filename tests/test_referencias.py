"""Ayuda › Referencias y créditos: toda dependencia del proyecto y todo proveedor de datos del código está citado."""
import json
import re
import tomllib
from importlib import metadata
from pathlib import Path

from terminal import centro_conectores, ingesta
from terminal.flujo import servicio as flujo_servicio

RAIZ = Path(__file__).resolve().parents[1]
REF = json.loads((RAIZ / "web/static/referencias.json").read_text(encoding="utf-8"))
CITADOS = {i for g in REF["grupos"] for it in g["items"] for i in it["ids"]}


def _nombre(dep: str) -> str:
    return re.split(r"[<>=!~ ;\[]", dep, maxsplit=1)[0].strip().lower()


def test_toda_dependencia_esta_citada():
    py = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    deps = [*py["project"]["dependencies"], *(d for g in py["dependency-groups"].values() for d in g)]
    faltan = sorted({_nombre(d) for d in deps} - {c.lower() for c in CITADOS})
    assert not faltan, f"dependencias sin cita: {faltan}"
    npm = json.loads((RAIZ / "cloud-alerts/package.json").read_text(encoding="utf-8"))
    assert set(npm.get("devDependencies", {})) <= CITADOS


def test_todo_proveedor_de_datos_esta_citado(con, ajustes):
    proveedores = {p["proveedor"] for p in ingesta.estado_proveedores(con, ajustes)}
    base = centro_conectores.ContextoAPI
    proveedores |= {c.proveedor for c in vars(centro_conectores).values()
                    if isinstance(c, type) and issubclass(c, base) and c is not base}
    proveedores |= {p["id"] for p in flujo_servicio.estado(con, ajustes)["proveedores"]}
    proveedores |= {ingesta.PROVEEDOR_VIVO, "actinver_portal", "actinver_pdf"}
    faltan = sorted(proveedores - CITADOS)
    assert not faltan, f"proveedores sin cita: {faltan}"


def test_cada_referencia_tiene_nombre_y_uso():
    for g in REF["grupos"]:
        for it in g["items"]:
            assert it["nombre"] and it["uso"] and it["ids"], it


def test_licencias_del_software_instalado_coinciden_con_sus_metadatos():
    """Comprueba cada paquete Python instalado; los opcionales ausentes no tienen metadatos locales."""
    software = next(g["items"] for g in REF["grupos"] if g["titulo"] == "Software")
    errores = []
    for item in software:
        for nombre in item["ids"]:
            if nombre in {"wrangler", "kronos", "backtesting.py"}:
                continue  # herramientas externas o código opcional sin distribución instalada
            try:
                datos = metadata.metadata(nombre)
            except metadata.PackageNotFoundError:
                continue  # grupo opcional no instalado en este entorno
            esperado = item["licencias"][nombre]
            expresion = datos.get("License-Expression") or ""
            licencia = datos.get("License") or ""
            clasificadores = " ".join(c for c in datos.get_all("Classifier", []) if c.startswith("License ::"))
            real = f"{expresion} {licencia[:100]} {clasificadores}".lower()
            clave = esperado.lower().split(" o ")[0].split("/")[0].split(" (")[0]
            if clave.startswith("bsd-3") and ("bsd-3" in real or "bsd 3-clause" in real or "bsd license" in real):
                continue
            if clave == "apache-2.0" and ("apache-2.0" in real or "apache software license" in real):
                continue
            if clave == "mit-cmu" and "mit-cmu" in real:
                continue
            if clave and clave not in real:
                errores.append(f"{nombre}: referencia {esperado!r}; metadatos {real[:90]!r}")
    assert not errores, "licencias que no coinciden:\n" + "\n".join(errores)


FAMILIAS = [("HPND", r"MIT-CMU|HPND|Historical Permission"), ("0BSD", r"\b0BSD\b"), ("BSD", r"(?<![0-9])BSD"),
            ("MIT", r"\bMIT\b(?!-CMU)"), ("APACHE", r"Apache"), ("MPL", r"\bMPL|Mozilla"), ("ZLIB", r"Zlib"),
            ("CC0", r"CC0"), ("AGPL", r"AGPL|Affero"), ("LGPL", r"LGPL|Lesser General")]


def _familias(texto: str) -> set[str]:
    return {f for f, rx in FAMILIAS if re.search(rx, texto, re.I)}


def test_licencias_declaradas_coinciden_con_los_metadatos_instalados():
    from importlib import metadata
    revisados, distintas = 0, []
    for g in REF["grupos"]:
        for it in g["items"]:
            for paquete, declarada in it.get("licencias", {}).items():
                try:
                    m = metadata.metadata(paquete)
                except metadata.PackageNotFoundError:
                    continue  # opcional no instalado (Kronos, torch) o herramienta externa (uv, wrangler)
                licencia = m.get("License") or ""
                texto = " ".join([m.get("License-Expression") or "", licencia if len(licencia) < 200 else licencia[:200],
                                  *(c for c in (m.get_all("Classifier") or []) if c.startswith("License"))])
                revisados += 1
                if _familias(declarada) != _familias(texto):
                    distintas.append((paquete, declarada, sorted(_familias(texto))))
    assert revisados >= 20 and not distintas, distintas
