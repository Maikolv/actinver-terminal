# 13 · Evidencia de los criterios de aceptación

Verificado el 2026-09-22 y 2026-09-23 en Windows 11, Python 3.12 (uv), Chrome 1xx y navegador integrado de Claude Desktop. Capturas y resumen de Lighthouse en [`docs/evidencia/`](evidencia/).

## Resumen

| Criterio | Estado | Evidencia principal |
|---|---|---|
| Arranca con un comando y README claro | Cumple | `start.bat` / `uv run terminal iniciar`; README |
| Vistas «Solo acciones» y «Acciones + ETF + fondos»; clase independiente del PDF | Cumple | `test_universo.py`, `test_solo_acciones_no_mezcla_clases` |
| Track del inversionista cuadra con transacciones conocidas | Cumple | `test_cartera.py` (valores calculados a mano) |
| Fuente, hora y vigencia por dato; dato vencido o fuente caída no produce recomendación actual | Cumple | `test_dato_vencido...`, `test_sin_tipo_de_cambio...`, alertas técnicas, modo real sin claves |
| Recalculo automático al llegar datos; reproducible ante riesgo/horizonte/restricciones | Cumple | Motor (`servicios.ciclo`), `test_reproducible`, `test_cambia_con_riesgo...`, `test_lentes...` |
| Alertas disparan en pruebas simuladas y respetan enfriamiento | Cumple | `test_alertas.py` (6 pruebas, todas las reglas) |
| Ficha por repositorio; uso documentado por URL | Cumple | `docs/repos.md` (64/64 verificado por script), `docs/fuentes.md` |
| Sin claves en repo ni historial; sin trading real | Cumple | Escáner de historial (0), `detect-secrets` (0), `test_no_existen_rutas_de_ordenes_reales` |
| Escritorio y móvil; accesibilidad, errores y rendimiento | Cumple | Lighthouse escritorio 100/100/100, móvil 93/100/100; 375 px y 768 px sin desbordamiento; consola limpia |
| Matriz de seguridad y web completa | Cumple | `docs/seguridad.md`, `docs/matriz.md` |

## 1. Arranque

- `start.bat` (o `start.bat demo`) verifica `uv`, sincroniza dependencias y ejecuta `uv run terminal iniciar` / `demo` en `http://127.0.0.1:8765`.
- Modo real sin credenciales: FRED entrega USD/MXN (1 268 observaciones, última 2026-09-18); ForexFactory y Seeking Alpha funcionan sin clave; las propuestas quedan «Suspendidas · Sin datos suficientes» con la acción para resolverlo (no se inventan precios).

## 2. Universo y clases

- 146 claves rotuladas «ETF's» en el PDF: **0** con bandera ETF=Y en Nasdaq Trader; la sección repite la de «Acciones».
- `pdf-inspector` clasifica el PDF como `image_based` (11/11 páginas requieren OCR) → transcripción visual verificada contra fuentes oficiales.
- Claves reasignadas (GOLD, PARA), deslistadas (CPE, MRO) y por confirmar (ALFA, ELEKTRA) excluidas con motivo.

## 3. Seguimiento del inversionista (`test_cartera.py`)

| Concepto | Esperado | Resultado |
|---|---|---|
| Costo tras 2 compras (10@1 000 + 29; 10@1 200 + 35) | 22 064 | ✔ |
| Realizado venta 5@1 500 (−20 comisión, −10 impuesto; costo salida 5 516) | 1 954 | ✔ |
| Split 2:1 | 30 títulos, costo 16 548 | ✔ |
| Dividendo neto (100 − 10) | 90 | ✔ |
| Efectivo final | 84 446 | ✔ |
| No realizado a 700 | 21 000 − 16 548 | ✔ |

Además: TWR sin contar aportaciones como rendimiento, operaciones en USD, posiciones iniciales, duplicados, corrección y anulación auditadas. En la interfaz: caída desde máximo y comparación con IPC (ACTIVAR), S&P 500 y 60/40; comisión del simulador (0.10 % + IVA) calculada al capturar.

## 4. Vigencia y fuentes caídas

