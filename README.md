# Albertitos · HackSpain 2026 · Maisa track "500 Sombras de Alberto"

**In short (English).** Alberto does accounts payable at a bank. He gets invoice PDFs (some scanned, some with
text that tries to give orders), a messy Excel of suppliers and purchase orders, and a 2009 ERP. For each invoice
the system decides **PAGAR / NO_PAGAR / ESCALAR** (pay / don't pay / send to a human).

The thesis: **the LLM extracts, the rules decide.** The model only fills a closed schema of facts; a versioned
set of rules in code makes the decision and records why, with evidence, so any decision can be replayed.

We delivered **540 invoices decided: 468 PAGAR, 62 ESCALAR, 10 NO_PAGAR**, both batches, audited, with 0 pending.
468 of the first 500 were read by deterministic templates at no model cost. A data change reprocesses only what it
touches, not the whole set.

Try it: **[albertitos.vercel.app](https://albertitos.vercel.app)** (read-only console, trace of any invoice and a
chat over the decisions; it asks for a shared key, see [Cómo verlo](#cómo-verlo)).

---

## El stack

### Lenguajes y base
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Bash](https://img.shields.io/badge/Bash-4EAA25?style=for-the-badge&logo=gnubash&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-WAL-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![uv](https://img.shields.io/badge/uv-DE5FE9?style=for-the-badge&logo=uv&logoColor=white)

### Motor y extracción
![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?style=for-the-badge&logo=pydantic&logoColor=white)
![Typer](https://img.shields.io/badge/Typer-CLI-0B7285?style=for-the-badge&logo=typer&logoColor=white)
![PyMuPDF](https://img.shields.io/badge/PyMuPDF-1.26-B5121B?style=for-the-badge)
![openpyxl](https://img.shields.io/badge/openpyxl-Excel-217346?style=for-the-badge)
![httpx](https://img.shields.io/badge/httpx-0.28-1F6FEB?style=for-the-badge)
![Anthropic SDK](https://img.shields.io/badge/Anthropic%20SDK-LLM-D97757?style=for-the-badge&logo=anthropic&logoColor=white)

### Consola
![Next.js](https://img.shields.io/badge/Next.js-16-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)
![Recharts](https://img.shields.io/badge/Recharts-3-FF6384?style=for-the-badge)
![Streamlit](https://img.shields.io/badge/Streamlit-consola%20interna-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)

### Calidad y despliegue
![pytest](https://img.shields.io/badge/pytest-718%20tests-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)
![Ruff](https://img.shields.io/badge/Ruff-lint%20%2B%20format-D7FF64?style=for-the-badge&logo=ruff&logoColor=black)
![Playwright](https://img.shields.io/badge/Playwright-UI-2EAD33?style=for-the-badge)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-CI-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Render](https://img.shields.io/badge/Render-puente%20y%20chat-46E3B7?style=for-the-badge&logo=render&logoColor=black)
![Vercel](https://img.shields.io/badge/Vercel-consola-000000?style=for-the-badge&logo=vercel&logoColor=white)

Sin ORM, sin cola, sin framework de agentes: SQLite en WAL, funciones puras para la norma y la CLI como única
puerta de escritura. Lo que no está aquí, no está en el proyecto.

## El equipo
| Persona | De qué se ocupó |
|---|---|
| Javier Saguar ([@javiersaguar](https://github.com/javiersaguar)) | Fuentes (ERP y Excel), extracción, entrega y despliegue |
| Miguel Vera ([@Mveradc](https://github.com/Mveradc)) | Contratos, pipeline, linaje y las decisiones de norma del lote 2 |
| Alejandro Cuevas ([@DRO98](https://github.com/DRO98)) | La consola web |
| Alfonso Jimena ([@AlfonsoJimena](https://github.com/AlfonsoJimena)) | Documentación, plan de arquitectura y defensa |
| Mónica Fernández ([@monicafdezlortal](https://github.com/monicafdezlortal)) | La norma de pagos y su validación |

## El reto
Llegan **540 facturas en PDF**: algunas escaneadas, algunas que en su propio texto piden «escalar», «ignorar el
NIF» o «pagar el total impreso», y varias con trampas de verdad (una cuenta bancaria cambiada, un pedido ya pagado,
totales que no cuadran). Hay que cruzarlas con un Excel de proveedores y pedidos y con un ERP de 2009 que se cae,
tarda y devuelve errores de Oracle.

Por cada factura hay que decidir **PAGAR, NO_PAGAR o ESCALAR**, sin pagar dos veces y sin pagar lo que una persona
debería mirar antes. La validación del reto es binaria: o están bien las 540, o no hay premio.

## Cómo funciona
![Diagrama de la arquitectura: las facturas, el Excel y el ERP entran en una SQLite; de ahí salen los pasos de leer, decidir, revisar y entregar, y encima de esa base están la consola, el chat y el calendario, que sólo leen.](docs/img/arquitectura.png)

*Las tres fuentes entran en una sola base de datos. El programa recorre los pasos y guarda lo que hace en cada uno. La consola, el chat y el calendario viven encima y no deciden nada: sólo miran.*

- **Motor por lotes:** una CLI que va del PDF a la entrega paso a paso y deja un evento en cada uno.
- **Fuentes:** el ERP se descarga entero a un *snapshot* versionado, con sus reintentos; el Excel y los CSV se leen
  por nombre de columna y forman un maestro versionado por el hash de su contenido. Nada se consulta por factura.
- **Extracción:** seis plantillas deterministas resuelven la mayoría; lo demás va al modelo con un esquema cerrado,
  caché por `sha256` y validadores. Las escaneadas se leen dos veces y, si no coinciden, se desempatan.
- **Norma:** funciones puras que devuelven motivo y evidencia por regla. Ninguna mira el reloj: la fecha de corte es
  un parámetro que se guarda con la decisión, así que una decisión de ayer se puede reproducir hoy.
- **Estado:** una SQLite con los ficheros, los hechos, los snapshots, el historial de decisiones y los eventos. De
  ahí salen la traza, la idempotencia y el reprocesado.
- **Producto:** una consola web de sólo lectura (panel, ficheros, traza, calendario de pagos) y un chat que
  consulta las decisiones con herramientas cerradas. Ninguno de los dos decide ni escribe.

**Qué pasa cuando algo falla.** Si el modelo se cae, la factura queda PENDIENTE y la entrega se niega a salir
incompleta: nunca se paga sin hechos validados. Al volver, la misma pasada reanuda. Si cambia un dato de la Caja o
del ERP, sólo se recalcula lo que ese dato toca, y el resto conserva la versión con la que se decidió.

**Qué hacemos con las facturas que intentan darnos órdenes.** El texto de una factura es un dato, nunca una
instrucción: la frase se guarda como evidencia y la decisión la toma la norma. Las 31 que lo intentan acaban en
ESCALAR o NO_PAGAR, y en la traza se ve por qué regla.

## Lo que sacamos
Cifras medidas, con sus condiciones y sus comandos en [`docs/CIFRAS.md`](docs/CIFRAS.md):
- **540 de 540** extraídas y decididas, 0 pendientes. Entrega auditada: **468 PAGAR · 62 ESCALAR · 10 NO_PAGAR**
  (lote 1: 445/46/9 · lote 2: 23/16/1, cada lote con su norma y su ERP).
- **468 de las 500** primeras salen por plantilla determinista (93,6 %), a 3 ms de mediana y **0 € de coste marginal**:
  los modelos que usamos van en una suscripción plana. El coste es el fijo: 399 €/mes, 0,0399 € por factura con
  10.000 al mes.
- **Pasada completa en frío:** 500 facturas en 204 s (2,5 ficheros/s). Con la caché llena, 15 s y 0 tokens.
- **Reprocesar un cambio del ERP:** 2 de 500 facturas en 0,04 s, porque el linaje sabe cuáles dependían de él.
- **Camino determinista a 10.000 facturas:** 57,1 s, midiendo por etapas y sin el modelo.

## Cómo verlo
**La demo pública:** [albertitos.vercel.app](https://albertitos.vercel.app). Pide una clave compartida, porque
detrás hay un modelo de verdad y no queremos que cualquiera lo gaste; pídesela al equipo. Con ella se ven las 540
decisiones, la traza de cada una, el calendario de pagos y el chat.

**En local**, con el repositorio clonado:
```bash
./bootstrap.sh                                      # uv, dependencias y verificación de la Caja
make erp-fast                                       # en otra terminal: el ERP de 2009 en :8009
uv run albertitos run --fecha-corte 2026-09-18      # ingest → extract → decidir → empaquetar
uv run albertitos trace F26-2201_transportes.pdf    # por qué esa factura escala, paso a paso
bash scripts/demo.sh arrancar                       # consola, puente y chat en http://localhost:3002
```

## Para seguir leyendo
- [`docs/README.md`](docs/README.md) · **el índice de los 100 documentos**, ordenados por a qué vienes: producto,
  defensa, código o el material de trabajo que se conserva como evidencia.
- [`docs/adr/`](docs/adr/) · las decisiones, con alternativas, consecuencias y evidencia. Las cinco que más se
  preguntan están resumidas en el plan.
- [`docs/plan/albertitos_plan.md`](docs/plan/albertitos_plan.md) · arquitectura y ADRs; es el PDF que se entrega.
- [`docs/ESTADO-BACKEND.md`](docs/ESTADO-BACKEND.md) · qué está hecho y qué falta, con dueño.
- [`CLAUDE.md`](CLAUDE.md) · cómo trabaja el equipo y qué hay en cada módulo.

## Límites, dichos claro
- **Los datos son sintéticos**, los del reto. Los IBAN de la Caja tienen forma de IBAN pero no pasan el dígito de
  control: el calendario de pagos es un borrador y lo dice, no una orden bancaria.
- **Las facturas en otra divisa se escalan.** No hay tabla de tipos de cambio en el material, y preferimos que lo
  mire una persona antes que convertir con un tipo inventado.
- **La clave de la demo es compartida**, no un sistema de usuarios: sirve para que nadie de fuera gaste el modelo
  ni suba ficheros, y así hay que entenderla.
- **No sabemos si acertamos las 540.** La referencia del reto es privada: aquí no hay ninguna verdad etiquetada,
  sólo lo que la norma decide y el porqué de cada decisión.

Este repositorio es la solución. **No es el repositorio de entrega**
([HS-Maisa-Entrega](https://github.com/javiersaguar/HS-Maisa-Entrega)), que sólo lleva `outcomes.jsonl`,
`outcomes_lote2.jsonl` y `albertitos_plan.pdf`.
