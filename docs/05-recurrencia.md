# 05 · Plan de recurrencia

## Actualización de datos

| Qué | Cuándo | Cómo | Límite |
|---|---|---|---|
| Tipo de cambio (Banxico FIX o FRED) | Días hábiles, tras las 17:45 CDMX | `uv run terminal actualizar` o tarea programada | 200/día Banxico, 50/día FRED (configurado) |
| Cierres SIC y ETF (Tiingo) | Días hábiles NYSE, tras el cierre | Igual; incremental desde la última fecha | 45/h, 900/día |
| Cierres BMV (EODHD) | Días hábiles BMV | Igual; prioriza instrumentos en cartera | 18/día (plan gratuito) |
| NAV de fondos | Cuando el usuario exporte su estado/hoja de precios | Importar CSV (`tipo_dato=nav`) | — |
| Universo verificado | Trimestral o ante eventos corporativos | `uv run python scripts/verificar_universo.py --descargar` y revisar diferencias con `git diff config/universo.csv` | 3 descargas públicas |

Tareas de Windows opcionales (las registra el usuario): `scripts/programar_tareas.ps1` crea «Terminal portafolios - actualizar» (lun–vie 17:45) y «Terminal portafolios - respaldo» (diario 22:00). La actualización automática dentro del servidor se activa con `[app] actualizacion_automatica = true`.

## Revisión del modelo

| Frecuencia | Revisión | Señal de alerta |
|---|---|---|
| Cada recálculo | Estabilidad de pesos, rotación en validación, calidad de datos | Estabilidad < 50 %, rotación > 100 % por ventana, calidad < 70 % |
| Trimestral | Comparación fuera de muestra propuesta vs 1/N vs actual | Propuesta peor que 1/N en Sharpe durante 2 trimestres |
| Semestral | Supuestos de costos, spreads, impuestos, pesos de la puntuación, umbrales de vigencia | Comisiones del contrato distintas a las configuradas |
| Anual | Versiones de skfolio/cvxpy; reproducir una propuesta guardada y comparar huella | Diferencias de pesos con la misma huella de datos |

## Mantenimiento

- Dependencias: `uv lock --upgrade` + `uv run pytest` trimestralmente; revisar avisos de seguridad de FastAPI/Starlette.
- Registros: `data/logs/terminal.log` rota a 2 MB × 5 archivos.
- Limpieza: propuestas antiguas se conservan para trazabilidad; si la base crece, exportar y podar la tabla `propuestas`.

## Copias de seguridad

- `uv run terminal respaldar`: copia en caliente con la API de respaldo de SQLite, `PRAGMA integrity_check`, conteo de operaciones y rotación (conserva 14).
- **Prueba de restauración (mensual)**: detener la terminal, copiar un respaldo a una carpeta temporal y abrirlo con `TERMINAL_DATA_DIR=<carpeta> uv run terminal iniciar`; verificar que la cartera coincide.
- **Restaurar**: detener la terminal, renombrar `data/terminal.db` y copiar el respaldo elegido como `data/terminal.db`.
- Recomendado: copiar `data/respaldos/` a un disco externo o nube cifrada del usuario (contiene su historial financiero).

## Monitoreo

- Barra superior: conteo por vigencia, tipo de cambio y última sesión; «Operaciones reales: deshabilitadas».
- Pestaña Datos: última corrida por proveedor, errores y peticiones restantes.
- Tabla `ingestas` (SQLite) con cada corrida; tabla `auditoria` con cada alta, corrección, anulación, importación y cambio de perfil.
