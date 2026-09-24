# Política de ahorro de tokens

Objetivo: dar a un asistente (o a una persona) el **fragmento mínimo con su evidencia** sin releer el repositorio. Ninguna compresión puede eliminar el precio, la moneda, la hora, la fuente, la licencia, la incertidumbre o la condición de una regla. Por eso se cita el texto original con su ruta y línea, en lugar de resumirlo.

## Mecanismos implementados

| Mecanismo | Implementación | Medición |
|---|---|---|
| Índice de archivos con hash y fecha | `scripts/indice_contexto.py construir`: sha256, fecha, líneas y marcas (títulos, `def`, `class`) de 88 archivos | Se reconstruye solo si cambia un hash |
| Recuperación del fragmento mínimo | `buscar "consulta"`: devuelve ≤ N fragmentos de ≤ 7 líneas con `ruta:línea` | «compras en una sola acción 50»: **≈555 tokens frente a ≈7,840** leyendo los archivos completos (−93 %) |
| Caché invalidada por cambios | `_renders/contexto_cache.json`, con claves por consulta y hashes de los archivos citados | La segunda consulta idéntica se sirve «desde caché»; se invalida si cambia algún archivo citado |
| Índice de símbolos del código | `codebase-memory-mcp` (1,193 nodos, 4,837 aristas) | «precio confiable» devolvió 5 funciones con sus líneas en ~200 tokens, frente a ~8,000 del archivo |
| Resúmenes jerárquicos con enlace al original | `README.md` → `docs/*.md` → código; cada documento enlaza a su fuente | — |
| Presupuesto por tarea | Consulta rutinaria ≤ 1,000 tokens de contexto; depuración ≤ 5,000; auditoría completa sin límite, pero con índice primero | Estimado ≈ caracteres / 4 (la plataforma no expone el conteo exacto) |

## Modelos locales

Ollama queda como opción para clasificar titulares. No está instalado en este equipo, así que no hay comparación de calidad, costo y tiempo frente al léxico; queda pendiente. colibri se descartó porque apunta a modelos de 744B a 2.8T parámetros, con un costo desproporcionado para esta tarea.

## Métodos adoptados de otros repositorios

- `context-mode`: salida mínima y recuperación puntual. Se adoptó el método, no el código (Elastic License).
- `attention-span`: primero la respuesta y en lenguaje claro.
- `ponytail`: menos líneas verificables.
- `awesome-llm-apps`: respuestas con cita de ruta:línea.

`anything-llm` (RAG con servidor) se evaluó y no se adoptó: el índice local sin embeddings basta para este tamaño de proyecto.

## Canales y costos de infraestructura

- **Costo actual:** $0. Todo corre local.
- **Costos opcionales:**
  - túnel HTTPS para el webhook (Cloudflare Quick Tunnel sin costo, según free-for-dev; verificar sus límites);
  - datos licenciados de la BMV (costo según contrato);
  - EODHD de pago si hacen falta más de 20 consultas al día.
- agentic-inbox no aporta frente a correo o Telegram.
