# Política vigente: solo recursos gratuitos — 2-nov-2026

Directriz humana de esta fecha: utilizar solo proveedores gratuitos e informar inmediatamente si un recurso, API, clave o complemento exige facturación. Una clave disponible no autoriza gasto, alta de un plan, prueba con renovación ni compra de datos. La ausencia de una condición de precio verificable no equivale a gratuidad.

## Aplicación local

- `app.solo_proveedores_gratuitos = true` en configuración predeterminada y local.
- Los conectores actuales de Twelve Data (solo BMV) y Barchart (contrato) se deshabilitan también al construir los adaptadores, aunque una configuración antigua los marque activos y haya claves.
- La API de Claude se bloquea bajo esta política incluso ante una aprobación de costo anterior. Se conservan respuestas locales y Ollama ya configurado; no se instala ni contrata ningún servicio.
- Ningún cambio de una opción local constituye permiso humano para pagar. No iniciar estrategias, brokers, órdenes o notificaciones externas.
- Si un proveedor gratuito alcanza su cuota, se conserva SIN DATO o el dato anterior con su etiqueta/fecha; nunca se compra capacidad ni se sustituye silenciosamente un dato fresco por uno viejo.

## Twelve Data: importación y condiciones comprobadas

La clave proporcionada por el usuario se importó únicamente al mecanismo `.env` local, ignorado y no rastreado por Git. Su valor no aparece en este documento, frontend ni resultados del diagnóstico. No se creó una copia de respaldo con secretos.

Una solicitud a `/api_usage`, autenticada mediante cabecera, respondió HTTP 200 y validó la clave. El resultado informó límite de ocho créditos por minuto, uso actual uno y uso diario uno; el nombre exacto del plan no se identificó en el resumen seguro. No se deduce la contratación de un plan a partir de esos límites. Esta consulta no solicitó cotizaciones ni acceso BMV y no activó suscripciones. La documentación atribuye un crédito API a esta consulta.

El plan Basic publicado cuesta USD 0, con ocho créditos por minuto y 800 diarios. La cobertura oficial de XMEX/BMV exige Pro o superior y es EOD: queda fuera del mandato gratuito. No se ejecutó la consulta BMV antigua pendiente; su autorización nunca obliga a usar un recurso de pago.

Fuentes oficiales consultadas el 2-nov-2026: [planes](https://twelvedata.com/pricing), [BMV/XMEX](https://twelvedata.com/exchanges/XMEX), [control de créditos](https://support.twelvedata.com/en/articles/5713553-control-over-api-usage) y [autenticación por cabecera](https://twelvedata.com/docs).

Evidencia sanitizada: `proveedores-20261101-evidencia/twelve-importacion-uso-20261102.json`. La clave deja de ser un pendiente de configuración; la cobertura BMV de Twelve pasa a estar excluida por pago, no aprobada ni implementada como fuente gratuita. Las evidencias anteriores de ausencia de clave se conservan como historia.

La suscripción de ChatGPT/Claude de escritorio no acredita créditos gratuitos de sus APIs. No se hicieron compras, cambios de cuenta, reinicios del motor ni operaciones.

## Ampliación de controles y verificación general en seguimiento

El diagnóstico CLI de Claude también se bloquea antes de consultar la API. El panel de costos muestra Claude API, Twelve BMV y Barchart como bloqueados, oculta aprobación y conserva decisiones antiguas sin habilitar gasto. Quince pruebas específicas de política/CLI/costos/bot aprobaron en 31.64 s, salida 0, una advertencia. No se suman a las selecciones anteriores como casos distintos.

La primera suite general fue interrumpida expresamente para corregir la vía CLI; log politica-gratuita-conjunto-interrumpido-20261102.txt. La repetición sigue activa en politica-gratuita-conjunto-20261102.txt: último avance observado 75 %, cuatro fallas aún sin resumen final. No se declara aprobada ni se reinicia por ausencia de salida. Node: 47 aprobados y un módulo fallido por normalizarAltos ausente en la Mesa actual; worker: 19 aprobados, salida 0, 1117.3791 ms. Se solicitó aclarar si conservar la altura automática o recuperar ajuste manual; no se revirtió código de otra sesión.

Dos revisiones visuales aisladas de costos agotaron el tiempo de captura (elemento/página). Las aserciones del primer caso habían comprobado tres servicios bloqueados y ningún botón de aprobación, pero no equivalen a cuatro recorridos completos. Un intento posterior de iniciar una tarea auxiliar devolvió Windows os error 1450, recursos insuficientes al leer metadatos de python_dateutil en uv; no se reinstaló ni modificó el entorno. Se suspendió lanzar procesos nuevos mientras termina la suite existente. Sin solicitudes de pago, claves en informes, reinicio de instancia habitual, notificaciones ni operaciones.

## Verificación adicional del 2-nov

La corrida completa anterior terminó: 860 aprobadas, 4 fallidas y una advertencia en 2976.71 s. No se presenta como aprobada. Se corrigieron la selección mensual del respaldo FRED y el cálculo interanual exacto de CPI, así como la entrega del CSRF de Mesa sin caché. La repetición específica de macro, Mesa y OCR terminó con 27 aprobadas y una advertencia en 73.94 s. La prueba OCR reforzada para comparar el estado de capturas antes y después terminó con una aprobada y una advertencia en 65.87 s; el fallo anterior de OCR no se reprodujo, sin atribuirle una causa no demostrada.

El usuario eligió conservar la altura automática. La prueba real de navegador detectó y permitió corregir la actualización del ancho al reutilizar un panel entre disposiciones guardadas. La regresión pasó en 390 y 1440 px: altura automática, límite de 2000 px, reutilización del marco, destrucción al cerrar y cero errores JS. Proveedores simulados, solo interfaz. Evidencia: mesa-altura-automatica-ui-20261102.json.

La revisión de costos pasó sus cuatro combinaciones móvil/escritorio y claro/oscuro: tres servicios de pago bloqueados y ningún botón de aprobar. Capturas y resultado en politica-gratuita-ui-20261102. Los otros endpoints se simularon sin datos: esta revisión no acredita disponibilidad de proveedores.

Se inició una nueva corrida completa después de las correcciones, con entorno sin motor, sin .env y sin configuración local. Resultado aún pendiente; log politica-gratuita-conjunto-final-20261102.txt. No se iniciaron operaciones, estrategias ni notificaciones.

## Resultado completo observado — 2-nov-2026

La corrida politica-gratuita-conjunto-final-20261102.txt terminó con salida 0: 866 aprobadas, cero fallidas, una advertencia de deprecación de Starlette/AnyIO, 708.24 s (11:48). Confirma las correcciones macro/CSRF/OCR y política gratuita del código de esa corrida. La prueba posterior de Retry-After todavía no existía al recolectar esa suite; no se incluye en sus 866 casos y cualquier corrección posterior requiere verificación nueva.
