"""Consultas oficiales opcionales para la Mesa; sin precios, órdenes o credenciales en informes.

Los conectores nuevos permanecen apagados en la configuración por defecto. La hora
de descarga nunca se interpreta como hora histórica de publicación.
"""
from __future__ import annotations

import csv
import io
import json
import re
import unicodedata
from datetime import UTC, date, datetime, timedelta
from email.utils import parsedate_to_datetime

import httpx

from . import db
from .adaptadores.base import Adaptador, ErrorProveedor, LimiteAlcanzado


def _norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s.lower()) if not unicodedata.combining(c))


class ConsultaMesa(Adaptador):
    requiere_credencial = True
    tipo_dato = 'contexto_investigacion'
    descripcion = 'Publicaciones oficiales, no cotizaciones'
    uso_permitido = 'Consulta según condiciones oficiales; sin redistribución implícita.'

    def _ventanas(self, ahora=None):
        return super()._ventanas(ahora or getattr(self, '_hora_peticion', None))

    def _peticion(self, url, *, ahora, params=None, headers=None):
        self._hora_peticion = ahora
        if not self.configurado():
            raise ErrorProveedor('Conector apagado o sin credencial.')
        alias = 'alpha_vantage' if self.proveedor == 'alpha_calendario' else self.proveedor
        proveedor_pausa = {'banxico_sie': 'banxico', 'sec_resultados': 'sec_edgar'}.get(alias, alias)
        clave = 'proveedor_pausa:' + proveedor_pausa
        pausa = self.con.execute('SELECT valor FROM ajustes_usuario WHERE clave=?', (clave,)).fetchone()
        if pausa and datetime.fromisoformat(json.loads(pausa[0])['hasta']) > ahora:
            raise LimiteAlcanzado('Proveedor en espera por Retry-After.')
        # Una sola solicitud, sin reintentos automáticos. Cupo compartido para Alpha Vantage.
        original = self.proveedor
        ajustes_originales = self.ajustes
        try:
            self.proveedor = alias
            if alias == 'alpha_vantage':
                self.ajustes = {**self.ajustes, 'peticiones_por_dia': min(25, self.ajustes.get('peticiones_por_dia', 25)),
                                'peticiones_por_minuto': min(1, self.ajustes.get('peticiones_por_minuto', 1))}
            self._consumir()
        finally:
            self.proveedor = original
            self.ajustes = ajustes_originales
        try:
            r = self.cliente.get(url, params=params, headers=headers)
        except httpx.HTTPError:
            raise ErrorProveedor('Error de conexión con el proveedor.') from None
        if r.status_code == 429 or (r.status_code == 503 and 'Retry-After' in r.headers):
            try:
                segundos = max(0, float(r.headers.get('Retry-After', '60')))
            except ValueError:
                try:
                    segundos = max(0, (parsedate_to_datetime(r.headers['Retry-After']) - ahora).total_seconds())
                except (ValueError, TypeError, KeyError):
                    segundos = 60
            if not 0 <= segundos <= 31536000:
                segundos = 86400
            hasta = (ahora + timedelta(seconds=segundos)).isoformat()
            db.escribir(self.con, "INSERT INTO ajustes_usuario VALUES (?,?,?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor, actualizado_en=excluded.actualizado_en",
                        (clave, json.dumps({'hasta': hasta}), ahora.isoformat()))
            raise ErrorProveedor(f'HTTP {r.status_code}: se respeta Retry-After; no se reintenta ahora.')
        if r.status_code != 200:
            raise ErrorProveedor(f'Proveedor respondió HTTP {r.status_code}; no se guarda el cuerpo ni la URL de error.')
        return r

    def cerrar(self):
        if self._cliente is not None:
            self._cliente.close()


