# Directriz post-Reto: de «actinver-terminal» a «help-quote-terminal»

Dictada por el usuario el 25-oct-2026. **Se activa cuando termine la competencia del Reto Actinver 2026:
13-nov-2026 a las 15:00 (Ciudad de México)**, según `config/reto.yaml` (`competencia_fin`). Antes de esa fecha no se
aplica nada de esto: el Reto sigue rigiendo la terminal.

## Qué hacer a partir de esa fecha

1. **Nuevo nombre: `help-quote-terminal`** (nombre visible: «Help Quote Terminal»). Debe cambiar en:
   - el código: paquete en `pyproject.toml`, títulos de la interfaz, Telegram, reportes, lanzador y scripts de arranque;
   - toda la documentación local: README, CLAUDE.md, `docs/`, CHANGELOG (nueva entrada; el historial anterior se conserva
     tal cual);
   - GitHub: el repositorio `Maikolv/actinver-terminal` pasa a `help-quote-terminal`;
   - la carpeta local, las notas de memoria de Claude y cualquier otro archivo o chat local que nombre la terminal.
2. **Quitar todas las reglas del Reto:**
   - mínimo de 5 emisoras y máximo de 50 % por emisora;
   - catálogo cerrado del simulador, horario y comisiones del Reto;
   - días restantes, etapas y la captura manual del portal como cartera de referencia.
   La cartera pasa a ser la que el usuario registre (importación o captura propia).
3. **Nuevo objetivo: armar el mejor portafolio posible en dos horizontes:**
   - largo plazo;
   - intradía.
   Lo de siempre aplica: comparar contra una referencia simple (1/N), probar fuera de muestra y decir con claridad cuando
   no haya ventaja demostrada.
4. **Conservar absolutamente todas las funciones actuales:**
   - propuestas, plan del día y Telegram;
   - riesgo, backtesting y Laboratorio;
   - Velas y widgets de TradingView;
   - Order Flow, Option Flow e investigación;
   - Asistente, avisos de pérdida, monitor en la nube y Aprender.
   Se cambian sus textos y supuestos, no se eliminan.

## Lo que NO cambia (límites del mandato v2 y del usuario)

- Sin dinero real ni órdenes en vivo: la terminal informa y simula; el usuario decide y opera.
- Secretos solo en `.env`; servir solo en `127.0.0.1`; datos solo por vía legal.
- Nunca presentar datos retrasados o simulados como tiempo real.
- No es asesoría de inversión personalizada.
- **No borrar los datos del Reto:** capturas, transacciones y backtests se archivan (copia en `data/respaldos/` y
  etiqueta «Reto 2026»). No se eliminan.
- **Pedir confirmación al usuario antes de** renombrar el repositorio en GitHub y la carpeta local. El renombre rompe
  enlaces y rutas (lanzador, accesos directos, tareas programadas, `.claude/launch.json`).

## Cómo ejecutarla (para Claude Code, Codex u otra sesión)

1. Comprobar que ya pasó `competencia_fin` y avisar al usuario que se va a aplicar esta directriz.
2. Respaldo verificado de `data/` y rama `pre-help-quote` en GitHub.
3. Renombre en código y documentos, con la suite completa en verde.
4. Desactivar las reglas del Reto: en `config/reto.yaml` dejar `activo: false` o equivalente, y quitar sus validaciones
   y textos. Las pruebas que dependan del Reto se adaptan al nuevo objetivo; no se borran sin reemplazo.
5. Con la confirmación del usuario, renombrar el repositorio en GitHub, actualizar el `origin` y la carpeta local, y
   actualizar los accesos directos.
6. Actualizar CLAUDE.md, la memoria de Claude y el CHANGELOG con lo hecho y las métricas.
