# Auditoría inicial (fase 0)

Fecha: 2026-09-23. Rama de trabajo: `ampliacion-integral`, creada desde `main` en el commit `89c9841` con el árbol limpio.

## Identidad del repositorio

La instrucción se refiere al repositorio `reto-actinver`. En `C:\Users\MIKE\Desktop\Repos` no existe una carpeta con ese nombre. El repositorio del Reto es `actinver-terminal`: se creó para el Reto Actinver 2026 y contiene todo el trabajo previo. No se renombra, para no romper rutas, `start.bat` ni el índice de código.

No hay ningún `AGENTS.md`. Las instrucciones vigentes del proyecto están en `CLAUDE.md`.

## Estado observado

| Aspecto | Hallazgo |
|---|---|
| Lenguajes | Python 3.12 (servidor y cálculo), JavaScript sin dependencias ni build (interfaz), HTML/CSS |
| Gestor | `uv` con `uv.lock` (dependencias fijadas); sin componente npm/pnpm |
| Servidor | FastAPI local en 127.0.0.1:8765. Controles: Host local, CSRF, Origin, CSP estricta y límites por ruta |
| Datos | SQLite (`data/terminal.db`; la demo usa `data/demo/`), migraciones versionadas (`version_esquema`) |
| Pruebas | pytest: 106 pruebas al iniciar esta fase, 129 al cerrarla |
| CI | No hay CI remota. Se ejecutan localmente `uv run pytest` y el escaneo de secretos (`scripts/escanear_secretos.py`) |
| Secretos | `.env` ignorado por Git y sin valores. Escaneo del historial: 0 hallazgos |
| Historial relevante | Dos sesiones han hecho commits en paralelo (D-30). Se trabaja en una rama para que los cambios sean revisables |
| Deuda visible | `optimizador.py` importa `Portfolio` sin usarlo (ruff F401, previo). Las propuestas usan la historia del mercado de origen como aproximación del SIC (D-34) |

## Flujo actual

```
Entrada de precios ─┬─ FRED/Banxico (tipo de cambio) ─┐
                    ├─ Tiingo/Alpaca/EODHD (cierres, con clave; hoy sin claves)
                    ├─ Alpaca IEX en vivo (referencia de origen, USD)
                    ├─ CSV del participante (precios, NAV, operaciones)
                    └─ Webhook TradingView (eventos)  ┘
        │
Normalización ─ cotizaciones.normalizar_simbolo (BMV local / SIC / origen extranjero; rechaza CFD y cripto)
        │        vigencia (calendarios XMEX/XNYS) · migraciones (event_time / available_at / ingested_at)
Almacenamiento ─ SQLite: precios, fx, cotizaciones_registro, cobertura, noticias, insiders, eventos_macro,
        │        transacciones (etapa), pendientes, bitácora, snapshots, experimentos, pronósticos
Cartera ─ cartera.py (costo promedio, realizado, splits) · servicios.operaciones_etapa (práctica | competencia)
        │
Modelos ─ optimizador (skfolio, 4 propuestas) · comparador_modelos · investigacion (walk-forward, referencias, prueba intacta)
        │
Alertas ─ alertas.py (flanco de subida, enfriamiento, inhibición por datos, ficha de revisión) → notificador
        │
Interfaz ─ Resumen · Pasado/Presente/Futuro · Propuestas · Alertas · Mi cartera · Mercado · Datos · Reto
```

## Catálogo del simulador

La lista real de valores del simulador **no está en el repositorio**. Solo existe el universo verificado a partir del PDF «Datos Actinver» y de fuentes oficiales: 176 instrumentos activos o por confirmar. La importación manual existe en «Mi cartera → Importar», tipo `universo`, con ejemplo en `ejemplos/catalogo_simulador.csv`. La cobertura de cada instrumento queda **pendiente** mientras no se importe esa lista: la terminal no supone que todo valor de la BMV sea elegible.

Tipos de instrumento que se distinguen:

- **BMV local:** `BMV:*`, MIC XMEX, en MXN.
- **SIC:** `SIC:*`, MIC XMEX, en MXN. Se guarda aparte su listado de origen (MIC XNYS o XNAS, en USD).
- **Fondos Actinver:** `FONDO:*`, valorados con su NAV.
- **ETF del SIC.**
- **Instrumentos no elegibles:** con estado `por_confirmar`, o detectados como CFD o cripto por `clasificacion.py`.

Un ADR estadounidense, la acción del SIC en pesos y la acción negociada en EE. UU. son objetos distintos (`correspondencia_simbolos`).

## Comparación con FinceptTerminal (evaluación)

FinceptTerminal (AGPL-3.0, C++/Qt) resuelve la BMV con el sufijo `.MX` de Yahoo. No tiene un feed licenciado. Su licencia impide copiar componentes a este proyecto MIT. Se toma solo la idea de un buscador de comandos, que aquí ya cubren las pestañas y la búsqueda del universo.

## Secuencia de cambios de esta fase

1. Reglas del Reto versionadas, con aviso de discrepancia, y pruebas de límites (`registro.py`, `test_ampliacion.py`).
2. Entidades nuevas: correspondencia de símbolos, órdenes pendientes, bitácora, instantáneas, versiones de modelo, licencias de fuente. Migraciones v2 y v3 con `ingested_at` y disparadores de integridad.
3. Control de clasificación contra CFD y cripto.
4. Inhibición de alertas direccionales y ficha de revisión.
5. Investigación ampliada:
   - variable de noticias sujeta a `available_at`;
   - referencias de estrategia;
   - caída máxima y sensibilidad a costos;
   - prueba de Diebold-Mariano;
   - verificación con backtrader;
   - candidato Kronos;
   - experimento con índices reales de FRED.
6. Política de tokens (`scripts/indice_contexto.py`) y documentación exigida.
