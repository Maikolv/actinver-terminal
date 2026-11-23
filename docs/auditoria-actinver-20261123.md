# Auditoría y entrega — 23-nov-2026 (mega prompt Actinver Terminal y Concurso Finanzas IA)

## (a) Identidad y nombre

| Superficie | Estado |
|---|---|
| Interfaz, título, cabecera, 404, Mesa, Oficina, Cuaderno, Laboratorio | **Actinver Terminal** (restaurado) |
| Telegram, Excel de Markowitz, lanzador (`launcher/`), scripts de arranque, `start.bat`, Worker | Restaurado |
| README, DESIGN.md, Codespaces, portada de Pages, reporte ejecutivo, guía de inicio, propuesta de stand | Restaurado + aviso «no afiliado a Grupo Actinver» |
| CHANGELOG, historial, prompts y auditorías anteriores | Sin cambios (registros de su época) |
| **Repositorio en GitHub** (`Maikolv/help-quote-terminal`) | **PENDIENTE (paso externo).** El sistema de permisos bloqueó `gh repo rename`. Comando para el usuario: `gh repo rename actinver-terminal -R Maikolv/help-quote-terminal --yes`, y luego `git remote set-url origin https://github.com/Maikolv/actinver-terminal.git`. Al hacerlo, la URL de Pages pasa a `maikolv.github.io/actinver-terminal/` y hay que volver a exportar con `PREFIJO=/actinver-terminal/terminal/ npm run estatico` y reemplazar los enlaces. |
| Carpeta local | Ya se llama `actinver-terminal` (no requiere cambio) |

