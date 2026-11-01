# DESIGN.md — sistema visual de Actinver Terminal

Formato inspirado en la colección `awesome-design-md` y en los criterios de `hallmark`: sin estética genérica y con contraste verificado.

## Principio

**Un dato observado, un dato retrasado y un pronóstico nunca se ven igual.**

| Clase de dato | Tratamiento visual |
|---|---|
| Observado y vigente (`REAL_TIME` o EOD de la última sesión) | chip verde «vigente», cifra monoespaciada |
| Retrasado o desconocido (`DELAYED`, `UNKNOWN`) | chip ámbar o gris, con la latencia en segundos al lado |
| Sin precio confiable | chip rojo **SIN PRECIO CONFIABLE**; el motivo se lee al pasar el cursor |
| Referencia externa (bolsa de origen en USD) | columna separada, texto secundario, con la etiqueta «estimado» |
| Pronóstico | sección FUTURO con borde discontinuo y sello violeta «FUTURO · ESTIMACIONES»; rangos 10–90 %, nunca un solo número |
| Ficticio | banda «DATOS SIMULADOS» y la marca «FICTICIO» en cada cotización |

**Cualquier persona puede usar cualquier herramienta sin saber qué escribir.** Toda calculadora o formulario de
cálculo abre con valores iniciales que ya producen un resultado válido, ofrece «Ejemplo listo» o «Escenario listo»
con opciones predefinidas (más «Personalizado») y, cuando el resultado es técnico, lo acompaña de una lectura en
palabras simples. Los ejemplos son hipótesis de estudio y se rotulan así; nunca se presentan como cotizaciones.
Hoy: escenarios NQ en Mesa (`ESCENARIOS_NQ`), ejemplos de Modelos (`EJEMPLOS_OPCIONES`) y ejemplo sintético del
Laboratorio de alfa. `tests/mesa.test.mjs` exige que cada escenario NQ calcule al menos un contrato.

## Tokens

- **Colores:** definidos en `web/static/app.css` (`:root`) para modo claro y oscuro: `--vigente`, `--retrasado`, `--vencido`, `--sin-datos`, `--sintetico`.
- **Contraste mínimo:** 5.24:1 en claro y 6.1:1 en oscuro. Accesibilidad 100 en Lighthouse.
- **Tipografía:** interfaz con Segoe UI y cifras con Consolas (`--mono`); sin fuentes externas.
- **Cuadrícula:** gutter de 16 px; tres cortes: ≤ 720 px, 721–1024 px y > 1024 px.

## Componentes

- **Tarjetas de espacio:** PASADO (borde gris), PRESENTE (borde verde) y FUTURO (borde violeta discontinuo).
- **Ficha de revisión en cada alerta:** qué ocurrió, qué datos lo sustentan, qué falta confirmar, costos, riesgos y opciones para revisar. **No hay botones de operar.**
- **Esqueletos de carga:** tres pulsos como máximo; se respeta la preferencia de movimiento reducido del sistema.

## Accesibilidad

Pestañas con ARIA y navegación con teclado (flechas, Inicio, Fin). Todo el contenido dinámico se crea con `textContent`, nunca como HTML.
