# Auditoría de la entrega de reels — 31-oct-2026

Al iniciar no existían el informe de auditoría ni el JSON de pendientes. Sí había una carpeta de preparación con estado Git y huellas; no se tomó como auditoría terminada de Claude. Este informe corresponde a la continuación ejecutada por Codex.

## Alcance y resultado

Se corrigieron la validación numérica, el tratamiento del catálogo, etiquetas y foco de controles, estado de disposición y resultado manual obsoleto al editar entradas. No se iniciaron estrategias, cuentas, adaptadores, Telegram ni órdenes. La vista previa usa TERMINAL_SIN_MOTOR=1 y 127.0.0.1:8766. No se leyó ni imprimió .env. Sin commits ni push.

La skill codebase-memory se intentó mediante list_projects y devolvió Transport closed. Se siguió lectura directa en mesa.mjs, mesa.html, mesa.css, navegación, Pine, núcleo C# de riesgo, pruebas y controles de seguridad. No hay prueba de cobertura global del grafo. La revisión es acotada a estos cambios, no de cada línea de toda la terminal.

## Hallazgos y estado

| ID | Prioridad | Estado | Hallazgo / criterio | Evidencia y siguiente acción |
|---|---|---|---|---|
| R31-01 | P1 | resuelto | Validación numérica: Rechazar ticks fraccionales de slippage, no finitos, desbordamientos y objetivos inválidos. | mesa.mjs y PlanManualNQ.cs; 12 vectores, 3 no finitos y referencia exacta independiente. Mantener los vectores al cambiar unidades. |
| R31-02 | P1 | parcial | Paridad Pine: Compilar en Pine Editor y comprobar los mismos escenarios. | JS/C# coinciden; Pine comparte epsilon, tolerancia y límites. Sin compilación remota. Abrir Pine Editor, pegar tradingview/mesa_riesgo_nq.pine, Guardar y Añadir al gráfico NQ solo como indicador; revisar largo/corto y cero contratos. No crear alertas ni estrategia. |
| R31-03 | P1 | resuelto | Catálogo y cobertura: No construir gráficas de símbolo predeterminado si falta catálogo o cobertura. | UI: catálogo vacío, petición fallida e instrumento sin gráfica muestran SIN DATO. Conservar los casos de fallo en la prueba de navegador. |
| R31-04 | P2 | resuelto | Disposición y accesibilidad: Actualizar la disposición personalizada, etiquetar flechas y conservar foco al mover. | UI por teclado, recarga persistente, seis combinaciones de tema/tamaño y cero errores JS. Añadir/Quitar conserva estado personalizado; cambios de escenario invalidan el resultado anterior. |
| R31-05 | P2 | resuelto | Carga diferida: No crear marcos cerrados y retirarlos al plegar. | Prueba Chromium confirma creación y eliminación de iframe. Mantener cero peticiones de paneles cerrados. |
| R31-06 | P2 | parcial | Proveedores: Comprobar contenido y vigencia por panel e instrumento, no solo HTTP. | Tres widgets públicos cargaron en contexto sin sesión; cotizaciones mostró contenido, mapa y calendario no acreditan vigencia de precios. Comprobar los restantes y cada símbolo con procedencia, hora y retraso; conservar SIN DATO si no hay cobertura. |
| R31-07 | P2 | resuelto_en_alcance | Floorplan Actinver: Describir todos los archivos y rutas que detecta el escáner de Actinver. | 239/239 archivos de código, 127/127 rutas y cero sin asignar. No analiza Pine ni acredita seguridad completa. Actualizar el mapa cuando cambie el código; los proyectos externos requieren mapas separados si se solicita su alcance completo. |
| R31-08 | P2 | pendiente_fuente | Recursos sin identidad: Confirmar propietario y URL antes de añadir un recurso con nombre ambiguo. | config/reels-20261031.json; no se inventaron los enlaces restantes ni se enviaron DMs. Obtener enlace público inequívoco o descripción/fotograma que identifique autor y repositorio. |
| R31-09 | P2 | parcial | Inventario y licencias: Distinguir skills instaladas y clones, con licencias comprobadas. | 33 recursos sin observaciones; taste-skill, skills y andrej-karpathy-skills carecen de licencia inventariada verificable; Caveman instalado no coincide con la versión del clon archivado. Conservarlos como referencias de lectura; confirmar procedencia y licencia de la versión exacta antes de copiar contenidos. |
| R31-10 | P1 | verificado_sin_aprobacion | Candados y evidencia: Adaptador, live y fondeada apagados; no iniciar órdenes ni estrategias. | estado_demo.py: false/false/false, sin diario, incidentes no auditados, sin ventaja demostrada. Nada en esta auditoría autoriza trades, tampoco demo. |
| R31-11 | P2 | pendiente_investigacion | Hipótesis NQ: Regla y dataset preregistrados antes de inferencia estadística. | Los reels y el calculador manual no especifican una estrategia reproducible con ventaja. Definir contrato, horario, datos, costos y regla causal offline. Fuera de la corrección de la Mesa; no empezar estrategias. |

