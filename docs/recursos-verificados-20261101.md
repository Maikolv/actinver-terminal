# Recursos verificados e incorporación — 1-nov-2026

El usuario aportó las descripciones de London Strategic Edge y KolaTrade y confirmó que
CMXT se refería a **pmxt-dev/pmxt**, y microestructura a **philippdubach/polymarket-microstructure**.
No se leyó el video de Instagram ni se comprobó la correspondencia exacta descripción/ID.
No se enviaron comentarios EDGE, mensajes ni formularios externos.

## Repositorios locales y estrellas

- **londonstrategicedge/lse-data**: C:\Users\MIKE\Desktop\Repos\lse-data; commit `d504065a5cdde9ed704bafa339e6a9b474910146`; estrella verificada: True. Licencia API: MIT.
- **evan-kolberg/prediction-market-backtesting**: C:\Users\MIKE\Desktop\Repos\prediction-market-backtesting; commit `c76e77af00ef53472a9da8f66dae7fdd2d3e5928`; estrella verificada: True. Licencia API: NOASSERTION.
- **Jon-Becker/prediction-market-analysis**: C:\Users\MIKE\Desktop\Repos\prediction-market-analysis; commit `2d69f7330fdee142d2cf75d901841f9174fdbbd2`; estrella verificada: True. Licencia API: MIT.
- **pmxt-dev/pmxt**: C:\Users\MIKE\Desktop\Repos\pmxt; commit `4a367d812541154002eedda36b0916a3cf68e0f2`; estrella verificada: True. Licencia API: MIT.
- **philippdubach/polymarket-microstructure**: C:\Users\MIKE\Desktop\Repos\polymarket-microstructure; commit `c20b9037bc67f3602ec1971b3b6e7283ae2eee7f`; estrella verificada: True. Licencia API: MIT.

Los cinco clones y estrellas son nuevos en esta entrega. No se instalaron dependencias,
no se ejecutaron clientes, estrategias ni recolectores upstream, ni se descargaron los
archivos masivos de mercado. Clones superficiales, LFS sin smudge, hooks desactivados
solo para el comando de clonación; ningún hook global se modificó. La revisión de los
37 repositorios del inventario previo encontró los 37 ya en estrellas; no se duplicaron.

**Licencia especial:** prediction-market-backtesting no es MIT-only. LICENSE delimita
LGPL-3.0-or-later para prediction_market_extensions y archivos derivados de NautilusTrader;
MIT para los archivos propios indicados. No se copió ese código al proyecto MIT.

## Qué quedó implementado

- **Datos alternativos:** respaldo optativo FredMacroLaboral para UNRATE/PAYEMS/CPIAUCSL,
  tres consultas reales HTTP 200 y 81 observaciones. La base habitual conserva BLS para
  meses iguales/más recientes. No resuelve la cobertura BMV ni se activa automáticamente.
- **LSE Data:** cliente propio `terminal/lse_lectura.py` para catálogo y muestras de hasta
  diez velas. Solo GET, clave en cabecera, redirecciones bloqueadas, cuotas locales,
  validación OHLCV y timestamps, sin exportaciones/jobs/streaming, escritura de precios
  ni alimentación de modelos. Apagado por defecto y probado mediante HTTP simulado;
  **acceso real pendiente de clave propia y consulta autorizada**.
- **Secuencias y restricciones:** calculadora propia en
  `/static/recursos/lab-secuencias.html`, accesible por el selector global. Diez mil
  iteraciones predeterminadas, semilla reproducible por intento, drawdown estático o
  trailing al cierre de trade/día, costos y límites hipotéticos. Datos independientes
  e idénticamente distribuidos, binarios y con riesgo fijo: no replica fielmente una
  evaluación real ni modela MAE/MFE intratrade. Se separan aprobados, fallidos e inconclusos.
  No se presentan resultados de KolaTrade como aprobados ni probabilidades reales.
- **Futuros Lab:** inventario, referencias de compatibilidad y acceso al mismo laboratorio
  en `artifact/laboratorio-secuencias.html`; no hay un segundo algoritmo divergente.
