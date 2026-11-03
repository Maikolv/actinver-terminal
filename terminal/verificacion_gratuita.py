"""Verificación manual y acotada de APIs gratuitas con secretos ya disponibles en memoria.

No carga archivos de credenciales, no arranca servidor/motor, no contrata ni habilita
fuentes. Solo agrega observaciones validadas de investigación cuando se solicita.
"""
from datetime import UTC, datetime
import json
import logging
from urllib.parse import urlsplit

from . import centro_investigacion as centro, db
from .adaptadores.base import ErrorProveedor, LimiteAlcanzado
from .centro_conectores import FredMacro, FredMacroLaboral
from .proveedores_mesa import AlphaCalendario, AlphaResultados, BanxicoSIE, SECResultados, guardar_resultados_alpha

# Candidatos documentados: cada respuesta vuelve a comprobar identidad por API.
# CIK comprobados en company_tickers.json el 1-nov-2026, incluido el nuevo holding XOM.
# Cada submissions vuelve a confirmar símbolo/CIK; no se une a la entidad histórica.
EMISORAS = {'MU': 723125, 'NVDA': 1045810, 'AMD': 2488, 'XOM': 2115436}
SERIES_SIE = {'BANXICO_OBJETIVO': 'SF61745', 'INPC': 'SP1'}


class Contador:
    def __init__(self, cliente):
        self.cliente = cliente
        self.solicitudes = 0
        self.historial = []

    def get(self, *args, **kwargs):
        self.solicitudes += 1
        ruta = urlsplit(str(args[0]))
        entrada = {'host': ruta.hostname, 'ruta': ruta.path, 'http': None}
        self.historial.append(entrada)  # Nunca parámetros, cabeceras o cuerpos.
        r = self.cliente.get(*args, **kwargs)
        entrada['http'] = r.status_code
        return r


