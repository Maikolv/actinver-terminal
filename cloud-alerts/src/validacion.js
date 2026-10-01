// Validación estricta de la carga que envía la terminal local. Claves desconocidas, tipos o rangos fuera de lo
// esperado ⇒ rechazo. Solo se aceptan los datos mínimos para vigilar (nada de credenciales ni documentos).

export const MAX_BYTES = 65536;
const ID = /^(BMV|SIC|FONDO):[A-Z0-9.&+\-]{1,24}$/;
const SIMBOLO = /^[A-Z][A-Z0-9.\-]{0,9}$/;
const FECHA = /^\d{4}-\d{2}-\d{2}$/;
export const UMBRALES_POR_OMISION = {
  movimiento_pct: 0.03, cartera_pct: 0.02, sync_max_horas: 26, conciliacion_max_horas: 30, local_inactivo_min: 20,
};
const RANGOS = {
  movimiento_pct: [0.005, 0.5], cartera_pct: [0.005, 0.5], sync_max_horas: [1, 168], conciliacion_max_horas: [1, 336],
  local_inactivo_min: [5, 240],
};

class Invalida extends Error {}

function exigir(cond, msg) { if (!cond) throw new Invalida(msg); }
const esObj = (x) => x !== null && typeof x === "object" && !Array.isArray(x);
function soloClaves(o, permitidas, donde) {
  for (const k of Object.keys(o)) exigir(permitidas.includes(k), `${donde}: campo no permitido «${k}»`);
}
function num(x, donde, min = -Infinity, max = Infinity, nulo = false) {
  if (nulo && (x === null || x === undefined)) return null;
  exigir(typeof x === "number" && Number.isFinite(x) && x >= min && x <= max, `${donde}: número fuera de rango`);
  return x;
}
function txt(x, donde, max, nulo = true, patron = null) {
  if (nulo && (x === null || x === undefined)) return null;
  exigir(typeof x === "string" && x.length <= max && (!patron || patron.test(x)), `${donde}: texto inválido`);
  return x;
}
function iso(x, donde, nulo = false) {
  if (nulo && (x === null || x === undefined)) return null;
  exigir(typeof x === "string" && x.length <= 40 && !Number.isNaN(Date.parse(x)), `${donde}: fecha y hora inválidas`);
  return new Date(x).toISOString();
}
function lista(x, donde, max) {
  if (x === undefined || x === null) return [];
  exigir(Array.isArray(x) && x.length <= max, `${donde}: lista inválida o demasiado larga`);
  return x;
}

function posicion(p, i) {
  const d = `posiciones[${i}]`;
  exigir(esObj(p), d);
  soloClaves(p, ["id", "clave", "simbolo_eeuu", "titulos", "precio_ref", "moneda_ref", "fecha_precio", "fuente_precio", "tipo_precio"], d);
  return {
    id: txt(p.id, `${d}.id`, 32, false, ID), clave: txt(p.clave, `${d}.clave`, 32),
    simbolo_eeuu: txt(p.simbolo_eeuu, `${d}.simbolo_eeuu`, 10, true, SIMBOLO),
    titulos: num(p.titulos, `${d}.titulos`, 0, 1e9), precio_ref: num(p.precio_ref, `${d}.precio_ref`, 0, 1e9, true),
    moneda_ref: txt(p.moneda_ref ?? "MXN", `${d}.moneda_ref`, 3, false, /^MXN$/),
    fecha_precio: txt(p.fecha_precio, `${d}.fecha_precio`, 10, true, FECHA),
    fuente_precio: txt(p.fuente_precio, `${d}.fuente_precio`, 40), tipo_precio: txt(p.tipo_precio, `${d}.tipo_precio`, 30),
  };
}

function opcion(o, i) {
  const d = `plan.opciones[${i}]`;
  exigir(esObj(o), d);
  soloClaves(o, ["id", "clave", "simbolo_eeuu", "accion", "titulos", "precio_ref", "fuente_precio", "fecha_precio",
    "limite_compra", "limite_venta", "condicion"], d);
  return {
    id: txt(o.id, `${d}.id`, 32, false, ID), clave: txt(o.clave, `${d}.clave`, 32),
    simbolo_eeuu: txt(o.simbolo_eeuu, `${d}.simbolo_eeuu`, 10, true, SIMBOLO),
    accion: txt(o.accion, `${d}.accion`, 12, false, /^(comprar|vender|mantener|pendiente)$/),
    titulos: num(o.titulos, `${d}.titulos`, 0, 1e9, true), precio_ref: num(o.precio_ref, `${d}.precio_ref`, 0, 1e9, true),
    fuente_precio: txt(o.fuente_precio, `${d}.fuente_precio`, 40), fecha_precio: txt(o.fecha_precio, `${d}.fecha_precio`, 40),
    limite_compra: num(o.limite_compra, `${d}.limite_compra`, 0, 1e9, true),
    limite_venta: num(o.limite_venta, `${d}.limite_venta`, 0, 1e9, true),
    condicion: txt(o.condicion, `${d}.condicion`, 240, false),
  };
}

