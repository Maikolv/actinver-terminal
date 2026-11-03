# Comprobación visual Pine: límite del diseño separado

TradingView Desktop se abrió mediante su instalación existente. Se observó un diseño guardado «Reto Actinver», con USDMXN de FxPro y el indicador educativo de Auction Market Theory. Esto no verifica el indicador manual mesa_riesgo_nq ni un contrato NQ/MNQ.

Se abrió una pestaña separada y se intentó crear «Revision visual NQ sin operaciones». TradingView rechazó la creación mostrando «Ha llegado al límite de diseños de gráficos guardados en su plan». Evidencia: `proveedores-20261101-evidencia/pine-visual/limite-diseno-gratuito.png`. No se pulsó Ampliar ni se contrató nada. No se eliminó ni modificó el diseño existente para liberar espacio. La solicitud fallida de crear otro diseño no acredita que se haya guardado alguno.

R31-02 conserva la compilación remota previa y sigue pendiente visual. Para continuar gratis hace falta un gráfico temporal sin guardar admitido por la plataforma, o que el usuario disponga un espacio de revisión en el diseño existente. No se interpreta el aviso como permiso para borrar el diseño ni para saltar el límite. No se iniciaron alertas, estrategias, conexiones de broker u órdenes.

Los tres posts DfLZk23jLGs, DfKkuOOOSA8 y DfHxxjztOkR se consultaron nuevamente mediante lectura web pública: los tres devolvieron `Online fetch throttled`. No se atribuyó su contenido por orden de la descripción aportada por el usuario y no se eludió la restricción.

## Continuación autorizada por el usuario: caso visual real

El usuario autorizó explícitamente utilizar temporalmente «Reto Actinver» y restaurarlo. Se registró FXPRO:USDMXN, intervalo 1D, Volumen/Tics y AMT con entradas 0/0/0/2. Se cargó NQZ2026: la plataforma lo identificó como CME_MINI_DL:NQZ2026, futuro diciembre de 2026, con diez minutos de retraso. No se usó esa cotización como entrada.

Se pegó el archivo local `tradingview/mesa_riesgo_nq.pine` en Script sin título y se pulsó únicamente Añadir al gráfico. El indicador se compiló y apareció como «Futuros Lab · Mesa de riesgo MANUAL». Caso predeterminado: entrada de estudio 20000, stop 19990, objetivo 2R, presupuesto USD 100, comisión y slippage cero hipotéticos. Se observaron TP 20020, SL 19990, riesgo USD 200 y cero contratos, junto con las advertencias SIN EJECUCIÓN, costos cero como hipótesis y riesgo por gap. Captura `pine-visual/nqz2026-manual-cero-contratos.png`.

Se detectó superposición entre las tablas AMT y Mesa en la esquina superior derecha. Se ocultó AMT temporalmente para leer el caso y se restauró con Deshacer; después se deshizo añadir Mesa y el cambio de símbolo. Verificación final: FXPRO:USDMXN 1D con Volumen/Tics y AMT visibles, sin la superposición manual. Capturas `estado-anterior-usdmxn.png` y `restaurado-usdmxn.png` en la misma carpeta. No se guardó ni publicó el script, ni se crearon alertas, estrategias, conexiones u órdenes.

R31-02 queda **parcial visual comprobado en NQ**, no cerrado: falta recorrer en plataforma los demás vectores (corto, costos, slippage, entradas inválidas y MNQ). La superposición observada también necesita una solución de disposición antes de afirmar armonía cuando se usan ambos indicadores. No se modificó la fuente local para superar esta revisión.

## Segundo recorrido: 2-nov-2026

Sobre el mismo contrato NQZ2026 retrasado, se verificó además el vector corto: entrada manual 20000, stop 20010, 2R, presupuesto hipotético USD 1000, comisión USD 5 y deslizamiento total 2 ticks. Tras esperar el recálculo final se observaron TP 19980, SL 20010, riesgo USD 215 y cuatro contratos: coincide con el vector local. Una captura intermedia mostró USD 205 antes de incorporar el slippage; no se usó como resultado final. Evidencia: `proveedores-20261101-evidencia/pine-visual/nq-corto-costos-20261102.png`.

