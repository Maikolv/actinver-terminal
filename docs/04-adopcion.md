# 04 · Plan de adopción

## Arranque en un comando

```bat
start.bat
start.bat demo
```

El primero usa datos reales (con las claves de `.env`); el segundo, datos sintéticos en una base separada. `start.bat` verifica `uv`, instala dependencias la primera vez y abre `http://127.0.0.1:8765`.

## Antes del 5 de octubre (Reto)

1. Inscribirse en retoactinver.com (reglamento: hasta el 4 oct 23:59; la portada sugiere el 2 oct).
2. En la semana de práctica (28 sep–2 oct), exportar o copiar la lista de instrumentos del simulador y cargarla en «Mi cartera → Importar → Lista de instrumentos del simulador».
3. Configurar `.env` (Banxico, Tiingo y, si se quiere cobertura diaria de la BMV, EODHD) y opcionalmente `SEC_USER_AGENT`.
4. El 5 oct, registrar la aportación de 1 000 000 y cada orden ejecutada en el simulador (la comisión de 0.10 % + IVA se calcula al capturar).
5. Dejar la terminal abierta en horario de mercado: el motor recalcula y avisa.

## Semana 1 — Instalar y conocer (sin riesgo)

1. Instalar uv (si no existe): `winget install astral-sh.uv`.
2. `cd C:\Users\MIKE\Desktop\Repos\actinver-terminal` → `uv sync` → `uv run pytest` (deben pasar 44 pruebas).
3. `uv run terminal demo`: recorrer las seis pestañas con datos sintéticos (base separada en `data/demo/`). Opcional: `uv run python scripts/cartera_demo.py` e importar `data/demo/cartera_demo.csv` para ver el seguimiento.
4. Leer «Ayuda» dentro de la terminal y [02-prd.md](02-prd.md) §Límites.

## Semana 2 — Datos reales

1. Crear `.env` desde `.env.example`.
2. Registrar un token gratuito de Banxico (tipo de cambio FIX) y una clave gratuita de Tiingo (emisoras del SIC y ETF). La creación de cuentas y la aceptación de términos las hace usted.
3. Decidir cobertura BMV: EODHD gratuito (lento, 18 emisoras/día con el margen configurado) o plan de pago; alternativa: importar cierres propios por CSV.
4. `uv run terminal actualizar` y revisar la pestaña **Datos**: cada proveedor debe verse «Configurado» y con última corrida «ok».
5. Exportar de Actinver el valor liquidativo de los fondos que le interesan e importarlo (tipo «Precios / valor liquidativo», `tipo_dato=nav`).

## Semana 3 — Su cartera

1. Registrar el saldo inicial con **Posiciones iniciales** (fecha, instrumento, cantidad, costo promedio) o, mejor, el historial de operaciones con la plantilla de **Operaciones**.
2. Verificar que efectivo, posiciones y costo promedio coinciden con su estado de cuenta; corregir con «Corregir» (queda auditado).
3. Ajustar **Perfil** (riesgo, horizonte, capital, topes, exposición USD) y los supuestos de costos en `config/local.toml` según su contrato.
4. Recalcular y revisar: puntuación, motivos, riesgos, escenarios y cambios sugeridos.

## Hábitos recomendados

| Momento | Acción |
|---|---|
| Tras cada operación real | Registrarla (o importar el estado de cuenta del mes) |
| Semanal | «Actualizar datos» → «Recalcular propuestas» → revisar cambios que superen la banda |
| Mensual | `uv run terminal respaldar`; conciliar con el estado de cuenta |
| Trimestral | Revisar supuestos de costos, perfil y pesos de la puntuación; re-verificar universo |

## Configuración de ejemplo (`config/local.toml`)

```toml
[costos]
comision_pct = 0.0020      # su comisión pactada

[perfil]
riesgo = "conservador"
horizonte_anios = 3
capital = 400000

[app]
actualizacion_automatica = true   # consulta tras el cierre mientras la terminal esté abierta
```

## Cómo desinstalar

Borrar la carpeta del proyecto. Antes, conserve `data/terminal.db` y `data/respaldos/` si quiere guardar su historial.