## Correcciones verificadas

- `web/static/mesa.mjs`, función planNQ: antes aceptaba 0.5 ticks de slippage y un R extremo devolvía recompensa Infinity. Ahora exige ticks enteros y valores finitos dentro del dominio documentado de la calculadora. Dominio de estudio: precios y presupuesto ≤ 1e9, R ≤ 1000, comisión y ticks de deslizamiento ≤ 1e6. Son límites del software, no reglas de la bolsa ni del broker.
- Pine tenía distinta tolerancia de tick y carecía del epsilon de redondeo que usa JS. Comparte ahora los valores y el dominio; el compilador remoto sigue pendiente. La inspección estática no es compilación ni paridad ejecutada de Pine.
- `FuturosLab.Nucleo/PlanManualNQ.cs` es una nueva función pura, sin referencias a órdenes y sin conexión con un adaptador. El runner compara resultados contra JS y la cantidad contra Riesgo.Contratos existente, convirtiendo ticks a dólares. No se desplegó una DLL en Quantower.
- Catálogo vacío/fallido: ya no carga una gráfica NVDA por suposición. Para instrumentos sin gráfica declarada muestra SIN DATO. Los paneles macro independientes y el escenario manual siguen disponibles.
- Añadir/Quitar/Mover muestran disposición personalizada; flechas tienen nombre accesible y límites deshabilitados. El foco sigue al panel movido; al quitar vuelve al selector. Al editar entradas se invalida el resultado anterior.
- El inventario distinguía mal la skill Caveman de un clon Git. Ahora comprueba su huella; la versión instalada no coincide con los SKILL.md del clon archivado y no hereda su licencia por el nombre. Se completaron archivos de licencia de otros clones sin instalarlos de nuevo. Quedan tres observaciones de licencia y una de procedencia, sin convertirlas en aprobadas.

## Pruebas reproducibles

Desde actinver-terminal:

```powershell
node --test tests/mesa.test.mjs tests/mesa_paridad.test.mjs tests/riesgo_nq_referencia.test.mjs tests/navegacion.test.mjs tests/guias.test.mjs
.\.venv\Scripts\python.exe -m pytest tests/test_referencias.py tests/test_inventario_reels.py tests/test_seguridad.py -q
.\.venv\Scripts\python.exe tools/verificar_repositorios_reels.py --json docs/auditoria-reels-20261031-evidencia/codex-continuacion/inventario-comprobado.json
```

Resultados: 14 pruebas Node y 23 Python aprobadas; una advertencia de deprecación de Starlette. La prueba de referencia exacta fue encontrada como cambio nuevo de otra sesión y se conservó; pasó con la implementación actual. No se cambió su generador ni sus resultados para hacerla pasar.

Paridad C# (SDK existente de futuros-lab, sin descargas):

```powershell
& C:\Users\MIKE\Desktop\Repos\futuros-lab\_tools\dotnet\dotnet.exe run --project docs/auditoria-reels-20261031-evidencia/codex-continuacion/paridad/Paridad.csproj -- docs/auditoria-reels-20261031-evidencia/codex-continuacion/vectores-resultados-js.json
```

