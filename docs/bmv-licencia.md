# Precios BMV con licencia: comparación y recomendación (6-oct-2026)

**No se contrató, activó ni pagó nada.** Las cifras son las que publica cada proveedor en su sitio, consultado el
6-oct-2026. Ninguna fuente se ha medido todavía en horario de mercado: el retraso que se anota es el que **declara**
el proveedor. Mientras no haya contrato, la terminal conserva sus etiquetas actuales: cierre BMV de EODHD con su
fecha, SIC como referencia de origen × tipo de cambio y precio del portal del participante.

## Comparación

Cobertura de la BMV en el catálogo del Reto: 48 claves, de las cuales 43 tienen precio del portal del 5-oct y 17
tienen el cierre de EODHD del 2-oct.

| Opción | Datos | Retraso | Historia | Acceso y límites | Condiciones de uso | Costo confirmado |
|---|---|---|---|---|---|---|
| **EODHD gratis** (actual) | Cierres BMV; precio «Live» diferido | Cierre: fin de día. Live: 15–20 min (declarado) | 1 año | REST; 20 peticiones/día, compartidas | Uso personal; «precios indicativos, no aptos para operar» | 0 |
| **EODHD «Historian»** | Cierres BMV y Live diferido; 574 claves .MX | 15–20 min (declarado) | 30+ años | REST; 100,000 peticiones/día | Uso personal; precios indicativos; no es licencia directa de Grupo BMV | **USD 19.99/mes** (16.58/mes anual) |
| EODHD «Active Trader» | Lo anterior + intradía | igual | 30+ años | 100,000/día | Uso personal | USD 29.99/mes |
| **DataBursatil** | Cotizaciones e intradía BMV y BIVA, mercado local y global (SIC) en MXN | 20 min (declarado) | Varios años | REST; 200,000 créditos/mes (1 crédito por KiB); 1 token | **«solo educacional»; los datos «no tienen el fin de ser utilizados para toma de decisiones de inversión»**; no declara licencia con BMV/BIVA; requiere crear cuenta | 0 |
| **Grupo BMV oficial** | Información de cierre (EOD) | Fin de día | — | Correo/FTP o Web Service | Licencia directa; cuota adicional por aplicación automatizada | **USD 240/mes** uso interno, + USD 1,000/mes por aplicación automatizada |
| Grupo BMV oficial | Soluciones Web: capitales, local y global | 20 min | — | Web Service | Licencia directa | **USD 1,080/mes** (+ cuotas de despliegue) |
| Grupo BMV oficial | Feed de capitales con retraso | 20 min | — | Multicast | Licencia de vendor | ≈ USD 1,000/mes uso interno |
| **Infosel** (conector ya programado) | Último hecho y posturas BMV y SIC en MXN | Tiempo real (declarado) | Histórico e intradía | REST v3 con token | Contrato con derechos de BMV | Hub: MXN 1,499 o 2,499/mes; **precio de la API no publicado** (cotización) |
| Twelve Data | BMV (XMEX) | Solo fin de día | — | REST | Personal, no comercial | XMEX no aparece en Basic, Grow ni Pro; Ultra cuesta USD 329/mes (inclusión de XMEX no confirmada) |
| LSEG / ICE | Feed BMV | Según contrato | — | Según contrato | Empresarial | Solo por cotización |

Fuentes:
- [EODHD, precios](https://eodhd.com/pricing), [EODHD, API Live](https://eodhd.com/financial-apis/live-realtime-stocks-api)
  y [EODHD, bolsa MX](https://eodhd.com/exchange/MX).
- [DataBursatil](https://databursatil.com/), su [documentación](https://www.databursatil.com/docs.html) y sus
  [términos](https://www.databursatil.com/terminos.html).
- [Grupo BMV, Market Data](https://www.bmv.com.mx/es/productos-de-informacion/market-data), su
  [lista de precios para vendors 2026](https://www.bmv.com.mx/work/models/Grupo_BMV/Resource/1999/32/images/Lista_de_precios_vendor_BMV_2026.pdf)
  y sus [Web Solutions](https://www.bmv.com.mx/en/information-products/web-services).
- [Infosel, APIs](https://www.infosel.com/apis).
- [Twelve Data, precios](https://twelvedata.com/pricing) y [XMEX](https://twelvedata.com/exchanges/xmex).

## Recomendación concreta

**EODHD «Historian», USD 19.99 al mes, suscrito por usted, durante el Reto (≈ USD 40 hasta el 13-nov).** Razones:
1. Es la única opción barata que resuelve las dos brechas a la vez:
   - historia BMV de 30+ años en lugar de 1 año, lo que permite validar con historia larga también las emisoras
     nacionales (ver `docs/historia-y-horizonte.md`);
   - refrescar a diario las 48 claves BMV: 100,000 peticiones contra 20.
2. Incluye precio diferido de 15–20 minutos. La terminal lo medirá con la hora del evento antes de mostrarlo, y no se
   llamará «tiempo real».
3. Su licencia es de uso personal, que corresponde a un participante individual en un simulador.

Límites que debe aceptar: EODHD no es licencia directa de Grupo BMV y declara sus precios «indicativos». El precio
que manda sigue siendo el del portal del Reto.

Alternativas:
- **Si quiere licencia oficial:** pida cotización de la API a Infosel. El conector ya existe; solo falta el token.
  Grupo BMV directo cuesta al menos USD 1,240 al mes con la cuota por aplicación automatizada: desproporcionado para
  el Reto.
- **No recomendada:** DataBursatil, aunque es gratuita. Sus términos excluyen expresamente el uso para decisiones de
  inversión y no declaran licencia de origen. Además requiere crear una cuenta a su nombre.

## Interfaz preparada (sin contrato)

- `EodhdDiferidoProvider` (`terminal/cotizaciones.py`) con la especificación `config/proveedores/eodhd_diferido.json`,
  verificada contra la documentación pública. Está **apagado**: se activa con
  `EODHD_DIFERIDO_ESPECIFICACION=config/proveedores/eodhd_diferido.json` en `.env`.
  - Con el plan gratuito, cada consulta gasta 1 de las 20 peticiones diarias: sirve solo para medir el retraso en 2 o
    3 emisoras.
  - El retraso se clasifica con la hora del evento (`REAL_TIME`, `DELAYED` o `UNKNOWN`). Sin hora del evento, no hay
    cotización.
  - Pruebas con datos simulados en `tests/test_eodhd_diferido.py`.
- `InfoselProvider` y `BmvLicensedProvider` (ya existentes) esperan su token o especificación de contrato.

## Pendiente de medir

El retraso real de EODHD Live en la BMV no se ha medido: el mercado estaba cerrado y el cupo gratuito es mínimo. Con
el conector activado, 2 o 3 consultas a las 10:00 CDMX registran la latencia en `cotizaciones_registro`, y
`docs/fuentes.md` debe actualizarse con esa cifra medida.
