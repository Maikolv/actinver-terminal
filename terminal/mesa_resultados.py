"""Calendario de solo lectura: distingue previsiones, publicaciones SEC y revisiones.

No convierte aceptación EDGAR en hora del anuncio ni atribuye BPA a un 8-K sin
un dato estructurado. No consulta proveedores ni modifica precios o modelos.
"""
from datetime import UTC, date, datetime
import json
import math
from zoneinfo import ZoneInfo

from . import centro_investigacion


def _marca(o):
    marca = {k: o.get(k) for k in ('valor', 'unidad', 'fuente', 'disponible_desde', 'hora_fuente', 'origen', 'url')}
    try:
        m = json.loads(o.get('texto', ''))
        if isinstance(m, dict):
            marca['base_bpa'] = m.get('base_bpa')
            marca['periodo_fiscal'] = m.get('periodo_fiscal')
            marca['revision_observada'] = m.get('clase') == 'revision_observada'
    except (ValueError, TypeError):
        pass
    return marca


def _variacion_diaria(con, simbolo, fecha, momento, ahora):
    """Dos cierres consecutivos de una fuente; no estima una hora ni efecto causal."""
    from . import vigencia
    from .mesa_datos import reaccion_resultados
    cal = vigencia.calendario('XNYS')
    dia = date.fromisoformat(fecha)
    if not cal.is_session(fecha):
        return {'estado': 'SIN DATO', 'motivo': 'El día reportado no es una sesión de la bolsa de origen.'}
    base = cal.previous_session(fecha).date() if momento == 'antes' else dia
    fin = cal.next_session(base.isoformat()).date()
    if vigencia.cierre_sesion('XNYS', fin) > ahora:
        return {'estado': 'SIN DATO', 'motivo': 'La sesión posterior necesaria todavía no ha cerrado.'}
    ids = con.execute("SELECT id FROM instrumentos WHERE listado_referencia=? AND estado='activo' AND moneda_referencia='USD'", (simbolo,)).fetchall()
    if len(ids) != 1:
        return {'estado': 'SIN DATO', 'motivo': 'Falta un único instrumento de referencia en USD.'}
    filas = con.execute("SELECT * FROM precios WHERE instrumento_id=? AND tipo_dato='cierre' AND moneda='USD' "
        "AND obtenido_en<=? AND fecha IN (?,?) ORDER BY obtenido_en DESC,proveedor", (ids[0][0], ahora.isoformat(), base.isoformat(), fin.isoformat())).fetchall()
    fuentes = {}
    for f in filas:
        if not math.isfinite(f['cierre']) or f['cierre'] <= 0:
            continue
        if f['hora_cotizacion']:
            try:
                hora = datetime.fromisoformat(f['hora_cotizacion'])
                if hora.tzinfo is None or hora > ahora:
                    continue
            except (TypeError, ValueError):
                continue
        fuentes.setdefault(f['proveedor'], {})[f['fecha']] = f
    for fuente, pareja in fuentes.items():
        if len(pareja) != 2:
            continue
        resultado = reaccion_resultados([(f['fecha'], f['cierre']) for f in pareja.values()], fecha, momento)
        resultado.update(fuente_cierres=fuente, moneda='USD',
            conocido_desde_cierres=max(f['obtenido_en'] for f in pareja.values()),
            criterio='Variación de cierres consecutivos por ventana declarada; no aísla splits, dividendos ni efecto causal.')
        return resultado
    return {'estado': 'SIN DATO', 'motivo': 'Faltan ambos cierres consecutivos en USD de una misma fuente, conocidos al corte.'}


