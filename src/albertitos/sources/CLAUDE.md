# sources/ — ERP 2009, Excel, snapshots, caos y estado de la BD · dueño: Javier

Todo lo que entra de fuera pasa por aquí y sale ya normalizado: `Decimal` para dinero, `date` para fechas,
NIF/IBAN/pedido sin espacios y en mayúsculas.

| Fichero | Qué hace |
|---|---|
| `erp.py` | `ClienteERP`: login, token renovado a los 250 usos / 13 min, reintento de `ORA-00600`, `Retry-After` en 429, `SES-401` → relogin, limitador < 10 rps y un evento por petición. `descargar_todo(tag)` → `ErpSnapshot` (516 asientos, ~30 consultas, 2-3 reintentos, ~4 s) |
| `excel.py` | `cargar_maestro(xlsx)` → `MasterSnapshot` limpio (trim, P007 duplicado, 20 pedidos sin NIF, notas de Alberto como `avisos_calidad`) y `leer_norma()` |
| `snapshot.py` | guardar y cargar snapshots `maestro`/`erp` en la BD y `diff_erp(v1, v2)` (nuevos, cambiados, pedidos afectados) |
| `chaos.py` | interruptor de caos **por base de datos** (`<db>.chaos.json`; `ALBERTITOS_CHAOS` manda si se indica): `llm_down`, `llm_429`, `llm_invalid`, `llm_timeout` |
| `estado_bd.py` | qué hay en la BD: ficheros fantasma, hechos huérfanos, sin hechos, sin decisión, qué snapshot del ERP se usaría sin `--erp`, y un resumen. Lo usa `scripts/preflight_lote2.py` |

## Reglas del módulo
- **Nunca consultar el ERP por factura**: se descarga entero una vez a un snapshot versionado y se cruza en local (`ErpSnapshot.por_pedido()`).
- Nada de scraping de `/erp/consulta` (es para humanos) y nada de mocks del ERP: el bridge es local y arranca en un segundo con `make erp-fast`.
- El ERP es la referencia contable; cuando el Excel y el ERP discrepan, la norma decide, no el loader.
- El caos es por BD a propósito: ensayar una caída en una copia no puede tumbar una extracción real (pasó el 18/09).
- Antes de tocar el lote 2: `uv run python scripts/preflight_lote2.py`. Comprueba lo que se nos escapó aquella noche (ficheros de un lote simulado que seguían en la BD, y qué snapshot del ERP se usaría sin `--erp`).
