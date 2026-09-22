# Terminal de portafolios (local)

Terminal local en español para comparar dos propuestas de portafolio —**solo acciones** y **acciones + ETF + fondos**— contra la cartera registrada del inversionista, con seguimiento de posiciones, flujos, costo promedio, rendimiento realizado y no realizado, dividendos, comisiones, evolución histórica y comparación con un índice de referencia.

**Solo informa y simula.** No existe ninguna ruta que envíe órdenes a una casa de bolsa. Los precios capturados en el PDF de origen nunca se muestran como cotizaciones actuales.

## Inicio rápido (Windows, PowerShell o Git Bash)

Requisitos: [uv](https://docs.astral.sh/uv/) (instala Python 3.12 automáticamente). Nada más.

```bash
cd C:\Users\MIKE\Desktop\Repos\terminal-portafolios
uv sync
uv run terminal demo        # modo demostración: datos SINTÉTICOS etiquetados, sin credenciales
```

Se abre `http://127.0.0.1:8765`. Para usar datos reales:

```bash
copy .env.example .env      # y complete las claves que tenga (ver «Fuentes de datos»)
uv run terminal actualizar  # descarga tipo de cambio y precios respetando límites
uv run terminal iniciar     # abre la terminal con datos reales
```

Sin ninguna clave, el modo real ya obtiene el tipo de cambio USD/MXN de FRED; las propuestas quedan **suspendidas** («sin datos suficientes») hasta que haya precios de un proveedor configurado o importados por usted. Esto es intencional: la terminal no simula cotizaciones.

| Comando | Qué hace |
|---|---|
| `uv run terminal iniciar` | Servidor local en 127.0.0.1:8765 y abre el navegador |
| `uv run terminal demo` | Igual, con base separada `data/demo/` y datos sintéticos etiquetados |
| `uv run terminal actualizar` | Actualización incremental de datos (respeta límites por proveedor) |
| `uv run terminal respaldar` | Copia verificada (`PRAGMA integrity_check`) en `data/respaldos/`, conserva 14 |
| `uv run pytest` | 44 pruebas: libro, vigencia, universo, optimizador, seguridad y adaptadores |
| `uv run python scripts/verificar_universo.py --descargar` | Re-verifica el universo contra Nasdaq Trader y la BMV |

## Uso

1. **Perfil**: riesgo, horizonte, capital, peso máximo por activo, exposición máxima al dólar, escenario y exclusiones. Se guardan en la base local sin tocar código.
2. **Mi cartera**: registre operaciones manualmente o importe CSV (`operaciones`, `posiciones iniciales` o `precios / valor liquidativo`). Siempre hay vista previa; nada se guarda hasta confirmar. Duplicados detectados; el archivo original se conserva. Correcciones y anulaciones quedan en auditoría.
3. **Recalcular propuestas**: calcula ambas, las compara con 1/N y con mantener su cartera, y muestra puntuación, motivos, riesgos, escenarios, sensibilidad y cambios sugeridos.
4. **Datos**: proveedor, bolsa, moneda, zona horaria, hora del dato, tipo (cierre, valor liquidativo, tipo de cambio), retraso medido y vigencia de cada instrumento.

Plantillas CSV: `http://127.0.0.1:8765/api/plantilla/transacciones` (también `posiciones` y `precios`).

## Fuentes de datos

| Proveedor | Uso en la terminal | Credencial | Condiciones |
|---|---|---|---|
| FRED (DEXMXUS) | Tipo de cambio USD/MXN diario (rezago de días) | No | Datos públicos, citar fuente |
| Banxico SIE (SF43718) | Tipo de cambio FIX; prioridad sobre FRED | Token gratuito | Límites del SIE |
| Tiingo EOD | Cierres de EE. UU. para emisoras del SIC y ETF (ajuste por dividendos/splits) | Clave gratuita | Uso personal, sin redistribución |
| EODHD | Cierres de la BMV | Clave (20/día gratis) | Planes de pago para más cobertura |
| Archivo CSV | Valor liquidativo de fondos y cualquier precio que usted obtenga legítimamente | No | — |

Detalle, evaluación de TradingView, Seeking Alpha, Forex Factory, InsiderFinance, Barchart y Dukascopy en [docs/10-fuentes.md](docs/10-fuentes.md). **Tiempo real**: ninguna de las fuentes configuradas lo ofrece; ver [docs/10-fuentes.md](docs/10-fuentes.md#tiempo-real).

## Configuración

- `config/ajustes.ejemplo.toml`: valores por defecto versionados (vigencia, límites, perfiles, costos, optimización, pesos de la puntuación). Para cambiarlos cree `config/local.toml` (no versionado) con solo las secciones a modificar.
- `.env`: credenciales. Ignorado por Git.
- `config/universo.csv`: universo verificado (lo genera `scripts/verificar_universo.py`).

## Estructura

```
terminal/            núcleo (Python)
  adaptadores/       FRED, Banxico, Tiingo, EODHD, archivo, generador demo
  vigencia.py        calendarios NYSE/BMV, festivos, umbrales por tipo de dato
  mercado.py         precios normalizados a MXN con fuente y vigencia
  cartera.py         libro de operaciones, costo promedio, TWR, TIR
  importar.py        CSV validado con vista previa, duplicados y auditoría
  optimizador.py     universo elegible, media-varianza (skfolio), walk-forward, escenarios, puntuación
  app.py, seguridad.py  servidor local y controles HTTP
web/                 interfaz (HTML/CSS/JS sin dependencias)
config/              ajustes de ejemplo, universo verificado, fondos, candidatos ETF, transcripción del PDF
scripts/             transcripción y verificación del universo, cartera demo, tareas de Windows
docs/                diagnóstico, PRD, planes, decisiones, matriz de aplicabilidad, evidencia
tests/               pruebas automatizadas
```

## Documentación

| Documento | Contenido |
|---|---|
| [00 Diagnóstico CAIO](docs/00-diagnostico-caio.md) | Definición, supuestos y evaluación de capacidades, arquitectura, información y operación |
| [01 Bucle de datos](docs/01-bucle-datos.md) | Adquisición → validación → normalización → análisis → propuesta → visualización → seguimiento → evaluación |
| [02 PRD](docs/02-prd.md) | Usuarios, casos de uso, criterios de aceptación y límites |
| [03 Plan de implementación](docs/03-plan-implementacion.md) | Etapas, dependencias y riesgos |
| [04 Adopción](docs/04-adopcion.md) | Instalación, configuración y uso |
| [05 Recurrencia](docs/05-recurrencia.md) | Actualización, revisión del modelo, mantenimiento, respaldos, monitoreo |
| [06 Decisiones](docs/06-decisiones.md) | Registro de decisiones (ADR) |
| [07 Matriz de aplicabilidad](docs/07-matriz-aplicabilidad.md) | Seguridad, sitio, medición y diseño |
| [08 Inventario de repositorios](docs/08-inventario-repositorios.md) | Qué se reutilizó, corrigió y descartó |
| [09 Auditoría del PDF](docs/09-auditoria-pdf.md) | Revisión página por página y hallazgos |
| [10 Fuentes](docs/10-fuentes.md) | Proveedores y URL candidatas: uso permitido, licencia, API |
| [11 Diseño](docs/11-diseno.md) | Decisiones de interfaz |
| [12 Seguridad](docs/12-seguridad.md) | Controles, revisión de secretos y rotación |
| [13 Evidencia](docs/13-evidencia.md) | Pruebas de los criterios de aceptación |

## Aviso

Herramienta de análisis personal. No es asesoría de inversión ni una recomendación personalizada; los rendimientos esperados son estimaciones inciertas basadas en datos históricos. Verifique disponibilidad, costos y condiciones de cada instrumento con su casa de bolsa antes de operar.
