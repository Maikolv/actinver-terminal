# Práctica autorizada

Hoy: usar únicamente replay offline. No activar adaptador_habilitado. No seleccionar Lucid ni cuentas de intermediarios, aunque se llamen demo.

1. Leer PRERREGISTRO.json y MATRIZ_DATOS.md. Mantener PAPER, live_habilitado=false, fondeada_habilitada=false, adaptador_habilitado=false.
2. Ejecutar desde futuros-lab:

```powershell
.\.venv\Scripts\python.exe -m pytest tests	est_nq_investigacion.py -q
.\.venv\Scripts\python.exe -m futuros_lab.nq_investigacion --protocolo entregables
q-investigacion-20261020\PRERREGISTRO.json --datos entregablesmt-lucid\diagnostico-real\_NQZ26_XCME-barras.json --salida entregables
q-investigacion-20261020\RESULTADOS_HISTORICOS.json
```

3. Interpretar cero trades como ausencia de evidencia. No reducir calentamiento ni riesgo para producir operaciones.
4. Para pruebas futuras del conector hace falta controlador nativo disponible, respaldo nuevo verificable, cuenta/símbolo/conexión SDK identificados positivamente como TradingSimulator y build auditado. Cada arranque/parada crea cuenta nueva según documentación Quantower: invalida vínculo anterior. Verificar de nuevo cada mutación. Cotizaciones dxFeed y destino Simulator son funciones distintas.
5. Máximo1NQ ficticio con vencimiento confirmado. Confirmar órdenes protectoras observadas y OCO después del fill; éxito de PlaceOrder no basta. Utilizar MATRIZ_PRUEBAS.csv. No cerrar posiciones ajenas para probar fallos. No iniciar mientras no estén cumplidos los requisitos.
6. Diario técnico separado y marcado PRUEBA SINTÉTICA/REPLAY. No tocar diario forward. Solo datos actuales, calendario cubierto y pruebas técnicas aprobadas permiten iniciar20sesiones y30trades mínimos demo; no garantizan ventaja.
7. Al cerrar, verificar posiciones/órdenes propias en Simulator y estrategias de prueba detenidas, luego candados false. Hoy esas comprobaciones visuales permanecen pendientes; no simular su confirmación.

Interfaz futura sugerida: un gráfico contexto, uno operativo y un panel órdenes/riesgo; flujo solo si existen datos. No se alteraron paneles. Telegram solo información y, si se prueba después, marcar PRUEBA SINTÉTICA y exigir API ok=true; no acredita lectura.
Fuente: https://help.quantower.com/quantower/trading-panels/trading-simulator
