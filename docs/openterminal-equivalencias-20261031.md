# Catálogo completo de OpenTerminal y decisión de reutilización

Revisión local: `ErTasselli/OpenTerminal`, commit inventariado `aed097c680cd8ec1c391ae06966babe7d6d91fc6`. Fuente: unión `WidgetType` en `web/store/terminal.ts` y switch `WidgetBody` en `web/components/Workspace.tsx`: **15 tipos**. No confundirlos con los 23 paneles iniciales de Mesa. Implementación propia; no se copian código, textos ni marca. MIT upstream no licencia los datos de sus endpoints.

| Tipo upstream | Equivalente Actinver | Decisión y motivo |
|---|---|---|
| quote | Ficha de cotización / catálogo | Externo indicativo, no modelo |
| chart | Velas e indicadores; sección Velas | Externo para comparación, sección nativa para datos locales |
| watchlist | Seguimiento | Acceso nativo existente; no duplicar lista ni polling |
| news | Noticias / instrumento | Externo; fechas y cobertura dependen de proveedor |
| heatmap | Mapa sectorial / ETF | Externo; no exportar cifras al modelo |
| screener | Explorador / Ranking | Externo indicativo y ranking local separado |
| crypto | Mapa cripto | Externo, fuera del Reto y sin sustitución CME |
| macro | Macro e índices / investigación | Externo y series locales con procedencia |
| options | Option Flow | Acceso nativo; cadena indicativa/OI fechado, no señal NQ |
| portfolio | Cartera | Acceso nativo, sin duplicar libro |
| ai | Asistente | Acceso nativo opcional; no cargar modelos grandes |
| calendar | Calendario económico | Externo; earnings/historia de reacción no acreditados por este widget, permanecen parciales |
| insider | Movimientos públicos | Acceso nativo SEC; publicación no es fecha del hecho |
| tv | Paneles TradingView | 16 tipos externos servidos por rutas existentes |
| recap | Plan/resumen y Datos y fuentes | Reutilización parcial; no se añade resumen automático de precios sin fuente/fecha |

## Componente elegido

La búsqueda por teclado del catálogo (concepto de la paleta global de OpenTerminal) faltaba en Mesa: 214 instrumentos obligaban a recorrer un selector largo. Se añade filtro por clave/nombre junto al selector existente; Ctrl/Cmd+K enfoca ese filtro y Escape restaura el catálogo. No duplica cartera, reloj ni navegación. No añade React, Next, Express, paquetes ni llamadas de precios. Mantiene los 23 tipos de panel y la disposición guardada. Diseño mediante etiquetas, controles y colores heredados de `app.css` y espacio de 16 px de `mesa.css`.

El filtro no acredita cobertura de mercado: conserva la bandera `grafica` del catálogo y el estado SIN DATO. Los componentes que dependen de cotizaciones no se convierten en nativos por parecido visual.
