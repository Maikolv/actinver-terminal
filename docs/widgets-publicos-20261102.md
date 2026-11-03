# Widgets públicos: cobertura visual acotada — 2-nov-2026

Se revisaron los 15 tipos externos actuales de Mesa en Chromium aislado, 1440x1000, sin sesión ni claves. Las funciones reales de la aplicación generaron los marcos con un catálogo mínimo de NVDA público, sin posiciones ni precios locales, SQLite en memoria y SIN_ENV/SIN_MOTOR/SIN_CONFIG_LOCAL=1. No se inició servidor o motor ni se cambió CSP, sandbox o código de producción.

Primera ejecución: GET/HEAD solamente. Dos mapas vacíos y explorador sin filas: el propio diagnóstico bloqueaba consultas públicas de lectura del embed. Se conservó ese resultado. Segunda ejecución permitió POST de lectura del embed oficial a scanner.tradingview.com con ruta terminada en /scan. Para el explorador se permitió además OPTIONS y POST /america/metainfo; entonces aparecieron filas. La telemetría POST permaneció bloqueada. Estos endpoints internos se usaron por el embed, NO se incorporaron como API de datos de Actinver ni se reutilizaron sus resultados en modelos.

Los cuatro procesos terminaron con salida 0; incluye generación de marcos y tres variantes de navegador. Un intento inicial no encontró el runtime antiguo; se reutilizó el ya instalado en work/ui-check, sin instalar paquetes. Los contextos y navegadores se cerraron.

| Panel | Observación | Vigencia/acceso completo |
|---|---|---|
| mapa | Mapa visible en captura; texto DOM solo escala. Consulta pública scan necesaria. | NO VERIFICADOS |
| calendario | Eventos visibles; tres errores de cookie/Locks API con sandbox. | NO VERIFICADOS |
| noticias | Contenido del proveedor visible en el marco; no validación financiera. | NO VERIFICADOS |
| filtro | Tabla visible tras permitir metainfo y scan; no bastaban sus controles. | NO VERIFICADOS |
| resumen | Contenido del proveedor visible en el marco; no validación financiera. | NO VERIFICADOS |
| cotizaciones | Contenido del proveedor visible en el marco; no validación financiera. | NO VERIFICADOS |
| destacados | Contenido del proveedor visible en el marco; no validación financiera. | NO VERIFICADOS |
| mapa-etf | Mapa visible; consulta pública scan necesaria. | NO VERIFICADOS |
| divisas | Contenido del proveedor visible en el marco; no validación financiera. | NO VERIFICADOS |
| info | NVDA: el proveedor rotula AL CIERRE y 30-oct, USD y D; no cotización vigente verificada. | NO VERIFICADOS |
| perfil | Contenido del proveedor visible en el marco; no validación financiera. | NO VERIFICADOS |
| finanzas | NVDA: períodos fiscales visibles; no dato de mercado actual. | NO VERIFICADOS |
| tecnico | Contenido del proveedor visible en el marco; no validación financiera. | NO VERIFICADOS |
| noticias-emisora | Contenido del proveedor visible en el marco; no validación financiera. | NO VERIFICADOS |
| grafica | NVDA: Cboe One y vela diaria observados; no acredita SIP/CME ni hora de disponibilidad. | NO VERIFICADOS |

## Límites conservados

El aviso SIN DATO se mantiene visible si el script de TradingView no crea un marco. Chromium confirmó que se oculta al insertar un marco simulado y que cabe en la cinta de 76 píxeles a 320, 390 y 1440 píxeles de ancho. Esta comprobación cubre la presentación local. La disponibilidad de los datos dentro del marco se evalúa por separado.

