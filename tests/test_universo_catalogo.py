"""El selector no calcula precios ni presenta ausencia de precio como cotización."""
def test_catalogo_no_consulta_cotizaciones(con, monkeypatch):
    from terminal import app
    def prohibida(*args, **kwargs):
        raise AssertionError('Un catálogo no debe consultar precios')
    monkeypatch.setattr(app.mercado, 'cotizaciones', prohibida)
    resultado = app.get_universo(con, solo_catalogo=True)
    assert resultado['instrumentos']
    assert all(f['precio'] is None and f['proveedor'] is None for f in resultado['instrumentos'])
    assert all('grafica' in f and 'nombre' in f for f in resultado['instrumentos'])

def test_universo_normal_conserva_procedencia(con, monkeypatch):
    from terminal import app
    iid = next(iter(app.mercado.instrumentos(con)))
    dato = dict(precio=23.5, fecha='2026-01-01', proveedor='prueba_offline', tipo_dato='sintetico')
    monkeypatch.setattr(app.mercado, 'cotizaciones', lambda *a: {iid: dato})
    filas = {f['id']: f for f in app.get_universo(con)['instrumentos']}
    for clave, valor in dato.items():
        assert filas[iid][clave] == valor
