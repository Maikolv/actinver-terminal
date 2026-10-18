# Auditoría general — 18-oct-2026

Base: `main` en d9f2f88 (ya en GitHub), más el trabajo sin commitear de otra sesión (11 archivos modificados y 5
rutas nuevas). Todo lo que sigue se ejecutó hoy, salvo donde se indica.

## 1. Seguridad: sin hallazgos graves

| Control | Resultado |
|---|---|
| Escucha local | `terminal/__main__.py` rechaza cualquier host distinto de 127.0.0.1, localhost o ::1 |
| Órdenes | Ninguna ruta de órdenes. `tests/test_tiempo_real.py` prohíbe `/v2/orders`, `/v2/positions` y `/v2/account` en el código de Alpaca |
| Secretos | `.env` y `data/` están ignorados; `.env` nunca entró al historial. `detect-secrets` sobre los archivos versionados: 7 hallazgos, todos claves de prueba o huellas sha256 (`vector_firma.json`, tests y evidencias) |
| POST | CSRF, origen local, tamaño máximo y límite por minuto |

## 2. Dependencias

| Hallazgo | Severidad | Acción |
|---|---|---|
| `multidict 6.7.1`, aviso **PYSEC-2026-4244** (corregido en 6.9.1); llega por `ccxt → aiohttp`, en el grupo `cripto`, que se instala por omisión | Media: lo usa el adaptador de Bitso, que hace llamadas salientes | `uv lock --upgrade-package multidict` |
| Desactualizados: anthropic 1.9.0 → 1.15.0; fastapi 0.141.1 → 0.143.3; numpy 2.5.3 → 2.5.4; pypdf 6.19.0 → 6.21.1; skfolio 1.3.0 → 1.9.4; uvicorn 0.53 → 0.54; websockets 17.1 → 17.2; ccxt 4.5.85 → 4.5.88 | Baja | Actualizar por grupos y correr la suite; skfolio es el salto mayor (lo usa el optimizador) |
| Worker en la nube: `npm audit` sin vulnerabilidades; wrangler 4.145 → 4.151 | Baja | Opcional |
| Grupo `kronos` (torch) | — | Opcional; sigue sin ventaja demostrada |
| `pyproject.toml` en versión 0.1.0, mientras el CHANGELOG va en v0.30.0 | Cosmética | Alinear |

## 3. Pruebas

- Suite completa (17-oct): **639 aprobadas y 3 fallidas**, en ≈ 9 min. Las 3 vienen del trabajo **sin commitear** de
  otra sesión:
  - `test_tiempo_real.py::test_solo_dominios_de_datos_de_alpaca` ya espera el dominio `paper-api.alpaca.markets`, pero
    el adaptador aún no lo tiene. Es el endpoint de contratos de Alpaca (API de trading), que requería tu autorización
    textual. **Confirma si la diste.**
  - `test_notebook_tema3.py` (2 pruebas): el notebook del tema 3 está en desarrollo.
- No hay integración continua (no existe `.github/workflows`): las pruebas solo corren en esta PC.

## 4. Mantenibilidad

- `web/static/app.js` tiene 2,790 líneas y `terminal/app.py` 1,465. Son los archivos que más se tocan, y dos
  sesiones paralelas los editan a la vez: es el principal riesgo de conflicto y de commits mezclados.
- Documentación desactualizada:
  - en `CLAUDE.md`, el encabezado «Estado comprobado (2026-10-12, v0.30.0)», «Pruebas: 283», «Cuenta del Reto: sin
    captura del portal» y la brecha 3 contradicen las capturas del 6 al 16-oct;
  - `CLAUDE.md` pasa de 300 líneas, lo que encarece cada sesión;
  - `docs/acciones-requeridas-usuario.md` sigue pidiendo aprobar la etapa 2, que se aprobó el 12-oct.

## 5. Datos y modelos

- No hay tiempo real. La BMV depende de EODHD (20 consultas al día). La historia externa termina el 9-oct-2025 y no
  se sabe si incluye dividendos.
- Nada tiene **ventaja demostrada**:
  - validación V1 frente a 1/N;
  - pronóstico al cierre;
  - Kronos;
  - TSM mensual (Holm 1.000 en 6 ETF);
  - Laboratorio y anomalías: solo descriptivos.
- Cartera del Reto (16-oct): −9.36 %, con MU en 45 % del valor. Es un dato de riesgo, no una recomendación.

## 6. Decisiones pendientes del usuario

1. Endpoint de contratos de Alpaca (OI y multiplicador para GEX): confirmar la autorización que la otra sesión parece
   estar implementando.
2. Fuentes de pago: Finviz Elite (USD 39.50 al mes), EODHD (USD 19.99 al mes), crédito de Databento (USD 125, solo
   históricos).
3. Las 9 propuestas de revisión del mandato (pendientes desde el 6-oct).
4. Referencia del plan frente a 1/N (pendiente desde el 30-sep).
