// Calendario bursátil. Fuente principal: las sesiones que sincroniza la terminal (exchange_calendars + horario de las
// bases del Reto, ya en UTC: cambios de horario de EE. UU. incluidos). Respaldo si faltan: días hábiles, festivos
// conocidos y horario de Nueva York 09:30–16:00 (la BMV se alinea a esa hora durante el Reto); se marca «supuesto».

export const ZONA = "America/Mexico_City";
const FESTIVOS = {
  XNYS: ["2026-09-07", "2026-11-26", "2026-12-25", "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26"],
  XMEX: ["2026-09-16", "2026-11-02", "2026-11-16", "2026-12-25", "2027-01-01", "2027-02-01", "2027-03-15", "2027-03-25", "2027-03-26"],
};

function partes(fecha, zona) {
  const f = new Intl.DateTimeFormat("en-CA", {
    timeZone: zona, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit",
    hourCycle: "h23", weekday: "short",
  }).formatToParts(fecha);
  const o = Object.fromEntries(f.map((p) => [p.type, p.value]));
  return { fecha: `${o.year}-${o.month}-${o.day}`, hora: Number(o.hour), minuto: Number(o.minute), seg: Number(o.second), dia: o.weekday };
}

export const fechaLocal = (fecha, zona = ZONA) => partes(fecha, zona).fecha;

export function horaLocal(fecha, zona = ZONA) {
  const p = partes(fecha, zona);
  return `${p.fecha.slice(8, 10)}-${p.fecha.slice(5, 7)} ${String(p.hora).padStart(2, "0")}:${String(p.minuto).padStart(2, "0")}`;
}

/** Instante UTC de una hora local («YYYY-MM-DD», «HH:MM») en una zona (resuelve horario de verano con Intl). */
export function utcDe(fecha, hhmm, zona) {
  const [h, m] = hhmm.split(":").map(Number);
  const supuesto = Date.UTC(+fecha.slice(0, 4), +fecha.slice(5, 7) - 1, +fecha.slice(8, 10), h, m);
  let t = supuesto;
  for (let i = 0; i < 2; i++) {  // dos iteraciones bastan para converger alrededor del cambio de horario
    const p = partes(new Date(t), zona);
    const visto = Date.UTC(+p.fecha.slice(0, 4), +p.fecha.slice(5, 7) - 1, +p.fecha.slice(8, 10), p.hora, p.minuto);
    t += supuesto - visto;
  }
  return new Date(t);
}

/** Sesión de un mercado en la fecha (de la Ciudad de México) o null si está cerrado. */
export function sesion(calendario, mercado, fecha) {
  const propias = (calendario || []).filter((s) => s.mercado === mercado);
  if (propias.length) {
    const fechas = propias.map((s) => s.fecha).sort();
    if (fecha >= fechas[0] && fecha <= fechas[fechas.length - 1]) {
      const s = propias.find((x) => x.fecha === fecha);
      return s ? { apertura: new Date(s.apertura), cierre: new Date(s.cierre), fuente: "sincronizado" } : null;
    }
  }
  const dia = partes(utcDe(fecha, "12:00", ZONA), ZONA).dia;
  if (dia === "Sat" || dia === "Sun" || FESTIVOS[mercado].includes(fecha)) return null;
  return { apertura: utcDe(fecha, "09:30", "America/New_York"), cierre: utcDe(fecha, "16:00", "America/New_York"), fuente: "supuesto" };
}

export function estadoMercado(calendario, mercado, ahora) {
  const s = sesion(calendario, mercado, fechaLocal(ahora));
  return { sesion: s, abierto: Boolean(s && ahora >= s.apertura && ahora < s.cierre) };
}

// Próxima ejecución del disparador de wrangler.jsonc: cada 15 min, de 12 a 21 h UTC, de lunes a viernes.
export function proximaRevision(ahora) {
  const t = new Date(Math.floor(ahora.getTime() / 900000) * 900000 + 900000);
  for (let i = 0; i < 4 * 24 * 8; i++, t.setTime(t.getTime() + 900000)) {
    const d = t.getUTCDay(), h = t.getUTCHours();
    if (d >= 1 && d <= 5 && h >= 12 && h <= 21) return t;
  }
  return null;
}
