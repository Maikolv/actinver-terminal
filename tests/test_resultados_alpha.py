"""BPA oficial simulado, cambios entre capturas y estimaciones sin fuga temporal."""
from datetime import UTC, datetime, timedelta
import json

import httpx
import pytest

from terminal import centro_investigacion as centro, db, mesa_datos
from terminal.mesa_resultados import calendario
from terminal.proveedores_mesa import AlphaResultados, BanxicoSIE, guardar_resultados_alpha

AHORA = datetime(2026, 11, 1, 12, tzinfo=UTC)
TITULO_SP1 = 'IPC Por objeto del gasto                                                         Nacional I n d i c e   G e n e r a l'


def test_sp1_titulo_legado_exactamente_nacional_indice_mensual():
    assert BanxicoSIE.coincide('INPC', TITULO_SP1, sid='SP1', cifra='Indices', periodicidad='Mensual')
    for cambio in ({'sid': 'SP2'}, {'cifra': 'Porcentajes'}, {'periodicidad': 'Quincenal'}):
        assert not BanxicoSIE.coincide('INPC', TITULO_SP1, **({'sid': 'SP1', 'cifra': 'Indices', 'periodicidad': 'Mensual'} | cambio))
    assert not BanxicoSIE.coincide('INPC', TITULO_SP1, sid='SP1', cifra='Indices', periodicidad='Mensual', unidad='Porcentajes')
    assert not BanxicoSIE.coincide('INPC', TITULO_SP1.replace('Nacional', 'Regional'), sid='SP1', cifra='Indices', periodicidad='Mensual')


def test_sp1_metadatos_antes_de_datos_y_unidad_indice(con):
    vistos = []
    def responder(r):
        vistos.append(r.url.path)
        f = {'idSerie': 'SP1', 'titulo': TITULO_SP1, 'cifra': 'Indices', 'periodicidad': 'Mensual', 'unidad': 'Sin Unidad'}
        if r.url.path.endswith('/datos'):
            f['datos'] = [{'fecha': '01/09/2026', 'dato': '146.075'}]
        return httpx.Response(200, json={'bmx': {'series': [f]}})
    cfg = {'series': dict.fromkeys(BanxicoSIE.CANDIDATOS) | {'INPC': 'SP1'}}
    filas = BanxicoSIE(con, cfg, 'clave-ficticia', httpx.Client(transport=httpx.MockTransport(responder))).consultar(AHORA)
    assert vistos[1] == vistos[0] + '/datos'
    assert filas[0]['unidad'] == 'índice' and filas[0]['valor'] == 146.075
    assert json.loads(filas[0]['texto'])['titulo_catalogo'] == TITULO_SP1


def datos(valor='1.2', simbolo='MU'):
    return {'symbol': simbolo, 'reportedCurrency': 'USD', 'quarterlyEarnings': [
        {'fiscalDateEnding': '2026-08-31', 'reportedDate': '2026-10-01', 'reportedEPS': valor,
         'estimatedEPS': '999', 'surprise': '-999', 'reportTime': 'post-market'},
        {'fiscalDateEnding': '2030-08-31', 'reportedDate': '2030-10-01', 'reportedEPS': '5'}]}


def filas_bpa(con, d, ahora=AHORA):
    def responder(r):
        assert r.url.params['function'] == 'EARNINGS' and r.url.params['symbol'] == 'MU'
        return httpx.Response(200, json=d)
    a = AlphaResultados(con, {'simbolo': 'MU'}, 'clave-ficticia', httpx.Client(transport=httpx.MockTransport(responder)))
    origen = next(f for f in centro.fuentes() if f['id'] == 'alpha_calendario')
    return [centro._validar(f, origen, ahora, 'api') for f in a.consultar(ahora)]


