> **Aviso (19/09/2026).** Este brief es del prototipo "Alberto AI". En producto lo sustituye el contrato de Albertitos
> (HS-Maisa: `core/contracts.py`, `docs/contratos.md`) y `PLAN-ADAPTACION.md`: decisiones `PAGAR | NO_PAGAR | ESCALAR`,
> sin umbral de confianza, 6 etapas en vez de 3 workers, consola de sólo lectura y copy en español. Sigue valiendo para el
> look (§3 design system) y la arquitectura del frontend (§5, reglas de implementación).

# Alberto AI — Project Brief

**Documento de referencia para Claude Code.**  
Leer este archivo completo antes de tocar código. No inventar features. No clonar Maisa Studio. Preparar el frontend para conectar con el backend del equipo.

| Campo | Valor |
|---|---|
| Producto | Alberto AI |
| Tipo | Consola de operaciones para Digital Workers de facturas |
| Hackathon sponsor | [Maisa](https://maisa.ai/) |
| Stack frontend | Next.js 16, React 19, Tailwind 4, Recharts, shadcn/base-ui |
| Estado actual | Prototipo visual con datos mock, todo en `app/page.tsx` |
| Objetivo inmediato | Limpiar arquitectura, alinear producto, dejar el frontend listo para API |

---

## 1. Qué es este producto

Alberto AI es una plataforma enterprise para que equipos de finanzas automaticen el ciclo **Procure to Pay** con Digital Workers:

1. Reciben facturas PDF.
2. Extraen datos.
3. Validan contra ERP y proveedor.
4. Recomiendan pagar, no pagar o escalar.
5. Dejan una traza auditable de cada paso.

El usuario no es un developer. Es finance, operations o un admin de ERP. La interfaz debe sentirse como un SaaS premium, no como un panel de admin genérico.

### Flujo de negocio

```
Invoice PDF
    → Perception / OCR Worker
    → Validation Worker (ERP + supplier + rules)
    → Decision Worker (PAY | NO_PAY | ESCALATE)
    → Human review si hace falta
    → ERP / payment
```

Cada factura es un **caso**. Cada caso produce una **Chain of Work**: pasos, herramientas, datos, validaciones y evidencia.

### Decisiones de producto ya tomadas

- Vertical: **facturas / P2P**. No ampliar a loans, KYC, claims ni otros casos de Maisa.
- Tres workers fijos del pipeline: **OCR**, **Validation**, **Decision**.
- Decisiones: `PAY`, `NO_PAY`, `ESCALATE`.
- Umbral de auto-aprobación: **75%** de confidence. Por debajo → review humana.
- Usuarios: finance teams, operations managers, ERP admins.
- Idioma de UI: inglés (el prototipo ya está en inglés). No traducir pantallas.

---

## 2. Qué es Maisa de verdad (y qué copiamos)

Maisa no es un chatbot ni un RPA clásico. Es una plataforma de **Agentic Process Automation** para industrias reguladas.

Fuentes oficiales usadas para este brief:

- [maisa.ai](https://maisa.ai/)
- [Maisa Studio / Product](https://maisa.ai/product)
- [Digital Workers](https://maisa.ai/digital-workers/)
- [Chain of Work](https://maisa.ai/chain-of-work/)
- [How Digital Workers actually work](https://maisa.ai/agentic-insights/how-maisa-digital-workers-actually-work/)
- [O2C & P2P Automation](https://maisa.ai/insurance/o2c-p2p/)
- [HALP](https://maisa.ai/agentic-insights/halp/)

### Conceptos de Maisa que importan

| Concepto Maisa | Qué significa | Relevancia para Alberto AI |
|---|---|---|
| **Digital Worker** | Empleado digital que ejecuta un proceso entero, no un copilot que sugiere | Nuestro objeto principal. Evitar llamarlos solo "AI agents" en copy de producto |
| **Maisa Studio** | Builder no-code en lenguaje natural para onboardear workers | **Fuera de alcance.** Nosotros somos la consola de operaciones, no el builder |
| **KPU** | Runtime que genera y ejecuta código por caso, hallucination-resistant | Mencionar en copy/audit si el backend lo expone. No construir un KPU |
| **Chain of Work** | Traza reproducible: task, tools, sources, output, validations, pass/fail | **Concepto central a subir de nivel** en Invoice Detail y Audit Trail |
| **Traces** | Cada paso se convierte en evidencia que la empresa posee | El audit trail no puede ser un log decorativo |
| **HALP** | Human-Augmented LLM Processing: el humano enseña en el flujo real | La review humana (Approve / Reject / Flag) es el HALP de este hackathon |
| **Perception → Reasoning → Execution** | Capas de un Digital Worker | Encaja con OCR → Validation → Decision |
| **Cost / ROI / access** | Maisa vende control enterprise: coste, accesos, ROI en tiempo real | Cost Optimization **no es P0** salvo que el backend ya lo tenga |
| **300+ integrations** | Conectores a legacy y apps modernas | Nos basta SAP / NetSuite como conexiones mock o reales del backend |
| **P2P invoice automation** | Caso real de Maisa: intake, extracción, reglas, pago, excepciones | **Este es nuestro caso.** Estamos alineados de vertical |

### Qué diferencia a Maisa de un dashboard de IA genérico

1. El worker no sigue un grafo rígido: se adapta al caso.
2. Cada decisión tiene evidencia, no solo un porcentaje de confidence.
3. El humano entra en excepciones, no en cada factura.
4. La traza es reproducible: mismo input + misma config = mismo output.
5. El producto se siente como operaciones, no como un playground de prompts.

Si Alberto AI no hace visibles esos 5 puntos, parece un prototipo de OCR y no un producto Maisa-like.

---

## 3. Inventario del frontend actual

Todo vive en un único archivo: `app/page.tsx` (~277 líneas, pero con componentes enormes).  
No hay rutas. La navegación es `useState`. Los datos están hardcodeados. No hay capa de API.

### Pantallas que existen

| Superficie | Estado | Notas |
|---|---|---|
| Dashboard | Implementada | Workers live, PDF processing KPIs, decision distribution, activity chart, recent decisions |
| Invoices | Implementada | Search, filtros, tabla, export CSV, New Run, selección múltiple |
| Invoice Detail | Implementada | Visor PDF mock, highlights, AI Analysis, ERP match, Audit Trail, Approve/Reject |
| AI Workers | Implementada | KPIs, cards, workflow overview, recent executions, filtros, Create Worker |
| Worker Detail | Implementada | Métricas, executions, timeline |
| New Run | Implementada | Upload PDFs, seleccionar workers, ERP, priority, confidence threshold |
| Audit Trail | Implementada | Timeline filtrable (AI / Human / System) |
| Profile | Implementada | Nombre, email, notificaciones, password, plan |
| Run Execution (live) | **No existe** | New Run dice que abre monitoring, pero solo lanza un toast |
| Analytics | **No existe** | Estaba en el brief viejo |
| Cost Optimization | **No existe** | Estaba en el brief viejo |
| Settings | **No existe** | Profile lo sustituye a medias |

### Sidebar actual

Dashboard · Invoices · AI Workers · Audit Trail · Profile

### Componentes internos en `page.tsx`

`ProgressRing`, `StatusBadge`, `Sidebar`, `Card`, `NewRun`, `InvoiceModal`, `InvoiceDetail`, `AuditTrail`, `ProfilePage`, `LegacyInvoiceDetail`, `InvoicesPage`, `WorkerDetail`, `CreateWorkerModal`, `WorkersPage`.

### Código muerto o engañoso

- `LegacyInvoiceDetail`: duplicado muerto. **Borrar.**
- `InvoiceModal`: definido y no usado. **Borrar.**
- New Run suma `+22` ficheros y `118 MB` ficticios. **Quitar.**
- Create Worker no persiste nada y fabrica modelos (`Alberto Reasoning 2`).
- Export solo genera CSV, aunque el brief viejo pedía Excel y PDF.
- El botón Help del dashboard solo abre un toast.
- `components/ui/button.tsx` (shadcn) no se usa. El prototipo pinta botones a mano.
- `globals.css` tiene dark mode completo; el producto es light enterprise. No invertirlo ahora.
- No hay estados de loading, error, empty ni paginación real.

### Design system de facto (mantener)

| Token | Valor | Uso |
|---|---|---|
| Background | `#F7F8F5` / `#F7F7F3` | Canvas |
| Cards | `#FFFFFF` | Superficies |
| Primary | `#164F45` | Acciones, sidebar activo |
| Success / mint | `#67D4AD`, `#35B889` | PAY, running, health |
| Warning | `#D6F52A`, `#FFF6C9` | ESCALATE |
| Danger | `#BD3434`, `#F05B5B` | NO_PAY, errors |
| Text | `#17211E` | Carbón |
| Border | `#E1E5DF` | Soft borders |
| Radius | `xl` / `2xl` | Cards redondeadas |

Reglas visuales: whitespace, jerarquía clara, poco motion, look premium. Referencias: Maisa, Linear, Vercel.  
No rediseñar la paleta. Extraer tokens a CSS variables o constantes compartidas, no reescribir el look.

---

## 4. Gap analysis: nosotros vs Maisa vs el brief original

### 4.1 Mantener (está bien y es el núcleo)

- Dashboard operativo con workers + volumen de PDFs + decisiones recientes.
- Cola de invoices con status, decision, confidence y tiempo.
- Invoice Detail con documento + campos extraídos + reasoning + acciones humanas.
- Pipeline OCR → Validation → Decision.
- New Run como forma de lanzar trabajo.
- Audit trail como idea (hay que subirlo a Chain of Work).
- Estética verde enterprise ya conseguida.

### 4.2 Añadir — P0, necesario para producto y para el backend

Estas piezas faltan y sí hacen falta. Sin ellas el frontend no se puede conectar ni se entiende como producto Maisa-like.

1. **Arquitectura real de Next.js**
   - Rutas: `/`, `/invoices`, `/invoices/[id]`, `/workers`, `/workers/[id]`, `/runs/new`, `/runs/[id]`, `/audit`.
   - Layout con sidebar persistente. Dejar de montar/desmontar el chrome por `useState`.

2. **Capa de datos desacoplada de la UI**
   - `lib/types.ts` con los modelos de abajo.
   - `lib/api/` con funciones tipadas.
   - Adapter mock ahora, HTTP real detrás de `NEXT_PUBLIC_API_URL` después.
   - Cero arrays hardcodeados dentro de componentes de página.

3. **Run Execution**
   - Pantalla que New Run promete y no existe.
   - Debe mostrar: run id, documentos, worker actual, progreso, errores, Chain of Work en vivo, CTA a invoices resultantes.
   - Es la pantalla más "Maisa" del producto: se ve al worker trabajando con traza.

4. **Chain of Work de verdad, no un log bonito**
   - Cada evento debe poder mostrar: task, actor, tool/source, input, output, validation, pass/fail, evidence, timestamp.
   - En Invoice Detail, sustituir el reasoning suelto + mini-timeline por esta estructura (se puede mantener el resumen y abrir "full trace").
   - Audit Trail global reutiliza el mismo componente.

5. **Estados de producto**
   - Loading, empty, error, unauthorized.
   - Invoice en `processing`, `processed`, `needs_review`, `failed`.
   - Worker `running`, `waiting`, `paused`, `error`.
   - Review actions que llamen API: approve, reject, flag, re-run, send back to OCR.

6. **Contrato listo para el backend**
   - Types + client + env + errores de red.
   - No meter fetch sueltos en componentes.

### 4.3 Añadir — P1, solo si el backend ya lo tiene

- Coste por run / spend / savings. Maisa lo vende; nosotros no lo construimos de adorno.
- Analytics de volumen más allá del chart del dashboard.
- Export Excel/PDF.
- Persistencia de Create Worker.
- Integraciones más allá de SAP/NetSuite.
- Knowledge / policies adjuntas al worker.
- Onboarding del worker en lenguaje natural.

### 4.4 No añadir — parece Maisa pero nos sobra en un hackathon

- Maisa Studio: builder NL, 5 pasos de onboarding corporativo, 300 conectores.
- Entrenar SLMs a partir de traces.
- Model marketplace / "freedom from frontier labs".
- Certificaciones SOC2 / ISO / GDPR como pantalla.
- Dark mode.
- Multi-vertical (claims, KYC, trade finance).
- Auth completa, billing, SSO, RBAC fino.
- Chat genérico con el worker.

### 4.5 Quitar o no invertir más

| Pieza actual | Decisión | Por qué |
|---|---|---|
| `LegacyInvoiceDetail` | Eliminar | Código muerto |
| `InvoiceModal` | Eliminar | No se usa |
| Profile (password, sessions, plan) | Recortar a un bloque mínimo o mover a `/settings` vacío de verdad | No es el producto y no hay backend de cuentas |
| Create Worker wizard de 5 pasos | Dejar de invertir. Si se mantiene, que sea un CTA deshabilitado o un form mínimo conectable | Maisa Studio no es nuestro scope; además no persiste |
| Filtros de workers que no filtran de verdad | O se conectan a datos o se simplifican | UI falsa |
| `+22 files` / `118 MB` | Eliminar | Mentira de prototipo |
| Help toast | Quitar o sustituir por nada | Ruido |
| Analytics y Cost Optimization como páginas vacías | No crearlas | El brief viejo las pedía; Maisa las tiene; nuestro frontend y el hackathon no las necesitan para demo |
| Duplicar Invoice Detail | Una sola implementación | Ya hay dos |

El brief original pedía Analytics, Cost Optimization y Settings. **No las implementéis** salvo que el backend las entregue. Diluyen la demo.

### 4.6 Ajuste de lenguaje (barato, alto impacto)

No hace falta un rebrand. Sí conviene alinear copy con Maisa:

| Evitar | Preferir |
|---|---|
| AI agent / bot | Digital Worker |
| Audit log / history | Chain of Work / Trace |
| Magic AI decision | Decision + evidence + rules applied |
| Alberto Reasoning 2 (modelo inventado) | Modelo que venga del backend, o "Decision Worker" |

Nombre de producto: **Alberto AI** se mantiene. Maisa es la referencia, no el nombre.

---

## 5. Arquitectura objetivo

```
app/
  layout.tsx                         # sidebar + main
  page.tsx                           # Dashboard
  invoices/page.tsx
  invoices/[id]/page.tsx
  workers/page.tsx
  workers/[id]/page.tsx
  runs/new/page.tsx
  runs/[id]/page.tsx
  audit/page.tsx

components/
  layout/Sidebar.tsx
  ui/                                # Button, Card, Badge, etc. reutilizables
  dashboard/                         # MetricCard, ActivityChart, DecisionDistribution
  workers/                           # WorkerCard, WorkerStatus, WorkflowTimeline
  invoices/                          # InvoiceTable, FilterBar, InvoiceDocument
  runs/                              # RunProgress, RunSummary
  audit/                             # ChainOfWork, TraceStep

lib/
  types.ts
  api/client.ts                      # fetch wrapper
  api/workers.ts
  api/invoices.ts
  api/runs.ts
  api/audit.ts
  api/dashboard.ts
  mock/                              # datos actuales, mismo contrato que la API
  config.ts                          # API_BASE_URL

hooks/
  useWorkers.ts
  useInvoices.ts
  useRun.ts
```

### Reglas de implementación

1. Entender la arquitectura actual antes de reescribir.
2. Extraer, no rediseñar.
3. Un componente = una responsabilidad. UI separada de fetch.
4. Reutilizar `StatusBadge`, `Card`, `ProgressRing`, tabla, filtros.
5. No añadir dependencias nuevas sin necesidad. Ya hay Recharts, lucide, shadcn.
6. Empezar a usar `components/ui/button.tsx` donde encaje, sin romper el look.
7. Tokens de color en un solo sitio.
8. TypeScript estricto en models y API.
9. No mezclar lógica de backend en componentes visuales.
10. Si una acción no tiene endpoint, dejar el botón cableado a una función API stub, no a un `alert` / toast mentiroso.

---

## 6. Modelos y contrato de API

El backend lo hacen los compañeros. El frontend debe definir types claros y un client. Si el backend usa otros nombres, mapear en el client, no en la UI.

Hasta que exista `NEXT_PUBLIC_API_URL`, el client usa `lib/mock`.

### 6.1 Types

```ts
type WorkerStatus = 'running' | 'waiting' | 'paused' | 'error'
type InvoiceStatus = 'processing' | 'processed' | 'needs_review' | 'failed'
type Decision = 'PAY' | 'NO_PAY' | 'ESCALATE' | null
type RunStatus = 'draft' | 'queued' | 'running' | 'completed' | 'failed'
type TraceActor = 'system' | 'ocr' | 'validation' | 'decision' | 'human'
type TraceResult = 'pass' | 'fail' | 'warning' | 'info'

interface Worker {
  id: string
  name: string
  slug: 'ocr' | 'validation' | 'decision'
  description: string
  status: WorkerStatus
  progress: number | null
  runs: number
  successRate: number
  avgTimeSeconds: number
  costPerRun: number | null
  lastActivityAt: string
}

interface Invoice {
  id: string
  supplier: string
  amount: number
  currency: 'EUR'
  invoiceNumber: string
  invoiceDate: string
  status: InvoiceStatus
  decision: Decision
  confidence: number | null
  processingTimeSeconds: number | null
  runId: string | null
  extractedFields: ExtractedField[]
  reasoningSummary: string
}

interface ExtractedField {
  key: 'supplier' | 'amount' | 'date' | 'invoiceNumber' | 'taxId' | 'poNumber'
  label: string
  value: string
  confidence: number | null
}

interface Run {
  id: string
  status: RunStatus
  documentCount: number
  workerIds: string[]
  erp: 'sap' | 'netsuite'
  priority: 'low' | 'normal' | 'high'
  confidenceThreshold: number
  createdAt: string
  estimatedDurationSeconds: number | null
}

interface TraceStep {
  id: string
  invoiceId?: string
  runId?: string
  actor: TraceActor
  title: string
  task: string
  tool?: string
  source?: string
  output?: string
  validation?: string
  result: TraceResult
  evidence?: string
  timestamp: string
}
```

### 6.2 Endpoints esperados

Alinear con el backend cuando exista. Nombres canónicos:

```
GET    /workers
GET    /workers/:id
GET    /workers/:id/executions

GET    /invoices
GET    /invoices/:id
POST   /invoices/:id/review          { action: 'approve' | 'reject' | 'flag', comment?: string }
POST   /invoices/:id/rerun
PATCH  /invoices/:id/fields          { fields: ExtractedField[] }

POST   /runs                         { files, workerIds, erp, priority, confidenceThreshold }
GET    /runs/:id
GET    /runs/:id/events              # polling o SSE si el backend lo ofrece

GET    /audit                        # ?invoiceId & ?runId & ?type
GET    /dashboard                    # kpis + activity + recent decisions
```

Query params útiles en invoices: `q`, `status`, `decision`, `confidenceMin`, `page`, `pageSize`.

### 6.3 Variables de entorno

```
NEXT_PUBLIC_API_URL=
NEXT_PUBLIC_USE_MOCK=true
```

Cuando `NEXT_PUBLIC_USE_MOCK=false` y hay URL, el client cambia a HTTP. No reescribir páginas.

---

## 7. Pantallas: especificación corta

### Dashboard `/`

- KPI de procesamiento: processed, pending, needs attention, requires resolution.
- Lista de Digital Workers del pipeline con status y progreso.
- Distribución PAY / NO_PAY / ESCALATE.
- Actividad semanal.
- Recent decisions → click abre `/invoices/[id]`.
- CTA `+ New Run` → `/runs/new`.

### Invoices `/invoices`

- Search + filtros reales sobre el dataset (mock o API).
- Tabla: id, supplier, amount, status, decision, confidence, time.
- Export CSV de la selección o del resultado filtrado.
- New Run.
- Click fila → detail.

### Invoice Detail `/invoices/[id]`

- Documento a la izquierda, análisis a la derecha.
- Tabs: AI Analysis · ERP match · Chain of Work.
- Acciones: Approve as PAY, Reject, Flag, Send back to OCR, Re-run.
- Campos extraídos clicables (highlight). Edit values solo si el backend lo soporta; si no, UI deshabilitada.
- Full trace = mismo `ChainOfWork` que Audit.

### Digital Workers `/workers`

- Cards de los 3 workers del pipeline.
- Métricas: runs, success rate, avg time, last activity.
- Workflow overview del pipeline.
- Recent executions.
- Create Worker: no bloquear la demo. Si no hay POST `/workers`, no fingir creación.

### Worker Detail `/workers/[id]`

- Header + KPIs.
- Executions recientes.
- Timeline / Chain of Work filtrada a ese worker.

### New Run `/runs/new`

- Upload PDF real (guardar File objects, no solo nombres).
- Workers del pipeline, en secuencia.
- ERP, priority, confidence threshold, notify, stop on error.
- Summary honesto (sin +22 files).
- Start Run → `POST /runs` → navegar a `/runs/[id]`.

### Run Execution `/runs/[id]`

- Status del run.
- Progreso por documento y por worker.
- Errores visibles.
- Chain of Work en vivo (poll cada pocos segundos en mock; mismo hook para API).
- Al completar, listar invoices generadas.

### Audit `/audit`

- Mismo componente `ChainOfWork`.
- Filtros: All / AI / Human / System.
- Expandir un step para ver evidence.

### Profile / Settings

- No es P0. Si se mantiene el item del sidebar, página mínima (nombre, rol) sin password/plan inventados.

---

## 8. Orden de trabajo para Claude Code

Hacerlo en este orden. Un paso estable antes del siguiente. No mezclar rediseño con refactor.

1. **Inventario y extracción sin cambiar UX**
   - Romper `app/page.tsx` en rutas y componentes.
   - Borrar `LegacyInvoiceDetail`, `InvoiceModal` y dead code.
   - Extraer mock data a `lib/mock`.
   - Extraer `Card`, `StatusBadge`, `ProgressRing`, `Sidebar`.

2. **Types + API client + mock adapter**
   - Mismo contrato para mock y red.
   - Sustituir lecturas locales por hooks/funciones API.

3. **Alinear producto**
   - Copy Digital Worker / Chain of Work.
   - Quitar datos falsos (+22 files, modelos inventados).
   - Recortar Profile y Create Worker.

4. **Añadir Run Execution**
   - Cablear New Run → POST → `/runs/[id]`.
   - Mock que avance de estado para la demo.

5. **Subir Audit Trail a Chain of Work**
   - Un componente, dos sitios (invoice + /audit).

6. **Estados y acciones reales**
   - Loading/empty/error.
   - Review / re-run / start run contra el client.

7. **Conexión backend**
   - Leer env.
   - Mapear response del backend a nuestros types.
   - No cambiar UI para encajar nombres raros; mapear en el client.
   - Dejar `README` corto: cómo levantar, qué env, qué endpoints espera.

### Definition of done

- El frontend ya no depende de un único `page.tsx` monolítico.
- No hay código muerto ni toasts que fingen features.
- Todas las lecturas/escrituras pasan por `lib/api`.
- Con `NEXT_PUBLIC_USE_MOCK=true` la demo funciona offline.
- Con URL de backend, no hay que reescribir páginas: solo el client.
- Un reviewer de finanzas puede: ver el dashboard, lanzar un run, seguir la ejecución, abrir una factura, entender por qué ESCALATE, aprobar o rechazar, y ver la Chain of Work.
- El look actual se conserva.

### Qué no hacer

- No inventar pantallas nuevas (Analytics, Billing, Marketplace, Studio).
- No cambiar decisiones de producto (3 workers, 3 decisions, umbral 75%).
- No clonar el marketing site de Maisa.
- No añadir librerías de state management / data fetching si no hacen falta. `fetch` + hooks es suficiente.
- No "mejorar" el diseño con un theme nuevo.
- No commitear secretos ni `.env` con tokens.

---

## 9. Prompt para pegar en Claude Code

```
Lee project-context.md entero antes de tocar código.

Objetivo: dejar el frontend de Alberto AI limpio, fiel al producto y listo para conectar con el backend de la hackathon.

Hazlo en este orden:
1) Extrae app/page.tsx a rutas y componentes reutilizables sin cambiar el look.
2) Borra LegacyInvoiceDetail, InvoiceModal y cualquier dead code.
3) Crea lib/types.ts + lib/api con adapter mock y client HTTP (NEXT_PUBLIC_API_URL + NEXT_PUBLIC_USE_MOCK).
4) Quita datos falsos (+22 files, modelos inventados, toasts que fingen features).
5) Recorta Profile y no inviertas en Create Worker si no hay API.
6) Implementa /runs/[id] (Run Execution) y conecta New Run a POST /runs.
7) Sustituye el audit log decorativo por un componente Chain of Work reutilizado en Invoice Detail y /audit.
8) Añade loading / empty / error y deja las acciones de review/re-run/start-run pasando por el API client.

No añadas Analytics, Cost Optimization, Maisa Studio, dark mode, auth ni nuevas dependencias.
No rediseñes. No inventes features. Si el backend usa otros nombres de campos, mapea en el client.
Cuando termines, resume qué moviste, qué borreste, qué quedó pendiente de backend y cómo conectar la API.
```

---

## 10. Contexto que este documento reemplaza

El `project-context.md` anterior era un dump de ideas: estructura deseada, design system, mocks incompletos y reglas mezcladas. Servía como brainstorm, no como brief.

Este archivo es la fuente de verdad. Si hay conflicto entre el prototipo, el brief viejo y Maisa:

1. Este documento gana.
2. El prototipo visual se conserva.
3. Maisa informa el lenguaje y la Chain of Work, no el scope.
4. El backend manda en datos reales cuando exista.
