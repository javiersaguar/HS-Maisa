# Auditoría de entrega · E2 · ciclo 5 (sábado 19/09/2026)

`scripts/auditoria_entrega.py` se ejecuta **antes de cada `package` y de cada `/entrega`**. Sólo lee la BD, los PDF
y los JSONL: no decide ni corrige nada. Tarda 0,3 s sobre la BD de la Caja.

El validador (`albertitos validate`) comprueba la **forma** de la entrega: conjunto exacto, NFC, enum. La
auditoría comprueba el **contenido**. La noche del 18/09 se colaron tres cosas que el validador daba por buenas:
`PO-2026-0492` en PAGAR dos veces, `scan_025.pdf` escalado por el motivo `"None"` y 10 ficheros simulados que
movieron 20 decisiones. Las tres salen aquí en rojo.

## Si tienes prisa (18:05)

```bash
uv run python scripts/auditoria_entrega.py           # los dos lotes; sale 1 si hay algo ROJO
```

- **ROJO** → no empaquetes ni subas nada. Cada rojo trae su "qué hacer". Arregla, reprocesa y repite.
- **ÁMBAR** → se puede entregar. Léelo y díselo a quien toque (casi siempre, Mónica).
- **VERDE** → `make package` y `/entrega`.

Para el ensayo del lote simulado (E3) o cualquier BD que no sea la real:

```bash
uv run python scripts/auditoria_entrega.py --db dist/ensayo/ensayo.db \
    --dir-lote2 data/fixtures/lote2_sim/facturas --entrega dist/ensayo/entrega
```

Opciones: `--db` (por defecto `ALBERTITOS_DB` o `dist/albertitos.db`) · `--lote 1|2|ambos` · `--dir-lote1` y
`--dir-lote2` (por defecto los de la CLI) · `--entrega` (carpeta de los JSONL, por defecto `dist/entrega`) ·
`--json` (para otro script: `veredicto`, `rojos`, y cada comprobación con sus ejemplos).

## Salida literal contra la BD real (19/09, 03:53)

```
Auditoría de entrega · dist/albertitos.db · lotes [1, 2]
  lote 1: 500 decisiones · {'ESCALAR': 48, 'NO_PAGAR': 9, 'PAGAR': 443}

nivel     n  comprobación
OK        0  Ficheros en la BD que no existen en disco
OK        0  Cada PDF del lote tiene decisión vigente
OK        0  Mismo pedido o misma factura en PAGAR más de una vez
OK        0  Duplicado sin marcar con alguna factura en PAGAR
OK        0  Duplicado sin marcar (ninguna en PAGAR)
OK        0  PAGAR que no cuadra con el maestro o el ERP
OK        0  Decisión tomada con unos hechos que ya no son los de la BD
OK        0  Hechos reescritos después de decidir (mismo hash)
ROJO      2  Motivo o evidencia falsos ("None", cita que no está en el PDF, cita vieja)
OK        0  Evidencia que no es literal (tildes, mayúsculas o PDF ausente)
OK        0  PAGAR con un aviso del extractor que no es benigno
OK        0  Reparto de resultados fuera de lo esperable
ÁMBAR     5  PAGAR con una lectura reconciliada con el maestro (confianza < 1)
OK        0  La entrega que hay en disco no pasa el validador
OK        0  La entrega en disco no es la de las decisiones vigentes

[ROJO] Motivo o evidencia falsos ("None", cita que no está en el PDF, cita vieja) · 2
  - scan_025.pdf: texto_sospechoso = 'None' (ESCALAR)
  - scan_025.pdf: el motivo de R6 cita 'None'
  qué hacer: (…)

[ÁMBAR] PAGAR con una lectura reconciliada con el maestro (confianza < 1) · 5
  - scan_006.pdf: confianza 0.6
  - scan_009.pdf: confianza 0.6
  - scan_011.pdf: confianza 0.6
  - scan_012.pdf: confianza 0.6
  - scan_017.pdf: confianza 0.6
  qué hacer: (…)
nota: sin lote 2: no existe data/lote2/facturas
nota: no hay dist/entrega/outcomes_lote2.jsonl: nada que comparar

VEREDICTO: ROJO · 1 comprobación(es) en rojo: NO entregar
```

