# Mejora de la terminal — 10-nov-2026

Sesión de mejora por etapas (prompt `docs/prompt-fable-mejora-20261110.md`). Cada cifra es una medición de esta sesión
en la PC del usuario; lo no comprobado se dice.

## 1. Reglas de riesgo validadas fuera de muestra

`terminal/validacion_riesgo.py` simula las reglas de `gestion_riesgo` (mismas señales, comprobado por prueba) en carteras
al azar de 8 emisoras del universo con ≥ 500 cierres. La señal usa cierres hasta el día t y la orden se ejecuta al cierre de
t+1, con comisión de 0.116 %. Ventana 7-oct-2022 a 30-sep-2026: anterior al diseño de las reglas (5-nov-2026), sin ajuste
de parámetros. 400 carteras por caso (80 fechas × 5); intervalo de confianza por bootstrap agrupado por fecha.
Repetir: `uv run python -m terminal.validacion_riesgo` (≈ 5 min; escribe `docs/evidencia/validacion-riesgo.json`).

Cartera concentrada como la real (46 / 17 / 14 / 12 / 6 / 3 / 1.5 / 0.5 %):

| 30 sesiones | Media | Mediana | Peor 10 % | Caída máx. media | Dif. vs mantener (IC 95 %) |
|---|---|---|---|---|---|
| Mantener | +1.8 % | +1.4 % | −7.8 % | −7.2 % | — |
| 1/N mensual | +1.6 % | +1.1 % | −5.5 % | −6.3 % | −0.2 [−0.7, +0.3] |
| Reglas, lo vendido a efectivo | +0.8 % | 0.0 % | −3.2 % | −3.2 % | −1.1 [−2.1, −0.1] |
| Reglas + reinversión | +1.0 % | +0.1 % | −6.3 % | −5.8 % | −0.8 [−1.7, +0.1] |
| Solo stop | +0.8 % | −0.1 % | −4.2 % | −4.3 % | −1.0 [−2.0, −0.1] |
| Solo tendencia | +1.0 % | +0.5 % | −5.4 % | −5.2 % | −0.9 [−1.7, −0.2] |
| Solo concentración | +1.5 % | +1.2 % | −5.5 % | −5.4 % | −0.3 [−0.7, +0.1] |
| Solo volatilidad | +1.8 % | +1.5 % | −7.1 % | −6.4 % | 0.0 [−0.4, +0.3] |

| 126 sesiones | Media | Peor 10 % | Caída máx. media | Dif. vs mantener (IC 95 %) |
|---|---|---|---|---|
| Mantener | +10.8 % | −10.0 % | −14.5 % | — |
| 1/N mensual | +10.3 % | −7.4 % | −12.2 % | −0.6 [−1.9, +0.7] |
| Reglas, lo vendido a efectivo | +1.2 % | −4.0 % | −3.6 % | −9.7 [−12.3, −7.0] |
| Reglas + reinversión | +6.0 % | −11.0 % | −11.6 % | −4.9 [−7.1, −2.7] |
| Solo concentración | +8.3 % | −6.5 % | −10.4 % | −2.6 [−3.6, −1.6] |
| Solo volatilidad | +9.6 % | −9.6 % | −12.4 % | −1.2 [−2.1, −0.4] |

Con carteras parejas (1/8) el resultado es el mismo en signo y tamaño (30 sesiones: reglas −1.0 pp; 126: −8.7 pp).

**Conclusión.** Las ventas por stop y por tendencia no tienen ventaja demostrada: bajan la caída a la mitad y rinden menos
que mantener (diferencia distinta de cero). Equivalen a tener parte de la cartera en efectivo. El tope de concentración y
el objetivo de volatilidad casi no cuestan a 30 sesiones. Ninguna variante supera a 1/N.

**Límites.** Periodo mayormente alcista; sin dividendos (igual para todas); la reinversión usa ocho emisoras al azar en vez
de la propuesta Markowitz; lo vendido no se recompra salvo por reinversión; sin el mínimo de emisoras del Reto.

**Qué cambió en el plan.** Cuando el plan pide vender, Telegram añade una línea con estas cifras (promedio y mal escenario
frente a mantener). Las reglas no se cambiaron: es decisión del usuario (ver «Decisiones»).

**Dos modos de venta (añadido después por decisión del usuario).** «Estricta: vende todo» (por defecto) y «Suave: reduce a
la mitad», elegibles en el Plan de acción; se guardan en la base y Telegram usa el mismo.

| Cartera concentrada, con reinversión | Media 30 s. | Peor 10 % 30 s. | Media 126 s. | Peor 10 % 126 s. |
|---|---|---|---|---|
| Mantener | +1.8 % | −7.8 % | +10.8 % | −10.0 % |
| Estricta | +1.0 % | −6.3 % | +6.0 % | −11.0 % |
| Suave | +1.1 % | −5.8 % | +6.7 % | −9.8 % |

La suave queda algo mejor que la estricta en media y en mal escenario, y ambas rinden menos que mantener.

## 2. Confiabilidad

- **Terminal apagada:** el monitor en la nube ya avisaba a las 26 h sin sincronizar y solo en día hábil (del 6 al 9-nov el
  aviso no pudo salir hasta el lunes). Nuevo aviso a los 90 min sin latido con el mercado abierto, uno por episodio
  (`cloud-alerts/src/reglas.js`, prueba nueva; 20 pruebas del worker). **Falta desplegarlo** (`wrangler deploy`): es una
  acción hacia fuera y requiere confirmación.
