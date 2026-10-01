-- Estado mínimo del monitor en la nube (D1). Sin credenciales: los secretos viven en el gestor de secretos de Cloudflare.
CREATE TABLE IF NOT EXISTS estado (clave TEXT PRIMARY KEY, valor TEXT NOT NULL, actualizado_en TEXT NOT NULL);
-- Nonces de sincronización ya usados (anti-reenvío); se depuran después de 1 día.
CREATE TABLE IF NOT EXISTS nonces (nonce TEXT PRIMARY KEY, visto_en INTEGER NOT NULL);
-- Avisos: la clave única impide duplicados aunque el Worker se reinicie o dos ejecuciones se crucen.
CREATE TABLE IF NOT EXISTS avisos (
  clave TEXT PRIMARY KEY, tipo TEXT NOT NULL, texto TEXT NOT NULL,
  estado TEXT NOT NULL CHECK (estado IN ('pendiente', 'enviado', 'error', 'descartado')),
  intentos INTEGER NOT NULL DEFAULT 0, creado_en TEXT NOT NULL, enviado_en TEXT, no_antes_de TEXT
);
CREATE INDEX IF NOT EXISTS avisos_pendientes ON avisos (estado, no_antes_de);
CREATE TABLE IF NOT EXISTS ejecuciones (id INTEGER PRIMARY KEY AUTOINCREMENT, inicio TEXT NOT NULL, fin TEXT, resultado TEXT);
