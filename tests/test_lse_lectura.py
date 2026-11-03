"""Contrato HTTP simulado de LSE: solo lectura, sin secretos ni precios de cartera."""
from datetime import UTC, datetime

import httpx
import pytest

from terminal.adaptadores.base import ErrorProveedor
from terminal.lse_lectura import LSELectura

AHORA = datetime(2026, 11, 1, 22, tzinfo=UTC)


def respuesta():
    return {'market':'us_stocks','symbol':'AAPL','timeframe':'1d','data':'candles','adjusted':True,
            'rows':[{'time':'2026-10-30 20:00:00','open':100,'high':105,'low':99,'close':103,'volume':50}]}


def test_muestra_solo_get_con_cabecera_no_secreto_en_url_y_sin_ingesta(con):
    vistos=[]
    def responder(r):
        vistos.append(r)
        assert r.method=='GET' and r.headers['X-API-Key']=='ficticia-lse'
        assert 'ficticia-lse' not in str(r.url)
        return httpx.Response(200,json=respuesta())
    cli=httpx.Client(transport=httpx.MockTransport(responder))
    antes=con.execute('SELECT COUNT(*) FROM precios').fetchone()[0]
    r=LSELectura(con,{'activo':True},'ficticia-lse',cli).muestra_velas('us_stocks','AAPL',ahora=AHORA)
    assert len(vistos)==1 and not r['apto_para_modelos'] and r['moneda'] is None
    assert r['available_at']==AHORA.isoformat() and r['rows'][0]['event_time']=='2026-10-30 20:00:00'
    assert con.execute('SELECT COUNT(*) FROM precios').fetchone()[0]==antes


@pytest.mark.parametrize('caso',['sin_clave','apagado','cme','redireccion','texto_en_activo'])
def test_no_consulta_sin_permiso_local_o_mercado_de_pago(con,caso):
    cli=httpx.Client(transport=httpx.MockTransport(lambda r:pytest.fail('No debe consultar')),follow_redirects=caso=='redireccion')
    a=LSELectura(con,{'activo':'false' if caso=='texto_en_activo' else caso!='apagado'},None if caso=='sin_clave' else 'ficticia-lse',cli)
    with pytest.raises(ErrorProveedor):a.muestra_velas('cme' if caso=='cme' else 'us_stocks','AAPL',ahora=AHORA)


@pytest.mark.parametrize('caso',['precio','identidad','secreto','demasiadas'])
def test_rechaza_contrato_no_finito_ajeno_y_respuesta_con_clave(con,caso):
    d=respuesta()
    if caso=='precio':d['rows'][0]['high']='NaN'
    if caso=='identidad':d['market']='cme'
    if caso=='secreto':d['api_key']='ficticia-lse'
    if caso=='demasiadas':d['rows']*=11
    cli=httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=d)))
    with pytest.raises(ErrorProveedor):
        LSELectura(con,{'activo':True},'ficticia-lse',cli).muestra_velas('us_stocks','AAPL',ahora=AHORA)
