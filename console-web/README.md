# Albertitos — consola web

Consola de sólo lectura para el pipeline de cuentas a pagar de Albertitos: ficheros, decisiones de la norma
(`PAGAR | NO_PAGAR | ESCALAR`), `PENDIENTE` cuando no hay decisión vigente, y la traza de cada fichero.

El dominio lo fija [HS-Maisa](https://github.com/javiersaguar/HS-Maisa): `src/albertitos/core/contracts.py` + `docs/contratos.md`.
Cómo llega este repo a HS-Maisa como `console-web/`: `PLAN-ADAPTACION.md`. Esta es la consola de producto; el backend de
lectura es el puente HTTP de `src/albertitos/console/` (su `CLAUDE.md` es el contrato). Streamlit fue el andamiaje del viernes.

## Levantar el mock

```bash
pnpm install
cp .env.example .env.local
pnpm dev
```

Con `NEXT_PUBLIC_USE_MOCK=true` (por defecto) todo funciona sin red contra `lib/mock`: 500 ficheros de la Caja + 10 del lote 2,
con las trampas reales de `docs/trampas.md` (p. ej. `F26-2201_transportes.pdf`, `FA-5590_ofimática.pdf`, `2026-06-04_P006.pdf`)
y un `PENDIENTE` (`scan_017.pdf`, LLM caído). Las decisiones del mock salen de `lib/mock/norma.ts`, copia de `rules/norma_v3.py`;
la UI nunca la importa.

## Pantallas

| Ruta | Qué es |
|---|---|
| `/` | Panel: ficheros por lote, decisiones vigentes por resultado, pendientes, versiones, ficheros/s, coste, reintentos |
| `/invoices` | Cola de ficheros. Filtros: resultado, regla incumplida, lote. CSV con las columnas de `outcomes.jsonl` |
| `/invoices/detalle?file=<file_id>` (alias `/invoices/[id]`) | Hechos, reglas con evidencia, maestro + asiento ERP 2009, traza |
| `/workers`, `/workers/[etapa]` | Las 6 etapas (`ingest extract validate enrich decide emit`) a partir de `eventos` |
| `/audit` | Traza global: eventos por etapa y reglas de la norma |

`/runs/*` y `/profile` sólo muestran que eso se hace por CLI. Su código está en `congelado/`, fuera de la compilación.

## Conectar el backend

El puente vive en `src/albertitos/console/api.py` (stdlib, sólo lectura, sin FastAPI):

```
uv run python -m albertitos.console.api   # http://127.0.0.1:8000  (sin dist/albertitos.db sólo responde /salud)
```

En `console-web/.env.local`:

```
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_USE_MOCK=false
```

Hacen falta las dos; sin URL la app se queda en el mock. Ninguna página cambia. La barra lateral dice siempre de dónde
salen los datos (*Datos de ejemplo* · *Caja de Alberto · N facturas* · *Aún no hay Caja* · *Sin conexión*): en la defensa no se
confunde el mock con la Caja.

- `lib/api/*.ts`: una función por lectura. Único código que conoce rutas.
- `lib/api/mappers.ts`: payload → `lib/types.ts`. Acepta el contrato (snake_case), filas crudas de la SQLite (`motivos_json`, `hechos_json`, `tiene_texto` 0/1) y los nombres del prototipo viejo (`PAY`, `decision`, `id`). Si el puente cambia un nombre, se toca aquí y ninguna página.
- `lib/api/client.ts`: `fetch` + `ApiError` (red / 401-403 / 404 / 503 sin BD / resto). Comprueba la cabecera `X-Albertitos-Api` contra `API_CONTRACT_VERSION` (`lib/config.ts`) y avisa en consola si el backend habla otra versión.

Contrato (versión 1; detalle en `src/albertitos/console/CLAUDE.md`):

| Método | Ruta | Devuelve |
|---|---|---|
| GET | `/salud` | `{ ok, api, bd | null }` — responde aunque no haya BD |
| GET | `/panel` | `PanelResumen` (versiones con `normas[]`, operación con `ventana` y `coste_eur_historico`) |
| GET | `/ficheros?q&estado&regla&lote&page&pageSize` | `{ api, items, total, page, page_size }` |
| GET | `/ficheros/:file_id` | `Fichero` + `fuentes` (proveedor, pedido y asientos del snapshot) |
| GET | `/traza?file_id&etapa&categoria` | `PasoTraza[]`: eventos + motivos de la decisión vigente |
| GET | `/etapas` | `eventos` agrupados por etapa y estado |
| GET | `/eventos?etapa&limit` | últimas filas de `eventos` |

`file_id` va en NFC y codificado en la URL. No hay escrituras: la consola no aprueba ni rechaza. Recalcular es
`albertitos reprocess --impacted`.

## Estructura

```
app/                 rutas (/, /invoices, /invoices/detalle?file=, /invoices/[id] → alias, /workers, /workers/[id], /audit; /runs y /profile mínimas)
components/audit     ChainOfWork (fichero, etapa y /audit), TraceFilter
components/invoices  tabla, filtros, documento, hechos, maestro/ERP, linaje
components/dashboard components/workers components/layout components/ui
hooks/               usePanel, useFicheros, useEtapas, useTraza, useSalud (todos sobre useAsync)
lib/                 types (contrato), config, format, theme, api/, mock/
congelado/           código del prototipo que el plan congela (no compila, no se copia a HS-Maisa)
```
