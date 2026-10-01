// Fuentes autorizadas del proyecto que funcionan sin la PC: Alpaca (IEX, gratis) para listados de EE. UU. y el FIX de
// Banxico. La BMV no tiene fuente intradía gratuita en la nube (EODHD da 20 consultas/día y las usa la terminal), así que
// las emisoras BMV y los fondos se muestran con el último cierre sincronizado y su fecha.
// Una referencia SIC = precio de EE. UU. × FIX: NO es el precio del SIC.

export const URL_ALPACA = "https://data.alpaca.markets/v2/stocks/snapshots";
export const URL_BANXICO = "https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF43718/datos/oportuno";
const VIVO_MIN = 15;

export class ErrorProveedor extends Error {
  constructor(proveedor, estado) {
    super(`${proveedor}: ${estado}`);  // nunca incluye URL ni cabeceras (llevan credenciales)
    this.proveedor = proveedor;
    this.estado = estado;
  }
}

export async function alpacaSnapshots(simbolos, env, fetchFn = fetch) {
  if (!env.ALPACA_API_KEY_ID || !env.ALPACA_API_SECRET_KEY) throw new ErrorProveedor("alpaca", "sin_credenciales");
  if (!simbolos.length) return {};
  const url = `${URL_ALPACA}?symbols=${encodeURIComponent(simbolos.join(","))}&feed=iex`;
  let r;
  try {
    r = await fetchFn(url, { headers: { "APCA-API-KEY-ID": env.ALPACA_API_KEY_ID, "APCA-API-SECRET-KEY": env.ALPACA_API_SECRET_KEY } });
  } catch {
    throw new ErrorProveedor("alpaca", "sin_conexion");
  }
  if (r.status !== 200) throw new ErrorProveedor("alpaca", `http_${r.status}`);
  const d = await r.json();
  const out = {};
  for (const s of simbolos) {
    const x = d[s];
    if (!x || !x.latestTrade) continue;
    out[s] = {
      precio: Number(x.latestTrade.p), hora: x.latestTrade.t,
      cierre_previo: x.prevDailyBar ? Number(x.prevDailyBar.c) : null,
      fecha_previa: x.prevDailyBar ? String(x.prevDailyBar.t).slice(0, 10) : null,
    };
  }
  return out;
}

function fechaBanxico(txt) {  // «30/09/2026» → «2026-09-30»
  const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(txt || "");
  return m ? `${m[3]}-${m[2]}-${m[1]}` : null;
}

export async function banxicoFix(env, fetchFn = fetch) {
  if (!env.BANXICO_TOKEN) throw new ErrorProveedor("banxico", "sin_credenciales");
  let r;
  try {
    r = await fetchFn(URL_BANXICO, { headers: { "Bmx-Token": env.BANXICO_TOKEN, Accept: "application/json" } });
  } catch {
    throw new ErrorProveedor("banxico", "sin_conexion");
  }
  if (r.status !== 200) throw new ErrorProveedor("banxico", `http_${r.status}`);
  const d = await r.json();
  const dato = d?.bmx?.series?.[0]?.datos?.[0];
  const valor = Number(String(dato?.dato || "").replace(",", ""));
  const fecha = fechaBanxico(dato?.fecha);
  if (!fecha || !Number.isFinite(valor) || valor < 5 || valor > 50) throw new ErrorProveedor("banxico", "dato_invalido");
  return { valor, fecha, fuente: "banxico_fix" };
}

/** Grado de actualidad de una operación IEX frente a la sesión de NYSE. */
export function gradoIex(horaTrade, ahora, sesionNyse) {
  const t = new Date(horaTrade);
  const min = (ahora - t) / 60000;
  if (sesionNyse && ahora >= sesionNyse.apertura && ahora < sesionNyse.cierre) {
    if (t < sesionNyse.apertura) {  // último precio de una sesión anterior: no sirve para medir el movimiento de hoy
      return min <= 4 * 24 * 60 ? { grado: "iex_cierre", etiqueta: "sin operaciones IEX hoy todavía (precio de la sesión anterior)" }
        : { grado: "vencido", etiqueta: "dato IEX vencido" };
    }
    if (min <= VIVO_MIN) return { grado: "iex_vivo", etiqueta: "IEX en vivo (solo la bolsa IEX, volumen parcial)" };
    return { grado: "iex_retrasado", etiqueta: `IEX con ${Math.round(min)} min de retraso` };
  }
  if (min <= 4 * 24 * 60) return { grado: "iex_cierre", etiqueta: "último precio IEX de la sesión (mercado cerrado)" };
  return { grado: "vencido", etiqueta: "dato IEX vencido" };
}

/** Factor acumulado de splits con fecha en (desde, hasta]: el precio anterior se divide entre él. */
export function factorSplit(splits, id, desde, hasta) {
  return (splits || []).filter((s) => s.id === id && s.fecha > desde && s.fecha <= hasta).reduce((f, s) => f * s.factor, 1);
}

/** Si un cambio parece un split no informado (≈ 1/k o ≈ k), devuelve k; si no, null. */
export function posibleSplit(razon) {
  for (const k of [2, 3, 4, 5, 8, 10, 15, 20, 25, 50]) {
    if (Math.abs(razon * k - 1) < 0.04 || Math.abs(razon / k - 1) < 0.04) return k;
  }
  return null;
}

export function referenciaSic(precioUsd, fx) {
  if (!fx || !Number.isFinite(precioUsd)) return null;
  return { precio_mxn: precioUsd * fx.valor,
    etiqueta: `referencia SIC = EE. UU. × FIX ${fx.valor.toFixed(4)} del ${fx.fecha} (no es precio del SIC)` };
}
