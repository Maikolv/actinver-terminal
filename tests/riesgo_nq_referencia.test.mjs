// Contraste de planNQ (Mesa) con una referencia independiente en aritmética exacta (Fraction de Python, futuros-lab).
// Los vectores salen de futuros-lab/scripts/generar_vectores_mesa_riesgo.py; esta copia debe ser idéntica a la de futuros-lab.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {planNQ} from '../web/static/mesa.mjs';

const datos = JSON.parse(readFileSync(new URL('./vectores/mesa_riesgo_ref.json', import.meta.url), 'utf8'));
const cerca = (a, b) => Math.abs(a - b) <= 1e-9 * Math.max(1, Math.abs(b));

test('la Mesa coincide con la referencia exacta en los escenarios NQ (USD 20/punto)', () => {
  const nq = datos.casos.filter(c => c.raiz === 'NQ');
  assert.ok(nq.length > 300);
  const fallos = [];
  for (const c of nq) {
    const args = [c.entrada, c.stop, c.r, c.presupuesto, c.costos, c.slip];
    let p = null, error = null;
    try { p = planNQ(...args); } catch (e) { error = e.message; }
    if (!c.valido) { if (p) fallos.push({c, motivo: 'debía rechazarse', p}); continue; }
    if (error) { fallos.push({c, motivo: 'se rechazó un escenario válido', error}); continue; }
    const e = c.esperado;
    if (p.lado !== e.lado || !cerca(p.tp, e.tp) || !cerca(p.sl, e.sl) || !cerca(p.riesgo, e.riesgo) || p.contratos !== e.contratos || !cerca(p.recompensaNeta, e.recompensa_neta))
      fallos.push({c, motivo: 'resultado distinto', p, e});
  }
  assert.deepEqual(fallos.slice(0, 5), [], `${fallos.length} discrepancias`);
});

test('contratos nunca excede lo que paga el presupuesto y TP nunca pasa de R (redondeo conservador)', () => {
  for (const c of datos.casos.filter(c => c.raiz === 'NQ' && c.valido)) {
    const p = planNQ(c.entrada, c.stop, c.r, c.presupuesto, c.costos, c.slip);
    assert.ok(p.contratos * p.riesgo <= c.presupuesto + 1e-9, 'sobrepasa el presupuesto');
    assert.ok(Math.abs(p.tp - c.entrada) <= Math.abs(c.entrada - c.stop) * c.r + 1e-9, 'TP más lejos que R');
    assert.ok(Math.abs(p.tp * 4 - Math.round(p.tp * 4)) < 1e-8, 'TP fuera de tick');
  }
});
