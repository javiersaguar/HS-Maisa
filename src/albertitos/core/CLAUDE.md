# core/ — contratos congelados · dueño: Miguel

Aquí vive lo único contra lo que trabajan los cinco a la vez. Se congeló en la hora 1 y **no se edita sin
avisar en el canal** (un hook lo bloquea a quien no sea Miguel: marcador `.claude/dueno.local` con `contratos`).

| Fichero | Qué es |
|---|---|
| `contracts.py` | Tipos pydantic: `InvoiceFacts`, `MasterSnapshot`, `ErpSnapshot`, `Decision`, `Motivo`, `Event`, `Outcome`, enums |
| `schema.sql` | DDL idempotente: `ficheros`, `identidades` (nombres extra de un PDF ya registrado: copias exactas, P0-1), `hechos`, `snapshots`, `decisiones` (con `vigente`), `eventos`, `cache_llm` |
| `db.py` | `conectar`, `init_schema`, `guardar_*`, `registrar_evento`, `traza`, `resumen`. SQL a mano, sin ORM |
| `hashing.py` | `sha256_fichero` (identidad del PDF), `hash_canonico` (linaje) |
| `versions.py` | Versiones de extractor, prompt, norma por defecto. Súbelas cuando cambie el comportamiento |

## Cómo se usa desde otros módulos
```python
from albertitos.core.contracts import InvoiceFacts, Decision, Event, Etapa, EstadoEvento
from albertitos.core import db

conn = db.conectar()
db.init_schema(conn)
db.registrar_evento(
    conn,
    Event(file_id=fid, sha256=sha, etapa=Etapa.EXTRACT, estado=EstadoEvento.OK, latencia_ms=812),
)
```

## Protocolo de cambio
1. Miguel anuncia: campo/tabla, motivo, quién lo consume.
2. Campo nuevo → opcional con default. Nunca renombrar, nunca cambiar tipo, nunca borrar.
3. Test en `tests/test_contracts.py` + fila en `docs/contratos.md` + subir `ESQUEMA_VERSION` si toca `schema.sql`.
4. Los demás hacen `/sync` y `make db` (el DDL es `IF NOT EXISTS`, así que añadir columnas nuevas exige `ALTER TABLE ... ADD COLUMN` al final de `schema.sql`, también idempotente vía `db.init_schema`).

## Lo que estos tipos impiden a propósito
- `InvoiceFacts` no admite campos extra (`extra="forbid"`) ni tiene `resultado`: el LLM no decide.
- `Decision` guarda `fecha_corte`, `hechos_hash`, `maestro_version`, `erp_version`, `norma_version`: cualquier cambio en una entrada deja huella para `reprocess --impacted`.
- `Outcome` rechaza `file_id` que no esté en NFC o que no sea un nombre de PDF: el verificador es exacto.
