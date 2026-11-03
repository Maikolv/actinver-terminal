# Pausa persistente de proveedores — 2-nov-2026

Parte de PERF31-06 implementada en terminal/adaptadores/base.py. La reproducción inicial tuvo ocho fallos en 8.80 s: _get no interpretaba Retry-After. Tras la corrección, la selección final de adaptadores y proveedores Mesa tuvo 47 aprobadas en 17.64 s, salida 0. Incluye doce casos nuevos, con segundos/fecha HTTP, respuestas 429/503, uno o tres intentos máximos, cabeceras inválidas/no finitas/negativas, reinstanciación, cuota sin consumo durante pausa y recuperación al vencer. HTTP simulado con MockTransport y reloj fijo; cero consultas reales.

Se reutiliza ajustes_usuario y la clave proveedor_pausa:<proveedor>, con la misma forma de registro hasta que emplean los conectores Mesa. No hay tabla, servicio o dependencia nueva. Ante 429/503 con cabecera se registra la pausa y se devuelve el error sin dormir ni reintentar. La próxima consulta del mismo proveedor falla antes de consumir cuota. Una cabecera inválida deja una pausa conservadora de 60 s; una duración que desborda datetime difiere hasta su límite representable. Sin cabecera se conserva el backoff previo y el conteo de cada intento. No se guardan URL, cabecera, cuerpo o credenciales en la pausa.

Referencia oficial: RFC 9110, sección 10.2.3, permite fecha HTTP o segundos de demora: https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3 (consultada 2-nov-2026). Implementación propia; sin copiar código del RFC o de otros repositorios.

Alcance: adaptadores que usan _get. ConsultaMesa conserva su camino específico ya probado. No se afirma que todos los clientes HTTP externos al adaptador común compartan esta espera. La normalización completa de tiempos de procedencia de PERF31-06 sigue pendiente, al igual que PERF31-04 y PERF31-05. No demuestra ahorro medido, frescura ni ventaja financiera.

La suite completa anterior a esta corrección terminó con 866 aprobadas y una advertencia en 708.24 s. Ese resultado no incluye los doce casos nuevos ni valida por sí solo este cambio. Evidencias: retry-after-antes-20261102.txt, retry-after-despues-20261102.txt (43), retry-after-despues-final-20261102.txt (47). codebase-memory list_projects y cobertura devolvieron Transport closed; fallback directo en base.py, proveedores_mesa.py, db.py y sus pruebas. No se modificó el esquema de db.py. Sin motor, .env, red real, mensajes u operaciones.

## Suite posterior terminada

retry-after-conjunto-20261102.txt terminó con salida 0: 878 aprobadas, cero fallidas, una advertencia de dependencia, 684.36 s (11:24). Incluye los doce casos nuevos y la regresión completa después del cambio de base.py. No cierra los pendientes de procedencia, arranque/memoria o fuentes externas.

## Extensión a Mesa: HTTP 503

Con HTTP simulado, antes del ajuste dos instancias de Alpha Calendario hicieron dos peticiones separadas por 61 segundos pese a recibir `Retry-After: 120` y no persistieron una pausa. `ConsultaMesa` ahora aplica a un 503 con cabecera la misma espera persistente que aplica a un 429. Conserva el identificador compartido `alpha_vantage` y la política de una sola solicitud por intento. Un 503 sin cabecera conserva el tratamiento previo.

Las pruebas comprueban ambos códigos con segundos y fecha HTTP, nueva instancia, cuota intacta durante la pausa y recuperación al vencer. Selección `test_proveedores_mesa.py` y `test_adaptadores_retry_after.py`: 41 aprobadas en 15.93 s, salida 0. Logs `mesa-503-antes-20261102.txt` y `mesa-503-despues-20261102.txt`. La suite de 895 aprobadas de la cuarentena precede a este cambio. Sin red real ni costos. Quedan otros clientes directos por revisar; este resultado no cierra todo PERF31-06.
