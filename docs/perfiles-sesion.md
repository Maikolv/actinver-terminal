# Perfiles de sesión: TPO observado y área de valor

Revisión: 16-oct-2026. Cálculos descriptivos, sin ventaja predictiva demostrada.

## TPO observado, periodos de 30 minutos

`terminal/flujo/calculos.py::perfil_tpo` recibe barras guardadas y la zona IANA,
apertura y cierre de la sesión. Por defecto usa `America/New_York`, 09:30–16:00;
el llamador debe elegir la sesión del mercado de origen. Las fechas se agrupan
después de convertir el instante a esa zona; los desfases estacionales siguen
la base de zonas horarias. No se deduce una sesión a partir del idioma del equipo.
Para cripto admite `apertura="00:00", cierre="24:00", zona_horaria="UTC"`:
el cierre es la medianoche del día siguiente e incluye la última barra del día.

Solo entran barras intradía de duración conocida no mayor de 30 minutos,
enteramente dentro del horario y de un único periodo. Se excluyen barras diarias,
horarias, instantes sin zona y barras que cruzan límites. No se reparte una barra
entre periodos. Se exige observar al menos dos periodos distintos por sesión:
con uno solo el perfil es nulo; sin barras admisibles no se devuelve una sesión.

Cada sesión tiene 24 cubetas uniformes entre el menor y mayor precio OHLC
observado (configurable 1–200). El máximo pertenece a la última cubeta. Si todos
los precios son iguales se utiliza una única cubeta de ancho 1, como el perfil
de volumen existente. Una cubeta recibe una marca por cada periodo que tenga
alguno de los cuatro precios OHLC realmente almacenados en ella. Varias barras
o varios precios dentro del mismo periodo y cubeta cuentan una sola vez.
No se dibujan cubetas ni periodos que no tengan observaciones.

Este **TPO observado es una cota inferior**, no un Market Profile completo de ticks:
los OHLC no permiten conocer todos los precios negociados ni su secuencia. No se
rellenan precios entre mínimo y máximo. Tampoco se interpola ningún periodo
faltante. El resultado contiene los índices de periodo y sus inicios con desfase
para permitir una representación fiel y accesible. Es un perfil de lo guardado,
puede ser parcial y no certifica cobertura de toda la sesión. No incluye calendario
de festivos ni cierres anticipados: el horario se declara en la respuesta.
El llamador debe evitar mezclar proveedores, monedas y mercados incompatibles;
el cálculo recibe una sola selección homogénea de barras.

## POC y área de valor del perfil de volumen existente

`resumen_operaciones` conserva las mismas cubetas y volúmenes calculados a partir
de operaciones guardadas. `area_valor` se aplica directamente sobre ese perfil:

1. Ordena las cubetas presentes por su límite inferior. El POC es la cubeta de
   mayor volumen; ante empate, la de menor precio. Su precio representativo es
   el centro de la cubeta, y se devuelven también ambos límites para no sugerir
   que el punto medio fue un precio observado.
2. Comienza por el volumen del POC. Compara las cubetas presentes inmediatamente
   inferiores y superiores e incorpora la de mayor volumen. Si empatan incorpora
   ambas. Repite hasta acumular al menos el 70 % del volumen total.
3. VAL es el borde inferior de la primera cubeta incluida y VAH el borde superior
   de la última. Devuelve fracción objetivo y realmente incluida; esta puede
   superar el 70 % porque no fracciona cubetas. Un hueco entre cubetas no recibe
   volumen inventado; los límites solo acotan el intervalo de precios incluido.

No existe un único algoritmo universal de desempate: esta convención queda
fijada para reproducción. Menos de dos operaciones o de dos cubetas, volumen
negativo/no finito, límites inválidos o volumen total cero producen nulo.
La cobertura corresponde al rango de operaciones solicitado y no se presenta
como perfil de volumen de una sesión completa.

## Verificación

`tests/test_perfiles_sesion.py`: ejemplos **SINTÉTICOS**, con valores conocidos,
desempates, pocos datos, periodos ausentes, no duplicación, barras incompatibles
y separación por fecha local y horario estacional. No consulta red ni credenciales.
