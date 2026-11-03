"""Consultas puntuales LSE Data 3.0: sin exportaciones, ejecución o escritura de precios.

Contrato: londonstrategicedge/lse-data, docs/api.md. El cliente upstream no se
importa ni ejecuta. Su licencia MIT no concede derechos sobre los datos.
"""
from datetime import UTC, datetime
import json
import re

import httpx

from .adaptadores.base import ErrorProveedor
from .centro_conectores import numero
from .proveedores_mesa import ConsultaMesa


class LSELectura(ConsultaMesa):
    proveedor = 'lse_data'
    BASE = 'https://download.londonstrategicedge.com/v3/'
    MERCADOS = {'us_stocks','uk_stocks','ca_stocks','forex','crypto','futures','indices','commodities','us_options'}

    def __init__(self, con, ajustes=None, credencial=None, cliente=None):
        cfg = {'activo': False, 'peticiones_por_dia': 5, 'peticiones_por_minuto': 2, **(ajustes or {})}
        cfg['peticiones_por_dia'] = min(5, cfg['peticiones_por_dia'])
        cfg['peticiones_por_minuto'] = min(2, cfg['peticiones_por_minuto'])
        super().__init__(con, cfg, credencial, cliente)

    @property
    def cliente(self):
        if self._cliente is None:
            self._cliente = httpx.Client(timeout=15, follow_redirects=False, trust_env=False)
        return self._cliente

    def _json_lectura(self, ruta, ahora, params=None):
        if ahora.tzinfo is None:
            raise ValueError('La consulta requiere un corte con zona horaria.')
        if ruta not in ('markets','usage','preview'):
            raise ErrorProveedor('Solo se permiten catálogo, uso y muestra de velas.')
        if self.ajustes.get('activo') is not True or not self.configurado():
            raise ErrorProveedor('Consulta optativa apagada o sin clave; no se crea una conexión.')
        if self.cliente.follow_redirects:
            raise ErrorProveedor('El cliente debe desactivar redirecciones antes de enviar una clave.')
        r = self._peticion(self.BASE+ruta, ahora=ahora, params=params, headers={'X-API-Key': self.credencial or ''})
        if len(r.content) > 65536:
            raise ErrorProveedor('Muestra demasiado grande; no se procesa ni exporta.')
        try:
            d = r.json()
        except ValueError:
            raise ErrorProveedor('LSE no entregó JSON reconocido.') from None
        if not isinstance(d, dict) or (self.credencial and self.credencial in json.dumps(d, ensure_ascii=False)):
            raise ErrorProveedor('Respuesta no admisible; no se guarda su contenido.')
        return d

    def catalogo(self, ahora=None):
        d = self._json_lectura('markets', ahora or datetime.now(UTC))
        if not isinstance(d.get('markets'), list):
            raise ErrorProveedor('Catálogo sin contrato de mercados.')
        return [{'mercado': f['folder'], 'permitido_por_clave': f.get('allowed') is True,
                 'alcance_gratuito_documentado': f['folder'] in self.MERCADOS}
                for f in d['markets'] if isinstance(f, dict) and isinstance(f.get('folder'), str)]

    def muestra_velas(self, mercado, simbolo, intervalo='1d', ahora=None):
        if mercado not in self.MERCADOS:
            raise ErrorProveedor('Mercado fuera del alcance gratuito documentado; no se contrata ni consulta CME/TotalView.')
        if not isinstance(simbolo, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/ =-]{0,63}', simbolo):
            raise ValueError('Símbolo no válido; debe proceder del catálogo oficial.')
        if intervalo not in ('1m','5m','1h','1d'):
            raise ValueError('Solo se permite muestra acotada de velas, nunca ticks u órdenes.')
        conocido = ahora or datetime.now(UTC)
        d = self._json_lectura('preview', conocido, {'market': mercado, 'symbol': simbolo, 'timeframe': intervalo, 'data': 'candles'})
        if (d.get('market') != mercado or d.get('symbol') != simbolo or d.get('timeframe') != intervalo
                or d.get('data') != 'candles' or not isinstance(d.get('rows'), list) or len(d['rows']) > 10
                or not isinstance(d.get('adjusted'), bool)):
            raise ErrorProveedor('Identidad o contrato de la muestra no confirmado.')
        filas = []
        for f in d['rows']:
            if not isinstance(f, dict):
                raise ErrorProveedor('Fila no reconocida.')
            valores = {k: numero(f.get(k)) for k in ('open','high','low','close','volume')}
            t = f.get('time')
            if (not isinstance(t, str) or not 1 <= len(t) <= 64 or any(v is None for v in valores.values())
                    or any(valores[k] <= 0 for k in ('open','high','low','close')) or valores['volume'] < 0
                    or valores['high'] < max(valores['open'],valores['close'],valores['low'])
                    or valores['low'] > min(valores['open'],valores['close'],valores['high'])):
                raise ErrorProveedor('OHLCV no válido; no se rellena ni se convierte en precio.')
            try:
                evento = datetime.fromisoformat(t)
            except ValueError:
                raise ErrorProveedor('Fecha de la muestra no reconocida.') from None
            if (evento > conocido if evento.tzinfo else evento.date() > conocido.date()):
                raise ErrorProveedor('Muestra con fecha futura; no se presenta como histórica.')
            filas.append({'event_time': t, **valores})
        conocido = ahora or datetime.now(UTC)
        return {'source': 'lse_data', 'market': mercado, 'symbol': simbolo, 'interval': intervalo,
                'available_at': conocido.isoformat(), 'ingested_at': conocido.isoformat(), 'rows': filas,
                'adjusted': d['adjusted'], 'moneda': None, 'zona_horaria': 'sin confirmar en la muestra',
                'tipo_dato': 'muestra_historica_latencia_desconocida', 'apto_para_modelos': False,
                'nota': 'Moneda/latencia/zona horaria no verificadas. Esta muestra no acredita acceso a CME. No se escribe en precios ni se trata como DOM CME.'}
