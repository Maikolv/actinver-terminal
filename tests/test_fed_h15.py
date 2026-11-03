"""La publicación XML oficial conserva su identidad y conocimiento; ejemplos sintéticos."""
from datetime import UTC, datetime, timedelta
import json
import zipfile

import pytest

from terminal import centro_investigacion as centro, fed_h15, mesa_datos

AHORA = datetime(2026, 11, 1, 12, tzinfo=UTC)


def archivos(tmp_path, cambios=None, filas=None, codigo='RIFLGFCY30_N.B'):
    cruce = tmp_path / 'cruce.csv'
    cruce.write_text('ddp_release,board_series_id,fred_series_id\nH15,' + codigo + ',DGS30\n', encoding='utf-8')
    atributos = {**fed_h15.IDENTIDAD, **(cambios or {})}
    attrs = ' '.join(f'{k}="{v}"' for k, v in atributos.items())
    filas = filas or [('2026-10-29', '5.32', 'A'), ('2026-10-30', 'NaN', 'A'), ('2030-01-01', '6', 'A')]
    obs = ''.join(f'<Obs TIME_PERIOD="{p}" OBS_VALUE="{v}" OBS_STATUS="{s}"/>' for p, v, s in filas)
    xml = '<Data xmlns="http://www.SDMX.org/resources/SDMXML/schemas/v1_0/message"><DataSet><Series ' + attrs + '>' + obs + '</Series></DataSet></Data>'
    archivo = tmp_path / 'h15.zip'
    with zipfile.ZipFile(archivo, 'w') as z:
        z.writestr('H15_data.xml', xml)
    return archivo, cruce


def test_h15_importa_y_macro_declara_fuente_real_sin_fuga(con, ajustes, tmp_path):
    archivo, cruce = archivos(tmp_path)
    antes = con.execute('SELECT COUNT(*) FROM precios').fetchone()[0]
    r = fed_h15.importar(con, archivo, cruce, AHORA)
    assert r['observaciones'] == 1 and r['nuevas'] == 1 and not r['api_fred_verificada']
    assert centro.observaciones(con, hasta=AHORA-timedelta(seconds=1)) == []
    o = centro.observaciones(con, hasta=AHORA)[0]
    assert o['fuente'] == 'fed_h15' and o['origen'] == 'manual'
    assert json.loads(o['texto'])['serie_board'] == 'RIFLGFCY30_N.B' and o['huella']
    p = next(f for f in mesa_datos.macro(con, ajustes, AHORA)['series'] if f['serie'] == 'DGS30')
    assert p['fuente'] == 'fed_h15' and p['valor'] == 5.32 and 'no verifica API FRED' in p['via']
    assert 'requisito' not in p and p['estado'] == 'PUBLICACIÓN · NO COTIZACIÓN'
    assert con.execute('SELECT COUNT(*) FROM precios').fetchone()[0] == antes
    assert fed_h15.importar(con, archivo, cruce, AHORA+timedelta(seconds=1))['nuevas'] == 0


@pytest.mark.parametrize('cambio', [{'MATURITY': 'Y10'}, {'INSTRUMENT': 'TCMII'}, {'UNIT': 'Index'}, {'FREQ': 'M'}])
def test_h15_rechaza_plazo_tipo_unidad_o_frecuencia_distintos(con, tmp_path, cambio):
    archivo, cruce = archivos(tmp_path, cambios=cambio)
    with pytest.raises(ValueError, match='no confirmados'):
        fed_h15.importar(con, archivo, cruce, AHORA)
    assert con.execute('SELECT COUNT(*) FROM investigacion_observaciones').fetchone()[0] == 0


def test_h15_no_acepta_otro_codigo_en_cruce_ni_dos_valores_para_fecha(con, tmp_path):
    archivo, cruce = archivos(tmp_path, codigo='RIFLGFCY10_N.B')
    with pytest.raises(ValueError, match='cruce oficial'):
        fed_h15.importar(con, archivo, cruce, AHORA)
    archivo, cruce = archivos(tmp_path, filas=[('2026-10-29', '5.3', 'A'), ('2026-10-29', '6.3', 'A')])
    with pytest.raises(ValueError, match='incompatibles'):
        fed_h15.importar(con, archivo, cruce, AHORA)
    assert con.execute('SELECT COUNT(*) FROM investigacion_observaciones').fetchone()[0] == 0


def test_h15_mas_antiguo_no_sustituye_fred_mas_reciente(con, ajustes, tmp_path):
    archivo, cruce = archivos(tmp_path)
    fed_h15.importar(con, archivo, cruce, AHORA)
    from test_proveedores_mesa import guardar
    guardar(con, 'fred_macro', 'DGS30', 4.5, cuando=AHORA)
    con.execute("UPDATE investigacion_observaciones SET periodo='2026-10-30' WHERE fuente='fred_macro'")
    con.commit()
    p = next(f for f in mesa_datos.macro(con, ajustes, AHORA)['series'] if f['serie'] == 'DGS30')
    assert p['fuente'] == 'fred_macro' and p['periodo'] == '2026-10-30'