- **Quantower/TradingView:** documentos de integración y límites actualizados; no se cambió
  una DLL, Pine, broker o puente ni se inició ejecución.

## Condiciones y límites que importan

El README oficial de lse-data anuncia un plan de archivo gratuito y licencia MIT para
la biblioteca. Sus docs/api.md distinguen nueve mercados incluidos de **cme** y **nasdaq**,
que requieren planes de pago. `futures` genérico no demuestra DOM CME gratuito ni permite
sustituir NQ/MNQ con CFD o cripto. No se verificaron acceso real, licencia de redistribución,
moneda, latencia o zona horaria de una muestra de la cuenta. La lista revisada tampoco
acredita un mercado de acciones BMV. No se contrata ni intenta eludir un permiso.

El sitio público de KolaTrade describe también funciones de liquidación y cancelación
automática; **no se conectan**. El enlace directo al optimizador Monte Carlo descrito
por el usuario no se pudo verificar en la lectura pública. Nuestra calculadora es
original, con supuestos explícitos: no una copia ni una validación de ese servicio.

Los datasets Polymarket/Kalshi y sus estudios son material de investigación de mercados
predictivos, no datos de CME ni evidencia de una estrategia NQ. El análisis de agresor,
latencia y fills puede orientar pruebas metodológicas, sin transferir resultados o alfa.
No se ejecutaron sus scripts de scraping ni loggers.

## Pasos manuales, solo cuando corresponda

1. Si desea probar LSE, obtenga usted una clave del plan incluido en
   https://londonstrategicedge.com/data/ tras revisar condiciones. Configúrela mediante
   el mecanismo habitual como LSE_API_KEY; nunca la pegue en el chat. No comprar CME.
2. Twelve sigue sin clave disponible y su consulta autorizada no se consumió. Sitios:
   https://twelvedata.com/register y https://twelvedata.com/account/api-keys. Una clave
   Basic no acredita XMEX; no es necesario contratar para seguir con el laboratorio.
3. Para atribuir cada recurso al post exacto aún hace falta su enlace directo asociado
   o el texto que identifique el ID. El contenido aportado ya se incorporó como recurso
   del usuario, sin inventar esa correspondencia.

Prompt de optimización: docs/prompt-optimizacion-recursos-20261101.md. No autoriza operar.

## Verificación final de esta entrega

- Python completo, sin red externa: **854 aprobadas, 1 advertencia de dependencia**, 823.28 s, salida 0. Evidencia: `proveedores-20261101-evidencia/reels-nuevos-pytest-completa-20261101.txt`.
- JavaScript completo: **48 aprobadas, 0 fallidas**, 2089.9101 ms. Evidencia: `proveedores-20261101-evidencia/reels-final-node-20261101.txt`.
- Worker: **19 aprobadas, 0 fallidas**, 1104.7426 ms. Evidencia: `proveedores-20261101-evidencia/reels-nuevos-worker-20261101.txt`.
- Chromium aislado: **4 recorridos aprobados** (1440/390 px, claro/oscuro), sin errores JavaScript, sin desbordamiento horizontal y sin solicitudes distintas de GET. Proveedores externos bloqueados: esto prueba interfaz y cálculo, no disponibilidad de proveedores. Capturas y resultados en `proveedores-20261101-evidencia/lab-secuencias-ui/`.
- El cálculo monetario del simulador usa centavos enteros, rechaza subcentavos y muestra la relación ganancia/pérdida efectiva después del redondeo. Las pruebas incluyen el objetivo de diez centavos con riesgo de un centavo para evitar un trade adicional por error binario.
- Consulta de solo lectura de `futuros-lab/scripts/estado_demo.py`: adaptador, live y fondeada apagados; sin diario real disponible, incidentes no auditados y sin ventaja demostrada. El modo PAPER no significa que se hayan autorizado o realizado operaciones.

La captura visual anterior al último arranque fue seguida por un intento que devolvió conexión rechazada mientras el servidor aislado todavía iniciaba. Ese intento no demuestra un fallo del producto ni una revisión visual aprobada; la repetición se registra en `proveedores-20261101-evidencia/lab-secuencias-ui/resultado.json`.