def test_bpa_no_convierte_estimacion_historica_en_pronostico(con):
    filas = filas_bpa(con, datos())
    assert len(filas) == 1 and filas[0]['serie'] == 'reportado_bpa' and filas[0]['valor'] == 1.2
    m = json.loads(filas[0]['texto'])
    assert m['hora_anuncio'] is None and m['periodo_fiscal'] == '2026-08-31'
    assert 'estimatedEPS' not in m and 'surprise' not in m and filas[0]['unidad'] == 'USD/acción'
    desconocida = datos()
    del desconocida['reportedCurrency']
    assert filas_bpa(con, desconocida, AHORA+timedelta(minutes=2))[0]['unidad'] == 'BPA · moneda no informada'


def test_bpa_no_finito_simbolo_ajeno_y_filas_duplicadas_no_se_guardan(con):
    assert filas_bpa(con, datos('NaN')) == []
    with pytest.raises(Exception, match='símbolo'):
        filas_bpa(con, datos(simbolo='NVDA'), AHORA+timedelta(minutes=2))
    repetida = datos()
    repetida['quarterlyEarnings'].append(repetida['quarterlyEarnings'][0])
    with pytest.raises(Exception, match='mismo periodo'):
        filas_bpa(con, repetida, AHORA+timedelta(minutes=4))
    assert con.execute('SELECT COUNT(*) FROM investigacion_observaciones').fetchone()[0] == 0


def test_revision_observada_conserva_original_y_asof(con):
    for i, valor in enumerate(('1.2', '1.3', '1.3', '1.2')):
        cuando = AHORA+timedelta(minutes=i*2)
        filas = filas_bpa(con, datos(valor), cuando)
        with db.transaccion(con):
            nuevos = guardar_resultados_alpha(con, filas, cuando)
        assert nuevos == (0 if i == 2 else 1)
    inicial = calendario(con, AHORA)['resultados'][0]
    assert inicial['reportado_bpa']['valor'] == 1.2 and inicial['revisado_bpa'] is None
    assert inicial['momento'] == 'despues' and inicial['momento_declarado_por'] == 'Alpha EARNINGS.reportTime'
    assert inicial['hora_anuncio'] is None and inicial['reaccion']['estado'] == 'SIN DATO'
    revision = calendario(con, AHORA+timedelta(minutes=2))['resultados'][0]
    assert revision['reportado_bpa']['valor'] == 1.2 and revision['revisado_bpa']['valor'] == 1.3
    assert revision['revisado_bpa']['revision_observada']
    final = calendario(con, AHORA+timedelta(minutes=6))['resultados'][0]
    assert final['reportado_bpa']['valor'] == final['revisado_bpa']['valor'] == 1.2
    assert calendario(con, AHORA-timedelta(seconds=1))['resultados'] == []


def test_fiscal_une_fecha_prevista_distinta_sin_usar_estimacion_tardia(con):
    from test_proveedores_mesa import guardar
    texto = json.dumps({'fecha_reporte': '2026-10-02', 'periodo_fiscal': '2026-08-31'})
    guardar(con, 'alpha_calendario', 'estimacion_bpa:2026-10-02', 999, texto, AHORA-timedelta(minutes=1), 'MU')
    with db.transaccion(con):
        guardar_resultados_alpha(con, filas_bpa(con, datos()), AHORA)
    r = calendario(con, AHORA)['resultados']
    assert len(r) == 1 and r[0]['fecha_reporte'] == '2026-10-01' and r[0]['fecha_prevista'] == '2026-10-02'
    assert r[0]['estimacion_bpa'] is None and r[0]['estimacion_posterior_no_utilizada']
    assert r[0]['reaccion']['estado'] == 'SIN DATO'


def test_macro_bono_promedio_mensual_no_se_presenta_como_diario(con, ajustes):
    from test_proveedores_mesa import guardar
    guardar(con, 'banxico_sie', 'BANXICO_BONO10', 9.0)
    con.execute("UPDATE investigacion_observaciones SET titulo='Bonos a tasa fija a 10 años Tasa de rendimiento promedio mensual' WHERE serie='BANXICO_BONO10'")
    con.commit()
    fila = next(f for f in mesa_datos.macro(con, ajustes, AHORA)['series'] if f['serie'] == 'BANXICO_BONO10')
    assert fila['frecuencia'] == 'mensual (promedio)' and fila['estado'] == 'PUBLICACIÓN · NO COTIZACIÓN'


