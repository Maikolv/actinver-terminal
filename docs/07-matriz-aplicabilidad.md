# 07 · Matriz de aplicabilidad

Estados: **Implementado** · **Previsto si se publica** (no se implementa porque la terminal es local y de un solo usuario; se documenta cómo hacerlo) · **No aplica** (con motivo). No se inventaron datos de contacto, horarios, servicios, métodos de pago, resultados de pruebas A/B ni eventos de conversión.

## Seguridad y privacidad

| Requisito | Estado | Motivo / evidencia |
|---|---|---|
| Claves API fuera del código, frontend, Git y registros | Implementado | `.env` ignorado; `config.credencial`; errores saneados; `test_sin_secretos...` |
| Revisar variables de entorno y repositorios en busca de secretos | Implementado | [12-seguridad.md](12-seguridad.md) §Revisión de secretos |
| Informar cómo rotar secretos expuestos sin copiar su valor | Implementado | Ídem; ningún valor en documentos |
| Límites de gasto y de peticiones por proveedor | Implementado | `[proveedores.*]`, tabla `uso_proveedor`, `test_limite_diario_persistente` |
| Validar entradas y archivos | Implementado | `cartera.validar`, `importar.leer`, `validar_perfil` |
| Restringir tipos y tamaños de subida | Implementado | `.csv`, ≤ 1 MB, ≤ 5 000 filas; `test_subida_restringida` |
| Evitar inyección SQL | Implementado | Consultas parametrizadas; `test_inyeccion_sql...` |
| Evitar inyección NoSQL | No aplica | No hay base NoSQL |
| Evitar XSS / escapar contenido del usuario | Implementado | DOM por `textContent`, CSP sin `unsafe-inline`; `test_xss...` |
| Evitar falsificación de solicitudes (CSRF) | Implementado | Token + Origin + Host; `test_mutaciones_exigen_csrf...` |
| Limitar respuestas de API | Implementado | Topes de filas y de historia |
| Cabeceras de seguridad | Implementado | `seguridad.CABECERAS`; `test_cabeceras...` |
| Autenticación comprobada en servidor | Previsto si se publica | Sin cuentas: acceso solo desde la propia PC |
| Permisos mínimos | Implementado | Proceso del usuario sin privilegios; tareas programadas sin administrador; sin rutas de órdenes |
| Rutas administrativas protegidas | Previsto si se publica | Hoy todas las rutas exigen CSRF y Host local |
| Límite de intentos de inicio de sesión / protección contra bots | Previsto si se publica | No hay inicio de sesión |
| Cookies seguras | No aplica | La terminal no usa cookies (CSRF por `<meta>` + cabecera) |
| Aislamiento por usuario | No aplica | Un solo usuario local |
| Cifrado de datos sensibles | Previsto si se publica | Local: se recomienda BitLocker para el disco y respaldos cifrados |
| Control de acceso a registros | Implementado | Registros en la carpeta del usuario, sin credenciales |
| Monitoreo de consultas | Implementado (local) | Tablas `ingestas` y `auditoria`; registro rotativo |
| RLS y *buckets* privados | No aplica | No se usa plataforma con RLS; plan en [12](12-seguridad.md) |
| Solo clave pública en el cliente | No aplica | El cliente no recibe ninguna clave |
| Impedir manipulación de campos protegidos | Implementado | `huella`, `anulada`, `reemplaza_id`, `origen` los fija el servidor |
| Forzar HTTPS | Previsto si se publica | Tráfico solo en 127.0.0.1 |
| Restringir CORS | Implementado | No se emiten cabeceras CORS: solo mismo origen |
| CSP | Implementado | Ver cabeceras |
| Desactivar depuración | Implementado | Sin `/docs`, errores genéricos; `test_documentacion...` |
| Eliminar rutas de prueba | Implementado | No existen |
| Revisar ajustes de producción | Implementado | Uvicorn sin encabezado de servidor, sin recarga, nivel *warning* |
| Evaluar Cloudflare delante del servicio | Previsto si se publica | Útil solo con acceso remoto (Tunnel + Access); sin valor en local |
| Dependencias actualizadas | Implementado | `uv.lock`; plan trimestral en [05](05-recurrencia.md) |
| Copias de seguridad comprobables | Implementado | `terminal respaldar` con `integrity_check` y prueba de restauración mensual |
| Autenticación de dos factores | Previsto si se publica | Recomendado ya en las cuentas de Actinver y de proveedores de datos |
| Documentar controles para uso exclusivamente local | Implementado | [12-seguridad.md](12-seguridad.md) |

## Sitio y formularios

