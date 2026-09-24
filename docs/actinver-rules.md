# Reglas del Reto Actinver 2026 (configuración versionada)

- **Fuente oficial:** <https://www.retoactinver.com/web/reto-actinver/bases-y-mecanica>. Consultada el **2026-09-23**; la portada, <https://www.retoactinver.com>, también ese día.
- **Configuración:** `config/reto.yaml`.
- **Versión local:** tabla `versiones_reglas` (huella sha256 del archivo).
- **Zona horaria:** `America/Mexico_City`.

## Fragmentos aplicables y su configuración

Citas breves de las bases; la sección aparece entre paréntesis.

| Regla | Fragmento (sección) | Configuración | Implementación y prueba |
|---|---|---|---|
| Práctica | «00:00:00 hr del 28 de septiembre del 2026 … hasta las 23:59:59 hrs. del 02 de octubre» (§5) | `fechas.practica_*` | `reto.etapa`, `test_fechas_del_reto_y_zona_horaria` |
| Competencia | «… 05 de octubre del 2026 y hasta las 15:00:00 hrs del 13 de noviembre» (§5) | `fechas.competencia_*` | idem |
| Reinicio | «se reiniciará el saldo de 1 millón de actipesos» (§5) | `capital: 1000000` | `servicios.operaciones_etapa`, `test_practica_y_competencia_separadas` |
| Cinco acciones | «operaciones con por lo menos 5 (cinco) acciones distintas» (§6) | `reglas.min_emisoras: 5` | `reto.acciones_operadas`, `test_cinco_acciones_distintas_solo_competencia` |
| Límite 50 % | «en ningún momento haber realizado compras en una sola acción por más del 50 %» (§6/§7) | `reglas.max_peso_emisora: 0.50` | `reto.verificar_compras`, `test_limite_de_compra_del_cincuenta_por_ciento` |
| Costos | «tasa de 0.10 % … más 16 % … equivalente a la comisión e IVA» (§8) | `costos.comision_pct`, `iva_sobre_comision` | `reto.costo_detalle`, `test_costo_comision_mas_iva` |
| Horario | 07:30–14:00; desde el 3 nov, 08:30–15:00 (§8) | `horario_bmv` | calendario XMEX |
| Dividendos | «no reproducirá los derechos corporativos … como el pago de dividendos» (§13) | `dividendos_reproducidos: false` | precios sin ajuste por dividendos; los splits sí se reproducen |
| Automatización | uso de «robots, scripts, autómatas, macros» prohibido (§17) | `prohibicion_automatizacion` | la terminal no inicia sesión, no extrae datos del portal ni envía órdenes (`test_no_existen_rutas_de_ordenes_reales`) |
| Inscripción | hasta 23:59:59 del 04 de octubre (§2). La portada dice 2 de octubre | `inscripcion_fin` | discrepancia documentada; se usa el reglamento |

**Resultado principal:** la ganancia absoluta al cierre (`reto.ganancia`), mostrada también como porcentaje. El resumen muestra por separado el importe, la comisión, el IVA y el total de cada operación, así como la comisión estimada si se liquidara la cartera.

**Interpretación del 50 %:** las bases no dicen si el límite aplica a cada compra individual o a la posición acumulada. La terminal advierte en ambos casos **antes** de presentar una propuesta:

- **Crítica:** una compra individual mayor al 50 % del valor del portafolio.
- **Aviso:** una compra tras la cual la posición supera el 50 %.

La interpretación oficial corresponde al Comité.

**«Acciones»:** cuentan las acciones, FIBRAs y REIT con compra confirmada en la competencia. Los ETF no se cuentan hasta que el Comité confirme si valen.

## Órdenes pendientes frente a operaciones confirmadas

Una orden registrada como pendiente (`/api/pendientes-portal`) es solo una referencia de lo que el participante capturó en el portal. **No cambia posiciones ni efectivo**; lo verifica `test_orden_pendiente_no_cambia_tenencia`. Solo una operación **confirmada** registrada en «Mi cartera» actualiza la tenencia.

## Cambios en las bases

Si `config/reto.yaml` cambia, se abre una versión nueva. La pestaña «Reto» muestra un **aviso de discrepancia** hasta que el participante la marque como revisada. Las instantáneas, la bitácora y los pronósticos guardan la versión con que se calcularon: no se recalculan en silencio. Lo verifica `test_reglas_versionadas_y_aviso_de_discrepancia`.

## Estados de orden, deslizamiento y conciliación (v0.7)

- **Estados:** `enviada`, `pendiente`, `ejecutada`, `cancelada`, `expirada`. Solo `ejecutada`, enlazada a una operación confirmada con folio, cambia posiciones y efectivo (`test_estados_de_orden_solo_ejecutada_con_confirmacion`).
- **Costos:** comisión 0.10 % + IVA 16 % sobre la comisión, con escenarios de deslizamiento de 0, 0.1 % y 0.5 %, y el caso de no ejecución de una orden limitada (`terminal/boleta.py`).
- **Conciliación:** los saldos del portal se capturan o importan; si la diferencia con la estimación es de 1 % o más, se genera una alerta.