Se deshicieron, uno por uno, los cuatro cambios de parámetros, la incorporación del indicador y el cambio de símbolo. Observación final: FXPRO:USDMXN 1D, Volumen/Tics y AMT visibles, sin indicador manual. No se guardó ni publicó el script ni se realizaron operaciones. La fuente local permanece intacta. La superposición, MNQ, redondeo y entradas inválidas siguen pendientes de comprobación/solución visual; este recorrido no cierra R31-02. El índice de código devolvió Transport closed; se leyeron directamente la fuente Pine y los vectores locales.

## Disposición corregida y MNQ: 2-nov-2026

Se movió únicamente la tabla manual a position.bottom_right y se sincronizaron las dos copias activas en futuros-lab. Las fórmulas y límites permanecen iguales. Cuatro pruebas Node de referencia y cuatro Python de paridad/copias aprobaron (salidas 0; Python 1.54 s). El índice de cobertura devolvió Transport closed; se usaron las fuentes concretas como respaldo.

La nueva fuente se pegó en el editor sin guardar/publicar y Añadir al gráfico la compiló/renderizó. AMT quedó arriba y Mesa abajo, sin superposición entre ambas tablas. Sobre USDMXN se comprobó el rechazo de instrumento incompatible. La búsqueda con prefijo de bolsa quedó cargando; se canceló y una búsqueda MNQZ2026 sin prefijo sí devolvió el contrato oficial CME_MINI_DL:MNQZ2026 diciembre 2026, etiquetado retrasado.

Casos visuales MNQ:
- Predeterminado: entrada 20000, SL 19990, 2R, presupuesto 100, costos cero hipotéticos: TP 20020, riesgo USD 20, cinco contratos.
- Tick inválido: SL 19999.9: Sin escenario válido, sin líneas manuales.
- Redondeo: entrada 20000, SL 19999.75, 1.1R, presupuesto 100 y costos cero hipotéticos: TP 20000.25, riesgo USD 0.5, 200 contratos. Es un escenario aritmético, no una recomendación de tamaño.

Capturas en proveedores-20261101-evidencia/pine-visual: tablas-separadas-instrumento-incompatible-20261102.png, mnq-default-20261102.png, mnq-tick-invalido-20261102.png y mnq-redondeo-20261102.png. Se deshicieron todos los parámetros, símbolo e incorporación temporal; restaurado-final-20261102.png confirma FXPRO:USDMXN 1D, Volumen/Tics y AMT, sin Mesa. No se guardó/publicó, crearon alertas, estrategias ni órdenes.

La revisión sigue parcial: no se recorrieron TODOS los vectores en plataforma. Casos no finitos y límites rechazados por input pertenecen a las pruebas offline y no deben presentarse como ejecutados en Pine Editor. La fuente actual tiene compilación y los casos descritos, no una certificación exhaustiva ni alfa.

## Verificación numérica en Pine: los 532 vectores locales

Se generó un indicador de comprobación separado a partir de las seis expresiones aritméticas de la fuente manual actual y de tests/vectores/mesa_riesgo_ref.json: 532 casos, 510 válidos y 22 inválidos. No utiliza cotizaciones, solicita datos, genera señales o ejecuta operaciones. El primer intento con miles de array.push fue rechazado por el compilador: 161488 tokens frente al límite indicado de 100256 (CE10117); captura comprobacion-limite-tokens.png. Se conservó el fallo.

La segunda representación usa cadenas de números fijos y str.split/str.tonumber, sin quitar casos ni cambiar fórmulas/resultados. Se compiló y ejecutó en Pine Editor: tabla visible «532 casos · diferencias: 0», primer índice distinto -1; captura 532-casos-cero-diferencias.png. Generador reproducible: tools/generar_comprobacion_pine.py. Manifiesto con SHA de fuente, vectores y comprobador en comprobacion-vectores-manifiesto.json. Una prueba independiente de integridad del generador verifica los 532 registros serializados, referencias completas y expresiones de origen: una aprobada en 0.62 s, salida 0. No se corrió otra suite completa.

