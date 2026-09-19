---
name: Fix invoice detail
overview: El detalle no carga en varios ficheros porque el `file_id` (tildes + `.pdf`) va en un segmento dinámico de Next y se codifica dos veces; además algunos `scan_*` sí abren pero se ven vacíos porque están PENDIENTE sin hechos.
todos:
  - id: routes-query
    content: Cambiar ficheroHref a /invoices/detalle?file= (NFC + encodeURIComponent sólo en query) y mover la página de detalle
    status: pending
  - id: alias-id
    content: Dejar app/invoices/[id] como redirect al query para URLs ASCII del guion
    status: pending
  - id: empty-pending
    content: Dejar claro el estado PENDIENTE y mostrar eventos de traza aunque no haya hechos/decisión
    status: pending
  - id: api-exceptions
    content: Capturar Exception en console api.py do_GET para no romper la respuesta HTTP
    status: pending
  - id: verify-browser
    content: Verificar en el navegador ofimática, mensajería, F26-2201 y un scan PENDIENTE
    status: pending
isProject: false
---

# Arreglar el detalle de factura que no carga

## Qué está pasando

Hay **dos fallos distintos** que se sienten igual (“pincho y no veo el detalle de lo que ha hecho”).

### 1. Las facturas con tilde no llegan a renderizar (el más grave)

El enlace se construye así:

```10:10:console-web/components/invoices/InvoiceTable.tsx
export const ficheroHref = (fileId: string) => `/invoices/${encodeURIComponent(fileId)}`
```

Eso alimenta `router.push` / `<Link>` hacia [`app/invoices/[id]/page.tsx`](console-web/app/invoices/[id]/page.tsx).

- En la Caja hay **decenas** de `file_id` con tilde: `FA-5590_ofimática.pdf`, `F26-3355_mensajería.pdf`, `*_informática.pdf`, etc. `FA-5590_ofimática.pdf` es fichero de demo.
- `encodeURIComponent` convierte `á` en `%C3%A1`. Next App Router **vuelve a codificar** el path (`%` → `%25`). `useParams` + un solo `decodeURIComponent` se queda a medias (`ofim%C3%A1tica`) y el puente busca un nombre que no existe → 404 / pantalla de error.
- Next en `next dev` local tiene un bug abierto con slugs no-ASCII ([next.js#73965](https://github.com/vercel/next.js/issues/73965)): `router.push` / `Link` pueden ir a **404** sin montar la página.
- Los logs del `pnpm dev` actual lo confirman: solo hay `200` en nombres ASCII (`scan_017.pdf`, `factura_4619.pdf`, `F26-2201_…` no aparece ni una `ofimática`/`mensajería`). El `.pdf` **no** es el problema en Next 16.3.3: los `scan_*.pdf` sí entran.

```mermaid
flowchart LR
  click["Click en la tabla"] --> href["/invoices/FA-5590_ofim%C3%A1tica.pdf"]
  href --> nextEnc["Next recodifica % a %25"]
  nextEnc --> miss["404 o id mal decodificado"]
  miss --> api["GET /ficheros/FA-5590_ofim%C3%A1tica.pdf"]
  api --> notfound["Puente 404"]
```

### 2. Varios `scan_*` sí abren, pero el detalle parece vacío

Esos mismos logs muestran `GET /invoices/scan_0xx.pdf 200`. La ruta monta. Muchos `scan_*` son **PENDIENTE** (sin capa de texto / LLM visión): sin `hechos` ni decisión vigente. La UI enseña “Extracción pendiente” / “sin decisión vigente” y la Chain of Work está en otra pestaña. Se lee como “no ha cargado”.

## Qué no tocar

- `core/` (congelado), `data/caja/`, `dist/**/*.jsonl`.
- El contrato del puente: `file_id` NFC, `encodeURIComponent` **solo en la petición HTTP a `:8000`**, no en la ruta de Next.

## Arreglo

**Navegación por query, path ASCII.** Así Next no ve tildes ni `%` en el segmento dinámico.

1. Extraer `ficheroHref` a [`console-web/lib/routes.ts`](console-web/lib/routes.ts):

```ts
export const ficheroHref = (fileId: string) =>
  `/invoices/detalle?file=${encodeURIComponent(fileId.normalize('NFC'))}`
```

2. Mover el detalle de [`app/invoices/[id]/page.tsx`](console-web/app/invoices/[id]/page.tsx) a `app/invoices/detalle/page.tsx`. Leer el id con `useSearchParams().get('file')` (ya viene decodificado) y NFC. Quitar el `decodeURIComponent` extra.

3. Dejar `[id]/page.tsx` como **alias** que redirige a `detalle?file=…` para que sigan valiendo los enlaces ASCII del guion (`/invoices/F26-2201_transportes.pdf`, `/invoices/scan_017.pdf`).

4. Actualizar usos de `ficheroHref`: tabla, [`RecentDecisions`](console-web/components/dashboard/RecentDecisions.tsx), [`EventosTable`](console-web/components/workers/EventosTable.tsx), [`ChainOfWork`](console-web/components/audit/ChainOfWork.tsx).

5. Vacío honesto: si no hay `hechos`/`decisión`, el tab Decisión debe decir que el fichero está PENDIENTE y enseñar ya los eventos de traza (ingest/extract), no un documento en blanco que parece un fallo de carga.

6. En [`api.py`](src/albertitos/console/api.py) `do_GET`: capturar `Exception` (hoy solo `sqlite3.Error`). Un JSON raro hoy deja `status` sin asignar y una respuesta HTTP rota → la UI se queda colgada.

## Comprobar en el navegador (dev ya corre)

- ASCII: `scan_017.pdf`, `F26-2201_transportes.pdf` (desde la tabla y pegando la URL vieja).
- Tilde: `FA-5590_ofimática.pdf`, `F26-3355_mensajería.pdf` — debe verse decisión + traza.
- PENDIENTE real: un `scan_*` sin hechos — mensaje claro + eventos, no pantalla en blanco.
