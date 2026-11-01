# Proveedores oficiales de Mesa — 1-nov-2026

Alcance: consultas de investigación y calendario de solo lectura. Sin motor, órdenes,
cuentas, mensajes externos, compras, commit o push. No se leyó `.env` ni se cambiaron
credenciales. Los datos simulados de pruebas nunca se guardaron en la base del usuario.

## Implementación por ID

| ID | Cambio comprobable en código | Estado externo |
|---|---|---|
| F2 | DGS30 en FredMacro; Mesa elimina el requisito cuando existe observación al corte | Identidad confirmada en ficha oficial FRED; descarga con clave no comprobada |
| F3 | BanxicoSIE: GET de catálogo antes de datos, compara idSerie y título de tasa objetivo; BANXICO_TOKEN existente | SF61745 documentado, GET sin token HTTP 400; título por API NO confirmado. Apagado |
| F6 | Misma ruta y almacenamiento; filtro bono M/tasa fija, 10 años, excluye UDIBONOS/TIIE | ID pendiente; no se adivina ni se configura. SIN DATO |
| F4 | INPC en el mismo conector, filtro de título del índice y rechazo de variaciones; sin credencial nueva | ID pendiente; SP1 sin token HTTP 400 no valida nada. Apagado |
| F1a | ClienteSEC reutilizado, comprueba CIK/símbolo, filtra Item 2.02, conserva aceptación EDGAR zonificada y URL oficial | Sin SEC_USER_AGENT disponible; cero consultas. No hay BPA ni hora del anuncio estructurados en este contrato |
| F1b | CSV EARNINGS_CALENDAR, estimación/fecha prevista/moneda, conocimiento al descargar y revisiones conservadas | Sin clave disponible; cero consultas, plan_verificado=false, apagado |
| F1c | GET /api/mesa/resultados lee SQLite; Mesa muestra tres campos separados, procedencia y fecha de conocimiento; reutiliza reaccion_resultados | Parcial solo cuando hay datos. SIN DATO en campos ausentes. Reacción requiere anuncio verificado, coherente con sesión y cierres conocidos al corte |
| F5 | Diagnóstico manual de UNA petición a símbolo BMV verificado, valida mercado/símbolo y precio finito positivo; nunca activa cola | Sin clave, cero consultas. XMEX general documenta Pro+/Venture+, EOD; no se añade un proveedor Basic sin permiso acreditado |

Banxico reutiliza la infraestructura HTTP/cupos `Adaptador` y la misma variable existente.
No reutiliza `tasa_libre()` como lector de indicadores: esa función calcula CETES y no
valida identidad por catálogo. El nuevo lector no escribe tasas de Markowitz ni precios.
Las observaciones pasan por la validación y transacción existentes de investigación:
fuente `banxico_sie`, periodo, unidad, huella y `disponible_desde` de descarga. No se
atribuye conocimiento en el pasado a una serie histórica descargada hoy.

El calendario lee todas las revisiones de las dos fuentes al corte. El resumen general
de investigación colapsa revisiones y por ello no sirve para reconstruir una previsión
previa. Al exceder 4.000 registros relevantes devuelve SIN DATO explícito, en vez de
calcular con una historia truncada. La importación manual conserva su etiqueta y no
acredita automáticamente hora del anuncio. Una estimación sin hora verificada se muestra
como tal, sin sorpresa ni reacción inferida. No se asocia un filing SEC a una fecha prevista
por simple proximidad temporal.

## Identidad oficial y comprobaciones reales

