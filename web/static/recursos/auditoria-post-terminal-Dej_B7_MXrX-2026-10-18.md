# Cómo se aplicó el reel de la mini terminal

Revisión: 18 de octubre de 2026. Post: [chrispathway — Dej_B7_MXrX](https://www.instagram.com/p/Dej_B7_MXrX/).

La aplicación comprobada del reel es educativa y de evaluación de herramientas: se incorporó su ficha al catálogo de la terminal, se identificaron y clonaron yfinance y FinBERT y se ejecutaron demostraciones aisladas. **No se reprodujo dentro de actinver-terminal toda la arquitectura del video.** FRED y SEC ya tenían integraciones anteriores, con un alcance distinto del que presenta el reel. La terminal no obtiene rentabilidad por haber añadido estos recursos.

## Matriz de aplicación real

| Elemento del reel | Estado comprobado | Dónde se usa y diferencia concreta | Evidencia/prueba |
|---|---|---|---|
| Mercado mediante yfinance | Instalado y probado fuera de la terminal; integración propuesta | Copia local `C:/Users/MIKE/Desktop/Repos/yfinance` y entorno aislado `work/finanzas-17-env`. La demostración anterior consultó 5 días de OHLCV de MSFT. No es el proveedor de precios de la terminal. | `terminal/ingesta.py:17` fija la prioridad Tiingo/Alpaca/Barchart/EODHD/TwelveData. `terminal/adaptadores/__init__.py:4` registra los adaptadores; no incluye yfinance. `pyproject.toml:6` no declara yfinance. Informe de ejecución del 17 de octubre. |
| Fundamentales SEC EDGAR | Integración previa, parcial frente al reel | El código actual descarga **Formulario 4 de insiders**, exige `SEC_USER_AGENT` y registra operaciones de emisoras de EE. UU. No equivale a estados financieros ni a balances XBRL Company Facts. | `terminal/fuentes_web.py:135`, `:153`, `:162`, `:289`. Pruebas `tests/test_fuentes_web.py:54` y `:60`. |
| FRED macroeconómico | Integración previa y funcionalidad de contexto | USD/MXN DEXMXUS por CSV/API y, en Investigación, DGS10, DGS2, FEDFUNDS e INDPRO. La lista actual no incluye una serie de inflación en ese conector; el calendario macro es otra fuente. Configuración y vigencia del dato siguen siendo necesarias. | `terminal/adaptadores/proveedores.py:13`, `:27`; `terminal/centro_conectores.py:44`; `tests/test_adaptadores.py:25`, `:94`; `tests/test_centro_investigacion.py:142`. |
| Yahoo Finance para titulares | Propuesta; no integración observada en el flujo auditado | Las noticias actuales se obtienen por Seeking Alpha RSS. Importar un CSV con columnas de Yahoo no constituye conexión a sus titulares ni una autorización de uso de datos. | `terminal/fuentes_web.py:96`, `:254`, `:277`; `terminal/ingesta.py:208`. |
| FinBERT para sentimiento | Instalado y demostrado fuera de la terminal; integración pendiente | La demo anterior clasificó tres frases sintéticas localmente. La terminal actual clasifica con reglas léxicas y, opcionalmente, Ollama; no llama FinBERT en este flujo. | `terminal/fuentes_web.py:30`, `:41`, `:47`, `:273`; informe de ejecución y modelo aislado. La búsqueda en `terminal`, `config`, `tests` y dependencias solo localizó FinBERT en el catálogo educativo. |
| Paneles integrados y base de datos | Capacidad previa; relación educativa añadida | Noticias, insiders y contexto ya se guardan en SQLite. La ficha del reel pide abrir Mercado e Investigación y documentar fuente/retraso. No se obtuvo el proyecto privado de Replit ni se puede asegurar equivalencia con él. | `terminal/fuentes_web.py:280`, `:306`; `config/aprendizaje.json:111`; `terminal/aprendizaje.py:7`; `web/static/app.js:2735`. |
| Alfa o decisiones automáticas | No demostrado | No hubo prueba que relacione las probabilidades de sentimiento con retornos futuros ni evaluación fuera de muestra de esta combinación. Los conectores de contexto no envían órdenes. | `terminal/fuentes_web.py:10`; límites explícitos del informe de ejecución del 17 de octubre. |

## Qué cambió realmente a raíz del reel

1. **Catálogo visible:** la ficha “Terminal con datos gratuitos” enlaza el post, enumera sus cinco recursos, advierte sobre licencias y propone un ejercicio de trazabilidad (`config/aprendizaje.json:111–120`). El catálogo se carga desde JSON y se presenta mediante `/api/aprendizaje` (`terminal/aprendizaje.py:7`, `web/static/app.js:2735`).
2. **Evaluación local:** se clonaron yfinance y FinBERT, se añadieron/confirmaron estrellas según el registro previo y Claude Code ejecutó la demostración descrita en [el informe del 17 de octubre](./claude-ejecucion-yfinance-finbert-2026-10-17.md). Esta auditoría leyó el informe y comprobó que existen ambas carpetas; no volvió a consultar GitHub ni a descargar datos/modelos.
3. **Documentación:** la aplicación y los límites quedaron reflejados en `docs/instagram-2026-10-17.md` y `docs/historial-estado.md:232`. Esto no añade por sí solo un nuevo proveedor al motor.

## Qué ya existía antes

El historial de Git muestra que `terminal/fuentes_web.py` tuvo su último cambio registrado el 29 de septiembre (`9945f1f`) y `terminal/centro_conectores.py` el 12 de octubre (`3910c6e`), antes del trabajo del 17 de octubre. Se comprobó además que `clasificar_titular`, `SecEdgar` y `FredMacro` existían en el padre del commit `38bab651`. No corresponde atribuir la creación de esas integraciones al reel.

## Lo que falta para reproducir la idea completa

- Resolver permisos de los datos Yahoo antes de conectar yfinance al motor, y añadir pruebas de ajustes, dividendos, huecos, zonas horarias, procedencia y vigencia. El código abierto de la biblioteca no concede derechos sobre los datos.
- Si se desean estados financieros SEC, crear un conector específico XBRL/Company Facts, con unidades, periodos, revisiones y fecha de disponibilidad. Formulario 4 no lo sustituye.
- Seleccionar y verificar series FRED adicionales, por ejemplo inflación, si la investigación las necesita. Revisiones macro requieren tratamiento temporal apropiado para backtests.
- Definir una fuente autorizada de titulares y registrar fecha de publicación, obtención y deduplicación.
- Resolver la licencia de los **pesos** FinBERT y validar su desempeño en un conjunto separado de noticias. La licencia Apache del código y CC-BY-NC-SA de los pesos son condiciones diferentes. No se habilitó su uso comercial ni en un bot de fondeo.

Estas son propuestas verificables; no se implementaron como parte de esta auditoría.

## Alcance y verificación

Se usó la skill `codebase-memory`: búsqueda de símbolos, cobertura de doce archivos y ámbitos `terminal`/`tests`, seguida de lectura directa de las fuentes. El grafo corresponde al 24 de septiembre y marca varios archivos como cambiados/no registrados, además de excluir `web/static`; por eso las conclusiones materiales se apoyan en el código actual, no en ausencias del grafo.

La transcripción automática del reel confunde algunos nombres (por ejemplo “FinBird”); se tomó la interpretación ya contrastada en el informe anterior y no se presenta la transcripción como cita literal. La auditoría no contactó brokers, no usó cuentas de trading, no alteró código ni consultó secretos. Se revisó la presencia de pruebas unitarias con respuestas simuladas. Se intentó ejecutar `tests/test_adaptadores.py`, `tests/test_fuentes_web.py` y `tests/test_centro_investigacion.py` con el Python de `.venv`; el proceso no produjo resultados de pytest durante la espera y se detuvo. **Esta auditoría no certifica que esas pruebas hayan aprobado hoy**; su presencia y contenido se comprobaron mediante lectura. No se diagnosticó la causa del bloqueo.

Fuentes locales auditadas: repositorio `C:/Users/MIKE/Desktop/Repos/actinver-terminal`; transcripción `work/instagram-17/Dej_B7_MXrX.txt`; informes `outputs/instagram-2026-10-17.md` y `outputs/claude-ejecucion-yfinance-finbert-2026-10-17.md` de este espacio de trabajo. Las líneas corresponden al estado local del 18 de octubre; pueden cambiar con ediciones posteriores.
