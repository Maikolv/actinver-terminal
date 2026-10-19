# Oficina de inversión del TikTok: incorporación a Actinver-terminal

Revisión: 19 de octubre de 2026. Fuente: [TikTok de desde_ciro](https://vt.tiktok.com/ZSghdDLfa/), vídeo 7698135026516413717. La descripción visible propone crear un fondo con IA y enlaza los tres proyectos de abajo. No se presenta esa propuesta como un fondo autorizado ni como evidencia de rentabilidad. Se verificaron descripción y repositorios; no se afirma haber transcrito íntegramente el vídeo.

## Repositorios descargados

- **[PixelFund-AI](https://github.com/kyjwang/PixelFund-AI)**: `C:\Users\MIKE\Desktop\Repos\PixelFund-AI`. Commit `a821c685c7885b93af83b769042299f0840cc662`. Licencia: MIT. Clonado superficialmente; dependencias no instaladas; servidor no iniciado.
- **[pixel-hedge-fund](https://github.com/jaypolanco96/pixel-hedge-fund)**: `C:\Users\MIKE\Desktop\Repos\pixel-hedge-fund`. Commit `eb34f4d306901c5fb949c83a1bea74479bf44fec`. Licencia: No se encontró licencia general en la raíz. Clonado superficialmente; dependencias no instaladas; servidor no iniciado.
- **[company-pixel-office](https://github.com/ATK-zk/company-pixel-office)**: `C:\Users\MIKE\Desktop\Repos\company-pixel-office`. Commit `a5414480cbdeb813b1c2cfc02c1390ffa938127b`. Licencia: Sólo LICENSE-pixel-agents-MIT para recursos de terceros; licencia general no identificada. Clonado superficialmente; dependencias no instaladas; servidor no iniciado.

PixelFund-AI aporta como referencia una simulación con comité, datos y cartera virtual, pero requiere Node, PostgreSQL y Redis. Pixel Hedge Fund aporta mesas visuales y análisis técnico; incluye rutas de órdenes de Bybit/BloFin. Company Pixel Office aporta una oficina estática de seis roles, con consultas a la cuenta pública de sus autores y partes decorativas. No se conectó ninguna cuenta ni se inició ninguno de esos servidores. Un clon no equivale a instalación completa ni a revisión exhaustiva de seguridad. No se eliminó ningún repositorio.

## Implementación funcional incluida

Abre **Aprender y recursos → Oficina de inversión**, o `/static/recursos/oficina-inversion.html` desde la terminal local. Código original, sin reutilizar assets ni código de licencia incierta.

1. Importa velas y operaciones autorizadas en los apartados existentes. No se compran datos ni se actualizan proveedores desde la oficina.
2. Introduce el identificador exacto guardado, con vencimiento y mercado cuando corresponda. `MES` o `MNQ` por sí solos no garantizan que existan datos ni identifican necesariamente el contrato negociable.
3. Consulta seis mesas: Datos, Cuantitativo, Order Flow, Crítico, Riesgo y Coordinación. Describen los datos mediante reglas transparentes; **no son agentes LLM autónomos**.
4. Descarga el informe JSON con procedencia. Si faltan datos, se muestra la ausencia; los indicadores nulos y las fuentes mezcladas no producen una comparación válida. El umbral de 15 minutos desde el inicio de la barra es sólo un filtro conservador de esta vista, no una certificación de tiempo real ni una regla de entradas.
5. Pulsa **Preparar análisis para Claude**. Se genera un prompt con la evidencia para que lo revises y copies tú. No hay transmisión automática ni consumo de API. Sin las observaciones originales no se ejecutan nuevas pruebas estadísticas.

La vista reutiliza dos GET locales ya existentes: velas de siete días y operaciones de sesenta minutos. No añade endpoints de órdenes, dependencias, polling, animación continua, Redis, Docker ni procesos LLM. Coste LLM automático: cero. No se ha medido todavía una reducción porcentual de CPU/RAM frente a las tres aplicaciones completas.

Gamma, Option Flow, TPO y validación de alfa permanecen en las herramientas existentes; esta oficina no fabrica esos datos ni los sustituye por votos de agentes. La siguiente fase, si se desea, es integrar un único servicio de análisis por demanda con esquema validado, presupuesto y trazabilidad; no está implementado como agente autónomo en esta entrega.

## Quantower y TradingView

| Plataforma | Incorporado ahora | Trabajo posterior necesario |
|---|---|---|
| Actinver-terminal | Oficina funcional de sólo lectura, informe y prompt de comité; referencias y repos locales | Un feed autorizado para cada futuro; LLM sólo si se configura expresamente |
| Quantower | Prompt ampliado con estas referencias y contrato de integración de sólo lectura | Compilar y probar un adaptador C# con el SDK instalado que exporte datos autorizados a los contratos de importación existentes. No se instaló un plugin ni se modificó la plataforma |
| TradingView | Prompt ampliado: contexto y checklist compartidos; separación de análisis externo y Pine | Portar sólo reglas matemáticas compatibles a Pine y validar bar-close, sesiones y rollover. No se publicó ni pegó código en tu cuenta |

Quantower permite indicadores y extensiones C# mediante su SDK: [documentación oficial](https://help.quantower.com/quantower/quantower-algo/introduction). Svelte/React y las apps de oficina no son plugins nativos de Quantower.

Pine obtiene datos mediante las funciones documentadas de `request.*`: [fuente oficial](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/). No se promete ejecutar estas apps Node/Svelte o consultar un endpoint localhost arbitrario desde Pine. Los webhooks salen de TradingView hacia un receptor accesible; no alcanzan automáticamente 127.0.0.1 ni devuelven decisiones al indicador. No se abrió ningún túnel. Comprobar plan, permisos y conexión reales antes de usar footprint o alertas.

## Optimización

Usa [el prompt de optimización](prompt-optimizacion-recursos-claude.md). Define rendimiento como calidad y consumo medidos, no como mayor rentabilidad ni desactivación de protecciones del PC. El mandato vigente sigue siendo sólo lectura/simulación, sin operaciones reales.

## Validación de esta entrega

Cuatro pruebas Node y ocho Python aprobadas. Navegador: se verificaron las seis mesas sin datos, el prompt para Claude y la descarga del JSON sin órdenes. Cinco archivos estáticos respondieron HTTP 200 y el catálogo expone el acceso. No se probaron datos CME en vivo, agentes LLM autónomos ni adaptadores nativos instalados. La prueba Python mostró una advertencia de deprecación Starlette/AnyIO.


### Diseño integrado en la terminal — 19-oct-2026

La oficina reutiliza directamente `web/static/app.css`: misma paleta azul/neutra, Segoe UI, botones, bordes y modo claro/oscuro según el sistema. Se retiraron personajes pixelados, colores decorativos y textura de suelo. Las mesas son filas numeradas con jerarquía de informe; los documentos y la guía ocupan una columna lateral que se apila en móvil. Sin imágenes generadas, fuentes externas ni dependencias nuevas. Cuatro pruebas funcionales existentes aprobadas; consulta y preparación de prompt verificadas en navegador. Escritorio y móvil de 390 px revisados sin desbordamiento horizontal. No se cambiaron las fórmulas ni las fuentes de datos.


### Navegación, catálogo y depuración — 19-oct-2026

Acceso **Oficina** fijo junto a la navegación principal y **Volver a la terminal** en la cabecera de la oficina. Se comprobó que la sección previa se restaura mediante el mecanismo existente de la terminal; no se añadió un historial paralelo.

El instrumento se selecciona de `/api/universo` y del catálogo de `/api/flujo/estado`: unión por identificador exacto, sin duplicados ni instrumentos inactivos, incluidos símbolos importados y sus vencimientos. En la prueba local se mostraron 240 instrumentos. El número depende del catálogo del usuario. Un símbolo catalogado no garantiza datos recientes. Se maneja catálogo parcial/vacío con reintento cuando corresponde. Cambiar instrumento o intervalo invalida el informe anterior y bloquea su exportación; los controles de selección se bloquean durante la consulta para evitar respuestas de otra selección.

Limpieza aplicada: retirados el acceso duplicado a la oficina en el encabezado de Aprender y recursos, el menú interno de anclas, la guía lateral repetitiva, el rótulo duplicado de seis mesas, el pie decorativo y sus reglas CSS sin uso. El campo libre se sustituyó por el selector. Se conservaron procedencia, alcance, errores, exportación y preparación del análisis porque tienen una función comprobable. No se eliminaron datos, repositorios ni cambios de otras sesiones. Esto es una depuración acotada a navegación y oficina, no una afirmación de que toda la terminal haya pasado una auditoría exhaustiva.

El prompt `prompt-auditoria-tecnica-estetica-claude.md` pide auditar e implementar mejoras técnicas y visuales en toda la terminal: mapa de funciones, prioridad de espacios y tareas, controles con propósito, rendimiento, integridad de datos, accesibilidad y eliminación de elementos con evidencia. La auditoría completa está preparada para Claude; no se presenta como ejecutada en esta entrega.

Verificación: seis pruebas Node aprobadas; selector accesible, consulta, invalidación, navegación de ida/vuelta y restauración de sección comprobadas en navegador. Sin errores de consola observados durante la navegación. Escritorio y 390 px sin desbordamiento horizontal.