12 vectores JS/C# coincidentes, incluidos inválidos, y tres no finitos rechazados. Datos sintéticos de prueba; no trades ni rentabilidad.

Chromium aislado: seis vistas (oscuro/claro × 390/768/1440 px), persistencia, teclado, foco y carga diferida; cuatro fallos controlados (catálogo vacío, red caída, almacenamiento denegado y símbolo sin cobertura). Cero errores JS y cero desbordamientos horizontales. `ui-resultados.json` y capturas en la carpeta de evidencia. Reproductor: work/audit31_ui.cjs del workspace original; usa dependencias ya existentes, sin perfiles personales.

Prueba separada con red pública, sin sesión del usuario: eventos, mapa y cotizaciones cargaron sus scripts y marcos. Cotizaciones mostró datos; no se verificó su fecha de mercado ni su exactitud. El calendario y el mapa no aportaron evidencia textual suficiente de datos vigentes. Los demás paneles y símbolos siguen pendientes. Capturas y textos en proveedores.json. Ningún HTTP 200 se presenta como aprobación del feed.

## Mapa y límites estructurales

Floorplan en http://127.0.0.1:4378; archivos locales en floorplan/. Describe 239 archivos y 127 rutas detectados, sin código sin asignar. Interfaz → servidor → datos locales; pruebas y herramientas separados del servicio opcional de avisos. Cambios de esta auditoría resaltados. El mapa queda fuera de Git y sus descripciones son editables; puede actualizarse después. No se añadieron notas de activación automática en CLAUDE.local.md.

Health: cero hallazgos altos. Dos observaciones medias: falta de identidad de usuario detectada por el escáner y archivos muy grandes. La primera no demuestra acceso público sin control: seguridad.py verifica Host, Origin y CSRF; pruebas de seguridad aprobadas. No se rebajan esas protecciones para arreglar marcos. La segunda queda como deuda de mantenibilidad de app.py/app.js; no se hizo una reescritura masiva. Esto no certifica ausencia de vulnerabilidades.

El mapa es del código detectado de Actinver; no analiza Pine ni la totalidad de futuros-lab y no representa una integración nativa con Quantower.

## Matriz de fuentes

