# Seguridad y privacidad

## Modelo de amenaza (uso local)

Un solo usuario en su PC. Riesgos: (1) una página web maliciosa abierta en el mismo navegador que llame a `127.0.0.1:8765` (CSRF, *DNS rebinding*); (2) fuga de credenciales de proveedores por registros, Git o interfaz; (3) archivos importados manipulados; (4) contenido de terceros (titulares, nombres) interpretado como HTML; (5) pérdida de datos; (6) ejecución accidental de operaciones reales.

Estados: **Aplicado** · **Previsto si se publica** · **No aplica** (con motivo).

## Secretos

| Punto | Estado | Evidencia |
|---|---|---|
| Ocultar claves API | Aplicado | Solo en variables de entorno / `.env`; `config.credencial()`; la interfaz muestra «Configurado/Requiere credencial», nunca el valor |
| Revisar variables de entorno | Aplicado | Revisadas por nombre: sin claves de proveedores financieros definidas en el sistema |
| `.env` nunca en Git | Aplicado | `.gitignore`; `test_env_ignorado_por_git` |
| Escanear historial Git | Aplicado | `scripts/escanear_secretos.py` revisa cada archivo de cada commit (6 commits, 0 hallazgos) + `detect-secrets scan` (0 hallazgos). Se usaron en lugar de gitleaks/trufflehog para no descargar binarios externos |
| No *hardcodear* | Aplicado | `test_sin_secretos_en_archivos_versionados` en cada ejecución de pruebas |
| Sin secretos en frontend ni registros | Aplicado | Registro HTTP de bajo nivel silenciado (`httpx` en WARNING); errores saneados (`limpiar()` oculta `token=`/`api_token=`); errores de Telegram no se registran (el token va en la URL) |
| Si hay fuga: cómo rotar sin copiar el valor | Aplicado | Sección «Revisión de secretos» abajo |
| Límites de gasto y de peticiones | Aplicado | `[proveedores.*]` por hora/día, contadores persistentes en SQLite; `test_limite_diario_persistente`; FF ≤ 1/h, SA ≤ 1 por emisora cada 30 min, SEC ≤ 10/s |
| Informes crudos con datos de sesión | Aplicado | `docs/evidencia/*.json` (Lighthouse) fuera de Git: contienen el token CSRF efímero |

## Aplicación

| Punto | Estado | Evidencia |
|---|---|---|
| Validar y sanear toda entrada | Aplicado | Operaciones, perfil, precios, universo, simulación y tareas validados en servidor con mensajes por campo |
| Escapar contenido de usuario (XSS) | Aplicado | DOM por `textContent`; sin `innerHTML`/`eval` (`test_xss...`); enlaces externos solo `https://` con `rel="noopener noreferrer"`; RSS descarta enlaces no `https` |
| Consultas parametrizadas (SQL) | Aplicado | `test_inyeccion_sql...`; nombres de tabla fijos |
| Inyección NoSQL | No aplica | No hay base NoSQL |
| Subida de archivos restringida | Aplicado | Solo `.csv`, ≤ 1 MB (cuerpo ≤ 1.2 MB), ≤ 5 000 filas, rechazo de binarios (`\x00`), decodificación controlada; no se ejecuta ni se guarda en disco (el original se conserva como BLOB para auditoría). Escaneo antivirus: no aplica a texto CSV validado |
| Protección CSRF | Aplicado | Token aleatorio por proceso + cabecera `X-CSRF-Token` + Origin local; `test_mutaciones_exigen_csrf...`, `test_cambio_de_modo...` |
| CORS restringido a localhost | Aplicado | No se emiten cabeceras CORS ⇒ solo mismo origen; Host y Origin deben ser locales |
| Cabeceras de seguridad + CSP | Aplicado | CSP `default-src 'self'` sin `unsafe-inline`; nosniff, DENY, no-referrer, Permissions-Policy, COOP/CORP, `no-store`. La página `/grafica/<id>` tiene CSP propia limitada a TradingView |
| Cookies `HttpOnly`/`Secure`/`SameSite` | No aplica | La terminal no usa cookies |
| Limitar tamaño de respuestas | Aplicado | Listas acotadas (≤ 1 000–5 000 filas), historia ≤ 1 500 puntos, 400 filas en la tabla de universo; gzip |
| *Rate limiting* | Aplicado | 6/min cálculo, 4/min actualización, 20/min importación, 60/min otras mutaciones; candado de cálculo compartido con el motor |
| Depuración desactivada | Aplicado | Sin `/docs`, `/redoc`, `/openapi.json`; errores genéricos al cliente |
| Eliminar rutas de prueba | Aplicado | No existen; sin rutas de órdenes (`test_no_existen_rutas_de_ordenes_reales`) |
| Ajustes de «producción» | Aplicado | Uvicorn sin encabezado de servidor, sin recarga; motor desactivable (`TERMINAL_SIN_MOTOR`) en pruebas |
| Operaciones reales | Aplicado (bloqueadas) | No hay integración con brókers; `ccxt`, `freqtrade`, `hummingbot`, `nautilus_trader` no se instalan; el simulador del Reto se opera manualmente |
| Notificaciones | Aplicado | Toast de Windows con contenido en base64 (sin interpolar texto en PowerShell); correo/Telegram solo si el usuario los activa |

