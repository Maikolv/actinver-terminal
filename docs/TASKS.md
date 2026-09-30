# Tareas — Actinver Terminal

Estado al **30-sep-2026**. Orden por impacto dentro de cada bloque. **Responsable:** «Usuario» (requiere su cuenta, licencia, datos o aprobación) o «Desarrollo» (se puede hacer en el código sin nada externo). Historial detallado: [CHANGELOG.md](../CHANGELOG.md) y [03-plan-implementacion.md](03-plan-implementacion.md).

## Pendientes

| # | Tarea | Responsable | Impacto | Notas |
|---|---|---|---|---|
| 1 | Subir los commits locales pendientes (`git push origin main`) | Usuario | Alto | `fb4a1cf` ya está en GitHub; falta el de esta documentación |
| 2 | Pegar la captura del portal en «Mi cartera → Capturar desde el portal» | Usuario | Alto | Sin ella, el saldo no está conciliado (solo hay 1M local del 28-sep) |
| 3 | Media robusta en el optimizador (acotar saltos únicos como el +175 % de MRNA del 19-ago) | Desarrollo | Alto | Hoy solo los escenarios acotan saltos; la selección todavía se sesga hacia esos casos |
| 4 | Revisar por qué la lente «Máxima puntuación» (70.9) queda por debajo de «Ajuste» (76.4) | Desarrollo | Medio | Incoherencia de nombre o de búsqueda |
| 5 | Contrato de Infosel (URL + JWT) para cotización BMV y SIC | Usuario (licencia) | Alto | Haría ejecutables las boletas del SIC; el conector ya está listo |
| 6 | O bien `TWELVEDATA_API_KEY` (plan Pro) para cierres BMV | Usuario (licencia) | Medio | Cubre 37 de 44 emisoras BMV |
| 7 | Recuperar 22 emisoras BMV sin historia | Automático | Medio | 6 por día con EODHD (≈ 4 sesiones); TERRA13 y SMARTRC no están disponibles |
| 8 | Fuente de catalizadores fechados (reportes trimestrales) | Desarrollo + fuente | Medio | Hoy no hay fechas de reportes por candidato |
| 9 | Spread y liquidez del SIC | Usuario (licencia) | Medio | Requiere cotización BMV/SIC con posturas |
| 10 | Alertas por correo (SMTP en `.env`) | Usuario | Bajo | Telegram ya funciona |
| 11 | `ANTHROPIC_API_KEY` para el chatbot con Claude | Usuario (de pago) | Bajo | Sin clave responde con datos locales |
| 12 | Confirmar con el Comité si los ETF cuentan como «acciones» y cómo aplica el 50 % | Usuario | Bajo | Hoy se advierte en ambos casos |
| 13 | Verificar SEC EDGAR (`SEC_USER_AGENT`) | Usuario | Bajo | No verificado en la última auditoría |
| 14 | Actualizar `config/pdf_transcripcion.csv` si el simulador cambia su lista | Usuario | Bajo | Luego: `uv run terminal catalogo-simulador --confirmar` |

## Hechas recientemente

| Fecha | Tarea |
|---|---|
| 30-sep | Precios ajustados solo por splits en el Reto (el reverse split de FUBO inflaba todas las propuestas) |
| 30-sep | Escenarios al horizonte real del 13-nov, con media contraída y saltos acotados |
| 30-sep | La cabecera no ASCII de la hoja de fondos ya no tira el ciclo |
| 30-sep | Catálogo del simulador aplicado: 169 claves; fuera 10 ETF no vistos y SMARTRC |
| 30-sep | Boletas condicionales (banda ±2 %) sin cotización confiable |
| 30-sep | «🔁 Plan corregido» antes de la apertura; enviado el 30-sep a las 00:09 |
| 29-sep | Plan del día enviado en cuanto hay cierres de la última sesión |
| 29-sep | Acceso remoto privado con Tailscale verificado |
| 29-sep | Hoja oficial de fondos Actinver: 23 de 23 fondos; JPMRVUS serie B-1 |
| 28/29-sep | Bot de Telegram (`/plan /boletas /estado /alertas /cartera /ayuda`) y captura del portal por copiar y pegar |

## Fechas límite

- **2-oct 23:59**: fin de la práctica.
- **4-oct 23:59**: fin de la inscripción.
- **5-oct 07:30**: inicia la competencia. El saldo se reinicia: hay que capturar de nuevo la cuenta del portal.
- **3-nov**: el horario cambia a 08:30–15:00.
- **13-nov 15:00**: cierre de la competencia.
