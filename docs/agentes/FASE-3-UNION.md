# Fase 3 — Unir `console-web/` con el backend

Documento de trabajo de Alejandro. No es un ADR.

**Rama:** `alejandro/console-api`. El puente HTTP de sólo lectura ya existe
(`src/albertitos/console/lecturas.py` + `api.py`, 6 GET, tests en `tests/test_console.py`).
Streamlit no se ha tocado. Makefile tampoco (hay que pedírselo a Miguel).

Arranque del puente:

```
uv run python -m albertitos.console.api   # http://127.0.0.1:8000
```

En `console-web/.env.local`: `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000` y `NEXT_PUBLIC_USE_MOCK=false`.

Hoy es sábado 19. La defensa es el domingo. A las **20:00** (repliegue 3 de `docs/hitos.md`): si la consola no enseña una traza, Alfonso enseña `albertitos trace` en terminal. Streamlit ya cubre ese repliegue. Esta fase es para que la demo se vea en Next, no para que el equipo deje de tener consola.

---

## 1. Dónde estamos

| Pieza | Estado | Dónde |
|---|---|---|
| Dominio Albertitos en la UI | Hecho (fase 1) | `console-web/lib/types.ts`, pantallas, mock |
| Next dentro de HS-Maisa | Hecho (fase 2) | `console-web/` |
| Capa HTTP del frontend | Lista, en mock | `lib/api/*` + `mappers.ts` + `USE_MOCK` |
| Backend HTTP de lectura | **No existe** | El backend no tiene FastAPI ni `/panel` |
| Consola oficial | Streamlit, sólo lectura | `src/albertitos/console/app.py` · `make console` → `:8501` |
| Fuente de verdad | SQLite WAL | `dist/albertitos.db` (ADR-0008) |
| Quién escribe | Solo la CLI | `albertitos run / reprocess / …` (ADR-0007) |

El frontend **ya no hay que reescribirlo**. Las páginas hablan `PAGAR | NO_PAGAR | ESCALAR`, `file_id` NFC, etapas `ingest extract validate enrich decide emit`, y `PENDIENTE` cuando no hay decisión vigente. `lib/api/*.ts` ya tiene las 6 lecturas. Con `NEXT_PUBLIC_USE_MOCK=false` y una URL, el client pega a HTTP. Ninguna página cambia.

El backend **ya tiene los datos**. Hoy: 500/500 con decisión (438 PAGAR · 53 ESCALAR · 9 NO_PAGAR, cifras de `docs/ESTADO-BACKEND.md`). `core.db.traza(file_id)` y `core.db.resumen()` existen. Streamlit los usa.

**El hueco es un puente de lectura** entre `dist/albertitos.db` y `console-web/lib/api`.

---

## 2. Cómo arrancar ahora (sin unir nada)

El mock funciona solo. No hace falta Python ni BD.

```bash
cd console-web
pnpm install
cp .env.example .env.local   # ya trae USE_MOCK=true
pnpm dev                     # http://localhost:3000
```

Pantallas que importan para la defensa:

| Ruta | Qué enseña Alfonso |
|---|---|
| `/` | Panel: volumen, PAGAR/ESCALAR/NO_PAGAR, pendientes, versiones, ritmo, coste |
| `/invoices` | Cola. Filtro ESCALAR / PENDIENTE / lote / regla |
| `/invoices/F26-2201_transportes.pdf` | El PDF que ordena escalar; nosotros escalamos por la norma + fragmento |
| `/invoices/scan_017.pdf` | PENDIENTE (LLM caído) — bloque 4 de resiliencia |
| `/audit` y detalle → pestaña Traza | hechos → maestro → ERP → reglas → resultado |

Streamlit de reserva (ya con BD real):

```bash
make db                      # si no hay dist/albertitos.db
make console                 # http://localhost:8501
```

La demo de Alfonso puede ir **entera** por Streamlit. Next es la cara bonita. Si Next no llega a las 20:00, no es NO APTO.

---

## 3. Qué no se hace