def verificar(con, *, env, cliente, ahora=None, guardar=False, bono10=None, emisoras=None, solo=None, ajustes=None, bpa=None, macro_laboral=False):
    """Como máximo diez peticiones sin bono; no recibe ni guarda claves en el informe.

    ``bono10`` es un candidato, nunca un ID confirmado por el llamador. Solo el GET
    oficial y su título pueden confirmarlo antes de pedir datos. Sin código se omite F6.
    Cupos compartidos y Retry-After permanecen bajo los adaptadores existentes.
    """
    corte_fijo = ahora is not None
    ahora = ahora or datetime.now(UTC)
    if ahora.tzinfo is None:
        raise ValueError('El corte requiere zona horaria.')
    emisoras = EMISORAS if emisoras is None else emisoras
    if not isinstance(emisoras, dict) or not 1 <= len(emisoras) <= 4 or not set(emisoras) <= set(EMISORAS):
        raise ValueError('Seleccione de una a cuatro emisoras del alcance; no se amplía el presupuesto.')
    permitidas = {'fred_macro', 'banxico_sie', 'sec_resultados', 'alpha_calendario'}
    seleccion = permitidas if solo is None else set(solo)
    if not seleccion or not seleccion <= permitidas:
        raise ValueError('Solo se pueden seleccionar las cuatro fuentes gratuitas del verificador.')
    if macro_laboral and seleccion != {'fred_macro'}:
        raise ValueError('El respaldo laboral solo permite seleccionar fred_macro: tres consultas como máximo.')
    if bpa is not None and bpa not in EMISORAS:
        raise ValueError('El BPA debe corresponder a una de las cuatro emisoras del alcance.')
    centro.inicializar(con)
    catalogo = {f['id']: f for f in centro.fuentes()}
    resultados = {}
    fuentes = [("F2", 'fred_macro', FredMacro, 'FRED_API_KEY', {}, {'DGS30': FredMacro.SERIES['DGS30']})]
    if macro_laboral:
        fuentes = [('MACRO-RESPALDO', 'fred_macro', FredMacroLaboral, 'FRED_API_KEY', {}, None)]
    for tema, sid in {**SERIES_SIE, **({'BANXICO_BONO10': bono10} if bono10 else {})}.items():
        cfg = {'series': {**dict.fromkeys(BanxicoSIE.CANDIDATOS), tema: sid}}
        fuentes.append(({'BANXICO_OBJETIVO': 'F3', 'INPC': 'F4', 'BANXICO_BONO10': 'F6'}[tema],
                        'banxico_sie', BanxicoSIE, 'BANXICO_TOKEN', cfg, None))
    if not bono10:
        resultados['F6'] = {'estado': 'requiere_seleccion_explicita', 'solicitudes': 0, 'activado': False,
                            'id_confirmado': BanxicoSIE.CANDIDATOS['BANXICO_BONO10']}
    for simbolo, cik in emisoras.items():
        fuentes.append(('F1-SEC-' + simbolo, 'sec_resultados', SECResultados, 'SEC_USER_AGENT',
                        {'emisoras': {simbolo: cik}}, None))
    fuentes.append(('F1-BPA-' + bpa, 'alpha_calendario', AlphaResultados, 'ALPHAVANTAGE_API_KEY', {'simbolo': bpa}, None)
                   if bpa else ('F1-ALPHA', 'alpha_calendario', AlphaCalendario, 'ALPHAVANTAGE_API_KEY', {}, None))
    fuentes = [f for f in fuentes if f[1] in seleccion]
    if 'banxico_sie' not in seleccion:
        resultados.pop('F6', None)
    # Evita el registro de URLs con parámetros de autenticación incluso si el llamador
    # configuró el registro HTTP a nivel INFO. Se restaura al salir.
    registros = [logging.getLogger(n) for n in ('httpx', 'httpcore')]
    niveles = [r.level for r in registros]
    for registro in registros:
        registro.setLevel(logging.WARNING)
    try:
        for identificador, fid, clase, variable, opciones, series in fuentes:
            clave = env.get(variable)
            if not clave:
                resultados[identificador] = {'estado': 'sin_credencial_en_memoria', 'solicitudes': 0, 'activado': False}
                continue
            configurada = centro._cfg(ajustes, fid) if ajustes is not None else centro.DEFAULTS[fid]
            cfg = {**configurada, **opciones, 'activo': True}
            if fid == 'alpha_calendario':
                compartida = centro._cfg(ajustes, 'alpha_vantage') if ajustes is not None else centro.DEFAULTS['alpha_vantage']
                cfg['peticiones_por_dia'] = min(cfg['peticiones_por_dia'], compartida['peticiones_por_dia'])
            transporte = Contador(cliente)
            adaptador = clase(con, cfg, clave, cliente=transporte)
            if series:
                adaptador.SERIES = series  # Solo esta instancia: no altera FredMacro global.
            try:
                bruto = (adaptador.comprobar_acceso(ahora) if isinstance(adaptador, AlphaCalendario)
                         else adaptador.consultar(ahora))
                serializado = json.dumps(bruto, ensure_ascii=False)
                if any(isinstance(v, str) and len(v) >= 6 and v in serializado for v in env.values()):
                    raise ErrorProveedor('La respuesta contiene información sensible; no se guarda.')
                conocido = ahora if corte_fijo else datetime.now(UTC)
                filas = [centro._validar(f, catalogo[fid], conocido, 'api') for f in bruto]
                nuevos = 0
                if guardar and filas:
                    with db.transaccion(con):
                        nuevos = (guardar_resultados_alpha(con, filas, conocido) if isinstance(adaptador, AlphaResultados)
                                  else centro._guardar(con, filas, conocido))
                evidencia = [dict(t) for t in {tuple((k, f[k]) for k in ('serie', 'simbolo', 'titulo', 'unidad')) for f in filas}]
                resultados[identificador] = {'estado': 'confirmado' if filas else 'acceso_confirmado_sin_observaciones',
                    'solicitudes': transporte.solicitudes, 'observaciones_validas': len(filas), 'nuevas': nuevos,
                    'guardado_solicitado': guardar, 'conocido_desde': conocido.isoformat(),
                    'identidad_observada': sorted(evidencia, key=lambda f: (f['serie'], f['simbolo'])),
                    'id_sie': next((v for v in opciones.get('series', {}).values() if v), None),
                    'emisoras_confirmadas': opciones.get('emisoras', {}) if fid == 'sec_resultados' else {}, 'activado': False}
            except LimiteAlcanzado:
                resultados[identificador] = {'estado': 'cupo_o_espera', 'solicitudes': transporte.solicitudes, 'activado': False}
            except Exception as error:
                # No se vuelca la excepción, URL, cabecera ni respuesta del proveedor.
                categoria = ('proveedor' if isinstance(error, ErrorProveedor) else
                             'contrato' if isinstance(error, (ValueError, KeyError, TypeError)) else 'interno')
                resultados[identificador] = {'estado': 'respuesta_no_confirmada', 'categoria': categoria,
                                            'solicitudes': transporte.solicitudes, 'activado': False}
            resultados[identificador]['http'] = transporte.historial
    finally:
        for registro, nivel in zip(registros, niveles):
            registro.setLevel(nivel)
    return {'corte': ahora.isoformat(), 'fuentes': resultados,
            'solicitudes': sum(r['solicitudes'] for r in resultados.values()),
            'nota': 'Investigación manual; no activa conectores ni acredita negociación o vigencia de cotizaciones.'}
