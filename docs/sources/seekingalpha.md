# Seeking Alpha — https://seekingalpha.com/market-news

- **Finalidad:** contexto, noticias, análisis y tesis de acciones, ETF y fondos **extranjeros** (emisoras del SIC). Es la fuente central de la capa de investigación para valores extranjeros. No es fuente de precios.
- **Modalidad:** **RSS público** por emisora (`https://seekingalpha.com/api/sa/combined/<TICKER>.xml`), que no está bloqueado en `robots.txt`. Se guarda solo lo siguiente:
  - titular, URL y emisora vinculada;
  - **autor** (`sa:author_name`);
  - **fecha de publicación** (`event_time`), **fecha de disponibilidad** (`available_at`, cuando la terminal lo obtuvo) y `ingested_at`;
  - **tipo de contenido**: enlaces con `/news` = hecho reportado; `/article/` = opinión o análisis; otro = sin clasificar.

  No se accede a contenido tras inicio de sesión, ni se redistribuye o usa el texto para entrenamiento masivo.
- **Medición del 2026-09-24 02:14 UTC (AAPL):** HTTP 200, latencia de 0.23 s. El titular más reciente tenía 13.2 h de antigüedad; es un feed de noticias, no de tiempo real.
- **Reglas de uso:**
  - Un hecho material se verifica con la emisora o el regulador (`verificado_fuente_primaria`, que por defecto vale 0).
  - Una opinión nunca es señal automática de compra o venta.
  - Una noticia solo entra a las variables después de su `available_at`: lo imponen un disparador de SQLite y `datos.noticias_hasta`.
  - El precio de una acción de EE. UU. que muestre Seeking Alpha **no sustituye** la serie SIC en MXN.
- **Licencia de datos:** sin licencia de datos ni API contratada; uso personal de titulares y enlaces.
- **Alternativas evaluadas:** firecrawl y Scrapling (`repository-adoption-matrix.md`). No se usan para Seeking Alpha.
- **Pruebas:** `tests/test_fuentes_web.py`, `tests/test_ampliacion.py::test_noticia_futura_no_puede_entrar_al_pasado`.
