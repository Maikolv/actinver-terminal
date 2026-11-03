# Avance de los pendientes gratuitos — 1-nov-2026

Objetivo activo: completar los pendientes de proveedores que no necesiten facturación.
**No es un cierre del objetivo.** No se confunden pruebas simuladas con validación externa.
Continúan las restricciones de no operar, no contratar y no crear cuentas. El usuario autorizó exclusivamente el cargador habitual de claves en memoria para ocho consultas gratuitas; no se muestran ni se copian valores de `.env`. Las ocho consultas ya se consumieron.

## Completado con fuentes reales

### Publicaciones SEC: cuatro emisoras actuales

Se reutilizó ClienteSEC y se validó cada submissions contra símbolo y CIK. Para identificar
el programa se usó el contacto Git ya configurado localmente, solo en memoria y cabecera:
no se imprimió ni se guardó ese contacto; no se inventó dirección ni se leyó `.env`.

| Símbolo | CIK actual comprobado | Publicaciones 8-K Item 2.02 guardadas |
|---|---:|---:|
| MU | 723125 | 36 |
| NVDA | 1045810 | 25 |
| AMD | 2488 | 37 |
| XOM | **2115436** | 2 |
| Total | | **100** |

El primer intento de XOM al CIK histórico 34088 recibió HTTP 200 pero se rechazó:
no confirmó la identidad actual. Se consultó el catálogo oficial
https://www.sec.gov/files/company_tickers.json y se confirmó **ExxonMobil Holdings Corp**,
CIK 2115436; se repitió únicamente XOM con ese identificador. No se mezcló el emisor
histórico con el holding actual ni se borró el intento rechazado.

Coste: sin cuenta, sin clave API, sin contratación. **Seis GET a SEC:** cuatro submissions
iniciales, un catálogo y un submissions de XOM actual. Se respetaron los cupos locales y
no hubo reintentos automáticos. Los conectores automáticos siguen apagados.

Los 100 registros tienen aceptación EDGAR, enlace y conocimiento desde esta descarga.
**No prueban hora del anuncio ni aportan por sí solos BPA realizado/revisado.** Esos campos
permanecen SIN DATO y no se calcula reacción usando aceptación como sustituto del anuncio.

Evidencia primaria saneada:
- `proveedores-20261101-evidencia/gratis-sec-20261101.json`;
- `proveedores-20261101-evidencia/sec-catalogo-20261101.json`;
- `proveedores-20261101-evidencia/gratis-sec-xom-20261101.json`.

### Treasury 30 años: fuente original H.15 sin clave

La Federal Reserve Board publica oficialmente el XML de H.15 y el cruce DDP–FRED:

- https://www.federalreserve.gov/releases/h15/ (enlace XML);
- https://www.federalreserve.gov/releases/h15/data/FRB_h15_xml.zip;
- https://www.federalreserve.gov/data/data-download-fred-information.htm;
- https://www.federalreserve.gov/data/documents/DDP-FRED%20Data%20Series%20Crosswalk.csv.

El cruce descargado confirma **DGS30 ↔ H15 / RIFLGFCY30_N.B**. El XML confirma Treasury
nominal, plazo Y30, frecuencia 9, unidad Percent:_Per_Year y multiplicador 1. Se importaron
**24 observaciones**, del **25-sep al 29-oct-2026**, conocidas desde **1-nov-2026
11:18:41 UTC**. El valor final es 5,32 %, publicación histórica; no cotización vigente.

Dos HEAD comprobaron tamaños y dos GET descargaron 6.062.543 bytes en total. No hubo
cuenta, token, extracción de datos de HTML ni uso del endpoint público no documentado
fredgraph.csv. Se consumió la publicación XML enlazada por su editor, con tamaño acotado,
lectura del ZIP sin extracción a disco, identidad/unidad/plazo/frecuencia comprobados,
fechas futuras y no finitos excluidos y hashes de ambos recursos.

Fuente guardada: **fed_h15**, origen **manual** por importación puntual de publicación,
con URL primaria y huella. No se etiqueta como respuesta de la API de FRED. Mesa usa esta
observación cuando FRED no tiene DGS30 o su periodo es anterior; no sustituye un periodo
más reciente por otro más viejo. Título y fuente indican XML H.15. No cambian precios,
FX, ponderaciones, modelos, estrategias o ejecución.