class BanxicoSIE(ConsultaMesa):
    proveedor = 'banxico_sie'
    # Identidades confirmadas por GET oficial el 1-nov-2026. Cada consulta las revalida.
    # SF30057 es promedio mensual: nunca se trata como rendimiento diario o vigente.
    CANDIDATOS = {'BANXICO_OBJETIVO': 'SF61745', 'BANXICO_BONO10': 'SF30057', 'INPC': 'SP1'}
    BASE = 'https://www.banxico.org.mx/SieAPIRest/service/v1/series/'

    @staticmethod
    def _serie(respuesta, sid):
        try:
            series = respuesta.json()['bmx']['series']
            if not isinstance(series, list) or len(series) != 1 or not isinstance(series[0], dict) or series[0].get('idSerie') != sid:
                raise ValueError
            return series[0]
        except (ValueError, KeyError, TypeError):
            raise ErrorProveedor('SIE no confirmó un contrato de serie válido; SIN DATO.') from None

    @staticmethod
    def coincide(tema, titulo, *, sid=None, cifra=None, periodicidad=None, unidad=None):
        s = _norm(titulo)
        if tema == 'BANXICO_OBJETIVO':
            return 'objetivo' in s and 'tasa' in s
        if tema == 'BANXICO_BONO10':
            return bool('udibono' not in s and 'tiie' not in s and re.search(r'\bbonos?\b', s) and re.search(r'\b10\s+anos\b', s)
                        and (re.search(r'\bbonos?\s+m\b', s) or re.search(r'tasa.*fija', s)))
        if tema != 'INPC' or 'variacion' in s:
            return False
        if unidad is not None and ('%' in str(unidad) or 'porc' in _norm(str(unidad)) or 'por ciento' in _norm(str(unidad))):
            return False
        if periodicidad is not None and _norm(str(periodicidad)).strip() != 'mensual':
            return False
        if 'indice nacional de precios al consumidor' in s:
            return True
        # Título real del catálogo SP1: IPC Por objeto del gasto Nacional I n d i c e G e n e r a l.
        # No se acepta por parecido: ID, texto completo, tipo índice y periodicidad deben coincidir.
        return (sid == 'SP1' and re.sub(r'[^a-z0-9]', '', s) == 'ipcporobjetodelgastonacionalindicegeneral'
                and _norm(str(cifra)).strip() in ('indice', 'indices')
                and _norm(str(periodicidad)).strip() == 'mensual')

    def consultar(self, ahora):
        from .centro_conectores import observacion, numero
        out = []
        for tema, sid in {**self.CANDIDATOS, **self.ajustes.get('series', {})}.items():
            if sid is None:
                continue
            if tema not in self.CANDIDATOS or not re.fullmatch(r'[A-Z]{2}\d{1,8}', sid):
                raise ErrorProveedor('Código SIE no válido o tema no reconocido.')
            headers = {'Bmx-Token': self.credencial, 'Accept': 'application/json'}
            meta = self._serie(self._peticion(self.BASE + sid, ahora=ahora, headers=headers), sid)
            if not isinstance(meta.get('titulo'), str) or not self.coincide(tema, meta['titulo'], sid=sid,
                    cifra=meta.get('cifra'), periodicidad=meta.get('periodicidad'), unidad=meta.get('unidad')):
                raise ErrorProveedor('El catálogo SIE no confirmó la identidad de la serie; SIN DATO.')
            # El título se confirma ANTES de pedir o persistir observaciones.
            datos = self._serie(self._peticion(self.BASE + sid + '/datos', ahora=ahora, headers=headers), sid)
            for f in datos.get('datos', [])[-24:]:
                if not isinstance(f, dict):
                    raise ErrorProveedor('SIE devolvió una observación inválida.')
                try:
                    periodo = datetime.strptime(f['fecha'], '%d/%m/%Y').date()
                except (ValueError, KeyError):
                    continue
                valor = numero(str(f.get('dato', '')).replace(',', ''))
                if valor is None or periodo > ahora.date():
                    continue
                texto = json.dumps({'serie_sie': sid, 'titulo_catalogo': meta['titulo'],
                    'periodicidad': meta.get('periodicidad'), 'unidad_catalogo': meta.get('unidad'),
                    'cifra_catalogo': meta.get('cifra'),
                    'aviso': 'Identidad confirmada por GET. Publicación original desconocida; disponible desde la descarga.'}, ensure_ascii=False)
                titulo = 'INPC nacional · índice general' if tema == 'INPC' else meta['titulo'][:160]
                out.append(observacion(tema, periodo.isoformat(), valor, 'índice' if tema == 'INPC' else '%', titulo, texto=texto))
        return out


