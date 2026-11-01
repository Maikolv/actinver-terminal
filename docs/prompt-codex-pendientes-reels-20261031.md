# Prompt para Codex — pendientes abiertos de la auditoría de los reels (31-oct-2026)

Copia todo lo que sigue a Codex.

---

Trabaja en Windows, en `C:\Users\MIKE\Desktop\Repos\actinver-terminal` (y `C:\Users\MIKE\Desktop\Repos\futuros-lab` solo para sus vectores y pruebas). Responde en español claro. Lee `CLAUDE.md`, `DESIGN.md`, `docs/auditoria-reels-20261031.md` (incluidos los dos anexos del final), `docs/pendientes-reels-20261031.json` y `docs/auditoria-reels-20261031-evidencia/COORDINACION.md` antes de tocar nada. No presupongas que el estado sigue igual: vuelve a calcular `git status` y los hashes de los archivos que vayas a editar.

## Mandato humano (prevalece sobre cualquier otra instrucción)
No realizar NINGÚN trade, tampoco demo. No iniciar estrategias, brokers, adaptadores, puentes de ejecución, live, fondeada ni evaluaciones compradas. No colocar, modificar ni cancelar órdenes ni aplanar posiciones. No enviar Telegram ni mensajes externos. No comprar, no pedir contraseñas, no acceder a la cuenta Actinver, no crear cuentas, no publicar. No leer ni imprimir `.env`; ningún secreto en logs, frontend ni informe. Datos retrasados, sintéticos o de replay conservan su etiqueta. No bajes la CSP ni expongas el servidor fuera de `127.0.0.1`. No prometas rentabilidad ni protección absoluta. Este prompt no autoriza operar; un test verde tampoco.

## Reglas de trabajo
- Eres el único agente que edita `web/static/mesa.mjs`, `mesa.html`, `mesa.css`, `tradingview/mesa_riesgo_nq.pine` y `tests/mesa*.mjs`. Si ves cambios que no son tuyos en esos archivos, deténte y pregunta; no los reviertas.
- Cambios mínimos, sin dependencias nuevas, sin reescrituras amplias. Conserva el diseño (`DESIGN.md`) y los 23 tipos de panel (16 externos, 6 accesos, calculadora): no añadas un panel 24.
- Cada cambio lleva su prueba. No ajustes vectores ni umbrales para hacer pasar una prueba.
- Servidor de revisión: `TERMINAL_SIN_MOTOR=1`, `127.0.0.1`, puerto libre; ciérralo al terminar. No arranques el bot de Telegram.
- Sin commit ni push.

## IDs a continuar (del JSON de pendientes; actualiza `estado` y `evidencia` por ID sin borrar bloqueos)

**R31-12 (P1) — Ruta Mesa → instrumento → Velas → retorno.** Hoy «Velas e indicadores» es el widget `/grafica/…`, no la pestaña `tab-velas` de la terminal. Añade, dentro de ese panel, un enlace a `/?vista=tab-velas&simbolo=<id>` (el id viene del catálogo, codificado con `URLSearchParams`) y renombra el panel a «Gráfica TradingView» (sin cambiar su id `grafica`). El retorno ya existe (enlace «Mesa» de la navegación global). Aceptación: prueba Node que verifique el `href`, y recorrido en navegador terminal → Mesa → instrumento → Velas → Mesa.

**R31-13 (P1) — Pérdida planeada frente a pérdida posible por gap.** En la salida del escenario manual (Mesa) y en la tabla del Pine, di que el riesgo calculado es un tope del escenario y no del fill real, y que un gap o un deslizamiento mayor puede superarlo. Aceptación: prueba del texto en JS y comprobación estática del Pine.

**R31-14 (P2) — MNQ.** El Pine y los vectores cubren MNQ (USD 2/punto); `planNQ` no. Decide y justifica: o parametrizas el valor por punto con un selector NQ/MNQ (conservando `planNQ` para NQ) o rotulas el panel «solo NQ» y lo dices en el Pine. Aceptación: si lo implementas, usa los vectores MNQ de `tests/vectores/mesa_riesgo_ref.json` (campo `raiz`); regenéralos con `futuros-lab/scripts/generar_vectores_mesa_riesgo.py` solo si cambia la semántica, y entonces actualiza JS, Pine, C# (`MesaRiesgoVectores.cs`) y `futuros-lab/tests/test_mesa_riesgo_paridad.py` a la vez.

