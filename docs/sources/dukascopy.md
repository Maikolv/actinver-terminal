# Dukascopy — https://www.dukascopy.com/swiss/spanish/cfd/what-are-cfds/

- **Finalidad obligatoria:** educación y control de clasificación. La página explica que un **CFD** es un contrato por diferencias: un derivado con apalancamiento cuyo precio y riesgos **no equivalen a poseer la acción**.
- **Uso en la terminal:**
  1. Enlace en «Ayuda», sección «CFD y apalancamiento».
  2. **Control** `terminal/clasificacion.py`. Una serie reconocida como CFD (`CFD`, `DUKASCOPY:`, sufijos `.CFD`, índices `USD.IDX`) lanza `InstrumentoNoElegible` y nunca se normaliza a un instrumento del Reto, así que no puede alimentar la valuación de acciones ni ETF. Los mismos controles rechazan criptoactivos con el formato de ccxt (`BTC/USDT`).
- **Qué no es:** esta URL es explicativa. No es un feed bursátil de la BMV.
- **Otros datos de Dukascopy:** no se evaluaron, porque sus derechos de uso y el instrumento concreto no son adecuados para valuar el Reto.
- **Pruebas:** `tests/test_ampliacion.py::test_clasificacion_de_series` y `::test_cfd_y_cripto_rechazados_en_normalizacion`.
