# Monitor de alertas en la nube (Cloudflare Workers Free)

Envía avisos por Telegram aunque la PC esté apagada. La terminal local sigue siendo la fuente del portafolio y de los
cálculos completos: el optimizador no se duplica aquí. La nube conserva solo lo mínimo para vigilar precios, detectar
cambios relevantes y avisar. **No coloca órdenes, no opera y no entra al portal del Reto.**

## Cómo funciona

```
Terminal local (PC encendida)                 Cloudflare Worker (siempre)
 cada 10 min: POST /sync firmado  ───────────▶  D1: último estado, nonces, avisos enviados
   (cartera mínima, umbrales, plan,             cron */15 12-21 UTC lun-vie:
    calendario, FIX, splits)                       ¿la terminal sincronizó hace < 20 min? → pausa (ella avisa)
                                                   si no → Alpaca IEX (1 petición) + FIX Banxico (≤ 1/h)
                                                          → reglas → Telegram (sin duplicados)
```

- **Relevo.** Cada sincronización es un latido. Mientras llegue, la nube no envía nada: la terminal local manda sus
  propias alertas, así que no hay avisos dobles. Si deja de llegar durante 20 min (PC apagada o dormida), la nube toma
  el relevo.
- **Sin competencia con el bot local.** La nube solo usa `sendMessage`. No lee el chat (`getUpdates`), así que los
  comandos `/plan` y `/boletas` siguen funcionando en la terminal.

## Datos y su grado de actualidad

| Dato | Fuente | Cómo se etiqueta |
|---|---|---|
| Listados de EE. UU. (posiciones y plan del SIC) | Alpaca, feed IEX gratuito, 1 petición `snapshots` por ejecución | «IEX en vivo (solo la bolsa IEX, volumen parcial)» si tiene ≤ 15 min; «IEX con N min de retraso»; «último precio IEX de la sesión» con el mercado cerrado |
| Referencia SIC en pesos | precio de EE. UU. × FIX | «referencia SIC = EE. UU. × FIX … (no es precio del SIC)». Nunca se llama «precio del SIC en tiempo real» |
| Tipo de cambio | FIX de Banxico (SIE API), como máximo 1 consulta por hora; si falla, el FIX sincronizado | se usa solo si tiene ≤ 4 días; si no, se suspenden las referencias en pesos |
| BMV y fondos | último cierre sincronizado por la terminal (EODHD o NAV oficial) | «último cierre sincronizado (sin fuente intradía en la nube)». EODHD da 20 consultas al día y las usa la terminal: la nube no las gasta |
| Saldo y posiciones | copia de la última captura del portal | «copia del portal de DD-MM HH:MM — NO es el saldo actual del simulador» |

## Qué se sincroniza (y qué nunca)

**Se sincroniza cada 10 min** con la terminal encendida, en unos 11 KB:
- la cartera: efectivo, por liquidar, valor total, hora de la captura del portal y posiciones (clave, símbolo de EE. UU., títulos, precio de referencia con fuente y fecha);
- los umbrales;
- el último plan: nombre, puntuación, si es vigente y está validado, y por emisora la acción, los títulos, la referencia, el límite y su condición; también las propuestas alternativas de mayor puntuación;
- las sesiones de la BMV y de NYSE de los próximos 14 días, en UTC (con los cambios de horario de EE. UU. y los festivos);
- el último FIX y los splits de los últimos 60 días.

**Nunca viajan:** la base SQLite, `.env`, contraseñas, claves, costos promedio ni documentos o capturas del portal.

Vista previa sin enviar nada: `uv run terminal nube carga`.

## Alertas

| Alerta | Cuándo | Se suspende si… |
|---|---|---|
| Movimiento de una posición SIC | ±3 % frente al cierre previo en EE. UU.; vuelve a avisar en cada 3 % adicional | el dato IEX es de otro día o no hay respuesta; posible split no registrado |
| Variación estimada de la cartera | ±2 % frente a la copia sincronizada | sincronización vencida, copia del portal antigua, sin tipo de cambio o alguna posición sin precio |
| Condición del plan (comprar o vender) | la referencia SIC cruza el límite del plan | el plan no es vigente (> 30 h) o no está validado; la copia del portal tiene más de 30 h o es el registro local; sincronización vencida |
| Cartera sin sincronizar | más de 26 h sin sincronizar, un aviso por episodio y solo en días hábiles | — (suspende las recomendaciones de compra o venta basadas en ese saldo) |
| Falla persistente de datos | Alpaca o Banxico fallan 3 veces seguidas (≈ 45 min); un aviso, y otro al recuperarse | — |
| Posible split o error de datos | cambio ≈ 1/k o k sin split registrado | (no emite señal de precio) |
| Resumen diario | desde 35 min antes de la apertura de la BMV, una vez por sesión | se envía igual, con las suspensiones explicadas |
| Aviso de prueba | lo pide `uv run terminal nube prueba`; sale solo cuando la terminal deja de sincronizar | — |

- **Duplicados.** Cada aviso tiene una clave única en D1 (por ejemplo `mov:SIC:MU:2026-10-01:+1`), así que no se repite aunque el Worker se reinicie o dos ejecuciones se crucen.
- **Telegram.** Los avisos de una ejecución van en un solo mensaje, con 1.1 s entre mensajes. Ante un 429 con `retry_after` ≤ 3 s se espera y se reintenta. Si la espera es mayor, todo queda en cola hasta esa hora; se hacen como máximo 5 intentos.

