# Seguimiento desde Mesa — 1-nov-2026

TP01-07: botón junto al selector de instrumento, sobre la misma lista SQLite que ya usa la terminal. Reutiliza POST /api/seguimiento, que conserva notas existentes al repetir una incorporación. No crea una segunda lista ni cambia las reglas de la API.

GET /static/mesa.html ahora se resuelve antes del montaje estático, incorpora el mismo control CSRF de la página principal y declara Cache-Control: no-store. No carga credenciales de proveedores. No se relaja el middleware de origen/CSRF ni se añaden rutas de operación.

El botón se deshabilita sin catálogo activo, sin lectura confirmada de Seguimiento, al guardar y cuando el instrumento ya existe. Sin control CSRF válido solicita recargar, sin enviar petición. Errores HTTP permanecen visibles; no se agrega de forma optimista. La respuesta correcta se vuelve a leer de la lista compartida. Timeout de 15 segundos, credenciales de mismo origen. La acción es exclusivamente una preferencia local de investigación.

## Evidencia

- Python, pruebas nuevas y regresión de Mesa: **11 aprobadas, una advertencia de dependencia**, 30.37 s. `proveedores-20261101-evidencia/mesa-seguimiento-pytest-20261101.txt`.
- JavaScript completo: **51 aprobadas, 0 fallidas**, 2756.7218 ms. `proveedores-20261101-evidencia/mesa-seguimiento-node-20261101.txt`.
- Seguridad: **15 aprobadas, una advertencia de dependencia**, 32.97 s. `proveedores-20261101-evidencia/mesa-seguimiento-seguridad-20261101.txt`. Primer intento abortó antes de ejecutar pruebas por fallo del PowerShell resuelto por Windows PowerShell explícito; no se contó como resultado del producto.
- Chromium, página completa con FastAPI/SQLite aislados: cuatro recorridos (1440/390, claro/oscuro). Incorporación real de SIC:NVDA solo en la base de prueba, persistencia al recargar y botón deshabilitado después; sin errores JS, desbordamiento ni peticiones prohibidas. Solo POST a /api/seguimiento permitido; proveedores bloqueados. Resultados: `proveedores-20261101-evidencia/mesa-seguimiento-ui/resultado.json`.
- Pruebas Python verifican rechazo sin CSRF y con Origin externo, y que repetir la incorporación no borre una nota previa. Control CSRF nunca guardado en el informe o las capturas.
- `git diff --check` del código afectado: salida 0, solo avisos de finales de línea de Git.
- No se repitió la suite Python completa por este cambio acotado. Los resultados de 854 pruebas de la fase anterior no validan este código posterior.

Se detuvo únicamente el servidor aislado, después de comprobar su línea de comando. La base habitual del usuario no se modificó durante la verificación. Sin trades, ejecución, Telegram, commit o push.

Exploración: codebase-memory no disponible (Transport closed); fallback directo en app.py, seguridad.py, seguimiento.py, mesa.mjs, mesa.html y las pruebas relevantes, preservando cambios previos.
