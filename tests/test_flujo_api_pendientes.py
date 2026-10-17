"""Rutas nuevas de lectura: base temporal, sin red, aislamiento y límites HTTP."""
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from terminal.flujo import almacen
from terminal.flujo.contratos import OperacionOpcion, Procedencia
from terminal.seguridad import Seguridad, TOKEN_CSRF


@pytest.fixture
def cliente_pendientes(con, ajustes, monkeypatch):
    import terminal.app as modulo
    monkeypatch.setattr(modulo, 'AJUSTES', ajustes)
    app = FastAPI()
    rutas = {'/api/flujo/skylit', '/api/flujo/perfiles', '/api/flujo/actualizar'}
    for ruta in modulo.app.routes:
        if getattr(ruta, 'path', None) in rutas:
            app.add_api_route(ruta.path, ruta.endpoint, methods=ruta.methods)
    app.dependency_overrides[modulo.con_db] = lambda: con
    app.add_middleware(Seguridad)
    with TestClient(app, base_url='http://127.0.0.1:8765') as cliente:
        yield cliente


def test_get_skylit_cinta_persistida_sin_futuro_ni_sintetico(cliente_pendientes, con):
    t = (datetime.now(UTC)-timedelta(minutes=30)).replace(microsecond=0).isoformat()
    op = OperacionOpcion('MU271120C00100000', 'SIC:MU', t, 'X', 5, 10, ['A'], t, '2027-11-20', 100, 'call')
    p = Procedencia('alpaca','prueba HTTP falsa','OPRA indicativo',feed='indicative',retraso_s=960)
    almacen.guardar_operaciones_opciones(con, [op], p)
    op.contrato = 'MU271120P00100000'
    almacen.guardar_operaciones_opciones(con, [op], Procedencia('demo','SINTÉTICO','prueba',calidad='sintetico'))
    op.contrato = 'MU271120C00200000'
    almacen.guardar_operaciones_opciones(con, [op], p)
    con.execute("UPDATE flujo_opciones_operaciones SET disponible_desde=? WHERE contrato=?",
                ((datetime.now(UTC)+timedelta(days=1)).isoformat(),op.contrato))
    r = cliente_pendientes.get('/api/flujo/skylit',params={'subyacente':'SIC:MU'})
    assert r.status_code == 200
    d = r.json()
    assert d['operaciones'] == 1 and not d['filtro_completo_aplicado']
    assert d['procedencia'][0]['feed'] == 'indicative'
    assert d['filas'][0]['criterios']['en_ask']['estado'] == 'no_evaluable'
    assert cliente_pendientes.get('/api/flujo/skylit').status_code == 422


def test_get_perfiles_sesion_vacia_y_validacion(cliente_pendientes):
    c = cliente_pendientes
    r = c.get('/api/flujo/perfiles',params={'simbolo':'SIC:MU'})
    assert r.status_code == 200
    assert r.json()['zona_horaria'] == 'America/New_York'
    assert r.json()['sesiones'] == []
    assert c.get('/api/flujo/perfiles',params={'simbolo':'SIC:MU','intervalo':'1Day'}).status_code == 422
    assert c.get('/api/flujo/perfiles',params={'simbolo':'CSV:SIN_SESION'}).json()['zona_horaria'] == 'sin configurar'
    assert c.get('/api/flujo/perfiles').status_code == 422


@pytest.mark.parametrize('ruta,parametros', [
    ('/api/flujo/skylit',{'subyacente':'SIC:MU'}),
    ('/api/flujo/perfiles',{'simbolo':'SIC:MU'})])
def test_lecturas_limitadas_y_host_local(cliente_pendientes, monkeypatch, ruta, parametros):
    from terminal import seguridad
    monkeypatch.setitem(seguridad.LIMITES_LECTURA,ruta,2)
    assert cliente_pendientes.get(ruta,params=parametros,headers={'Host':'malicioso.example'}).status_code == 400
    assert cliente_pendientes.get(ruta,params=parametros).status_code == 200
    assert cliente_pendientes.get(ruta,params=parametros).status_code == 200
    assert cliente_pendientes.get(ruta,params=parametros).status_code == 429


def test_post_skylit_conserva_csrf_y_validacion(cliente_pendientes):
    c = cliente_pendientes
    assert c.post('/api/flujo/skylit',json={'csv':'incorrecto'}).status_code == 403
    assert c.post('/api/flujo/skylit',json={'csv':'incorrecto'},headers={'X-CSRF-Token':TOKEN_CSRF}).status_code == 422
    assert c.post('/api/flujo/actualizar',json={'tipo':'opciones_operaciones','simbolo':'SIC:MU'}).status_code == 403


def test_corte_http_respeta_nanosegundos(monkeypatch):
    import httpx
    from terminal.flujo import adaptadores
    ahora = datetime.now(UTC).replace(microsecond=123456)
    class Reloj(datetime):
        @classmethod
        def now(cls, tz=None):
            return ahora
    monkeypatch.setattr(adaptadores,'datetime',Reloj)
    fin = ahora-timedelta(seconds=960)
    inicio = fin-timedelta(minutes=60)
    def sello(t, fraccion):
        return t.strftime('%Y-%m-%dT%H:%M:%S')+'.'+fraccion+'Z'
    sellos = [sello(fin,'123456001'),sello(fin,'123455999'),sello(inicio,'123455999')]
    def respuesta(req):
        return httpx.Response(200,json={'trades':{'MU271120C00100000':[
            {'t':t,'x':'X','p':1,'s':1,'c':[]} for t in sellos]}})
    with httpx.Client(transport=httpx.MockTransport(respuesta)) as cliente:
        a = adaptadores.Alpaca(env={'ALPACA_API_KEY_ID':'prueba','ALPACA_API_SECRET_KEY':'prueba'},cliente=cliente)
        ops,_ = a.operaciones_opciones(['MU271120C00100000'])
    assert [op.t_origen for op in ops] == [sellos[1]]


def test_skylit_no_une_instantes_con_nanosegundos_distintos(con, ajustes):
    from terminal.flujo import servicio
    from terminal.flujo.contratos import ContratoOpcion
    base = (datetime.now(UTC)-timedelta(minutes=30)).replace(microsecond=123456)
    normal = base.isoformat()
    raw = base.strftime('%Y-%m-%dT%H:%M:%S')+'.123456789Z'
    op = OperacionOpcion('MU271120C00100000','SIC:MU',normal,'X',5,2000,[],raw,'2027-11-20',100,'call')
    p = Procedencia('prueba','HTTP falso','OPRA')
    almacen.guardar_operaciones_opciones(con,[op],p)
    ct = ContratoOpcion(op.contrato,'SIC:MU','2027-11-20',100,'call',normal,multiplicador=100,spot=90,moneda='USD')
    almacen.guardar_opciones(con,[ct],p)
    resultado = servicio.skylit_guardado(con,ajustes,'SIC:MU')
    assert resultado['filas'][0]['prima_usd'] is None
    assert resultado['filas'][0]['criterios']['fuera_del_dinero']['estado'] == 'no_evaluable'