- **DGS30:** [ficha oficial](https://fred.stlouisfed.org/series/DGS30) confirma Treasury a
  30 años, diario y porcentaje; se revisó documentación, no se descargó a SQLite por web.
- **SF61745:** [documentación oficial SIE](https://www.banxico.org.mx/SieAPIRest/service/v1/)
  lo cita como tasa objetivo. El GET requerido devolvió 400 sin token: NO confirmado por
  metadatos y NO habilitado. **No hay otro código Banxico confirmado en esta entrega.**
- **Bono M 10 años e INPC:** pendiente identificación y GET válido en catálogo oficial.
  Los códigos SF123/SP123 de las pruebas son ficticios y no son recomendaciones de serie.
- [SEC API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces):
  submissions es público sin clave; ClienteSEC exige identificación válida. No se inventó
  correo ni se automatizó una cuenta.
- [Alpha Vantage](https://www.alphavantage.co/documentation/#earnings-calendar): contrato
  documentado, plan de la cuenta NO comprobado. No se usó una clave demo ajena.
- [Twelve Data XMEX](https://twelvedata.com/exchanges/XMEX): ficha Pro+/Venture+, EOD,
  GMEXICOB de prueba. No deducir Basic o acceso general de una excepción.

Evidencia de peticiones reales: `proveedores-20261101-evidencia/verificacion-publica.json`.
Solo dos GET sin token a Banxico, ambos 400. Alpha, Twelve y SEC: cero llamadas
autenticadas/de datos reales en esta entrega. La lectura de documentación pública no
equivale a probar el acceso de una cuenta. Presencia de credenciales comprobada solo como
booleanos en proceso/usuario/máquina, sin leer valores de `.env`.

## Cupos y estado por defecto

| Ruta | Política aplicada | Medición real / simulada |
|---|---|---|
| FRED | Cupo existente; cinco series por ciclo en vez de cuatro | MockTransport comprueba cinco solicitudes, incluida DGS30; ninguna descarga real con clave |
| Banxico | 20/día y 8/min compartidos entre tres indicadores; son topes locales conservadores, no cuota oficial acreditada | Simulación: catálogo + datos = 2; identidad errónea = 1, sin datos; real = 2 GET rechazados sin token |
| Alpha calendario | 25/día bajo alias alpha_vantage compartido, 1/min calendario, una petición por CSV | Simulación: permiso ausente = 0; CSV o rechazo = 1; real = 0 |
| SEC | Cliente existente 5/s, política local adicional 5/min y 20/día, hasta ocho CIK configurados | Simulación: 1 CIK = 1; real = 0 |
| Twelve diagnóstico | 8/min; menor entre techo Basic 800/día y configuración local 700/día | Simulación: falta clave/catálogo = 0; aceptación/rechazo = 1; real = 0 |

HTTP 429 persiste espera Retry-After (segundos o fecha HTTP), sin reintento inmediato.
Los cupos usan reloj inyectado en estos conectores; no se reinician al crear otra instancia.
No se habilita un conector desde una respuesta ni desde una prueba.

## Pruebas y alcance

Comandos ejecutados desde el repositorio, sin sincronizar dependencias ni leer configuración
local de cuentas (conftest fija TERMINAL_SIN_MOTOR=1, TERMINAL_SIN_ENV=1 y base temporal):

```text
uv run --offline --frozen pytest tests -q
uv run --offline --frozen pytest tests/test_proveedores_mesa.py tests/test_mesa_datos.py -q
node --test tests/*.test.mjs
npm --prefix cloud-alerts test
```

Resultados exactos en `proveedores-20261101-evidencia/resultado-pruebas.json` y logs:

| Ejecución | Resultado |
|---|---|
| Python completa | **783 aprobadas, 3 fallidas**, una advertencia Starlette, 1283,84 s |
| Python específica final (con conexiones/DNS externos bloqueados) | **67 aprobadas**, cero fallas, una advertencia, 52,59 s |
| Repetición aislada de los tres fallos, sin red | **2 aprobadas, 1 fallida**, una advertencia, 23,61 s |
| Node | **43 aprobadas**, cero fallas/omisiones, 1943,6912 ms |
| Worker | **19 aprobadas**, cero fallas/omisiones, 1053,4905 ms |

Fallos iniciales: `test_bot_telegram.py::test_sin_credencial_no_se_activa_claude`,
`test_cobertura_secciones.py::test_mesa_declara_las_tres_familias_del_catalogo_real` y
`test_flujo.py::test_cripto_libro_y_operaciones_con_lado`. En la repetición solo persiste
el de cobertura: expectativa de 16 externos frente a 15 declarados. No se editó ese
módulo ni esas pruebas. Otra sesión cambió pruebas durante la ejecución: la prueba cripto
actual ya contiene una habilitación explícita que no figura en la traza de la corrida
completa. Las dos aprobaciones posteriores no se atribuyen a esta entrega. No se presenta
la suite completa como aprobada ni como instantánea inmutable del estado final.

Windows reportó recursos insuficientes al arrancar PowerShell; se continuó con PowerShell
del sistema. No se detuvieron procesos ajenos. Primera ronda acotada: 59 aprobadas;
pruebas específicas posteriores: 33 aprobadas; la validación final de 67 incluye los
últimos cambios y dos nuevos casos de respuesta SIE malformada.

Cada conector se prueba con `httpx.MockTransport`: no son pruebas de integración contra
proveedores. No se declara validación visual del calendario por esos tests ni rendimiento
medido. Ningún cálculo offline acredita forward, ventaja, rentabilidad o autorización.

## Pendientes concretos

1. Con la credencial ya disponible por mecanismo autorizado, confirmar GET de cada serie
   Banxico y guardar evidencia pública saneada del título/ID. No activar por un código
   tomado de un tercero. El usuario puede revisar el catálogo; no se solicita token nuevo.
2. Confirmar identificación SEC y CIK en fuente oficial. Los campos BPA realizado/revisado
   y anuncio deben venir de fuente estructurada con licencia; Item 2.02 solo no los cubre.
3. Una prueba Alpha autorizada con clave existente; solo si devuelve CSV válido y el plan
   lo permite revisar activación explícita de investigación. No habilitar desde el frontend.
4. Una prueba Twelve con cuenta cuyo plan sea conocido; documentar excepción por símbolo
   frente a cobertura general. Sin evidencia positiva, mantener cola sin cambios.
5. Verificación visual de registros reales en Mesa cuando las fuentes estén disponibles.
6. Coordinar con la otra sesión la expectativa de conteo en `test_cobertura_secciones.py`,
   sin reponer paneles ni cambiar el catálogo solo para hacer pasar la prueba.

## Cambios ajenos y revisión

Se preservan los cambios sin commit de la otra sesión, incluidos colores, guías, ajustes,
bot Telegram y navegación. En app.py esta tarea solo cambia el GET de resultados; en
mesa.mjs solo el render de Calendario. El parche acotado frente a los respaldos de inicio
está en `proveedores-20261101-evidencia/cambios-proveedores.patch`. No aplicar ese parche
automáticamente sobre cambios posteriores sin revisar.

Se leyó la skill codebase-memory. Sus herramientas de índice/cobertura no estaban
disponibles: fallback documentado mediante `rg`, lectura de definiciones/callers de
centro_investigacion, conectores, Adaptador, ClienteSEC, Mesa y sus pruebas. No se declara
cobertura exhaustiva del grafo ni se reindexa otro proyecto. No se añadieron dependencias.
