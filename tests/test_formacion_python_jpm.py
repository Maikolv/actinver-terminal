from copy import deepcopy

import pytest

from terminal.formacion_python import resumen_cierres


def ejemplo():
    return [dict(fecha=f'2026-01-0{n}',cierre=p,fuente='ejemplo_local',tipo_dato='sintetico')
            for n,p in enumerate([100,110,99],1)]


def test_estadisticas_y_procedencia_sin_anualizar():
    filas=ejemplo();previo=deepcopy(filas);r=resumen_cierres(filas)
    assert r['rendimiento_tramo']==pytest.approx(-.01)
    assert r['caida_maxima']==pytest.approx(-.1)
    assert r['volatilidad_entre_observaciones']==pytest.approx(2**.5/10)
    assert r['tipo_dato']=='sintetico' and filas==previo


@pytest.mark.parametrize('malo',[0,-1,True,float('nan'),float('inf')])
def test_rechaza_cierres_invalidos(malo):
    f=ejemplo();f[1]['cierre']=malo
    with pytest.raises(ValueError):resumen_cierres(f)


def test_rechaza_orden_fuentes_mezcladas_y_sin_dato():
    with pytest.raises(ValueError):resumen_cierres(ejemplo()[::-1])
    f=ejemplo();f[1]['fuente']='otra'
    with pytest.raises(ValueError):resumen_cierres(f)
    with pytest.raises(ValueError):resumen_cierres([])


@pytest.mark.parametrize('fuente',[None,{'nombre':'sin-identidad'},123])
def test_procedencia_requiere_texto(fuente):
    f=ejemplo();f[1]['fuente']=fuente
    with pytest.raises(ValueError):resumen_cierres(f)
