# Titulares: léxico frente a LLM locales (6-oct-2026)

## Conjunto de evaluación

`docs/evidencia/titulares/conjunto_eval.csv`, con 161 titulares de Seeking Alpha publicados entre mar y oct-2026 y
fechados:
- los 71 que el léxico marca de alto impacto;
- 90 elegidos al azar entre el resto, con semilla 20261006;
- sin duplicados ni transcripciones.

Cada titular se etiquetó como positivo (66), negativo (29), neutral (37) o ambiguo (29), según su efecto probable en
la emisora indicada. Además se marcó si es relevante para invertir (110 de 161).

**Quién etiquetó.** Las etiquetas las hizo el asistente (Claude), leyendo cada titular, y están **pendientes de
revisión del usuario**: la columna `nota` explica cada una. Como el etiquetador también es un modelo de lenguaje, la
comparación podría favorecer a los LLM. Se mitiga usando los mismos 161 ejemplos para todos los métodos y
reportando los errores costosos por separado.

Los titulares son datos: el prompt los delimita y ordena no seguir instrucciones que contengan.

## Resultados (mismos ejemplos, CPU Ryzen 7 3700U, 5.9 GB de RAM)

| Método | Acierto (4 clases) | Acierto sin «ambiguos» | Dirección invertida (pos↔neg, relevantes) | Negativos relevantes no detectados | Precisión en «negativo» | Latencia por titular | Pico de RAM |
|---|---|---|---|---|---|---|---|
| **Léxico actual** | 47 % | 57 % | **2** | 13/29 | 59 % | ≈0 ms | 33 MB |
| Qwen2.5-0.5B-Instruct Q4_K_M (491 MB) | 29 % | 36 % | 1 | 29/29 | — | 1.45 s | 411 MB |
| Qwen2.5-1.5B-Instruct Q4_K_M (1.1 GB) | 58 % | 70 % | **9** | **1/29** | 37 % | 3.5 s | 976 MB |

LLM ejecutados con `llama-cpp-python` 0.3.2 (CPU, entorno aislado, sin servicio residente), temperatura 0. Salida:
`docs/evidencia/titulares/resultado_*.json` y `resumen.json` (`scripts/evaluar_titulares.py`).

## Decisión: se conserva el léxico

**Qwen 1.5B:**
- Detecta casi todos los negativos, pero para hacerlo marca 76 de 161 titulares como negativos: precisión del 37 %.
- Invierte la dirección de 9 titulares positivos relevantes. Le bastan palabras como «wrong», «misled» o «hiccups»
  en titulares alcistas.
- En la terminal, un titular negativo de alto impacto inhibe las alertas de compra o venta. Con este modelo se
  inhibirían con mucha más frecuencia y por error.
- Cuesta 1 GB de RAM y 3.5 s por titular, en un equipo con 0.4–0.6 GB libres.

**Qwen 0.5B:** nunca clasifica un titular como negativo. No sirve.

La integración opcional por Ollama (`OLLAMA_URL`) sigue desactivada. La mejora no compensa su costo operativo ni sus
errores de dirección.

### Dónde falla el léxico (13 negativos relevantes no detectados)

- **Rebaja dentro de un titular mixto:** «Gerdau upgraded, Ternium downgraded…». Aparece «upgraded» y empata.
- **Negativos sin palabra clave:**
  - «Trump administration mulls new round of tariffs on chips» (aranceles se marca de alto impacto, pero no negativo);
  - «Coca-Cola: Not At This Price»;
  - «Citi's London branch fined…»;
  - «RFK Jr. is probing…»;
  - «Micron: Exit Before It's Too Late».
- **No tiene clase «ambiguo»:** los 29 ambiguos cuentan como error.

Esas palabras («fined», «probing», «exit», «tariffs» como negativo) no se agregaron al léxico. Hacerlo después de ver
el conjunto de evaluación sería ajustar el método a la prueba. Una mejora del léxico necesita un conjunto nuevo,
etiquetado por el usuario, para medirla.