- Cada instrumento muestra proveedor, bolsa, moneda, zona horaria, fecha, tipo de dato, retraso en horas y chip de vigencia (pestaña Datos).
- `test_dato_vencido_se_excluye_y_suspende`, `test_sin_tipo_de_cambio_no_se_valoran_activos_en_dolares`; propuestas guardadas pasan a «no actual» si envejecen o cambia el perfil.
- Alertas técnicas: `dato_vencido`, `fuente_caida`, `propuesta_suspendida` (`test_alerta_tecnica_y_silencio_fuera_de_horario`).

## 5. Motor, lentes y reproducibilidad

- Ciclo de arranque en demo: 15.7 s, 4 propuestas recalculadas, 9 alertas nuevas (silenciadas por estar fuera de horario), contexto FF «ok», SA «ok», SEC «requiere configuración».
- Lentes coherentes (μ global, D-22): lente de máximo rendimiento con mayor rendimiento esperado y mayor volatilidad que la de ajuste en ambos universos; todas cumplen ≥ 5 emisoras y ≤ 50 % (`test_lentes_cumplen_reglas_y_difieren`).
- Reproducible: mismos datos → mismos pesos, puntuación y huella (`test_reproducible`); conservador ⇒ más deuda; horizonte corto ⇒ fondos de ventana anual excluidos.

## 6. Alertas (`test_alertas.py`)

| Regla | Prueba |
|---|---|
| Deriva ≥ 5 pp + mejora neta ≥ 0.5 %, histéresis 3 pp, enfriamiento 6 h | `test_deriva_con_histeresis_y_enfriamiento` |
| Propuesta no actual no genera rebalanceo | `test_propuesta_no_actual_no_genera_deriva` |
| Stop-loss, toma de utilidad, caída desde máximo | `test_stop_take_y_caida_desde_maximo` |
| Macro, insider, noticia (una sola vez) | `test_macro_insider_noticia_una_sola_vez` |
| Dato vencido y silencio fuera de horario | `test_alerta_tecnica_y_silencio_fuera_de_horario` |
| Agrupación de notificaciones | `test_agrupa_notificaciones` |

Notificación de escritorio de Windows probada en vivo (`notificador.escritorio` → «enviada»). «Simular cambio» verificado en la interfaz (títulos enteros, costo, cumplimiento del Reto, aviso de poder de compra).

## 7. Interfaz, accesibilidad y rendimiento

| Verificación | Resultado |
|---|---|
| Lighthouse escritorio | Rendimiento 100 · Accesibilidad 100 · Buenas prácticas 100 (FCP 0.4 s, LCP 0.8 s, TBT 10 ms, CLS 0) |
| Lighthouse móvil | Rendimiento 93 · Accesibilidad 100 · Buenas prácticas 100 (FCP 0.8 s, LCP 2.1 s, TBT 280 ms, CLS 0.047) |
| SEO | 63 a propósito: `robots.txt Disallow` + `noindex` (herramienta privada) |
| Móvil 375 px / tableta 768 px | `scrollWidth` = ancho (sin desbordamiento); tableta en 2 columnas |
| Contraste | Mínimo 5.24:1 claro, 6.1:1 oscuro |
| Consola del navegador | Sin errores |
| Tiempos de API (instancia local) | `/api/estado` 0.10 s · `/api/propuestas` 0.02 s · `/api/reto` 0.01 s · `/api/cartera` 0.40 s |
| Gráfica TradingView | Widget oficial carga (`docs/evidencia/grafica-tradingview.png`) |

Trayectoria de rendimiento móvil: 72 → 84 → 91–94 tras eliminar desplazamientos de diseño, diferir el universo y el detalle de propuestas, unificar la carga inicial y reordenar las pilas de fuentes (la resolución de `system-ui`/`ui-monospace` costaba ~60 ms por diseño en Windows).

## 8. Seguridad

- Historial completo (6+ commits) y árbol: 0 secretos; `pip-audit`: sin vulnerabilidades conocidas.
- 12 pruebas de seguridad (Host, CSRF, Origin, CSP, subida, XSS, SQL, 404, rutas de prueba, sin órdenes, secretos, `.env` ignorado, cambio de modo).

## 9. Ejecución de pruebas

```
63 passed
test_adaptadores 6 · test_alertas 6 · test_cartera 7 · test_fuentes_web 5 · test_optimizador 9 · test_reto 7 · test_seguridad 12 · test_universo 4 · test_vigencia 7
```