Evidencia: `fed-h15-descarga-20261101.json` y `h15-importacion-real-20261101.json` en la
carpeta de evidencia. Descargas originales en `data/verificacion-gratuita-20261101/`.
Posteriormente se comprobó la API autenticada de FRED mediante un GET HTTP 200: 23 observaciones válidas de DGS30 guardadas como fred_macro. La importación H.15 conserva su identidad y procedencia independientes.

## Consulta autorizada y pendientes reales

Evidencia: `proveedores-20261101-evidencia/gratis-verificacion-autorizada-20261101.json`
(siete consultas) y `sie-sp1-catalogo-20261101.json` (octava consulta).
Solo se usó el cargador habitual en memoria. No se activaron conectores automáticos.

| ID | Resultado real | Pendiente |
|---|---|---|
| F1 | Alpha EARNINGS_CALENDAR HTTP 200, tres estimaciones guardadas (AMD, NVDA y MU); SEC conserva 100 publicaciones | BPA reportado aún no consultado. Las revisiones solo pueden conocerse desde capturas sucesivas; no se inventa historia. Sin hora verificable no se calcula reacción |
| F2 | API FRED DGS30 HTTP 200, 23 observaciones guardadas; H.15 conserva 24 observaciones independientes | Sin bloqueo de acceso acreditado para esta consulta puntual; no equivale a servicio continuo |
| F3 | SF61745: catálogo y datos HTTP 200, título Tasa objetivo, 24 observaciones guardadas | Actualización automática permanece apagada |
| F4 | SP1 confirmado en catálogo: título legado IPC Por objeto del gasto / Nacional / Índice General, periodicidad Mensual, cifra Indices | El primer validador rechazó correctamente un título no reconocido antes de descargar datos. Se corrigió con identidad SP1, periodicidad y tipo de cifra; descarga pendiente de nueva autorización de consultas |
| F6 | SF30057: catálogo y datos HTTP 200, 21 observaciones guardadas | Es rendimiento promedio **mensual**, no diario ni vigente. Etiqueta mensual corregida en código; no confundir código actualizado con proceso antiguo recargado |
| F5 | XMEX general requiere Pro+/Venture+ según ficha oficial | Fuera del objetivo gratuito; no se activa ni compra |

Se preparó un lector manual EARNINGS y un registro conservador del BPA original y
revisiones observadas, sin importar estimaciones históricas revisadas como si hubieran
sido conocidas antes del anuncio. Está probado con HTTP simulado; **todavía no verificado
con respuesta real de EARNINGS**. No se presenta como implementación validada en producción.

Se solicitó ampliar el alcance en hasta seis consultas gratuitas: dos SP1 y una EARNINGS
por cada MU, NVDA, AMD y XOM. No se ejecutarán sin respuesta autorizante. No se repiten
consultas ya comprobadas ni se reinician cuotas para forzar acceso.

## Verificación y revisión visual

- 86 pruebas específicas aprobadas, una advertencia Starlette, **38,55 s**, con DNS y
  conexiones externas bloqueadas. Log `gratis-pytest-20261101.txt`.
- Node: **43 aprobadas**, sin fallas/omisiones, **2317,6133 ms**; log `gratis-node-20261101.txt`.
- Chromium aislado: 1440 y 390 px, claro/oscuro, cuatro casos sin errores JS ni
  desbordamiento de página. Capturas anteriores a la tanda autenticada: base de revisión con solo las **124 publicaciones reales**;
  sin cartera, cotizaciones o credenciales. Se comprobó DGS30 de fuente fed_h15 y 100
  publicaciones SEC con los tres BPA y reacción ausentes rotulados SIN DATO.
- Capturas generales y detalles de Macro/SEC en `proveedores-20261101-evidencia/gratis-ui/`.
  Bloquear terceros en el navegador prueba interfaz; la disponibilidad de fuentes se
  comprobó separadamente con los GET reales arriba.
- Servidor de revisión exclusivamente en 127.0.0.1:8796 con TERMINAL_SIN_MOTOR=1,
  TERMINAL_SIN_ENV=1 y conexiones externas bloqueadas; sin modificar el servidor abierto. El servidor de revisión ya se detuvo.
- Suite completa con bloqueo de red: **815 aprobadas, una advertencia, 903,15 s**; log `gratis-pytest-completa-20261101.txt`. Este resultado precede los últimos cambios de SP1/BPA/calendario.
- Cambios posteriores de SP1/BPA/calendario: **53 aprobadas, una advertencia, 54,05 s**, log `gratis-fase2-pytest-20261101.txt`; no equivale a repetir toda la suite después de esos cambios.

