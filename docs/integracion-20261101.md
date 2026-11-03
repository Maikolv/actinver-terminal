# Recursos del 1-nov-2026: estado verificable

Los tres nuevos posts están registrados en config/reels-20261101.json. Sus descripciones,
videos y repositorios todavía no se pudieron leer. La búsqueda por ID no encontró
resultados; el lector web limitó Instagram y el controlador Windows detuvo el uso al
no poder verificar la URL. No se elude ese control. No se atribuye ninguna técnica,
repositorio, skill ni resultado a esos posts y no se descargan candidatos por conjetura.

OpenTerminal ya está en C:\Users\MIKE\Desktop\Repos\OpenTerminal, commit
aed097c680cd8ec1c391ae06966babe7d6d91fc6. Su estrella ya está presente en la cuenta
GitHub autenticada; se comprobó por API, sin duplicar la acción ni descargar otra copia.
La matriz de widgets previa permanece en docs/terminal-pro-20261101.md; esta entrega
no afirma haber añadido otros widgets procedentes de los reels sin leer.

Se preparó respaldo macro optativo FredMacroLaboral: UNRATE, PAYEMS y CPIAUCSL, con
CPI interanual calculado usando el mismo mes del año previo de la misma captura.
La Mesa conserva BLS para meses iguales/más recientes y muestra la fuente real de
FRED al usar respaldo. No se añade al registro de conectores automáticos ni se
activan fuentes. El usuario autorizó tres consultas adicionales: las tres respondieron
HTTP 200 y se guardaron 81 observaciones. Evidencia:
docs/proveedores-20261101-evidencia/fred-macro-respaldo-20261101.json. Las pruebas
simuladas se distinguen de esa comprobación real.

La lectura de la base real confirmó que ya había BLS del mismo mes para esas tres
variables. Se conservó BLS como fuente; FRED queda como respaldo. No se atribuye el
SIN DATO de una copia aislada sin BLS a la base habitual, ni se afirma resolver BMV.

La consulta pública BLS sin clave recibió HTTP 200, pero su contrato completo no fue
confirmado; no se guardaron observaciones por ese intento. Evidencia saneada:
docs/proveedores-20261101-evidencia/bls-sin-clave-20261101.json. No significa acceso
comprobado ni rechazo HTTP del servicio. Las equivalencias se verificaron en las fichas
oficiales FRED: https://fred.stlouisfed.org/series/UNRATE,
https://fred.stlouisfed.org/series/PAYEMS y https://fred.stlouisfed.org/series/CPIAUCSL.

Revisión posterior: una petición directa oficial sin clave, ventana 2025–2026,
respondió HTTP 200, REQUEST_SUCCEEDED y 21 observaciones por cada una de
CUSR0000SA0, LNS14000000 y CES0000000001. Evidencia:
docs/proveedores-20261101-evidencia/bls-sin-clave-revision-20261101.json.
Confirma acceso para esa petición; no se importaron observaciones ni se activó el
conector. No sustituye el intento anterior fallido ni demuestra la ventana de tres
años que solicita el cliente actual. La documentación oficial de la firma está en
https://www.bls.gov/developers/api_signature_v2.htm.

El conector existente `BLS.consultar` también se verificó con su ventana 2024–2026,
credencial nula y SQLite en memoria: devolvió 32 CPI, 32 desempleo, 33 empleo y
20 CPI interanuales calculados. El contador temporal registró una petición.
Los conteos de filas crudas no se confunden con meses válidos: el conector omite
periodos M13 y valores no numéricos. Intervalo de los resultados válidos:
2024-01 a 2026-09. Evidencia: bls-conector-real-20261101.json en la misma carpeta.
No se cambió código ni se activó el ciclo automático; cero observaciones importadas
a la base habitual. La diferencia de cobertura entre series se conserva.

Regresión offline posterior: `pytest tests/test_centro_investigacion.py -q -k bls`,
dos aprobadas, 25 deseleccionadas, una advertencia de dependencia, 19.75 s,
salida 0. Registro bls-regresion-20261101.txt. Son pruebas simuladas, separadas
de la consulta real. codebase-memory list_projects y check_index_coverage
devolvieron Transport closed; se revisaron directamente centro_conectores.py,
adaptadores/base.py y los casos BLS de test_centro_investigacion.py. No se
atribuye cobertura al grafo ni se modificó código para esta comprobación.

Para Quantower y TradingView se registra la misma lista de recursos en futuros-lab,
sin activar estrategias ni cambiar DLL/Pine a partir de contenido desconocido. El
prompt de optimización está en docs/prompt-optimizacion-recursos-20261101.md y rige
solo investigación, medición y pruebas offline.

Paso manual necesario para los posts: aportar su descripción o los enlaces exactos de
GitHub que aparecen en ellos. Para Twelve, la clave solo se configura por el usuario en
su mecanismo habitual; nunca se pega al chat. La ficha XMEX sigue indicando Pro+/Venture+
y un símbolo de prueba no acredita cobertura general gratuita de BMV.
