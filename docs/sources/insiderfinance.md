# InsiderFinance — https://www.insiderfinance.io/insider-trades

- **Finalidad:** descubrimiento y contraste de operaciones de personas con información privilegiada (insiders).
- **Modalidad:** producto de suscripción **sin API pública**. Se usa para **lectura humana** y los datos se toman de la **fuente primaria**: SEC EDGAR, Formulario 4 (`terminal/fuentes_web.py::SecEdgar`, que requiere `SEC_USER_AGENT`).
- **Fechas que se distinguen:**
  - **Operación** (`fecha`, transactionDate).
  - **Presentación** ante la SEC (`fecha_presentacion`).
  - **Publicación:** índice EDGAR.
  - **Disponibilidad para el modelo:** `available_at` = cuándo la terminal lo obtuvo.
- **Cobertura:** solo emisoras de EE. UU. Cada registro se marca `NO CUBRE BMV`: una operación de insiders de una empresa estadounidense nunca se atribuye a una emisora mexicana homónima.
- **Estado:** SEC EDGAR conectada con `SEC_USER_AGENT` mediante `terminal/movimientos/` (Form 4 y 13F; ver docs/movimientos-publicos.md). InsiderFinance requiere suscripción y no se usa de forma automática.
- **Limitaciones:** el Formulario 4 se presenta hasta 2 días hábiles después de la operación.
- **Prueba:** `tests/test_fuentes_web.py::test_formulario4_parseo` (distingue la operación de la presentación).