- **Precios faltantes en posiciones:** ya existía (`alertas.inhibir_direccionales` emite «Datos insuficientes para alertas
  direccionales» con las emisoras sin precio confiable). No se duplicó.
- **Arranque automático** al iniciar sesión: hecho el 9-nov.

## 3. Frescura de datos

La cola ya priorizaba: `ingesta.orden_cola` pone en nivel 0 la cartera y la captura del portal y en nivel 1 las emisoras de
las propuestas, antes de gastar el cupo de EODHD. No se cambió. El bloque «Qué hacer hoy» muestra la fecha del precio de
cada orden y marca los que son referencia.

## 4. Rendimiento

| Medición | Antes | Después |
|---|---|---|
| Plan durante el ciclo del motor | 79 s (5-nov) | 2.7–4.3 s |
| Option Flow durante el ciclo | 24 s (5-nov) | 1.9 s |
| Ficha técnica durante el ciclo | — | 3.4 s |
| GEX durante el ciclo | — | 1.3 s |
| `/api/estado`, cartera, ranking (tibio), velas durante el ciclo | — | 0.05–0.2 s |
| Cálculo del plan (perfil, en frío de caché) | 4.99 s | 1.75 s |
| Boletas dentro del plan (10 emisoras) | 3.85 s | 0.40 s |

- **Motor en proceso aparte** (`terminal/motor_aislado.py`): el ciclo corría en un hilo del servidor y, como Python ejecuta
  un hilo a la vez, la interfaz esperaba. Ahora corre en un proceso hijo con prioridad baja; el servidor conserva el
  bloqueo de cálculo mientras tanto. Comprobado: ciclo completo terminado en el hijo (541 s) con la interfaz respondiendo.
  Se apaga con `[app] motor_proceso_aparte = false`. Registro del hijo: `data/terminal_motor.log`.
- **Plan:** leía la historia de precios una vez por emisora; ahora una sola vez (`plan_accion.py`, `boleta.py`).
- **No se cumplió** «< 2 s siempre»: el plan queda en 2.7–4.3 s con el ciclo corriendo y la ficha en 3.4 s.
- **Pendiente:** perfilar el recálculo de propuestas (342–1,196 s) y la etapa de investigación (210–562 s). No se hizo.

## 5. Almacenamiento (propuesta, sin borrar nada)

Base: 1.43 GB. `flujo_operaciones`: 1,275,659 filas, 827 MB con índices (≈ 650 bytes por fila; 144 emisoras × ≤ 10,000,
el límite por consulta de Alpaca). Cada fila repite fuente, licencia, mercado, feed, calidad y dos marcas de tiempo.

| Opción | Ahorro estimado | Costo |
|---|---|---|
| A. Tope configurable de 3,000 operaciones por emisora | ≈ 580 MB | Order Flow cubre menos minutos del cierre |
| B. Mover la procedencia repetida a una tabla aparte | ≈ 250–300 MB | Migración de esquema y pruebas |
| C. Quitar el índice `ix_flujo_operaciones` (lo cubre el UNIQUE si se reordena) | ≈ 125 MB | Migración; medir consultas |
| D. Dejarlo así | 0 | Respaldos de 1.4 GB cada uno (5 copias = 3.6 GB) |

Recomendación: A, porque los datos se vuelven a descargar gratis. Requiere permiso porque borra filas.

## 6. Diseño

- La portada ya era el Plan de acción, pero lo accionable empezaba a ≈ 1,070 px. Ahora la guía de la portada abre cerrada
  (se recuerda si el usuario la abre) y el plan empieza con **«Qué hacer hoy»**: tres columnas (1 · Vende primero,
  2 · Después compra, Mantén) con cantidad, precio límite, motivo corto y fecha del precio. Coincide con Telegram
  (10-nov: 5 ventas, 4 compras, mismos límites). Antes la tabla contaba «Ventas 2 · Decisión pendiente 7».
- Comprobado en el navegador: escritorio (1024 px) y celular (375 px), sin desbordamiento horizontal ni errores de consola.
- Contraste medido del bloque en modo oscuro: 16.7:1 (texto) y 9.4:1 (texto secundario); AA pide 4.5:1.
- **No revisado:** modo claro, navegación por teclado, y la altura de la cabecera
  (≈ 515 px antes del contenido en 1024 px) y de la tabla del plan (≈ 3,750 px).

## 7. No hecho

- **GEX y vela de 1 min con mercado abierto:** la sesión fue de madrugada (mercados cerrados).
- **Post-Reto:** la directriz prohíbe aplicarla antes del 13-nov-2026 15:00.
- Perfil del recálculo de propuestas; revisión completa de accesibilidad y de las demás secciones.

## Pruebas

Python 950 (suite completa `pytest tests`, sin fallas; una advertencia de Starlette), Node 52 y worker 20.
Nuevas: 3 del simulador, 2 del motor aislado y 1 del worker.

## Decisiones del usuario

1. Reglas de venta: dejarlas (protegen, cuestan rendimiento) o suavizarlas (p. ej. el stop reduce a la mitad).
2. Desplegar el aviso de terminal apagada en Cloudflare.
3. Retención de operaciones de Order Flow (opción A).
4. Subir a GitHub.
