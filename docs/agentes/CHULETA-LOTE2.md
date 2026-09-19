# Chuleta del lote 2 · **EJECUTADA** (19/09 18:00 → 20/09 00:17)

> **Ya no es una previsión: esto es lo que pasó.** El lote 2 está integrado, decidido y entregado
> (`d2ade3f`: 500 líneas 445/46/9 + 40 líneas 23/16/1, auditoría VERDE). La receta de abajo se conserva porque
> sirve para repetirlo: si mañana cambia la norma, se reprocesa y se vuelve a publicar con estos mismos pasos.

## Lo que pasó de verdad, con sus tiempos
| Paso | Cómo salió |
|---|---|
| **Material** | **No hubo ZIP ni hashes en el canal.** Llegó como el commit `f831e34` del repo de participantes: 40 PDF en `facturas_primin/` y tres CSV. Copiado a `data/lote2/` con su manifiesto; `caja verify --lote 2` → OK |
| **La regla nueva** | **Nunca se publicó.** Mónica y Miguel decidieron con lo que dicen los datos: norma v4 con la regla de moneda (ADR-0022) |
| Maestro del lote 2 | `maestro --lote2 data/lote2` → 15 proveedores, 555 pedidos (`f504377103b2`). Los IBAN de P013, P014 y P015 no pasan el control: avisos de calidad |
| ERP v2 | 556 asientos (516 + 40 nuevos), 33 consultas, 3 reintentos, **4,3 s**. `AS-90001` deja `PO-2026-0071` PAGADA |
| Ingesta y extracción | 40/40 sin pendientes: **23 por plantilla y 17 por LLM de texto**. **Ninguna escaneada**, así que los 6-10 minutos de visión que temíamos no hicieron falta |
| Decisión | `reprocess --impacted --lote 2 --norma v4 --erp v2` → 40 de 40 en **0,03 s** |
| Lote 1 | ADR-0017 aplicado (`hechos import` + `reprocess --impacted --lote 1`): 438/53/9 → **445/46/9**, cambian 7 escaneadas |
| Auditoría y entrega | `package` → 500 + 40, las dos APTO; auditoría **VERDE** con un ámbar esperado (16 de 40 escalados en el lote 2, por las divisas); `make publicar` en seco y después de verdad |
| **P0-5** (nombre repetido) y **P0-1** (copia exacta) | **No pasó ninguno** en el lote 2 real. El código estaba listo y no hizo falta |
| Contingencia (ADR-0009) | No hizo falta: 0 pendientes |

## Lo que no habíamos previsto
- **Los proveedores nuevos vienen en CSV, no en el Excel**, y sin cargarlos las 18 facturas `e*` salían con «el
  pedido no existe en el maestro». Se resolvió con `sources/lote2.py` y `maestro --lote2`.
- **Ocho facturas en divisa** contra pedidos en euros, y **siete declarando IVA 0 %**. Escalan: sin tabla de cambio
  oficial no convertimos. Es la pregunta abierta para los mentores (`docs/hitos.md`).
- **Tres facturas manuscritas o corregidas a mano** (`e16`, `e17`, `e18`). La peligrosa es `e18`: el texto impreso
  cuadra con el ERP y el papel dice otra cosa. La caza el aviso de anotación a mano (ADR-0020).
- **Cuatro identificadores extranjeros** (IVA alemán y francés, CNPJ, número japonés) daban `NIF_INVALIDO` y
  escalaban una factura limpia. Arreglado en `formatos.py`.

## Ensayo previo (19/09 13:12), que es lo que nos dejó llegar preparados
Con el código de `main` (`54b4171`), sobre una copia y con 14 PDF simulados: `bash scripts/ensayo/lote2-ensayo.sh`
→ **14,3 s de principio a fin**, todo en verde. Tiempos por paso en `dist/ensayo/j1/tiempos.tsv`. No medía la
visión, y al final no hizo falta: el lote 2 no trae escaneadas.

## Entorno
```bash
export ALBERTITOS_DB=dist/albertitos.db
export ALBERTITOS_FECHA_CORTE=2026-09-18
export ALBERTITOS_WORKERS=4
```
El ERP v1 del equipo vive en `:8009` y **no se toca**. El v2 del lote 2 va en **`:8011`**.

