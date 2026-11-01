"""Calendario de solo lectura: distingue previsiones, publicaciones SEC y revisiones.

No convierte aceptación EDGAR en hora del anuncio ni atribuye BPA a un 8-K sin
un dato estructurado. No consulta proveedores ni modifica precios o modelos.
"""
from datetime import UTC, date, datetime
import json
from zoneinfo import ZoneInfo

from . import centro_investigacion


def _marca(o):
    return {k: o.get(k) for k in ('valor', 'unidad', 'fuente', 'disponible_desde', 'hora_fuente', 'origen', 'url')}


def calendario(con, ahora=None):
    from .mesa_datos import CONTRATO_RESULTADOS, reaccion_resultados
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
        if not isinstance(identificador, str) or not identificador:
            continue
        k = (o['simbolo'], identificador)
        r = grupos.setdefault(k, {'simbolo': o['simbolo'], 'fecha_reporte': fecha,
            'fecha_publicacion_sec': m.get('fecha_publicacion_sec'), 'momento': m.get('momento'),
            'hora_anuncio': m.get('hora_anuncio'), 'estimacion_bpa': None,
            'hora_anuncio_verificada': m.get('anuncio_verificado') is True and o['origen'] == 'api',
            'reportado_bpa': None, 'revisado_bpa': None, 'publicaciones': [], 'estimaciones_conocidas': []})
        if o['serie'].startswith('estimacion_bpa:'):
            r['estimaciones_conocidas'].append(_marca(o))
        elif o['serie'].startswith('publicacion_sec:'):
            r['publicaciones'].append({**_marca(o), 'hora_sec': m.get('fecha_publicacion_sec'),
                                      'nota': 'Hora de publicación EDGAR; no confirma la hora del anuncio de resultados.'})
        elif o['serie'] in ('reportado_bpa', 'revisado_bpa'):
            r[o['serie']] = _marca(o)
            r['hora_anuncio'] = m.get('hora_anuncio') or r['hora_anuncio']
            r['momento'] = m.get('momento') or r['momento']
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
        conocidas = r.pop('estimaciones_conocidas')
        antes = [o for o in conocidas if t is None or datetime.fromisoformat(o['disponible_desde']) < t]
        r['estimacion_bpa'] = antes[-1] if antes else None
        r['estimacion_antes_anuncio_confirmada'] = bool(t and antes)
        r['estimacion_posterior_no_utilizada'] = bool(t and len(antes) != len(conocidas))
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
        if coherente:
            ids = con.execute("SELECT id FROM instrumentos WHERE listado_referencia=? AND estado='activo'", (r['simbolo'],)).fetchall()
            if len(ids) == 1:
                # Una sola fuente; solo cierres ya ingeridos al corte del estudio.
                p = con.execute("SELECT proveedor FROM precios WHERE instrumento_id=? AND tipo_dato='cierre' AND obtenido_en<=? AND fecha<=? ORDER BY fecha DESC,obtenido_en DESC LIMIT 1",
                                (ids[0][0], ahora.isoformat(), ahora.date().isoformat())).fetchone()
                if p:
                    cierres = [tuple(x) for x in con.execute("SELECT fecha,cierre FROM precios WHERE instrumento_id=? AND proveedor=? AND tipo_dato='cierre' AND obtenido_en<=? AND fecha<=? ORDER BY fecha",
                        (ids[0][0], p[0], ahora.isoformat(), ahora.date().isoformat()))]
                    r['reaccion'] = reaccion_resultados(cierres, r['fecha_reporte'], r['momento'])
                    r['reaccion']['fuente_cierres'] = p[0]
        r['estado'] = 'parcial'  # Ningún campo ausente se convierte en cubierto por tener otro dato.
    salida = dict(CONTRATO_RESULTADOS)
    salida['resultados'] = list(grupos.values())
    if grupos:
        salida.update(estado='parcial', motivo='Solo se cubren los campos con observaciones al corte. SIN DATO para los demás.',
                      siguiente_accion='Confirmar hora real del anuncio y BPA reportado/revisado con fuente estructurada; sin inferirlos del 8-K.')
    return salida