def preparar_ventana(con, momento='post-market'):
    assert con.execute("SELECT moneda_referencia FROM instrumentos WHERE id='SIC:MU'").fetchone()[0] == 'USD'
    d = datos()
    d['quarterlyEarnings'][0].update(reportedDate='2026-10-29', reportTime=momento)
    with db.transaccion(con):
        guardar_resultados_alpha(con, filas_bpa(con, d), AHORA)


def cierre(con, fecha, valor, fuente='prueba', moneda='USD', tipo='cierre', obtenido=None):
    con.execute("INSERT INTO precios (instrumento_id,fecha,cierre,moneda,proveedor,tipo_dato,obtenido_en) VALUES ('SIC:MU',?,?,?,?,?,?)",
        (fecha, valor, moneda, fuente, tipo, (obtenido or AHORA).isoformat()))
    con.commit()


@pytest.mark.parametrize('momento,base,fin', [('pre-market','2026-10-28','2026-10-29'), ('post-market','2026-10-29','2026-10-30')])
def test_ventana_api_permite_variacion_diaria_sin_inventar_hora(con, momento, base, fin):
    preparar_ventana(con, momento)
    cierre(con, base, 100)
    cierre(con, fin, 110)
    r = calendario(con, AHORA)['resultados'][0]
    assert r['hora_anuncio'] is None and not r['hora_anuncio_verificada']
    assert r['reaccion']['reaccion'] == pytest.approx(.1)
    assert (r['reaccion']['base'], r['reaccion']['fin']) == (base, fin)
    assert r['reaccion']['moneda'] == 'USD' and r['reaccion']['fuente_cierres'] == 'prueba'
    assert r['reaccion']['precision_anuncio'] == 'ventana declarada; hora exacta SIN DATO'
    assert 'efecto causal' in r['reaccion']['criterio']


@pytest.mark.parametrize('caso', ['fuentes','moneda','sintetico','retrasado','no_finito','fecha','ingesta','hora_futura','manual','ventana_ajena'])
def test_variacion_diaria_no_mezcla_fuentes_ni_fuga_ni_admite_ventana_manual(con, caso):
    preparar_ventana(con)
    cierre(con, '2026-10-29', 100)
    cierre(con, '2026-10-30' if caso != 'fecha' else '2026-11-02', float('inf') if caso == 'no_finito' else 110,
        fuente='otra' if caso == 'fuentes' else 'prueba', moneda='MXN' if caso == 'moneda' else 'USD',
        tipo=caso if caso in ('sintetico','retrasado') else 'cierre', obtenido=AHORA+timedelta(days=1) if caso == 'ingesta' else AHORA)
    if caso == 'hora_futura':
        con.execute("UPDATE precios SET hora_cotizacion=? WHERE fecha='2026-10-30'", ((AHORA+timedelta(days=1)).isoformat(),))
    if caso == 'manual':
        con.execute("UPDATE investigacion_observaciones SET origen='manual'")
    if caso == 'ventana_ajena':
        fila = con.execute('SELECT id,texto FROM investigacion_observaciones LIMIT 1').fetchone()
        texto = json.loads(fila['texto'])
        texto['momento_declarado_por'] = 'otra fuente sin confirmar'
        con.execute('UPDATE investigacion_observaciones SET texto=? WHERE id=?', (json.dumps(texto), fila['id']))
    con.commit()
    assert calendario(con, AHORA)['resultados'][0]['reaccion']['estado'] == 'SIN DATO'


def test_variacion_diaria_espera_cierre_real_aunque_exista_barra_del_dia(con):
    preparar_ventana(con)
    temprano = datetime(2026, 10, 30, 12, tzinfo=UTC)
    con.execute('UPDATE investigacion_observaciones SET disponible_desde=?', (temprano.isoformat(),))
    con.commit()
    cierre(con, '2026-10-29', 100, obtenido=temprano)
    cierre(con, '2026-10-30', 110, obtenido=temprano)
    r = calendario(con, temprano)['resultados'][0]['reaccion']
    assert r['estado'] == 'SIN DATO' and 'todavía no ha cerrado' in r['motivo']
