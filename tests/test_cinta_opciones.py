"""Cinta indicativa con HTTP falso: sin red ni credenciales reales."""
from datetime import UTC, datetime, timedelta
import httpx
import pytest
from terminal.flujo import almacen, servicio
from terminal.flujo.adaptadores import Alpaca, FuenteNoDisponible
from terminal.flujo.contratos import ContratoOpcion, Procedencia

CONTRATO = 'MU271120C00100000'


def cinta():
    t = (datetime.now(UTC) - timedelta(minutes=30)).replace(microsecond=0).isoformat()
    llamadas = []
    def responder(req):
        llamadas.append(req)
        assert req.url.host == 'data.alpaca.markets'
        assert req.url.path == '/v1beta1/options/trades'
        assert req.url.params['feed'] == 'indicative'
        assert datetime.fromisoformat(req.url.params['end']) <= datetime.now(UTC) - timedelta(minutes=15)
        return httpx.Response(200, json={'trades': {CONTRATO: [
            {'t': t, 'x': 'X', 'p': 10, 's': 200, 'c': ['A']},
            {'t': datetime.now(UTC).isoformat(), 'x': 'X', 'p': 10, 's': 1, 'c': []}]}})
    cli = httpx.Client(transport=httpx.MockTransport(responder))
    return Alpaca(env={'ALPACA_API_KEY_ID': 'prueba', 'ALPACA_API_SECRET_KEY': 'prueba'}, cliente=cli), llamadas


def test_cinta_http_corte_procedencia_y_validacion():
    a, llamadas = cinta()
    ops, proc = a.operaciones_opciones([CONTRATO], 60)
    assert len(ops) == 1 and ops[0].condiciones == ['A'] and ops[0].mercado_origen == 'X'
    assert proc.retraso_s >= 900 and proc.feed == 'indicative'
    assert len(llamadas) == 1
    with pytest.raises(ValueError):
        a.operaciones_opciones(['incorrecto'])
    with pytest.raises(FuenteNoDisponible, match='faltan'):
        Alpaca(env={}).operaciones_opciones([CONTRATO])


def test_guardado_dedup_y_sin_fuga_temporal(con, ajustes):
    a, _ = cinta()
    ops, proc = a.operaciones_opciones([CONTRATO])
    op = ops[0]
    assert almacen.guardar_operaciones_opciones(con, ops, proc) == 1
    assert almacen.guardar_operaciones_opciones(con, ops, proc) == 0
    assert not almacen.operaciones_opciones(con, 'MU', hasta=op.instante)
    filas = almacen.operaciones_opciones(con, 'MU')
    assert filas[0]['t'] == op.instante and filas[0]['c'] == ['A']
    # Una cadena de otra hora no es contexto simultáneo, aunque tenga bid/ask/multiplicador/spot.
    ct = ContratoOpcion(CONTRATO, 'MU', '2027-11-20', 100, 'call',
                        (datetime.fromisoformat(op.instante)-timedelta(minutes=1)).isoformat(),
                        bid=9, ask=10, multiplicador=100, spot=90, moneda='USD')
    almacen.guardar_opciones(con, [ct], proc)
    r = servicio.skylit_guardado(con, ajustes, 'MU')
    assert r['operaciones'] == 1 and not r['filtro_completo_aplicado']
    cr = r['filas'][0]['criterios']
    for k in ('prima','en_ask','fuera_del_dinero','una_pata','volumen_oi'):
        assert cr[k]['estado'] == 'no_evaluable'
    ct.instante = op.instante
    almacen.guardar_opciones(con, [ct], proc)
    r = servicio.skylit_guardado(con, ajustes, 'MU')
    assert r['filas'][0]['prima_usd'] == 200000
    assert r['filas'][0]['criterios']['en_ask']['estado'] == 'no_evaluable'
    assert not servicio.skylit_guardado(con, ajustes, 'MU', hasta=op.instante)['operaciones']


def test_sintetico_no_se_expone_en_real(con, ajustes):
    a, _ = cinta()
    ops, _ = a.operaciones_opciones([CONTRATO])
    almacen.guardar_operaciones_opciones(con, ops, Procedencia('prueba','SINTÉTICO','prueba',calidad='sintetico'))
    assert not servicio.skylit_guardado(con, ajustes, 'MU')['operaciones']


def test_actualizar_cinta_seleccion_explicita_y_cache(con, ajustes):
    from terminal.flujo.contratos import ContratoOpcion
    t = (datetime.now(UTC)-timedelta(minutes=30)).replace(microsecond=0).isoformat()
    nombres = [f'MU271120C{100000+i:08d}' for i in range(101)]
    assert CONTRATO in nombres
    proc = Procedencia('prueba','HTTP falso','OPRA')
    almacen.guardar_opciones(con,[ContratoOpcion(c,'SIC:MU','2027-11-20',100,'call',t) for c in nombres],proc)
    con.commit()
    llamadas = []
    def responder(req):
        llamadas.append(req)
        assert req.url.path == '/v1beta1/options/trades'
        assert req.url.params['symbols'] == CONTRATO
        return httpx.Response(200,json={'trades':{CONTRATO:[{'t':t,'x':'X','p':5,'s':10,'c':[]}]}})
    env = {'ALPACA_API_KEY_ID':'prueba','ALPACA_API_SECRET_KEY':'prueba'}
    with httpx.Client(transport=httpx.MockTransport(responder)) as cli:
        r = servicio.actualizar(con,ajustes,'opciones_operaciones','SIC:MU',env=env,cliente=cli)
        assert r['estado'] == 'sin_fuente' and 'lista explícita' in r['mensaje']
        r = servicio.actualizar(con,ajustes,'opciones_operaciones','SIC:MU',env=env,cliente=cli,contratos=['OTRO'])
        assert r['estado'] == 'error'
        r = servicio.actualizar(con,ajustes,'opciones_operaciones','SIC:MU',env=env,cliente=cli,contratos=[CONTRATO])
        assert r['estado'] == 'ok' and r['registros'] == 1
        r = servicio.actualizar(con,ajustes,'opciones_operaciones','SIC:MU',env=env,cliente=cli,contratos=[CONTRATO])
        assert r['estado'] == 'en_espera'
    assert len(llamadas) == 1
