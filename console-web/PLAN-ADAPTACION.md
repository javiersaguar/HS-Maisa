# Plan: adaptar la consola e incorporarla a HS-Maisa

Documento de trabajo del frontend. No es un ADR del equipo. No se implementa la API aquí.

Repo destino: [HS-Maisa](https://github.com/javiersaguar/HS-Maisa).  
Contrato que manda: `src/albertitos/core/contracts.py` + `docs/contratos.md`.  
Consola oficial hoy: Streamlit en `src/albertitos/console/` (se queda; esto no la borra).

```
AHORA                          DESPUÉS (juntos)                 MÁS TARDE
adaptar este Next.js     →     copiarlo a HS-Maisa        →     crear API y cablear
al dominio Albertitos          como console-web/               BD / CLI ↔ UI
```

Hasta terminar la fase 1, el mock sigue siendo la fuente de datos. `NEXT_PUBLIC_USE_MOCK=true`.

---

## 1. Objetivo

Dejar este frontend hablando el mismo idioma que el backend, para que:

1. Se pueda copiar a HS-Maisa sin reescribir pantallas.
2. Cuando exista un puente (HTTP o lectura de SQLite), solo cambie `lib/api`.
3. La demo de defensa (panel, escalados, traza) encaje con `PAGAR / NO_PAGAR / ESCALAR`, `file_id` y eventos por etapa.

## 2. Qué no se hace en este plan

- No se clona HS-Maisa ni se hace commit allí todavía.
- No se inventa `GET /invoices` ni `POST /runs`. Ellos no tienen HTTP.
- No se toca `core/`, `pipeline/`, `Makefile` ni Streamlit.
- No se rediseña. Paleta y look se conservan.
- No se invierte en Profile, Create Worker, New Run ni umbral 75%.
- No se escriben decisiones desde la UI. La consola es de sólo lectura.

---

## 3. Contrato congelado (a esto nos adaptamos)

| Concepto | Valor en Albertitos | Dejar de usar |
|---|---|---|
| Producto | Albertitos | Alberto AI |
| Decisión | `PAGAR` \| `NO_PAGAR` \| `ESCALAR` | `PAY` \| `NO_PAY` \| `ESCALATE` |
| Identidad | `file_id` (nombre NFC del PDF) | `Invoice.id` UUID |
| Hechos | `InvoiceFacts` (sin campo de decisión) | `extractedFields` sueltos + `confidence` que decide |
| Motivo | `{ regla_id, ok, detalle, evidencia }` | `reasoningFindings` genéricos |
| Etapas | `ingest extract validate enrich decide emit` | workers `ocr / validation / decision` |
| Estado fichero | con decisión vigente, o `PENDIENTE` | `processing / needs_review` + umbral 75% |
| Fuentes | maestro Excel + ERP 2009 | SAP / NetSuite |
| Traza | `Event` (etapa, estado, intento, latencia, tokens, coste, error) | audit log de “Digital Workers” |
| Quién decide | la norma como código | botón Approve / Reject |

`confianza` existe en `InvoiceFacts` y es un dato de extracción. **No decide.**  
`PENDIENTE` = fichero sin decisión vigente (LLM caído, etc.). Es la demo de resiliencia.

---

## 4. Rutas: las que quedan y las que se congelan

Las URLs de Next se pueden mantener. Cambia el significado, no hace falta un rediseño de routing.

| Ruta actual | En Albertitos | Fase 1 |
|---|---|---|
| `/` | Panel: N ficheros, PAGAR / ESCALAR / NO_PAGAR, pendientes, versiones | Adaptar KPIs y copy |
| `/invoices` | Cola de ficheros. Filtros: resultado, lote, `PENDIENTE` | Adaptar filtros y tabla (`file_id`) |
| `/invoices/[id]` | Detalle por `file_id`: hechos, motivos, maestro/ERP, traza | Adaptar; `id` = `file_id` |
| `/audit` | Chain of Work = eventos + reglas | Adaptar actores a `Etapa` |
| `/workers` y `/workers/[id]` | Estado de etapas del pipeline, no catálogo de productos | Bajar intensidad; no Create Worker |
| `/runs/new`, `/runs/[id]` | El run es `albertitos run` (CLI) | Quitar del sidebar y CTAs. No borrar carpetas aún |
| `/profile` | No existe en el backend | Quitar del sidebar |

Sidebar objetivo: **Panel · Ficheros · Etapas · Traza**.

---

## 5. Fases

### Fase 1 — Adaptar este repo (ahora, con mock)

Trabajo local en `dashboard-design-implementation2`. Al terminar, la UI ya es Albertitos y sigue funcionando offline.

#### 1.1 Tipos y config

- Reescribir `lib/types.ts` al contrato: `Resultado`, `Etapa`, `EstadoEvento`, `InvoiceFacts`, `Motivo`, `Decision`, `Event`, `Fichero`.
- `lib/config.ts`: quitar `AUTO_APPROVE_THRESHOLD` y `ERP_LABELS` SAP/NetSuite. Marca = Albertitos. ERP = 2009.
- `lib/format.ts`: etiquetas `PAGAR / NO_PAGAR / ESCALAR`, money/fechas ya sirven.
- `lib/api/mappers.ts`: aceptar `resultado` / `PAGAR` / `file_id` / `motivos` / `hechos`. Seguir aceptando los nombres viejos un tiempo para no romper el mock a medias.

#### 1.2 Mock Albertitos

- `lib/mock/data.ts` y `lib/mock/store.ts`: `file_id` tipo `F26-2201_transportes.pdf`, motivos con `regla_id`, avisos (`TEXTO_INSTRUCCION`, …), etapas, un `PENDIENTE`.
- Quitar la rama que convierte confidence &lt; 75 en `ESCALATE`.
- Review humano en mock: no reescribe el resultado de la norma (la UI no decide).

#### 1.3 UI que se adapta (look igual)

| Fichero | Qué cambiar |
|---|---|
| `components/layout/Sidebar.tsx` | Albertitos; quitar Profile; CTAs de New Run fuera |
| `app/layout.tsx` | título Albertitos |
| `components/invoices/badges.tsx` | `PAGAR / NO_PAGAR / ESCALAR` |
| `components/invoices/FilterBar.tsx` | mismos valores; filtro lote si cabe en el mock |
| `components/invoices/InvoiceTable.tsx` | columna `file_id` |
| `components/invoices/ExtractedFields.tsx` | campos de `InvoiceFacts` |
| `components/invoices/ErpMatchPanel.tsx` | pedido + asiento ERP 2009, no SAP |
| `components/invoices/ReviewActions.tsx` | ocultar o desactivar Approve/Reject. Texto: sólo lectura |
| `app/invoices/page.tsx` | copy + filtros; sin New Run |
| `app/invoices/[id]/page.tsx` | param = `file_id`; hechos + motivos + traza |
| `components/dashboard/*` | distribución PAGAR/…; “pendientes” = sin decisión |
| `app/page.tsx` | Panel, no “+ New Run” |
| `components/audit/ChainOfWork.tsx` | un step = Event o Motivo |
| `app/audit/page.tsx` | filtros AI/Human/System → etapa / sistema / norma |
| `app/workers/page.tsx` | 6 etapas, no 3 Digital Workers |
| `components/workers/*` | copy de etapas |

#### 1.4 UI que se congela (no borrar aún)

`app/profile/`, `app/runs/`, `components/runs/`, `hooks/useRun.ts`, `hooks/useAccount.ts`, `lib/api/runs.ts`, `lib/api/account.ts`.

Fuera del sidebar y de los CTAs. Si alguien entra por URL, página mínima “el pipeline se lanza con `albertitos run`”.

#### 1.5 Docs de este repo

- `README.md`: Albertitos, cómo levantar el mock, apuntar a este plan.
- `CLAUDE.md`: el dominio lo marca HS-Maisa, no el brief viejo de 75% / 3 workers.
- `project-context.md`: no reescribirlo entero. Gana el contrato de Albertitos en lo de producto; el look se conserva.

**Hecho fase 1:** mock en marcha, cero `PAY`/`SAP`/`75%` en UI, detalle abre por `file_id`, traza enseña etapas/motivos.

---

### Fase 2 — Incorporar al repo (cuando la fase 1 esté verde)

Copiar, no fusionar lógica. Streamlit no se toca.

```
HS-Maisa/
  src/albertitos/console/     ← Streamlit (Alejandro, fallback defensa)
  console-web/                ← este Next.js ya adaptado
```

1. Clone + rama `alejandro/console-web` (regla `<nombre>/<tema>`).
2. Copiar **solo fuente** a `console-web/`:

   Sí: `app/`, `components/`, `hooks/`, `lib/`, `public/`, `package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`, configs, `.env.example`, `README.md`, `PLAN-ADAPTACION.md`.

   No: `node_modules/`, `.next/`, `.env.local`, `debug.log`, `tsconfig.tsbuildinfo`, el `CLAUDE.md` de este repo (chocaría con el de ellos).

3. En `console-web/package.json` el name puede ser `albertitos-console`.
4. Pedir a Miguel (dueño del Makefile / `.gitignore`): ignorar `console-web/node_modules`, `console-web/.next`, y si acuerda, `make console-web` → `cd console-web && pnpm dev`.
5. ADR corto (ellos puntúan ADRs): “consola web Next.js para la demo; Streamlit se queda; sin red en la defensa; Node solo para quien levante `console-web`”.
6. No tocar nada fuera de `console-web/` salvo el ignore / make que pida Miguel.

**Hecho fase 2:** `cd console-web && pnpm install && pnpm dev` pinta el mock dentro del clone. `make check` del Python sigue verde.

---

### Fase 3 — API y juntar (fuera de este plan, cuando estemos juntos)

El backend aún no está cerrado. Esta fase se abre entonces. Boceto para no diseñarlo mal ahora:

1. Ellos exponen lectura (preferible): HTTP mínimo sobre la BD, o nosotros leemos `dist/albertitos.db` en rutas `app/api` de Next. Decisión de equipo.
2. Un solo sitio de mapeo: `console-web/lib/api` + `mappers.ts`. Tablas: `ficheros`, `hechos`, `decisiones`, `eventos`, `snapshots`.
3. `GET` de panel / ficheros / detalle / traza. Escritura, si hay: solo `reprocess --impacted` (subprocess o endpoint de Miguel). Nada de Approve que invente un `PAGAR`.
4. `NEXT_PUBLIC_USE_MOCK=false` + URL o path de BD. Las páginas no se reescriben.
5. Streamlit sigue como plan B en el portátil de Alfonso (`make console`).

No implementar fase 3 hasta tener BD con decisiones reales o un contrato HTTP escrito por Miguel.

---

## 6. Orden de implementación de la fase 1

Un paso estable antes del siguiente. Extraer, no rediseñar.

1. Tipos + config + format + mappers.
2. Mock (data + store) al nuevo contrato. La app puede romper un rato.
3. Badges, filtros, tabla, detalle (hechos / motivos / ERP).
4. Dashboard / panel y Chain of Work.
5. Sidebar + quitar CTAs + congelar runs/profile.
6. Workers → etapas.
7. README / CLAUDE.md de este repo.
8. Probar a mano: panel, cola, un `ESCALAR` con evidencia, un `PENDIENTE`, traza.

---

## 7. Criterio para pasar de fase

| De → a | Condición |
|---|---|
| 1 → 2 | Mock Albertitos usable. Tipos = contrato. Sidebar sin Profile/New Run. |
| 2 → 3 | El Next está en `console-web/` de HS-Maisa, mock en verde, Python `make check` verde, ADR/aviso a Miguel. |
| 3 | Hay BD o endpoint real. Entonces sí: API y cableado. |

---

## 8. Defensa (para no adaptar de más)

Lo que Alfonso enseña con la consola, y por tanto lo que la fase 1 debe dejar visible:

- Panel: 500/500, N escalados, 0 pendientes.
- Cola: abrir un PDF que ordena escalar; nosotros escalamos por la norma + fragmento (`TEXTO_INSTRUCCION`).
- Traza: hechos → maestro → asiento ERP → reglas con evidencia → resultado.
- Bonus: coste, ficheros/s, reintentos ORA-00600, circuit breaker — mockear el hueco, no inventar cifra de producción.

Si una pantalla no ayuda a eso (Profile, New Run, Create Worker), no se trabaja.