Sistema visual (DESIGN.md, sin cambios):
- **Color:** grafito con rojo de identidad (#b3261e); violeta punteado = FUTURO; bandas 10–90 %.
- **Tipografía:** sans del sistema con cifras tabulares; monoespaciada solo para símbolos.
- **Densidad:** compacta, con modo cómodo opcional.
- **Voz:** español sencillo, siempre con fuente, fecha y vigencia.
- **Relación con la institución:** proyecto independiente y educativo, sin afiliación, patrocinio ni aval de Grupo Actinver.

## (b) Informe del concurso

- **Archivos:** `entregables/Informe_Concurso_Finanzas_IA.docx`, más el PDF de revisión exportado por Word (12 páginas, índice actualizado).
- **Generadores:** `scripts/informe_concurso_datos.py` (cifras) y `scripts/informe_concurso.cjs` (Word).
- **Formato:** carta, márgenes de la plantilla, encabezado y pie institucionales UVM tomados de la plantilla original.
- **Datos reales** del archivo del Reto (`data/archivo/reto-actinver-2026-20261117.db`, 31 capturas de la competencia):

| Concepto | Valor |
|---|---|
| Portafolio inicial (5-oct) | $999,136.55 |
| Corte de octubre (30-oct) | $891,643.12 (−10.84 %) |
| Final (12-nov) | $784,440.07 (−21.56 %) |
| Desviación diaria | 4.07 % (64.6 % anual) |
| VaR 95 % histórico | 5.27 % |
| NAFTRAC en el mismo periodo | +10.90 % |
| MU al 13-nov | RSI 42.5; precio bajo las medias de 20 y 50 días; MACD bajo su señal |

- **Movimientos:** 9 entre el 6 y el 31 de octubre; la rotación del 10–12 de noviembre, completa.
- **PENDIENTE (no se inventa):**
  - portada: equipo, nombres completos, matrículas, carrera, campus, fecha, docente y asignatura;
  - capturas del portal (la terminal guardó el texto, no la imagen);
  - indicadores fundamentales de MU (último 10-K en SEC EDGAR);
  - código del equipo y nickname.

## (c) Paridad local frente a GitHub Pages

URL: https://maikolv.github.io/help-quote-terminal/terminal/ (versión estática, **DEMO PÚBLICA con datos simulados**).

| Función local | Depende de | En Pages | Estado |
|---|---|---|---|
| 23 pestañas de lectura (plan, cartera, riesgo, propuestas, portafolios, ranking, mercado, ficha, flujo, investigación, ayuda, apariencia, legal…) | FastAPI + SQLite | 220 respuestas GET grabadas de la demo | **Equivalente en lectura** |
| Estación: monitor, gráfico e inspector de los 174 instrumentos | API de mercado y ficha | Grabadas por instrumento | Equivalente |
| Reporte imprimible con QR `#r=` | Cliente | Funciona igual | Equivalente |
| Apariencia (tema, letra, densidad) | localStorage | Funciona igual | Equivalente |
| Recalcular propuestas, guardar portafolios, «Usar como principal», capturar cartera, importar CSV/PDF | Python, SQLite y escritura | Responde «necesita la terminal local» | **Excepción**: no hay backend en Pages |
| Asistente de IA, Telegram, motor, alertas, actualización de datos | Servidor y claves en `.env` | No disponible | **Excepción** (secretos; nunca se publican) |
| Vela en vivo (SSE) y Option Flow con proveedor | Servidor y claves | Apagado | Excepción |
| Consultas no grabadas (un símbolo raro en Velas) | API | Aviso «sin dato en la versión estática» | Parcial |

**Conclusión:** no es «paridad total». Un backend público requeriría alojar Python con la base y las claves (costo, seguridad y licencias de datos que prohíben redistribuir precios), y por eso **no se hizo**. La alternativa vigente es una demo pública de lectura completa más la terminal local o Codespaces (privado) para todo lo demás.

## (d) Guiones y videos

- **Guiones A** (Miguel y Daniela) **y B** (Miguel, Daniela, Valeria y Camila): 60 s, con corte de 30 s, storyboard, tomas, caption, créditos, permisos y subtítulos `A-60s.srt` y `B-60s.srt`. Archivo: `docs/video/guiones-tiktok.md`.
- **Tendencias de TikTok Creative Center:** no se consultaron (requieren sesión); queda indicado en el guion.
- **Cuatro renders finales:** **no producidos**. No hay grabaciones del elenco para esta terminal; los audios de `Downloads` (Miguel 1–7 y Audios_Bruno) son de COATL. Se entregan **montajes provisionales rotulados** de la versión A: `docs/video/provisional/A-vertical-PROVISIONAL.mp4` (1080×1920) y `A-horizontal-PROVISIONAL.mp4` (1920×1080), de unos 59 s, con voz sintética.
- **Video explicativo** `docs/video/actinver-terminal.mp4`: regenerado con las capturas nuevas.
- **COATL:** el video final con las voces reales ya lo generó otra sesión (`coatl/entregables/COATL_Video.mp4`, 04:08 del 23-nov). Dos grabaciones quedaron fuera por desactualizadas, y no se usaron para no afirmar datos falsos:
  - Bruno «15-versiones» dice «13 versiones»;
  - Miguel «6» dice «coeficientes sin microdatos».

## (e) Recursos incorporados

| Recurso | Origen | Licencia | Versión | Ruta | Uso | Prueba |
|---|---|---|---|---|---|---|
| qrcode-generator | npm | MIT | 2.0.4 | `web/static/vendor/qrcode.js` | QR del reporte | `tests/reporte.test.mjs` |
| playwright | npm | Apache-2.0 | 1.65.x | `node_modules` (desarrollo) | Exportación, capturas, axe | `npm run e2e` |
| @axe-core/playwright | npm | MPL-2.0 | 4.14.x | `node_modules` (desarrollo) | Accesibilidad | 0 violaciones |
| docx, jszip | npm | MIT | — | `node_modules` (desarrollo) | Informe Word | Generado y revisado en Word |
| faster-whisper (modelo «small») | PyPI / Hugging Face | MIT | — | caché de uv, fuera del repositorio | Transcribir audios | Transcripciones en `data/medios` (privado) |
| matplotlib | PyPI | PSF | — | entorno temporal de uv | Gráficas del informe | 3 PNG generados |

Costo: **$0 confirmado**; ningún servicio con facturación.

## Precios: cobertura comprobada frente a pendiente (base real, 23-nov)

| Mercado | Instrumentos | Verificado por serie | Pendiente | Último cierre guardado |
|---|---|---|---|---|
| BMV local | 48 | 45 en EODHD (respuesta válida por serie) | 3 sin cobertura EODHD; BMV licenciado, ICE y LSEG por contrato | 17-nov-2026 |
| SIC | 107 | — (EODHD no aplica; referencia de bolsa de origen en USD por Tiingo/Alpaca) | Precio SIC en MXN: requiere proveedor licenciado | 17-nov-2026 |
| Fondos | 25 | 25 por PDF de Actinver importado por el usuario | — | 13-nov-2026 |

- **Cuota EODHD:**
  - 20 consultas al día, persistente en `uso_proveedor`;
  - cola priorizada en `terminal/ingesta.py::orden_cola`: cartera, luego propuestas, luego nuevos y atrasados;
  - prueba nueva del caso límite de cuota 0 (`tests/test_adaptadores.py`).
- **Datos de mercado:** sin actualizar desde el 17-nov porque la terminal no se ha ejecutado. Basta con `uv run terminal actualizar`.
- **Sin precio confiable:** se muestra «SIN PRECIO CONFIABLE» y la decisión queda «pendiente», sin boleta direccional. Ya existía; se verificó en el plan.
- **Prohibido y respetado:** nunca se usa tipo de cambio, ADR, CFD ni dato vencido para suplir un precio BMV.

### Checklist para evaluar Infosel (no activado; requiere contrato)

- [ ] Serie exacta BMV y SIC por emisora (clave, serie y mercado).
- [ ] Derechos de uso no profesional, almacenamiento local y prohibición de redistribución.
- [ ] Latencia: tiempo real, demorado (minutos) o fin de día.
- [ ] Límites de consultas y costo mensual.
- [ ] URL base, autenticación (token o IP) y renovación.
- [ ] Muestra de respuesta (JSON/CSV) para escribir el adaptador en `config/proveedores/`.

## (f) Comandos y pruebas reales

```bash
uv run pytest -q
```
```bash
node --test tests/*.test.mjs
```
```bash
npm run e2e
```
```bash
node scripts/capturas_demo.cjs
```
```bash
npm run estatico
```
```bash
uv run --with matplotlib python scripts/informe_concurso_datos.py
```
```bash
node scripts/informe_concurso.cjs
```
```bash
uv run python scripts/video_guion_provisional.py
```

Resultados en el CHANGELOG de la versión 103.

## (g) Acciones prohibidas, confirmadas como NO realizadas

- **Órdenes:** ninguna enviada, registrada ni confirmada en Actinver; tampoco en demo.
- **Cuenta de Actinver:** no se accedió ni se automatizó.
- **Gastos:** no se compraron servicios ni se activaron proveedores de pago (Infosel incluido).
- **Datos privados:** no se publicaron `.env`, claves, la cartera real ni la base privada (Pages solo tiene datos simulados).
- **Grabaciones:** no se fingió que el elenco grabó ni se declararon videos finales inexistentes.
- **Publicación:** no se publicó en TikTok.
- **Nombre:** no se afirma el renombre de GitHub: está pendiente.