- **No se toca `core/`.** Contratos congelados. Si falta un dato, se pide a Miguel una columna/evento; no se calcula en la consola.
- **No se borra Streamlit.** Es el plan B del portátil de Alfonso (`docs/guion-defensa.md`: “Consola → terminal”).
- **No se añade FastAPI ni otra dependencia Python.** El stack es “nada más sin ADR”. ADR-0007 descartó explícitamente “API web (FastAPI) y una SPA” como producto. Lo que sí cabe: un HTTP mínimo de **stdlib** que solo lee, o rutas `app/api` de Next.
- **No se escriben decisiones desde la UI.** Ni Approve, ni Reject, ni editar hechos. Recalcular es `albertitos reprocess --impacted` (CLI; Streamlit ya lo lanza por subprocess).
- **No se rediseña** paleta, rutas ni pantallas. El pulido de copy (`pulido_ux_consola_40d7af35.plan.md`) es independiente y se puede hacer contra el mock.
- **No hace falta servir el PDF real para el MVP.** `InvoiceDocument` es una página simulada con los hechos recuadrados. El contrato no expone URL del PDF. Servirlo desde `data/caja/` es bonus de demo, no bloquea la unión.
- **No se toca el Makefile / `.gitignore` raíz sin avisar a Miguel.**

---

## 4. La única decisión de diseño: dónde vive el puente

Hay dos sitios razonables. Hay que elegir **uno** con Miguel (dueño de Makefile y de “nada más sin ADR”) antes de escribir código. Recomendación abajo.

### Opción A — HTTP de stdlib en `src/albertitos/console/` (recomendada)

Un `http.server` (el ERP ya usa `ThreadingHTTPServer`; cero deps nuevas) que abre la BD en sólo lectura (`db.conectar(..., solo_lectura=True)`) y responde JSON a las 6 rutas que el frontend ya espera.

Por qué esta:

- Reutiliza `core.db.traza` / `resumen` y los modelos pydantic (`MasterSnapshot`, `ErpSnapshot`) para armar `fuentes`.
- Vive en el módulo de Alejandro. No entra en `core/`.
- Streamlit y el HTTP pueden compartir las mismas consultas (`console/lecturas.py`): un solo SQL, dos caras.
- En la defensa: Python ya está; Node solo lo necesita quien levante Next.
- Respeta el espíritu de ADR-0007: la consola sigue siendo sólo lectura; la CLI es quien escribe.

Arranque objetivo:

```
make console-api     # :8000, stdlib, CORS localhost:3000
make console-web     # cd console-web && pnpm dev
```

