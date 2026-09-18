# Albertitos · plan de arquitectura y decisiones

*HackSpain 2026 · reto Maisa "500 Sombras de Alberto" · equipo: Javier Saguar, Miguel Vera, Alejandro Cuevas, Alfonso Jimena, Mónica Fernández*

## 1. Arquitectura

### El problema y para quién
Alberto, administrativo de cuentas a pagar del Banco Miralmar, recibe facturas PDF (algunas escaneadas), un
Excel de proveedores y pedidos con su norma de pagos, y un ERP de 2009 con los asientos contables. Tiene que
decidir para cada factura PAGAR, NO_PAGAR o ESCALAR, sin pagar dos veces y sin pagar lo que un humano debe ver.

### Componentes
*(rellenar: diagrama de cajas; una frase por componente; enlazar a `src/albertitos/<modulo>/CLAUDE.md`)*

- **Motor por lotes (CLI `albertitos`)**: ingest → extract → decide → package.
- **Fuentes**: cliente ERP 2009 (snapshot versionado), loader del Excel (maestro versionado por contenido).
- **Extracción**: PyMuPDF → texto o imagen → LLM con esquema cerrado y caché → validadores deterministas.
- **Norma como código**: `norma_v3.py` (+ `norma_v4.py` el sábado), funciones puras con motivo y evidencia.
- **Estado**: SQLite WAL con `ficheros`, `hechos`, `snapshots`, `decisiones` (historial), `eventos`, `cache_llm`.
- **Consola**: Streamlit de sólo lectura: cola de escalados, traza de una decisión, panel operativo.

### Flujo de datos y estado
*(rellenar: qué entra y sale de cada etapa, qué tabla escribe, qué evento emite)*

### Reparto entre agentes, modelos y personas
- El **modelo** extrae campos (y lee las 29 escaneadas). No decide.
- El **código** (norma versionada) decide, con motivo y evidencia por regla.
- La **persona** (Alberto) resuelve la cola de ESCALAR con la evidencia delante.
- Los **agentes de código** (Claude Code) construyeron el sistema con contratos congelados y hooks; no forman parte del runtime.

### Observabilidad y recuperación
*(rellenar: tabla de eventos, qué señales ve Alberto, qué pasa si el LLM cae — PENDIENTE, circuit breaker, caché, reanudación sin duplicados por sha256)*

### Escala, evolución y coste
*(rellenar desde `docs/benchmark.md`: ficheros/s medidos, hardware, fórmula de coste, límites, qué cambia con emails/Excel/escaneados)*

## 2. ADRs / trade-offs

*(2 a 5. Resumen de 5 líneas de cada uno; el detalle está en `docs/adr/`)*

### ADR-0001 · El LLM extrae; la norma decide
*(resumen)*

### ADR-000N · …
