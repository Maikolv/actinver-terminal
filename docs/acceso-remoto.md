# Acceso remoto a la terminal (privado, con Tailscale)

La terminal no tiene usuario ni contraseña, así que **nunca debe quedar abierta a Internet**. El acceso remoto usa **Tailscale Serve**, que crea una red privada entre **sus** dispositivos:

- El servidor sigue escuchando solo en `127.0.0.1` de su PC.
- Tailscale lo publica con HTTPS únicamente dentro de su red.
- La terminal solo acepta una petición remota si su nombre `*.ts.net` está autorizado en `.env` y si trae la identidad del usuario de la red (cabecera `Tailscale-User-Login`, que Tailscale Serve añade).
- Un enlace público, como Tailscale **Funnel** o un túnel de Cloudflare o ngrok, se rechaza.

## Configuración (una sola vez)

1. **Instale Tailscale en la PC** donde corre la terminal:
   ```
   winget install tailscale.tailscale
   ```
   Abra Tailscale e inicie sesión con su cuenta. Si no tiene una, créela usted.
2. **Instale Tailscale en su celular o laptop** (App Store, Google Play o tailscale.com/download) e inicie sesión con **la misma cuenta**.
3. En la consola de Tailscale (login.tailscale.com), active **MagicDNS** y **HTTPS Certificates** en DNS.
4. Ejecute `iniciar-remoto.bat`. Publica el puerto 8765 en su red, muestra la dirección (por ejemplo, `https://mi-pc.tailXXXX.ts.net`) e inicia la terminal.
5. Agregue a `.env` el nombre sin `https://`. Si quiere limitarlo a su propia cuenta, agregue también su usuario:
   ```
   TERMINAL_HOSTS_REMOTOS=mi-pc.tailXXXX.ts.net
   TERMINAL_USUARIOS_REMOTOS=su-correo@ejemplo.com
   ```
   Reinicie con `iniciar-remoto.bat`.
6. Desde el celular, con Tailscale conectado, abra la dirección que se mostró.

## Qué funciona a distancia

Todo lo de la interfaz: resumen, propuestas, boletas, captura del portal, ranking y alertas. La PC debe estar **encendida y sin suspenderse**, con la terminal corriendo.

Sin Tailscale sigue disponible el bot de Telegram (`/plan`, `/boletas`, `/estado`, preguntas).

## Qué no hacer

- No use `tailscale funnel`: publica la terminal en Internet.
- No abra el puerto 8765 en el router ni use túneles públicos. La terminal los rechaza por diseño.
- Para dejar de publicarla: `tailscale serve --https=443 off` (o `tailscale serve reset`).