Alcance preciso: ejecución aritmética de los vectores finitos en Pine, con límites de input modelados explícitamente; contexto del contrato NQ/MNQ y algunos campos manuales ya comprobados en los recorridos anteriores. No equivale a teclear 532 formularios ni prueba interacción con NaN/Infinity: esos valores no forman parte del conjunto JSON y se cubren en las pruebas de validación JS/offline. No usa la cotización USDMXN sobre la que se dibuja la tabla. El comprobador NO reemplaza al indicador manual ni es una estrategia.

Se deshicieron la actualización y la incorporación temporal. restaurado-tras-532-casos.png confirma FXPRO:USDMXN 1D con Volumen/Tics y AMT originales, sin comprobador ni Mesa. No se guardó/publicó, crearon alertas ni órdenes. El propio reinicio previo de TradingView también mostró el diseño original restaurado.

R31-02 queda verificado en el alcance de cálculo fijo y revisión visual descrito, sustituyendo la nota anterior de «recorrido numérico exhaustivo pendiente». Se conserva el límite de interacción de campos, no se atribuye paridad absoluta a cualquier entrada futura y deben repetirse estas comprobaciones si cambia la fuente. La exactitud aritmética no demuestra rentabilidad ni autoriza operar.

## Contraste de la tabla: 2-nov-2026

Las cuatro filas de contenido usan blanco explícito sobre gris RGB(27,30,36), con contraste WCAG calculado de 16.7:1. Antes dependían del color de texto predeterminado del proveedor sobre gris. Se sincronizaron las tres copias y se compiló la fuente actual en Pine Editor; captura contraste-manual-20261102.png. El gráfico FXPRO:USDMXN rechaza el instrumento como corresponde; no se modificó símbolo, indicadores previos ni se usaron sus cotizaciones en cálculos. Tras la revisión se deshizo la incorporación temporal.

Nueve pruebas específicas aprobadas: integridad del generador (una, 2.22 s), cuatro Node (1091.3245 ms), cuatro Python de paridad/copias en futuros-lab (0.95 s), todas salida 0. El generador reproducido crea un comprobador idéntico byte a byte al que mostró 532 casos y cero diferencias: se conservó el manifiesto anterior y se registró la huella de la fuente de presentación nueva. No se atribuye la compilación antigua al nuevo SHA: el nuevo indicador manual se compiló aparte. No nueva suite completa.

La posición inferior puede coincidir con marcadores de eventos propios del gráfico en la última fila; el contraste queda corregido, no se afirma ausencia de cualquier solapamiento futuro. Pendiente de disposición configurable si se necesita evitar estos marcadores sin cambiar preferencias del usuario. Sin órdenes, alertas, estrategias, guardar/publicar, commit o push.

## Disposición configurable: 2-nov-2026

Se resuelve el solapamiento observado con los marcadores inferiores mediante la ubicación predeterminada Centro derecha. Un input de presentación permite también Abajo derecha y Arriba derecha. Fuente actual compilada y observada en Pine Editor: cinco filas completamente visibles, AMT arriba y marcadores abajo separados de la tabla en este recorrido; ubicación-configurable-20261102.png. No se cambió ninguna preferencia de eventos del usuario. Se retiró el indicador temporal; restaurado-ubicacion-20261102.png confirma USDMXN 1D, Volumen/Tics y AMT originales.

Cinco pruebas específicas posteriores aprobadas: integridad del generador (una, 0.47 s), paridad y copias (cuatro, 1.71 s), salida 0. El comprobador regenerado sigue idéntico al ejecutado con 532 casos/cero diferencias. Las tres copias activas coinciden. Manifiesto actual en ubicacion-configurable-20261102.json; no nueva suite completa. Esta disposición sustituye la nota anterior de pendiente configurable; no garantiza evitar otros indicadores futuros o cualquier posición alternativa. Sin guardar/publicar, alertas, estrategias ni órdenes.
