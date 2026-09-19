# Albertitos — consola web

Consola de sólo lectura para el pipeline de cuentas a pagar de Albertitos: ficheros, decisiones de la norma
(`PAGAR | NO_PAGAR | ESCALAR`), `PENDIENTE` cuando no hay decisión vigente, y la traza de cada fichero.

El dominio lo fija [HS-Maisa](https://github.com/javiersaguar/HS-Maisa): `src/albertitos/core/contracts.py` + `docs/contratos.md`.
Cómo llega este repo a HS-Maisa como `console-web/`: `PLAN-ADAPTACION.md`. La consola oficial sigue siendo Streamlit (`src/albertitos/console/`).

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
| `/invoices/[file_id]` | Hechos, reglas con evidencia, maestro + asiento ERP 2009, traza |
| `/workers`, `/workers/[etapa]` | Las 6 etapas (`ingest extract validate enrich decide emit`) a partir de `eventos` |
| `/audit` | Traza global: eventos por etapa y reglas de la norma |

`/runs/*` y `/profile` sólo muestran que eso se hace por CLI. Su código está en `congelado/`, fuera de la compilación.

## Conectar el backend (fase 3)

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCK=false
```

Hacen falta las dos; sin URL la app se queda en el mock. Ninguna página cambia.

- `lib/api/*.ts`: una función por lectura. Único código que conoce rutas.
- `lib/api/mappers.ts`: payload → `lib/types.ts`. Acepta el contrato, filas crudas de la SQLite (`motivos_json`, `hechos_json`, `tiene_texto` 0/1) y los nombres del prototipo viejo (`PAY`, `decision`, `id`).
- `lib/api/client.ts`: `fetch` + `ApiError` (red / 401-403 / 404 / resto).

Rutas **provisionales**: el backend no tiene HTTP todavía. Se decidirán en la fase 3 (HTTP de Miguel o rutas `app/api` que lean `dist/albertitos.db`).

| Método | Ruta | Equivale a |
|---|---|---|
| GET | `/panel` | vista Panel de Streamlit |
| GET | `/ficheros?q&estado&regla&lote&page&pageSize` | `ficheros` ⋈ `hechos` ⋈ `decisiones` (vigente) |
| GET | `/ficheros/:file_id` | lo anterior + `fuentes` (proveedor, pedido y asientos del snapshot) |
| GET | `/traza?file_id&etapa&categoria` | `core.db.traza()`: eventos + motivos |
| GET | `/etapas` | `eventos` agrupados por etapa y estado |
| GET | `/eventos?etapa&limit` | últimas filas de `eventos` |

`file_id` va en NFC y codificado en la URL. Respuestas: array o `{ items, total, page, pageSize }`.
No hay escrituras: la consola no aprueba ni rechaza. Recalcular es `albertitos reprocess --impacted`.

## Estructura

```
app/                 rutas (/, /invoices, /invoices/[id], /workers, /workers/[id], /audit; /runs y /profile mínimas)
components/audit     ChainOfWork (fichero, etapa y /audit), TraceFilter
components/invoices  tabla, filtros, documento, hechos, maestro/ERP, linaje
components/dashboard components/workers components/layout components/ui
hooks/               usePanel, useFicheros, useEtapas, useTraza (todos sobre useAsync)
lib/                 types (contrato), config, format, theme, api/, mock/
congelado/           código del prototipo que el plan congela (no compila, no se copia a HS-Maisa)
```
