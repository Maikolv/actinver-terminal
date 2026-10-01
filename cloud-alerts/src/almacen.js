// Acceso a D1: estado duradero, nonces, avisos con clave única y registro de ejecuciones.

export const MAX_INTENTOS = 5;

export async function leer(db, clave) {
  const f = await db.prepare("SELECT valor FROM estado WHERE clave = ?").bind(clave).first();
  return f ? JSON.parse(f.valor) : null;
}

export async function guardar(db, clave, valor, ahora = new Date()) {
  await db.prepare("INSERT INTO estado (clave, valor, actualizado_en) VALUES (?, ?, ?) "
    + "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor, actualizado_en = excluded.actualizado_en")
    .bind(clave, JSON.stringify(valor), ahora.toISOString()).run();
}

/** Registra el nonce; devuelve true si ya existía (reenvío). Atómico gracias a la clave primaria. */
export async function nonceUsado(db, nonce, tsSeg) {
  const r = await db.prepare("INSERT OR IGNORE INTO nonces (nonce, visto_en) VALUES (?, ?)").bind(nonce, tsSeg).run();
  return (r.meta?.changes ?? 0) === 0;
}

export async function depurar(db, ahora = new Date()) {
  await db.prepare("DELETE FROM nonces WHERE visto_en < ?").bind(Math.floor(ahora / 1000) - 86400).run();
  await db.prepare("DELETE FROM avisos WHERE creado_en < ? AND estado IN ('enviado', 'descartado')")
    .bind(new Date(ahora - 30 * 86400000).toISOString()).run();
  await db.prepare("DELETE FROM ejecuciones WHERE id <= (SELECT MAX(id) - 200 FROM ejecuciones)").run();
}

/** Inserta el aviso si su clave no existe. Devuelve true si es nuevo. */
export async function registrarAviso(db, a, ahora = new Date()) {
  const r = await db.prepare("INSERT OR IGNORE INTO avisos (clave, tipo, texto, estado, creado_en) VALUES (?, ?, ?, 'pendiente', ?)")
    .bind(a.clave, a.tipo, a.texto, ahora.toISOString()).run();
  return (r.meta?.changes ?? 0) > 0;
}

export async function pendientes(db, ahora = new Date(), limite = 10) {
  const r = await db.prepare("SELECT clave, tipo, texto, intentos FROM avisos WHERE estado IN ('pendiente', 'error') AND intentos < ? "
    + "AND (no_antes_de IS NULL OR no_antes_de <= ?) ORDER BY creado_en LIMIT ?").bind(MAX_INTENTOS, ahora.toISOString(), limite).all();
  return r.results || [];
}

export async function marcar(db, claves, estado, ahora = new Date(), noAntesDe = null) {
  for (const c of claves) {
    await db.prepare("UPDATE avisos SET estado = ?, intentos = intentos + 1, enviado_en = CASE WHEN ? = 'enviado' THEN ? ELSE enviado_en END, "
      + "no_antes_de = ? WHERE clave = ?").bind(estado, estado, ahora.toISOString(), noAntesDe, c).run();
  }
}

export async function posponer(db, claves, noAntesDe) {
  for (const c of claves) await db.prepare("UPDATE avisos SET no_antes_de = ? WHERE clave = ?").bind(noAntesDe, c).run();
}

export async function recientes(db, limite = 10) {
  const r = await db.prepare("SELECT clave, tipo, estado, creado_en, enviado_en FROM avisos ORDER BY creado_en DESC LIMIT ?").bind(limite).all();
  return r.results || [];
}

export async function iniciarEjecucion(db, ahora) {
  const r = await db.prepare("INSERT INTO ejecuciones (inicio) VALUES (?)").bind(ahora.toISOString()).run();
  return r.meta?.last_row_id ?? null;
}

export async function cerrarEjecucion(db, id, resultado, fin = new Date()) {
  if (id == null) return;
  await db.prepare("UPDATE ejecuciones SET fin = ?, resultado = ? WHERE id = ?").bind(fin.toISOString(), JSON.stringify(resultado), id).run();
}