Lo único rojo es `scan_025.pdf`, el error conocido. Todo lo demás de la noche anterior sale limpio: 0 pagos dobles,
0 PAGAR incoherentes de 443, 0 decisiones viejas, y las 29 evidencias de capa de texto son literales.

**Con `scan_025` reextraído** (copia `dist/ensayo/e2.db`, con el detector de `DOCUMENTO_SUPERPUESTO`, commit
`b678cfd`): `VEREDICTO: VERDE`, reparto 444 PAGAR · 47 ESCALAR · 9 NO_PAGAR. Además del ámbar de las 5 reconciliadas,
aparece un ámbar nuevo:

```
[ÁMBAR] PAGAR con un aviso del extractor que no es benigno · 1
  - scan_025.pdf: documento_superpuesto
```

Ese PAGAR depende de lo que decida Mónica (abajo).

## Qué significa cada comprobación y qué hacer

| Comprobación | Nivel | Qué detecta | Qué hacer |
|---|---|---|---|
| Ficheros en la BD que no existen en disco | ROJO | Restos de un ensayo (los `L2-*`) o de un intento anterior. Contaminan `marcar_duplicados` y `package` los metería en la entrega | `uv run python scripts/preflight_lote2.py` los lista; `--limpiar` los borra. Después, `albertitos reprocess --impacted` |
| Cada PDF del lote tiene decisión vigente | ROJO | PDFs sin ingerir, sin hechos o sin decidir. Una línea que falta es NO APTO | Sin ingerir: `ingest --dir <dir> --lote N`. Sin hechos: `extract --workers 4` (si queda PENDIENTE, `trace`). Sin decisión: `reprocess --impacted` |
| Mismo pedido o misma factura en PAGAR más de una vez | ROJO | Pago doble. La norma lo prohíbe por escrito | `reprocess --impacted` (corre `marcar_duplicados`) y repite |
| Duplicado sin marcar con alguna factura en PAGAR | ROJO | `marcar_duplicados` no ha corrido tras el último cambio de hechos (pasos sueltos) | Igual: `reprocess --impacted` o `run` entero |
| Duplicado sin marcar (ninguna en PAGAR) | ÁMBAR | Lo mismo, sin efecto hoy en ningún PAGAR | Igual, cuando puedas |
| PAGAR que no cuadra con el maestro o el ERP | ROJO | Un PAGAR sin pedido en el Excel, con IBAN o NIF que no son del proveedor del pedido, importe distinto (±0,01), sin asiento, con el asiento PAGADA, o con fecha ausente o posterior al corte. Se comprueba contra el maestro y el ERP **con que se decidió** | Decisión vieja → `reprocess --impacted`. Si persiste, es un hueco de la norma: a Mónica con `albertitos trace <file_id>`. No se corrige a mano |
| Decisión tomada con unos hechos que ya no son los de la BD | ROJO | Se reextrajo o se importó y no se volvió a decidir: lo entregado no sale de lo que hay | `reprocess --impacted` |
| Hechos reescritos después de decidir (mismo hash) | ÁMBAR | La evidencia pudo cambiar sin cambiar el hash: la traza puede citar un fragmento viejo | `reprocess --impacted` |
| Motivo o evidencia falsos | ROJO | `texto_sospechoso` = "None"/vacío; una cita que no está en el texto del PDF (sólo facturas con capa de texto); el motivo de R6 citando una evidencia distinta de la de los hechos | Reextraer el fichero (`extract --no-solo-pendientes --fixture <lista>`, 0 tokens desde la caché) y `reprocess --impacted`. Si cambia el resultado, a Mónica antes de entregar |
| Evidencia que no es literal | ÁMBAR | La cita sólo casa sin tildes o mayúsculas, o no está el PDF | `trace`; no bloquea |
| PAGAR con un aviso del extractor que no es benigno | ÁMBAR | Se paga una factura con un aviso que ninguna regla mira. Benignos: `sin_texto`, `fecha_en_letra` | A quien lleve la norma, con el `file_id` |
| Reparto de resultados fuera de lo esperable | ÁMBAR | ESCALAR > 15 % o NO_PAGAR > 5 % en un lote | Comparar con la referencia (443/48/9 en el lote 1 con v3 y ERP v1) y ver qué regla lo explica |
| PAGAR con una lectura reconciliada (confianza < 1) | ÁMBAR | Escaneadas cuyo NIF o IBAN se eligió con el maestro (ADR-0003) | Política nº 2 de DECISIONES-NORMA, pendiente de Mónica |
| La entrega que hay en disco no pasa el validador | ROJO | El JSONL que se subiría no es válido | `make package` la regenera, todo o nada |
| La entrega en disco no es la de las decisiones vigentes | ÁMBAR | Se decidió algo después del último `package` | `make package` antes de `/entrega` |

