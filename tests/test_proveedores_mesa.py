"""Contratos oficiales simulados: identidad, cupos y conocimiento temporal, sin red."""
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from terminal import centro_investigacion as centro, mesa_datos
from terminal.adaptadores.base import ErrorProveedor, LimiteAlcanzado
from terminal.centro_conectores import FredMacro
from terminal.mesa_resultados import calendario
from terminal.proveedores_mesa import AlphaCalendario, BanxicoSIE, ConsultaMesa, SECResultados, comprobar_twelve_basico

AHORA = datetime(2026, 10, 30, 23, tzinfo=UTC)


def cliente(responder):
    return httpx.Client(transport=httpx.MockTransport(responder))


def guardar(con, fuente, serie, valor, texto='', cuando=AHORA, simbolo=''):
    centro.inicializar(con)
    origen = next(f for f in centro.fuentes() if f['id'] == fuente)
    fila = centro._validar({'fuente': fuente, 'serie': serie, 'valor': valor, 'texto': texto,
        'simbolo': simbolo, 'periodo': min(cuando.date().isoformat(), '2026-10-29'), 'unidad': '%' if not simbolo else 'USD/acción',
        'titulo': 'Prueba simulada', 'url': origen['url']}, origen, cuando, 'api')
    centro._guardar(con, [fila], cuando)
    con.commit()


def test_f2_dgs30_se_solicita_y_macro_no_exige_requisito_con_dato(con, ajustes):
    vistos = []
    def responder(r):
        vistos.append(r.url.params['series_id'])
        return httpx.Response(200, json={'observations': [{'date': '2026-10-29', 'value': '4.5'}]})
    filas = FredMacro(con, {}, 'ficticia', cliente(responder)).consultar(AHORA)
    assert 'DGS30' in vistos and len(vistos) == 5
    fila = next(f for f in filas if f['serie'] == 'DGS30')
    guardar(con, 'fred_macro', 'DGS30', fila['valor'])
    dato = next(s for s in mesa_datos.macro(con, ajustes, AHORA)['series'] if s['serie'] == 'DGS30')
    assert dato['valor'] == 4.5 and 'requisito' not in dato


@pytest.mark.parametrize('tema,sid,titulo,unidad', [
    ('BANXICO_OBJETIVO', 'SF61745', 'Tasa objetivo de política monetaria', '%'),
    ('BANXICO_BONO10', 'SF123', 'Bonos M a tasa fija a 10 años', '%'),
    ('INPC', 'SP123', 'Índice Nacional de Precios al Consumidor', 'índice'),
])
def test_f3_f4_f6_catalogo_antes_de_datos_y_ausentes(con, tema, sid, titulo, unidad):
    vistos = []
    def responder(r):
        vistos.append(r.url.path)
        assert r.headers['Bmx-Token'] == 'ficticia'
        f = {'idSerie': sid, 'titulo': titulo}
        if r.url.path.endswith('/datos'):
            f['datos'] = [{'fecha': '29/10/2026', 'dato': '6.5'}, {'fecha': '30/10/2026', 'dato': 'N/E'},
                          {'fecha': '01/12/2026', 'dato': '7'}]
        return httpx.Response(200, json={'bmx': {'series': [f]}})
    cfg = {'series': dict.fromkeys(BanxicoSIE.CANDIDATOS), 'peticiones_por_dia': 20}
    cfg['series'][tema] = sid  # IDs ficticios: no constituyen confirmación oficial.
    filas = BanxicoSIE(con, cfg, 'ficticia', cliente(responder)).consultar(AHORA)
    assert len(vistos) == 2 and vistos[1] == vistos[0] + '/datos'
    assert len(filas) == 1 and filas[0]['unidad'] == unidad
    guardar(con, 'banxico_sie', tema, filas[0]['valor'])
    assert centro.observaciones(con, hasta=AHORA-timedelta(seconds=1)) == []
    o = centro.observaciones(con, hasta=AHORA)[0]
    assert o['huella'] and datetime.fromisoformat(o['disponible_desde']) == AHORA


@pytest.mark.parametrize('titulo', ['CETES 28 días', 'Tasa de interés interbancaria'])
def test_titulo_no_confirmado_impide_solicitud_y_escritura(con, titulo):
    vistos = []
    def responder(r):
        vistos.append(r)
        return httpx.Response(200, json={'bmx': {'series': [{'idSerie': 'SF61745', 'titulo': titulo}]}})
    with pytest.raises(ErrorProveedor, match='SIN DATO'):
        BanxicoSIE(con, {}, 'ficticia', cliente(responder)).consultar(AHORA)
    assert len(vistos) == 1
    assert con.execute('SELECT COUNT(*) FROM investigacion_observaciones').fetchone()[0] == 0


@pytest.mark.parametrize('tema,titulo', [('BANXICO_BONO10', 'UDIBONOS 10 años'),
    ('BANXICO_BONO10', 'Bonos M 3 años'), ('INPC', 'Índice Nacional de Precios al Consumidor variación anual')])
def test_identidades_no_equivalentes(tema, titulo):
    assert not BanxicoSIE.coincide(tema, titulo)


