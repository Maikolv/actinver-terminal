# Guía paso a paso para abrir Help Quote Terminal

[Repositorio en GitHub](https://github.com/Maikolv/help-quote-terminal)

| Ruta | Cuándo elegirla | Datos |
|---|---|---|
| A. Demo en el navegador | Para ver la estación de Mercado sin instalar nada | Simulados |
| B. GitHub Codespaces | Para usar la terminal completa en un entorno de GitHub | Simulados o reales con sus claves |
| C. Windows | Para usar la terminal completa en su PC | Simulados o reales con sus claves |

## Ruta A — Demo en el navegador

1. Abra la [portada pública](https://maikolv.github.io/help-quote-terminal/) y busque el aviso **DATOS SIMULADOS**.
2. Pulse **Abrir la estación (demo)**. El monitor muestra los instrumentos y la columna **Dato** marca sus precios como **SIMULADO**.
3. Pulse `/` para enfocar **Buscar instrumento**. Escriba, por ejemplo, `XOM` y pulse Enter para seleccionar la primera coincidencia. Use ↑ y ↓ para cambiar de fila. El filtro **Con gráfico en esta foto** deja solo los instrumentos con serie histórica.
4. En el celular verá **Monitor**, **Gráfico** y **Detalle**. Toque una fila para abrir **Gráfico**.

La portada y el monitor deberían cargar en unos segundos. La demo es una foto fija con datos simulados.

## Ruta B — GitHub Codespaces

1. Inicie sesión en GitHub. En el repositorio, pulse **Code** → **Codespaces** → **Create codespace on main**. También puede usar el botón de Codespaces del README. Use solo la cuota gratuita de su cuenta personal. Si GitHub pide una tarjeta o indica un costo, deténgase.
2. Espere a que abra el editor y termine la instalación de dependencias. Se abre [docs/codespaces.md](codespaces.md). El tiempo de creación depende de GitHub y de las descargas.
3. En el menú del editor, abra **Terminal** → **New Terminal** y ejecute:

   ```bash
   uv run terminal demo --sin-navegador
   ```

4. Abra **Ports**, busque el puerto **8765** y compruebe que su visibilidad sea **Private**. Pulse el icono del globo (**Open in Browser**) o use la pestaña que se abre automáticamente. Deje el puerto en **Private**. La terminal debe mostrar **DATOS SIMULADOS — modo demostración.**
5. Al terminar, pulse Ctrl+C en la terminal del editor. En [sus Codespaces](https://github.com/codespaces), abra el menú del entorno y seleccione **Stop codespace**. Si solo lo creó para probar, seleccione **Delete** después de detenerlo. Un Codespace detenido sigue ocupando espacio de la cuota mientras exista.

Para usar datos reales, detenga la demo, edite el `.env` del Codespace con sus claves gratuitas y ejecute estas líneas:

```bash
uv run terminal actualizar
uv run terminal iniciar --sin-navegador
```

El workflow [codespace.yml](../.github/workflows/codespace.yml) comprobó el contenedor, el arranque y el nombre de host permitido en 47 segundos. El reenvío privado en un Codespace real sigue pendiente. Para probarlo por CLI, su cuenta debe conceder el permiso `codespace` con `gh auth refresh -h github.com -s codespace`.

## Ruta C — Windows con PowerShell 5.1

### 1. Instale Git y uv

Si ya tiene las herramientas, pase al siguiente paso. Abra **Windows PowerShell** y ejecute:

```powershell
winget install --id Git.Git --exact
winget install --id astral-sh.uv --exact
```

Cierre y vuelva a abrir PowerShell. Compruebe que `git --version` y `uv --version` muestran su versión.

### 2. Descargue y prepare el repositorio

```powershell
$repos = Join-Path $env:USERPROFILE 'Repos'
New-Item -ItemType Directory -Path $repos -Force | Out-Null
Set-Location -LiteralPath $repos
git clone https://github.com/Maikolv/help-quote-terminal.git
Set-Location -LiteralPath .\help-quote-terminal
uv sync
if (-not (Test-Path -LiteralPath .env)) { copy .env.example .env }
```

Si ya tiene el repositorio, entre en su carpeta actual, incluso si se llama `actinver-terminal`, y ejecute `git pull --ff-only` antes de `uv sync`. La copia de `.env.example` conserva cualquier `.env` que ya exista.

En la prueba, clonar tomó 43 segundos y `uv sync` tomó 2 minutos y 26 segundos, con Git y uv ya instalados. La primera descarga depende de su conexión y de los paquetes que uv tenga guardados.

### 3. Abra la demo

```powershell
.\start.bat demo
```

Se abre [http://127.0.0.1:8765/](http://127.0.0.1:8765/). Si prefiere abrir la dirección usted mismo, use `.\start.bat demo --sin-navegador`. Confirme que la portada diga **DATOS SIMULADOS — modo demostración.** La demo guarda su base en `data/demo/`. Para detenerla, pulse Ctrl+C en la ventana donde la inició.

En la prueba, el primer arranque tardó unos 2 minutos y medio en responder mientras preparaba los datos simulados.

Si quiere verificar el servidor, ejecute esto desde otra ventana de PowerShell. Debe mostrar `200`.

```powershell
(Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8765/api/estado').StatusCode
```

### 4. Primer uso con datos reales (opcional)

1. Detenga la demo, abra el archivo con `notepad.exe .env`, agregue las claves gratuitas que tenga y guárdelo. Si todavía no hay cotizaciones confiables, las propuestas quedan suspendidas.
2. Ejecute `.\start.bat`. En la cabecera encontrará **Actualizar datos**. El comando equivalente es `uv run terminal actualizar`.
3. Abra **Mi portafolio Actinver**. En **Actualizar desde el portal (copiar y pegar)** puede ver cómo capturar una cartera. Para importar, abra **Registro local de la terminal, operaciones manuales e importación de archivos (avanzado)** → **Importar desde archivo**. Elija **Tipo de archivo** y use **Descargar plantilla** para obtener el formato.
4. Vuelva a **Plan de acción** para consultar qué vender, comprar o mantener.

## Si algo falla

| Síntoma | Qué hacer |
|---|---|
| `git` o `uv` no se reconoce | Cierre y vuelva a abrir PowerShell y confirme la instalación con `git --version` y `uv --version`. |
| `.\start.bat` no se reconoce o `Failed to spawn: terminal` | Entre en la carpeta que contiene `start.bat` y `pyproject.toml`. Ejecute `uv sync` y vuelva a iniciar. |
| `git clone` descarga el repositorio, pero falla al preparar los archivos | Intente en una carpeta donde tenga permisos de escritura, por ejemplo `$env:USERPROFILE\Repos`. Use una carpeta nueva para la prueba. |
| El puerto 8765 está ocupado | Deje abierta la terminal que ya usa ese puerto y configure un puerto libre en la copia de prueba, como se indica abajo. |
| El navegador dice que no puede conectarse | Espere a que termine el arranque. Revise la dirección y el puerto impresos en PowerShell. |
| La estación muestra instrumentos, pero alguno no tiene gráfico | Elija **Con gráfico en esta foto** o busque una fila con ◆. |
| Aparece «SIN PRECIO CONFIABLE» con datos reales | Revise las claves gratuitas en `.env` y pulse **Actualizar datos**. Para explorar la interfaz con precios de ejemplo, inicie la demo. |
| En Codespaces no aparece el puerto | Verifique que la demo siga corriendo. En **Ports**, pulse **Forward a Port**, escriba `8765` y confirme **Private**. |
| Codespaces muestra «Host no permitido» o solicita iniciar sesión | Abra el enlace del puerto 8765 desde **Ports** con la misma cuenta que creó ese Codespace. |

### Usar otro puerto en la copia de prueba de Windows

En una copia de prueba recién clonada, confirme que `Test-NetConnection -ComputerName 127.0.0.1 -Port 8766 -InformationLevel Quiet` devuelve `False`. Si devuelve `True`, elija otro puerto. Guarde este ajuste solo en el `config/local.toml` de esa copia:

```powershell
@('[app]', 'puerto = 8766') | Set-Content -LiteralPath .\config\local.toml -Encoding Ascii
.\start.bat demo --sin-navegador
```

Abra [http://127.0.0.1:8766/](http://127.0.0.1:8766/) y use el mismo puerto para consultar `/api/estado`. La terminal sirve únicamente en `127.0.0.1`.
