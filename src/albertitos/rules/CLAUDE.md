# rules/ — la norma como código · dueña: Mónica

| Fichero | Qué hace | Estado |
|---|---|---|
| `norma_v3.py` | 6 reglas = 6 funciones `regla_N(hechos, maestro, erp, ctx) -> Motivo` + `decidir()` → `Decision` | primera pasada; **validar** |
| `norma_v4.py` | v3 + R7 (moneda, hipótesis de divisas hasta que se publique la regla): sin tipo en `TIPOS_CAMBIO`, la divisa escala con su motivo; con tipo, R2 y R5 comparan convertido. ADR-0022 (Miguel, M3) | hecho; **Mónica revisa** |
| `__init__.py` | `REGISTRO = {"v3": norma_v3, "v4": norma_v4}` | hecho |

## Tareas de Mónica
1. **Muestra etiquetada** (con Alfonso, sábado 10:00): rellenar `data/fixtures/esperado_muestra.csv` a mano, cada uno por su cuenta, y comparar. Donde no coincidáis, es una pregunta para el mentor.
2. Revisar cada regla contra `docs/trampas.md`: ¿qué hace la R3 con `FA-5590_ofimática.pdf` (IVA 16 %)? ¿Qué hace la R5 con los 9 asientos PAGADA? ¿Y con dos PDFs del mismo pedido (`marcar_duplicados` en pipeline)?
3. `tests/test_rules.py`: tabla por regla con caso ok / ko / frontera (±0,01, fecha = corte, PAGADA, IBAN con espacios).
4. Decidir con el mentor la frontera NO_PAGAR vs ESCALAR y dejarla escrita en un ADR (`/adr frontera-no-pagar-escalar`).
5. Sábado 18:00: `norma_v4.py` nueva (copiar v3 y cambiar sólo lo que cambie), tests para lo nuevo, registrar en `REGISTRO`.

## Reglas del módulo
- Determinista y puro: sin I/O, sin red, sin `date.today()` (hook lo bloquea). `ctx.fecha_corte` es la única fecha "de hoy".
- Cada `Motivo` lleva `detalle` que Alberto entienda y `evidencia` con los valores comparados (aparecen en la traza y en la consola).
- `decidir` sólo ve `InvoiceFacts` tipado, nunca el texto del PDF. Si te falta una señal, pídesela a extract/ como `Aviso`.
- Tolerancias con `Decimal("0.01")`. Nunca `float`.
- Ante duda razonable → ESCALAR. Un ESCALAR de más cuesta minutos a Alberto; un PAGAR de más cuesta dinero (y la validación).
