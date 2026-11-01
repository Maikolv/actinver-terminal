# Lucid Flex 50K — candidata realista, no estrategia ganadora probada

La decisión actual es investigar y practicar. Ninguna estrategia del equipo tiene ventaja demostrada. No existe un «mejor» sistema verificable con cinco sesiones de OHLC y unos segundos de agresor. No operar sigue siendo la referencia.

## Candidata B-RTH-50K

Evaluar únicamente aceptación y retesteo del valor previo, utilizando el motor B existente. Empezar con MES, 1 micro; MNQ se evalúa aparte después, nunca ES/NQ simultáneos. Ventana propuesta 09:35–11:30 Nueva York, máximo dos intentos diarios. Son reglas nuevas propuestas, no ajustes ya activados en Quantower. Parámetros B conservados del motor, sin búsqueda adicional; config/preregistro_B_RTH_50k_20261020.json registra los valores.

1. Antes de abrir, obtener VAH/VAL de una sesión previa completa, contrastar TPO observado frente a perfil real y no usar referencias parciales. El contexto OHLC actual no es perfil de volumen por precio.
2. Esperar cierres consecutivos fuera del valor y retesteo según B; exigir volumen relativo y delta favorable medidos de agresores reales. Si faltan, no evaluar, sin fabricar delta con el color de la vela.
3. Entrada en el evento siguiente, nunca en el cierre retrospectivo. Stop tras el extremo del retesteo más el buffer B; objetivo y salida temporal B del preregistro. Costes y slippage incluidos.
4. Riesgo propuesto máximo USD50 incluyendo costes; además, máximo 5% de la distancia disponible al MLL después de reservar USD200. El menor manda. Si un micro supera el presupuesto, omitir la operación. No aumentar contratos para alcanzar un objetivo diario.
5. Pérdida interna diaria USD100, máximo dos intentos y una exposición; nunca ampliar stop, martingala ni promediar pérdidas. Son límites de investigación propios, no reglas oficiales universales.
6. Evitar ventanas de eventos macro predefinidas. Cerrar dentro de la ventana de estudio; el aplanado de emergencia y cierres anticipados del motor siguen siendo obligatorios. No esperar al límite de Lucid.

Ejemplo ilustrativo: MES stop 8 puntos = USD40 brutos; con USD1.50 ida/vuelta y 2 ticks de deslizamiento por lado, presupuesto USD46.50. MNQ stop 25 puntos ya consume USD50 antes de costes: no cabe. Tarifas de ejemplo, no comisión real confirmada. Los USD50 son presupuesto de riesgo, no pérdida máxima garantizada: gaps, slippage o fallos pueden superarlo.

## Reglas oficiales verificadas

La página oficial de drawdown publica para 50K MLL USD2,000, Initial Trail Balance USD52,100 y Locked MLL USD50,100. Es EOD trailing; no tratar USD50,000 nominales como capital que se puede perder. La consistencia de evaluación estándar es 40%, o 50% con el add-on; no confundir con la fondeada. La automatización está permitida con responsabilidad del trader y sin incumplir las demás reglas. Cuenta aún no comprada: condiciones contratadas pendientes.

Fuentes consultadas 20/oct/2026:
- https://support.lucidtrading.com/en/articles/12945815-lucidflex-drawdown
- https://support.lucidtrading.com/en/articles/12945805-lucidflex-consistency-percentage
- https://support.lucidtrading.com/en/articles/11404728-other-trading-activities
- https://support.lucidtrading.com/en/articles/12945790-lucidflex-evaluation-account

## Qué pruebas existen y qué no demuestran

Base local anterior: 88 pruebas Python, 167 comprobaciones C#, dos builds correctos. Telegram desde Quantower aceptado. Historial dxFeed NQ diciembre: 6,901 barras y cinco sesiones RTH completas; agresor en muestra de 12 segundos, no historial de delta. No copiar NQ como MNQ ni afirmar fills de micro a partir del mini.

No hay cuenta Lucid comprada ni demo forward, diario real o prueba completa de brackets/OCO del conector. El selector de la plataforma ha impedido completar la selección con automatización. No se sustituye esa prueba por tests sintéticos. La revisión actual registra el estado real en entregables/reels-20261020/validacion.json.

## Criterio de paso

Primero completar con 1 micro en Simulator: ACK, fill parcial, rechazo, stop/target/OCO, stop ausente, desconexión/reconexión, reinicio con posición, cierre temporal, comisión neta y persistencia. Después, datos actuales para mínimo 20 sesiones y 30 trades, cero incidentes, caída menor al 50% del MLL, según protocolo_fases.json. Ni siquiera eso garantiza rentabilidad: exigir muestra fuera de desarrollo, sensibilidad a costes, bootstrap por sesiones y comparación con no operar; si la incertidumbre incluye ausencia de ventaja, rechazar la implementación real. No acelerar esas semanas con replay histórico.

No activar fondeada sin cuenta verificada, evidencia suficiente y autorización posterior explícita. Mantener PAPER, adaptador/live/fondeada false.