## Límites y costos verificados (documentación oficial, 1-oct-2026)

| Servicio | Límite del plan gratuito | Uso estimado |
|---|---|---|
| [Workers Free](https://developers.cloudflare.com/workers/platform/limits/) | 100 000 peticiones/día; 10 ms de CPU por invocación; 50 subpeticiones; **5 Cron Triggers por cuenta** | 1 cron, 40 ejecuciones por día hábil y ~150 sincronizaciones/día; ≤ 4 subpeticiones por ejecución; la CPU es mínima (la espera de red no cuenta) |
| [D1 Free](https://developers.cloudflare.com/d1/platform/pricing/) | 5 M filas leídas/día, 100 000 escritas/día, 5 GB, 50 consultas por invocación | menos de 2 000 filas escritas por día |
| Al exceder | [Workers](https://developers.cloudflare.com/workers/platform/pricing/) y D1 devuelven error hasta el reinicio diario (00:00 UTC); **no cobran** | — |
| [Cron Triggers](https://developers.cloudflare.com/workers/configuration/cron-triggers/) | en UTC; los cambios tardan hasta 15 min en propagarse | — |
| [Telegram Bot API](https://core.telegram.org/bots/api#sendmessage) | 4096 caracteres por mensaje; ~1 msg/s por chat; 429 con `retry_after` | pocos mensajes al día |
| Alpaca IEX (gratis) | 200 peticiones/min | ~28 por día |
| Banxico SIE | con token gratuito | ≤ 10 por día |

El plan Workers Free no pide tarjeta ni activa facturación: al llegar a un límite, las peticiones fallan con error y no se cobra.

## Instalación (una vez)

1. Requisitos: Node 22.5 o superior, y `npm install` dentro de `cloud-alerts/`. Wrangler queda como dependencia local; npm 11 pide aprobar los scripts de `esbuild` y `workerd`: `npm approve-scripts esbuild workerd`.
2. **Iniciar sesión en Cloudflare (lo hace usted):** `cd cloud-alerts` y `npx wrangler login`. Se abre el navegador; cree la cuenta gratuita si no la tiene (solo correo, sin tarjeta) y autorice.
3. Desde la raíz del repositorio: `uv run python cloud-alerts/scripts/desplegar.py`. El script:
   - crea la base D1 y aplica la migración;
   - despliega el Worker;
   - carga los secretos desde `.env` con `wrangler secret put`, por la entrada estándar y sin imprimirlos;
   - guarda `CLOUD_ALERTS_URL` en `.env`;
   - genera `CLOUD_ALERTS_SECRET` si falta.
4. Reinicie la terminal: el sincronizador arranca solo si `CLOUD_ALERTS_URL` y `CLOUD_ALERTS_SECRET` están en `.env`.

## Operación

- **En la terminal:** pestaña «Alertas» → «Monitor en la nube» muestra:
  - si está activo o inactivo;
  - la última sincronización, la última ejecución y la próxima revisión;
  - quién envía las alertas ahora;
  - los motivos de las alertas suspendidas.
- **Línea de comandos:**
  - `uv run terminal nube estado` muestra el estado del monitor;
  - `uv run terminal nube sincronizar` sincroniza ahora;
  - `uv run terminal nube prueba` pide un aviso de prueba, que llega solo cuando la terminal está cerrada ≥ 20 min en día hábil.
- **Registros de Cloudflare:** `npx wrangler tail`. Los registros no contienen montos ni secretos.

## Desactivación

- Pausar sin borrar: `uv run python cloud-alerts/scripts/desplegar.py --desactivar` (quita el cron).
- Borrar el Worker: `npx wrangler delete`. Borrar los datos: `npx wrangler d1 delete actinver-alertas`.
- En la terminal: `[nube] activo = false` en la configuración, o quite `CLOUD_ALERTS_URL` de `.env`.

## Pruebas

- `npm test` corre 19 pruebas del Worker (Node `node:test`, con D1 simulada sobre `node:sqlite` y la misma migración SQL). Cubren:
  - firmas inválidas, reenvíos, ventana de tiempo, secuencia y tamaño;
  - cartera y precios vencidos, y caída de un proveedor;
  - MXN/USD y la referencia SIC, y splits;
  - fines de semana, festivos y horario de verano;
  - duplicados, el 429 de Telegram y la convivencia con la terminal local.
- `uv run pytest tests/test_nube.py` comprueba la carga mínima y que la firma Python coincide con la del Worker (vector compartido `test/vector_firma.json`). También valida la carga real con el validador del Worker.
- **Prueba local:** `npm run migrar:local` y `npm run dev`, con `.dev.vars`, que está ignorado por Git. El cron se dispara con `curl "http://127.0.0.1:8787/cdn-cgi/handler/scheduled?cron=*/15+12-21+*+*+1-5"`.

## Qué se reutilizó

- **Nada copiado de repositorios externos.** [cloudflare/workers-sdk](https://github.com/cloudflare/workers-sdk) solo sirvió de referencia para Wrangler y las pruebas locales; Wrangler se instala desde npm.
- **Repositorios locales revisados:** `agentic-inbox` es un Worker de correo con Durable Objects, R2 y Workers AI; no contiene una función compatible y necesaria, así que no se usó.
- **De la terminal:** la firma HMAC sigue el patrón del webhook de TradingView; el calendario, el plan de acción, la cartera conciliada y las etiquetas de vigencia salen de sus propios módulos (`vigencia`, `plan_accion`, `servicios`).
