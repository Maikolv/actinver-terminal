# Cobertura por símbolo y proveedor

Generado por `uv run terminal cobertura` el 2026-09-24 00:35 (hora local).
Estados: `verificado` (consulta real con instrumento, moneda y mercado exactos), `pendiente` (falta contrato, especificación o credencial), `no_cubierto`, `no_coincide`, `no_aplica`, `sin_verificar`.

Catálogo: **la lista del simulador aún no se importa**; se usa el universo verificado (PDF + fuentes oficiales).

## Proveedores

- **bmv_licenciado** — Producto de datos de Grupo BMV (o distribuidor autorizado) con acceso programático contratado. Pendiente: Contrato de datos de mercado con Grupo BMV o un distribuidor autorizado que permita acceso programático a cotizaciones del mercado local y del SIC (uso no profesional) y su documentación técnica; con la documentación del contrato, crear la especificación (plantilla config/proveedores/ejemplo_especificacion.json) y fijar BMV_ESPECIFICACION; credencial BMV_API_KEY (entregada por el proveedor con el contrato)
- **lseg** — LSEG (Refinitiv) — solo con acceso contratado y documentación verificable. Pendiente: Suscripción LSEG con derechos de la bolsa mexicana (BMV) y documentación de la API contratada; con la documentación del contrato, crear la especificación (plantilla config/proveedores/ejemplo_especificacion.json) y fijar LSEG_ESPECIFICACION; credencial LSEG_API_KEY (entregada por el proveedor con el contrato)
- **ice** — ICE Data Services — solo con acceso contratado y documentación verificable. Pendiente: Contrato ICE con cobertura de la BMV y documentación de la API contratada; con la documentación del contrato, crear la especificación (plantilla config/proveedores/ejemplo_especificacion.json) y fijar ICE_ESPECIFICACION; credencial ICE_API_KEY (entregada por el proveedor con el contrato)
- **eodhd_bmv** — Cierre diario de la BMV en MXN (EODHD); requiere EODHD_API_KEY. Configurado.
- **manual_csv** — Precios y operaciones confirmadas capturados o importados por el participante. Configurado.
- **demo** — Datos ficticios (demostración); jamás representan cotizaciones reales. Pendiente: solo disponible en modo demostración (datos ficticios)
- **referencia_origen** — Precio en la bolsa de origen (USD) — referencia, no cotización BMV. Configurado.
- **extranjero_licenciado** — Proveedor contratado de la bolsa de origen (USD u otra moneda); referencia, no serie BMV. Pendiente: Contrato con un proveedor de datos de la bolsa de origen (NYSE/Nasdaq/otras) que permita uso programático personal, con su documentación; con la documentación del contrato, crear la especificación (plantilla config/proveedores/ejemplo_especificacion.json) y fijar EXT_ESPECIFICACION; credencial EXT_API_KEY (entregada por el proveedor con el contrato)

## Latencia medida

- eodhd_bmv: mediana 34464.0 s, p90 34465.0 s (n=18)

## Tabla