| Fuente | Recurso / aplicación real | Archivo / evidencia | Estado |
|---|---|---|---|
| [De7fAL3pNpE](https://www.instagram.com/p/De7fAL3pNpE/) | Arquitectura de automatización de una prop firm | config/reels-20261031.json; docs/integracion-20261031.md | Lectura y catálogo; sin ejecución de agentes |
| [DfH0XUytCkS](https://www.instagram.com/p/DfH0XUytCkS/) | Procedimiento de backtesting MT5 | config/reels-20261031.json; docs/integracion-20261031.md | Lectura y catálogo; sin ejecución de agentes |
| [DfHvgtrt-B_](https://www.instagram.com/p/DfHvgtrt-B_/) | Gamma scalping y volatilidad | config/reels-20261031.json; docs/integracion-20261031.md | Lectura y catálogo; sin ejecución de agentes |
| [DfF0Tb5Dwr5](https://www.instagram.com/p/DfF0Tb5Dwr5/) | ErTasselli/OpenTerminal | config/reels-20261031.json; docs/integracion-20261031.md | Mesa, navegación y pruebas UI |
| [DfKC9sgoA6Z](https://www.instagram.com/p/DfKC9sgoA6Z/) | haydenschmitty/floorplan | config/reels-20261031.json; docs/integracion-20261031.md | Mapa local |
| [De-ccVLk3Aw](https://www.instagram.com/p/De-ccVLk3Aw/) | The-Swarm-Corporation/AutoHedge, HKUDS/Vibe-Trading, Fincept-Corporation/FinceptTerminal | config/reels-20261031.json; docs/integracion-20261031.md | Lectura y catálogo; sin ejecución de agentes |
| [De1mAq9oaDP](https://www.instagram.com/p/De1mAq9oaDP/) | EricJujianZou/rederive | config/reels-20261031.json; docs/integracion-20261031.md | Lectura y catálogo; sin ejecución de agentes |
| [DeumR-AE7Xy](https://www.instagram.com/p/DeumR-AE7Xy/) | Leonxlnx/taste-skill, addyosmani/agent-skills, JuliusBrussee/caveman, Graphify-Labs/graphify, nextlevelbuilder/ui-ux-pro-max-skill, DietrichGoetz/ponytail, anthropics/skills, multica-ai/andrej-karpathy-skills, mattpocock/skills, obra/superpowers | config/reels-20261031.json; docs/integracion-20261031.md | Lectura y catálogo; sin ejecución de agentes |
| [DfLGXy_AT5v](https://www.instagram.com/p/DfLGXy_AT5v/) | Jakeschincariol/day-trader-skill | config/reels-20261031.json; docs/integracion-20261031.md | Lectura y catálogo; sin ejecución de agentes |
| [DfCtGNgiWeb](https://www.instagram.com/p/DfCtGNgiWeb/) | Jakeschincariol/replica-skill, ChromeDevTools/chrome-devtools-mcp | config/reels-20261031.json; docs/integracion-20261031.md | Lectura y catálogo; sin ejecución de agentes |
| [De3LhlCgT9F](https://www.instagram.com/p/De3LhlCgT9F/) | affaan-m/ECC | config/reels-20261031.json; docs/integracion-20261031.md | Lectura y catálogo; sin ejecución de agentes |
| [DfBQ1AgOC1S](https://www.instagram.com/p/DfBQ1AgOC1S/) | Treinta plugins por trabajo | config/reels-20261031.json; docs/integracion-20261031.md | Lectura y catálogo; sin ejecución de agentes |
| [Dep4K9exVQ2](https://www.instagram.com/p/Dep4K9exVQ2/) | TauricResearch/TradingAgents, virattt/ai-hedge-fund, microsoft/qlib, AI4Finance-Foundation/FinGPT, AI4Finance-Foundation/FinRL | config/reels-20261031.json; docs/integracion-20261031.md | Lectura y catálogo; sin ejecución de agentes |

Las ideas de gamma y los agentes IA son referencias de investigación; no se transformaron en señales NQ ni se afirmó alfa. No se volvieron a descargar repositorios ni a añadir estrellas. Los nombres restantes sin propietario inequívoco y las 320 skills prometidas por mensaje privado siguen sin resolver; no se enviaron mensajes para obtenerlos.

## Pendientes externos y pasos seguros

R31-02: este entorno no expone una conexión de edición a Pine Editor. Abra TradingView personalmente, copie el indicador y compile sin crear alertas ni estrategia. Registre versión, mensaje del compilador y captura de los escenarios del JSON. Ninguna marca estática de esta auditoría acredita ese paso.

R31-06: revisar disponibilidad y retraso de cada panel y símbolo con fuentes autorizadas; no activar cuentas, contratar datos ni sustituir NQ por CFD.

R31-08/R31-09: confirmar identidad y licencia antes de incorporar o copiar recursos ambiguos. No se inventan enlaces ni se supone una licencia por el número de estrellas.

Estado final de estado_demo.py: PAPER; adaptador=false, live=false, fondeada=false; sin diario disponible, incidentes no auditados y sin ventaja demostrada. No se inició ningún trade, tampoco demo. La auditoría y el mapa no autorizan ejecución.

Documentación primaria consultada: [Pine v6: Inputs](https://www.tradingview.com/pine-script-docs/concepts/inputs/) y [CME: especificación NQ](https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.contractSpecs.html). Las restricciones del calculador no se atribuyen a esas fuentes.

## Anexo — verificación independiente de Claude (31-oct-2026, 20:20)

Claude auditó en paralelo con el Codex que escribió este informe (ver `docs/auditoria-reels-20261031-evidencia/COORDINACION.md`; hechos: R31-22). Lo siguiente se comprobó por separado; no sustituye lo anterior.

**Resultado**
- Aritmética: la Mesa (NQ), las fórmulas del Pine (NQ y MNQ, transliteradas) y `NoiseBands.cs` (NQ y MNQ) coinciden con una referencia exacta (Fraction) en 532 escenarios, 510 válidos, 0 diferencias. Vectores: `futuros-lab/scripts/generar_vectores_mesa_riesgo.py`; pruebas: `tests/riesgo_nq_referencia.test.mjs`, `futuros-lab/tests/test_mesa_riesgo_paridad.py`, `MesaRiesgoVectores.cs`. Las del Pine son de las fórmulas, no de Pine.
- **Pine compilado en el servidor de TradingView** (`pine_check`, sin gráfico, alertas ni estrategia): éxito, 0 errores, 0 advertencias, sobre el archivo sha256 `c020bd30…` (R31-02: ya no es «sin compilación remota»; falta la comprobación visual en un gráfico).
- Catálogo: 23 tipos = 16 externos + 6 accesos + calculadora; cada panel externo tiene ruta en `terminal/app.py` y cada acceso apunta a una pestaña real (`tests/mesa_catalogo_auditoria.test.mjs`).
- Navegador (127.0.0.1:8791, `TERMINAL_SIN_MOTOR=1`): añadir, quitar, mover, persistencia y recarga bien; `localStorage` con destinos inyectados, `javascript:` y símbolo malicioso queda neutralizado (2 paneles válidos, 0 enlaces, 0 marcos); JSON corrupto vuelve a la disposición por defecto; 375, 768 y 1280 px sin desbordamiento; tema claro/oscuro sigue `prefers-color-scheme`; cero errores de consola.
- Seguridad: sin `innerHTML`/`eval` en `mesa.mjs`, `navegacion.mjs` ni `mesa.html`; sin secretos en los archivos nuevos o modificados; la Mesa no hace mutaciones (sin CSRF); `/widget` y `/grafica` rechazan símbolos con `<script>`, rutas con `..%2f` y temas/intervalos fuera de lista (404/422); la CSP global no se tocó (`frame-ancestors 'none'`; las dos rutas de marcos usan `'self'`).
- Repositorios: `tools/verificar_repositorios_reels.py` (solo lectura): 37 inventariados, 33 sin observaciones y 4 con observaciones (caveman: procedencia; taste-skill, anthropics/skills y andrej-karpathy-skills: sin archivo de licencia, por lo que solo son referencia; Fincept sigue marcado AGPL-3.0 y no se copia).
- Pruebas ejecutadas: Node `tests/*.test.mjs` 20/20 antes de los míos más 4 de catálogo; `tests/test_referencias.py tests/test_cobertura_secciones.py tests/test_tradingview_pine.py` 9/9; futuros-lab 163 pasan y 1 se omite (las copias del Pine, ahora sincronizadas) y 244 comprobaciones C# sin fallos.

**Pendientes nuevos (ver `docs/pendientes-reels-20261031.json`)**: R31-12 (ruta Velas), R31-13 (gap), R31-14 (MNQ), R31-16 (duplicado y paneles abiertos), R31-17 (sandbox), R31-18 (Datos y fuentes), R31-19 (cobertura real), R31-20 (estrellas y OpenTerminal sin reproducir), R31-21 (day-trader-skill y Time Machine), R31-22 (edición concurrente). R31-15 (copias del Pine) quedó resuelto.

**Límites**: no se vio ninguna captura de widgets (el panel del navegador no podía dibujar); la disponibilidad dentro de los marcos de TradingView no se verificó. La aritmética no es una estrategia: sin diario forward, incidentes no auditados y sin ventaja demostrada. Ningún trade, demo ni inicio de estrategia; adaptador, live y fondeada siguen en false.

## Anexo — matriz de 13 fuentes con su prueba

Una fila por post de `config/reels-20261031.json`. «Aplicación» es lo que existe en el código o en los documentos; «prueba» es lo que lo verifica hoy. «Sin prueba» significa que no hay código que probar: el post solo alimentó un documento o un inventario.

| Post | Recurso (inventario) | Archivo donde vive | Aplicación | Prueba |
|---|---|---|---|---|
| De7fAL3pNpE | Arquitectura de prop firm (sin repo) | `docs/integracion-20261031.md` | Solo diseño de investigación; el puente de ejecución se excluye | Sin prueba. Candados: `futuros-lab/tests/test_noise_bands_avisos.py::test_no_hay_apis_de_ordenes_en_los_avisos` y `estado_demo.py` |
| DfH0XUytCkS | Procedimiento de backtesting MT5 (sin repo) | `docs/integracion-20261031.md` | Se cita como protocolo; MT5 no se conecta | Sin prueba |
| DfHvgtrt-B_ | Gamma scalping (sin repo) | `docs/integracion-20261031.md` | Aviso conceptual: GEX no es P&L de gamma scalping ni señal NQ | Sin prueba |
| DfF0Tb5Dwr5 | ErTasselli/OpenTerminal (MIT) | `web/static/mesa.{html,mjs,css}`, `navegacion.*`, `referencias.json` | Mesa nativa de 23 tipos; implementación propia, no copia | `tests/mesa.test.mjs`, `mesa_paridad.test.mjs`, `mesa_catalogo_auditoria.test.mjs`, `riesgo_nq_referencia.test.mjs`, `tests/test_referencias.py`; navegador en 127.0.0.1:8791 |
| DfKC9sgoA6Z | haydenschmitty/floorplan (MIT) | mapa local de Codex (fuera de Git) | Descripción de 239 archivos y 127 rutas de Actinver | `tools/verificar_repositorios_reels.py` (licencia/commit); el mapa no tiene prueba automática |
| De-ccVLk3Aw | AutoHedge, Vibe-Trading (MIT), FinceptTerminal (AGPL-3.0) | `config/repositorios-20261031.json` | Referencias; no se activan agentes ni se copia AGPL a MIT | `tests/test_inventario_reels.py`, `tools/verificar_repositorios_reels.py` |
| De1mAq9oaDP | EricJujianZou/rederive (MIT) | `config/repositorios-20261031.json` | Skill de apoyo para explicar decisiones; opcional | Inventario (huella de `SKILL.md`) |
| DeumR-AE7Xy | Diez skills: siete con archivo de licencia verificado; caveman con procedencia sin verificar; anthropics/skills y andrej-karpathy-skills sin archivo de licencia (el taste-skill de senlindesign es otro repositorio local, también sin licencia inventariada) | `config/repositorios-20261031.json` | Referencias; no se instalan las «320 skills» | `tools/verificar_repositorios_reels.py` (4 observaciones) |
| DfLGXy_AT5v | Jakeschincariol/day-trader-skill (MIT) | `web/static/mesa.mjs` (cálculo propio); clon en Repos | Se implementó el cálculo NQ con ticks; trader-exit/broker no se usan | `futuros-lab/tests/test_day_trader_exit_no_apto_futuros.py` (por qué no sirve), `tests/riesgo_nq_referencia.test.mjs`, `futuros-lab/tests/test_mesa_riesgo_paridad.py`, `MesaRiesgoVectores.cs` |
| DfCtGNgiWeb | replica-skill, chrome-devtools-mcp (Apache-2.0), REA, Agent-Reach, Context7 | `config/repositorios-20261031.json` | Herramientas de desarrollo; no se activó ningún MCP global | Inventario; la Mesa se probó en un Chromium aislado |
| De3LhlCgT9F | affaan-m/ECC (MIT) | `config/repositorios-20261031.json` | Referencia de revisión; no se cargan hooks | Inventario |
| DfBQ1AgOC1S | 30 plugins por trabajo (nombres sin URL) | `config/reels-20261031.json` | Catálogo con procedencia; los nombres ambiguos siguen sin resolver (R31-08) | Sin prueba |
| Dep4K9exVQ2 | TradingAgents (Apache-2.0), ai-hedge-fund, qlib, FinGPT, FinRL (MIT) | `config/repositorios-20261031.json` | Referencias de hipótesis; sin modelos ni agentes de trading | Inventario |


## Continuación Codex: cierre de pendientes

Ver `cierre-pendientes-reels-20261031.md`, hashes, pruebas y capturas. Actualización por ID sin borrar anexos: R31-12/13/14/16/18 resueltos; R31-17/19 parciales. Pine actual recompilado en servidor (0 errores/advertencias), visual pendiente. Sin operaciones ni conexión de ejecución.
