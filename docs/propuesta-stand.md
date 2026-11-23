# Propuesta de stand físico — Actinver Terminal

Objetivo: que un evaluador o inversionista entienda en **30 segundos** qué hace la terminal y en **3 minutos** por qué es seria (metodología, datos honestos, seguridad).

## 1. Distribución (stand de 3 × 2 m)

```
 ┌──────────────────────── pared de fondo (lona 3 × 2 m) ────────────────────────┐
 │  Logo + «Su cartera, con datos honestos»   ·   3 cifras grandes   ·   QR        │
 │                                                                                  │
 │   [Pantalla 1: 55" vertical u horizontal]        [Pantalla 2: 43"]               │
 │    Video en bucle (docs/video)                     Terminal en vivo (demo)        │
 │                                                                                  │
 │   ┌────────── mesa alta 1.8 m ──────────┐                                        │
 │   │ Laptop con la terminal · tableta    │   Tótem lateral: «Cómo funciona» en 4 pasos
 │   │ para el visitante · folletos · QR   │                                        │
 │   └─────────────────────────────────────┘                                        │
 └──────────────────────────────────────────────────────────────────────────────────┘
```

## 2. Recursos

### Equipo (prioridad alta)

| Recurso | Uso | Costo aprox. (MXN) | Alternativa gratis |
|---|---|---|---|
| Pantalla 50–55" con soporte de piso | Video en bucle visible a 5 m | 9,000–14,000 (renta: 1,500–3,000/día) | Pedir prestada a la universidad |
| Laptop con la terminal en modo demo | Demostración guiada | — (la propia) | — |
| Segunda pantalla o monitor 27" | Estación de Mercado en vivo | 3,500–5,000 (renta: 800/día) | Monitor propio |
| Tableta 10" en soporte | El visitante explora la demo pública | 3,000–5,000 | Celular propio en soporte |
| Regleta, extensión 5 m y cinta para cables | Seguridad | 400 | — |
| Router móvil / hotspot | Por si el Wi-Fi del evento falla (la demo corre local, el video también) | 0–500 | Hotspot del celular |

### Gráficos

| Recurso | Contenido | Costo aprox. |
|---|---|---|
| Lona de fondo 3 × 2 m | Logo, lema, 3 cifras («950+ pruebas automáticas», «0 órdenes enviadas: solo simula», «100 % fuentes gratuitas y legales»), QR al sitio | 1,200–2,000 |
| Roll-up 85 × 200 cm | «Cómo funciona» en 4 pasos: Datos → Portafolio → Riesgo → Plan | 900–1,400 |
| 100 folletos tríptico | Resumen del reporte ejecutivo + QR | 600–1,000 |
| 50 tarjetas | Contacto y QR | 300 |
| Reporte ejecutivo impreso (10 copias) | `docs/reporte-ejecutivo/reporte-ejecutivo.pdf` para evaluadores | 400 |
| Mantel negro con logo | Mesa | 500 |

### Contenido digital (ya existe o se genera con el repo)

- Video explicativo en bucle: `docs/video/actinver-terminal.mp4` (≈ 2 min).
- Demo pública: https://maikolv.github.io/help-quote-terminal/ (QR).
- Terminal en modo demostración: `start.bat demo` (datos simulados; no muestra cuentas reales).
- Reporte ejecutivo PDF y aviso legal (pestaña «Legal»).

### Personas

- 2 presentadores: uno capta a la gente; el otro hace la demostración.
- Guion de 30 s, de 3 min y de 10 min (abajo).
- Vestimenta coherente (negro/gris con acento rojo, como la terminal).

**Presupuesto total estimado:** 20,000–30,000 MXN comprando; **5,000–9,000 MXN** rentando pantallas e imprimiendo lo esencial.

## 3. Guion de demostración

**30 s (pasillo):** «Es una terminal que le dice qué vender, comprar o mantener en su cartera, con datos de fuentes oficiales y sin prometer lo que no puede: cada dato dice de dónde viene y qué tan viejo es.»

**3 min (evaluador):**
1. Estación de Mercado: busque un símbolo con `/`, muestre el inspector y el rango 10–90 %.
2. Mis portafolios: cree un portafolio de máximo Sharpe y márquelo como **principal**.
3. Plan de acción: muestre cómo cambia el plan y por qué (motivo e invalidación).
4. Cierre con la honestidad: «ningún modelo supera a 1/N fuera de muestra todavía, y la terminal lo dice».

**10 min (inversionista):** lo anterior más Riesgo (VaR/CVaR, validación en 1,600 carteras), costos (100 % gratuito), seguridad (local, sin órdenes) y hoja de ruta.

## 4. Qué atrae a evaluadores e inversionistas

- **Evidencia, no promesas:** pruebas automáticas, validación fuera de muestra y límites declarados.
- **Demo que el visitante toca:** la tableta con la demo pública.
- **Un número grande que se recuerde:** «0 órdenes enviadas: solo informa».
- **Aviso legal visible:** muestra madurez y reduce riesgos.
- **Hoja de ruta clara:** datos en tiempo real (requiere proveedor de pago), app móvil, asistente con Gemini.

## 5. Lista de verificación del día

- [ ] Terminal en modo demo probada sin internet.
- [ ] Video en bucle en USB y en la laptop.
- [ ] QR probado con 2 celulares.
- [ ] Laptop con tema claro y letra 110 % (pestaña Apariencia; se lee mejor bajo luces del evento).
- [ ] Ningún dato de cuenta real visible (modo demo).
- [ ] Reporte ejecutivo impreso y aviso legal a la mano.