| instrumento_id | clave_operable | mercado | moneda | bmv_licenciado | lseg | ice | eodhd_bmv | manual_csv |
|---|---|---|---|---|---|---|---|---|
| BMV:AC | AC * | local | MXN | pendiente | pendiente | pendiente | verificado | no_cubierto |
| BMV:ACTINVR | ACTINVR B | local | MXN | pendiente | pendiente | pendiente | verificado | no_cubierto |
| BMV:ALFA | ALFA A | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:ALPEK | ALPEK A | local | MXN | pendiente | pendiente | pendiente | verificado | no_cubierto |
| BMV:ALSEA | ALSEA * | local | MXN | pendiente | pendiente | pendiente | verificado | no_cubierto |
| BMV:AMX | AMX B | local | MXN | pendiente | pendiente | pendiente | verificado | no_cubierto |
| BMV:ASUR | ASUR B | local | MXN | pendiente | pendiente | pendiente | verificado | no_cubierto |
| BMV:BBAJIO | BBAJIO O | local | MXN | pendiente | pendiente | pendiente | verificado | no_cubierto |
| BMV:BIMBO | BIMBO A | local | MXN | pendiente | pendiente | pendiente | verificado | no_cubierto |
| BMV:BOLSA | BOLSA A | local | MXN | pendiente | pendiente | pendiente | verificado | no_cubierto |
| BMV:CEMEX | CEMEX CPO | local | MXN | pendiente | pendiente | pendiente | verificado | no_cubierto |
| BMV:CHDRAUI | CHDRAUI B | local | MXN | pendiente | pendiente | pendiente | verificado | no_cubierto |
| BMV:CUERVO | CUERVO * | local | MXN | pendiente | pendiente | pendiente | verificado | no_cubierto |
| BMV:ELEKTRA | ELEKTRA * | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:FEMSA | FEMSA UBD | local | MXN | pendiente | pendiente | pendiente | verificado | no_cubierto |
| BMV:FIBRAMQ | FIBRAMQ 12 | local | MXN | pendiente | pendiente | pendiente | verificado | no_cubierto |
| BMV:FIBRAPL | FIBRAPL 14 | local | MXN | pendiente | pendiente | pendiente | verificado | no_cubierto |
| BMV:FUNO | FUNO 11 | local | MXN | pendiente | pendiente | pendiente | verificado | no_cubierto |
| BMV:GAP | GAP B | local | MXN | pendiente | pendiente | pendiente | verificado | no_cubierto |
| BMV:GCARSO | GCARSO A1 | local | MXN | pendiente | pendiente | pendiente | verificado | no_cubierto |
| BMV:GCC | GCC * | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:GENTERA | GENTERA * | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:GFINBUR | GFINBUR O | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:GFNORTE | GFNORTE O | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:GMEXICO | GMEXICO B | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:GRUMA | GRUMA B | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:KIMBER | KIMBER A | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:KOF | KOF UBL | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:LAB | LAB B | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:LASITE | LASITE B-1 | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:LIVEPOL | LIVEPOL C-1 | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:MEGA | MEGA CPO | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:MFRISCO | MFRISCO A-1 | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:OMA | OMA B | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:ORBIA | ORBIA * | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:PE&OLES | PE&OLES * | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:PINFRA | PINFRA * | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:Q | Q * | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:R | R A | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:SITES1 | SITES1 A-1 | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:SMARTRC | SMARTRC | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:TERRA | TERRA 13 | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:TLEVISA | TLEVISA CPO | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:VESTA | VESTA * | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:VOLAR | VOLAR A | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| BMV:WALMEX | WALMEX * | local | MXN | pendiente | pendiente | pendiente | no_cubierto | no_cubierto |
| FONDO:ACTDUAL | ACTDUAL B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| FONDO:ACTI500 | ACTI500 B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| FONDO:ACTIAI | ACTIAI B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| FONDO:ACTICOB | ACTICOB B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| FONDO:ACTICRE | ACTICRE B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| FONDO:ACTIG+ | ACTIG+ B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| FONDO:ACTIG+2 | ACTIG+2 B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| FONDO:ACTIGOB | ACTIGOB B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| FONDO:ACTIMED | ACTIMED B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| FONDO:ACTIPLU | ACTIPLU B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| FONDO:ACTIREN | ACTIREN B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| FONDO:ACTIVAR | ACTIVAR B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| FONDO:ALTERN | ALTERN B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| FONDO:DINAMO | DINAMO B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| FONDO:ESCALA | ESCALA B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| FONDO:ESFERA | ESFERA B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| FONDO:JPMRVUS | JPMRVUS B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| FONDO:MAXIMO | MAXIMO B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| FONDO:MAYA | MAYA B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| FONDO:OPORT1 | OPORT1 B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| FONDO:ROBOTIK | ROBOTIK B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| FONDO:SALUD | SALUD B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| FONDO:TEMATIK | TEMATIK B | fondo | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:AA1 | AA1 * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:AAL | AAL * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:AAPL | AAPL * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:ABBV | ABBV * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:ABNB | ABNB * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:AFRM | AFRM * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:AGG | AGG * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:AGNC | AGNC * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:AMAT | AMAT * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:AMD | AMD * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:AMZN | AMZN * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:AVGO | AVGO * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:AXP | AXP * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:BA | BA * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:BABA | BABA N | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:BAC | BAC * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:BMY | BMY * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:BRKB | BRKB * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:C | C * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:CAT | CAT * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:CCL1 | CCL1 N | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:CLF | CLF * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:COST | COST * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:CRM | CRM * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:CSCO | CSCO * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:CVS | CVS * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:CVX | CVX * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:DAL | DAL * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:DIS | DIS * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:DVN | DVN * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:ETSY | ETSY * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:F | F * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:FANG | FANG * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:FCX | FCX * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:FDX | FDX * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:FSLR | FSLR * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:FUBO | FUBO * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:GE | GE * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:GM | GM * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:GME | GME * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:GOOGL | GOOGL * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:HD | HD * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:IAU | IAU * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:IEF | IEF * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:INTC | INTC * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:IVV | IVV * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:JNJ | JNJ * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:JPM | JPM * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:KO | KO * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:LCID | LCID * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:LLY | LLY * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:LUV | LUV * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:LVS | LVS * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:MA | MA * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:MARA | MARA * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:MCD | MCD * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:MELI | MELI N | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:META | META * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:MRK | MRK * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:MRNA | MRNA * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:MSFT | MSFT * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:MU | MU * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:NCLH | NCLH N | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:NFLX | NFLX * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:NKE | NKE * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:NU | NU N | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:NVAX | NVAX * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:NVDA | NVDA * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:ORCL | ORCL * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:OXY1 | OXY1 * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:PEP | PEP * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:PFE | PFE * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:PG | PG * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:PINS | PINS * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:PLTR | PLTR * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:PYPL | PYPL * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:QCOM | QCOM * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:QQQ | QQQ * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:RCL | RCL * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:RIOT | RIOT * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:RIVN | RIVN * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:SBUX | SBUX * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:SHOP | SHOP N | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:SHV | SHV * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:SOFI | SOFI * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:SPCE | SPCE * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:T | T * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:TGT | TGT * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:TMO | TMO * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:TSLA | TSLA * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:TSM | TSM N | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:TX | TX * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:UAL | UAL * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:UBER | UBER * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:UNH | UNH * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:UPST | UPST * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:V | V * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:VEA | VEA * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:VNQ | VNQ * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:VOO | VOO * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:VWO | VWO * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:VZ | VZ * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:WFC | WFC * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:WMT | WMT * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:XOM | XOM * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:XYZ | XYZ * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
| SIC:ZM | ZM * | SIC | MXN | pendiente | pendiente | pendiente | no_aplica | no_cubierto |
