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

## Arrancar todo contra la BD real

Tres procesos, **uno por puerto**, cada uno en su terminal desde la raíz del repo:

| Puerto | Proceso | Comando |
|---|---|---|
| 8000 | puente con la bandeja (`dist/bandeja.db`, Dropzone activo) | `uv run python -m albertitos.console.api --bandeja` |
| 8001 | chat AlbertitosAI sobre la misma BD | `uv run python -m albertitos.chat --servidor --db dist/bandeja.db` |
| 3000 | consola Next | `cd console-web && pnpm dev` (con el `.env.local` de «Conectar el backend») |

`bandeja.db` es una copia de la de la entrega (se crea sola la primera vez) más lo que subas por el Dropzone, que
va al lote 99 y nunca toca `dist/albertitos.db`. Chat y consola sobre la misma BD ven las mismas facturas. Sin
Dropzone basta el puente sin `--bandeja` y `make chat`, los dos sobre `dist/albertitos.db`.

Comprobación: `curl http://127.0.0.1:8000/salud` da `"ficheros": 500` y `curl http://127.0.0.1:8001/chat/salud`
da `"api": 2, "modelo_disponible": true`. Si la salud del chat no trae `api` ni `modelo_disponible`, contestas a un
servidor viejo.

**Windows: dos procesos pueden escuchar en el mismo puerto** sin error y las peticiones van al más antiguo. Así un
chat arrancado antes de un merge contesta con código viejo («Ahora mismo no puedo consultar al modelo») aunque el
nuevo funcione. Antes de arrancar, mira que el puerto esté libre y mata lo que sobre:

```powershell
netstat -ano | Select-String ':(8000|8001) .*LISTEN'        # un PID por puerto, o ninguno
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object CommandLine -like '*albertitos*' |
  Select-Object ProcessId, CreationDate, CommandLine      # qué es cada uno y desde cuándo
Stop-Process -Id <pid> -Force
```

`make console` levanta 8000 y 3000 juntos, pero en Windows Ctrl-C puede dejar vivo el Python: compruébalo con `netstat`.
El puente con `--bandeja` sirve `dist/bandeja.db` (la de subir PDFs), no la Caja: no lo tengas a la vez que el normal
en el 8000.

Si el chat contesta «degradado», prueba sin la consola: `uv run python -m albertitos.chat "¿Cuántas facturas hay en
PAGAR, ESCALAR y NO_PAGAR?"`. Si ahí contesta bien, el problema es el proceso del 8001, no el modelo ni la clave.

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

## AlbertitosAI

Botón «AlbertitosAI» (abajo a la derecha) y un panel lateral contra el **chat de sólo lectura**: un proceso
aparte, no el puente de `:8000`, porque necesita POST. Contrato: `docs/api/chat.md` y `/chat/salud` v2 en
`docs/agentes/PLAN-13.md`. Código: `lib/api/chat.ts`, `components/chat/`, `lib/mock/chat.ts`.

```bash
make chat                                              # o: uv run python -m albertitos.chat --servidor
                                                       # http://127.0.0.1:8001, lee dist/albertitos.db en sólo lectura
uv run python -m albertitos.chat "¿Por qué se escala F26-2201_transportes.pdf?"   # repliegue por terminal
```

- `NEXT_PUBLIC_CHAT_URL` (por defecto `http://127.0.0.1:8001`). Si el 8001 está ocupado, arranca el chat con
  `ALBERTITOS_CHAT_PUERTO=8011` y pon aquí `http://127.0.0.1:8011`. El chat sólo acepta los orígenes de
  `ALBERTITOS_CHAT_ORIGENES` (por defecto `localhost:3000` y `127.0.0.1:3000`).
- **Estado y presupuesto:** «En vivo» o el motivo de indisponibilidad, sin nombres de modelo, respaldo ni herramientas.
  Salud se consulta cada 30 s sin gastar llamadas. El contador se actualiza además con cada respuesta:
  barra verde (>50 %), ámbar (20–50 %) o roja (<20 %), descenso de 600 ms y «−N».
  Con movimiento reducido no se anima. Un backend antiguo puede omitir los campos nuevos.
- **Respuesta y trazabilidad:** texto plano, «Ver más» tras cinco líneas y botón Copiar. La primera cita lleva una
  ficha obtenida de GET /ficheros/:id, con decisión, proveedor, importe, motivo y traza; las demás son enlaces.
  Si hay veinte se advierte que puede haber más. En mock la ficha avisa «Datos de ejemplo · no es la BD».
- **Entrada:** texto libre con atajos Factura, Pedido, Proveedor, Semana y Confianza que muestran la pregunta
  antes de usarla. Cuatro sugerencias iniciales, Nueva conversación y panel a ancho completo en móvil.
  Un 429 se traduce como «Ya hay una consulta en curso; espera a que termine».
- **Respuestas grabadas:** el interruptor «Ver respuestas grabadas (evaluación 19/09 15:00)» enseña las 15 respuestas
  reales de `docs/api/ejemplos/chat-*.json`. Cada una lleva la etiqueta fija «respuesta grabada · no es una consulta en
  vivo» y su evaluación. Sólo responde a esas 15 preguntas, tal cual: nunca inventa una. El interruptor está disponible
  si el modelo no lo está, si una respuesta llega degradada, con `NEXT_PUBLIC_USE_MOCK=true` o con
  `NEXT_PUBLIC_CHAT_GRABADAS=true`.
- **Sin servidor del chat**, el botón no aparece y la consola no cambia. Con `NEXT_PUBLIC_USE_MOCK=true` o
  `NEXT_PUBLIC_CHAT_GRABADAS=true` aparece, pero sólo con las respuestas grabadas.
- Teclado: el foco va al campo al abrir, Intro envía (Mayús+Intro, salto de línea) y Escape cierra.

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
