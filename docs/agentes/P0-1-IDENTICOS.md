# P0-1 · El mismo PDF con otro nombre · para Miguel (H1, 19/09 11:00)

> **Superado (19/09 11:10).** P0-1 va con la implementación de Miguel, `e3b3764` en `miguel/pipeline` (tabla
> `identidades`, mismo diseño). **El parche `dist/ensayo/h1/identicos.patch` no se aplica.** Lo que sigue valiendo de
> H1: el fixture `data/fixtures/lote2_identicos/`, `tests/test_identicos.py` y el ensayo. Validación de la rama de
> Miguel con todo eso (R1-R5, de punta a punta): bitácora, 19/09 11:10. Este documento queda como registro del problema.

**Qué pasa hoy.** `ficheros` usa la sha256 como clave, y los hechos y las decisiones también van por sha256. Con una copia
byte a byte renombrada hay tres fallos, y los tres nos dejan sin premio o pagan dos veces:
- **(a)** Una copia de un PDF del lote 1 que llega en el lote 2: `guardar_fichero` hace `ON CONFLICT(sha256) DO UPDATE SET file_id, lote`. El lote 1 pierde su línea y `package` se niega.
- **(b)** Dos nombres con el mismo contenido dentro del lote 2: queda uno solo, y falta una línea.
- **(c)** Aunque se guardaran los dos nombres, hay **un** hecho para dos facturas. `marcar_duplicados` no ve ningún grupo y **las dos salen PAGAR**.

`verificar_material` para el lote en (a) y (b), pero entonces esa factura se queda sin línea: NO APTO igual. En el lote 1 no
hay ningún caso (500 sha256 distintas); el lote 2 es otra historia.

**Reproducirlo:** `uv run pytest tests/test_identicos.py -rx`. Salen 5 xfail estrictos (R1-R4) y 2 tests que documentan el
fallo de hoy. Fixture: `data/fixtures/lote2_identicos/` (una copia exacta de `2026-01-08_P001.pdf`, una pareja idéntica y un
control), con el ERP v1 real y el maestro real, sin red.

## El parche: `dist/ensayo/h1/identicos.patch` (sha256 `ede37b97d8fa`, 9 ficheros, +165 −46)
| Fichero | Cambio |
|---|---|
| `core/schema.sql` + `versions.py` | Tabla aditiva `identidades(file_id PK, sha256, lote, ingerido_en)` + índice. `ESQUEMA_VERSION` 3 |
| `core/db.py` | `tiene_identidades`, `guardar_identidad` e `identidades`. `decisiones_vigentes` devuelve una fila por **nombre** (las identidades comparten la decisión de su sha256, con su file_id y su lote). `traza(copia)` encuentra su fichero y añade `identidades` y `mismo_pdf_que` |
| `pipeline/etapas.py` | `ingest`: si la sha256 ya está con otro nombre **y ese nombre sigue existiendo** (en otro lote o en la misma carpeta), es una **copia** → `identidades`. Si no, es un **renombrado**, como hasta ahora. Lo guardado en la pasada cuenta como conocido (sin eso, la pareja del mismo lote se renombraba). `marcar_duplicados` cuenta las identidades como grupo → DUPLICADO_SOSPECHOSO → R6 → **ESCALAR todas** |
| `pipeline/auditoria.py`, `package.py` | Una fila por nombre en la auditoría (si no, la puerta vería la copia «sin decisión» y bloquearía `package`). Los eventos de rechazo encuentran la sha256 de una copia |
| `tests/test_identicos.py` | Quita los xfail y los 2 tests del fallo de antes; añade la auditoría con cada nombre y la BD de antes del parche |
| `docs/contratos.md`, `core/CLAUDE.md` | La fila del cambio, según el protocolo de `core/` |

**Las BD de antes del parche** se abren en solo lectura (auditoría, `status`, `trace`, consola) sin la tabla: todas las
consultas lo comprueban con `tiene_identidades` y hay un test para ese caso. Cualquier comando que escriba ejecuta
`init_schema` y crea la tabla.

## Aplicarlo (10 min)
```bash
git apply dist/ensayo/h1/identicos.patch && make check        # 412 passed en un worktree limpio (HEAD 2fb5f76 + parche)
uv run albertitos reprocess --todo --fecha-corte 2026-09-18 --erp v1 && make package    # debe quedar igual
```
El verificador (`scripts/verificar_material.py`, ya commiteado) detecta el parche solo (`db.guardar_identidad`) y pasa de
ROJO a AVISO.

## Pruebas (en un worktree, medidas)
- **R5, sin copias nada cambia:** copia de la BD real + parche → `reprocess --todo` da `500 de 500 recalculadas · 0 cambian`, `package` con auditoría da **438/53/9** y `outcomes.jsonl` **`1ec4be206089`**: el mismo sha256 que la entrega publicada.
- **De punta a punta con la CLI** (copia de la BD real + el fixture como `data/lote2/`, caos encendido para garantizar 0 red; log en `dist/ensayo/h1/e2e.log`): `ingest` registra 4 nombres y la copia como «copia exacta de 2026-01-08_P001.pdf (lote 1)». `reprocess --impacted` marca `duplicados: +5`. `package` con auditoría da **APTO los dos lotes** (lote 2: 4 líneas, todas ESCALAR). `validate` da APTO y APTO. `trace L2I-reenvio_…` devuelve `mismo_pdf_que: ["2026-01-08_P001.pdf"]`.
- El lote 1 cambia en 3 facturas: `2026-01-08_P001` por la copia exacta, y `2026-01-14_P002` y `2026-01-15_P003` porque el fixture reutiliza PDFs del lote 2 simulado, que repiten sus pedidos (el detector de pedidos de siempre, no el P0-1).

## Lo que decide Mónica (R3)
Con el parche, **todas** las identidades de un PDF repetido salen ESCALAR, también el original del lote 1 aunque ya se
hubiera entregado como PAGAR. Es la política vigente de duplicados («las dos ESCALAR», `PO-2026-0492`). Si prefiere pagar
el primero y escalar la copia, se cambia en un solo sitio, en `rules/`, porque la evidencia (`con`) ya dice cuál es cuál.