## Si hubiera cuentas, base de datos compartida o acceso remoto

| Punto | Estado | Motivo / plan |
|---|---|---|
| Autenticación verificada en servidor | Previsto si se publica | Hoy solo acceso local; plan: usuario único con contraseña fuerte + 2FA |
| Login seguro, límite de intentos, anti-bot | Previsto si se publica | No hay login |
| Permisos mínimos validados en servidor | Aplicado (local) | Proceso del usuario sin privilegios; tareas programadas sin administrador |
| Rutas protegidas por defecto, admin protegida | Previsto si se publica | Hoy todas las mutaciones exigen CSRF + Host local |
| Aislamiento por usuario | No aplica | Un usuario |
| RLS y *buckets* privados | No aplica | No se usa plataforma con RLS; si se migra a una (p. ej. Supabase): RLS en todas las tablas, *buckets* privados |
| Solo clave pública en el cliente | No aplica | El cliente no recibe ninguna clave |
| Bloquear manipulación de campos protegidos | Aplicado | `huella`, `anulada`, `reemplaza_id`, `origen`, estado de alertas los fija el servidor |
| Cifrar datos sensibles | Previsto si se publica | Local: BitLocker y respaldos cifrados recomendados |
| Restringir acceso a registros | Aplicado (local) | `data/logs/` en la carpeta del usuario, sin credenciales |
| Monitorear consultas | Aplicado (local) | Tablas `ingestas`, `auditoria`, `alertas`; registro rotativo |
| 2FA donde aplique | Previsto | Recomendado en Actinver, Reto y proveedores de datos |

## Red y operación

| Punto | Estado | Evidencia |
|---|---|---|
| Servir en `127.0.0.1` | Aplicado | El CLI rechaza otro host; `test_host_no_local_rechazado` |
| HTTPS forzado, Cloudflare delante | Previsto si se publica | Cloudflare Tunnel + Access (2FA, WAF, límite de tasa) solo tiene sentido con acceso remoto |
| Dependencias actualizadas | Aplicado | `pip-audit`: sin vulnerabilidades conocidas (2026-09-23); `npm audit` no aplica (sin Node en ejecución) |
| Respaldos probados | Aplicado | `uv run terminal respaldar` con `PRAGMA integrity_check` y rotación; prueba de restauración mensual ([05-recurrencia.md](05-recurrencia.md)) |

## Revisión de secretos en los repositorios (2026-09-23)

Se revisaron nombres de variables y rutas; **ningún valor se copió a este informe**.

| Hallazgo | ¿Expuesto en Git? | Acción |
|---|---|---|
| `AutoHedge/.env` define `WALLET_PRIVATE_KEY` (vacía) | No (ignorado) | No guardar llaves privadas de cartera en texto plano; si alguna vez tuvo valor y se compartió, mover fondos a una cartera nueva (una llave privada no se rota) |
| `anything-llm/server/.env` contiene `SIG_KEY` | No (ignorado) | Solo si el archivo salió del equipo: generar 32 bytes aleatorios nuevos, reemplazar, reiniciar |
| `paperclip/.env` contiene `BETTER_AUTH_SECRET` (20 caracteres) y `PAPERCLIP_TOOL_ACTION_SIGNING_SECRET` | No (ignorado) | `BETTER_AUTH_SECRET` es corto: sustituir por ≥ 32 bytes aleatorios (`openssl rand -base64 32`) y reiniciar |
| `browser-use/.env` `BROWSER_USE_API_KEY` | No (ignorado) | Valor de ejemplo |
| Patrones en archivos versionados de proyectos públicos (yt-dlp, penpot, pnpm, ccxt, FinceptTerminal, crewAI, hummingbot, paperclip, hyperframes, Plankton) | Sí, del proyecto original | No son secretos del usuario |
| `actinver-terminal` (árbol e historial) | — | 0 hallazgos |

Rotación de una clave de proveedor (Tiingo, EODHD, Banxico, Barchart, SEC User-Agent, SMTP, Telegram): panel del proveedor → revocar/regenerar → pegar la nueva en `.env` → reiniciar la terminal → revisar la pestaña Datos. Si una clave llegara a un commit: rotarla primero y después limpiar el historial (`git filter-repo`), porque ya debe considerarse comprometida.

## Privacidad

- Operaciones, perfil, importaciones y alertas permanecen en `data/` del equipo; no hay telemetría ni analítica.
- Salen del equipo solo: peticiones de precios/tipo de cambio (símbolo y fechas), consultas a los feeds de contexto (símbolo), el User-Agent de contacto que usted configure para la SEC, el símbolo al abrir una gráfica de TradingView, y las notificaciones por correo/Telegram si usted las activa.
- El PDF de origen no está en el repositorio; sus renders están en `_renders/` (ignorado).
