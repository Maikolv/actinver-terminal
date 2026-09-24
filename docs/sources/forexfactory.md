# Forex Factory — https://www.forexfactory.com/

- **Finalidad:** calendario macroeconómico (inflación, empleo, tasas, bancos centrales) para anticipar volatilidad en USD/MXN.
- **Modalidad:** el **feed de exportación semanal** que enlaza el propio sitio (`nfs.faireconomy.media/ff_calendar_thisweek.json`). Se consulta como máximo una vez por hora. Forex Factory **no** tiene una API documentada y no se le atribuye ninguna.
- **Medición del 2026-09-24 02:14 UTC:** HTTP 200, latencia de 0.62 s, 80 eventos de la semana en curso. Las horas vienen con su zona (`-04:00`) y se normalizan a UTC y a America/Mexico_City.
- **Datos:** país, título, importancia declarada, hora prevista, pronóstico (consenso) y dato previo. El feed **no trae el dato efectivo**: la columna `actual` queda vacía hasta que exista una fuente con permiso. Las revisiones del dato no se reconstruyen.
- **Tiempo:**
  - `event_time` = hora prevista del anuncio.
  - `available_at` = hora en que la terminal obtuvo el consenso.

  Para uso histórico solo cuenta el consenso vigente a esa hora de disponibilidad. No se reconstruye un consenso pasado.
- **Uso:** alerta «evento de alto impacto próximo» (USD/MXN, 24 h). No es variable del modelo hasta tener una historia con disponibilidad trazable.
- **Limitaciones:** solo la semana en curso; sin historia descargable autorizada.
