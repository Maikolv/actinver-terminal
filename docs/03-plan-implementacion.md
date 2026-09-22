# 03 · Plan de implementación por etapas

Estado al 2026-09-22: etapas 0–6 **completadas** en esta entrega; etapa 7 depende de decisiones del usuario.

| Etapa | Entregable | Depende de | Riesgos | Mitigación | Estado |
|---|---|---|---|---|---|
| 0. Auditoría | Transcripción del PDF, inventario de repositorios, revisión de secretos | — | PDF sin texto; símbolos ambiguos | Lectura visual página por página; verificación independiente | Hecho |
| 1. Universo verificado | `config/universo.csv` reproducible desde fuentes oficiales | 0 | Claves reasignadas o deslistadas; secciones mal rotuladas | Validación por nombre de emisor; estados explícitos | Hecho |
| 2. Datos | Adaptadores, límites, vigencia, calendarios, FX | 1 | Fuentes gratuitas sin BMV o con límites bajos; términos de uso | Adaptadores sustituibles; CSV del usuario; sin extracción no permitida | Hecho |
| 3. Seguimiento | Libro, importación, auditoría, TWR/TIR | 1 | Errores de cálculo; duplicados | Pruebas con valores calculados a mano; huella; todo-o-nada | Hecho |
| 4. Propuestas | Optimización, validación, sensibilidad, escenarios, puntuación, cambios | 2, 3 | Sobreajuste; inestabilidad de pesos; datos insuficientes | Contracción de μ, Ledoit-Wolf, L2, walk-forward con costos, banda; suspensión | Hecho |
| 5. Interfaz | Web local accesible y adaptable | 3, 4 | Complejidad visual; XSS | Seis pestañas, jerarquía clara; DOM por `textContent`; CSP | Hecho |
| 6. Seguridad y pruebas | Controles HTTP, 44 pruebas, documentación | 1–5 | Regresiones | `uv run pytest` antes de cada cambio | Hecho |
| 7. Datos reales | Credenciales, NAV de fondos, confirmación de ETF en el SIC | Usuario | Costos de planes; cobertura BMV | Empezar con Tiingo + Banxico gratis; EODHD de pago solo si hace falta la BMV diaria | Pendiente del usuario |
| 8. Opcional | Tiempo real, acceso desde el móvil por red, notificaciones | 7 | Exposición de red; costos | Ver [12-seguridad.md](12-seguridad.md) antes de exponer | Previsto |

## Dependencias técnicas

- Python 3.12 (instalado por uv), FastAPI, Uvicorn, pandas, NumPy, skfolio 1.3 (con cvxpy/Clarabel), exchange-calendars, httpx, xlrd.
- Sin dependencias de interfaz (HTML/CSS/JS nativos).

## Riesgos residuales

1. **Cobertura BMV**: el plan gratuito de EODHD (20 peticiones/día) actualiza ~18 emisoras por día; la primera carga completa tarda varios días o requiere plan de pago.
2. **Precio SIC**: se valora con el mercado de origen convertido a MXN; puede diferir del precio en la BMV por spread y horario.
3. **Modelo**: con datos ruidosos la selección de acciones rota bastante entre ventanas (se informa en «costos» y «estabilidad»).
4. **Fondos**: sin API pública; dependen de la importación de NAV.
