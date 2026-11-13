# Correr la terminal desde GitHub (Codespaces)

1. En la página del repositorio: **Code → Codespaces → Create codespace on main**.
2. Espere a que termine `uv sync` (2–4 min la primera vez).
3. En la terminal del Codespace:

```bash
uv run terminal demo --sin-navegador      # datos sintéticos etiquetados
uv run terminal iniciar --sin-navegador   # datos reales (requiere claves en .env)
```

4. Se abre el puerto 8765 en el navegador. El puerto queda **privado**: solo su cuenta de GitHub lo ve.

## Datos reales

El Codespace empieza sin base de datos (la base de su PC no se sube a GitHub). Edite `.env` en el Codespace con sus
claves gratuitas (FRED no requiere clave; Banxico, Tiingo, EODHD, Alpaca, ver `.env.example`) y ejecute:

```bash
uv run terminal actualizar
uv run terminal iniciar --sin-navegador
```

No suba `.env` al repositorio (está en `.gitignore`). Su cuenta del Reto no se copia: se captura igual que en su PC.

## Seguridad y costo

- El servidor sigue escuchando en `127.0.0.1` dentro del contenedor. La terminal acepta, además, **solo** el dominio
  reenviado exacto de ese Codespace (`terminal/seguridad.py::host_codespace`), y solo cuando `CODESPACES=true`.
- No cambie la visibilidad del puerto a «Public»: cualquiera con el enlace vería su información.
- Codespaces es gratuito para cuentas personales dentro de la cuota mensual de GitHub. Con el límite de gasto en $0
  (predeterminado) no se cobra; al agotar la cuota el Codespace se detiene. Detenga el Codespace al terminar.
