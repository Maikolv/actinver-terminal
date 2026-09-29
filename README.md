# Actinver Terminal

Terminal local en español para el **Reto Actinver 2026** (y para inversión personal): calcula y recalcula en todo momento las mejores carteras **Solo acciones** y **Acciones + ETF + fondos**, cada una con dos lentes —**máximo rendimiento esperado** y **ajuste a su perfil y cartera**—, sigue su cartera real y le avisa cuando conviene cambiar algo.

**Solo informa y simula.** No existe ninguna ruta que envíe órdenes a una casa de bolsa ni al simulador del Reto. Los precios del PDF de origen nunca se muestran como cotizaciones actuales.

## Inicio en un comando (Windows)

```bat
start.bat
```

Requisito único: [uv](https://docs.astral.sh/uv/) (`winget install astral-sh.uv`). `start.bat demo` abre la demostración con datos **sintéticos** etiquetados en una base separada. Equivalentes: `uv run terminal iniciar` / `uv run terminal demo`. Se abre `http://127.0.0.1:8765`.

Para datos reales copie `.env.example` como `.env` y complete las claves que tenga. Sin ninguna clave ya funcionan el tipo de cambio (FRED), el calendario macro (ForexFactory) y los titulares (Seeking Alpha); las propuestas quedan **suspendidas** hasta tener precios (proveedor configurado o CSV propio): la terminal no simula cotizaciones.

| Comando | Qué hace |
|---|---|
| `uv run terminal iniciar` | Servidor local + motor automático (recalcula y evalúa alertas) |
| `uv run terminal demo` | Igual, con datos sintéticos en `data/demo/` |
| `uv run terminal actualizar` | Actualización incremental de datos (respeta límites) |
| `uv run terminal respaldar` | Respaldo verificado en `data/respaldos/` |
| `uv run terminal alpaca` | Comprueba las claves de Alpaca (solo datos) |
| `uv run terminal telegram` | Detecta su chat de Telegram, lo guarda en `.env` y envía una prueba |
| `uv run terminal investigar` | Experimento sin fuga de información (walk-forward → validación → prueba) y pronósticos |
| `uv run terminal cobertura` | Verifica cobertura por símbolo y proveedor; escribe `docs/cobertura.md` |
| `uv run terminal webhook-secreto` | Genera el secreto del webhook de TradingView en `.env` |
| `uv run terminal reporte cierre` | Reporte en Markdown en `data/reportes/` (`preapertura`, `cierre`, `semanal`) |
| `uv run pytest` | 146 pruebas |
| `uv run python scripts/escanear_secretos.py` | Escaneo de secretos en todo el historial de Git |
| `uv run python scripts/verificar_universo.py --descargar` | Re-verifica el universo contra Nasdaq Trader y la BMV |

## Instalación desde cero

1. Instale [uv](https://docs.astral.sh/uv/): `winget install astral-sh.uv`.
2. Clone o copie esta carpeta y abra una terminal **dentro de ella**. En PowerShell, los scripts de la carpeta actual se ejecutan con `.\`.
3. Ejecute `.\start.bat`. La primera vez, `uv` crea el entorno con las versiones fijadas en `uv.lock`.
4. Opcional: copie `.env.example` como `.env` y llene las claves que tenga. Vea [docs/proveedores.md](docs/proveedores.md).

**Importar operaciones confirmadas.** Use «Mi cartera → Importar», con el tipo `transacciones` y el ejemplo `ejemplos/operaciones_confirmadas.csv`. También puede capturarlas una por una. Solo las operaciones **confirmadas** cambian posiciones y efectivo. Las órdenes pendientes se anotan como referencia en «Pasado · Presente · Futuro». Importe la lista del simulador con el tipo `universo` (ejemplo: `ejemplos/catalogo_simulador.csv`).

**Cuenta del Reto.** En «Mi cartera → Capturar desde el portal», copie usted la tabla de posiciones, el efectivo y el valor total desde su sesión del Reto; péguelos, revise la vista previa e indique la hora que muestra el portal. La terminal no accede al portal. Rechaza capturas incompletas, descuadradas o anteriores a la última. Mientras no haya una captura válida de la etapa actual, el saldo local se muestra claramente como registro de la terminal, no como saldo confirmado del Reto. Telegram y escritorio avisan de cambios entre capturas y de posibles movimientos sugeridos; el correo requiere configurar SMTP en `.env`.

**Pruebas.** `uv run pytest` ejecuta la suite (170 pruebas al 29-sep-2026). `uv run python scripts/escanear_secretos.py` revisa el historial en busca de secretos. `uv run python scripts/experimento_indices_fred.py` repite el experimento con datos reales de FRED.

**Mantenimiento desde el editor.** Abra la carpeta en su editor o agente (por ejemplo Cline o Claude Code). Las convenciones están en `CLAUDE.md`. Busque con `uv run python scripts/indice_contexto.py buscar "…"` antes de leer archivos completos.

### Resolución de fallos

| Síntoma | Causa y solución |
|---|---|
| `start.bat` no se reconoce | Está en otra carpeta o falta `.\`: `cd …\actinver-terminal` y luego `.\start.bat` |
| `Failed to spawn: terminal` | Ejecutó `uv run terminal` fuera de la carpeta del proyecto |
| `terminal.exe` en uso al actualizar | Hay otra terminal abierta: ciérrela con `Ctrl+C` |
| Todo aparece como «SIN PRECIO CONFIABLE» | No hay proveedor BMV verificado. Capture precios del portal o configure una fuente y ejecute `uv run terminal cobertura` |
| Aviso «Las reglas del Reto cambiaron» | `config/reto.yaml` cambió: revíselo contra las bases y márquelo como revisado en la pestaña «Reto» |
| Propuestas suspendidas | Faltan precios o el tipo de cambio: revise la pestaña «Datos» |

## Monitor y predicción (versión 0.5)

- **Pasado · Presente · Futuro**: pestaña con tres espacios separados.
  - **PASADO:** hechos con su hora de disponibilidad.
  - **PRESENTE:** última cotización BMV confiable o «SIN PRECIO CONFIABLE», referencia externa aparte, efectivo, posiciones confirmadas, exposición, alertas y saldo del portal que usted captura.
  - **FUTURO:** pronósticos a 1 y 5 sesiones con rangos, siempre etiquetados como estimaciones.
- **Proveedores**: vea [docs/proveedores.md](docs/proveedores.md) y la tabla [docs/cobertura.md](docs/cobertura.md). Hoy no hay ninguna fuente BMV con licencia conectada; los conectores BMV, LSEG e ICE esperan su contrato y su documentación.
- **Investigación**: vea [docs/investigacion.md](docs/investigacion.md). Si el modelo no supera a las referencias simples fuera de muestra, no se emite recomendación.
- **Límites del Reto**: la terminal no inicia sesión en el portal, no extrae datos de él y no registra órdenes (reglamento §17).

## Qué muestra

- **Resumen**: estado de datos y del motor, alertas nuevas, Reto (sesiones restantes, reglas, pendientes), cartera (valor, resultado, caída, vs IPC) y las dos propuestas con selector de lente, clasificación, riesgos y cambios sugeridos.
- **Propuestas**: pesos, montos, títulos enteros, razones, puntuación explicada, rendimiento esperado al cierre del Reto, validación fuera de muestra, escenarios, sensibilidad, cambios frente a su cartera y «Simular estos cambios».
- **Alertas**: deriva con mejora neta de costos, stop-loss, toma de utilidad, caída desde máximo, evento macro, insider, noticia de alto impacto y alertas técnicas; notificación de escritorio de Windows; «Simular cambio».
- **Mi cartera**: operaciones (captura o CSV con vista previa), posiciones, costo promedio, realizado/no realizado, dividendos, comisiones con IVA, curva de valor, caída, IPC/S&P 500/60-40, auditoría.
- **Mercado**: calendario macro, titulares e insiders de sus emisoras; gráfica por activo (widget de TradingView).
- **Datos**: proveedor, bolsa, moneda, zona horaria, hora, tipo de dato, retraso y vigencia de cada instrumento.
- **Reto y perfil**: reglas oficiales (con «regla sin confirmar»), tareas pendientes, perfil y criterios.

## Reto Actinver 2026

Reglas en `config/reto.yaml` (fuente: bases oficiales, consultadas el 23-sep-2026): 1 000 000 actipesos; práctica 28 sep–2 oct; competencia 5 oct–13 nov 15:00; comisión 0.10 % + IVA; al menos 5 emisoras; máximo 50 % por emisora; sin dividendos (sí splits); horario BMV 07:30–14:00 hasta el 2 nov y 08:30–15:00 desde el 3 nov. Importe la lista de instrumentos del simulador en «Mi cartera → Importar» para restringir el universo. La calificación por avance (Acelera Academy) no la cubre la terminal.

## Fuentes y credenciales

| Fuente | Uso | Credencial |
|---|---|---|
| FRED | USD/MXN (rezago 2–3 sesiones) | No |
| Banxico SIE | USD/MXN FIX (prioritario) | `BANXICO_TOKEN` gratuito |
| Tiingo | Cierres de EE. UU. (SIC y ETF) | `TIINGO_API_KEY` gratuita |
| EODHD | Cierres de la BMV | `EODHD_API_KEY` (20/día gratis) |
| Alpaca (solo datos) | Cierres de EE. UU. y **precio en vivo IEX** del SIC/ETF (30 símbolos) | `ALPACA_API_KEY_ID` + `ALPACA_API_SECRET_KEY` (gratis) |
| Barchart OnDemand | Históricos | `BARCHART_API_KEY` (contrato) |
| ForexFactory | Calendario macro | No |
| Seeking Alpha RSS | Titulares por emisora | No |
| SEC EDGAR | Formulario 4 (insiders) | `SEC_USER_AGENT` (su contacto) |
| TradingView | Gráfica (widget oficial) | No |
| CSV propio | NAV de fondos, precios, operaciones, universo del simulador | No |

**Tiempo real**: las emisoras del SIC y los ETF se actualizan en vivo con Alpaca (IEX, gratis) y se convierten a MXN con el tipo de cambio más reciente; las emisoras locales de la BMV no tienen fuente gratuita autorizada y se presentan como cierre con su fecha. Opciones en [docs/fuentes.md](docs/fuentes.md#tiempo-real).

## Configuración

- `config/ajustes.ejemplo.toml` (versionado): vigencia, proveedores y límites, referencias, motor, alertas, perfiles, costos, optimización, puntuación. Cambios propios en `config/local.toml` (no versionado).
- `config/reto.yaml`: reglas del Reto.
- `.env`: credenciales (ignorado por Git).

## Documentación de la ampliación integral

| Documento | Contenido |
|---|---|
| [initial-audit](docs/initial-audit.md) | Arquitectura observada y flujo de datos |
| [actinver-rules](docs/actinver-rules.md) | Reglas con fragmento, versión y pruebas |
| [source-matrix](docs/source-matrix.md) · [sources/](docs/sources/) | Seis sitios y la BMV: papel, modalidad, cobertura, latencia y condiciones |
| [instrument-matrix](docs/instrument-matrix.md) | Símbolo, serie, MIC, moneda, origen, proveedor, latencia y discrepancia por instrumento |
| [repository-adoption-matrix](docs/repository-adoption-matrix.md) | Los 63 repositorios, con commit, licencia, uso y evidencia |
| [quant-methodology](docs/quant-methodology.md) · [model-card](docs/model-card.md) | Metodología y resultados fuera de muestra |
| [decision-workflow](docs/decision-workflow.md) · [data-providers](docs/data-providers.md) · [instrument-mapping](docs/instrument-mapping.md) | Boleta, estados de orden y registro manual; proveedores; correspondencia de series |
| [token-budget](docs/token-budget.md) | Índice con hashes, fragmentos mínimos y caché |
| [arquitectura](docs/arquitectura.md) · [DESIGN.md](DESIGN.md) | Diagramas y sistema visual |

## Documentación

| Documento | Contenido |
|---|---|
| [00 Diagnóstico CAIO](docs/00-diagnostico-caio.md) | Capacidades, arquitectura, información, operación; supuestos |
| [01 Bucle de datos](docs/01-bucle-datos.md) | Adquisición → … → propuesta → alerta → visualización → seguimiento → evaluación |
| [02 PRD](docs/02-prd.md) | Usuarios, casos de uso, criterios de aceptación, límites |
| [03 Plan de implementación](docs/03-plan-implementacion.md) | Etapas, dependencias, riesgos |
| [04 Adopción](docs/04-adopcion.md) | Instalación, configuración, primer uso en el Reto |
| [05 Recurrencia](docs/05-recurrencia.md) | Datos, re-optimización, modelo, respaldos, monitoreo, rotación de claves |
| [09 Auditoría del PDF](docs/09-auditoria-pdf.md) | Revisión página por página |
| [13 Evidencia](docs/13-evidencia.md) | Criterios de aceptación con pruebas, Lighthouse y capturas |
| [Repositorios](docs/repos.md) | 64 fichas (lectura fácil, técnico, uso, cambios) |
| [Fuentes](docs/fuentes.md) | Tipo, retraso medido, límites, credenciales, condiciones |
| [Decisiones](docs/decisiones.md) | Registro D-01 a D-30 |
| [Seguridad](docs/seguridad.md) | Checklist aplicado / previsto / no aplica con evidencia |
| [Matriz](docs/matriz.md) | Sitio, legal, SEO, indexación, medición |
| [Diseño](docs/diseno.md) | Decisiones de interfaz |
| [CHANGELOG](CHANGELOG.md) | Historial de cambios |

## Aviso

Herramienta de análisis personal. No es asesoría de inversión ni recomendación; los rendimientos esperados son estimaciones inciertas con datos históricos. Verifique disponibilidad, costos y reglas con Actinver y con las bases del Reto.
