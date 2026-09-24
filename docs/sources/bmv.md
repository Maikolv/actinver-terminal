# BMV — referencia del mercado local

- **Autoridad de precios:** para las acciones mexicanas y todas las series que se negocian en la BMV (incluido el SIC en pesos), la referencia es la **BMV**. El precio debe venir de un producto de datos **licenciado** (por ejemplo, un producto contratado a la BMV o a un distribuidor autorizado) y se coteja con la valuación del simulador.
- **Conector:** `BmvLicensedProvider`. Se configura con una especificación copiada de la documentación del contrato (`docs/proveedores.md`).
- **Estado:** **pendiente**. Faltan el contrato, la documentación técnica, `BMV_API_KEY` y `BMV_URL_BASE`. Sin contrato no se hace ninguna llamada.
- **Latencia verificada:** ninguna.
- **Alternativa temporal:**
  - EODHD da cierres diarios de la BMV con una clave del plan gratuito (EOD, mercado local).
  - Captura o importación manual de precios copiados del portal (`manual_csv`, EOD).
- **SIC:** se guardan por separado la serie en MXN de la BMV, el precio del mercado de origen en USD y el tipo de cambio. La conversión teórica **no** reemplaza un precio negociado en el SIC: un disparador de SQLite rechaza registrar una cotización SIC en USD.