def calendario(con, ahora=None):
    from .mesa_datos import CONTRATO_RESULTADOS
    ahora = ahora or datetime.now(UTC)
    centro_investigacion.inicializar(con)
    # El resumen de investigación colapsa revisiones. Aquí se necesitan TODAS las
    # versiones conocidas para recuperar una previsión anterior al anuncio.
    filas = [dict(f) for f in con.execute("SELECT * FROM investigacion_observaciones WHERE "
        "fuente IN ('alpha_calendario','sec_resultados') AND disponible_desde<=? "
        "ORDER BY disponible_desde DESC,id DESC LIMIT 4001", (ahora.isoformat(timespec='microseconds'),))]
    if len(filas) > 4000:
        return {**CONTRATO_RESULTADOS, 'resultados': [],
                'motivo': 'SIN DATO: demasiadas revisiones para este corte; acote el estudio antes de calcular.'}
    grupos = {}
    for o in sorted(filas, key=lambda o: (o['disponible_desde'], o['id'])):
        if o['fuente'] not in ('alpha_calendario', 'sec_resultados'):
            continue
        try:
            m = json.loads(o['texto'])
        except (ValueError, TypeError):
            continue
        if not isinstance(m, dict):
            continue
        fecha = m.get('fecha_reporte')
        if fecha is not None:
            try:
                fecha = date.fromisoformat(fecha).isoformat()
            except (ValueError, TypeError):
                continue
        identificador = fecha or m.get('acceso')
        fiscal = None
        if m.get('periodo_fiscal'):
            try:
                fiscal = date.fromisoformat(m['periodo_fiscal']).isoformat()
                identificador = 'fiscal:' + fiscal
            except (ValueError, TypeError):
                pass
        if not isinstance(identificador, str) or not identificador:
            continue
        k = (o['simbolo'], identificador)
        r = grupos.setdefault(k, {'simbolo': o['simbolo'], 'fecha_reporte': fecha,
            'periodo_fiscal': fiscal, 'fecha_prevista': None,
            'fecha_publicacion_sec': m.get('fecha_publicacion_sec'), 'momento': m.get('momento'),
            'momento_declarado_por': m.get('momento_declarado_por'),
            'ventana_api_verificada': False,
            'hora_anuncio': m.get('hora_anuncio'), 'estimacion_bpa': None,
            'hora_anuncio_verificada': m.get('anuncio_verificado') is True and o['origen'] == 'api',
            'reportado_bpa': None, 'revisado_bpa': None, 'publicaciones': [], 'estimaciones_conocidas': []})
        if o['serie'].startswith('estimacion_bpa:'):
            r['estimaciones_conocidas'].append(_marca(o))
            r['fecha_prevista'] = fecha
            if not r['reportado_bpa']:
                r['fecha_reporte'] = fecha
        elif o['serie'].startswith('publicacion_sec:'):
            r['publicaciones'].append({**_marca(o), 'hora_sec': m.get('fecha_publicacion_sec'),
                                      'nota': 'Hora de publicación EDGAR; no confirma la hora del anuncio de resultados.'})
        elif o['serie'] in ('reportado_bpa', 'revisado_bpa'):
            r[o['serie']] = _marca(o)
            r['fecha_reporte'] = fecha or r['fecha_reporte']
            r['hora_anuncio'] = m.get('hora_anuncio') or r['hora_anuncio']
            r['momento'] = m.get('momento') or r['momento']
            r['momento_declarado_por'] = m.get('momento_declarado_por') or r['momento_declarado_por']
            r['ventana_api_verificada'] = (o['origen'] == 'api' and o['fuente'] == 'alpha_calendario'
                and m.get('momento_declarado_por') == 'Alpha EARNINGS.reportTime' and m.get('momento') in ('antes', 'despues'))
            r['hora_anuncio_verificada'] = m.get('anuncio_verificado') is True and o['origen'] == 'api'
    for r in grupos.values():
        # Solo la última estimación conocida ANTES del anuncio, nunca la revisada después.
        t = None
        try:
            t = datetime.fromisoformat(r['hora_anuncio']) if r['hora_anuncio'] and r['hora_anuncio_verificada'] else None
            if t is not None and (t.tzinfo is None or t > ahora):
                t = None
        except (ValueError, TypeError):
            pass
        limite_estimacion = t
        if limite_estimacion is None and r['reportado_bpa'] and r['reportado_bpa']['origen'] == 'api' and r['fecha_reporte']:
            # Sin hora exacta, una previsión anterior al INICIO del día reportado es
            # inequívocamente anterior; una recibida durante/después no se usa.
            dia = date.fromisoformat(r['fecha_reporte'])
            limite_estimacion = datetime.combine(dia, datetime.min.time(), ZoneInfo('America/New_York'))
        conocidas = r.pop('estimaciones_conocidas')
        antes = [o for o in conocidas if limite_estimacion is None or datetime.fromisoformat(o['disponible_desde']) < limite_estimacion]
        r['estimacion_bpa'] = antes[-1] if antes else None
        r['estimacion_antes_anuncio_confirmada'] = bool(limite_estimacion and antes)
        r['estimacion_posterior_no_utilizada'] = bool(limite_estimacion and len(antes) != len(conocidas))
        r['criterio_estimacion'] = 'hora exacta verificada' if t else 'inicio del día reportado, conservador' if limite_estimacion else 'no confirmado'
        r['reaccion'] = {'estado': 'SIN DATO', 'motivo': 'Falta hora del anuncio verificada; no se usa aceptación SEC como sustituto.'}
        coherente = False
        if t and r['fecha_reporte'] and r['momento'] in ('antes', 'despues'):
            from . import vigencia
            try:
                dia = datetime.fromisoformat(r['fecha_reporte']).date()
                coherente = t.astimezone(ZoneInfo('America/New_York')).date() == dia and (
                    t < vigencia.apertura_sesion('XNYS', dia) if r['momento'] == 'antes'
                    else t >= vigencia.cierre_sesion('XNYS', dia))
            except (ValueError, TypeError):
                pass
        bpa = r['reportado_bpa']
        ventana_api = (not r['hora_anuncio'] and r['ventana_api_verificada'] and bpa and bpa['origen'] == 'api' and bpa['fuente'] == 'alpha_calendario'
            and r['momento_declarado_por'] == 'Alpha EARNINGS.reportTime' and r['momento'] in ('antes', 'despues'))
        if coherente or ventana_api:
            r['reaccion'] = _variacion_diaria(con, r['simbolo'], r['fecha_reporte'], r['momento'], ahora)
            r['reaccion']['precision_anuncio'] = 'hora exacta verificada' if coherente else 'ventana declarada; hora exacta SIN DATO'
        r['estado'] = 'parcial'  # Ningún campo ausente se convierte en cubierto por tener otro dato.
    salida = dict(CONTRATO_RESULTADOS)
    def orden(r):
        texto = r.get('fecha_reporte') or (r.get('fecha_publicacion_sec') or '')[:10]
        try:
            dia = date.fromisoformat(texto)
        except (ValueError, TypeError):
            return (2, 0, r['simbolo'])
        futura = dia >= ahora.date() and r['reportado_bpa'] is None and not r['publicaciones']
        return (0 if futura else 1, dia.toordinal() if futura else -dia.toordinal(), r['simbolo'])
    salida['resultados'] = sorted(grupos.values(), key=orden)
    if grupos:
        salida.update(estado='parcial', motivo='Solo se cubren los campos con observaciones al corte. SIN DATO para los demás.',
                      siguiente_accion='Completar únicamente los campos sin evidencia. La variación diaria requiere dos cierres consecutivos y una ventana declarada; no confirma una hora exacta ni efecto causal.')
    return salida
