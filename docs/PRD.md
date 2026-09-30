# PRD — Actinver Terminal

Documento de producto vigente al **30-sep-2026**. El PRD original (22-sep) con casos de uso y requisitos numerados está en [02-prd.md](02-prd.md); este archivo lo actualiza con lo añadido para el Reto Actinver 2026.

## Propósito

Terminal **local** (127.0.0.1) que ayuda a un participante del **Reto Actinver 2026** y a un inversionista individual a:

1. saber qué cartera conviene con los datos disponibles, con criterios explícitos y sin prometer rendimientos;
2. cumplir las reglas del Reto (≥ 5 emisoras, ≤ 50 % por emisora, horario, costos);
3. enterarse a tiempo, por Telegram, de qué órdenes capturar y por qué;
4. saber en todo momento **qué dato es confirmado, estimado, vencido o falta**.

**La terminal solo informa y simula.** Nunca inicia sesión en el portal del Reto, no lee la sesión del usuario ni registra órdenes (reglamento §17). Cada orden la captura el participante a mano.

## Usuarios

| Usuario | Necesidad principal |
|---|---|
| Participante del Reto (principal) | Plan diario de órdenes con títulos, precio límite y razón; cumplir reglas; alertas en el celular |
| Inversionista individual | Seguir su cartera, comparar propuestas y entender riesgos antes de decidir en su casa de bolsa |
| Persona de confianza (secundaria) | Revisar supuestos y lógica |

## Periodo objetivo

| Etapa | Fechas (bases oficiales, consultadas el 29-sep-2026) |
|---|---|
| Práctica | 28-sep al 2-oct-2026 |
| Competencia | 5-oct al 13-nov-2026, 15:00 CDMX |
| Horario BMV | 07:30–14:00; desde el 3-nov, 08:30–15:00 |

Capital: 1,000,000 actipesos. Gana la **mayor ganancia absoluta**. Comisión: 0.10 % + IVA. El Reto no paga dividendos y sí replica splits. Detalle y citas: [RULES.md](RULES.md).

## Funciones

| Área | Qué hace | Estado |
|---|---|---|
| Resumen | Panel «¿En qué puedo confiar hoy?» con nivel por tema y acción concreta | Operativo |
| Mi cartera | Registro local de operaciones y **captura copiada del portal** (copiar y pegar), con conciliación | Operativo; sin captura del portal aún |
| Datos y precios | Cierres diarios por instrumento con fuente, fecha, moneda y vigencia | Operativo (sin tiempo real) |
| Ranking | Clasificación de emisoras BMV y SIC en MXN con la misma base | Operativo |
| Propuestas | 3 lentes (rendimiento, ajuste, máxima puntuación) × 2 universos, más variantes nacionales y extranjeras | Operativo |
| Plan del día | Mensaje por Telegram en cuanto hay cierres de la última sesión; «plan corregido» si cambia antes de la apertura | Operativo |
| Boletas | Guía para capturar a mano: títulos, límite, costo y efecto. Sin cotización confiable: guía condicional con banda de ±2 % | Operativo |
| Alertas | Cambios de cuenta, captura pendiente, posible movimiento, reglas del Reto | Telegram y escritorio operativos; correo pendiente |
| Bot de Telegram | `/plan /boletas /estado /alertas /cartera /ayuda` y preguntas libres | Operativo; Claude inactivo sin clave |
| Noticias | Titulares del RSS público de Seeking Alpha (contexto, no señal) | Operativo |
| Acceso remoto | Tailscale Serve privado, con identidad | Operativo |

## Requisitos no negociables

- Todo precio y señal muestra **fuente, fecha y hora, moneda y estado** (actual, retrasado, vencido o ausente).
- Se bloquean propuestas y boletas que dependen de precios insuficientes o no verificables.
- Durante el Reto, el universo se limita al **catálogo del simulador** del participante.
- El millón local nunca se presenta como saldo confirmado.
- No hay rutas de órdenes ni integración con brókers. Los secretos viven solo en `.env`.

## Criterios de aceptación vigentes

| Criterio | Evidencia |
|---|---|
| Suite de pruebas completa | `uv run pytest`: 214 pruebas pasando (30-sep-2026) |
| Sin rutas de órdenes reales | `test_no_existen_rutas_de_ordenes_reales` |
| Universo del Reto = catálogo del simulador | `tests/test_catalogo_simulador.py` |
| Splits reproducidos, dividendos no | `test_precios_solo_splits_...` |
| Plan del día único por sesión, con corrección controlada | `tests/test_resumen.py` |

## Fuera de alcance

Ejecución de órdenes, scraping del portal del Reto, precios en tiempo real sin contrato, asesoría de inversión personalizada con dinero real.

Relacionados: [ARCHITECTURE.md](ARCHITECTURE.md) · [TASKS.md](TASKS.md) · [MEMORY.md](MEMORY.md)
