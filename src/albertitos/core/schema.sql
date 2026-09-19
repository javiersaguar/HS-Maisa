-- Esquema Albertitos v3 (core/versions.py: ESQUEMA_VERSION). Idempotente: sólo CREATE IF NOT EXISTS. Sin migraciones destructivas.
-- Fuente de verdad única. La consola la lee tal cual; la CLI la escribe.

CREATE TABLE IF NOT EXISTS ficheros (
  sha256       TEXT PRIMARY KEY,               -- identidad real del PDF (idempotencia, caché)
  file_id      TEXT NOT NULL UNIQUE,           -- nombre exacto del PDF en NFC (clave de entrega)
  lote         INTEGER NOT NULL DEFAULT 1,     -- 1 = Caja, 2 = lote sorpresa
  bytes        INTEGER,
  paginas      INTEGER,
  tiene_texto  INTEGER,                        -- 0 → escaneada, hace falta visión
  ingerido_en  TEXT NOT NULL
);

-- Nombres extra de un PDF ya registrado en `ficheros` con otro nombre o en otro lote: copia exacta, misma
-- sha256 (P0-1). `ficheros` guarda el primero y no se toca; cada nombre extra tiene su línea en la entrega
-- de su lote, con la decisión de la sha256 (una sola: hechos y decisiones van por contenido).
CREATE TABLE IF NOT EXISTS identidades (
  file_id      TEXT NOT NULL,                  -- nombre exacto del PDF en NFC (clave de entrega)
  lote         INTEGER NOT NULL,
  sha256       TEXT NOT NULL REFERENCES ficheros(sha256),
  ingerido_en  TEXT NOT NULL,
  PRIMARY KEY (file_id, lote)
);
CREATE INDEX IF NOT EXISTS ix_identidades_sha ON identidades(sha256);

CREATE TABLE IF NOT EXISTS hechos (
  sha256            TEXT NOT NULL REFERENCES ficheros(sha256),
  extractor_version TEXT NOT NULL,
  metodo            TEXT NOT NULL,             -- plantilla | llm_texto | llm_vision | cache
  hechos_json       TEXT NOT NULL,             -- InvoiceFacts serializado
  hechos_hash       TEXT NOT NULL,             -- InvoiceFacts.hash(): entra en el linaje
  creado_en         TEXT NOT NULL,
  PRIMARY KEY (sha256, extractor_version)
);

CREATE TABLE IF NOT EXISTS snapshots (
  tipo        TEXT NOT NULL,                   -- maestro | erp
  version     TEXT NOT NULL,                   -- hash (maestro) o tag v1/v2 (erp)
  datos_json  TEXT NOT NULL,                   -- MasterSnapshot | ErpSnapshot serializado
  creado_en   TEXT NOT NULL,
  PRIMARY KEY (tipo, version)
);

CREATE TABLE IF NOT EXISTS decisiones (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  sha256           TEXT NOT NULL REFERENCES ficheros(sha256),
  file_id          TEXT NOT NULL,
  resultado        TEXT NOT NULL CHECK (resultado IN ('PAGAR','NO_PAGAR','ESCALAR')),
  norma_version    TEXT NOT NULL,
  fecha_corte      TEXT NOT NULL,
  hechos_hash      TEXT NOT NULL,
  maestro_version  TEXT NOT NULL,
  erp_version      TEXT NOT NULL,
  motivos_json     TEXT NOT NULL,
  decidido_en      TEXT NOT NULL,
  vigente          INTEGER NOT NULL DEFAULT 1  -- el reprocesado no borra: marca la anterior como 0
);
CREATE INDEX IF NOT EXISTS ix_decisiones_vigente ON decisiones(file_id, vigente);
CREATE INDEX IF NOT EXISTS ix_decisiones_linaje ON decisiones(norma_version, maestro_version, erp_version, vigente);
-- guardar_decision (UPDATE ... WHERE sha256=? AND vigente=1) y el JOIN de linaje: sin él, cada decisión
-- recorre la tabla entera y el historial la hace crecer con cada reprocesado (ESCALA-10K §5)
CREATE INDEX IF NOT EXISTS ix_decisiones_sha_vigente ON decisiones(sha256, vigente);

CREATE TABLE IF NOT EXISTS eventos (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  ts            TEXT NOT NULL,
  sha256        TEXT,
  file_id       TEXT,
  etapa         TEXT NOT NULL,                  -- ingest | extract | validate | enrich | decide | emit
  estado        TEXT NOT NULL,                  -- ok | error | pendiente | retry | skip
  intento       INTEGER NOT NULL DEFAULT 1,
  latencia_ms   INTEGER,
  tokens_in     INTEGER,
  tokens_out    INTEGER,
  coste_eur     REAL,
  error_codigo  TEXT,                           -- ORA-00600, ERP-429, SES-401, LLM-TIMEOUT...
  detalle       TEXT,
  version       TEXT
);
CREATE INDEX IF NOT EXISTS ix_eventos_fichero ON eventos(file_id);
CREATE INDEX IF NOT EXISTS ix_eventos_etapa ON eventos(etapa, estado);

CREATE TABLE IF NOT EXISTS cache_llm (
  clave           TEXT PRIMARY KEY,             -- sha256 | prompt_version | modelo
  respuesta_json  TEXT NOT NULL,
  tokens_in       INTEGER,
  tokens_out      INTEGER,
  coste_eur       REAL,
  creado_en       TEXT NOT NULL
);
