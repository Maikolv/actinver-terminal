# Confirmación externa de proveedores — 1-nov-2026

**Este documento conserva la revisión documental inicial.** El estado operativo posterior
está en `avance-gratuitos-20261101.md`: SEC ya se verificó por API (incluido XOM con CIK
actual 2115436), y H.15 cubre el dato Treasury 30 años sin clave. Los bloqueos descritos
abajo no deben interpretarse como ausencia actual de esas publicaciones.

Revisión posterior a `proveedores-mesa-20261101.md`. Solo documentación oficial y
referencias publicadas en EDGAR; sin descargar datos a SQLite, activar conectores,
leer `.env`, inventar identificación, comprar, abrir cuentas o enviar mensajes.

## Resultado por pendiente

| ID | Confirmado en esta revisión | Lo que sigue pendiente |
|---|---|---|
| F2 | DGS30 identifica Treasury a 30 años, frecuencia diaria, porcentaje, en FRED | Descarga con la clave de la instalación; no disponible en variables permitidas. La documentación no prueba acceso del conector |
| F3 | La documentación oficial SIE identifica SF61745 como tasa objetivo | GET /series/SF61745 con credencial válida y título coincidente. El HTTP 400 histórico no confirma metadatos |
| F4 | **SP1 está identificado como INPC en publicaciones del propio Banco de México** (fuentes abajo) | Son referencias históricas, no catálogo actual ni respuesta de la API. Falta GET /series/SP1 que confirme título, índice y unidad actuales; no se añade como candidato activo ni se almacena dato |
| F6 | No se obtuvo un código de bono M 10 años suficientemente confirmado en fuente oficial | Seleccionar serie correcta y validar metadatos por API. No confundir expectativa de encuesta, subasta, curva secundaria o UDIBONO; no se inventa ID |
| F1 SEC | Referencias documentales EDGAR para MU/723125, NVDA/1045810, AMD/2488 y XOM/34088 | Confirmar cada par en submissions con ClienteSEC e identificación válida. Las referencias citadas son documentos de emisores de productos estructurados alojados en EDGAR, no respuesta oficial de company_tickers ni validación API de las cuatro compañías |
| F1 Alpha | Documentación de EARNINGS_CALENDAR confirma calendario previsto a 3, 6 o 12 meses | **No se confirma el permiso efectivo de una cuenta** ni datos realizados/revisados con esa descripción. Sigue faltando una única petición autenticada con clave existente |
| F5 | **Cobertura general XMEX no se debe considerar gratuita en Basic**: ficha oficial indica Pro+/Venture+, EOD y GMEXICOB como símbolo de prueba | La excepción de prueba no acredita el mercado completo. Comprobación de una cuenta/símbolo pendiente por falta de clave; no se modifica la cola |

No se elevan búsquedas en terceros a confirmación de catálogo. No se deriva una serie
por semejanza del nombre ni se reemplaza la confirmación por una respuesta simulada.

## Fuentes oficiales y alcance de evidencia

- DGS30: https://fred.stlouisfed.org/series/DGS30
- Tasa objetivo: https://www.banxico.org.mx/SieAPIRest/service/v1/
- INPC/SP1: apéndice de fuentes de un documento de investigación de Banxico,
  https://www.banxico.org.mx/publicaciones-y-prensa/documentos-de-investigacion-del-banco-de-mexico/%7BA06CD25A-E264-9819-A7E7-4AFB197C77B6%7D.pdf
  (página impresa 48: INPC, fuente SIE, serie SP1; periodo histórico 1980–2006).
- Segunda referencia Banxico para SP1:
  https://www.banxico.org.mx/publicaciones-y-prensa/documentos-de-investigacion-del-banco-de-mexico/%7BBE65250B-396D-9E1D-D41D-CB5FA2F15C5C%7D.pdf
  (página impresa 16, nota 15; índice nacional de precios, no confirma base vigente).
- MU/CIK: https://www.sec.gov/Archives/edgar/data/1045520/000191870426000876/form424b2.htm
- NVDA/CIK: https://www.sec.gov/Archives/edgar/data/83246/000110465926055494/tm2613458d10_fwp.pdf
- AMD/CIK: https://www.sec.gov/Archives/edgar/data/83246/000110465925061617/tm2516893d161_fwp.htm
- XOM/CIK: https://www.sec.gov/Archives/edgar/data/1045520/000110465922079897/tm2220148d6_424b2.htm
- Contrato Alpha: https://www.alphavantage.co/documentation/#earnings-calendar
- Cobertura XMEX: https://twelvedata.com/exchanges/XMEX

Las referencias documentales se revisaron mediante el lector y el índice web; no son
consultas de datos de los conectores. No se guardaron valores de indicadores o precios
vistos en esas páginas ni se presentaron como cotizaciones vigentes.

## Bloqueo comprobado sin acceder a secretos de archivos

Se volvió a comprobar únicamente **presencia booleana**, sin imprimir valores, de
BANXICO_TOKEN, FRED_API_KEY, ALPHAVANTAGE_API_KEY, TWELVEDATA_API_KEY y SEC_USER_AGENT:
ausentes en proceso, variables de usuario y variables de máquina de Windows.
No se leyó `.env`, no se recorrieron almacenes de credenciales ni perfiles del navegador.
No se reutilizaron tokens de terceros, claves demo o contactos inventados.

Por ello se hicieron **cero peticiones autenticadas nuevas**, no se repitieron los GET
sin token que ya habían fallado y no se consumieron cupos de datos de Alpha/Twelve.
No se necesita compartir secretos en el chat. La validación operativa seguirá bloqueada
hasta que la instalación disponga de las variables existentes mediante un mecanismo
permitido. Esta revisión no cambia esa restricción ni habilita operaciones.

## Cambios y verificaciones

Solo documentación: este informe y notas en proveedores-gratuitos/pendientes/informe
anterior. Código, configuración efectiva, base de datos y candados sin cambios por esta
revisión. No se vuelven a ejecutar las suites largas por cambios exclusivamente
documentales. Los resultados de pruebas anteriores conservan su fecha y alcance y no
se convierten en comprobaciones de proveedores reales.
