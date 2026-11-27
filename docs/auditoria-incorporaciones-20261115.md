# Auditoría de incorporaciones — 15-nov-2026

Qué se puede sumar a Actinver Terminal, con costo, riesgo y estado. Regla vigente: **solo recursos gratuitos**.

## 1. Asistente con la API de Gemini — implementado (apagado por defecto)

| Punto | Detalle |
|---|---|
| Qué hace | El asistente de la terminal y las preguntas libres de Telegram responden con Gemini, usando el mismo contexto que ya recibe Claude/Ollama: cartera, plan, fichas, documentación y notas. |
| Cómo se activa | Agregue `GEMINI_API_KEY=` en `.env` (clave de [Google AI Studio](https://aistudio.google.com/apikey)) y `[asistente] gemini = true` en `config/local.toml`. Modelo opcional: `GEMINI_MODELO` (predeterminado `gemini-2.5-flash`). |
| Orden de motores | Claude (si se aprobó su costo) → **Gemini** → Ollama local → respuestas locales sin IA. |
| Costo | Capa gratuita de AI Studio: sin cobro, con límites por minuto y por día. Use una clave de un proyecto **sin facturación**; así nunca hay cargo. Si se excede el límite, la terminal responde con el motor local. |
| Privacidad | En la capa gratuita, Google puede usar lo que se envía para mejorar sus productos. Se envía el contexto de su cartera. Si eso no le conviene, use Ollama, que no sale del equipo. |
| Código | `terminal/bot_telegram.py`: `gemini_habilitado`, `Chatbot._preguntar_gemini`. Es REST con `httpx`, sin dependencias nuevas. |
| Pruebas | `tests/test_seguridad.py::test_gemini_apagado_por_defecto`. Sin llamada real: no hay clave en este equipo. |
| Límites | No se probó con una clave real. Errores 401/403/429 o de red se registran y se pasa al motor local. |

## 2. Otras incorporaciones posibles

| # | Idea | Valor | Costo | Recomendación |
|---|---|---|---|---|
| 2.1 | Gemini para explicar el plan del día en lenguaje sencillo (resumen de 3 líneas) | Alto: el plan es largo | Gratis (misma clave) | Siguiente paso; reutiliza `_preguntar_gemini` |
| 2.2 | Gemini con «grounding» en Google Search para noticias por emisora | Medio | La búsqueda con grounding tiene cuota gratuita limitada | Evaluar cuotas antes de activar |
| 2.3 | Lectura de capturas del portal con Gemini Vision (en lugar del OCR de Windows) | Medio | Gratis con límites | Hoy el OCR local basta y no envía imágenes fuera |
| 2.4 | Embeddings de Gemini para el buscador de documentación del asistente | Bajo | Gratis | El índice local actual funciona sin red |
| 2.5 | Gráfico del portafolio principal frente a la cartera real (seguimiento diario) | Alto | Gratis (datos locales) | Recomendado: completa la función del portafolio principal |
| 2.6 | Exportar el plan a Google Sheets | Bajo | Gratis | Solo si lo pide |
| 2.7 | Aviso de terminal apagada (Cloudflare Worker) | Medio | Gratis | Ya construido; falta `npx wrangler login` del usuario |

## 3. Lo que NO conviene

- Proveedores de datos de pago (Finviz, Databento, EODHD de pago): excluidos por la regla de costos.
- Dar a cualquier IA permiso de operar: la terminal solo informa y simula.
- Publicar datos reales en GitHub Pages: las licencias de los proveedores no permiten redistribuirlos. La demo pública usa datos simulados.
