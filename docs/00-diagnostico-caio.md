# 00 · Diagnóstico CAIO

## Definición adoptada

Los materiales no definen «CAIO». Para este proyecto se interpreta como un diagnóstico en cuatro dimensiones:

| Letra | Dimensión | Pregunta que responde |
|---|---|---|
| **C** | Capacidades | ¿Qué debe poder hacer la terminal y qué componentes existentes lo permiten? |
| **A** | Arquitectura | ¿Cuál es la estructura más pequeña que cumple el objetivo con seguridad? |
| **I** | Información | ¿Qué datos hay, de qué calidad, con qué licencia y con qué vigencia? |
| **O** | Operación | ¿Cómo se instala, actualiza, respalda, monitorea y mantiene en el tiempo? |

## Supuestos declarados

1. Usuario único, persona física en México, cliente de Actinver, que opera en MXN en la BMV (incluido el SIC) y en fondos de Actinver.
2. Uso exclusivamente local (una PC con Windows 11). No hay publicación en internet ni cuentas de usuario.
3. «Mejor portafolio» = mayor puntuación según criterios visibles y configurables (horizonte, riesgo, capital, diversificación, liquidez, costos, moneda, disponibilidad y escenario), nunca una promesa de rendimiento.
4. Los precios del PDF son capturas históricas: sirven para descubrir símbolos, no como cotización.
5. No hay contratos de datos en tiempo real. Se diseñan adaptadores sustituibles para cuando el usuario los contrate.
6. Las comisiones (0.25 % + IVA), spreads e impuestos (10 %) son supuestos editables; el usuario debe ajustarlos a su contrato.
7. Las posiciones del usuario no se deducen del PDF: solo se registran por captura o importación.

## C · Capacidades

| Capacidad requerida | Estado inicial | Resultado |
|---|---|---|
| Universo de instrumentos verificado | Solo capturas sin texto en el PDF | 182 instrumentos verificados contra Nasdaq Trader, BMV y fichas de Actinver (`config/universo.csv`) |
| Precios con fuente, hora y vigencia | Ninguno | Adaptadores FRED, Banxico, Tiingo, EODHD, CSV; vigencia por calendario NYSE/BMV |
| Seguimiento del inversionista | Ninguno | Libro con costo promedio, realizado/no realizado, dividendos, comisiones, TWR, TIR, auditoría |
| Dos propuestas comparables y explicadas | Ninguno | Media-varianza con skfolio, walk-forward, sensibilidad, escenarios, puntuación con motivos |
| Interfaz accesible y adaptable | Ninguna | Web local sin dependencias, AA de contraste, teclado, móvil |
| Seguridad local | — | Solo 127.0.0.1, CSRF, CSP, Host, límites, sin rutas de órdenes, secretos fuera de Git |

## A · Arquitectura

Se eligió la arquitectura más pequeña: **un proceso Python** (FastAPI + SQLite + skfolio) que sirve una interfaz estática. Sin Node en tiempo de ejecución, sin base de datos externa, sin contenedores, sin servicios en la nube. Justificación y alternativas descartadas en [06-decisiones.md](06-decisiones.md) y [08-inventario-repositorios.md](08-inventario-repositorios.md).

```
Navegador (127.0.0.1) ──HTTP──► FastAPI (seguridad, API) ──► SQLite local (data/terminal.db)
                                     │
                                     ├── adaptadores ──► FRED · Banxico · Tiingo · EODHD · CSV del usuario
                                     └── optimizador (skfolio + calendarios de mercado)
```

## I · Información

- **PDF**: 11 páginas, solo imágenes. 146 símbolos en «Acciones», la misma lista repetida bajo el rótulo «ETF's» (ningún ETF real) y 23 fondos cuya columna «1 año» aparece en 0.00 % para todos (dato no poblado). Detalle en [09-auditoria-pdf.md](09-auditoria-pdf.md).
- **Calidad del universo**: 2 deslistados (CPE, MRO), 2 claves reasignadas a otra empresa (GOLD → hoy «Gold.com»; PARA → hoy «Banzai»), 2 claves de BMV por confirmar (ALFA, probable SIGMAF; ELEKTRA). Todos excluidos de las propuestas con motivo visible.
- **ETF**: al no haber ETF en el PDF, se propone un conjunto candidato verificado como ETF en Nasdaq Trader (disponibilidad en el SIC por confirmar por el usuario) y el tracker SMARTRC de Actinver; ANGELD (2×) y DIABLOI (inverso) se excluyen por apalancamiento.
- **Licencias**: solo fuentes con uso personal permitido y sin evasión de controles (Stooq exige desafío anti-bot y Yahoo limita el acceso automatizado: descartados). Ver [10-fuentes.md](10-fuentes.md).

## O · Operación

- Inicio en un comando (`uv run terminal iniciar`), modo demostración aislado en `data/demo/`.
- Actualización incremental con límites persistentes por proveedor y registro de cada corrida.
- Respaldo verificado y rotado; tareas programadas de Windows opcionales (`scripts/programar_tareas.ps1`).
- Registro rotativo en `data/logs/`, sin credenciales (el registro HTTP de bajo nivel está silenciado).
- Plan de recurrencia en [05-recurrencia.md](05-recurrencia.md).

## Brechas que dependen del usuario

1. Obtener y configurar credenciales (Tiingo, EODHD, Banxico) o importar precios propios.
2. Confirmar con Actinver la disponibilidad en el SIC de los ETF candidatos y sus comisiones reales.
3. Exportar e importar el valor liquidativo de los fondos (no hay API pública de Actinver).
4. Decidir si contrata datos en tiempo real (ver [10-fuentes.md](10-fuentes.md#tiempo-real)).
