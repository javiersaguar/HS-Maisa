# Estado del proyecto y lo que falta · sábado 19/09, 14:30 (puesta en común)

La versión anterior, con cada P0 tachado según se cerraba, está en el historial de git (`git log -p docs/ESTADO-BACKEND.md`).

## 1 · Dónde estamos, en una frase por área
| Área | Estado | Evidencia |
|---|---|---|
| **Entrega del lote 1** | ✅ Publicada `232bb76`: 500 líneas, **438/53/9**, auditoría VERDE | `docs/entregas.log` · `outcomes.jsonl` `1ec4be206089` |
| **Código en `main`** | ✅ `javier/ingesta` = `main` + arreglos de Windows. **513 tests en verde** en Linux | `make check` |
| **Riesgos de NO APTO del lote 2** | ✅ Cerrados los cinco: copias exactas (P0-1), nombre repetido (P0-5, ya en `main`), auditoría como puerta, `--aceptar-rojo` y contingencia ESCALAR (ADR-0009) | tests + ensayos |
| **Lote 2 a las 18:00** | ✅ Ensayado con `main`: **14,2 s** de punta a punta sin visión nueva; nombre repetido en 39 s | `CHULETA-LOTE2.md` · `scripts/ensayo/` |
| **Fuentes con otra forma** | ✅ El Excel se lee por nombre de columna; una hoja nueva que parezca la regla se avisa | `ENSAYO-FUENTES.md` (J2) |
| **Resiliencia (10 pts)** | ✅ Demo sin red en 3 s, breaker, `--aceptar-rojo`, contingencia. Respaldo de visión medido: **falta la línea en `.env`** | `KIT-DEFENSA.md` · `RESPALDO-VISION.md` |
| **Escala y coste (25 pts)** | ✅ Cada cifra con su fuente y su comando; el dato en vivo, en **< 0,6 s** | `docs/CIFRAS.md` · `scripts/dato_en_vivo.py` |
| **Trazabilidad (20 pts)** | ✅ `trace` legible (hechos → maestro → ERP → duplicado → reglas), reintentos del ERP por snapshot | Miguel + G2 |
| **Bonus (+10)** | ✅ Calendario y remesa: **438 pagos, 2.428.159,06 €**, en solo lectura | `docs/BONUS.md` · ADR-0012 |
| **Consola** | 🟠 Alejandro la ha rehecho en **Next.js**, con un puente HTTP de solo lectura. Funciona contra la BD real, pero **necesita Node y pnpm** en el portátil de la defensa y **no tiene ADR** (el stack decía Streamlit). `make console` sigue lanzando el Streamlit viejo | `src/albertitos/console/CLAUDE.md` |
| **La norma (Mónica)** | 🔴 **Muestra etiquetada: 0 de 21.** Ninguna respuesta de los mentores anotada. Tres políticas abiertas | abajo |
| **Plan PDF (35 pts, Alfonso)** | 🔴 **Sin tocar en 12 h.** Tiene 4 ADRs más un hueco `ADR-000N · …`; hay 12 ADRs escritos | `docs/plan/albertitos_plan.md` |
| **Guion de la defensa (Alfonso)** | 🔴 **Sin tocar desde el andamiaje** (18 h). Hay presentación v1 (`presentaciones/`, 13,5 MB) y la chuleta del bloque 4 | `docs/guion-defensa.md` |
| **Windows** | ✅ Los 8 fallos que vio Miguel y 5 de codificación que salieron después, arreglados: **513 en verde en `windows-latest`, sin `PYTHONUTF8`**. El CI de Windows se lanza a mano o subiendo a una rama `windows-check/**` | `.github/workflows/windows.yml` |

**En resumen:** el sistema está terminado y ensayado. Lo que queda es **lo que no puede hacer un agente**: que la norma
se valide contra personas y mentores, y que el PDF y el guion cuenten lo que ya existe.

## 2 · Lo que falta, por orden de lo que nos cuesta si no se hace
### 🔴 A · Validar la norma, antes de las 18:00 · Mónica (+ Alfonso para la muestra)
La validación es binaria contra una referencia privada. Tenemos 438/53/9 **sin que ninguna persona lo haya comprobado**.
1. **Muestra etiquetada a ciegas** (0 de 21): menos de una hora. Después, `scripts/comparar_muestra.py` y cada
   discrepancia con su dueño: la regla, el dato o la etiqueta. La tercera lectura del agente H2 está preparada.
