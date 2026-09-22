# 12 · Seguridad y privacidad

## Modelo de amenaza (uso local)

Un solo usuario en su PC. Riesgos principales: (1) una página web maliciosa abierta en el mismo navegador que intente llamar a `127.0.0.1:8765` (CSRF, *DNS rebinding*), (2) fuga de credenciales de proveedores por registros o Git, (3) archivos importados manipulados, (4) contenido del usuario interpretado como HTML (XSS), (5) pérdida de datos.

## Controles aplicados

| Control | Implementación | Prueba |
|---|---|---|
| Solo red local | Uvicorn en 127.0.0.1; el CLI rechaza otro host | `terminal/__main__.py` |
| *DNS rebinding* | Cabecera Host debe ser `127.0.0.1`, `localhost` o `[::1]` | `test_host_no_local_rechazado` |
| CSRF | Token aleatorio por proceso en `<meta>` + cabecera `X-CSRF-Token` obligatoria en mutaciones; Origin no local rechazado | `test_mutaciones_exigen_csrf...` |
| CSP y cabeceras | `default-src 'self'`, sin `unsafe-inline`, `frame-ancestors 'none'`, `object-src 'none'`; nosniff, DENY, no-referrer, Permissions-Policy, COOP/CORP, `no-store` | `test_cabeceras_de_seguridad` |
| XSS | La interfaz construye el DOM con `textContent`; sin `innerHTML`/`eval` | `test_xss_en_nota...` |
| Inyección SQL | Solo consultas parametrizadas; nombres de tabla fijos | `test_inyeccion_sql...` |
| Inyección NoSQL | No aplica (no hay base NoSQL) | — |
| Subidas | Solo `.csv`, ≤ 1 MB (cuerpo ≤ 1.2 MB), ≤ 5 000 filas, rechazo de binarios, decodificación controlada | `test_subida_restringida` |
| Validación de entradas | Operaciones, perfil y precios validados en servidor con mensajes por campo | `test_cartera.py` |
| Límite de peticiones | 6/min cálculo, 4/min actualización, 20/min importación, 60/min otras mutaciones; candado de cálculo | `seguridad.py` |
| Límite de respuesta | Listas acotadas (1 000–5 000 filas); historia ≤ 1 500 puntos | `app.py` |
| Límite de gasto con proveedores | Contadores persistentes por hora/día por proveedor; al agotarse se detiene y registra | `test_limite_diario_persistente` |
| Credenciales | Solo variables de entorno/.env ignorado; nunca al navegador; errores sanean `token=`; el registro HTTP de bajo nivel está silenciado | `test_reintenta_429_y_oculta_credencial`, `test_sin_secretos...` |
| Depuración | Sin `/docs`, `/redoc`, `/openapi.json`; errores genéricos al cliente y detalle solo en el registro local | `test_documentacion...` |
| Rutas de prueba | No existen; sin rutas de órdenes | `test_no_existen_rutas_de_ordenes_reales` |
| Integridad del libro | Sin borrado; anulación/corrección auditadas; importación todo-o-nada | `test_duplicados_anulacion...` |
| Respaldos | Copia en caliente verificada con `integrity_check`, rotación | `terminal respaldar` |

## Controles que aplican solo si se publica o se accede por red

No se implementan porque la terminal no es accesible desde la red. Antes de exponerla (por ejemplo, para verla desde el móvil):

1. Autenticación verificada en servidor (usuario único con contraseña fuerte + segundo factor), cookies `Secure; HttpOnly; SameSite=Strict`, límite de intentos y bloqueo progresivo, protección contra bots en el inicio de sesión.
2. HTTPS obligatorio (HSTS), CORS restringido al propio origen, CSP igual o más estricta.
3. Rutas administrativas protegidas (actualización de datos, importación, perfil).
4. Cifrado en reposo de `data/terminal.db` (p. ej. BitLocker del equipo o SQLCipher) y de los respaldos.
5. Monitoreo de accesos y consultas; registros con acceso restringido.
6. **Cloudflare**: aporta valor real solo en ese escenario — *Cloudflare Tunnel* + *Access* (identidad con 2FA) evita abrir puertos y añade WAF y límite de tasa. Para uso local no aporta nada.
7. Si se migrara a una plataforma con RLS/buckets (p. ej. Supabase): RLS activado en todas las tablas, *buckets* privados, solo la clave pública en el cliente, claves privilegiadas únicamente en el servidor, columnas protegidas (`anulada`, `reemplaza_id`, `huella`) no editables por el cliente.

## Revisión de secretos (2026-09-22)

Se revisaron nombres de variables y rutas; **ningún valor se copió a este informe**.

| Hallazgo | ¿Expuesto en Git? | Acción recomendada |
|---|---|---|
| `AutoHedge/.env` define `WALLET_PRIVATE_KEY` (vacía) | No (ignorado) | Nunca guardar llaves privadas de cartera en texto plano; usar cartera de hardware o almacén cifrado. Si alguna vez tuvo un valor y el archivo se compartió, mover fondos a una cartera nueva (una llave privada no se «rota»). |
| `anything-llm/server/.env` contiene `SIG_KEY` (64 caracteres) | No (ignorado) | Solo si el archivo salió del equipo: generar un valor aleatorio nuevo (32 bytes), reemplazarlo en `.env` y reiniciar (invalida firmas/sesiones). |
| `paperclip/.env` contiene `BETTER_AUTH_SECRET` (20 caracteres) y `PAPERCLIP_TOOL_ACTION_SIGNING_SECRET` | No (ignorado) | `BETTER_AUTH_SECRET` es corto: sustituir por ≥ 32 bytes aleatorios (`openssl rand -base64 32`) y reiniciar (cierra sesiones). Rotar el secreto de firma del mismo modo si el archivo se compartió. |
| `browser-use/.env` `BROWSER_USE_API_KEY` | No (ignorado) | Es un valor de ejemplo; nada que rotar. |
| Patrones de clave en archivos versionados de yt-dlp, penpot (certificado autofirmado de desarrollo), pnpm (certificados de prueba), ccxt, FinceptTerminal, crewAI, hummingbot, paperclip, hyperframes, Plankton | Sí, pero son del proyecto original público | No son secretos del usuario; sin acción. |
| Variables de entorno del sistema | — | No hay claves de proveedores financieros definidas. |
| `terminal-portafolios` | — | Sin secretos; prueba automatizada lo verifica en cada ejecución. |

Procedimiento general de rotación de una clave de proveedor (Tiingo, EODHD, Banxico): entrar al panel del proveedor → revocar/regenerar la clave → pegar la nueva en `.env` → reiniciar la terminal → revisar la pestaña Datos. Si una clave llegara a un commit: rotarla primero y después limpiar el historial (p. ej. `git filter-repo`), porque la clave ya debe considerarse comprometida.

## Privacidad

- Todos los datos del usuario (operaciones, perfil, importaciones) permanecen en `data/` en su equipo; no hay telemetría, analítica ni envío a terceros.
- Solo salen del equipo peticiones de precios/tipo de cambio con el símbolo y fechas, y la credencial en la cabecera o parámetro que exige cada proveedor.
- El PDF de origen no se copió al repositorio; sus renders están en `_privado/` (ignorado).
