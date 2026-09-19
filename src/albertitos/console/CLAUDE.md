# console/ — la consola: puente HTTP de sólo lectura + `console-web/` (Next) · dueño: Alejandro (Cursor)

La consola de producto es **Next** (`console-web/`) hablando con el **puente HTTP** de este módulo.
`lecturas.py` es el único sitio Python que conoce tablas y JSON de snapshots; `api.py` lo sirve en `:8000`
con la stdlib (cero dependencias nuevas, ADR-0007 sigue en pie). Lee `dist/albertitos.db` en modo `ro`;
**no importa `rules/` ni `extract/`**, no recalcula nada. Sólo la CLI escribe (también la de la bandeja, abajo).

`app.py` (Streamlit) es el andamiaje del viernes: no se mantiene ni sirve de especificación. El repliegue de
las 20:00 es `albertitos trace` en terminal.

## Arranque
```
make db && uv run albertitos ingest      # datos mínimos (ficheros + eventos)
uv run python -m albertitos.console.api  # http://127.0.0.1:8000  (sin BD sólo contesta /salud)
uv run python -m albertitos.console.api --bandeja   # demo: dist/bandeja.db + botón «Añadir facturas»
cd console-web && pnpm dev               # http://localhost:3000
```
`console-web/.env.local`: `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000` y `NEXT_PUBLIC_USE_MOCK=false` (hacen falta las dos).
La barra lateral dice siempre de dónde salen los datos: *Datos de ejemplo* (mock) · *Caja de Alberto · N facturas* · *Aún no hay Caja* · *Sin conexión*.

BD realista sin LLM (así se probó el puente el sábado; la BD queda en `dist/`, gitignored):
```
albertitos db init && albertitos ingest && albertitos hechos import data/fixtures/hechos_caja.jsonl
albertitos maestro && albertitos erp pull --tag v1 && albertitos decide     # con `make erp-fast` abierto
```

## Contrato JSON (`lecturas.API_VERSION = 1`)
snake_case, copia `core/contracts.py` (`Decimal` como string, fechas ISO). Cada respuesta lleva la cabecera
`X-Albertitos-Api: 1`; los objetos de colección también el campo `api`. El frontend avisa en consola si no coincide
(`lib/config.ts: API_CONTRACT_VERSION`). Se sube la versión si cambia un nombre o un tipo que Next ya lee;
añadir campos no la sube (`mappers.ts` ignora lo que no conoce).

| GET | Devuelve | Origen |
|---|---|---|
| `/salud` | `{ ok, api, bd: { ficheros, decisiones_vigentes, pendientes, ultimo_evento_en, identidades, versiones } \| null }` | responde **sin BD** |
| `/panel` | `PanelResumen`: `ficheros, por_lote, por_estado, distribucion, versiones{norma, normas[], maestro, erp, extractor}, operacion{ficheros_s, ventana, coste_eur, coste_eur_historico, reintentos, pct_llm}, etapas[], por_mes[], recientes[]` | agregados SQL |
| `/ficheros?q&estado&regla&lote&page&pageSize` | `{ api, items: Fichero[], total, page, page_size }` (`pageSize` ≤ 1000: la exportación CSV pide todos) | `ficheros ⋈ hechos_ultimos ⋈ decisiones vigente` |
| `/ficheros/:file_id` | `Fichero` con `fuentes{maestro_version, erp_version, proveedor, pedido, asientos[]}` | + snapshots; sin snapshot → nulos y `[]`, nunca 500 |
| `/traza?file_id&etapa&categoria` | `PasoTraza[]`: un `evento` por fila y, tras `decide`, un `motivo` por regla de la **vigente** | `db.traza()` |
| `/etapas` | `{ api, ficheros, etapas: EtapaResumen[], recientes: Event[] }` | `eventos` por etapa/estado |
| `/eventos?etapa&limit` | `Event[]` | últimas filas |
| `/inbox` | `{ estado: idle\|ingiriendo\|extrayendo\|decidiendo\|listo\|error, file_ids, subidos[], ficheros[{file_id, nombre, estado}], log[], error, lote: 99, disponible, bd }` | memoria del puente + `lecturas.estados` |

**Rutas del bonus, registradas, no escritas aquí.** `api.py` hace `RUTAS.update(bonus.rutas())` y
`RUTAS.update(confianza.rutas())` en un import perezoso: si falta el módulo, el puente arranca igual y la consola
oculta esa parte. Contratos: `docs/api/bonus.md` y `docs/api/confianza.md` (no se duplican aquí). No suben `API_VERSION`.

| GET | Para qué en Next |
|---|---|
| `/bonus/{resumen,calendario,proveedores,remesa,avisos,tesoreria}` | `/pagos` (`components/pagos/`): cabecera, calendario semanal, programa con `?tope=`, proveedores, lista y avisos |
| `/confianza/resumen` | sondeo único al cargar: 200 enseña la confianza; 404 o red la ocultan |
| `/confianza/ficheros?limite=1000` · `/confianza/fichero?file_id=` | columna de la lista de ficheros · tarjeta «¿Cuánto nos fiamos?» del detalle |

