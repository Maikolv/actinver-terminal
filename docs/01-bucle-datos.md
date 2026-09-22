# 01 · Mapa del bucle de datos

```
 ┌────────────┐   ┌────────────┐   ┌──────────────┐   ┌──────────┐   ┌───────────┐   ┌──────────────┐   ┌─────────────┐   ┌────────────┐
 │ Adquisición│──►│ Validación │──►│ Normalización│──►│ Análisis │──►│ Propuesta │──►│ Visualización│──►│ Seguimiento │──►│ Evaluación │
 └────────────┘   └────────────┘   └──────────────┘   └──────────┘   └───────────┘   └──────────────┘   └─────────────┘   └─────┬──────┘
       ▲                                                                                                                         │
       └─────────────────────────────── ajuste de fuentes, umbrales, criterios y supuestos ◄────────────────────────────────────┘
```

| Etapa | Qué ocurre | Dónde | Controles |
|---|---|---|---|
| **Adquisición** | Descarga incremental por proveedor (FX: Banxico → FRED; EE. UU.: Tiingo; BMV: EODHD); importación CSV del usuario (operaciones, posiciones, precios/NAV). Prioriza instrumentos en cartera. | `terminal/ingesta.py`, `adaptadores/`, `importar.py` | Límites por hora/día persistentes, reintentos exponenciales ante 429/5xx, reconexión ante fallos de red, credenciales solo por entorno, registro en `ingestas` |
| **Validación** | Tipos, fechas, signos, instrumento existente, moneda coherente, tamaño y tipo de archivo, duplicados por huella; ventas no mayores a la posición. | `cartera.validar`, `importar.leer` | Vista previa obligatoria; importación todo-o-nada; auditoría |
| **Normalización** | Moneda base MXN (USD × tipo de cambio del día, con tolerancia de rezago); cierres ajustados por dividendos y splits para análisis, sin ajustar para valoración; calendarios NYSE/BMV; eventos corporativos almacenados. | `mercado.py`, `vigencia.py` | Sin conversión si no hay tipo de cambio (queda vacío, no se inventa) |
| **Análisis** | Rendimientos diarios alineados, estimación de μ (James-Stein) y Σ (Ledoit-Wolf), filtros de elegibilidad con motivo, métricas de riesgo. | `optimizador.universo`, `rendimientos` | Historia mínima (504 sesiones); datos vencidos excluidos |
| **Propuesta** | Media-varianza con topes, grupos (deuda, USD, ilíquidos), costos amortizados y regularización; asignación discreta en títulos; cambios frente a posiciones con banda. | `optimizador.proponer`, `cambios` | Suspensión si faltan datos o tipo de cambio; reproducibilidad (huella, versiones, semilla) |
| **Visualización** | Resumen, propuestas, cartera, datos, perfil; cada cifra con fuente, fecha y vigencia. | `web/` | Etiquetas «dato retrasado», «sin datos suficientes», «sintético»; propuestas guardadas se marcan «no actual» si envejecen o cambia el perfil |
| **Seguimiento** | Posiciones, costo promedio, realizado/no realizado, dividendos, comisiones, TWR, TIR, comparación con índice. | `cartera.py`, `/api/cartera` | Total «incompleto» si falta un precio |
| **Evaluación** | Validación walk-forward fuera de muestra con costos, comparación contra 1/N y cartera actual, sensibilidad y escenarios; puntuación por criterios. Se revisa en cada recálculo y periódicamente (ver [05-recurrencia.md](05-recurrencia.md)). | `optimizador` | Sin información futura (prueba automatizada) |

## Umbrales de vigencia por tipo de dato

| Tipo de dato | Calendario | Vigente | Retrasado | Vencido |
|---|---|---|---|---|
| Cierre de acción/ETF | NYSE (SIC, ETF) o BMV | Última sesión cerrada | 1 sesión de atraso | > 1 sesión |
| Valor liquidativo (fondo) | BMV | ≤ 1 sesión | ≤ 3 sesiones | > 3 sesiones |
| Tipo de cambio | BMV | ≤ 1 sesión | ≤ 5 sesiones (FRED publica con rezago) | > 5 sesiones |
| Retrasado intradía | Mercado abierto | ≤ 20 min | — | > 20 min |
| Tiempo real | Mercado abierto | ≤ 120 s | > 120 s | — |
| Sintético (demo) | — | nunca | — | siempre «sintético» |

Todos se editan en `[vigencia]` de la configuración. Los festivos (p. ej. 16 de septiembre en la BMV) no cuentan como atraso.