def comprobar_twelve_basico(con, cfg, clave, instrumento, cliente, ahora):
    """Prueba manual de UNA solicitud; no habilita el proveedor ni cambia la cola."""
    from .adaptadores.proveedores import TwelveData
    from .centro_conectores import numero
    if not clave:
        return {'estado': 'bloqueado', 'consultas': 0, 'motivo': 'Sin clave en un mecanismo permitido.'}
    adaptador = TwelveData(con, cfg, clave, cliente=cliente)
    if not adaptador.soporta(instrumento):
        return {'estado': 'sin_verificar', 'consultas': 0, 'motivo': 'Instrumento BMV fuera del catálogo verificado.'}
    transporte = ConsultaMesa(con, {'activo': True, 'peticiones_por_dia': min(800, cfg.get('peticiones_por_dia', 700)),
                                   'peticiones_por_minuto': 8}, clave, cliente=cliente)
    transporte.proveedor = 'twelvedata'
    try:
        d = transporte._peticion(TwelveData.URL, ahora=ahora, params={'symbol': adaptador.simbolo(instrumento),
            'mic_code': 'XMEX', 'interval': '1day', 'outputsize': 1, 'apikey': clave}).json()
    except (ErrorProveedor, ValueError):
        return {'estado': 'no_confirmado', 'consultas_maximas': 1, 'motivo': 'Consulta rechazada, sin reintentos.'}
    if not isinstance(d, dict):
        return {'estado': 'no_confirmado', 'consultas': 1, 'habilitado_automaticamente': False}
    meta, filas = d.get('meta', {}), d.get('values', [])
    valido = bool(meta.get('mic_code') == 'XMEX' and meta.get('symbol') == adaptador.simbolo(instrumento)
                  and filas and numero(filas[0].get('close')) is not None and numero(filas[0]['close']) > 0)
    return {'estado': 'acceso_simbolo_confirmado' if valido else 'no_confirmado', 'consultas': 1,
            'nivel_plan': 'No se deduce Basic de una respuesta de precios; verificar por separado.',
            'habilitado_automaticamente': False}


class AlphaCalendario(ConsultaMesa):
    proveedor = 'alpha_calendario'

    def consultar(self, ahora):
        from .centro_conectores import observacion, numero
        if not self.ajustes.get('plan_verificado'):
            raise ErrorProveedor('Calendario deshabilitado: falta verificar el plan con una única consulta autorizada.')
        return self.comprobar_acceso(ahora)

    def comprobar_acceso(self, ahora):
        """Una prueba manual del CSV; no cambia el permiso ni activa el conector."""
        from .centro_conectores import observacion, numero
        r = self._peticion('https://www.alphavantage.co/query', ahora=ahora,
                           params={'function': 'EARNINGS_CALENDAR', 'horizon': '3month', 'apikey': self.credencial})
        lector = csv.DictReader(io.StringIO(r.text))
        if not {'symbol', 'reportDate', 'estimate', 'currency', 'fiscalDateEnding'} <= set(lector.fieldnames or []):
            raise ErrorProveedor('El plan no entregó el CSV de resultados esperado; mantener deshabilitado.')
        permitidos = set(self.ajustes.get('simbolos', ['MU', 'AMD', 'NVDA', 'XOM']))
        out = []
        for f in lector:
            simbolo = f['symbol']
            if simbolo not in permitidos or numero(f['estimate']) is None:
                continue
            fecha = date.fromisoformat(f['reportDate']).isoformat()
            texto = json.dumps({'fecha_reporte': fecha, 'periodo_fiscal': f['fiscalDateEnding'],
                                'clase': 'estimacion', 'momento': None, 'hora_anuncio': None}, ensure_ascii=False)
            out.append(observacion('estimacion_bpa:' + fecha, ahora.date().isoformat(), f['estimate'],
                                   f['currency'] + '/acción', 'Estimación de BPA (fecha prevista, no anuncio confirmado)', simbolo, texto))
        return out