## 0 · Antes de abrir el ZIP
```bash
uv run python scripts/preflight_lote2.py --respaldar     # 0 fantasmas, ERP esperado v1 y «LLM» en VERDE
uv run python scripts/auditoria_entrega.py               # VERDE
sha256sum dist/albertitos.db dist/entrega/outcomes.jsonl # apúntalas: al final, iguales
```

**La fila «LLM» del preflight tiene que salir en VERDE** (clave presente, visión `qwen3.6`, respaldo `deepseek-v4-flash`).
Lo encontró R1: sin `.env`, el modelo por defecto es `claude-*`, que el gateway rechaza, así que **las escaneadas del
lote 2 se quedarían PENDIENTE**. En la carpeta de revisión, sin `.env`, así le pasó a él.

## 1 · Material
**Lo que llegó de verdad (19/09, 17:57): no un ZIP, sino un commit** del repo de participantes (`f831e34`), con los 40
PDFs en `facturas_primin/` y los tres CSV en la raíz. **Ya está en `data/lote2/`**, con manifiesto (rama
`javier/lote2-fuentes`, `48c4269`; origen en `data/lote2/ORIGEN.txt`). Sólo hay que comprobarlo:
```bash
uv run albertitos caja verify --lote 2                  # 40 PDFs · 2 con tildes · Lote 2 OK
sha256sum -c data/lote2.sha256 | grep -vc ': OK$'       # 0
```
Si el canal publica después un ZIP con hash, se compara con lo que hay (`verificar_material.py "$ZIP" --hash …
--esperados 40`) y, si difiere, **se para**. La receta de abajo es para ese caso:
```bash
: "${ZIP:?ruta del ZIP}" "${HASH_PUBLICADO:?sha256 del canal}"
uv run python scripts/verificar_material.py "$ZIP" --hash "$HASH_PUBLICADO" --esperados 40
# data/lote2 tiene que estar vacío; si no, PARAR y apartar el intento anterior
unzip -n "$ZIP" -d data/lote2/
uv run python scripts/verificar_material.py data/lote2 --esperados 40
uv run albertitos caja manifest --lote 2 && uv run albertitos caja verify --lote 2
git add -- data/lote2 data/lote2.sha256 && git commit --only data/lote2 data/lote2.sha256 -m "data: lote 2 recibido y manifiesto verificado"
```
Flags reales: `material` posicional · `--hash` · `--db` · `--lote1-dir` · `--esperados`.

| Lo que dice el verificador | Qué haces |
|---|---|
| AVISO «copia exacta (SHA-256)… (P0-1)» | **Sigues.** Cada nombre tendrá su línea; todas las copias, y el original del lote 1, salen ESCALAR |
| ROJO «PDF idéntico por SHA-256…» | Falta P0-1: `/sync` con `main` y repetir. Nunca ingerir así |
| AVISO **«nombre coincide con lote 1 y el contenido es otro»** (P0-5) | **Sigues.** P0-5 ya está en `main`: el verificador avisa y no para (R1, 15:55: APTO, exit 0), y **no hay nada que mergear**. El PDF que choca entra en `ficheros` como `./X.pdf` (`db.PREFIJO_INTERNO`) y su nombre de entrega va en `identidades`, con sus hechos, su decisión y su línea. Si vieras ROJO es que estás con código viejo: `git pull` |
| ROJO NFC · `.PDF` · subcarpeta | Corriges la estructura. **Nunca renombres un PDF oficial** |
| «sin adjuntos con posible regla» | La regla nueva llega por otro sitio: mírala en el canal y pásasela a Mónica literal |

## 2 · Maestro del lote 2, ingesta y flujo con el ERP v1
**Los proveedores P012-P015 y los 39 pedidos nuevos vienen en CSV, no en el Excel.** Sin este paso, las facturas
`e*` salen con el NIF o el pedido «fuera del maestro»:
```bash
uv run albertitos maestro --lote2 data/lote2   # 15 proveedores · 555 pedidos · versión f504377103b2
```
**Ojo:** si `albertitos run` recarga sólo el Excel (`pipeline/run.py`, avisado a Miguel en la bitácora), pisa este
maestro: después de cada `run`, vuelve a ejecutar `maestro --lote2` y luego `reprocess --impacted --lote 2`.
**Gateway:** con `PROMPT_VERSION` p-0.4 (ADR-0019), el lote 1 ya no sale de la caché si se reextrae. `run` sólo extrae
lo que no tiene hechos, que es el lote 2; nunca `extract --todo` ni borrar hechos del lote 1.
```bash
uv run albertitos ingest --dir data/lote2/facturas --lote 2
uv run albertitos run --erp v1 --norma v3 --fecha-corte 2026-09-18 --salida dist/lote2-preauditoria
uv run albertitos status
```
`run --erp` ya existe (`cli.py`); la vieja alternativa `extract` + `reprocess --todo` ya no hace falta.
`run` empaqueta: su salida preliminar **nunca** es `dist/entrega`.

