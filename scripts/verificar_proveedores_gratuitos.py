"""Consulta optativa de fuentes oficiales con variables ya presentes, nunca con .env."""
import argparse
import json
import os
from pathlib import Path
import sys

os.environ.update(TERMINAL_SIN_MOTOR='1', TERMINAL_SIN_ENV='1')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--consultar', action='store_true', help='Autoriza esta consulta manual de datos; no activa conectores.')
    parser.add_argument('--guardar', action='store_true', help='Agrega únicamente observaciones validadas de investigación.')
    parser.add_argument('--base', type=Path, required=True, help='Base existente; no crea ni migra una base del usuario.')
    parser.add_argument('--evidencia', type=Path, required=True, help='JSON de resultados sin secretos ni respuestas crudas.')
    parser.add_argument('--bono10', help='Código candidato a confirmar por GET oficial antes de pedir datos; no implica aprobación.')
    parser.add_argument('--solo', nargs='+', choices=('fred_macro', 'banxico_sie', 'sec_resultados', 'alpha_calendario'),
                        help='Consulta solo pendientes seleccionados; evita repetir fuentes ya verificadas.')
    parser.add_argument('--bpa', choices=('MU', 'NVDA', 'AMD', 'XOM'),
                        help='Una consulta EARNINGS en lugar del calendario. No importa estimaciones retrospectivas.')
    parser.add_argument('--macro-laboral', action='store_true',
                        help='Tres series FRED como respaldo de BLS. Requiere --solo fred_macro; no activa fuentes.')
    args = parser.parse_args()
    if not args.consultar:
        parser.error('Sin --consultar no se realiza ninguna petición.')
    if not args.base.is_file():
        parser.error('La base debe existir; no se inicializa ni se inventa un conjunto de datos.')
    if args.base.resolve().suffix.lower() not in ('.db', '.sqlite', '.sqlite3'):
        parser.error('La base debe ser un archivo SQLite; no se abren archivos de credenciales.')
    if args.evidencia.suffix.lower() != '.json' or args.evidencia.exists():
        parser.error('La evidencia debe ser un JSON nuevo; no se sobrescriben archivos existentes.')
    if args.evidencia.resolve() == args.base.resolve():
        parser.error('La evidencia y la base deben ser archivos distintos.')
    import httpx
    from terminal import db
    from terminal.verificacion_gratuita import verificar
    from terminal.config import cargar_ajustes
    ajustes = cargar_ajustes()  # SIN_ENV=1: solo configuración y límites, nunca el archivo de claves.
    con = db.conectar(args.base)
    try:
        with httpx.Client(timeout=15, follow_redirects=False, trust_env=False) as cliente:
            variables = ('BANXICO_TOKEN', 'FRED_API_KEY', 'ALPHAVANTAGE_API_KEY', 'SEC_USER_AGENT')
            env = {v: os.environ.get(v) for v in variables}
            resultado = verificar(con, env=env, cliente=cliente, guardar=args.guardar, bono10=args.bono10,
                                  solo=args.solo, ajustes=ajustes, bpa=args.bpa, macro_laboral=args.macro_laboral)
        args.evidencia.parent.mkdir(parents=True, exist_ok=True)
        with args.evidencia.open('x', encoding='utf-8') as archivo:
            json.dump(resultado, archivo, ensure_ascii=False, indent=2)
        print(json.dumps(resultado, ensure_ascii=False))
    finally:
        con.close()


if __name__ == '__main__':
    main()