El chat (K2) no pasa por aquí: proceso aparte en `:8001` (`NEXT_PUBLIC_CHAT_URL`), panel flotante sólo si `/chat/salud`
responde. Su CORS admite sólo `http://localhost:3000`: abre la consola por `localhost`. Decisión: ADR-0016.

**La bandeja (`bandeja.py`), el único POST.** `POST /inbox` multipart (≤ 20 PDF, 10 MB cada uno) → guarda en
`<carpeta de la BD>/inbox/`, `ingest --lote 99` síncrono y **202** `{ file_ids, lote: 99 }`; en un hilo
`extract --fixture` + `decide --fixture` (CLI por subproceso, nunca `reprocess`). 400 sin PDF, 409 si hay un trabajo
en curso o si el puente no se arrancó con `--bandeja`, 403 si el `Origin` no es la consola (`localhost:3000`).
**Sólo con `--bandeja`**, un flag que llega a `hacer_handler` y no se deduce de la ruta. Sirve `dist/bandeja.db`, una
copia de la real si no existe; bórrala para empezar de cero. Nunca abre la bandeja sobre `dist/albertitos.db`, porque un fichero de lote 99 allí deja la auditoría en ROJO
(`comprobar_fantasmas`, package se niega) y el siguiente `run` lo mete en `marcar_duplicados`. Una copia exacta de un
PDF de la Caja entra en `identidades` y hereda su decisión sin LLM (no se vuelve a extraer). Cada subida se sigue
por su sha256 hasta el `file_id` que le dio ingest, nunca por el nombre. Si el nombre ya era de la Caja y el
contenido es otro, ingest lo guarda como `./<nombre>` (P0-5), y el panel enseña su decisión, no la del original. El
mismo nombre subido otra vez con otro contenido da 400 y pide renombrarlo. `bandeja.cli` pasa
`ALBERTITOS_DIR_BANDEJA` para que extract encuentre los PDF (lote 99 en `extract.etapa.DIRECTORIOS`). Añadir la ruta no sube `API_VERSION`.

Reglas del contrato:
- `file_id` en NFC, `encodeURIComponent` en la URL; el servidor `unquote` + NFC. Un `estado` sin decisión vigente es `PENDIENTE`.
- `regla=R6` filtra por `regla_id LIKE '%.R6'`: vale para `v3.R6` y `v4.R6`. `norma` nunca es un literal: sale de la vigente más reciente; `normas` reparte cuando conviven versiones.
- **`identidades(file_id, sha256, lote)`** (P0-1 de Miguel) se **detecta** con `_tabla_existe`, no se exige: si existe, un segundo nombre del mismo PDF responde 200 en detalle y traza sin pisar el original. El listado enseña una fila por sha256.
- **Coste del panel**: `coste_eur` es el de la extracción **vigente** (por fichero, los eventos `extract` desde su último intento 1); `coste_eur_historico` suma todo. Así el panel no enseña los 2,38 € del viernes como coste de las decisiones de hoy (petición de `ESTADO-BACKEND.md`). Límite conocido: sin un marcador de run, dos runs seguidos que reextraen el mismo fichero cuentan sólo el último.
- **Ritmo**: `ventana` es la última ráfaga de `ingest/extract` (huecos > 60 s separan pasadas); `ficheros_s = ventana.ficheros / ventana.segundos`. No es 500 / (sábado − viernes).
- Sin BD: 503 con el comando que la crea; `/salud` 200 con `bd: null`. Errores siempre `{ "error": "..." }`.

## Medido contra `dist/albertitos.db` (500 ficheros, 438/53/9, sáb 19 11:00)
`/panel` 56 ms · `/ficheros?estado=ESCALAR` 37 ms · detalle 28 ms · NFC y NFD de `FA-5590_ofimática.pdf` 200 · `/traza` 25 ms ·
`/ficheros?pageSize=600` (exportación) 678 ms / 1,2 MB. `F26-2201_transportes.pdf`: ESCALAR por `v3.R6` con el fragmento
`TEXTO_INSTRUCCION`, `fuentes` con P002 / PO-2026-0809 / AS-70023.

## Reglas del módulo
- Todo dato viene de la BD. Si falta un dato, pídele a Miguel una columna/evento; no lo calcules aquí.
- < 3 s con 540 ficheros: agregados SQL en el panel, listado paginado, `hechos_json` sólo de la página.
- Sin red: la demo corre en el portátil de Alfonso. Nada de CDN ni componentes externos (Analytics de Vercel fuera).
- Tests en `tests/test_console.py` (`api.despachar(...)` sobre una BD de fixture; no levanta el servidor). Un test AST vigila que console/ no importe `rules/` ni `extract/`.
- Cursor no ejecuta los hooks: antes de commitear, `make check` a mano y no toques nada fuera de `console/` y `console-web/` sin avisar.
- `make console` arranca puente + Next (Ctrl-C para los dos); `pnpm install` en `console-web/` antes, con red.
