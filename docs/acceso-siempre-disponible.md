# Acceso a Actinver Terminal

## Acceso directo de este equipo

En el escritorio, abra **Actinver Terminal**. El acceso directo apunta a `launcher/ActinverTerminal.exe` dentro del repositorio. Si el servidor local ya responde, abre `http://127.0.0.1:8765/`. Si esta apagado, llama a `scripts/iniciar-remoto.ps1`, espera hasta dos minutos y abre la pagina cuando responda. Para reconstruir el ejecutable o el acceso directo: `launcher/compilar.ps1` y `launcher/crear-acceso-directo.ps1`.

Si Tailscale no esta instalado, no ha iniciado sesion o no responde, el iniciador **igual arranca la terminal en esta PC** (`http://127.0.0.1:8765/`) y avisa que el acceso remoto no esta activo; antes se detenia sin arrancarla. Para forzar el modo solo local: variable `ACTINVER_SIN_TAILSCALE=1`.

Pruebas del 30-sep-2026 en esta PC: con el servidor apagado, el `.exe` lo arranco y respondio en 27–51 s; con el servidor encendido abrio la pagina en 0.9 s sin crear un segundo proceso; el acceso directo del escritorio apunta a `launcher\ActinverTerminal.exe`; el servidor escucha solo en `127.0.0.1` y `tailscale serve status` indica **tailnet only**. La URL `.ts.net` respondio 200 desde esta misma PC; **falta probarla desde otro dispositivo**.

Este acceso directo depende de que **esta PC este encendida**. El ejecutable no aloja la aplicacion por si solo. El acceso remoto actual usa Tailscale Serve y sigue siendo privado.

## Acceso cuando esta PC este apagada

La aplicacion debe ejecutarse en **otro equipo encendido permanentemente**: un mini-PC o NAS compatible, o una maquina virtual/servidor Windows contratado. La opcion mas conservadora es Windows, porque el iniciador y las notificaciones de escritorio actuales ya estan preparados para ese sistema. Antes de elegir proveedor, compruebe que los contratos de datos permitan ejecutar los conectores en ese entorno.

Preparacion en el equipo permanente:

1. Instalar Windows, `uv` y Tailscale desde sus fuentes oficiales. Unir el equipo a la misma red privada Tailscale.
2. Clonar este repositorio en ese equipo. Transferir la base `data/` y `.env` por un medio privado y cifrado. Nunca subirlos a GitHub.
3. Ejecutar `iniciar-remoto.bat` una vez y verificar `/api/estado`, la interfaz y `tailscale serve status`. La salida debe indicar **tailnet only**, no Funnel.
4. Configurar el inicio automatico del proceso al arrancar ese equipo, con una cuenta de servicio propia y acceso minimo a la carpeta de datos. Probar un reinicio completo del equipo.
5. Probar desde el celular con Tailscale conectado, revisar que los respaldos y las alertas funcionen, y guardar la nueva direccion `https://<nombre-del-equipo>.ts.net/`.

La URL actual de esta PC no pasara a ser permanente por mover el servicio: el equipo nuevo tendra otro nombre. No publique la terminal con Funnel ni abra puertos del router; la aplicacion no tiene inicio de sesion propio. Tailscale Serve solo comparte el servicio con los dispositivos autorizados de la red privada: https://tailscale.com/docs/features/tailscale-serve.

**Estado:** este despliegue permanente no esta activado. Falta elegir o proporcionar el equipo anfitrion, y entonces instalar, migrar datos y probar la nueva URL.