## 3 · ERP v2, diff y reprocesado
El lote 1 **no se toca**: se entregó con la norma v3 y el ERP v1 (ADR-0021). Todo reproceso del sábado lleva
`--lote 2`; sin él, `reprocess`, `run` y `decide` se niegan si cambiarían el contexto del lote 1.
```bash
python3 data/caja/alberto_erp.py --puerto 8011 --lote2 data/lote2/erp_export_lote2.csv   # otra terminal
curl --fail --silent http://127.0.0.1:8011/erp/estado
ALBERTITOS_ERP_URL=http://127.0.0.1:8011 uv run albertitos erp pull --tag v2
uv run albertitos erp diff v1 v2        # real, 19/09: 556 asientos = 516 + 40 nuevos, 0 cambiados (4,3 s)
uv run albertitos reprocess --impacted --lote 2 --erp v2 --norma v3 --fecha-corte 2026-09-18
# Medido (J1, sólo para saberlo): con v2 aplicado al lote 1 cambiaría 1 de 500, factura_4635.pdf PAGAR → NO_PAGAR
# (R5: AS-90001 PAGADA). Por el ADR-0021 el lote 1 se queda con v1 y no cambia.
uv run python scripts/inventario_trampas.py --con-hechos --facturas data/lote2/facturas --erp-tag v2 --salida dist/anomalias_lote2.csv --sin-docs --solo-resumen
```

## 4 · La regla nueva (Mónica)
No la escribes tú ni la deduces de las facturas. Cuando exista `norma_v4`:
```bash
uv run albertitos reprocess --impacted --lote 2 --norma v4 --erp v2 --fecha-corte 2026-09-18
```
Si Mónica corrige la v3 **sin** subir la etiqueta, el linaje no lo ve: `reprocess --todo --lote 2 --norma v3 --erp v2`.

## 5 · Auditoría, package, entrega
```bash
uv run python scripts/auditoria_entrega.py --db "$ALBERTITOS_DB" --lote ambos --dir-lote1 data/caja/facturas --dir-lote2 data/lote2/facturas --entrega dist/lote2-preauditoria
uv run albertitos package --salida dist/entrega
uv run python scripts/auditoria_entrega.py --db "$ALBERTITOS_DB" --lote ambos --dir-lote1 data/caja/facturas --dir-lote2 data/lote2/facturas --entrega dist/entrega
make publicar          # en seco, se lee entero; publicar: make publicar ARGS=--publicar
```
500 líneas en el lote 1 y 40 en el lote 2, las dos APTO. `package` audita y **se niega** en rojo.
`--aceptar-rojo "<motivo>"` es el último recurso, con el motivo escrito: deja el evento
`AUDITORIA-ROJA-ACEPTADA`. Nunca se acepta por un JSONL inválido, ni con el motivo vacío.

## 6 · Si a las 07:30 del domingo queda algún PENDIENTE (ADR-0009)
```bash
uv run albertitos chaos --off && uv run albertitos extract --workers 4
uv run albertitos reprocess --impacted --lote 2 --erp v2 --norma v3 --fecha-corte 2026-09-18
uv run python scripts/contingencia.py --lote 2                       # en seco, primero
uv run python scripts/contingencia.py --lote 2 --aplicar --motivo "<qué falló y qué se reintentó>" --fecha-corte 2026-09-18
```
Sólo lote 2, sólo ESCALAR, sólo a la hora de entregar. Si el proveedor vuelve, `extract` +
`reprocess --impacted` la deshacen solos y hay que auditar y publicar otra vez.

## Trampa del ensayo (no del lote real)
`cli.LOTE2` es la constante `Path("data/lote2")`: `run`, `package` y `validate --lote 2` miran
**siempre** `data/lote2/facturas` y **no** leen `ALBERTITOS_DIR_LOTE2`. Para ensayar con
`data/fixtures/lote2_sim/` hay que copiar los PDFs a `data/lote2/facturas` dentro de un worktree
desechable; es lo que hace `scripts/ensayo/lote2-ensayo.sh`.