@pytest.mark.parametrize('cabecera', ['120', 'Fri, 30 Oct 2026 23:02:00 GMT'])
def test_retry_after_persistente_sin_reintento(con, cabecera):
    vistos = []
    def responder(r):
        vistos.append(r)
        return httpx.Response(429, headers={'Retry-After': cabecera})
    a = ConsultaMesa(con, {}, 'ficticia', cliente(responder))
    a.proveedor = 'banxico_sie'
    with pytest.raises(ErrorProveedor, match='Retry-After'):
        a._peticion('https://www.banxico.org.mx/', ahora=AHORA)
    with pytest.raises(LimiteAlcanzado):
        a._peticion('https://www.banxico.org.mx/', ahora=AHORA+timedelta(seconds=60))
    assert len(vistos) == 1


def test_cupo_por_minuto_y_cupo_compartido_alpha(con):
    a = ConsultaMesa(con, {'peticiones_por_minuto': 1, 'peticiones_por_dia': 100}, 'ficticia',
                     cliente(lambda r: httpx.Response(200)))
    a.proveedor = 'alpha_calendario'
    a._peticion('https://www.alphavantage.co/query', ahora=AHORA)
    with pytest.raises(LimiteAlcanzado):
        a._peticion('https://www.alphavantage.co/query', ahora=AHORA)
    assert {r[0] for r in con.execute('SELECT proveedor FROM uso_proveedor')} == {'alpha_vantage'}


def test_alpha_csv_fecha_prevista_futura_no_es_disponibilidad(con):
    a = AlphaCalendario(con, {'plan_verificado': True}, 'ficticia', cliente(lambda r: httpx.Response(200,
        text='symbol,reportDate,estimate,currency,fiscalDateEnding\nMU,2026-12-01,1.2,USD,2026-09-30\n')))
    o = a.consultar(AHORA)[0]
    assert o['periodo'] == '2026-10-30' and o['serie'] == 'estimacion_bpa:2026-12-01'
    assert json.loads(o['texto'])['hora_anuncio'] is None


@pytest.mark.parametrize('verificado', [False, True])
def test_alpha_no_infiere_permiso_del_plan(con, verificado):
    vistos = []
    def responder(r):
        vistos.append(r)
        return httpx.Response(200, json={'Information': 'Acceso no incluido'})
    with pytest.raises(ErrorProveedor):
        AlphaCalendario(con, {'plan_verificado': verificado}, 'ficticia', cliente(responder)).consultar(AHORA)
    assert len(vistos) == int(verificado)


def test_sec_202_no_infiere_hora_anuncio_ni_bpa(con):
    def responder(r):
        assert '@' in r.headers['User-Agent']
        return httpx.Response(200, json={'cik': '123', 'tickers': ['MU'], 'filings': {'recent': {
            'form': ['8-K', '8-K', '8-K'], 'items': ['2.02', '12.02', '2.02'],
            'acceptanceDateTime': ['2026-10-29T21:00:00Z', '2026-10-29T21:00:00Z', '2026-12-01T21:00:00Z'],
            'accessionNumber': ['0000000123-26-000001']*3}}})
    o = SECResultados(con, {'emisoras': {'MU': 123}}, 'Prueba prueba@example.test', cliente(responder)).consultar(AHORA)
    assert len(o) == 1
    m = json.loads(o[0]['texto'])
    assert m.get('hora_anuncio') is None and m['momento'] is None
    assert m['fecha_reporte'] is None and m['reportado_bpa'] is None
    guardar(con, 'sec_resultados', o[0]['serie'], None, o[0]['texto'], simbolo='MU')
    r = calendario(con, AHORA)['resultados'][0]
    assert r['fecha_publicacion_sec'] and r['reaccion']['estado'] == 'SIN DATO'


def test_calendario_revisiones_y_corte_no_usa_estimacion_posterior(con):
    anuncio = '2026-10-29T20:30:00+00:00'
    meta = json.dumps({'fecha_reporte': '2026-10-29', 'momento': 'despues', 'hora_anuncio': anuncio, 'anuncio_verificado': True})
    temprano = datetime(2026, 10, 28, 12, tzinfo=UTC)
    guardar(con, 'alpha_calendario', 'estimacion_bpa:2026-10-29', 1.0, meta, temprano, 'MU')
    guardar(con, 'alpha_calendario', 'estimacion_bpa:2026-10-29', 9.0, meta, AHORA, 'MU')
    guardar(con, 'sec_resultados', 'reportado_bpa', 1.2, meta, AHORA, 'MU')
    guardar(con, 'sec_resultados', 'revisado_bpa', 1.3, meta, AHORA+timedelta(seconds=1), 'MU')
    r = calendario(con, AHORA)['resultados'][0]
    assert r['estimacion_bpa']['valor'] == 1.0 and r['reportado_bpa']['valor'] == 1.2
    assert r['revisado_bpa'] is None and r['estimacion_posterior_no_utilizada']
    assert calendario(con, AHORA+timedelta(seconds=1))['resultados'][0]['revisado_bpa']['valor'] == 1.3