## Qué NO comprueba

- **Que el resultado sea el de la referencia privada.** No la tenemos. Comprueba coherencia, no acierto.
- **La evidencia de las escaneadas contra la imagen.** Sólo las citas de facturas con capa de texto se cotejan.
- **La política de duplicados entre lotes.** Un duplicado bien marcado y escalado sale limpio, aunque cruce lotes.
  Si Mónica decide pagar una y no la otra, `pago_doble` seguirá en verde mientras sólo una esté en PAGAR.
- **La regla nueva del sábado.** Las comprobaciones de PAGAR son las seis de la v3. Si la v4 añade una condición
  para pagar, hay que añadirla aquí.

## Aplicar el arreglo de `scan_025` a la BD real (lo hace Javier cuando Mónica decida)

Mónica decide si `DOCUMENTO_SUPERPUESTO` entra en `ANOMALIAS_HUMANO` (recomendación de E2: sí). **Primero su cambio
en `rules/`, después esto.** Si su cambio llega después, en el paso 3 hace falta `--todo` en vez de `--impacted`:
el linaje ve versiones, no código (ADR-0006).

```bash
uv run python scripts/preflight_lote2.py --respaldar          # copia de seguridad de la BD (E1)
printf 'scan_025.pdf\n' > /tmp/scan_025.txt
uv run albertitos extract --no-solo-pendientes --fixture /tmp/scan_025.txt     # 0 tokens: sale de la caché
uv run albertitos reprocess --impacted --fecha-corte 2026-09-18 --erp v1
uv run python scripts/auditoria_entrega.py                    # tiene que salir VERDE
uv run albertitos hechos export --salida data/fixtures/hechos_caja.jsonl        # 500 hechos; scan_025 no está en la muestra
make package && sha256sum dist/entrega/outcomes.jsonl
```

Medido en la copia `dist/ensayo/e2.db` (las dos opciones, sin guardar la segunda):
- **sin su cambio** (v3 tal cual): `29 de 500 recalculadas · 1 cambian: scan_025.pdf ESCALAR → PAGAR`, reparto
  444/47/9, y la auditoría lo avisa en ámbar;
- **con `DOCUMENTO_SUPERPUESTO` en `ANOMALIAS_HUMANO`** (simulado en memoria sobre los 500 hechos de la copia):
  cambia sólo `scan_025.pdf`, que queda ESCALAR con el motivo verdadero, `v3.R6: anomalía que debe ver una persona:
  documento_superpuesto`, y el reparto vuelve a 443/48/9. El proveedor superpuesto (P006) está en el evento de
  extract, no en el motivo: se ve con `albertitos trace scan_025.pdf`.