`.env.local` del frontend:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCK=false
```

Hacen falta **las dos**. Sin URL, `lib/config.ts` se queda en mock aunque el flag sea false.

### Opción B — Route Handlers de Next (`console-web/app/api`)

Next lee `dist/albertitos.db` con `better-sqlite3` (o sql.js). Un solo proceso Node.

Por qué no (salvo que Miguel prefiera no tocar Python):

- Dependencia nativa en Windows (el portátil de Alejandro) y en el de Alfonso.
- Node hablando WAL mientras la CLI escribe es más frágil que el cliente sqlite3 de Python, que ya está ensayado.
- Las `fuentes` (join hechos × snapshot maestro × snapshot ERP) son lógica que Python ya tiene.
- El kit de demo es Python; meter SQLite en Node es otro camino a romper a las 10:30 del domingo.

### Lo que no es una opción

- FastAPI / Flask / otra lib. ADR y stack.
- Que el frontend importe `rules/` o recalcule decisiones.
- Dump JSON estático: no sirve para `reprocess` en vivo (minuto 4–8 de la defensa).

**Acción 0:** mensaje a Miguel: “puente de lectura stdlib en `console/`, puerto 8000, Streamlit se queda, Next opcional para la demo. ¿OK el `make console-api` / `make console-web` y el ignore de `.next`?”. Hasta que diga sí, no se toca el Makefile.

---

## 5. Contrato de lectura (ya escrito en el frontend)

Rutas **provisionales** de `console-web/README.md`. El puente debe hablar esto. `file_id` en NFC y `encodeURIComponent` en la URL (tildes: `FA-5590_ofimática.pdf`).

| Método | Ruta | Qué sale | Origen en BD |
|---|---|---|---|
| GET | `/panel` | `PanelResumen` | `ficheros` + `decisiones` vigente + `eventos` + `snapshots` |
| GET | `/ficheros?q&estado&regla&lote&page&pageSize` | `{ items, total, page, pageSize }` | `ficheros` ⋈ `hechos` ⋈ `decisiones` vigente |
| GET | `/ficheros/:file_id` | un `Fichero` **con `fuentes`** | lo anterior + snapshot maestro + snapshot ERP |
| GET | `/traza?file_id&etapa&categoria` | `PasoTraza[]` | `core.db.traza()`: eventos + motivos de la vigente |
| GET | `/etapas` | `EtapasResumen` | `eventos` agrupados por etapa/estado |
| GET | `/eventos?etapa&limit` | `Event[]` | últimas filas de `eventos` |

Respuestas: array o `{ items, total, page, pageSize }`. `mappers.ts` acepta snake_case, camelCase y columnas crudas (`motivos_json`, `hechos_json`, `tiene_texto` 0/1). Preferible emitir **el contrato** (`resultado`, `PAGAR`, `hechos`, `motivos`) y dejar los alias por si acaso.

No hay POST de Approve. El único write que existe hoy es el botón Streamlit → `albertitos reprocess --impacted`. En Next, `/runs/*` ya dice “se lanza con la CLI”. No hace falta endpoint de reproceso para el MVP; si se quiere para la demo, que sea un POST que lance el mismo subprocess y **no** invente un `PAGAR`.

---

## 6. Qué hay que construir (desglose)

### 6.1 Capa de lecturas Python (`src/albertitos/console/lecturas.py`)

Extraer el SQL de `app.py` (Streamlit) a funciones puras que devuelven dicts. Streamlit las llama; el HTTP también. Cero negocio: no se interpretan reglas.

Funciones mínimas:

1. `panel(conn) -> dict` — no reusar `db.resumen()` a pelo: el frontend pide más campos.
2. `listar_ficheros(conn, q, estado, regla, lote, page, page_size) -> dict`
3. `fichero(conn, file_id) -> dict | None` — 404 si no está.
4. `traza_pasos(conn, file_id, etapa, categoria) -> list`
5. `etapas(conn) -> dict`
6. `eventos(conn, etapa, limit) -> list`

Reglas de rendimiento (CLAUDE.md de console): abrir en **< 3 s con 540 ficheros**. No cargar `hechos_json` de todos a la vez. En el listado, hechos/decisión de la página actual (15). En el panel, `COUNT` / `GROUP BY`, no hidratar 500 objetos.

### 6.2 Forma de cada payload (para no iterar con el mapper)

**Panel** (`PanelResumen`):

```json
{
  "ficheros": 500,
  "por_lote": [{"lote": 1, "ficheros": 500}],
  "por_estado": {"PAGAR": 438, "ESCALAR": 53, "NO_PAGAR": 9, "PENDIENTE": 0},
  "distribucion": [{"resultado": "PAGAR", "count": 438, "percent": 87.6}, ...],
  "versiones": {"norma": "v3", "maestro": "<hash>", "erp": "v1", "extractor": "..."},
  "operacion": {
    "ficheros_s": 2.24,
    "coste_eur": 0.54,
    "reintentos": 66,
    "pct_llm": 29.1
  },
  "etapas": [ /* EtapaResumen */ ],
  "por_mes": [{"mes": "2026-01", "ficheros": 40}, ...],
  "recientes": [ /* Fichero, sin fuentes */ ]
}
```

Cuidado con el coste: `ESTADO-BACKEND.md` pide que el panel **no sume el histórico** (los 2,38 € de ayer). Misma regla que `status`. Acordar con Miguel el filtro (¿eventos del último run? ¿desde un `ts`?). `ficheros_s` = nº de ficheros con evento ingest/extract / (max ts − min ts) de ese recorte.

**Fichero en listado:** `file_id`, `sha256`, `lote`, `paginas`, `tiene_texto`, `ingerido_en`, `hechos` (objeto o `hechos_json`), `decision` vigente o ausente → el mapper pone `estado: PENDIENTE`.

**Filtros del listado:**

- `q`: substring de `file_id` / `razon_social` / `num_factura` (esta última está dentro de `hechos_json`: o se filtra en SQL con `json_extract` o se filtra poco y se documenta).
- `estado`: `PAGAR | NO_PAGAR | ESCALAR | PENDIENTE`.
- `regla`: incumplimiento sin versión, `"R2"` — hay que parsear `motivos_json` de la vigente (`ok == false`, `regla_id` termina en `.R2`).
- `lote`: 1 o 2.
- Paginación 1-indexada, `pageSize` default 15.

**Detalle + `fuentes`:** es el endpoint más caro de diseñar, no de ejecutar (un fichero). Streamlit hoy **no** cruza maestro/ERP en el detalle; Next sí lo espera.

```json
"fuentes": {
  "maestro_version": "...",
  "erp_version": "...",
  "proveedor": { "id": "P001", "razon_social": "...", "nif": "...", "iban": "...", "ciudad": null, "condiciones_dias": 30 },
  "pedido": { "pedido": "PO-2026-0096", "proveedor_id": "P001", "nif": "...", "importe_total": 2489.99, "estado": "...", "fecha_pedido": "2026-01-02" },
  "asientos": [{ "asiento_id": "...", "fecha_registro": "...", "proveedor_id": "...", "nif": "...", "pedido": "...", "importe_esperado": 2489.99, "estado": "PENDIENTE" }]
}
```

Cómo armarlo sin negocio:

- Versiones: las de la **decisión vigente** (`maestro_version`, `erp_version`). Si está PENDIENTE, el snapshot más reciente (`db.ultimo_snapshot`).
- Pedido: `hechos.pedido` → `MasterSnapshot.pedidos[pedido]`.
- Proveedor: `pedido.proveedor_id` o `maestro.proveedor_por_nif(hechos.nif_emisor)`.
- Asientos: `ErpSnapshot.por_pedido().get(hechos.pedido, [])`.

Importar `MasterSnapshot` / `ErpSnapshot` desde `core.contracts` está permitido: es leer el contrato, no `rules/` ni `extract/`.

**Traza:** `db.traza(conn, file_id)` ya trae fichero, hechos, decisiones, eventos. El frontend quiere una lista plana de `PasoTraza`:

- un paso `tipo: evento` por fila de `eventos` (orden `ts`);
- un paso `tipo: motivo` por cada `Motivo` de la decisión **vigente** (no las seis históricas a la vez).

Filtro `categoria`: `norma` = solo motivos; `incidencias` = eventos no `ok`; o una `Etapa`.

Petición de Streamlit que también vale aquí: **vigente arriba, historial plegado**. En Next el historial puede vivir en `Linaje.tsx` (versiones de la vigente). No hace falta mandar las decisiones viejas en el GET de fichero.

### 6.3 Servidor HTTP (`src/albertitos/console/api.py`)

- `ThreadingHTTPServer` + handler JSON.
- CORS: `http://localhost:3000` (y `127.0.0.1`).
- 404 → `{ "error": "..." }` (el client lee `error` / `detail` / `message`).
- `file_id` se `unquote` y se `.normalize("NFC")`.
- Lee `ALBERTITOS_DB` (igual que Streamlit). Si no existe el fichero: 503 con el mensaje de `make db && uv run albertitos ingest`.
- Sin auth. Localhost. Defensa sin red.

