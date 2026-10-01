// Autenticación de la sincronización: HMAC-SHA256 sobre marca de tiempo, nonce, método, ruta y hash del cuerpo.
// Ventana de 5 minutos y nonce de un solo uso (guardado en D1) contra reenvíos; nunca se registra el secreto.

const enc = new TextEncoder();
export const VENTANA_SEGUNDOS = 300;

const hex = (buf) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");

export async function sha256Hex(texto) {
  return hex(await crypto.subtle.digest("SHA-256", enc.encode(texto)));
}

export async function hmacHex(secreto, texto) {
  const clave = await crypto.subtle.importKey("raw", enc.encode(secreto), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return hex(await crypto.subtle.sign("HMAC", clave, enc.encode(texto)));
}

export function canonico({ ts, nonce, metodo, ruta, hashCuerpo }) {
  return `v1:${ts}:${nonce}:${metodo.toUpperCase()}:${ruta}:${hashCuerpo}`;
}

export async function firmar(secreto, { ts, nonce, metodo, ruta, cuerpo = "" }) {
  return hmacHex(secreto, canonico({ ts, nonce, metodo, ruta, hashCuerpo: await sha256Hex(cuerpo) }));
}

export function igual(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}

/**
 * Verifica una petición firmada. `nonceUsado(nonce)` debe registrar el nonce de forma atómica y devolver true si ya
 * existía. Devuelve {ok, motivo}; el motivo es genérico hacia fuera (no revela qué parte falló).
 */
export async function verificar({ secreto, ts, nonce, firma, metodo, ruta, cuerpo, ahoraSeg, nonceUsado }) {
  if (!secreto || secreto.length < 32) return { ok: false, motivo: "monitor sin secreto configurado" };
  if (!/^\d{10}$/.test(String(ts || "")) || !/^[0-9a-f]{32,64}$/.test(String(nonce || "")) || !/^[0-9a-f]{64}$/.test(String(firma || ""))) {
    return { ok: false, motivo: "cabeceras de firma inválidas" };
  }
  if (Math.abs(ahoraSeg - Number(ts)) > VENTANA_SEGUNDOS) return { ok: false, motivo: "marca de tiempo fuera de la ventana" };
  const esperada = await firmar(secreto, { ts, nonce, metodo, ruta, cuerpo });
  if (!igual(esperada, firma)) return { ok: false, motivo: "firma inválida" };
  if (await nonceUsado(nonce, Number(ts))) return { ok: false, motivo: "petición repetida" };
  return { ok: true };
}
