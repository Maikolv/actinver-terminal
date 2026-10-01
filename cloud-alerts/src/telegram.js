// Envío por Telegram (solo sendMessage: la nube no lee mensajes, así no compite con el getUpdates del bot local).
// Respeta 429 con retry_after: reintenta una vez si la espera es corta; si no, deja el aviso en cola para la
// siguiente ejecución. Nunca registra la URL (contiene el token).

export const MAX_TEXTO = 4000;
export const PAUSA_MS = 1100;   // ≤ 1 mensaje por segundo al mismo chat
const ESPERA_MAX_S = 3;

const dormirReal = (ms) => new Promise((r) => setTimeout(r, ms));

export function recortar(texto) {
  return texto.length <= MAX_TEXTO ? texto : `${texto.slice(0, MAX_TEXTO - 40)}\n… (recortado; detalle en la terminal)`;
}

export async function enviar(env, texto, { fetchFn = fetch, dormir = dormirReal } = {}) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_CHAT_ID) return { estado: "no_configurado" };
  const url = `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`;
  const cuerpo = JSON.stringify({ chat_id: env.TELEGRAM_CHAT_ID, text: recortar(texto), disable_web_page_preview: true });
  for (let intento = 0; intento < 2; intento++) {
    let r;
    try {
      r = await fetchFn(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: cuerpo });
    } catch {
      return { estado: "error", detalle: "sin_conexion" };
    }
    if (r.status === 200) return { estado: "enviado" };
    if (r.status === 429) {
      let espera = 30;
      try { espera = Number((await r.json())?.parameters?.retry_after) || 30; } catch { /* cuerpo no JSON */ }
      if (intento === 0 && espera <= ESPERA_MAX_S) {
        await dormir(espera * 1000);
        continue;
      }
      return { estado: "limite", retry_after: espera };
    }
    return { estado: "error", detalle: `http_${r.status}` };
  }
  return { estado: "limite", retry_after: ESPERA_MAX_S };
}
