# Verificación de cinta de opciones, perfiles y Laboratorio

Fecha de revisión: 16-oct-2026, America/Mexico_City.

## Pruebas y revisión final

- `uv run pytest -q`: **601 aprobadas**, 1 aviso de deprecación preexistente
  Starlette/AnyIO, 1393.96 s. Esta corrida se inició durante la implementación.
- Tras los últimos ajustes, `uv run pytest -q tests/test_flujo_api_pendientes.py
  tests/test_perfiles_sesion.py tests/test_cinta_opciones.py
  tests/test_preregistro_skylit.py tests/test_flujo.py`: **49 aprobadas**,
  mismo aviso, 56.33 s. Incluye selección/caché, nanosegundos, medianoche
  de cripto, rutas y seguridad, cálculos y regresión del preregistro/CSV.
- `node --check web/static/app.js` correcto, también tras el último ajuste de UI.
- Patrones de `scripts/escanear_secretos.py` sobre los 18 archivos propios:
  **0 hallazgos**. No se imprimieron valores de credenciales.
- `git diff --check` y revisión del índice correctos; CHANGELOG del índice
  construido con `git show HEAD:CHANGELOG.md`, `hash-object` y `update-index`.
  Se comprobó que el contenido ajeno del archivo de trabajo queda intacto al
  retirar exclusivamente la entrada propia. TradingView excluido del commit.

## Entorno y aislamiento

Servidor temporal exclusivamente en `127.0.0.1:8777`, modo demo, con
`TERMINAL_SIN_ENV=1` y `TERMINAL_SIN_MOTOR=1`. El puerto 8766 de la otra sesión
no se modificó. La base de demostración está separada de la real en `data/demo`.
No se consultaron proveedores ni se arrancaron bot, motor o sincronizador.
Los datos de prueba de flujo tienen calidad `sintetico`, feed `SINTETICO` y
procedencia visible «SINTÉTICO». No se copiaron precios ni posiciones reales.

## Recorrido de Laboratorio en navegador

Chrome, ancho solicitado y comprobado con DOM: 375 px.

1. Cargar ejemplo SINTÉTICO, completar preregistro identificado como prueba.
   B=199, semilla=12345, holdout=0.3, embargo=5; dos estrategias sintéticas.
2. Guardar con Enter: experimento demo #1, huella del preregistro
   `ce977938c5dcf8f3df15c7d475542a165a4a7e487ea88195dfb22cb50a7de728`.
3. Evaluar con Enter: exploración=107, embargo=5, holdout=48.
4. Reemplazar los rendimientos por 160 filas de otros valores sintéticos.
   «Ver resultado» devuelve el mismo resultado y muestra:
   «El holdout ya se usó: se devuelve el resultado guardado».
5. Exportar JSON mediante teclado. El archivo se descargó y se leyó como JSON;
   contiene preregistro y resultado. La huella del holdout conservada es
   `89a94ef54301963a93ff942c88828fa7a57dc30228cfd869d0e1844af750b2ba`.

Esto prueba persistencia y bloqueo de reevaluación, no hipótesis financieras.

## Order Flow y Option Flow a 375 px

- TPO: seis barras de 5 minutos SINTÉTICAS en tres periodos (A=09:30,
  B=10:00, C=10:30), zona America/New_York, sin rellenar niveles o periodos.
- Perfil de volumen de doce operaciones SINTÉTICAS: volumen=186,
  POC representativo=102.9375, VAH=103, VAL=101. Cobertura parcial rotulada.
- Skylit: una operación SINTÉTICA guardada; cero pasan, una no evaluable;
  «Filtro completo aplicado: No» y motivos visibles. No se toma NBBO de cadena.
- Navegación Order Flow → Option Flow con flecha derecha y controles con
  Tab/Enter. Selectores y botones accesibles. Contenedores de tablas con foco
  explícito para permitir desplazamiento horizontal mediante teclado.
- Ancho del documento observado: 360 px dentro de viewport de 375 px, sin
  desbordamiento horizontal global. Las tablas anchas usan desplazamiento interno.
- Consulta de consola: sin errores JavaScript durante los recorridos completados.
  Hubo fallos de conexión del control del navegador y mensajes esperables mientras
  se reiniciaba el servidor temporal; se recuperó la sesión antes de verificar.
  Después de capturar los recorridos se perdió de nuevo la conexión del navegador:
  la última adición de foco explícito a tablas y del campo de selección OCC no pudo
  repetirse visualmente. La selección y caché sí pasaron pruebas HTTP falsas;
  el JavaScript final pasó la comprobación de sintaxis. No se afirma una segunda
  revisión visual de esos dos ajustes finales. Se detuvo el servidor temporal.

## Límites restantes

Sin datos reales nuevos en esta entrega: el adaptador se comprueba con HTTP falso.
La disponibilidad real previa de Alpaca queda fechada en la matriz de proveedores.
TPO OHLC es una cota inferior, sin calendario de cierres anticipados; no un perfil
completo de ticks. GEX sigue sin poblarse con la fuente gratuita sin OI fechado.
Finnhub y Twelve Data no se conectaron. Contratos Alpaca y tema Colab siguen
condicionados a las decisiones explícitas del usuario. Sin ventaja demostrada.

## Cierre de la verificación visual pendiente (16-oct-2026)

La desconexión descrita arriba se resolvió al retomar la tarea. Se revisó el código
final del commit `20638e7` en una nueva sesión Chrome, únicamente en la base demo
y en `127.0.0.1:8777`, con los mismos interruptores de aislamiento.

- Viewport comprobado: 375 px; documento de 360 px, sin desbordamiento global.
- Campo OCC: se introdujo `MU261120C00110000`; Tab pasa a «Evaluar cinta guardada»
  y después a «Actualizar cinta indicativa». Enter en actualizar muestra
  «En demostración no se consultan proveedores» y evalúa la cinta sintética guardada.
- Tabla Skylit: región con `tabindex=0`; las flechas movieron `scrollLeft` de 0
  a 120 px, conservando el foco. El filtro sigue explícitamente incompleto.
- TPO: tabla con foco de teclado, periodos A/B/C y zona America/New_York visibles.
  POC/VAH/VAL mantienen los valores sintéticos registrados arriba.
- Laboratorio: la lista recibe foco; al volver a abrir el resultado con otros
  rendimientos sintéticos devuelve el aviso de holdout usado y conserva la huella
  `89a94ef54301963a93ff942c88828fa7a57dc30228cfd869d0e1844af750b2ba`.
- Consola del recorrido final: **0 errores**. Capturas locales nuevas de campo OCC,
  tabla con desplazamiento, TPO y Laboratorio. Se restauró el tamaño del navegador,
  se cerró la pestaña de prueba y se detuvo el servidor temporal.

La comprobación visual de los dos últimos ajustes queda completada. No se activó
ninguna conexión de contratos, proveedor nuevo, cuenta ni servicio persistente.

### Resultado definitivo de la suite completa

`uv run pytest -q` sobre la versión final `20638e7`: **610 pruebas aprobadas**,
1 aviso de deprecación Starlette/AnyIO ya existente, **831.34 s (13 min 51 s)**.
La corrida incluye los últimos casos de selección/caché, nanosegundos, rutas y
medianoche de cripto. Sintaxis JavaScript y revisión de secretos correctas.
Esta nueva corrida completa sustituye la combinación de resultados parciales
como evidencia del estado final. En la continuación solo cambió documentación.
