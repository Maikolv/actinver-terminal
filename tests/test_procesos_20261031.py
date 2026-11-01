"""Regresiones offline: respaldo acotado, reloj inyectado y procedencia del plan."""
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from terminal import bot_telegram, ingesta, mensaje_simple, reportes, servicios
from terminal.adaptadores.base import Adaptador
from terminal.adaptadores.proveedores import Alpaca, Tiingo

CERRADO = datetime(2026, 10, 30, 22, tzinfo=UTC)
ABIERTO = datetime(2026, 10, 30, 17, tzinfo=UTC)


def proveedores(con, barras=True, cuota=10):
    llamadas = []
    def respuesta(r):
        llamadas.append(r.url.host)
        if r.url.host == 'api.tiingo.com':
            return httpx.Response(200, json=[])
        assert r.url.host == 'data.alpaca.markets'  # ningún endpoint de operaciones
        assert r.url.params['start'] == '2026-10-30'
        return httpx.Response(200, json={'bars': [{'t': '2026-10-30T04:00:00Z', 'c': 150, 'v': 4}] if barras else []})
    cliente = httpx.Client(transport=httpx.MockTransport(respuesta))
    ads = {n: Adaptador(con, {'activo': False}, cliente=cliente) for n in ingesta.ORDEN_PRECIOS}
    ads['tiingo'] = Tiingo(con, {}, 'ficticia-de-prueba', cliente=cliente)
    ads['alpaca'] = Alpaca(con, {'peticiones_por_dia': cuota}, 'ficticia-de-prueba', secreto='ficticio', cliente=cliente)
    con.execute("UPDATE instrumentos SET estado='inactivo' WHERE id!='SIC:AMD'")
    con.commit()
    return ads, llamadas


@pytest.mark.parametrize('momento,prioritaria,esperadas', [(CERRADO,True,3), (ABIERTO,True,1), (CERRADO,False,1)])
def test_respaldo_solo_cartera_despues_del_cierre(con, momento, prioritaria, esperadas):
    ads, llamadas = proveedores(con)
    ingesta.actualizar_precios(con, ads, ['SIC:AMD'] if prioritaria else [], ahora=momento)
    assert len(llamadas) == esperadas
    filas = list(con.execute('SELECT proveedor,barras FROM intentos_precio_historial ORDER BY id'))
    if esperadas == 3:
        assert [tuple(f) for f in filas] == [('tiingo',0),('alpaca',1)]
        p = con.execute("SELECT proveedor,fecha,tipo_dato FROM precios WHERE instrumento_id='SIC:AMD'").fetchone()
        assert tuple(p) == ('alpaca','2026-10-30','cierre')
        assert con.execute("SELECT proveedor FROM intentos_precio WHERE instrumento_id='SIC:AMD'").fetchone()[0]=='alpaca'
    else:
        assert len(filas)==1 and not con.execute('SELECT 1 FROM precios').fetchone()


def test_respaldo_no_reintenta_otra_fuente_si_devuelve_cero(con):
    ads,llamadas=proveedores(con,barras=False)
    ingesta.actualizar_precios(con,ads,['SIC:AMD'],ahora=CERRADO)
    assert llamadas==['api.tiingo.com','data.alpaca.markets']
    assert con.execute('SELECT COUNT(*) FROM intentos_precio_historial').fetchone()[0]==2


def test_respaldo_respeta_cupo_sin_llamada_http(con):
    ads,llamadas=proveedores(con,cuota=0)
    r=ingesta.actualizar_precios(con,ads,['SIC:AMD'],ahora=CERRADO)
    assert llamadas==['api.tiingo.com'] and r['alpaca']['omitidos_limite']==1


def test_error_del_respaldo_no_dispara_un_tercer_proveedor(con,monkeypatch):
    from terminal.adaptadores.base import ErrorProveedor
    ads,llamadas=proveedores(con)
    def error(*a):raise ErrorProveedor('sin datos de respaldo')
    monkeypatch.setattr(ads['alpaca'],'historico',error)
    tercero=ads['barchart']
    monkeypatch.setattr(tercero,'configurado',lambda:True)
    monkeypatch.setattr(tercero,'soporta',lambda ins:True)
    monkeypatch.setattr(tercero,'historico',lambda *a:pytest.fail('No se permite un tercer intento'))
    ingesta.actualizar_precios(con,ads,['SIC:AMD'],ahora=CERRADO)
    assert llamadas==['api.tiingo.com']
    assert [tuple(f) for f in con.execute('SELECT proveedor,barras FROM intentos_precio_historial ORDER BY id')]==[('tiingo',0),('alpaca',0)]


