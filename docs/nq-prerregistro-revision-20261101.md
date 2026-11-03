# Investigación NQ existente: revisión de evidencia — 1-nov-2026

R31-11 no debe describirse como ausencia total de regla reproducible: Futuros Lab ya contiene un protocolo específico de Noise Bands. Tampoco debe marcarse resuelto como estrategia validada.

## Fuentes locales revisadas

En `C:\Users\MIKE\Desktop\Repos\futuros-lab`:

- `entregables/noise-bands/PRERREGISTRO.json`, ID NB-NQ-20261025-v1.
- `entregables/noise-bands/INFORME_FINAL.md`, `RESULTADOS_BACKTEST.json` y `MANIFIESTO_SHA256.json`.
- `config/preregistro_B_RTH_50k_20261020.json`: protocolo distinto, propuesto para micros; no se fusiona con Noise Bands NQ ni se heredan sus presupuestos.

Noise Bands identifica NQ con vencimiento, tick 0.25 y USD 20/punto; sesión America/New_York 09:30–16:00; 14 sesiones completas previas para sigma, k=1, decisiones semihorarias y variantes A de referencia y B con SL/TP experimental. Costos y slippage son supuestos explícitos. Los criterios exigen al menos 60 sesiones evaluables y 30 operaciones históricas, además de robustez y partición temporal. No se modificaron parámetros ni cálculos.

## Integridad comprobada

Se recalculó SHA256 de los 25 archivos declarados: **25 coinciden, ninguno ausente o diferente**. La huella del prerregistro coincide con `RESULTADOS_BACKTEST.json`. Evidencia nueva: `futuros-lab/docs/noise-bands-integridad-20261101.json`.

Esto prueba consistencia de los archivos locales frente al manifiesto, no una fecha de congelación certificada externamente, acceso a datos nuevos ni ausencia de selección histórica. No se reescribió el manifiesto congelado.

## Lo que sigue faltando

El resultado guardado usa 6901 barras de /NQZ26:XCME y cinco sesiones RTH completas (13, 14, 15, 16 y 19-oct). Está etiquetado HISTÓRICO RETRASADO / DESARROLLO / NO FORWARD. Al no completar el calentamiento de 14 sesiones previas, hay cero sesiones evaluables; el propio expediente declara NO EVALUABLE y no fabrica resultados de operaciones.

No se ejecutó de nuevo el backtest, no se abrió el holdout, no se adquirieron datos ni se convirtió replay en forward. Para evaluar se necesita historia licenciada suficiente del contrato y los campos exigidos por el protocolo. Los resultados publicados sobre SPY no se trasladan a NQ. La existencia de código, protocolo y hashes no demuestra ventaja.

Nada aquí autoriza iniciar estrategias, avisos de entradas o TP/SL actuales, cuentas, puentes, órdenes o pruebas demo. Sigue vigente el mandato de no operar.
