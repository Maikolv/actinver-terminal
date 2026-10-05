# Auditoría de la terminal — 5-oct-2026 (primer día de competencia)

Datos medidos el 5-oct, 22:00 CDMX, con la base real (`data/terminal.db`). Orden: mayor impacto en la decisión primero.
«Hecho» = corregido en esta sesión; «Decisión» = requiere al usuario (sección 7 del mandato).

## 1. Noticias y datos macro en tiempo real: qué hay y qué NO hay

| Fuente | Estado medido | Cómo se usa |
|---|---|---|
| Calendario macro ForexFactory (JSON semanal público) | 315 eventos; último refresco 5-oct 15:11 CDMX; se consulta cada hora | Alerta «macro» 48 h antes de cada evento de alto impacto de EE. UU./México; **nuevo**: el plan del día por Telegram menciona el próximo evento en palabras sencillas |
| Titulares Seeking Alpha (RSS público) | 741 titulares, 448 en las últimas 24 h; cada 30 min por emisora de la cartera | Alertas de noticia de alto impacto; inhibe compras/ventas si hay noticias contradictorias |
| Form 4 / 13F (SEC EDGAR) | Conectado (D-48) | Solo contexto, peso 0 |

**Respuesta directa:** el optimizador que arma el portafolio **no usa noticias ni el calendario macro**. Usa precios
históricos, reglas del Reto, costos y riesgo. Las noticias y los eventos macro llegan como alertas y avisos, no
mueven pesos. No es un descuido: no hay evidencia fuera de muestra de que meterlos mejore el resultado (D-46, D-48).
Tampoco son «tiempo real» estricto: el calendario se refresca cada hora y el dato publicado («actual») puede
tardar hasta 1 h en verse; los titulares, hasta 30 min.

Esta semana (alto impacto, EE. UU./México): minutas de la Reserva Federal, miércoles 7-oct 12:00 CDMX.

Brecha: el JSON es «de esta semana»; el viernes no se conocen los eventos del lunes siguiente. Mejora posible: añadir
la semana siguiente si la fuente la publica (verificar términos antes).

## 2. Hallazgos por prioridad

### Alto impacto

1. **19 emisoras BMV del catálogo nunca han tenido precio**, entre ellas WALMEX, OMA, ORBIA, PINFRA, TLEVISA,
   VESTA, VOLAR, PE&OLES, Q, R, NAFTRAC, ALFA y ELEKTRA. Por eso nunca aparecen en propuestas. Causa: EODHD gratis
   da 18–20 consultas al día y solo 17 de las 48 BMV del catálogo tienen el cierre del 2-oct; la cola de
   actualización ya da prioridad a la cartera y las propuestas, pero el cupo no alcanza ni para refrescar las que ya
   tienen historia. Opciones:
   - a) **Capturas de la lista de Acciones del simulador**: precio visible en el portal, enviado por el usuario.
     La vía legal ya usada para la cartera; daría el precio del simulador para las 146 emisoras de una vez.
   - b) Ampliar `reserva_nuevos` para cargar la historia de esas 19 en 1–2 días, a costa de dejar
     otras sin refrescar ese día.
   - c) Proveedor de pago (**Decisión**).
2. **El plan conservaba una propuesta dominada.** **Hecho.** La regla «estable» (no cambiar sin 2 puntos de
   mejora) mantenía «Acciones · Máximo rendimiento» (+0.9 % central, −19.7 % en el escenario adverso). Otra
   propuesta tenía +1.6 % y −5.9 %: más ganancia esperada y mucho menos riesgo. Ahora se cambia si otra la domina
   (más central y ≥ 2 puntos menos de pérdida adversa). Antes de la apertura aplica la regla entre sesiones, porque
   aún no se pudo operar. Pruebas: 2 nuevas.
3. **Los mensajes de Telegram eran técnicos.** **Hecho.** `/plan` y el envío diario ahora dicen solo qué hacer:
   vender primero, comprar después, precio límite, el rango cuando el precio es aproximado y si el efectivo alcanza.
   También cubren la captura vieja, las reglas del Reto, el evento macro y el rango esperado al cierre. El formato
   completo sigue en `/completo`, `/detalle` y `/boletas detalle`. `alertas.formato_plan = "completo"` restaura el
   envío anterior.
4. **La referencia del plan rinde menos que 1/N fuera de muestra** (+1.1 % contra +10.8 % anual, 84 sesiones).
   **Decisión** pendiente desde el 30-sep: seguir con «plusvalía» o usar pesos iguales como referencia.

### Impacto medio

5. **Fondos: 25/25 con precio, pero solo 5 sesiones de historia** (hoja pública diaria de Actinver desde el 28-sep).
   Quedan fuera de las propuestas por «sin datos suficientes». La historia crece una sesión por día. **Hecho**:
   ACTIRVT y PROTEGE incorporados, con NAV del 28-sep al 2-oct desde las hojas ya guardadas.
6. **Cada cambio de código o de catálogo invalida todas las propuestas** (huella de cálculo). Durante el recálculo
   (varios minutos) `/plan` responde «no cambies nada todavía». Mejora: servir la versión anterior marcada como
   «anterior al cambio» mientras se recalcula, solo si el cambio no afecta pesos.
7. **Ventas no liquidadas.** Las compras solo usan el efectivo confirmado, no el de las ventas del mismo día. Falta
   confirmar en el portal si el dinero de una venta aparece al momento en «Poder de compra». Si aparece, el plan
   puede hacer la rotación completa en un día; si no, toma dos. **Decisión/dato del usuario**: una captura justo
   después de una venta lo resuelve.
8. **AAXJ y NAFTRAC sin historia** (ETF del simulador). NAFTRAC depende del mismo cupo de EODHD (punto 1).

### Impacto bajo

9. Boletas con vencimiento corto (válidas hasta las 08:45 del día siguiente cuando el precio es aproximado), lo
   que obliga a regenerarlas en la mañana. Es intencional (precio viejo), pero conviene decirlo en el mensaje.
10. `data/terminal_errores.log` recibe líneas INFO (p. ej. «bot de Telegram activo»): ruido en el archivo de errores.
11. Experimento Kronos sin terminar por memoria (de antes; sin cambios).
12. Monitor en la nube: falta comprobar un aviso real de relevo (de antes; sin cambios).

## 3. Lo que NO se hizo, a propósito

- No se conectó ninguna fuente de pago ni se automatizó el portal del Reto (reglamento y mandato).
- No se metieron noticias al optimizador sin prueba fuera de muestra.
- No se cambió el criterio del plan (decisión del usuario, punto 4).
