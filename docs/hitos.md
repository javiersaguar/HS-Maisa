# Hitos y señales de repliegue (hora de Madrid)

| Cuándo | Qué | Dueño |
|---|---|---|
| Vie 18 19:00 | Material inicial = el repo de participantes (web actualizada el 18/09 ~23:00: ya no hay zip de la Caja a las 21:00). `data/caja` es el oficial; `data/caja.sha256` lo fija | Javier |
| Vie 18 23:59 | Contratos aceptados por Miguel · ERP snapshot v1 en BD · maestro cargado · `docs/trampas.md` v1 · LLM real sobre `muestra.txt` | Miguel / Javier / Alfonso |
| Sáb 19 02:00 | **Repliegue 1:** si no hay `outcomes.jsonl` completo y válido, se para todo lo demás hasta que exista | todos |
| Sáb 19 10:00 | Muestra etiquetada por dos personas (`esperado_muestra.csv`) · preguntas a mentores resueltas | Mónica + Alfonso |
| Sáb 19 12:00 | **Repliegue 2:** si > 10 ficheros sin extracción validada → segunda opinión LLM para todos, plantillas aparcadas. Consola con BD real | Alfonso / Alejandro |
| Sáb 19 17:30 | **Entrega de seguro** del lote 1 (`/entrega`) | Miguel |
| Sáb 19 18:00 | Lote 2: `lote-2-sorpresa-v3.2.zip` (40 facturas + ERP actualizado) y **una regla nueva** (la web ya no la llama "norma v4" ni promete un fichero: puede venir en el zip, en el canal o en el Excel). Hashes en el canal. (`/lote2`) | todos |
| Sáb 19 20:00 | **Repliegue 3:** si la consola no enseña una traza, la demo se hace con `trace` en terminal y Alejandro pasa a docs | Alejandro |
| Sáb 19 22:00 | **Repliegue 4:** si el lote 2 no está procesado, se cancela el bonus y todo el equipo va al lote 2 | todos |
| Sáb 19 23:00 | Escenario del "dato en vivo" del domingo ensayado (`reprocess --impacted` < 30 s) · benchmark medido | Miguel |
| Dom 20 02:00 | **Congelación de funcionalidad.** Sólo docs, ensayo y arreglos de NO APTO | todos |
| Dom 20 08:00 | **Entrega final** (`/entrega`): 3 ficheros, repo público, commit anotado en `docs/entregas.log` | Miguel |
| Dom 20 10:30 | **Cierre interno** (colchón). Oficial en la web: **11:00** "cierre de entrega y registro del commit" | — |
| Dom 20 11:00 | La organización clona y registra el commit (hora oficial) | — |
| Dom 20 (hora por confirmar) | Defensa 10 min (2/2/4/2). Bloque 4 pide explícitamente demostrar **timeout, rate limit, respuesta inválida o caída** del proveedor | Alfonso |

## Preguntas para los mentores (hoy, antes de las 23:00)
1. ¿Cuándo es NO_PAGAR frente a ESCALAR? (hipótesis: NO_PAGAR = violación objetiva comprobada en el ERP, p. ej. ya PAGADA)
2. ¿Respecto a qué fecha se evalúa "fecha no futura"? (usamos `ALBERTITOS_FECHA_CORTE`)
3. ¿`outcomes.jsonl` (lote 1) debe reflejar la norma v3 y el ERP v1, o la regla nueva y el ERP actualizado?
5. La regla nueva del sábado: ¿llega como fichero en el zip, como texto en el canal o dentro del Excel? ¿Se aplica también al lote 1?
4. ¿Los PDFs que se declaran "documento de prueba del evaluador" se validan igual que el resto?

Respuestas: *(anotar aquí con hora y quién respondió)*

## Turnos de sueño
*(rellenar: quién duerme cuándo; mientras Miguel duerme no hay merges a main, el trabajo se acumula en ramas)*
