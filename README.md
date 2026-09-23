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
| `uv run pytest` | 63 pruebas |
| `uv run python scripts/escanear_secretos.py` | Escaneo de secretos en todo el historial de Git |
| `uv run python scripts/verificar_universo.py --descargar` | Re-verifica el universo contra Nasdaq Trader y la BMV |

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
| Barchart OnDemand | Históricos | `BARCHART_API_KEY` (contrato) |
| ForexFactory | Calendario macro | No |
| Seeking Alpha RSS | Titulares por emisora | No |
| SEC EDGAR | Formulario 4 (insiders) | `SEC_USER_AGENT` (su contacto) |
| TradingView | Gráfica (widget oficial) | No |
| CSV propio | NAV de fondos, precios, operaciones, universo del simulador | No |

**Tiempo real**: ninguna fuente gratuita autorizada lo da para la BMV; todo se presenta como cierre con su fecha. Opciones en [docs/fuentes.md](docs/fuentes.md#tiempo-real).

## Configuración

- `config/ajustes.ejemplo.toml` (versionado): vigencia, proveedores y límites, referencias, motor, alertas, perfiles, costos, optimización, puntuación. Cambios propios en `config/local.toml` (no versionado).
- `config/reto.yaml`: reglas del Reto.
- `.env`: credenciales (ignorado por Git).

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