export function validar(obj) {
  try {
    exigir(esObj(obj), "la carga debe ser un objeto JSON");
    soloClaves(obj, ["version", "secuencia", "generado_en", "cartera", "umbrales", "plan", "calendario", "fx", "splits", "prueba"], "carga");
    exigir(obj.version === 1, "versión no admitida");
    exigir(Number.isSafeInteger(obj.secuencia) && obj.secuencia > 0, "secuencia inválida");
    const c = obj.cartera;
    exigir(esObj(c), "falta la cartera");
    soloClaves(c, ["fuente", "hora_conciliacion", "efectivo", "por_liquidar", "valor_total", "posiciones"], "cartera");
    const umb = { ...UMBRALES_POR_OMISION };
    if (obj.umbrales !== undefined) {
      exigir(esObj(obj.umbrales), "umbrales");
      soloClaves(obj.umbrales, Object.keys(RANGOS), "umbrales");
      for (const [k, [a, b]] of Object.entries(RANGOS)) if (obj.umbrales[k] !== undefined) umb[k] = num(obj.umbrales[k], `umbrales.${k}`, a, b);
    }
    let plan = null;
    if (obj.plan !== undefined && obj.plan !== null) {
      const p = obj.plan;
      exigir(esObj(p), "plan");
      soloClaves(p, ["calculado_en", "nombre", "puntuacion", "vigente", "validado", "motivo_no_validado", "opciones", "alternativas"], "plan");
      exigir(typeof p.vigente === "boolean" && typeof p.validado === "boolean", "plan: vigente y validado deben ser booleanos");
      plan = {
        calculado_en: iso(p.calculado_en, "plan.calculado_en"), nombre: txt(p.nombre, "plan.nombre", 120, false),
        puntuacion: num(p.puntuacion, "plan.puntuacion", 0, 100), vigente: p.vigente, validado: p.validado,
        motivo_no_validado: txt(p.motivo_no_validado, "plan.motivo_no_validado", 240),
        opciones: lista(p.opciones, "plan.opciones", 20).map(opcion),
        alternativas: lista(p.alternativas, "plan.alternativas", 5).map((a, i) => {
          exigir(esObj(a), `plan.alternativas[${i}]`);
          soloClaves(a, ["nombre", "puntuacion"], `plan.alternativas[${i}]`);
          return { nombre: txt(a.nombre, `plan.alternativas[${i}].nombre`, 120, false), puntuacion: num(a.puntuacion, `plan.alternativas[${i}].puntuacion`, 0, 100) };
        }),
      };
    }
    let fx = null;
    if (obj.fx !== undefined && obj.fx !== null) {
      exigir(esObj(obj.fx), "fx");
      soloClaves(obj.fx, ["valor", "fecha", "fuente"], "fx");
      fx = { valor: num(obj.fx.valor, "fx.valor", 5, 50), fecha: txt(obj.fx.fecha, "fx.fecha", 10, false, FECHA), fuente: txt(obj.fx.fuente, "fx.fuente", 20, false) };
    }
    exigir(obj.prueba === undefined || typeof obj.prueba === "boolean", "prueba debe ser booleano");
    const datos = {
      version: 1, secuencia: obj.secuencia, generado_en: iso(obj.generado_en, "generado_en"),
      cartera: {
        fuente: txt(c.fuente, "cartera.fuente", 10, false, /^(portal|local)$/),
        hora_conciliacion: iso(c.hora_conciliacion, "cartera.hora_conciliacion", true),
        efectivo: num(c.efectivo, "cartera.efectivo", -1e9, 1e10), por_liquidar: num(c.por_liquidar ?? 0, "cartera.por_liquidar", -1e9, 1e10),
        valor_total: num(c.valor_total, "cartera.valor_total", 0, 1e10),
        posiciones: lista(c.posiciones, "cartera.posiciones", 80).map(posicion),
      },
      umbrales: umb, plan, fx,
      calendario: lista(obj.calendario, "calendario", 80).map((s, i) => {
        const d = `calendario[${i}]`;
        exigir(esObj(s), d);
        soloClaves(s, ["mercado", "fecha", "apertura", "cierre"], d);
        return { mercado: txt(s.mercado, `${d}.mercado`, 4, false, /^(XMEX|XNYS)$/), fecha: txt(s.fecha, `${d}.fecha`, 10, false, FECHA),
          apertura: iso(s.apertura, `${d}.apertura`), cierre: iso(s.cierre, `${d}.cierre`) };
      }),
      splits: lista(obj.splits, "splits", 40).map((s, i) => {
        const d = `splits[${i}]`;
        exigir(esObj(s), d);
        soloClaves(s, ["id", "fecha", "factor"], d);
        return { id: txt(s.id, `${d}.id`, 32, false, ID), fecha: txt(s.fecha, `${d}.fecha`, 10, false, FECHA), factor: num(s.factor, `${d}.factor`, 0.001, 1000) };
      }),
      prueba: obj.prueba === true,
    };
    return { ok: true, datos };
  } catch (e) {
    if (e instanceof Invalida) return { ok: false, error: e.message };
    throw e;
  }
}