Se conservan los cambios de la otra sesión. No se hicieron commit, push, trades, mensajes
Telegram, órdenes, arranques de estrategia ni consultas a la cuenta Actinver.

## Continuación de verificación offline

- Últimos validadores SP1/BPA y verificador manual: **18 aprobadas, 8,14 s**.
- JavaScript después del ajuste del calendario: **43 aprobadas, 0 fallas, 2943,5191 ms**.
- Worker de alertas, únicamente pruebas simuladas: **19 aprobadas, 0 fallas, 2861,8973 ms**.
- La nueva suite completa se inició con conexiones externas bloqueadas y se interrumpió
  por presión de memoria: Windows llegó a informar **27.980 KiB libres**. Se comprobaron
  los comandos de los únicos dos procesos detenidos (30832 y 26636), ambos de esta
  ejecución de `pruebas_sin_red.py tests -q`. La sesión terminó con código 1 por esa
  interrupción; no produjo un resumen de pytest. Log parcial:
  `gratis-pytest-final-fase2-20261101.txt`. **No es una suite aprobada ni una falla de
  aserción identificada.** Queda pendiente completar la suite después de los últimos
  cambios en condiciones con recursos suficientes; el resultado previo de 815 conserva
  su alcance anterior.
- Se preparó una base aislada con 323 observaciones públicas reales, sin copiar cartera,
  precios o credenciales. El primer arranque de revisión falló al importar
  `sklearn._loss.loss`; la comprobación independiente posterior de esa misma importación
  fue correcta, sin reinstalar dependencias. La navegación falló por conexión rechazada,
  por lo que **no existen todavía capturas válidas de esta revisión posterior**.
  En ese corte Windows informó 56.556 KiB de memoria física libre sobre 6.174.988 KiB.
  Esa coincidencia no demuestra la causa del error. No se detuvieron servidores ajenos.

El alcance adicional de consultas sigue pendiente de respuesta humana. Las pruebas
offline y los datos ya descargados no amplían el límite autorizado de ocho solicitudes.

### Segundo intento de revisión aislada

Después de detener únicamente la suite propia, Windows todavía informó 42.248 KiB
libres. El segundo arranque de la misma revisión aislada también terminó con código 1,
esta vez al importar `Extension` desde `websockets.extensions`. No se logró abrir el
puerto de revisión ni se obtuvo una captura válida posterior. No se reinstalaron paquetes,
no se desactivaron protocolos para encubrir el fallo y no se modificaron procesos ajenos.
La causa de ambos errores de importación sigue sin confirmar: la presión de memoria es
un hecho medido, no un diagnóstico probado. Esta revisión requiere recursos disponibles
y comprobar la integridad del entorno antes de repetir el arranque.

Para cerrar este objetivo faltan la ampliación humana del límite de consultas y la
verificación final completa/visual en un entorno que permita ejecutarlas. Ningún
pendiente se convierte en aprobado por estar implementado o tener una prueba parcial.

## Ampliación autorizada y completada: seis consultas adicionales

El usuario autorizó expresamente las seis consultas y el mismo cargador interno.
Se ejecutaron exactamente seis GET entre las 12:55 y 12:58 CDMX del 1-nov-2026:
catálogo SP1, datos SP1 y un EARNINGS por MU/NVDA/AMD/XOM. Todas respondieron HTTP 200.
No hubo reintentos, redirecciones ni activaciones. Evidencia saneada:
`proveedores-20261101-evidencia/gratis-seis-adicionales-20261101.json`.

Se guardaron 24 observaciones INPC y 32 BPA, ocho por emisora. El conocimiento empieza
al terminar cada descarga, nunca en la fecha histórica. EARNINGS no informó moneda ni
base contable: se conserva esa ausencia y no se calcula sorpresa. La ventana declarada
pre/post-market se muestra con su fuente, sin convertirla en hora exacta. La reacción y
las revisiones no observadas continúan SIN DATO.

El bloqueo anterior de autorización ya quedó resuelto para esas seis consultas. No es
permiso para otras llamadas ni para activar conectores. La revisión de código utilizó
codebase-memory cuando volvió a estar disponible: índice del 24-sep, rutas nuevas sin
seguimiento y web/static excluido. Por ello se verificaron directamente los archivos
actuales; ese índice no acredita cobertura completa.

