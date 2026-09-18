# sources/ — ERP 2009, Excel, snapshots, caos · dueño: Javier

| Fichero | Qué hace | Estado |
|---|---|---|
| `erp.py` | `ClienteERP`: login, token renovado a los 250 usos/13 min, reintento de `ORA-00600`, `Retry-After` en 429, `SES-401` → relogin, limitador < 10 rps, evento por petición. `descargar_todo(tag)` → `ErpSnapshot` | base hecha; **probar contra `make erp-fast`** |
| `excel.py` | `cargar_maestro(xlsx)` → `MasterSnapshot` limpio (trim, P007 duplicado, notas de Alberto como `avisos_calidad`) y `leer_norma()` | hecho; validar avisos |
| `snapshot.py` | guardar/cargar snapshots `maestro`/`erp` en la BD; `diff_erp(v1, v2)` | hecho |
| `chaos.py` | `activar("llm_down"|"llm_429"|"llm_invalid")` / `desactivar()` / `modo()` vía `dist/chaos.json` | hecho |

## Tareas de Javier (viernes)
1. `make erp-fast` en una terminal y `uv run albertitos erp pull --tag v1`: 516 asientos, ~27 consultas, ≥2 reintentos ORA-00600. Añadir `tests/test_erp.py` (marcado `erp`): descarga completa = `<meta>.total`, sobrevive a ORA-00600 y a un token caducado (forzar `usos = 300`).
2. `uv run albertitos maestro`: revisar los `avisos_calidad` e inventariar las trampas en `docs/trampas.md` (o lanzar el subagente `cazador-trampas`).
3. Cruzar Excel ↔ ERP: ¿todos los pedidos del Excel tienen asiento? ¿importes iguales? ¿los 9 PAGADA a qué pedidos corresponden? Anotar en `docs/trampas.md`; es evidencia para la norma (Mónica) y para un ADR.
4. Sábado 18:00: `/lote2` → `make erp-lote2`, `erp pull --tag v2`, `erp diff v1 v2`.

## Reglas del módulo
- Todo lo que sale de aquí ya está normalizado: `Decimal`, `date`, NIF/IBAN/pedido sin espacios y en mayúsculas.
- Nunca consultar el ERP por factura: snapshot completo una vez y lookup en local (`ErpSnapshot.por_pedido()`).
- Nada de scraping de `/erp/consulta`. Nada de mocks del ERP: es local.
