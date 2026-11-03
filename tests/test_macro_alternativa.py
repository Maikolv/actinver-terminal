"""Respaldo mensual oficial: unidades, cortes y ausencia de reemplazos antiguos."""
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

import httpx
import pytest

from terminal import centro_investigacion as centro, mesa_datos
from terminal.verificacion_gratuita import verificar

AHORA = datetime(2026, 11, 1, 20, tzinfo=UTC)


def guardar(con, fuente, serie, periodo, valor, unidad):
    origen = next(f for f in centro.fuentes() if f['id'] == fuente)
    fila = {'serie': serie, 'periodo': periodo, 'valor': valor, 'unidad': unidad,
            'titulo': serie, 'simbolo': '', 'texto': ''}
    centro._guardar(con, [centro._validar(fila, origen, AHORA, 'api')], AHORA)
    con.commit()


def test_respaldo_tres_consultas_sin_alterar_precios_y_cpi_exactamente_interanual(con, ajustes):
    consultas = []
    def responder(r):
        sid = r.url.params['series_id']
        consultas.append(sid)
        valores = {'UNRATE': [('2026-10-01', '4.2')], 'PAYEMS': [('2026-10-01', '159000')],
                   'CPIAUCSL': [('2026-10-01', '300'), ('2025-10-01', '200'), ('2025-09-01', '.')]}[sid]
        return httpx.Response(200, json={'observations': [{'date': d, 'value': v} for d, v in valores]})
    antes = con.execute('SELECT COUNT(*) FROM precios').fetchone()[0]
    r = verificar(con, env={'FRED_API_KEY': 'ficticia'}, cliente=httpx.Client(transport=httpx.MockTransport(responder)),
        ahora=AHORA, guardar=True, solo=['fred_macro'], macro_laboral=True)
    assert consultas == ['UNRATE', 'PAYEMS', 'CPIAUCSL'] and r['solicitudes'] == 3
    assert r['fuentes']['MACRO-RESPALDO']['observaciones_validas'] == 5
    series = {f['serie']: f for f in mesa_datos.macro(con, ajustes, AHORA)['series']}
    assert series['CPI_YOY']['valor'] == pytest.approx(50)
    assert series['LNS14000000']['valor'] == 4.2 and series['LNS14000000']['serie_fuente'] == 'UNRATE'
    assert series['CES0000000001']['valor'] == 159000 and series['CES0000000001']['unidad'] == 'miles de personas'
    assert all(series[s]['fuente'] == 'fred_macro' for s in ('CPI_YOY','LNS14000000','CES0000000001'))
    assert con.execute('SELECT COUNT(*) FROM precios').fetchone()[0] == antes
    previa = next(f for f in mesa_datos.macro(con, ajustes, AHORA-timedelta(seconds=1))['series'] if f['serie'] == 'LNS14000000')
    assert previa['valor'] is None


@pytest.mark.parametrize('primaria,esperada', [('2026-09','fred_macro'),('2026-10','bls'),('2026-11','bls')])
def test_misma_fecha_prefiere_bls_y_no_sustituye_fresca_por_respaldo_antiguo(con, ajustes, primaria, esperada):
    guardar(con, 'fred_macro', 'UNRATE', '2026-10-01', 4.2, '%')
    guardar(con, 'bls', 'LNS14000000', primaria, 4.3, '%')
    f = next(f for f in mesa_datos.macro(con, ajustes, AHORA)['series'] if f['serie'] == 'LNS14000000')
    assert f['fuente'] == esperada
    assert f['valor'] == (4.2 if esperada == 'fred_macro' else 4.3)


def test_respaldo_no_amplia_seleccion_ni_consulta_sin_clave(con):
    cli = httpx.Client(transport=httpx.MockTransport(lambda r: pytest.fail('No consultar')))
    with pytest.raises(ValueError, match='solo permite'):
        verificar(con,env={},cliente=cli,macro_laboral=True)
    r = verificar(con,env={},cliente=cli,macro_laboral=True,solo=['fred_macro'])
    assert r['solicitudes'] == 0


@pytest.mark.parametrize('periodo,valor', [('2025-09-01', 200), ('2025-10-01', 0)])
def test_cpi_no_improvisa_base_interanual_ni_divide_entre_cero(con, ajustes, periodo, valor):
    guardar(con, 'fred_macro', 'CPIAUCSL', '2026-10-01', 300, 'índice')
    guardar(con, 'fred_macro', 'CPIAUCSL', periodo, valor, 'índice')
    fila = next(f for f in mesa_datos.macro(con, ajustes, AHORA)['series'] if f['serie'] == 'CPI_YOY')
    assert fila['valor'] is None and fila['estado'] == 'SIN DATO'


def test_reels_pendientes_no_atribuyen_autores_ni_repositorios():
    ruta = Path(__file__).resolve().parents[1] / 'config/reels-20261101.json'
    filas = json.loads(ruta.read_text(encoding='utf-8'))
    assert {f['id'] for f in filas} == {'DfLZk23jLGs','DfKkuOOOSA8','DfHxxjztOkR'}
    for f in filas:
        assert f['url'] == 'https://www.instagram.com/p/'+f['id']+'/'
        assert f['contenido_verificado'] is False and f['autor'] is None and f['repositorios'] == []
