from datetime import UTC, datetime, timedelta
import pytest
from terminal.flujo.subasta import analizar, area_tpo, contexto


def sesion(fecha="2026-10-15", precio=100):
    inicio = datetime.fromisoformat(fecha+"T13:30:00+00:00")
    return [{"inicio":(inicio+timedelta(minutes=5*i)).isoformat(),"intervalo":"5Min",
             "apertura":precio,"maximo":precio+.5,"minimo":precio-.5,"cierre":precio}
            for i in range(78)]


AHORA = datetime(2026,10,16,21,tzinfo=UTC)


def test_area_tpo_contigua_empates_y_huecos():
    r=area_tpo({0:{0},1:{0,1,2,3},2:{0,1,2},3:{0,1}},1)
    assert (r["poc"],r["val"],r["vah"],r["fraccion"]) == (1.5,1,3,.7)
    assert area_tpo({0:{0},4:{0}},1)["vah"] == 5
    assert area_tpo({},1) is None


def test_referencia_previa_ib_y_no_lookahead():
    bs=sesion()+sesion("2026-10-16",102)
    r=analizar(bs,ahora=AHORA)["sesiones"][-1]
    assert r["referencia"]["fecha"] == "2026-10-15"
    assert r["estado"] == "aceptacion_alcista"
    assert r["ib"] == {"alto":102.5,"bajo":101.5}
    corte=datetime(2026,10,16,13,40,tzinfo=UTC)
    a=analizar(bs,ahora=corte)
    b=analizar(bs[:-30],ahora=corte)
    assert a["sesiones"] == b["sesiones"]
    assert a["sesiones"][-1]["barras"] == 2
    assert a["sesiones"][-1]["ib"] is None


def test_sesion_parcial_duplicados_y_disponibilidad():
    bs=sesion()[:-1]+sesion("2026-10-16")
    assert analizar(bs,ahora=AHORA)["sesiones"][-1]["referencia"] is None
    bs=sesion();bs += [bs[0]]
    assert analizar(bs,ahora=AHORA)["sesiones"][0]["barras"] == 78
    bs[0]={**bs[0],"disponible_desde":"2026-10-20T00:00:00Z"}
    assert not analizar(bs[:78],ahora=AHORA)["sesiones"][0]["completa_observada"]


@pytest.mark.parametrize("paso",[0,-1,float('nan'),float('inf')])
def test_paso_invalido(paso):
    with pytest.raises(ValueError): analizar([],paso=paso)


def test_estados_simetria_rechazo_y_no_adivinar():
    ref={"val":100,"vah":101}
    assert contexto([102,102],103,101,ref) == "aceptacion_alcista"
    assert contexto([99,99],100,98,ref) == "aceptacion_bajista"
    assert contexto([100.5],102,100,ref) == "rechazo_superior"
    assert contexto([100.5],101,99,ref) == "rechazo_inferior"
    assert contexto([100.5],102,99,ref) == "rechazo_ambos_extremos"
    assert contexto([100.5],100.75,100.25,ref) == "rotacion_en_valor"
    assert contexto([102],103,101,ref) == "exploracion_fuera_de_valor"
    assert contexto([102],103,101,None) == "sin_referencia"


def test_barras_invalidas_y_sin_datos():
    assert analizar([],ahora=AHORA)["sesiones"] == []
    bs=sesion();bs[0]["cierre"]=float('nan')
    r=analizar(bs,ahora=AHORA)
    assert r["barras_omitidas"] == 1 and not r["operable"]
    bs=sesion();bs.pop(3)
    assert analizar(bs,ahora=AHORA)["sesiones"][0]["ib"] is None


def test_api_perfiles_incluye_amt_y_valida_rejilla(monkeypatch):
    from fastapi.testclient import TestClient
    from terminal.app import app
    from terminal.flujo import almacen, servicio
    filas=[{**b,"fuente":"prueba","feed":"sintetico","calidad":"importado"} for b in sesion()]
    monkeypatch.setattr(almacen,"barras",lambda *a,**kw:filas)
    monkeypatch.setattr(servicio,"origen_eeuu",lambda *a:"NASDAQ")
    monkeypatch.setattr(servicio,"_procedencia",lambda *a:[])
    with TestClient(app,base_url="http://127.0.0.1:8765") as c:
        r=c.get('/api/flujo/perfiles?simbolo=PRUEBA&paso_precio=0.25')
        assert r.status_code==200
        assert r.json()['subasta']['version']=='amt-1.0'
        assert not r.json()['subasta']['operable']
        assert c.get('/api/flujo/perfiles?simbolo=PRUEBA&paso_precio=0').status_code==422
