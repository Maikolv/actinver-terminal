# 09 · Auditoría de «Datos Actinver.pdf»

Archivo: `C:\Users\MIKE\Desktop\Datos Actinver.pdf` · 11 páginas · creado con Word 2013 el 2026-09-22 13:49 (−06:00) · sin capa de texto (solo capturas de pantalla). No se copió al repositorio; los renders de revisión quedaron en `_privado/` (ignorado por Git).

## Revisión página por página

| Página | Rótulo | Contenido | Símbolos |
|---|---|---|---|
| 1 | Acciones | 3 tablas «Último precio» (columnas: Emisora, Precio, % Variación, Volumen/Precio de compra, Volumen/Precio de venta, Operar) | AA1 * … CCL1 N (30) |
| 2 | — | 2 tablas | CEMEX CPO … FEMSA UBD (20) |
| 3 | — | 3 tablas | FIBRAMQ 12 … LLY * (30) |
| 4 | — | 3 tablas | LUV * … PINFRA * (30) |
| 5 | — | 3 tablas | PINS * … VZ * (30) |
| 6 | Acciones / **ETF's** | Fin de acciones: WALMEX * … ZM * (6). Bajo «ETF's»: AA1 * … BA * (20) | 26 |
| 7 | ETF's | BABA N … FEMSA UBD (30) | 30 |
| 8 | ETF's | FIBRAMQ 12 … LLY * (30) | 30 |
| 9 | ETF's | LUV * … PINFRA * (30) | 30 |
| 10 | ETF's | PINS * … VZ * (30) | 30 |
| 11 | ETF's / **Fondos** | WALMEX * … ZM * (6); tabla de fondos (Fondo, Categoría, Precio, 1 año, 3 años, 5 años) | 6 + 23 fondos |

Transcripción reproducible: `scripts/transcribir_pdf.py` → `config/pdf_transcripcion.csv` (315 filas: 146 + 146 + 23). No se transcribieron precios.

## Hallazgos

1. **La sección «ETF's» no contiene ETF.** Repite en el mismo orden las 146 claves de «Acciones», capturadas en otro momento (volúmenes y algunos precios difieren, p. ej. AAPL 5,890.00 vs 5,880.93). Verificación: 0 de 146 tienen bandera ETF=Y en Nasdaq Trader (`tests/test_universo.py`).
2. **Precios históricos en MXN.** Son del momento de la captura (hora no visible). La terminal no los usa ni los muestra como cotización.
3. **Mezcla de clases dentro de «Acciones».** 4 FIBRA (FIBRAMQ, FIBRAPL, FUNO, TERRA: certificados CBFI, no acciones), 1 REIT de EE. UU. (AGNC), ADR (BABA, TSM, TX…) y emisoras locales con serie «*» (WALMEX *, ORBIA *…). La serie «*» no indica por sí misma que sea extranjera.
4. **Claves no vigentes.** CPE (Callon, adquirida por APA en 2024) y MRO (Marathon Oil, adquirida por ConocoPhillips en 2024) no figuran en el directorio actual; en la captura tienen volumen 0.
5. **Claves reasignadas.** GOLD hoy es «Gold.com, Inc.» (Barrick cotiza como B); PARA hoy es «Banzai International» (Paramount Skydance cotiza como PSKY). Un cruce solo por clave asignaría precios de otra empresa.
6. **Emisoras BMV por confirmar.** ALFA no está en el listado vigente de emisoras de la BMV (sí SIGMAF, Sigma Foods); ELEKTRA tampoco figura. Ambas excluidas hasta confirmar.
7. **Emisoras sin posturas** en ambos lados en la captura (ALFA, CPE, ELEKTRA, GOLD, LASITE, MRO, PARA, TERRA) o en uno de ellos (AA1, ETSY, FANG): señal de baja liquidez en el SIC/BMV en ese momento; no se usa como dato, se documenta.
8. **Fondos**: 23 fondos Actinver. La columna «1 año» muestra 0.00 % en todos (dato no poblado en la pantalla); «3 años» y «5 años» tienen valores. Clasificación verificada en actinver.com: 11 de deuda (4 primaria, 4 especializada, 3 en dólares), 1 multiactivo, 11 de renta variable (3 local, 8 global). ACTIG+ y ACTIG+2 compran/venden **anualmente** y MAXIMO **trimestralmente**: restricción de liquidez aplicada en las propuestas.
9. **Clave abreviada en la captura**: «ACTIA?» corresponde a ACTIAI según el menú oficial de fondos.
10. **Datos personales**: el PDF marca favoritos (estrellas). No se transcribieron. No hay números de cuenta ni tenencias; la terminal no deduce posiciones del PDF.

## Qué se tomó del PDF y qué no

| Se usó | No se usó |
|---|---|
| Claves y series como lista de descubrimiento | Precios, volúmenes, variaciones (históricos) |
| Nombres de fondos | Rendimientos 1/3/5 años (incompletos y sin fecha) |
| Estructura de columnas para entender el origen (plataforma de Actinver) | Favoritos del usuario |
