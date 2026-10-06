# Memoria conversacional y recuperación de documentación (evaluación del 6-oct-2026)

## 1. ¿Las preguntas reales necesitan memoria?

**Datos disponibles.** El bot de Telegram no registra el texto de las preguntas libres: solo atiende y responde.
Por eso no hay muestra de preguntas reales al bot. La única evidencia de uso real son las sesiones de trabajo con el
usuario del 30-sep al 6-oct-2026: unas 60 peticiones.

| Tipo de petición | Cuántas (aprox.) | ¿Requería recordar algo? | Dónde estaba ese dato |
|---|---|---|---|
| «Envíame el plan / las boletas por Telegram» | 20 | No | Base local (propuestas, boletas vigentes) |
| «Súbelo a GitHub» | 12 | No | Git |
| Capturas y PDF del portal | 10 | No | Se procesan en el momento |
| Preguntas sobre la cartera («¿por qué FUBO?», «¿conservo QQQ?») | 8 | No, usan el estado actual | Base local |
| Seguimiento inmediato («¿a qué te refieres con +2.2 %?») | 3 | Sí, la respuesta anterior (memoria corta) | La conversación |
| Decisiones previas («la decisión del 30-sep…», «las boletas de la alternativa C») | 3 | Sí, decisiones confirmadas | `docs/decisiones.md`, `CLAUDE.md`, base local y `docs/alternativa-nvda-2026-10-05.md` |
| Texto de un documento antiguo (mandato de autonomía) | 1 | Sí, búsqueda en documentación y registros | Registro de la sesión del 23-sep; ahora en `docs/mandato-autonomia.txt` |

**Conclusión.** Las necesidades de memoria observadas ya se cubren con almacenes persistentes y auditables: el perfil
(criterio del plan), `docs/decisiones.md` (D-xx con fecha), la base local (boletas y capturas) y los documentos
fechados. No se encontró ningún caso que exigiera una memoria conversacional nueva. **No se agrega memoria
conversacional:** sumaría riesgo de guardar datos sensibles sin un beneficio medido.

**Si se quiere medir en el bot:** activar un registro local con consentimiento explícito. Guardaría solo la
categoría de la pregunta y si la respuesta necesitó contexto previo, nunca el texto. Se mediría durante dos
semanas. Queda propuesto, no implementado.

## 2. Recuperación sobre documentación autorizada

Evaluación fija: 15 preguntas redactadas como las reales, cada una con el archivo que la responde
(`scripts/evaluar_busqueda.py`). El script de evaluación se excluye del índice para no contaminar la medición, y las
palabras vacías son genéricas del español: ninguna se eligió a partir de las preguntas.

| Método | Acierto@3 | Tiempo por consulta | Memoria adicional | Estado |
|---|---|---|---|---|
| Conteo de términos por línea (anterior) | 4/15 (27 %) | ≈0.5 s | — | Se conserva como `buscar_conteo` |
| **BM25 por sección, sin modelo** | **13/15 (87 %)** | ≈0.1 s | Ninguna | **Vigente** en `scripts/indice_contexto.py buscar` |
| Semántica (multilingual-e5-small, 118 M parámetros) | 12/15 (80 %) | ≈0.06 s (más 298 s para indexar 612 secciones) | modelo de ≈470 MB más torch | **No se adopta** |

Cada fragmento cita `archivo:línea` y la fecha del archivo. Solo se indexa documentación y configuración del
repositorio: nada de `.env`, `data/` ni textos completos del portal.

Fallos de BM25:
- «¿Me penalizan por comprar ETF o fondos?»: el documento de reglas no usa «penalizan».
- «¿A qué hora abre y cierra la bolsa?»: el horario está en `config/reto.yaml` con otras palabras.

## 3. Decisión

- **Memoria conversacional:** no se agrega. Las necesidades medidas ya se cubren con datos persistentes y auditables.
  Para el bot se propone medirlas primero, con consentimiento.
- **Recuperación:** se adopta BM25 por sección. Mejora de 4/15 a 13/15, sin modelo, sin memoria extra y con citas
  `archivo:línea` y fecha. La semántica e5-small no supera a BM25 (12/15), cuesta 5 minutos de indexado y ~0.5 GB,
  así que no se agrega.
- **Límite:** son 15 preguntas, redactadas por el asistente a partir de las reales; una muestra pequeña.