Pruebas de esta tanda: 53 específicas aprobadas en 33,62 s antes del rótulo de ventana;
después de añadirlo, 7 pruebas BPA aprobadas en 2,39 s y 43 Node en 763,3265 ms.
La revisión aislada usa 379 observaciones públicas, sin copiar precios, cartera o claves.
El servidor de revisión volvió a arrancar en 127.0.0.1:8796; las capturas y la suite
completa siguen sujetas a su resultado final, sin heredar aprobación del intento fallido.

### Resultado visual posterior a las seis consultas

Recorrido final aprobado: 1440 y 390 px, claro y oscuro, cuatro casos sin errores
JavaScript ni desbordamiento horizontal de página. API de la copia aislada: 135 filas
de calendario (100 publicaciones SEC, tres estimaciones y 32 BPA), reacción SIN DATO
y ninguna revisión inventada. Macro confirmó DGS30 de FRED, bono mensual e INPC.
Capturas y resultado: `proveedores-20261101-evidencia/gratis-ui-fase3/resultado.json`.
Se inspeccionaron directamente la tabla macro oscura y la ficha BPA móvil clara.
Los archivos con sufijo `-sec.png` en esta última carpeta muestran una ficha BPA,
por reutilización del nombre de la prueba anterior; no son evidencia de hora SEC.

La primera captura de esta tanda falló por un selector antiguo de H.15 en la prueba;
se corrigió el selector al título FRED y se repitieron los cuatro casos. No fue una
falla del dato ni se omitió el recorrido fallido. El servidor aislado se detuvo tras
verificar su PID y comando; no se tocó ningún servidor del usuario.

Nueva suite completa con red bloqueada: `gratis-pytest-tras-seis-20261101.txt`.
Se limitaron a un hilo BLAS/OpenMP/MKL para reducir concurrencia; no se cambiaron
datos, ventanas, parámetros de modelos ni aserciones para obtener un resultado.
Hasta su terminación no se considera aprobada. La autorización externa adicional
quedó consumida (6/6); no se requieren nuevas llamadas para verificar lo ya guardado.

## Variación diaria por ventana declarada y auditoría del alcance

El contrato original define `momento` como antes de apertura/después de cierre, no como
un timestamp exacto. El campo oficial EARNINGS.reportTime permite esa ventana cuando
proviene de una observación API validada. Se reutiliza reaccion_resultados() sobre dos
cierres consecutivos reales de calendario XNYS: base previa para pre-market y base del
mismo día para post-market. Se requiere referencia USD, misma fuente, ambos cierres
positivos/finito y conocidos al corte, sesión final ya cerrada y cotización no futura.
No se usan datos sintéticos/retrasados ni un cierre posterior para rellenar uno faltante.

La presentación dice «Variación histórica entre cierres», conserva hora exacta SIN DATO
y advierte que no aísla splits, dividendos ni efecto causal. No se cambia el estimador
ni se infiere un trade. La aceptación SEC tampoco sustituye la hora del anuncio.
Se pudieron calcular **32 variaciones** con precios públicos ya guardados, sin nueva
consulta externa ni escritura de precios. Evidencia:
`proveedores-20261101-evidencia/variacion-diaria-auditoria-20261101.json`.

- Suite anterior a esta extensión: **824 aprobadas, una advertencia, 563,91 s**;
  `gratis-pytest-tras-seis-20261101.txt`. Se confirmó sesión terminal con código 0.
- Nuevas pruebas y regresión de calendario: inicialmente 13 fallos por duplicar el
  instrumento MU ya sembrado en la base de prueba; se corrigió el montaje, sin relajar
  aserciones. Después **55 aprobadas, una advertencia, 23,98 s**. Se añadió después una
  comprobación explícita de procedencia API de la ventana; queda cubierta por la suite
  final posterior, no se atribuye retroactivamente al resultado anterior.
- Node **43 aprobadas, 2260,8265 ms**, y worker **19 aprobadas, 1574,9895 ms**;
  logs `gratis-node-variacion-20261101.txt` y `gratis-worker-20261101.txt`.
- Chromium: cuatro casos 1440/390 px claro/oscuro, sin errores JS ni desbordamiento;
  135 filas de calendario y 32 variaciones. Base aislada con 379 observaciones y solo
  64 cierres públicos históricos; sin cartera ni claves. Capturas:
  `gratis-ui-fase4/resultado.json` y `390-light-sec.png` (la ficha mostrada es de BPA).
  Se inspeccionó directamente esa ficha. El servidor propio ya se detuvo.
- Conectores automáticos Banxico/SEC/Alpha confirmados **false** mediante configuración
  habitual con SIN_ENV=1; evidencia `candados-conectores-20261101.json`.