class AlphaResultados(ConsultaMesa):
    """Una consulta EARNINGS por símbolo; las estimaciones retrospectivas no se importan."""
    proveedor = 'alpha_calendario'  # Mismo permiso de fuente y cupo compartido alpha_vantage.

    def consultar(self, ahora):
        from .centro_conectores import observacion, numero
        simbolo = self.ajustes.get('simbolo', '')
        if not isinstance(simbolo, str) or not re.fullmatch(r'[A-Z][A-Z0-9.-]{0,14}', simbolo):
            raise ErrorProveedor('Símbolo de resultados no válido.')
        d = self._peticion('https://www.alphavantage.co/query', ahora=ahora,
            params={'function': 'EARNINGS', 'symbol': simbolo, 'apikey': self.credencial}).json()
        if not isinstance(d, dict) or d.get('symbol') != simbolo or not isinstance(d.get('quarterlyEarnings'), list):
            raise ErrorProveedor('La API no confirmó el símbolo y el contrato de resultados; no se activa nada.')
        moneda = d.get('reportedCurrency')
        unidad = moneda + '/acción' if isinstance(moneda, str) and re.fullmatch(r'[A-Z]{3}', moneda) else 'BPA · moneda no informada'
        vistos, out = set(), []
        for f in d['quarterlyEarnings']:
            if not isinstance(f, dict):
                raise ErrorProveedor('Fila de resultados no válida.')
            valor = numero(f.get('reportedEPS'))
            try:
                fiscal = date.fromisoformat(f.get('fiscalDateEnding', ''))
                reporte = date.fromisoformat(f.get('reportedDate', ''))
            except (TypeError, ValueError):
                continue
            if fiscal > reporte or reporte > ahora.date() or valor is None:
                continue
            if fiscal in vistos:
                raise ErrorProveedor('Dos resultados para el mismo periodo fiscal; no se elige uno arbitrariamente.')
            vistos.add(fiscal)
            momento = {'pre-market': 'antes', 'post-market': 'despues'}.get(f.get('reportTime'))
            texto = json.dumps({'fecha_reporte': reporte.isoformat(), 'periodo_fiscal': fiscal.isoformat(),
                'clase': 'bpa_reportado', 'momento': momento, 'hora_anuncio': None,
                'momento_declarado_por': 'Alpha EARNINGS.reportTime' if momento else None,
                'base_bpa': 'No especificada por la API; no se calcula sorpresa.',
                'aviso': 'Primera captura local del valor que entrega el proveedor, no necesariamente el anuncio original. '
                         'No se importan estimatedEPS ni surprise históricos como si se conocieran antes del anuncio.'}, ensure_ascii=False)
            out.append(observacion('reportado_bpa', fiscal.isoformat(), valor, unidad,
                'BPA reportado por Alpha · captura local', simbolo, texto))
        return sorted(out, key=lambda f: f['periodo'], reverse=True)[:8]


