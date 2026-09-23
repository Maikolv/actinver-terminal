# Proveedores de precios: instalación y configuración

Todas las fuentes implementan la interfaz `MarketDataProvider` (`terminal/cotizaciones.py`) y se configuran con variables de entorno en `.env`, que Git no versiona. Hay una plantilla en `.env.example`. **Ninguna** fuente se da por buena solo por lo que anuncia: se usa para un instrumento únicamente si `uv run terminal cobertura` (o el botón «Verificar cobertura» en «Datos») confirma **ese instrumento exacto**, con su serie, en MXN y en su mercado (BMV local o SIC). Cada cotización se etiqueta con la latencia **medida**: `REAL_TIME` (≤ 15 s), `DELAYED` (≤ 20 min), `EOD` (cierre diario) o `UNKNOWN`.

Si ninguna fuente verificada entrega un precio vigente, el PRESENTE muestra **SIN PRECIO CONFIABLE**. El precio de la bolsa de origen en USD (Alpaca o Tiingo) aparece aparte como «referencia externa». Nunca sustituye en silencio a la cotización del SIC en la BMV.

## Estado al 23-sep-2026

| Proveedor | Clase | Estado | Qué falta |
|---|---|---|---|
| Producto BMV con licencia | `BmvLicensedProvider` | **Pendiente** | Contrato con Grupo BMV o un distribuidor autorizado que permita acceso programático a cotizaciones del mercado local y del SIC; su documentación técnica (para escribir la especificación); `BMV_API_KEY` y `BMV_URL_BASE` |
| LSEG | `LsegProvider` | **Pendiente** | Suscripción con derechos de la BMV, documentación de la API contratada, `LSEG_*` |
| ICE | `IceProvider` | **Pendiente** | Contrato con cobertura de la BMV, documentación, `ICE_*` |
| EODHD (cierres de la BMV) | `EodhdBmvProvider` | **Pendiente** | `EODHD_API_KEY` (el plan gratuito da 20 peticiones al día); solo cubre el mercado local, siempre EOD |
| Captura o CSV del participante | `ManualOrCsvProvider` | **Funciona** | Nada. Importe precios, operaciones y posiciones desde «Mi cartera → Importar» (hay ejemplos en `ejemplos/`) |
| Demostración | `DemoProvider` | Funciona solo en modo demo | Datos ficticios en una base separada; nunca se mezclan con los reales |
| Alertas de TradingView | `TradingViewAlertReceiver` | **Implementado, sin conectar** | Secreto (`uv run terminal webhook-secreto`) y un túnel HTTPS público propio (vea abajo) |
| Referencia de origen (Alpaca/Tiingo) | `ReferenciaOrigenProvider` | Funciona si hay precios | Solo es referencia en USD; no es la cotización BMV |

## Conectores contratados (BMV, LSEG, ICE)

La terminal **no inventa endpoints**. Cuando tenga el contrato:

1. Copie `config/proveedores/ejemplo_especificacion.json` a `config/proveedores/bmv.json` (o `lseg.json`, `ice.json`).
2. Llene cada campo con lo que diga la documentación técnica de su contrato:
   - la ruta de cotización con `{simbolo}`;
   - la autenticación: cabecera o parámetro;
   - la ruta, dentro del JSON de respuesta, del precio, la moneda, la hora del evento, la bolsa y el símbolo;
   - la plantilla de símbolos o el mapa `mapa_simbolos`.
3. En `.env`: `BMV_ESPECIFICACION=config/proveedores/bmv.json`, `BMV_URL_BASE=…` y `BMV_API_KEY=…`.
4. Ejecute `uv run terminal cobertura`. Para cada instrumento del catálogo verá una de estas situaciones:
   - `verificado`: la consulta real devolvió el instrumento con la moneda y el mercado correctos;
   - `no_coincide`: devolvió otra moneda u otro mercado, por ejemplo un SIC en USD;
   - `no_cubierto`: el proveedor falló o no tiene el símbolo.

   La latencia verificada es la **medida** en esas consultas.
5. Si su contrato es por *streaming* (WebSocket o FIX), la especificación REST no basta: comparta la documentación y se añade un adaptador de flujo con reconexión, siguiendo el modelo de `terminal/tiempo_real.py`.

Para las fuentes contratadas se aplican estas protecciones:

- **Reconexión:** reintentos con espera exponencial.
- **Límite de consultas:** por minuto, configurable por clase.
- **Caché:** 2 s para las fuentes contratadas.
- **Métricas:** solicitudes, fallos, fallos consecutivos y último error, en la tabla `metricas_proveedor`.
- **Conmutación:** se pasa a otra fuente solo si también tiene cobertura verificada del mismo instrumento.
- **Credenciales:** los errores registran el tipo de fallo, nunca la URL con la clave.

## Webhook de TradingView (eventos de alerta)

TradingView puede avisar a una URL cuando se dispara **una alerta que usted configuró**. La terminal trata esos avisos como **eventos**, no como fuente de precios. No los consulta de forma continua y no alimentan la valuación.

1. Ejecute `uv run terminal webhook-secreto`. Genera `TRADINGVIEW_WEBHOOK_SECRETO` en `.env`.
2. TradingView necesita una URL **pública HTTPS**, y la terminal solo escucha en `127.0.0.1`. Exponerla requiere un túnel propio (por ejemplo, Cloudflare Tunnel) hacia `http://127.0.0.1:8765/webhook/tradingview`. Esa decisión es suya: añada el dominio del túnel en `TRADINGVIEW_WEBHOOK_HOSTS`. Solo esa ruta acepta ese Host. Opcionalmente, active `TRADINGVIEW_VERIFICAR_IP=1` para aceptar solo las IP de webhook que publica TradingView; verifique en su documentación que la lista esté vigente.
3. En la alerta, use como mensaje el JSON de `ejemplos/alerta_tradingview.json` con su secreto.

La terminal valida cada evento:

- **Secreto:** comparación en tiempo constante.
- **Símbolo:** debe pertenecer al catálogo y, si lo importó, a la lista del simulador.
- **Moneda:** debe coincidir con la del instrumento.
- **Hora:** no puede estar en el futuro ni tener más de 300 s.
- **Duplicados:** se detectan por su huella y no se registran dos veces.
- **Precio:** debe ser finito y positivo; si se aleja más de 30 % de la última referencia, se acepta marcado como «atípico».

El precio del evento se registra como `UNKNOWN`: TradingView no declara con qué retraso le entrega la BMV según su plan, y `{{timenow}}` es la hora de la alerta, no la del evento de mercado. Cada evento genera una alerta «REVISAR».

## Lo que la terminal nunca hace

- No inicia sesión en el portal del Reto.
- No extrae datos del portal ni registra, modifica o cancela órdenes. El reglamento §17 prohíbe robots, scripts y macros.
- No usa `ccxt`, `freqtrade`, `hummingbot`, `nautilus_trader` ni la API de operaciones de ningún bróker.
