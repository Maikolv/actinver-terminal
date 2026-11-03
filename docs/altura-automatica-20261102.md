# Altura automática conservada — 2-nov-2026

Decisión humana explícita: mantener la altura automática actual de Mesa. No se recuperó el control manual ni se revirtió su código de producción. Se retiró la prueba antigua que importaba normalizarAltos, función ausente en la versión actual; las pruebas de ajuste automático de estetica.test.mjs permanecen.

Node completo: 51 aprobadas, cero fallidas, 2336.1163 ms, salida 0. Se conserva la corrida anterior con 47 aprobadas y un módulo fallido. Logs politica-gratuita-node-20261102.txt y politica-gratuita-node-final-20261102.txt. La diferencia de conteo se explica por retirar el caso manual y por que el módulo fallido antes no ejecutaba sus otros cuatro casos.

La prueba de navegador mesa-disposiciones.cjs se adaptó para comprobar crecimiento automático a 1100 px, límite de 2000 px, ausencia de slider manual, conservación del mismo marco al cambiar disposición y destrucción al cerrar. Usa contenido simulado, no proveedores. Su ejecución todavía está pendiente; no se atribuyen a esta versión las capturas antiguas del control manual.

Esta decisión sustituye el alcance manual de TP01-04. Los documentos del 1-nov se conservan como historia, no como estado vigente.

Verificación posterior: el navegador pasó a 390 y 1440 px, sin errores JS, con contenido simulado. Se corrigió un defecto real de actualización del ancho al reutilizar paneles entre disposiciones guardadas, sin modificar el cálculo de altura. El cierre espera el evento asíncrono toggle antes de comprobar que el marco fue destruido. Evidencia: proveedores-20261101-evidencia/mesa-altura-automatica-ui-20261102.json.