def guardar_resultados_alpha(con, filas, conocido):
    """Conserva el primer BPA local; cambios posteriores son revisiones observadas.

    No afirma que un cambio sea una reformulación contable oficial. La disponibilidad
    sigue siendo la de cada captura, nunca la fecha histórica del reporte.
    """
    from . import centro_investigacion as centro
    nuevos = 0
    for f in filas:
        if f['fuente'] != 'alpha_calendario' or f['serie'] != 'reportado_bpa' or f['origen'] != 'api':
            raise ValueError('Solo se admiten BPA de la consulta oficial de resultados.')
        anterior = con.execute("SELECT * FROM investigacion_observaciones WHERE fuente='alpha_calendario' AND "
            "simbolo=? AND periodo=? AND serie IN ('reportado_bpa','revisado_bpa') AND origen='api' "
            "ORDER BY disponible_desde DESC,id DESC LIMIT 1", (f['simbolo'], f['periodo'])).fetchone()
        nueva = dict(f)
        if anterior and (anterior['valor'] != f['valor'] or anterior['serie'] == 'revisado_bpa'):
            nueva['serie'] = 'revisado_bpa'
            nueva['titulo'] = 'BPA modificado en capturas de Alpha'
            m = json.loads(nueva['texto'])
            m['clase'] = 'revision_observada'
            m['aviso_revision'] = 'Cambio entre capturas locales; no acredita una reformulación oficial del emisor.'
            nueva['texto'] = json.dumps(m, ensure_ascii=False)
        nuevos += centro._guardar(con, [nueva], conocido)
    return nuevos


class SECResultados(ConsultaMesa):
    proveedor = 'sec_resultados'

    def consultar(self, ahora):
        from .centro_conectores import observacion
        from .movimientos.sec import ClienteSEC, ErrorSEC, SUBMISSIONS
        padre = self
        class Transporte:
            def get(self, url, headers=None):
                return padre._peticion(url, ahora=ahora, headers=headers)
        try:
            sec = ClienteSEC(self.credencial, cliente=Transporte(), reintentos=0)
        except ErrorSEC:
            raise ErrorProveedor('Falta identificación SEC válida; mantener apagado.') from None
        emisoras = self.ajustes.get('emisoras', {})
        if not isinstance(emisoras, dict) or not 1 <= len(emisoras) <= 8:
            raise ErrorProveedor('Configure hasta ocho símbolos con CIK confirmado; no se inventa el mapeo.')
        out = []
        for simbolo, cik in emisoras.items():
            if not re.fullmatch(r'[A-Z][A-Z0-9.-]{0,14}', simbolo) or not str(cik).isdigit():
                raise ErrorProveedor('Símbolo/CIK inválido.')
            datos = sec.get(SUBMISSIONS.format(cik=int(cik))).json()
            if str(datos.get('cik', '')).lstrip('0') != str(cik).lstrip('0') or simbolo not in datos.get('tickers', []):
                raise ErrorProveedor('La SEC no confirmó el mapeo símbolo/CIK.')
            rec = datos.get('filings', {}).get('recent', {})
            campos = ('form', 'items', 'acceptanceDateTime', 'accessionNumber')
            if len({len(rec.get(c, [])) for c in campos}) != 1:
                raise ErrorProveedor('Metadatos SEC incompletos.')
            for forma, items, aceptado, acceso in zip(*(rec.get(c, []) for c in campos)):
                if forma not in ('8-K', '8-K/A') or '2.02' not in re.split(r'[,;\s]+', items):
                    continue
                t = datetime.fromisoformat(aceptado)
                if t.tzinfo is None or t > ahora:
                    continue
                if not re.fullmatch(r'\d{10}-\d{2}-\d{6}', acceso):
                    raise ErrorProveedor('Acceso SEC inválido.')
                url = f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acceso.replace("-", "")}/{acceso}-index.htm'
                texto = json.dumps({'clase': 'publicacion_sec', 'forma': forma, 'acceso': acceso,
                                    'fecha_publicacion_sec': t.isoformat(), 'fecha_reporte': None,
                                    'momento': None, 'reportado_bpa': None, 'revisado_bpa': None,
                                    'nota': 'Aceptación EDGAR, no hora del anuncio. Item 2.02 no entrega BPA estructurado.'}, ensure_ascii=False)
                o = observacion('publicacion_sec:' + acceso, t.date().isoformat(), None, '',
                                'Publicación SEC ' + forma + ' Item 2.02', simbolo, texto, t.isoformat())
                o['url'] = url
                out.append(o)
        return out
