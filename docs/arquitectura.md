# Arquitectura, límites de confianza y ruta de una alerta

Diagramas en Mermaid: texto versionado y verificable, con el enfoque de `archify`.

## Flujo de datos y límites de confianza

```mermaid
flowchart LR
  subgraph Externo["Fuera del equipo (no confiable)"]
    BMV[(Producto BMV licenciado<br/>PENDIENTE)]
    FRED[(FRED · Banxico<br/>tipo de cambio)]
    ORI[(Alpaca · Tiingo<br/>origen USD, con clave)]
    SA[(Seeking Alpha RSS)]
    FF[(Forex Factory feed)]
    SEC[(SEC EDGAR Form 4)]
    TV[(TradingView<br/>webhook del usuario)]
    PORTAL[[Portal Actinver<br/>SIN ACCESO AUTOMÁTICO]]
  end
  subgraph Local["Equipo del usuario · 127.0.0.1"]
    ADP[Adaptadores<br/>límites · caché · reintentos]
    NORM[Normalización<br/>símbolos · clasificación CFD/cripto<br/>vigencia · event_time/available_at]
    DB[(SQLite<br/>disparadores de integridad)]
    CART[Cartera confirmada<br/>práctica ↔ competencia]
    INV[Investigación<br/>walk-forward · prueba intacta]
    ALR[Alertas<br/>inhibición · ficha de revisión]
    UI[Interfaz<br/>PASADO · PRESENTE · FUTURO]
  end
  USR((Participante))
  BMV -.-> ADP
  FRED --> ADP
  ORI --> ADP
  SA --> ADP
  FF --> ADP
  SEC --> ADP
  TV -- "secreto · esquema · duplicados" --> NORM
  ADP --> NORM --> DB
  DB --> CART --> ALR
  DB --> INV --> DB
  ALR --> UI
  CART --> UI
  INV --> UI
  USR -- "captura operaciones y saldo" --> UI
  USR -- "opera a mano" --> PORTAL
```

## Ruta de una alerta

```mermaid
sequenceDiagram
  participant M as Motor (cada 15 min o evento)
  participant R as Reglas
  participant Q as Calidad de datos
  participant P as procesar()
  participant N as Notificador
  participant U as Participante
  M->>R: cartera, propuestas, precios, eventos
  R->>Q: condiciones direccionales y de datos
  Q-->>R: inhibe direccionales sin precio confiable o con noticias contradictorias
  R->>P: condiciones (prefijo REVISAR, cálculo, incertidumbre)
  P->>P: flanco de subida · enfriamiento 6 h · deduplicación
  P->>N: agrupa y silencia fuera de horario BMV
  N-->>U: escritorio / Telegram / correo (opcionales)
  U->>U: revisa la ficha, simula, registra la decisión en la bitácora
  Note over U: La orden, si la hay, la captura el participante en el portal
```

## Red de fuentes por instrumento

```mermaid
flowchart TB
  SICMXN["SIC:AAPL · MXN · XMEX"] ---|serie BMV licenciada| BMVs[(BMV)]
  SICMXN -.referencia, no sustituto.- ORIG["AAPL · USD · XNAS"]
  ORIG --- ORIp[(Alpaca/Tiingo)]
  SICMXN -.contexto.- SAc[(Seeking Alpha)]
  SICMXN -.insiders EE. UU.; NO CUBRE BMV.- SECc[(SEC)]
  LOCAL["BMV:AMX · MXN · XMEX"] --- BMVs
  LOCAL -.EOD con clave.- EOD[(EODHD)]
  CFD["Serie CFD / cripto"] -. rechazada por clasificacion.py .-x LOCAL
```