Velas ofrece cierres locales de BMV cuando faltan barras OHLC. La función de series, ejecutada contra la caché en modo de solo lectura, devolvió datos para 45 de 46 instrumentos activos con clave BMV. El faltante es SMARTRC 14 (ISIN MX1BSM020001, BMV, MXN). [Relación oficial de vehículos](https://www.gob.mx/cms/uploads/attachment/file/113093/relacio_n_de_vehiculos_accionarios_y_de_deuda.pdf). Su serie está confirmada en el catálogo de BMV y se conserva al regenerar el universo. El precio teórico publicado por Actinver queda separado del histórico de cierres negociados, que sigue pendiente de una fuente autorizada. [Ficha de BMV](https://www.bmv.com.mx/es/Grupo_BMV/Estadisticas_de_Operacion/SMARTRC-31400-332591) · [Ficha de Actinver](https://actinver.com/smartrc)

### América Móvil en la BMV

En Velas, el selector incluye el grupo «BMV · cierres diarios guardados» y separa los datos históricos de los sintéticos. Chromium verificó la selección de WALMEX con respuestas simuladas, el enlace directo a SMARTRC con serie vacía y el respaldo de AMX con cierres reales de caché. Cada escenario se probó en móvil y escritorio, con temas claro y oscuro. Para AMX también se verificaron una serie vacía y una respuesta HTTP 503. Los resultados y capturas están en `proveedores-20261101-evidencia/widgets-bmv/`.

El símbolo público es [BMV:AMX/B](https://www.tradingview.com/symbols/BMV-AMX%2FB/). La gráfica y el panel de información generados por la terminal envían ese identificador. En Chromium aislado, el panel de información identificó la emisora y ambos marcos indicaron que el símbolo está reservado a TradingView. La gráfica mostró OHLC vacíos. Mesa muestra SIN DATO y un enlace a los cierres locales de Velas para esos dos paneles de AMX. La observación no se generaliza a otras emisoras o paneles. Las capturas y el resultado están en `proveedores-20261101-evidencia/widgets-bmv/`.

Mesa distingue un marco HTML servido de un dato comprobado. Si falla el catálogo o la petición del marco, muestra SIN DATO. Si el marco se sirve, mantiene la indicación de que los datos y su vigencia siguen sin verificar. La regresión local de formato distingue cero de valores vacíos, booleanos o no finitos. Pasaron 20 pruebas de Mesa después del ajuste de mensajes. La suite JavaScript anterior a ese ajuste de mensajes pasó 52 pruebas.

Un solo instrumento NVDA en los paneles por símbolo, grupos predeterminados en los generales y una observación por variante. No acredita todo el universo, BMV, cada campo, actualización durante sesión, profundidad o CME. Las capturas de mapa muestran contenido aunque su DOM no enumere las emisoras; texto no vacío tampoco implica datos correctos. No debe convertirse este diagnóstico en API no documentada ni en una prueba de rentabilidad.

El sandbox del calendario permite contenido pero emite errores. Los demás marcos siguen sin aislamiento completo demostrado; no se añadió allow-same-origin ni se debilitó CSP. R31-17 continúa parcial. R31-06/19 avanzan en observación visual de los 15 tipos, pero mantienen pendiente cobertura/vigencia por instrumento.

Documentación oficial consultada el 2-nov: [datos de widgets](https://www.tradingview.com/widget-docs/faq/data/) y [preguntas generales](https://www.tradingview.com/widget-docs/faq/general/). TradingView distingue datos retrasados de los widgets y el plan de su plataforma; una suscripción del usuario no cambia automáticamente los datos del embed. Su widget no es una API de exportación ni admite alimentar datos propios. Conservar rótulos y alternativas nativas SIN DATO.

Evidencia: resultado.json (15 tipos), lectura-scan-resultado.json (cuatro variantes), lectura-scan-preflight-resultado.json y lectura-completa-resultado.json (explorador), capturas PNG y revisar.cjs en proveedores-20261101-evidencia/widgets-publicos-20261102. La evidencia se limita a diagnóstico visual; no se guarda como histórico de mercado ni se conecta a ingesta.

Para SMARTRC 14, la BMV publica una gráfica de consulta y ofrece bases históricas mediante su canal comercial. No se acreditó una descarga gratuita autorizada de cierres diarios para el ISIN MX1BSM020001. Se conserva SIN DATO para el histórico local y los enlaces de consulta manual. [Catálogo oficial de bases de datos](https://cognos.bmv.com.mx/es/productos-de-informacion/bases-de-datos).

Chromium aislado confirmó que el gráfico y la ficha del widget restringen BMV:SMARTRC/14. El gráfico carece de OHLC y ambos marcos remiten a TradingView. Velas conserva los enlaces manuales y SIN DATO para el histórico local. [Evidencia](proveedores-20261101-evidencia/widgets-bmv/smartrc-resultado.json).
