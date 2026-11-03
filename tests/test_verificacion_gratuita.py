"""Pruebas HTTP simuladas de la verificación optativa; no credenciales reales ni red."""
from datetime import UTC, datetime, timedelta
import json
import re

import httpx
import pytest

from terminal import centro_investigacion as centro
from terminal.mesa_datos import macro
from terminal.proveedores_mesa import AlphaCalendario
from terminal.verificacion_gratuita import EMISORAS, verificar

AHORA = datetime(2026, 11, 1, 12, tzinfo=UTC)
ENV = {'FRED_API_KEY': 'fred-ficticia', 'BANXICO_TOKEN': 'sie-ficticia',
       'ALPHAVANTAGE_API_KEY': 'alpha-ficticia', 'SEC_USER_AGENT': 'Prueba prueba@example.test'}


def respuesta(r):
    if r.url.host == 'api.stlouisfed.org':
        assert r.url.params['series_id'] == 'DGS30'
        return httpx.Response(200, json={'observations': [{'date': '2026-10-30', 'value': '4.5'}]})
    if r.url.host == 'www.banxico.org.mx':
        sid = r.url.path.split('/series/')[1].split('/')[0]
        f = {'idSerie': sid, 'titulo': {'SP1': 'Índice Nacional de Precios al Consumidor',
             'SF61745': 'Tasa objetivo', 'SF123': 'Bonos M a 10 años'}[sid]}
        if r.url.path.endswith('/datos'):
            f['datos'] = [{'fecha': '30/10/2026', 'dato': '6.5'}]
        return httpx.Response(200, json={'bmx': {'series': [f]}})
    if r.url.host == 'data.sec.gov':
        cik = int(re.search(r'CIK(\d+)', r.url.path)[1])
        simbolo = next(s for s, c in EMISORAS.items() if c == cik)
        return httpx.Response(200, json={'cik': cik, 'tickers': [simbolo], 'filings': {'recent': {
            'form': ['8-K'], 'items': ['2.02'], 'acceptanceDateTime': ['2026-10-30T20:30:00Z'],
            'accessionNumber': [f'{cik:010d}-26-000001']}}})
    assert r.url.host == 'www.alphavantage.co' and r.url.params['function'] == 'EARNINGS_CALENDAR'
    return httpx.Response(200, text='symbol,reportDate,estimate,currency,fiscalDateEnding\nMU,2026-12-01,1.2,USD,2026-09-30\n')


def test_sin_credenciales_no_consulta_y_no_inventa_cierre(con):
    cli = httpx.Client(transport=httpx.MockTransport(lambda r: pytest.fail('Sin credenciales: no se consulta')))
    r = verificar(con, env={}, cliente=cli, ahora=AHORA, guardar=True)
    assert r['solicitudes'] == 0 and r['fuentes']['F6']['estado'] == 'requiere_seleccion_explicita'
    assert all(x['estado'] == 'sin_credencial_en_memoria' for k, x in r['fuentes'].items() if k != 'F6')
    assert con.execute('SELECT COUNT(*) FROM investigacion_observaciones').fetchone()[0] == 0


def test_diez_peticiones_identidad_y_conocimiento_sin_tocar_precios(con, ajustes):
    cli = httpx.Client(transport=httpx.MockTransport(respuesta))
    antes = con.execute('SELECT COUNT(*) FROM precios').fetchone()[0]
    r = verificar(con, env=ENV, cliente=cli, ahora=AHORA, guardar=True)
    assert r['solicitudes'] == 10
    assert all(f['estado'] == 'confirmado' for k, f in r['fuentes'].items() if k != 'F6')
    assert all(f['activado'] is False for f in r['fuentes'].values())
    assert all(v not in json.dumps(r) for v in ENV.values())
    assert con.execute('SELECT COUNT(*) FROM precios').fetchone()[0] == antes
    assert centro.observaciones(con, hasta=AHORA-timedelta(seconds=1)) == []
    assert len(centro.observaciones(con, hasta=AHORA)) == 8
    dato = next(x for x in macro(con, ajustes, AHORA)['series'] if x['serie'] == 'DGS30')
    assert dato['valor'] == 4.5 and 'requisito' not in dato
    assert centro.DEFAULTS['alpha_calendario']['plan_verificado'] is False
    assert set(__import__('terminal.centro_conectores', fromlist=['FredMacro']).FredMacro.SERIES) != {'DGS30'}


def test_rechazo_de_plan_una_vez_no_se_reintenta_ni_guarda(con):
    vistos = []
    def no_incluido(r):
        vistos.append(r)
        return httpx.Response(200, json={'Information': 'Acceso no incluido'})
    r = verificar(con, env={'ALPHAVANTAGE_API_KEY': ENV['ALPHAVANTAGE_API_KEY']},
                  cliente=httpx.Client(transport=httpx.MockTransport(no_incluido)), ahora=AHORA, guardar=True)
    assert len(vistos) == 1 and r['fuentes']['F1-ALPHA']['estado'] == 'respuesta_no_confirmada'
    assert con.execute('SELECT COUNT(*) FROM investigacion_observaciones').fetchone()[0] == 0


