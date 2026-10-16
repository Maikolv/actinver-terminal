# Recursos educativos incorporados — 16 de octubre de 2026

Más → Aprender y recursos reúne los cuatro PDF de Ana Jiménez / Actinver Acelera Academy (página 1 de cada uno), las configuraciones visibles en las capturas de Quantower y los recursos de formación.

## Indicadores

- 2_12.pdf: SMA y EMA, semilla SMA y ponderación 2/(n+1). Al desplazar SMA sale el dato más antiguo.
- 2_1.pdf: MACD = EMA12−EMA26; señal = EMA9 de MACD; histograma = MACD−señal.
- 2_7.pdf: estocástico lento 14/3/3; rango cero indefinido, calentamiento nulo. 20/80 no son órdenes.
- 2_11.pdf: SAR previo + AF × (EP−SAR previo); se aclara el agrupamiento ausente de la fórmula impresa. AF inicial/paso 0.02, máximo 0.2.

Las implementaciones existentes conservan sus reglas; el catálogo explica su interpretación y las precisiones de los PDF. Un cruce no demuestra alfa.

## Order Flow

Las fotos 3–4 muestran dos paneles ES/MNQ de 5 minutos, footprint, perfil lateral y estadísticas de volumen/delta. Order Flow ahora agrupa operaciones guardadas por precio y 5 minutos, separando fuentes/feeds/mercados. El selector muestra bid/ask ejecutado, volumen o delta. Si falta agresor, delta es nulo.

El heatmap de liquidez utiliza hasta 60 snapshots compatibles y 80 precios; no interpola huecos. No equivale a GEX y un cambio de snapshot no permite distinguir cancelación de ejecución. No se identifican ni replican overlays propietarios de las capturas. No se agregan proveedores, credenciales ni ejecución de órdenes.

## Recursos de las fotos 5–10

- [Bookmap: mecánica, DOM y profundidad](https://bookmap.com/learning-center/en/market-mechanics/bookmap-education-course/trading-order-flow-dom-market-depth-trading): curso relacionado oficial.
- [Bookmap: heatmap](https://bookmap.com/learning-center/en/getting-started/liquidity-heatmap/heatmap-overview): documentación del concepto.
- Matt Owen, Start Trading with Orderflow: título/autor y seis videos visibles; URL exacta pendiente.
- [cbrackn: primer video de Order Flow Bootcamp](https://www.youtube.com/watch?v=xT77Go7HK6s): primer video localizado; no se transcribió toda la playlist.
- [Jigsaw: Order Flow Follow Up](https://www.jigsawtrading.com/blog/order-flow-follow-up/): recurso oficial relacionado.
- Andrea Cimi, Complete Orderflow Trading Course For Beginners: título/autor y 22 videos visibles; URL exacta pendiente.

Los conteos son de las capturas. No se afirma haber revisado todas las lecciones. El Artifact local separado contiene ejercicios propios de DOM, adiciones/cancelaciones/ejecuciones, heatmap temporal, medias y estocástico, junto con esta ruta de estudio.

## Certificaciones y privacidad

La foto 1 se transcribe en el catálogo con sus condiciones verificadas. Las letras son una clasificación subjetiva de la infografía; acceso gratuito al curso no garantiza certificado gratuito. CFI ofrece previews, no todo el catálogo y sus certificados gratis; promociones de 2025 no se presumen vigentes en 2026.

La foto 2 es una referencia local sin fecha/moneda/listado confirmados. No constituye cartera ni cotización actual. Sus números se guardan exclusivamente en data/recursos/captura-referencia.json (ignorado por Git), fuera del catálogo público; demo utiliza su propia carpeta. No se publican las imágenes ni los PDF originales.

## Verificación

83 pruebas enfocadas aprobadas: microestructura, separación real/demo, agresor desconocido, límites, API de lectura, indicadores y regresiones de flujo/seguridad. Sintaxis JavaScript comprobada. Se verificaron en navegador el catálogo, replay y medias; no se repitió la suite completa en esta entrega.
