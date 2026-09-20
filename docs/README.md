# Índice de la documentación

Son 100 documentos y no todos son para lo mismo. Esta página dice **qué leer según a qué vengas**, y qué es
material histórico que se conserva como evidencia pero ya no describe el sistema de hoy.

Estado a domingo 20/09, 10:45: **540 facturas entregadas (468 PAGAR · 62 ESCALAR · 10 NO_PAGAR)**, los dos lotes,
auditoría VERDE y 0 pendientes. Las cifras vivas están en [CIFRAS.md](CIFRAS.md).

## Si vienes a entender el producto en diez minutos

| Documento | Qué es |
|---|---|
| [`../README.md`](../README.md) | El reto, el equipo, el stack, cómo funciona y cómo probarlo |
| [`plan/albertitos_plan.md`](plan/albertitos_plan.md) | El plan de arquitectura y los ADR elegidos; es la fuente del PDF entregado |
| [`ANALISIS-DATOS.md`](ANALISIS-DATOS.md) | Qué hay dentro del material: proveedores, pedidos, ERP, las 540 facturas y sus trampas |
| [`CIFRAS.md`](CIFRAS.md) | Las cifras medidas que se pueden citar, con el comando que las reproduce |
| [`trampas.md`](trampas.md) | El inventario de anomalías del material, una por tipo |

## Si vienes a la defensa o a la demo

| Documento | Qué es |
|---|---|
| [`guion-defensa.md`](guion-defensa.md) | El guion de los 10 minutos, bloque a bloque |
| [`agentes/KIT-DEFENSA.md`](agentes/KIT-DEFENSA.md) | Qué se enseña, en qué orden y con qué comandos |
| [`ESTADO-BACKEND.md`](ESTADO-BACKEND.md) | **Estado al día de hoy**: qué está entregado, qué se enseña, qué repliegue hay y qué queda abierto |
| [`hitos.md`](hitos.md) | Plazos, lo que pasó en cada uno y las preguntas abiertas a los mentores |
| [`demo/ENSAYO-CLON-LIMPIO.md`](demo/ENSAYO-CLON-LIMPIO.md) | El ensayo de la demo desde un clon limpio |

## Si vienes al código

| Documento | Qué es |
|---|---|
| [`adr/`](adr/) | Las 26 decisiones de arquitectura, cada una con su evidencia. Empieza por el [índice](adr/README.md) |
| [`contratos.md`](contratos.md) | Los contratos congelados entre módulos |
| [`api/`](api/) | El contrato HTTP de la consola: [bonus](api/bonus.md), [chat](api/chat.md), [confianza](api/confianza.md), [demo privada](api/demo-privada.md) |
| [`benchmark.md`](benchmark.md) | Tiempos y coste medidos del pipeline |
| [`../CLAUDE.md`](../CLAUDE.md) y los `CLAUDE.md` de cada módulo | Las reglas de trabajo del repo |

## Material de trabajo, que se conserva como evidencia

Esto **no** describe el sistema de hoy: es el rastro de cómo se construyó en 36 horas. Se conserva porque la
trazabilidad del proceso también se defiende, y porque varios ADR lo citan.

| Carpeta o fichero | Qué contiene |
|---|---|
| [`agentes/BITACORA.md`](agentes/BITACORA.md) | El canal del equipo, en orden y con hora. Es el diario de las 36 h |
| `agentes/PLAN-01.md` … `PLAN-15.md` | Los repartos de trabajo por ciclo. El último es [PLAN-15](agentes/PLAN-15.md), la clave de la demo |
| [`agentes/partes/`](agentes/partes/) | Los partes de cierre de cada ciclo, con lo medido |
| `agentes/ENSAYO-*.md`, `agentes/CONTRASTE-TOTAL.md`, `agentes/MUESTRA-CONTRASTE.md` | Ensayos y contrastes con sus números |
| [`agentes/lote2/`](agentes/lote2/) | El lote 2: la [hipótesis a ciegas](agentes/lote2/HIPOTESIS.md) y el [informe real](agentes/lote2/EXTRACCION.md) |
| [`revision/`](revision/) | Las revisiones externas y sus resúmenes |
| [`PLAN-SABADO.md`](PLAN-SABADO.md), [`PLAN-MONICA.md`](PLAN-MONICA.md), [`reparto-backend.md`](reparto-backend.md) | Planificación de los días del reto |
| [`entregas.log`](entregas.log) | Cada entrega publicada, con su hash y su reparto |

## Cómo se comprueba que esto no miente

```bash
uv run python scripts/enlaces_check.py   # ningún enlace relativo roto
uv run python scripts/cifras_check.py    # ninguna cifra obsoleta en los documentos de cabecera
make check                               # 718 tests
```
