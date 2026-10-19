# Contratos Alpaca Paper y notebook del tema 3

Revisión: 18-oct-2026, America/Mexico_City. Autorización del usuario: consulta de
contratos sin suscripciones de pago; tema 3 elegido; mantener Skylit parcial si
no se encuentra una alternativa gratuita verificable.

## Contratos: solo lectura en Paper

- Única ruta permitida: `GET https://paper-api.alpaca.markets/v2/options/contracts`.
  Sin órdenes, cuentas, posiciones, endpoint live ni redirecciones.
- `[flujo.alpaca] contratos_oi = false` por defecto. Actualización bajo demanda,
  caché de una hora por símbolo, rango explícito de hasta 183 días y tres páginas
  como máximo. Se avisa cuando la cobertura queda parcial.
- Guarda OI con `open_interest_date` y `size` como multiplicador, sin suponer 100,
  en `flujo_opciones_contratos`, con procedencia y disponibilidad temporal.
- Solo enriquece campos ausentes; no cambia spot, gamma ni precios. El metadato
  debe ser conocido antes del snapshot y del corte solicitado; el OI debe tener
  fecha anterior a la sesión de Nueva York. OI de más de cuatro días calendario
  queda rotulado como desactualizado. Si solo se completa el multiplicador,
  no se atribuye a Paper el OI que ya existía ni se cambia su fecha.
- GEX muestra la fecha del OI y «cierre previo, no intradía», incluso si no es
  calculable por ausencia de otros campos. OI previo no prueba apertura o lado.
- Consulta real mínima: **éxito**, una petición, SPY, límite de un contrato y una
  página. No se repitió, no se registró respuesta cruda ni valores de credenciales.
  Esto no verifica cobertura del universo ni completa gamma, spot, NBBO o patas.
- El par ya aceptado por Paper quedó bajo nombres específicos en `.env` local,
  ignorado por Git; no se crearon ni cambiaron claves. El adaptador no usa fallback
  a credenciales de mercado. El interruptor conserva su estado apagado.

Uso: configure `contratos_oi = true` en `[flujo.alpaca]` de `config/local.toml`,
reinicie y use «Actualizar OI y multiplicador (Paper)» en Option Flow. Después
actualice la cadena. Las consultas nunca ocurren automáticamente ni desde demo.

Consultar este catálogo de contratos no compra opciones ni mueve dinero. La
implementación no envía órdenes y no contrató ninguna suscripción.

## Fuentes gratuitas y filtro parcial

La revisión oficial de Alpaca, Tradier, Cboe y Databento no confirmó una alternativa
gratuita permanente que entregue NBBO histórico por operación y todas sus patas.
Una cotización indicativa, una cadena actual, muestras o créditos temporales no
equivalen a esos datos. No se conectó otro proveedor, creó cuenta o consumió crédito.
Skylit sigue parcial con faltantes visibles; no se infiere volumen diario a partir
de una cinta incompleta. Fuentes y límites en `docs/proveedores-gratuitos.md` §8.

## Notebook: múltiples estrategias

`notebooks/multiples_estrategias.ipynb` es autocontenido para Colab, con celdas de
instalación, configuración, datos, validación, análisis, evaluación y exportación.
NumPy 2.5.3 y pandas 3.0.6 fijados, semilla explícita, referencia de exceso cero,
exploración separada de purga/embargo/holdout y corrección Holm de toda la familia.
El modo SINTÉTICO bloquea conclusiones financieras. No accede a cartera ni claves.

Se ejecutó localmente, sin pip ni red, en un directorio temporal. El resultado se
congela en la sesión; cambios en datos, configuración, selección o holdout se
rechazan, y las exportaciones existentes distintas no se sobrescriben. Se corrigió
el fin de línea del CSV para que la exportación repetida sea idempotente en Windows.
Doce pruebas del notebook aprobadas; no se ejecutó Colab remoto ni datos reales.
El bloqueo de sesión no impide reiniciar Colab: exige preregistro externo y no
reutilizar el tramo reservado. No demuestra ventaja estadística o predictiva.

## Pruebas y entrega

Las 42 pruebas enfocadas iniciales de contratos, notebook y compatibilidad pasaron.
Se añadió después una regresión de procedencia por campo; la suite completa final
incluye ese caso. La comprobación real de acceso no sustituye las pruebas con HTTP
falso, que cubren ruta/método, apagado, redirecciones, errores sanitizados, fecha de
OI y cortes sin fuga temporal. TradingView ajeno se conserva fuera del commit.


## Estado del objetivo

- **Código funcional verificado:** lectura de contratos Paper, almacenamiento,
  unión temporal y avisos; notebook completo ejecutado localmente con datos sintéticos.
- **Cálculo implementado, sujeto a datos:** GEX requiere también gamma y spot
  compatibles. La prueba mínima no certifica esos campos ni cobertura del universo.
- **Modelo sin ventaja demostrada:** el notebook prueba el procedimiento estadístico;
  no se evaluó una familia real preregistrada ni se demuestra rentabilidad.
- **Alcance parcial aceptado:** faltan NBBO histórico y patas para Skylit. No queda
  autorización pendiente para la entrega; pagos o nuevos proveedores requieren
  una solicitud posterior. Activar el interruptor local es opcional y manual.

La revisión visual usó datos SINTÉTICOS de demo a 375 px, navegación por teclado,
fecha y aviso de OI visibles y consola sin errores. Se cerró la pestaña y se detuvo
el servidor temporal de 127.0.0.1; no se utilizó la base real para esa comprobación.


Validación final: **649 pruebas aprobadas** en la suite completa; JavaScript válido,
revisión de espacios aprobada y 20 archivos examinados sin patrones de secretos.
La primera ejecución detectó una aserción textual que requería mencionar OPRA:
se aclaró que el feed indicativo no equivale a OPRA. Diecinueve pruebas de regresión
pasaron y después se repitió la suite completa. Persiste un aviso de deprecación
externo de Starlette/AnyIO, sin fallo de prueba.