| Requisito | Estado | Motivo / evidencia |
|---|---|---|
| Página 404 personalizada | Implementado | `web/404.html`; API devuelve JSON; `test_404_personalizada` |
| Llamada a la acción clara y visible al inicio | Implementado | «Recalcular propuestas» (primaria) |
| CTA fija en móvil | Implementado | Barra inferior < 720 px |
| CTA después del primer párrafo | No aplica | No hay contenido editorial; la CTA está en la cabecera |
| Diseño móvil y puntos de ruptura | Implementado | Rejillas `auto-fit`, punto de ruptura 720 px; verificado a 375 px |
| Estados de carga y error de formularios | Implementado | Mensajes por campo, `aria-invalid`, región de alerta, botones ocupados |
| Página de agradecimiento | No aplica | No hay formularios de contacto o conversión; las confirmaciones son notificaciones en contexto |
| Formularios probados | Implementado | Pruebas de validación y flujo real en navegador ([13](13-evidencia.md)) |
| Enlaces funcionales | Implementado | Enlaces internos (plantillas, pestañas); documentos enlazados entre sí |
| Política de privacidad | Previsto si se publica | Hoy: sección de privacidad en [12](12-seguridad.md); sin datos de terceros |
| Términos | Previsto si se publica | Aviso de uso en pie de página y README |
| Consentimiento de cookies | No aplica | Sin cookies ni analítica |
| Accesibilidad | Implementado | [11-diseno.md](11-diseno.md) §Accesibilidad |
| Dirección y correo de contacto reales | No aplica | No se proporcionaron; no se inventan |
| Enlaces sociales, botón de compartir | No aplica | Herramienta privada |
| Número pulsable para llamar, horario de atención | No aplica | No hay servicio de atención |
| Métodos de pago | No aplica | No hay cobros |

## Contenido e indexación

| Requisito | Estado | Motivo / evidencia |
|---|---|---|
| Metatítulo y metadescripción propios por página | Implementado | Página principal y 404 con título y descripción propios (aplicación de una página) |
| Un H1 por vista, distinto del metatítulo | Implementado | Cada pestaña tiene su `h1` («Propuestas», «Mi cartera»…) |
| Jerarquía H1/H2/H3 | Implementado | Revisado en todas las vistas |
| Intención de búsqueda | No aplica | `noindex`; no busca tráfico |
| Resumen o puntos clave | Implementado | Pestaña Resumen |
| Tablas y listas | Implementado | Posiciones, pesos, cambios, comparación |
| FAQ y marcado FAQ | No aplica | Hay pestaña Ayuda; el marcado estructurado solo sirve a buscadores |
| Nombres descriptivos y texto alternativo en imágenes | Implementado | Solo SVG: decorativos con `aria-hidden`, gráfica con `aria-label` |
| Imagen Open Graph | No aplica | No se comparte |
| Favicon | Implementado | `web/static/favicon.svg` |
| URL canónicas | No aplica | Sin indexación |
| URL limpias | Implementado | `/`, `/api/<recurso>` |
| Enlaces internos y grupos de contenido | Implementado | Pestañas y enlaces «Ver detalle y cambios» |
| `robots.txt` | Implementado | `/robots.txt` con `Disallow: /` + `<meta name="robots" content="noindex">` |
| `sitemap.xml` y envío a Search Console | No aplica | No debe indexarse |
| Reglas de indexación incluida `/page/` | Implementado | Todo bloqueado; la subcarpeta `/page/` no existe |
| `llms.txt` | No aplica | No hay contenido público para modelos |
| Marcado de negocio local | No aplica | No hay negocio local verificable |
| Página por servicio | No aplica | No hay servicios |
| Entradas de blog | No aplica | No hay estrategia editorial |

## Medición y rendimiento

| Requisito | Estado | Motivo / evidencia |
|---|---|---|
| GA4 | No aplica | Sin propósito definido ni consentimiento; datos financieros privados |
| Search Console | No aplica | Sin indexación |
| Captura de correo | No aplica | Sin propósito |
| Seguimiento de conversiones | No aplica | No hay conversiones |
| Mapas de calor | No aplica | Privacidad; un usuario |
| Pruebas A/B | No aplica | Un usuario; no se inventan resultados |
| Medición de velocidad | Implementado | Tiempos por ruta en [13](13-evidencia.md) §7 |
| Compresión de imágenes y recursos | Implementado | Gzip ≥ 1 KB; sin imágenes rasterizadas; ~66 KB de carga inicial |
| Revisión de rendimiento | Implementado | Consultas < 200 ms; cálculo ~10 s con indicador |

## Extras

| Requisito | Estado | Motivo |
|---|---|---|
| Galería de antes y después | No aplica | El equivalente funcional es la tabla «actual → objetivo» de cambios sugeridos |
| Ayudas emergentes enriquecidas | No aplica (se usa ayuda breve) | Títulos en controles clave y pestaña Ayuda; ventanas emergentes ricas no aportan utilidad comprobable |