def test_prueba_manual_alpha_no_fabrica_plan_verificado(con):
    cfg = {'activo': True, 'plan_verificado': False}
    a = AlphaCalendario(con, cfg, ENV['ALPHAVANTAGE_API_KEY'], httpx.Client(transport=httpx.MockTransport(respuesta)))
    assert len(a.comprobar_acceso(AHORA)) == 1
    assert cfg['plan_verificado'] is False
    with pytest.raises(Exception, match='deshabilitado'):
        a.consultar(AHORA)


def test_respuesta_que_incluye_clave_no_se_persiste(con):
    def eco(r):
        return httpx.Response(200, text='symbol,reportDate,estimate,currency,fiscalDateEnding\n'
            'MU,2026-12-01,1.2,' + ENV['ALPHAVANTAGE_API_KEY'] + ',2026-09-30\n')
    r = verificar(con, env={'ALPHAVANTAGE_API_KEY': ENV['ALPHAVANTAGE_API_KEY']},
        cliente=httpx.Client(transport=httpx.MockTransport(eco)), ahora=AHORA, guardar=True)
    assert r['fuentes']['F1-ALPHA']['estado'] == 'respuesta_no_confirmada'
    assert ENV['ALPHAVANTAGE_API_KEY'] not in json.dumps(r)
    assert con.execute('SELECT COUNT(*) FROM investigacion_observaciones').fetchone()[0] == 0


def test_bono_solo_se_confirma_despues_del_get_y_sin_escritura_implicita(con):
    r = verificar(con, env={'BANXICO_TOKEN': ENV['BANXICO_TOKEN']},
        cliente=httpx.Client(transport=httpx.MockTransport(respuesta)), ahora=AHORA, bono10='SF123')
    assert r['fuentes']['F6']['estado'] == 'confirmado' and r['fuentes']['F6']['solicitudes'] == 2
    assert con.execute('SELECT COUNT(*) FROM investigacion_observaciones').fetchone()[0] == 0


def test_xom_usa_cik_actual_y_rechaza_entidad_historica(con):
    assert EMISORAS['XOM'] == 2115436  # Catálogo SEC consultado, no referencia histórica 34088.
    def historico(r):
        assert 'CIK0002115436.json' in r.url.path
        return httpx.Response(200, json={'cik': 34088, 'tickers': ['XOM']})
    r = verificar(con, env={'SEC_USER_AGENT': ENV['SEC_USER_AGENT']},
        cliente=httpx.Client(transport=httpx.MockTransport(historico)), ahora=AHORA,
        guardar=True, emisoras={'XOM': EMISORAS['XOM']})
    assert r['fuentes']['F1-SEC-XOM']['estado'] == 'respuesta_no_confirmada'
    assert con.execute('SELECT COUNT(*) FROM investigacion_observaciones').fetchone()[0] == 0


def test_seleccion_acotada_no_repite_sec_ni_amplia_a_fuentes_de_pago(con):
    r = verificar(con, env=ENV, cliente=httpx.Client(transport=httpx.MockTransport(respuesta)),
                  ahora=AHORA, solo=['fred_macro'])
    assert set(r['fuentes']) == {'F2'} and r['solicitudes'] == 1
    with pytest.raises(ValueError, match='cuatro fuentes gratuitas'):
        verificar(con, env=ENV, cliente=None, solo=['twelvedata'])


def test_cupo_configurado_mas_bajo_impide_solicitud(con, ajustes):
    ajustes.datos['centro_investigacion'] = {'fred_macro': {'peticiones_por_dia': 0}}
    cli = httpx.Client(transport=httpx.MockTransport(lambda r: pytest.fail('Cupo local agotado: no consultar')))
    r = verificar(con, env=ENV, cliente=cli, ahora=AHORA, solo=['fred_macro'], ajustes=ajustes)
    assert r['solicitudes'] == 0 and r['fuentes']['F2']['estado'] == 'cupo_o_espera'


@pytest.mark.parametrize('caso', ['base_no_sqlite', 'evidencia_existente'])
def test_cli_rechaza_archivos_antes_de_consultar(con, tmp_path, monkeypatch, caso):
    import importlib.util
    from pathlib import Path
    import sys
    ruta = Path(__file__).resolve().parents[1] / 'scripts/verificar_proveedores_gratuitos.py'
    spec = importlib.util.spec_from_file_location('verificador_gratis_cli_prueba', ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    base = Path(con.execute('PRAGMA database_list').fetchone()[2])
    evidencia = tmp_path / 'evidencia.json'
    if caso == 'base_no_sqlite':
        base = tmp_path / 'credenciales.txt'
        base.write_text('archivo ficticio que no se debe abrir', encoding='utf-8')
    else:
        evidencia.write_text('conservar', encoding='utf-8')
    monkeypatch.setattr(sys, 'argv', ['verificar', '--consultar', '--base', str(base), '--evidencia', str(evidencia)])
    monkeypatch.setattr(httpx.Client, 'get', lambda *a, **k: pytest.fail('Validación anterior a cualquier HTTP'))
    with pytest.raises(SystemExit) as e:
        modulo.main()
    assert e.value.code == 2
    if caso == 'evidencia_existente':
        assert evidencia.read_text(encoding='utf-8') == 'conservar'