### 6.4 Makefile y ignore (Miguel)

Pedir, no hacer hasta que acuerde:

```
console-api:   uv run python -m albertitos.console.api
console-web:   cd console-web && pnpm dev
```

`.gitignore` raíz: `console-web/node_modules/` y `console-web/.next/` por si alguien instala desde la raíz. `console-web/.gitignore` ya los tiene.

`package.json` name sigue siendo `alberto-ai` → renombrar a `albertitos-console` (cosmético).

### 6.5 Frontend: cablear, no reescribir

1. `cp console-web/.env.example console-web/.env.local` y poner URL + `USE_MOCK=false`.
2. Probar las 6 llamadas. Si un campo no mapea, se arregla en `mappers.ts`, no en la página.
3. Quitar `@vercel/analytics` del `layout.tsx` antes de la defensa (sale a red; la demo es offline).
4. El visor PDF real, si hay tiempo: `GET /pdf/:file_id` leyendo `data/caja/` (lote 1) o `data/lote2/` (lote 2) y un `<iframe>` en `InvoiceDocument`. **No es P0.**

### 6.6 ADR corto (Alejandro, con el skill `/adr`)

Puntúan ADRs (35 pts). Uno de 20 líneas basta:

- Contexto: Streamlit cubre la defensa; Next es la cara de producto.
- Alternativas: FastAPI (descartada, ADR-0007 + deps), leer SQLite desde Node (descartada, nativo + WAL), stdlib HTTP de sólo lectura (elegida).
- Decisión: CLI escribe; Streamlit y Next leen la misma SQLite; Next opcional; sin red; Node solo si se levanta `console-web`.
- Evidencia: las 6 rutas contra `dist/albertitos.db`, captura de la traza de `F26-2201_transportes.pdf`.

