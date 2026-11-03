"""Importación puntual del XML H.15 oficial, con equivalencia DDP–FRED comprobada.

No consulta páginas, no carga credenciales ni inicia servicios. La fuente se conserva
como Federal Reserve Board: importar su XML no verifica acceso a la API de FRED.
"""
import csv
from datetime import UTC, date, datetime
import hashlib
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from . import centro_investigacion as centro, db
from .centro_conectores import numero, observacion

URL = 'https://www.federalreserve.gov/releases/h15/data/FRB_h15_xml.zip'
EQUIVALENCIA = 'https://www.federalreserve.gov/data/documents/DDP-FRED%20Data%20Series%20Crosswalk.csv'
IDENTIDAD = {'SERIES_NAME': 'RIFLGFCY30_N.B', 'INSTRUMENT': 'TCMNOM', 'MATURITY': 'Y30',
             'FREQ': '9', 'UNIT': 'Percent:_Per_Year', 'UNIT_MULT': '1', 'CURRENCY': 'NA'}


def importar(con, archivo, equivalencias, ahora=None):
    """Lee archivos descargados de las dos URL oficiales; no hace solicitudes HTTP."""
    fijo = ahora is not None
    corte = ahora or datetime.now(UTC)
    if corte.tzinfo is None:
        raise ValueError('El corte requiere zona horaria.')
    archivo, equivalencias = Path(archivo), Path(equivalencias)
    if archivo.stat().st_size > 10_000_000 or equivalencias.stat().st_size > 5_000_000:
        raise ValueError('El archivo supera el límite de esta importación acotada.')
    cruce = list(csv.DictReader(io.StringIO(equivalencias.read_text(encoding='utf-8-sig'))))
    candidatas = [f for f in cruce if f.get('fred_series_id') == 'DGS30']
    if len(candidatas) != 1 or candidatas[0].get('ddp_release') != 'H15' or candidatas[0].get('board_series_id') != IDENTIDAD['SERIES_NAME']:
        raise ValueError('El cruce oficial no confirmó la identidad exacta DGS30/H.15.')
    datos, encontrada = {}, False
    with zipfile.ZipFile(archivo) as z:
        miembros = [i for i in z.infolist() if i.filename == 'H15_data.xml']
        if len(miembros) != 1 or miembros[0].file_size > 100_000_000:
            raise ValueError('Archivo XML ausente, duplicado o demasiado grande.')
        with z.open(miembros[0]) as f:
            if b'<!DOCTYPE' in f.read(4096).upper():
                raise ValueError('No se admiten declaraciones de entidades.')
            f.seek(0)
            activa = False
            try:
                for evento, e in ET.iterparse(f, events=('start', 'end')):
                    nombre = e.tag.rsplit('}', 1)[-1]
                    if evento == 'start' and nombre == 'Series':
                        activa = e.attrib.get('SERIES_NAME') == IDENTIDAD['SERIES_NAME']
                        if activa:
                            if encontrada or any(e.attrib.get(k) != v for k, v in IDENTIDAD.items()):
                                raise ValueError('Serie repetida o unidad/plazo/frecuencia no confirmados.')
                            encontrada = True
                    if evento == 'end' and nombre == 'Obs' and activa and e.get('OBS_STATUS') == 'A':
                        periodo = date.fromisoformat(e.get('TIME_PERIOD', ''))
                        valor = numero(e.get('OBS_VALUE'))
                        if periodo <= corte.date() and valor is not None:
                            if periodo in datos and datos[periodo] != valor:
                                raise ValueError('Dos valores incompatibles para la misma fecha.')
                            datos[periodo] = valor
                    if evento == 'end':
                        if nombre == 'Series':
                            activa = False
                        e.clear()
            except ET.ParseError:
                raise ValueError('XML oficial no válido; no se guarda nada.') from None
    if not encontrada or not datos:
        raise ValueError('SIN DATO: la serie no entregó observaciones utilizables al corte.')
    conocido = corte if fijo else datetime.now(UTC)
    huella_zip = hashlib.sha256(archivo.read_bytes()).hexdigest()
    huella_cruce = hashlib.sha256(equivalencias.read_bytes()).hexdigest()
    texto = json.dumps({'via': 'importación puntual de publicación XML oficial',
        'serie_board': IDENTIDAD['SERIES_NAME'], 'equivalencia_oficial': EQUIVALENCIA,
        'sha256_xml_zip': huella_zip, 'sha256_equivalencias': huella_cruce,
        'aviso': 'Fuente primaria H.15; no es API FRED, cotización ni conocimiento histórico previo a la descarga.'}, ensure_ascii=False)
    fuente = next(f for f in centro.fuentes() if f['id'] == 'fed_h15')
    filas = [centro._validar({**observacion('DGS30', p.isoformat(), datos[p], '%',
        'Treasury 30 años · publicación XML H.15', texto=texto), 'url': URL}, fuente, conocido, 'manual')
        for p in sorted(datos)[-24:]]
    centro.inicializar(con)
    with db.transaccion(con):
        nuevos = centro._guardar(con, filas, conocido)
    return {'fuente': 'fed_h15', 'serie': 'DGS30', 'serie_board': IDENTIDAD['SERIES_NAME'],
        'identidad': IDENTIDAD, 'observaciones': len(filas), 'nuevas': nuevos,
        'periodo_inicial': filas[0]['periodo'], 'periodo_final': filas[-1]['periodo'],
        'disponible_desde': conocido.isoformat(), 'sha256_zip': huella_zip,
        'sha256_equivalencias': huella_cruce, 'api_fred_verificada': False, 'activado': False}