def test_cola_usa_fecha_inyectada_y_no_dia_del_ci(con):
    con.execute("INSERT INTO intentos_precio VALUES ('BMV:GCC','2026-10-29','eodhd',0)");con.commit()
    filas=[{'id':'BMV:GCC'},{'id':'BMV:VESTA'}]
    assert ingesta.orden_cola(con,filas,reserva_nuevos=1,ahora=CERRADO)[0]['id']=='BMV:VESTA'
    assert ingesta.orden_cola(con,filas,reserva_nuevos=1,ahora=CERRADO+timedelta(days=10))[0]['id']=='BMV:GCC'


@pytest.mark.parametrize('momento,hay_aviso',[(ABIERTO,True),(CERRADO,False)])
def test_reportes_y_motor_no_dependen_de_hora_real(con,ajustes,momento,hay_aviso,monkeypatch):
    assert ('aviso' in servicios.estado_motor(con,momento)) is hay_aviso
    recibido=[]
    monkeypatch.setattr(reportes,'_seccion_pronostico',lambda c,a,p,cart,t: recibido.append(t) or [])
    for tipo in ('preapertura','cierre','semanal'):
        texto=reportes.generar(con,ajustes,tipo,ahora=momento)
        assert 'Aún no ha corrido ningún ciclo' in texto
    assert recibido==[momento]*3


def test_alertas_del_reporte_no_miran_hora_real_ni_futuro(con,monkeypatch):
    def alerta(hora,titulo):return dict(ts=hora.isoformat(),severidad='info',titulo=titulo,motivo='prueba',fuente='offline')
    monkeypatch.setattr(reportes.alertas,'listar',lambda *a:[alerta(ABIERTO-timedelta(hours=1),'incluida'),alerta(ABIERTO+timedelta(hours=1),'futura')])
    texto='\n'.join(reportes._seccion_alertas(con,24,ABIERTO))
    assert 'incluida' in texto and 'futura' not in texto


def test_plan_nombra_solo_precios_atrasados_y_fecha(con):
    cart={'posiciones':[{'instrumento_id':'SIC:AMD','clave_operable':'AMD *','fecha_precio':'2026-10-29'}, {'instrumento_id':'SIC:MU','clave_operable':'MU *','fecha_precio':'2026-10-30'}]}
    filas=mensaje_simple.precios_atrasados(con,cart,CERRADO)
    assert filas==[{'clave':'AMD *','fecha':'2026-10-29'}]
    plan={'cuenta':dict(confirmada=True,valor_total=100,efectivo=100),'acciones':[],'reglas':dict(errores=[])}
    propuesta={'escenarios':{'central_p50':0,'adverso_p10':0}}
    import pandas as pd
    texto=mensaje_simple.construir(plan,propuesta,[],pd.Timestamp(CERRADO).tz_convert(mensaje_simple.ZONA),precios_atrasados=filas)
    assert 'AMD: 2026-10-29' in texto and 'MU:' not in texto


def test_texto_plan_propaga_el_reloj_sin_enviar(con,ajustes,monkeypatch):
    recibido=[]
    monkeypatch.setattr(mensaje_simple,'texto',lambda c,a,ahora:recibido.append(ahora) or 'texto local')
    assert bot_telegram.texto_plan(con,ajustes,ahora=CERRADO)=='texto local'
    assert recibido==[CERRADO]


@pytest.mark.parametrize('momento,fecha,espera_aviso',[(CERRADO,'2026-10-29',True), (datetime(2026,11,2,20,30,tzinfo=UTC),'2026-10-30',False)])
def test_texto_completo_de_plan_respeta_el_cierre_de_cada_mercado(con,ajustes,momento,fecha,espera_aviso):
    cart={'posiciones':[{'instrumento_id':'SIC:AMD','clave_operable':'AMD *','peso':1,'fecha_precio':fecha}]}
    plan={'cuenta':dict(confirmada=True,valor_total=100,efectivo=100),'acciones':[],'reglas':dict(errores=[])}
    propuesta={'escenarios':{'central_p50':0,'adverso_p10':0}}
    texto=mensaje_simple.texto(con,ajustes,propuesta=propuesta,cartera=cart,plan=plan,ahora=momento)
    assert ('precios atrasados en la valuación' in texto) is espera_aviso
    assert 'la valuación usa precios del' not in texto
    if espera_aviso:assert 'AMD: 2026-10-29' in texto


def test_precio_sin_fecha_valida_se_nombra_sin_fabricarla(con):
    filas=mensaje_simple.precios_atrasados(con,{'posiciones':[{'instrumento_id':'SIC:AMD','fecha_precio':'malformada'}]},CERRADO)
    assert filas==[{'clave':'SIC:AMD','fecha':None}]