### 6.7 Tests

En `tests/test_console.py` (o `test_console_api.py`):

- `/panel` con una BD de fixture: contadores coherentes, PENDIENTE = ficheros sin vigente.
- `/ficheros?estado=ESCALAR` no devuelve PAGAR.
- `/ficheros/<id>` 404 si no existe; 200 con `fuentes` si el snapshot está.
- `file_id` con tilde en NFC.
- La API no importa `albertitos.rules` ni `albertitos.extract`.

`make check` tiene que seguir verde. El frontend no entra en ruff/pytest.

---

## 7. Orden de trabajo (un paso estable antes del siguiente)

Tiempo realista si el puente es stdlib: **2–4 h** de cableado + **1 h** de prueba contra la BD real. El pulido UX es aparte y no bloquea.

| # | Qué | Hecho cuando | Prioridad |
|---|---|---|---|
| 0 | Acuerdo con Miguel (puente + make + ignore) | Mensaje en el canal / bitácora | ahora |
| 1 | `lecturas.py`: panel + listado + detalle sin fuentes | Streamlit puede seguir igual; tests de SQL | P0 |
| 2 | `api.py` + CORS + las 6 rutas (fuentes vacías al principio) | `curl localhost:8000/panel` contra la BD real | P0 |
| 3 | `fuentes` de verdad (maestro + asientos) | Detalle de `F26-2201_…` muestra NIF/pedido/asiento | P0 defensa |
| 4 | Traza como `PasoTraza[]` (eventos + motivos vigente) | `/audit?file_id=…` y pestaña Traza | P0 defensa · 20:00 |
| 5 | `.env.local` + probar las 4 pantallas de Alfonso en el navegador | Panel / cola / detalle / traza con datos reales | P0 |
| 6 | ADR-00xx + `make console-api` / `console-web` | Miguel mergea | P1 |
| 7 | Filtro coste/ritmo del último run (no histórico) | Cifras citables = `docs/CIFRAS.md` | P1 |
| 8 | Pulido UX (`pulido_ux_consola_…plan.md`) | Copy, chips, badges; se hace contra mock si hace falta | P1, paralelo |
| 9 | Quitar Analytics de Vercel | Defensa sin red | P1 |
| 10 | Servir PDF real | Bonus | P2 |
| 11 | POST reproceso desde Next | No. Se hace en CLI o Streamlit | no |
| 12 | Mejoras Streamlit (vigente arriba, historial plegado) | Plan B de las 20:00 | P1 si Next se retrasa |

Paralelo posible: 8 (pulido) mientras 1–4 (puente). El pulido no toca mock ni API.

---

## 8. Cómo se verifica la unión (cuando toque code)

