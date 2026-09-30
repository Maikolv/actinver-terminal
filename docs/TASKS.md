# Tareas — Actinver Terminal

Estado al **30-sep-2026, 14:40 CDMX** (auditoría v0.14.0). Orden por impacto dentro de cada bloque. **Responsable:** «Usuario» (requiere su cuenta, licencia, datos o aprobación) o «Desarrollo» (se puede hacer en el código sin nada externo). Historial detallado: [CHANGELOG.md](../CHANGELOG.md) y [03-plan-implementacion.md](03-plan-implementacion.md).

## Pendientes

| # | Tarea | Responsable | Impacto | Notas |
|---|---|---|---|---|
| 1 | Probar la URL `.ts.net` desde el celular u otro dispositivo con Tailscale | Usuario | Alto | Solo se probó desde esta misma PC (200); el acceso con la PC apagada requiere un anfitrión permanente (`docs/acceso-siempre-disponible.md`) |
| 2 | Pegar la captura del portal en «Mi cartera → Capturar desde el portal» | Usuario | Alto | Sin ella, el saldo no está conciliado (solo hay 1M local del 28-sep) |
| 3 | Decidir el criterio de la propuesta de referencia del plan del día | Usuario (decisión) | Alto | Hoy es la de mayor puntuación («Acciones · Máxima puntuación», 73.0), que fuera de muestra rindió +1.1 % anual contra +10.8 % del 1/N; la puntuación premia riesgo bajo y calidad de datos, no la ganancia absoluta que gana el Reto |
| 4 | Ampliar la validación fuera de muestra (hoy 84 sesiones en las propuestas principales) | Desarrollo + datos | Alto | La ventana común la acorta la emisora con menos historia; con EODHD gratuito se amplía poco a poco |
| 5 | Contrato de Infosel (URL + JWT) para cotización BMV y SIC | Usuario (licencia) | Alto | Haría ejecutables las boletas del SIC; el conector ya está listo |
| 6 | O bien `TWELVEDATA_API_KEY` (plan Pro) para cierres BMV | Usuario (licencia) | Medio | Cubre 37 de 44 emisoras BMV |
| 7 | Recuperar 22 emisoras BMV sin historia | Automático | Medio | 6 por día con EODHD (≈ 4 sesiones); TERRA13 y SMARTRC no están disponibles |
| 8 | Fuente de catalizadores fechados (reportes trimestrales) | Desarrollo + fuente | Medio | Hoy no hay fechas de reportes por candidato |
| 9 | Spread y liquidez del SIC | Usuario (licencia) | Medio | Requiere cotización BMV/SIC con posturas |
| 10 | Alertas por correo (SMTP en `.env`) | Usuario | Bajo | Telegram ya funciona |
| 11 | `ANTHROPIC_API_KEY` para el chatbot con Claude | Usuario (de pago) | Bajo | Sin clave responde con datos locales |
| 12 | Confirmar con el Comité si los ETF cuentan como «acciones» y cómo aplica el 50 % | Usuario | Bajo | Hoy se advierte en ambos casos |
| 13 | Marcar como revisada la versión 3 de las reglas en «Reto y perfil» | Usuario | Bajo | Aparece porque `config/reto.yaml` cambió (fecha de consulta y redacción del criterio); las reglas numéricas no cambiaron |
| 14 | Actualizar `config/pdf_transcripcion.csv` si el simulador cambia su lista | Usuario | Bajo | Luego: `uv run terminal catalogo-simulador --confirmar` |

## Hechas recientemente

| Fecha | Tarea |
|---|---|
| 30-sep | Horario BMV del Reto (07:30–14:00) en vez del de la librería (08:30–15:00) |
| 30-sep | Media robusta (MRNA fuera) y escenarios con la volatilidad fuera de muestra |
| 30-sep | Ranking limitado al catálogo; alerta de plan que reemplaza la anterior; respaldo diario verificado |
| 30-sep | Iniciador: arranca en local si falla Tailscale; lanzador `.exe` probado apagado/encendido |
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
