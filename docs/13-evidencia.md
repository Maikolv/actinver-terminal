# 13 · Evidencia de los criterios de aceptación

Verificado el 2026-09-22 en Windows 11, Python 3.12 (uv), navegador integrado de Claude Desktop.

## 1. Se inicia localmente con instrucciones claras (CA-1)

- `uv sync` → `uv run terminal demo` levanta `http://127.0.0.1:8765` (demo, base `data/demo/`); `uv run terminal iniciar` en modo real.
- `uv run terminal actualizar` en modo real **sin credenciales**: `{'fx': {'proveedor': 'fred', 'estado': 'ok', 'registros': 1268}, 'precios': {…'registros': 0…}}` — tipo de cambio real 2021-08-24 → 2026-09-18.
- `GET /salud` → `{"ok": true}`.

## 2. Vistas separadas sin mezclar clases (CA-2)

- `test_seccion_etf_del_pdf_no_contiene_etf_verificados`: 146 claves rotuladas «ETF's» en el PDF, **0** con bandera ETF=Y en Nasdaq Trader.
- `test_transcripcion_pdf_completa`: la sección «ETF's» repite exactamente la lista de «Acciones».
- `test_solo_acciones_no_mezcla_clases`: la propuesta «Solo acciones» solo contiene clases `accion`/`reit`.
- `test_mixta_incluye_etf_y_fondos_con_restricciones`: la mixta incluye ETF, fondos y FIBRA, con deuda mínima del perfil y pesos que suman 1.
- En la interfaz (demo): «Solo acciones» 13–15 posiciones de acciones; «Acciones + ETF + fondos» con ACTDUAL, ACTICOB, ACTIG+2 (≤ 10 % por ventana anual), acciones y ETF.

## 3. Seguimiento correcto con transacciones conocidas (CA-3)

`test_costo_promedio_realizado_no_realizado` (valores calculados a mano):

| Concepto | Esperado | Resultado |
|---|---|---|
| Costo tras 2 compras (10@1 000 + 29; 10@1 200 + 35) | 22 064 | ✔ |
| Realizado venta 5@1 500 (−20 comisión, −10 impuesto; costo salida 5 516) | 1 954 | ✔ |
| Split 2:1 | 30 títulos, costo total 16 548 | ✔ |
| Dividendo neto (100 − 10) | 90 | ✔ |
| Efectivo final | 84 446 | ✔ |
| No realizado a 700 | 21 000 − 16 548 | ✔ |

También: ventas mayores a la posición rechazadas; operaciones en USD con tipo de cambio; TWR que no cuenta aportaciones como rendimiento (`test_serie_historica_twr_con_flujos`); posiciones iniciales como aportación en especie; duplicados, corrección y anulación auditadas.

En la interfaz (cartera demo importada por CSV): aportación neta 290 000 (= 300 000 − 10 000), dividendos netos 405 (= 450 − 45), reimportar el mismo archivo → 8 duplicadas, 0 aceptadas.

## 4. Fuente, fecha y vigencia en cada dato; sin recomendación actual con datos caídos (CA-4)

- Pestaña Datos: por instrumento, proveedor, bolsa, moneda, zona horaria, fecha, tipo de dato, retraso en horas y chip de vigencia; por proveedor, estado, peticiones restantes y última corrida.
- `test_dato_vencido_se_excluye_y_suspende`: precios de hace 40 días → exclusión «Dato vencido» y propuesta **suspendida** sin pesos.
- `test_sin_tipo_de_cambio_no_se_valoran_activos_en_dolares`: sin FX → suspendida con motivo explícito.
- Modo real sin claves: ambas propuestas «Suspendida · Sin datos suficientes…» con la acción para resolverlo.
- Propuestas guardadas: se marcan «no actual» si el perfil cambia o sus datos tienen más sesiones de atraso que el umbral (`_revalidar`).
- Datos sintéticos: estado «Sintético», calidad de datos 0 y aviso «Modo demostración» permanente.
- `test_vigencia.py`: festivo del 16 de septiembre en la BMV, horario de cierre, umbrales por tipo.

## 5. Reproducibilidad y respuesta a criterios (CA-5)

- `test_reproducible`: dos cálculos con la misma entrada → mismos pesos, puntuación y huella de datos.
- `test_cambia_con_riesgo_horizonte_y_restricciones`: perfil conservador → más deuda; horizonte 1 año → ACTIG+2 excluido por ventana anual; exclusión manual → fuera del universo con motivo; repetir el cambio → mismo resultado.
- Cada propuesta muestra función objetivo, λ, γ, restricciones, ventana, walk-forward, escenario, huella y versiones.

## 6. Sin claves ni operaciones reales (CA-6)

- `test_sin_secretos_en_archivos_versionados` (patrones de claves en todos los archivos no ignorados) y `test_env_ignorado_por_git`.
- `test_no_existen_rutas_de_ordenes_reales`: ninguna ruta contiene orden/order/broker/trade/ejecutar. Barra superior: «Operaciones reales: deshabilitadas».

## 7. Escritorio, móvil, accesibilidad, errores y rendimiento (CA-7)

| Verificación | Resultado |
|---|---|
| Escritorio (≈800 px) y móvil (375×812) | Sin desplazamiento horizontal (`scrollWidth` 375 = ancho); CTA fija abajo en móvil |
| Tema claro y oscuro | Ambos con tokens; fondo explícito |
| Contraste (12 pares de color) | Mínimo 5.24:1 en claro y 6.1:1 en oscuro (AA exige ≥ 4.5:1) |
| Campos sin etiqueta / botones sin nombre | 0 / 0 |
| Teclado | Flecha derecha en pestañas mueve foco y selección; foco visible |
| Errores | 404 propia; errores por campo con `aria-invalid`; error 500 inicial detectado (configuración de scikit-learn por hilo) y corregido |
| Seguridad HTTP en vivo | Sin token → 403; Origin ajeno → 403; Host ajeno → 400; `.exe` → 422 |
| Tiempos | `/` 6 ms · `app.js` 6 ms · `/api/estado` 190 ms · `/api/universo` 35 ms (137 KB → 11 KB con gzip) · `/api/cartera` 10 ms · cálculo de ambas propuestas 8–10 s |
| Consola del navegador | Sin errores tras la corrección |

## 8. Matriz de aplicabilidad (CA-8)

[07-matriz-aplicabilidad.md](07-matriz-aplicabilidad.md): seguridad (35 filas), sitio (17), contenido e indexación (20), medición (9) y extras (2).

## Ejecución de pruebas

```
44 passed in 20.25s
test_adaptadores.py 6 · test_cartera.py 7 · test_optimizador.py 9 · test_seguridad.py 11 · test_universo.py 4 · test_vigencia.py 7
```
