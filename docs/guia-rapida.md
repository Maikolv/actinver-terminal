# Guía rápida: qué está confirmado y qué falta hacer

La terminal **solo informa y simula**. Nunca compra ni vende: cada orden la capturas tú, a mano, en el simulador del Reto. Tampoco entra al portal del Reto, porque el reglamento (§17) prohíbe robots y programas ahí.

## Dónde mirar primero

En **Resumen**, la tabla **«¿En qué puedo confiar hoy?»** muestra cada tema con una etiqueta:

| Etiqueta | Qué significa |
|---|---|
| **Confirmado** | Lo copiaste del portal del Reto o viene de una fuente oficial vigente (por ejemplo, el tipo de cambio de Banxico). |
| **Estimado** | Lo calculó la terminal con **cierres diarios**: valuaciones, propuestas y plan de órdenes. Puede diferir del portal. |
| **Vencido** | El dato existe, pero ya no está al día. |
| **Falta** | No hay dato. La columna «Qué falta hacer» dice la acción concreta. |

La terminal **no tiene precios en tiempo real**. Los de la BMV son cierres del día anterior. Los del SIC son el precio de la bolsa de origen convertido a pesos: una referencia, no la cotización del SIC.

## Tu saldo: cuenta del Reto o registro local

- **Registro local.** Lo que capturas a mano en la terminal, como la aportación virtual de $1,000,000 de la semana de práctica. **No** es un saldo confirmado.
- **Cuenta del Reto.** Lo que copias del portal y pegas en **Mi cartera → Capturar desde el portal**. En cuanto guardas una captura válida, las propuestas y las alertas usan tu cuenta del Reto.

Para capturar:
1. En el portal, selecciona tu tabla de posiciones **con sus encabezados**, además de las líneas de efectivo y valor del portafolio.
2. Copia con Ctrl+C.
3. En la terminal, pega con Ctrl+V, escribe la hora que muestra el portal y pulsa **Vista previa**.
4. Si no hay errores, pulsa **Guardar captura**. La terminal rechaza las capturas que no cuadran, las que tienen emisoras desconocidas, las que tienen hora futura o anterior a la última, y las duplicadas.

La captura deja de usarse cuando cambia la etapa del Reto (de práctica a competencia) o cuando registras una operación a mano después. En ese caso, pega una captura nueva.

## Alertas que recibes (Telegram y escritorio)

- **Plan del día**, a las 7:00 en días hábiles: órdenes con títulos, cambios frente a ayer y el porqué.
- **Cambio en tu cuenta del Reto**: después de cada captura que traiga cambios.
- **Actualiza la captura**: cuando la BMV cerró y no has capturado tu cuenta del día.
- **Posible movimiento**: cuando la mejor propuesta pide órdenes distintas. De noche no te despierta; va incluida en el plan de la mañana.

Cada aviso trae la hora, la fuente y el motivo. No se repite, y si un canal falla se reintenta cada 10 minutos. El correo se activa cuando agregues sus datos en `.env` (ver README).

## Cuándo la terminal bloquea una decisión

- Una **propuesta con avisos** (datos atrasados, perfil cambiado o captura con posiciones sin precio) no genera boletas ni avisos de movimiento.
- Una **boleta del SIC** sale como «investigar», sin cantidad: toma el precio del portal para calcular los títulos.
- Una propuesta que **no cumple tu perfil** (por ejemplo, demasiado en dólares) lo dice en «Riesgos» como «NO CUMPLE SU PERFIL».
- **Validación corta**: si la propuesta se validó con menos de medio año de datos, «Riesgos» lo advierte porque la puntuación es poco confiable.
