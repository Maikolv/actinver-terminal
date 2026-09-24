# Flujo de decisión: alertas, boleta y registro manual de la ejecución

**La terminal nunca registra, confirma ni cancela órdenes en Actinver** (reglamento §17: prohibidos los sistemas automáticos, con descalificación incluso por el intento). Todo lo que sigue es para que el participante decida y capture la orden **a mano**, rápido y con la información completa.

## 1. Alertas

Cada alerta (`terminal/alertas.py`) tiene:

- **prioridad**: 1 crítica, 2 aviso, 3 informativa;
- **caducidad**: 6 h para datos, 24 h para posición y reglas, 48–72 h para eventos, 7 días para deterioro del modelo;
- **deduplicación**: se dispara solo en el flanco de subida y tiene un enfriamiento de 6 h;
- una **ficha** con qué ocurrió, cuándo, qué fuente lo respalda, cuánto afecta al portafolio (en MXN), cuál es la incertidumbre y qué debe verificar el participante.

| Regla | Dispara cuando |
|---|---|
| `dato_vencido`, `datos_inciertos` | Un precio está vencido, no es confiable o las noticias se contradicen; se inhiben las alertas direccionales |
| `cambio_brusco` | El último precio de una posición cambió al menos 5 % |
| `ruptura_tesis` | El precio cruzó el nivel de invalidación registrado en la bitácora |
| `stop_loss`, `take_profit`, `caida_maximo` | Pérdida o ganancia frente al costo, o caída desde el máximo |
| `concentracion` | Una emisora pesa 45 % o más (crítica por encima del 50 %) |
| `cinco_acciones` | Faltan acciones distintas operadas en la competencia |
| `evento_corporativo`, `insider`, `noticia`, `macro`, `tradingview` | Llega información nueva relevante, verificable en su fuente |
| `deterioro_modelo` | Los pronósticos resueltos tienen más error que «sin cambio» |
| `diferencia_portal` | La cartera calculada difiere al menos 1 % del saldo capturado del portal |

## 2. Boleta de decisión (`terminal/boleta.py`)

Se genera desde la propuesta vigente, en «Pasado · Presente · Futuro → Boletas de decisión» o con `POST /api/boletas/generar`. **Se recalcula justo antes de mostrarse** (`GET /api/boletas`).

| Campo | Contenido |
|---|---|
| Emisora y serie | Clave exacta del simulador (p. ej. `AMX B`) y mercado (local/SIC) |
| Tipo | mantener · investigar · considerar compra · considerar venta; «considerar rebalanceo» si hay 2 o más cambios |
| Cantidad | Títulos **enteros**, limitados por el efectivo (con costos) o por la posición |
| Precio límite | Último precio confiable ± 0.2 %, redondeado a 0.01; orden limitada con vigencia de 1 día |
| Costos | Comisión 0.10 % + IVA 16 %; escenarios de deslizamiento de 0, 0.1 % y 0.5 %; qué pasa si la orden no se ejecuta |
| Efecto | Efectivo antes y después, peso de la emisora después, advertencias del 50 % |
| Valor esperado y rango | **Estimación histórica** (media contraída 50 % y volatilidad de 250 sesiones) a las sesiones que quedan: rango 10–90 % y pérdida plausible (percentil 5). No es un pronóstico validado |
| Liquidez | Volumen medio de 20 sesiones y fracción que representa la orden; «no verificada» si no hay volumen de la serie BMV |
| Alternativa | Mantener efectivo o no cambiar (valor esperado 0) |
| Invalidación | Movimiento de precio mayor a 1 %; dato STALE o sin precio; cambio de cartera o de reglas; caducidad |
| Caducidad | 15 min con la BMV abierta; con el mercado cerrado, 15 min después de la siguiente apertura |
| Datos faltantes y razones | Qué falta verificar y por qué se propone |

**Sin precio confiable** la boleta solo puede ser «investigar»: sin cantidad ni dirección.

## 3. Estados de la orden (referencia, `/api/pendientes-portal`)

`enviada` → `pendiente` → `ejecutada` | `cancelada` | `expirada`.

Solo una **ejecución confirmada** cambia posiciones y efectivo. Una orden no puede marcarse «ejecutada» sin la operación confirmada enlazada (`transaccion_id`).

## 4. Registro manual de la ejecución

1. El participante captura la orden en el portal.
2. Con la confirmación en mano, pulsa «Marcar ejecutada» en la boleta y escribe el **folio**, los títulos y el precio reales. La terminal registra la operación confirmada; la comisión y el IVA se calculan si no se indican.
3. Alternativa en lote: «Mi cartera → Importar → Confirmaciones del simulador», con plantilla y columnas `folio, fecha, instrumento_id, lado, cantidad, precio, comision, iva`. Enlaza boletas y órdenes por folio y rechaza duplicados y cantidades no enteras.
4. Conciliación: «Saldos del portal», que dispara una alerta si la diferencia es de 1 % o más.
