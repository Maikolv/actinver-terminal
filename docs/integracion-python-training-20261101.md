# Python Training: incorporación del 1-nov-2026

Repositorio oficial descargado una sola vez en `C:\Users\MIKE\Desktop\Repos\python-training`, commit `0c536090508181dcfcd64fbcfbfa507cda2db93c`, Apache-2.0. README y diez notebooks revisados sin ejecutar código upstream ni leer archivos .env. La skill codebase-memory se consultó pero su herramienta no está disponible en esta sesión: fallback acotado con rg y lectura directa; no se declara cobertura de grafo.

## Qué mejora

- Actinver: módulo puro terminal/formacion_python.py y práctica ejecutable de series. Fuente/etiqueta obligatorias, precios positivos finitos, orden temporal, sin mezclas silenciosas, rendimiento/volatilidad descriptivos y drawdown. No cambia cartera, optimizador ni señales.
- Futuros Lab: módulo puro futuros_lab/formacion_python.py, que reutiliza SPECS, y práctica de integridad de velas/contrato fechado. Sin red, estrategia ni dependencia del motor. Un resultado válido NO acredita forward ni continuidad del feed.
- Cuaderno financiero: sección «04 · Python aplicado» dentro del mismo Cuaderno (antes página aparte), con ejemplo sintético, descarga del notebook y CSV, guía de estudio y retorno a la terminal. Estilo heredado de app.css, sin sobrescribir la paleta de otra sesión.
- Referencias y manifiestos: identidad, commit, hashes, licencia y alcance. No se afirma que JPMorgan avale Actinver o que el repositorio otorgue certificado; no se añadió como certificación al PDF.

## Reutilización segura

No se copia código upstream ni logos del banco; la licencia original se conserva en el clon. Los ejemplos integrados son propios y se vinculan a los temas educativos. No se instala Pipfile: solicita Python3.11 y un conjunto amplio de bibliotecas; los proyectos usan sus entornos actuales. No se ejecutan 4_webapi, 5_website ni 6_financial_data originales: pueden requerir red/clave. Ninguna clave fue solicitada. La disponibilidad actual de los servicios de esos notebooks no se acredita.

Los notebooks propios se ejecutaron celda por celda mediante los intérpretes existentes con conexiones de socket bloqueadas; resultado en docs/formacion-python-jpm-ejecucion.json. No se afirma haber validado JupyterLab interactivo; no se instaló Jupyter. Para repetir, abre cada notebook desde su proyecto con un kernel de su entorno, o ejecuta su celda Python desde la raíz.

## Ruta sugerida según contenido real

0_best_practices y 1_basic: higiene de código y conceptos; 2_straddle: payoff de opciones, no estrategia rentable; 3_flights: manipulación de tablas como ejercicio general; 4_webapi y 5_website: lectura crítica de APIs/HTTP sin activar scraping; 6_financial_data: series y procedencia; 7_advanced_plotting y 9_3d_plotting: visualización; 8_altman_z_double_prime: análisis de empresas, no calibración directa de futuros NQ.

Las funciones son utilidades de estudio aisladas, no conectores nuevos ni cambios en los cálculos productivos. Backtests, Quantower, TradingView, broker, Telegram y candados no se modifican. La incorporación no demuestra alfa ni autoriza ningún trade, tampoco demo.

## Verificación de la entrega

- Actinver: diez pruebas del módulo de series aprobadas; cinco pruebas de referencias aprobadas en la comprobación conjunta anterior.
- Futuros Lab: once pruebas de integridad aprobadas.
- Guías/navegación: nueve pruebas Node aprobadas, conservando cambios previos de otras sesiones.
- Dos notebooks propios ejecutados de nuevo con sus intérpretes existentes y red bloqueada; no se ejecutó el código del curso original.
- Navegador aislado: seis vistas claro/oscuro a 390/768/1440 px, acceso desde Cuaderno, notebook descargable, cero errores JS y sin desbordamiento. Caso adicional de JSON ausente muestra SIN DATO sin consultar otro proveedor. Capturas y ui.json en docs/formacion-python-jpm-evidencia/.
- No se repitió la suite completa de modelos: solo se añaden módulos educativos aislados, sin cambiar sus algoritmos ni importarlos en el motor.
- Fuente upstream intacta y clon único; commit 0c536090508181dcfcd64fbcfbfa507cda2db93c. Sin compra, certificados atribuidos ni instalación de dependencias.