def test_conectores_apagados_por_defecto(con, ajustes):
    ajustes.datos['centro_investigacion'] = {'bls': {'activo': False}}
    r = centro.actualizar(con, ajustes, AHORA, env={'BANXICO_TOKEN': 'ficticia',
        'SEC_USER_AGENT': 'Prueba prueba@example.test', 'ALPHAVANTAGE_API_KEY': ''},
        cliente=cliente(lambda r: pytest.fail('Conectores optativos apagados: no se consulta')))
    assert all(r['fuentes'][s]['estado'] == 'desactivada' for s in ('banxico_sie', 'sec_resultados', 'alpha_calendario'))


def test_f5_sin_clave_o_catalogo_no_consulta_ni_habilita(con):
    cli = cliente(lambda r: pytest.fail('No debe consultar'))
    r = comprobar_twelve_basico(con, {}, None, {}, cli, AHORA)
    assert r['consultas'] == 0
    assert comprobar_twelve_basico(con, {}, 'ficticia', {'mercado': 'SIC'}, cli, AHORA)['consultas'] == 0


def test_banxico_actualizar_persiste_fuente_real_y_no_precios(con, ajustes):
    ajustes.datos['centro_investigacion'] = {'banxico_sie': {'activo': True}, 'bls': {'activo': False}}
    def responder(r):
        fila = {'idSerie': 'SF61745', 'titulo': 'Tasa objetivo'}
        if r.url.path.endswith('/datos'):
            fila['datos'] = [{'fecha': '29/10/2026', 'dato': '6.5'}]
        return httpx.Response(200, json={'bmx': {'series': [fila]}})
    antes = con.execute('SELECT COUNT(*) FROM precios').fetchone()[0]
    r = centro.actualizar(con, ajustes, AHORA, env={'BANXICO_TOKEN': 'ficticia'}, cliente=cliente(responder))
    assert r['fuentes']['banxico_sie']['estado'] == 'ok' and r['nuevos'] == 1
    o = centro.observaciones(con, hasta=AHORA)[0]
    assert o['fuente'] == 'banxico_sie' and o['origen'] == 'api' and o['unidad'] == '%'
    assert con.execute('SELECT COUNT(*) FROM precios').fetchone()[0] == antes


def test_revisiones_del_mismo_dia_no_ocultan_estimacion_previa(con):
    meta = json.dumps({'fecha_reporte': '2026-10-29', 'momento': 'despues',
                       'hora_anuncio': '2026-10-29T20:30:00+00:00', 'anuncio_verificado': True})
    guardar(con, 'alpha_calendario', 'estimacion_bpa:2026-10-29', 1, meta,
            datetime(2026, 10, 29, 12, tzinfo=UTC), 'MU')
    guardar(con, 'alpha_calendario', 'estimacion_bpa:2026-10-29', 9, meta, AHORA, 'MU')
    assert calendario(con, AHORA)['resultados'][0]['estimacion_bpa']['valor'] == 1


def test_sec_identificacion_invalida_es_error_controlado(con):
    with pytest.raises(ErrorProveedor, match='identificación'):
        SECResultados(con, {}, 'sin correo', cliente(lambda r: pytest.fail('No consultar'))).consultar(AHORA)


@pytest.mark.parametrize('permitido', [False, True])
def test_twelve_una_peticion_no_habilita_por_simbolo_de_prueba(con, permitido):
    vistos = []
    def responder(r):
        vistos.append(r)
        return httpx.Response(200, json=({'meta': {'mic_code': 'XMEX', 'symbol': 'GMEXICOB'},
            'values': [{'datetime': '2026-10-29', 'close': '100'}]} if permitido else
            {'code': 403, 'message': 'No incluido'}))
    instrumento = {'id': 'BMV:GMEXICO', 'mercado_operable': 'BMV', 'clave': 'GMEXICO', 'serie': 'B'}
    r = comprobar_twelve_basico(con, {'peticiones_por_dia': 700}, 'ficticia', instrumento, cliente(responder), AHORA)
    assert len(vistos) == 1 and r['habilitado_automaticamente'] is False
    assert (r['estado'] == 'acceso_simbolo_confirmado') == permitido


def test_reloj_inyectado_abre_siguiente_ventana_minuto(con):
    a = ConsultaMesa(con, {'peticiones_por_minuto': 1, 'peticiones_por_dia': 2}, 'ficticia',
        cliente(lambda r: httpx.Response(200)))
    a._peticion('https://www.banxico.org.mx/', ahora=AHORA)
    a._peticion('https://www.banxico.org.mx/', ahora=AHORA+timedelta(minutes=1))
    with pytest.raises(LimiteAlcanzado):
        a._peticion('https://www.banxico.org.mx/', ahora=AHORA+timedelta(minutes=2))


@pytest.mark.parametrize('respuesta', [{'bmx': {'series': ['incorrecta']}}, {'bmx': {'series': None}}])
def test_banxico_respuesta_malformada_falla_cerrado(con, respuesta):
    with pytest.raises(ErrorProveedor, match='SIN DATO'):
        BanxicoSIE(con, {}, 'ficticia', cliente(lambda r: httpx.Response(200, json=respuesta))).consultar(AHORA)