2. **Mentores**, con los números de I2 (`MAPA-POLITICAS.md`):
   - **frontera NO_PAGAR/ESCALAR**: **35 líneas** en juego, 28 de ellas fuera de la muestra. Es la que más pesa;
   - **texto que ordena la decisión**: 6 líneas;
   - **¿el lote 1 final va con la regla nueva y el ERP v2?** (P0-2): sin respuesta desde el viernes;
   - **pedido ANULADO en el Excel**: hoy no cambia nada, porque la v3 no lee `Pedido.estado` (J2, J4);
   - **copias exactas**: ¿también se escala el original del lote 1? (R3).
3. Las respuestas, **literales, con hora**, en `docs/hitos.md` («Respuestas»). Y los cambios de norma, **subiendo la
   etiqueta** (`v3.1`), para que el linaje los vea solos.

### 🔴 B · El PDF del plan (35 pts), antes de la entrega del domingo 08:00 · Alfonso
- Elegir **2-5 ADRs** de los 12. Mi propuesta: 0001 (el LLM extrae, la norma decide), 0006 (linaje), 0009
  (contingencia), 0011 (una lectura reconciliada no se paga sola) y 0003 o 0005.
- Quitar el hueco `ADR-000N · …` y comprobar las cifras con `uv run python scripts/cifras_check.py`.
- `make plan-pdf` y revisarlo impreso. Entra en la entrega final: es uno de los tres ficheros.

### 🟠 C · La defensa: ensayo a las 15:00 · Alfonso (+ todos)
- **Guion 2/2/4/2** al día con lo que existe: consola, traza, bloque 4 (`KIT-DEFENSA.md`), dato en vivo y bonus.
- **Kit de las 13:37** instalado en su portátil y la chuleta cronometrada allí.
- **Consola: decidir hoy cuál se enseña.** Next.js sólo si arranca en su portátil sin red en la sala (`pnpm install`
  hecho antes). Si no, `trace` en terminal: es el repliegue previsto. Si Next se queda, Alejandro escribe su ADR.

### 🟡 D · Operación · Javier
- **Antes de las 17:30:** `ALBERTITOS_MODELO_VISION_FALLBACK=deepseek-v4-flash` en `.env`.
- **18:00:** `CHULETA-LOTE2.md`. Lanzar el extract de las escaneadas en cuanto el material esté verificado (40
  escaneadas son 6-10 min). Si aparece un nombre repetido, ya no hay que mergear nada: P0-5 está en `main`.
- **Después del lote 2:** republicar con `make publicar`, rehacer el kit y, si hay tiempo, la prueba de Jev
  (`ANALISIS-JEV.md`: fuera del camino que decide).

### 🟢 E · Deseable
- `make console` lanza el Streamlit viejo: que apunte a lo que se enseñe (Alejandro).
- La presentación de 13,5 MB está en git y cada versión suma otro tanto: mejor fuera del repo, o sólo la final.
- Jev: ADR-0013, lo integremos o no.

## 3 · Calendario que queda
| Hora | Qué | Quién |
|---|---|---|
| **15:00** | Ensayo de la defensa en el portátil de Alfonso (kit 13:37) | Alfonso + todos |
| **antes de 17:00** | Muestra 21/21 · respuestas de los mentores · cambios de norma, si los hay | Mónica (+ Alfonso) |
| 17:30 | Entrega de seguro: ya está publicada. Sólo se republica si cambia la norma | Javier / Miguel |
| **18:00** | Lote 2 y regla nueva (`norma_v4`) | Javier → Mónica → Miguel |
| 20:00 | Repliegue de la consola: si no enseña una traza, `trace` en terminal | Alejandro |
| 22:00 | Lote 2 publicado; si no, se cancela lo opcional | todos |
| 23:00 | Dato en vivo ensayado (ya medido: < 0,6 s) | — |
| **02:00** | Congelación | todos |
| **08:00** | Entrega final: `outcomes.jsonl` + `outcomes_lote2.jsonl` + `albertitos_plan.pdf` | Javier / Miguel |
