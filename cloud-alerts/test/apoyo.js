// Apoyos de prueba: D1 simulada con node:sqlite (mismo SQL de la migración), fetch simulado y una carga de ejemplo.
import { readFileSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";

export function d1() {
  const db = new DatabaseSync(":memory:");
  db.exec(readFileSync(new URL("../migrations/0001_inicial.sql", import.meta.url), "utf8"));
  const sentencia = (sql, args = []) => ({
    bind: (...a) => sentencia(sql, a),
    first: async () => db.prepare(sql).get(...args) ?? null,
    all: async () => ({ results: db.prepare(sql).all(...args) }),
    run: async () => {
      const r = db.prepare(sql).run(...args);
      return { meta: { changes: Number(r.changes), last_row_id: Number(r.lastInsertRowid) } };
    },
  });
  return { prepare: (sql) => sentencia(sql), _db: db };
}

/** fetch simulado: `rutas` es una lista de [prefijo, fn(url, init) → {status, body}] */
export function fetchFalso(rutas) {
  const llamadas = [];
  const f = async (url, init = {}) => {
    llamadas.push({ url: String(url), init });
    const r = rutas.find(([p]) => String(url).startsWith(p));
    if (!r) throw new Error("sin red en pruebas");
    const { status = 200, body = {} } = await r[1](String(url), init);
    return { status, json: async () => body, text: async () => JSON.stringify(body) };
  };
  f.llamadas = llamadas;
  return f;
}

export const ENV_BASE = {
  SYNC_SECRET: "s".repeat(43), TELEGRAM_BOT_TOKEN: "123:abc", TELEGRAM_CHAT_ID: "42",
  ALPACA_API_KEY_ID: "id", ALPACA_API_SECRET_KEY: "sec", BANXICO_TOKEN: "tok",
};

export function carga(extra = {}) {
  return {
    version: 1, secuencia: 1000, generado_en: "2026-10-01T15:00:00Z",
    cartera: {
      fuente: "portal", hora_conciliacion: "2026-10-01T14:45:00Z", efectivo: 200000, por_liquidar: 0, valor_total: 1000000,
      posiciones: [
        { id: "SIC:MU", clave: "MU *", simbolo_eeuu: "MU", titulos: 16, precio_ref: 2000, moneda_ref: "MXN", fecha_precio: "2026-09-30", fuente_precio: "alpaca", tipo_precio: "cierre" },
        { id: "BMV:ALPEK", clave: "ALPEK A", simbolo_eeuu: null, titulos: 20000, precio_ref: 14.78, moneda_ref: "MXN", fecha_precio: "2026-09-30", fuente_precio: "eodhd", tipo_precio: "cierre" },
      ],
    },
    umbrales: { movimiento_pct: 0.03, cartera_pct: 0.02, sync_max_horas: 26, conciliacion_max_horas: 30, local_inactivo_min: 20 },
    plan: {
      calculado_en: "2026-10-01T13:00:00Z", nombre: "Acciones · Máxima puntuación", puntuacion: 87.4, vigente: true, validado: true,
      motivo_no_validado: null,
      opciones: [{ id: "SIC:MU", clave: "MU *", simbolo_eeuu: "MU", accion: "comprar", titulos: 5, precio_ref: 2000, fuente_precio: "alpaca",
        fecha_precio: "2026-09-30", limite_compra: 1950, limite_venta: null, condicion: "Comprar si la referencia baja a $1,950 o menos." }],
      alternativas: [{ nombre: "Mixta · Máxima puntuación", puntuacion: 84.3 }],
    },
    calendario: [
      { mercado: "XMEX", fecha: "2026-10-01", apertura: "2026-10-01T13:30:00Z", cierre: "2026-10-01T20:00:00Z" },
      { mercado: "XNYS", fecha: "2026-10-01", apertura: "2026-10-01T13:30:00Z", cierre: "2026-10-01T20:00:00Z" },
      { mercado: "XMEX", fecha: "2026-10-02", apertura: "2026-10-02T13:30:00Z", cierre: "2026-10-02T20:00:00Z" },
      { mercado: "XNYS", fecha: "2026-10-02", apertura: "2026-10-02T13:30:00Z", cierre: "2026-10-02T20:00:00Z" },
    ],
    fx: { valor: 18.0, fecha: "2026-09-30", fuente: "banxico" },
    splits: [],
    ...extra,
  };
}

/** Respuesta de Alpaca para MU: precio actual y cierre previo en USD */
export const alpaca = (precio, previo = 100, hora = "2026-10-01T16:00:00Z", fechaPrev = "2026-09-30") => ({
  MU: { latestTrade: { p: precio, t: hora }, prevDailyBar: { c: previo, t: `${fechaPrev}T04:00:00Z` } },
});
export const banxico = (dato = "18.0000", fecha = "01/10/2026") => ({ bmx: { series: [{ idSerie: "SF43718", datos: [{ fecha, dato }] }] } });