- estado_demo.py de futuros-lab: adaptador/live/fondeada false, sin diario real,
  incidentes no auditados y sin ventaja demostrada. No se iniciaron operaciones.
- Suite completa posterior en ejecución: `gratis-pytest-variacion-20261101.txt`;
  no se da por aprobada hasta su resumen terminal.

Matriz de cierre del alcance de proveedores (no de los otros pendientes de interfaz):

| Requisito | Evidencia actual | Límite conservado |
|---|---|---|
| F2 DGS30 | API FRED + respaldo oficial H.15 + pruebas + macro visual | Publicación histórica, no precio actual |
| F3 objetivo | SF61745 confirmado por catálogo/datos y almacenado | Conector automático apagado |
| F4 INPC | SP1 confirmado de nuevo y 24 índices mensuales guardados | Nivel del índice, no variación interanual inferida |
| F6 bono M10 | SF30057 confirmado y 21 promedios mensuales guardados | No curva diaria ni rendimiento actual |
| F1 publicación | SEC 100 documentos, cuatro identidades actuales | Aceptación EDGAR, no hora exacta del anuncio |
| F1 estimación/BPA/revisión | Tres previsiones, 32 BPA, versiones al corte y registro de revisiones observadas probado | Moneda/base no informadas; no se inventan revisiones ni consenso histórico |
| F1 variación diaria | Ventana API y pares consecutivos USD de una fuente; 32 cálculos | Descriptiva, no causal; hora exacta sigue SIN DATO |
| F5 BMV general | Ficha XMEX exige Pro+/Venture+; Basic no acredita mercado general | Cobertura de pago fuera del objetivo gratuito; prueba de símbolo no equivale a permiso general |

No se reinició la instancia habitual ni se alteró el trabajo de otra sesión. La prueba
visual acredita una instancia nueva aislada; la instancia habitual puede conservar módulos
Python anteriores hasta su reinicio seguro con SIN_MOTOR=1. No se afirma despliegue allí.

## Diagnóstico F5 autorizado: detenido por falta de clave

El usuario autorizó una única consulta adicional de Twelve Data para un símbolo BMV
verificado. Se ejecutó el diagnóstico preparado sobre BMV:ALPEK con el cargador habitual
solo en memoria. **No encontró TWELVEDATA_API_KEY**, nombre confirmado en terminal/config.py.
El diagnóstico terminó antes del HTTP: **0 solicitudes, ningún código HTTP, sin precios
nuevos ni activación**. Evidencia: `twelve-unico-diagnostico-20261101.json`.

La autorización de una consulta quedó sin consumir. No se crea una cuenta, no se pide
una clave nueva, no se usa una clave demo como si probara la cuenta del usuario y no se
concluye que hubo rechazo del plan Basic. La documentación XMEX que pide Pro+/Venture+
sigue siendo evidencia documental de cobertura general, separada de permisos de cuenta
que **continúan sin comprobar**. Si el usuario configura por sus propios medios una
clave existente en el mecanismo habitual, quedaría pendiente realizar el diagnóstico
único y documentar la respuesta antes de considerar cualquier uso como respaldo.

No se considera cerrada F5 por tener conector y pruebas simuladas. El requerimiento de
no crear cuentas y no inventar secretos impide subsanar automáticamente la credencial.

## Resultado final de pruebas — extensión de variación diaria

La suite completa posterior al último código finalizó con código 0: **837 aprobadas,
una advertencia Starlette, 713,73 s (11 min 54 s)**. Log `gratis-pytest-variacion-20261101.txt`.
Este resultado sí cubre la procedencia API de la ventana y los trece casos nuevos,
además de la regresión general; sustituye el estado «en curso» para esa ejecución.
Node: 43 aprobadas; worker: 19; cuatro recorridos Chromium aprobados. `git diff --check`
sin errores (solo avisos de normalización CRLF de Git). No se hicieron commit ni push.

Matriz actual por requisito y evidencia:
`proveedores-20261101-evidencia/matriz-cierre-proveedores-20261101.json`.
F5 continúa sin acceso de cuenta comprobado porque falta TWELVEDATA_API_KEY en el
mecanismo habitual; la autorización de un diagnóstico sigue sin consumir (0 llamadas).
No se declara completado ese punto ni el objetivo entero. No se reinició el servidor
habitual: la revisión visual acredita únicamente la instancia aislada nueva, ya cerrada.
