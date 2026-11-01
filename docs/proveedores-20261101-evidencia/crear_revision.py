"""Genera un diff acotado de esta entrega sin incorporar archivos ajenos ni secretos."""
from pathlib import Path
import difflib
import json
import subprocess

RAIZ = Path(__file__).resolve().parents[2]
EVIDENCIA = Path(__file__).resolve().parent
RESPALDOS = {
    'terminal/centro_conectores.py': 'centro_conectores.py.antes',
    'terminal/centro_investigacion.py': 'centro_investigacion.py.antes',
    'terminal/mesa_datos.py': 'mesa_datos.py.antes',
    'terminal/app.py': 'app.py.antes',
    'web/static/mesa.mjs': 'mesa.mjs.antes',
    'web/static/referencias.json': 'referencias.json.antes',
    'config/fuentes_investigacion.json': 'fuentes_investigacion.json.antes',
}
LIMPIOS_AL_INICIO = ['terminal/adaptadores/base.py', 'tests/test_centro_investigacion.py',
                    'docs/proveedores-gratuitos.md', 'docs/pendientes-terminal-pro-20261101.json', 'CLAUDE.md']
NUEVOS = ['terminal/proveedores_mesa.py', 'terminal/mesa_resultados.py', 'tests/test_proveedores_mesa.py',
          'docs/proveedores-mesa-20261101.md']
parche = []
resumen = []
for ruta in [*RESPALDOS, *LIMPIOS_AL_INICIO, *NUEVOS, 'CHANGELOG.md']:
    despues = (RAIZ / ruta).read_text(encoding='utf-8-sig')
    if ruta == 'CHANGELOG.md':
        inicio = despues.index('## [2026-11-01 — conectores opcionales de Mesa, sin activar proveedores]')
        fin = despues.index('\n## [', inicio + 1) + 1
        antes = despues[:inicio] + despues[fin:]
    elif ruta in RESPALDOS:
        antes = (EVIDENCIA / RESPALDOS[ruta]).read_text(encoding='utf-8-sig')
    elif ruta in LIMPIOS_AL_INICIO:
        antes = subprocess.check_output(['git', 'show', 'HEAD:' + ruta], cwd=RAIZ).decode('utf-8-sig')
    else:
        antes = ''
    if ruta == 'terminal/app.py':
        viejo = 'def mesa_resultados():\n    from . import mesa_datos\n    return mesa_datos.CONTRATO_RESULTADOS'
        nuevo = 'def mesa_resultados(con=Depends(con_db)):\n    from .mesa_resultados import calendario\n    return calendario(con)'
        assert viejo in antes and nuevo in despues
        despues = antes.replace(viejo, nuevo, 1)
    if ruta == 'web/static/mesa.mjs':
        inicio, fin = '  async function nativoCalendario(caja){', '  const NATIVOS='
        bloque_antes = antes[antes.index(inicio):antes.index(fin)]
        bloque_despues = despues[despues.index(inicio):despues.index(fin)]
        despues = antes.replace(bloque_antes, bloque_despues, 1)
    diferencia = list(difflib.unified_diff(antes.splitlines(True), despues.splitlines(True),
                                         fromfile='a/' + ruta, tofile='b/' + ruta))
    parche.extend(diferencia)
    resumen.append({'archivo': ruta, 'lineas_diff': len(diferencia)})
(EVIDENCIA / 'cambios-proveedores.patch').write_text(''.join(parche), encoding='utf-8')
(EVIDENCIA / 'archivos.json').write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(resumen, ensure_ascii=False))