No basta un screenshot. Flujo de Alfonso, con BD real:

1. Panel: 500/500 (o 540), N escalados, 0 pendientes, versiones norma/maestro/ERP.
2. Cola → filtro ESCALAR → abrir `F26-2201_transportes.pdf` → motivos con `TEXTO_INSTRUCCION` y el fragmento, no un JSON crudo.
3. Misma factura → Traza: ingest → extract → … → reglas → ESCALAR, con latencias.
4. `scan_017.pdf` o el PENDIENTE real si el caos está activo: estado PENDIENTE, sin resultado de norma.
5. Recargar `/` y `/workers` (poll 10 s): no deben romper si la CLI está parada.
6. Apagar el puente: la UI muestra el error de red de `ApiError` (`isNetwork`), no una página en blanco.
7. Streamlit `:8501` sigue abriendo la misma BD.

Si no hay browser tools, `curl` a las 6 rutas + el mock (`USE_MOCK=true`) como control de que las páginas no se rompieron.

---

## 9. Riesgos y repliegue

| Riesgo | Qué pasa | Repliegue |
|---|---|---|
| El puente no está a las 20:00 | Next sigue en mock (cifras de mentira en defensa = malo) | Alfonso enseña Streamlit o `trace` en terminal. Next ni se abre |
| Node no está en el portátil de Alfonso | Next no arranca | Kit + Streamlit. Next es opcional |
| `file_id` con tilde 404 | NFC mal normalizado | El mapper ya hace NFC; el server tiene que hacer lo mismo al buscar |
| Panel lento / 500 `hechos_json` | > 3 s, se ve el loading eterno | Agregados SQL; listado paginado |
| Coste 2,38 € históricos | Tribunal pregunta la cifra de `CIFRAS.md` y no cuadra | Recortar eventos al último run (punto 7) |
| ADR-0007 “descartamos SPA” | Alguien lo lee en la defensa | El ADR nuevo: Next es cara opcional; Streamlit sigue siendo la consola del producto |
| Tocar Makefile sin Miguel | Hook / pelea de ramas | Solo `console-web/` + `console/api.py` hasta que mergee él |

---

## 10. Relación con lo demás

- **`PLAN-ADAPTACION.md`:** fases 1 y 2 hechas. Este documento **es** la fase 3.
- **`pulido_ux_consola_40d7af35.plan.md`:** copy/presentación. No es la unión. Se puede hacer ya contra el mock.
- **`src/albertitos/console/CLAUDE.md`:** sigue mandando para Streamlit (Escalados, Traza, Panel, < 3 s, sin red, sin CDN). El HTTP nuevo vive en el mismo módulo y hereda esas reglas.
- **`docs/ESTADO-BACKEND.md` § Consola:** las dos peticiones (vigente arriba; panel sin histórico) aplican a Streamlit **y** al JSON del panel. No las ignore el puente.
- **Guion:** minuto 0–2 panel + `F26-2201_transportes.pdf`; minuto 4–8 traza de una PAGAR + ritmo/coste + `reprocess`. Eso es el criterio de “fase 3 verde”, no que existan `/profile` ni visor PDF.

---

## 11. Checklist de “fase 3 verde”

- [x] Puente stdlib en `console/` (sin FastAPI, sin tocar `core/`).
- [x] Las 6 rutas responden en tests de fixture (panel, listado, detalle NFC, traza, etapas, 404/405).
- [ ] Miguel ha dicho sí a `make console-api` / `make console-web` y al ignore.
- [ ] `curl :8000/panel` contra `dist/albertitos.db` (hace falta la BD real / el kit).
- [ ] Next con `USE_MOCK=false` pinta esos datos. Mock sigue funcionando si se vuelve el flag a true.
- [x] Streamlit intacto.
- [ ] `make check` verde en esta rama (los tests nuevos pasan; falta el check completo antes del handoff).
- [ ] ADR escrito.
- [ ] Ensayo en el portátil de Alfonso (o en el kit): si Next falla, Streamlit abre en < 3 s.
