# Cierres diarios: límites temporales y cuarentena local

## Reproducción y corrección

La ingesta aceptaba barras fuera del intervalo solicitado: una respuesta solapada podía sobrescribir historia y sus marcas de procedencia; una barra de sesión todavía abierta podía guardarse como cierre. La reproducción inicial produjo seis fallos (`procedencia-antes-20261102.txt`).

`terminal/ingesta.py` limita ahora la fecha final a la última sesión cerrada del calendario existente. Acepta solo fechas ISO canónicas dentro del intervalo solicitado. Los descartes se registran como error parcial del proveedor y no se cuentan como registros incorporados. Se preservan las cotizaciones intradía existentes. No se alteraron fórmulas, estrategias, parámetros de backtest ni el calendario.

Selección final anterior a la cuarentena: 38 pruebas aprobadas, una advertencia, 44.82 s (`procedencia-regresion-final-20261102.txt`). La selección con las nuevas pruebas de cuarentena terminó con 12 aprobadas en 3.68 s. Estas pruebas usan HTTP simulado y bases temporales, sin consultas autenticadas.

## Caché real: reparación reversible

La inspección de solo lectura encontró 136 cierres de Alpaca cuya recepción precedía a su `event_time` registrado: 21 del 5-oct, 18 del 8-oct y 97 del 23-oct. Todos tenían una alternativa local del mismo instrumento/fecha recibida después de su evento. Son candidatos a barras incompletas; esta comparación no demuestra que un precio sea incorrecto ni certifica el cierre oficial de subasta.

`scripts/cuarentena_cierres.py` inspecciona por defecto. Para aplicar exige un recuento explícito, crea un respaldo con la API SQLite y verifica su integridad, sin rotar respaldos previos. La operación conserva todos los campos originales y su SHA-256 en `precios_cuarentena`, y retira solo los candidatos de `precios`. Revierte si el recuento cambia o si aparecen escrituras adicionales. No consulta cuentas ni toca órdenes.

Aplicación ejecutada: `--aplicar --esperados 136`. Respaldo: `data/respaldos/terminal-20261102-200048-615000.db`. Resultado: 136 filas archivadas y retiradas; cero candidatos restantes y cero marcas no evaluables dentro de los cinco proveedores auditados. Esto no equivale a una auditoría universal de calidad.

La comparación posterior contra el respaldo confirmó los 136 originales archivados exactamente, las otras 377,160 filas de precios idénticas y ninguna fila nueva de precios. Los recuentos de otras 62 tablas se conservaron; no se afirma igualdad de sus contenidos porque no se leyeron sus valores. Evidencias y verificador en `docs/proveedores-20261101-evidencia/cuarentena-*` y `verificar_cuarentena.py`.

Los resultados financieros históricos no se recalcularon ni se aprobaron con los datos corregidos. La cuarentena cambia el conjunto de entradas disponible; cualquier estudio que consumiera esas filas necesita su propia revalidación. No se fabricaron operaciones forward ni evidencia de ventaja.

## Límites y siguientes verificaciones

El calendario conserva una reprogramación cuando ambas capturas comparten identificador. El feed de Forex Factory genera la clave local con título, país y fecha completa. Un cambio de hora en ese feed produce otra clave. No se unen anuncios por título y país porque podrían corresponder a publicaciones distintas.

La auditoría local de solo lectura del 3 de noviembre comprobó las tres marcas en 377,160 filas de precios, 9,543 de divisas, 1,523 noticias, 754 eventos macro y 132 registros de directivos. Los 2,122 eventos corporativos anteriores tienen evento y disponibilidad, pero carecen de hora de ingreso. Esa hora histórica no se deduce del cierre asociado. Las nuevas escrituras de eventos corporativos sí registran las tres marcas.

Alpaca documenta que el timestamp de una barra indica el inicio de su intervalo; no representa el instante de cierre. El `event_time` aquí evaluado proviene de la normalización del calendario del proyecto. El filtro evita incorporar sesiones no cerradas, pero no certifica publicación final, volumen definitivo ni cierre oficial. Referencias: [barras históricas](https://docs.alpaca.markets/us/reference/stockbars) y [preguntas oficiales de datos](https://docs.alpaca.markets/us/docs/market-data-faq), consultadas el 2-nov-2026.

PERF31-06 sigue parcial: faltan normalización completa de procedencia y revisión de clientes fuera del adaptador común. `markowitz.tasa_libre` es un cliente directo identificado para revisión posterior; no se ejecutó ninguna consulta real. El servicio de grafo devolvió `Transport closed`; se leyó el alcance directamente en los archivos y pruebas indicados.

La suite completa de esta etapa registró 895 aprobadas, una advertencia de Starlette y 559.58 s en `pytest-procedencia-completo-20261102.txt`. Incluye la cuarentena y precede al ajuste HTTP 503 de Mesa. Sin operaciones, compras, mensajes, commit ni push.