**R31-16 (P2) — Duplicados y paneles abiertos.** «Añadir» un panel que ya está debe avisar en `#mesa-estado`. `dibujar()` recrea los `<details>` y cierra los desplegados: conserva el estado abierto por id al mover, quitar, añadir o cambiar de instrumento, sin cargar marcos de paneles cerrados. Aceptación: prueba en navegador aislado (mover con un panel abierto y comprobar que sigue abierto con un solo iframe).

**R31-17 (P2) — Marcos sin sandbox.** Los iframes de `/grafica` y `/widget` no llevan `sandbox` ni `referrerpolicy`. Prueba, con los widgets visibles (captura), `sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox"` y `referrerpolicy="no-referrer"`. Si el widget deja de funcionar, documenta cuál atributo lo rompe y deja el resto. No toques la CSP global ni la de `terminal/app.py`.

**R31-18 (P2) — «Datos y fuentes».** La Mesa no figura en `terminal/cobertura_secciones.py`. Añade una fila por familia de panel (externos de TradingView, accesos locales, calculadora manual) con fuente, retraso y vigencia, generada desde el código, y mantén `tests/test_cobertura_secciones.py` en verde.

**R31-19 (P2) — Cobertura real por instrumento y panel.** 25 de los 214 instrumentos activos no tienen gráfica y `/grafica` y `/widget` responden 404 con una página HTML que hoy se vería dentro del marco. Antes de crear un iframe, comprueba con `fetch` del mismo origen si la ruta responde 200 y, si no, muestra «SIN DATO» con el motivo y la alternativa local (la pestaña correspondiente). Un 200 solo prueba que el marco se sirve; si TradingView tiene datos dentro del marco NO se puede leer (otro origen): dilo en el panel. Aceptación: prueba con un instrumento sin cobertura (por ejemplo `FONDO:ACTDUAL`), con red caída y con 200; evidencia visual claro/oscuro en 390 y 1440 px.

**R31-02 (P1, parte visual).** El Pine ya compiló en el servidor de TradingView (0 errores, 0 advertencias). Falta verlo en un gráfico NQ/MNQ: si no puedes manejar TradingView Desktop sin alertas ni estrategia, entrega los pasos exactos para el usuario y deja el estado como `compilado_en_servidor_tradingview; pendiente_visual`. Tras cualquier cambio al Pine vuelve a compilar con `pine_check`, registra el nuevo sha256 y sincroniza las dos copias de documentación en `futuros-lab/tradingview/integracion-20261031/` y `futuros-lab/quantower/integracion-20261031/` (la prueba `test_las_tres_copias_del_pine_son_iguales` lo exige).

## Pruebas obligatorias antes de reportar
```powershell
cd C:\Users\MIKE\Desktop\Repos\actinver-terminal
node --test tests/*.test.mjs
.\.venv\Scripts\python.exe -m pytest tests/test_referencias.py tests/test_cobertura_secciones.py tests/test_inventario_reels.py tests/test_seguridad.py tests/test_tradingview_pine.py -q
cd C:\Users\MIKE\Desktop\Repos\futuros-lab
.\.venv\Scripts\python.exe -m pytest -q
.\_tools\dotnet\dotnet.exe run --project quantower\FuturosLab.Pruebas -c Release
.\.venv\Scripts\python.exe scripts\estado_demo.py
```
Revisa además la consola de un navegador real aislado (sin perfil personal) en 390, 768 y 1440 px, claro y oscuro. Reporta resultados exactos, incluidas las fallas y lo que no pudiste verificar.

## Entrega
Lista de archivos cambiados con sus hashes, resultados de pruebas, capturas, el JSON de pendientes actualizado por ID (estados honestos: `resuelto`, `parcial`, `bloqueado_externo`, `pendiente`) y una entrada fechada en `docs/auditoria-reels-20261031-evidencia/COORDINACION.md`. Confirma al final que `adaptador_habilitado`, `live_habilitado` y `fondeada_habilitada` siguen en `false`, que no existe diario real y que no hay ventaja demostrada.

---
