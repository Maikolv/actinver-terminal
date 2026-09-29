# Resumen ejecutivo — Actinver Terminal

*Estado comprobado al 29 de septiembre de 2026 · versión 0.12.1*

## Qué es

Terminal local para participar en el **Reto Actinver 2026**:

- sigue la cartera real del participante;
- propone asignaciones que cumplen las reglas del concurso;
- vigila la calidad de los datos;
- avisa cuándo conviene **revisar** algo.

Corre en la computadora del participante (`127.0.0.1`), cuesta $0 y **nunca opera**. No inicia sesión en el portal, no extrae datos de él y no envía órdenes, como exige el reglamento (§17). Cada decisión y cada orden las toma y las captura el participante.

## Qué problema resuelve

El simulador del Reto da un saldo de 1 000 000 de actipesos y seis semanas para obtener la mayor ganancia, con dos condiciones de elegibilidad:

- haber operado al menos 5 acciones distintas;
- no haber hecho una compra de más del 50 % en una sola acción.

Además, cada operación paga comisión (0.10 %) más IVA. Sin una herramienta, el participante tiene que llevar esos límites, los costos y el seguimiento a mano, y con información de calidad desigual. La terminal centraliza todo eso y distingue explícitamente entre:

- lo observado;
- lo retrasado;
- lo que solo es una estimación.

## Qué hace hoy

| Área | Capacidad |
|---|---|
| **Reglas del Reto** | Configuración versionada con el fragmento oficial de cada regla. Práctica y competencia separadas; la competencia reinicia el saldo. Control de 5 acciones y del límite del 50 %. Comisión e IVA desglosados. Aviso si las bases cambian |
| **Cartera** | Solo las operaciones confirmadas cambian la tenencia. Ganancia absoluta y porcentual. Comparación con el saldo que el participante captura del portal |
| **Propuestas** | 4 carteras (solo acciones o mixta; lente de máximo rendimiento o de ajuste al perfil) optimizadas con skfolio bajo las restricciones del Reto, con títulos enteros y costos |
| **Pasado · Presente · Futuro** | Hechos con la hora en que se supo cada uno; estado observable ahora; pronósticos siempre rotulados como estimación |
| **Calidad de datos** | Un precio solo es «confiable» si una fuente verificó ese instrumento exacto en pesos. La propia base de datos rechaza un dato marcado como «tiempo real» sin latencia medida, una noticia «conocida» antes de publicarse y un precio en dólares como serie del SIC |
| **Alertas** | Concentración, cinco acciones, pérdida máxima, diferencia con el portal, cambio brusco, eventos, deterioro del modelo. Todas dicen **REVISAR** e incluyen una ficha: qué ocurrió, datos, qué falta confirmar, costos, riesgos y opciones. Sin precio confiable, las alertas de compra o venta se bloquean |
| **Investigación** | Validación cronológica con embargo y purga, prueba final intacta, registro de todos los experimentos y comparación contra referencias simples con prueba de significancia |

## Evidencia de calidad

- **203 pruebas automáticas** superadas el 29-sep-2026, incluidas pruebas que detectan series de fondos incorrectas y datos mal etiquetados.
- **Lighthouse:** escritorio 100/100/100; móvil 93/100/100 (rendimiento, accesibilidad, buenas prácticas).
- **Backtest:** un motor independiente por eventos (backtrader) coincide **exactamente** con el cálculo propio, en datos sintéticos y reales.
- **Secretos:** 0 hallazgos en el historial de Git.
- **Repositorios:** los 63 del inventario se evaluaron con commit, licencia y evidencia de uso.

## Resultados, con honestidad

Se probó el modelo predictivo con datos reales de índices de EE. UU. (FRED, 2016–2026, periodo de prueba de febrero de 2025 a septiembre de 2026):

| Horizonte | Veredicto | Por qué |
|---|---|---|
| Próxima sesión | **Sin ventaja demostrada** | Error casi igual al de «sin cambio» (p = 0.38) y peor resultado neto |
| Cinco sesiones | **Sin ventaja demostrada** | Error menor que las tres referencias, pero no significativo frente a «sin cambio» (p = 0.13), y con una caída máxima mayor |

Conclusión: **la terminal no emite recomendaciones de cambio basadas en el modelo**. Sus propuestas se apoyan en diversificación y control de riesgo, no en predecir precios. El modelo fundacional Kronos quedó instalado, pero su experimento completo no terminó por falta de memoria en el equipo.

## Estado de datos y limitaciones actuales

La terminal muestra **148 de 174 instrumentos con precio**: 41 vigentes, 107 retrasados porque corresponden al cierre de la sesión anterior y 26 emisoras BMV sin datos. Los 23 fondos Actinver tienen NAV en la hoja oficial del 28-sep-2026; `JPMRVUS` está identificado como serie B-1. El tipo de cambio proviene de Banxico. Las cotizaciones del SIC son referencias calculadas a partir del mercado de origen y el tipo de cambio, no precios ejecutables del SIC.

1. **Cuenta del Reto:** aún no hay captura del saldo y posiciones del portal. El millón inicial de la terminal es un registro local de práctica; no está confirmado por Actinver. El participante debe copiar la tabla del portal en «Mi cartera» → «Capturar desde el portal».
2. **Precios BMV pendientes:** el cupo gratuito de EODHD permite cargar gradualmente 24 de las 26 emisoras sin historia; TERRA 13 y SMARTRC requieren otra fuente o confirmación de cobertura. La actualización completa diaria supera el cupo gratuito.
3. **Tiempo real:** no hay licencia activa para BMV/SIC en tiempo real. La integración Infosel está preparada, pero requiere contrato, URL de producción y credencial. Ningún cierre diario debe mostrarse como una cotización actual.
4. **Catálogo del simulador:** la elegibilidad de instrumentos dudosos, en particular TERRA 13 y SMARTRC, requiere cotejo visual con el portal oficial.
5. **Alertas:** escritorio y Telegram están activos; el correo requiere los parámetros SMTP del usuario. La terminal propone y avisa, pero cada orden la decide y captura el participante.
6. **Modelo predictivo:** la validación histórica no demostró ventaja; las puntuaciones de propuestas se calculan con una ventana fuera de muestra corta y no garantizan rentabilidad.

## Acciones para completar la operación

| Acción | Quién la realiza | Resultado |
|---|---|---|
| Capturar saldo, efectivo, fecha y posiciones visibles del portal | Participante | Cartera confirmada y comparación de cambios real |
| Confirmar TERRA 13 y SMARTRC en el catálogo del portal | Participante | Elegibilidad sustentada para las propuestas |
| Mantener la terminal encendida para la cola de EODHD | Terminal | Recuperación gradual de emisoras BMV dentro del cupo gratuito |
| Contratar una fuente con licencia BMV/SIC y aportar su configuración | Participante, si desea tiempo real | Cotizaciones según cobertura y derechos del contrato |
| Configurar correo SMTP | Participante, si desea ese canal | Alertas por correo además de Telegram y escritorio |

## Cómo usarla

```bat
cd C:\Users\MIKE\Desktop\Repos\actinver-terminal
.\start.bat
```

Se abre en http://127.0.0.1:8765. Con `.\start.bat demo` se abre la demostración con datos simulados.

Más detalle: `README.md` y la carpeta `docs/` (auditoría, reglas, fuentes, metodología, ficha del modelo).
