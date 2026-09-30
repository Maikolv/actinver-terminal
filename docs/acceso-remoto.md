# Acceso remoto privado a Actinver Terminal

La terminal sigue escuchando solo en `127.0.0.1:8765`. **Tailscale Serve** ofrece una dirección HTTPS accesible únicamente desde dispositivos de la misma red privada Tailscale. La terminal exige además el nombre DNS de esta PC y la identidad de la cuenta Tailscale. No se usa Tailscale Funnel ni se abre el puerto del router.

## Activación

1. Instale Tailscale en la PC desde [su página oficial para Windows](https://tailscale.com/download/windows) e inicie sesión. Si `winget` funciona en su equipo, también puede usar `winget install tailscale.tailscale`.
2. Instale Tailscale en su celular o laptop e inicie sesión con la **misma cuenta**.
3. Haga doble clic en `iniciar-remoto.bat` dentro del proyecto. El iniciador encuentra Tailscale aunque no esté en `PATH`, toma el nombre y usuario de la cuenta conectada, configura `.env` sin mostrar sus secretos, reutiliza la terminal cuando ya tiene esa configuración y activa Serve. Si Tailscale solicita habilitar HTTPS en la red, complete la página de configuración que abre.
4. Abra desde el otro dispositivo la dirección `https://...ts.net` que muestra el iniciador. La PC debe permanecer encendida, sin suspenderse, y Tailscale debe seguir conectado.

Para detener la publicación privada, ejecute `tailscale serve --https=443 off` desde una consola con acceso a Tailscale. La terminal local seguirá disponible en `http://127.0.0.1:8765`.

## Seguridad y alcance

- `TERMINAL_HOSTS_REMOTOS` y `TERMINAL_USUARIOS_REMOTOS` se derivan de la sesión Tailscale de esta PC y se guardan en `.env`. El servidor debe reiniciarse para aplicar un cambio; el iniciador lo hace solo cuando es necesario.
- Tailscale Serve añade `Tailscale-User-Login`; Tailscale Funnel, que es público, no añade esa cabecera y la terminal lo rechaza. [Documentación oficial de Serve](https://tailscale.com/docs/features/tailscale-serve).
- El usuario decide y captura cada orden en el portal del Reto. El acceso remoto no activa operaciones automáticas.
- Telegram continúa disponible sin abrir la interfaz web a distancia.

Si el inicio de sesión de Tailscale no está terminado, el iniciador mostrará un mensaje y no publicará la terminal.
