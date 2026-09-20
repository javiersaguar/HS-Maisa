# Demo pública (ADR-0023): pasos para Javier

La consola está en Vercel; el puente y el chat, en Render. Sin clave configurada se conserva la demo de consulta. Con la misma clave privada en ambos servicios, la consola pide acceso y el puente habilita una bandeja temporal (ADR-0024).

## Una vez (unos 15 minutos, casi todo esperando al build)
1. **Render:** entra con GitHub en https://render.com, luego *New → Blueprint*, elige `javiersaguar/HS-Maisa` (rama `main`).
   Lee `render.yaml` y propone dos servicios: `albertitos-puente` y `albertitos-chat`.
2. Te pedirá **`ALBERTITOS_LLM_API_KEY`** para el chat: pega la clave del gateway (la de tu `.env`). Es un secreto; no va al repo. Para las subidas del modo privado también hace falta en el puente.
3. *Apply*. El primer build tarda unos 5 minutos por servicio. Cuando estén en verde, copia sus dos URL
   (`https://albertitos-puente-XXXX.onrender.com` y `https://albertitos-chat-XXXX.onrender.com`).
4. Comprueba: `curl https://albertitos-puente-XXXX.onrender.com/salud` y `…chat…/chat/salud` → `"modelo_disponible": true`.
5. **Vercel** (Settings → Environment Variables), sólo estas tres, y *Redeploy*:
   - `NEXT_PUBLIC_USE_MOCK=false`
   - `NEXT_PUBLIC_API_URL=https://albertitos-puente-XXXX.onrender.com`
   - `NEXT_PUBLIC_CHAT_URL=https://albertitos-chat-XXXX.onrender.com`

   **Borra de Vercel todas las demás** (`ANTHROPIC_API_KEY`, `ALBERTITOS_*`, `ENTREGA_REPO`…): no las usa y son secretos.
6. Abre el enlace en incógnito, desde el móvil con datos y desde otro navegador. Si el URL de Vercel cambiase, pon el
   nuevo en `ALBERTITOS_CHAT_ORIGENES` del servicio del chat.

## Cada vez que se publique una entrega nueva (p. ej. el lote 2)
```bash
uv run python scripts/exportar_demo_db.py      # dist/albertitos.db → deploy/demo.db (sin caché del LLM)
git add deploy/demo.db && git commit -m "deploy: demo pública con la entrega de las HH:MM" && git push
```
Render redespliega solo los dos servicios (unos 3 minutos).

## Si algo falla
- **La consola dice «Sin conexión»:** el plan gratuito duerme tras 15 minutos. El primer acceso lo despierta; la consola reintenta sola.
- **Render caído del todo:** en Vercel, `NEXT_PUBLIC_USE_MOCK=true` y *Redeploy*: datos de ejemplo, etiquetados como tales.
- **Demo en la defensa:** la consola local (`docs/agentes/KIT-DEFENSA.md`, «Grabar la demo en local») no depende de nada de esto.

## Levantarlo todo (local) y mantener despierta la pública
```bash
bash scripts/demo.sh arrancar    # puente con bandeja + chat + consola compilada; deja los PID y los logs en dist/demo/
bash scripts/demo.sh estado      # qué responde cada uno, local y público, y cuántas facturas sirve cada BD
bash scripts/demo.sh parar       # para los tres (también lo que quedara de un arranque anterior)
bash scripts/demo.sh despertar   # pings a Render cada 10 min para que no se duerma (Ctrl+C para salir)
```
Puertos por defecto: consola 3002, puente 8000, chat 8101 (el 3000 y el 8001 suelen estar ocupados por contenedores
de otros proyectos). Se cambian con `PUERTO_CONSOLA=… PUERTO_PUENTE=… PUERTO_CHAT=… bash scripts/demo.sh arrancar`.
La ventana del chat es de 12 h desde el arranque; con `CHAT_HASTA=2026-09-20T14:00` se fija a mano.
**La consola se abre por `http://localhost:3002`**, no por `127.0.0.1`.

Sin portátil encendido, la demo pública se mantiene despierta sola con el workflow
`.github/workflows/despertar-demo.yml`: cada 10 minutos el domingo de 07:00 a 15:00 (Madrid). Fuera de esa ventana
no corre, porque el plan gratuito de Render tiene 750 horas de instancia al mes en total. Para despertarla en otro
momento: pestaña **Actions** del repo → *despertar la demo pública* → **Run workflow**.

## Demo privada y subidas (PLAN-15, ADR-0024)

Integrar primero la puerta del backend (A1) y la pantalla de acceso (A2).
En **Environment** de los dos servicios Render configurar la **misma**
`ALBERTITOS_CLAVE_DEMO`, generada aleatoriamente (al menos 32 bytes).
No pegarla en tickets, logs, capturas, commits, Vercel ni variables NEXT_PUBLIC.
Guardar y redesplegar ambos servicios. El chat necesita además su clave del gateway;
el puente necesita `ALBERTITOS_LLM_API_KEY` para extraer los PDF nuevos.
Permitir la URL exacta de Vercel en `ALBERTITOS_CONSOLA_ORIGENES` y
`ALBERTITOS_CHAT_ORIGENES`.

El arranque del puente sin clave sirve deploy/demo.db de sólo lectura. Con clave
crea una copia SQLite en un directorio temporal nuevo y habilita --bandeja.
El original nunca se modifica. Reiniciar borra de la vista todas las pruebas:
**espacio de pruebas: lo que subas se borra cuando el servidor se reinicia**.
No hay disco persistente ni sincronización con la BD del chat, que sigue
consultando la instantánea publicada. La bandeja y sus resultados se ven en la consola.

`ALBERTITOS_BANDEJA_MAX=40` limita las admisiones por proceso y arranque.
Cero impide admitir archivos; valores negativos o no enteros impiden arrancar.
Siguen vigentes 20 PDF por petición y 10 MB por PDF. Las admisiones fallidas
también consumen cupo; los rechazos por formato y los rechazos mientras hay
un trabajo en curso no lo consumen. El cupo vuelve a empezar al reiniciar.
No es un límite global de gasto ni de varias réplicas: mantener una sola instancia.

### Comprobación antes de darlo por listo
- Salud pública en ambos servicios: requiere_clave=true.
- Consulta sin clave o con clave incorrecta: 401; con clave: 200.
- Preflight desde Vercel permite X-Albertitos-Clave.
- Desde la consola subir e02_P002.pdf y verificar el resultado ESCALAR y su traza.
  La copia exacta reutiliza los hechos existentes y no demuestra extracción de un PDF nuevo.
- Verificar aviso temporal, contador y rechazo 409 al superar el cupo.
- Ningún ensayo escribe JSONL/PDF ni ejecuta package/publicar sobre la entrega.

### Rotación y marcha atrás
Rotar reemplazando la variable en **ambos** servicios y redesplegándolos;
las sesiones con la clave anterior recibirán 401.
A las 10:15 (Madrid) del 20/09, si falta alguna comprobación, eliminar
**sólo ALBERTITOS_CLAVE_DEMO** en ambos servicios y redesplegar.
Esperar al despliegue efectivo: no prometer reversión instantánea.
Comprobar requiere_clave=false en ambas saludes, consultas sin clave operativas
y POST /inbox rechazado con 409 (con un origen permitido).
La consola A2 debe volver al modo sin puerta al leer la salud.
Los JSONL y el PDF ya publicados no forman parte de este despliegue.

### Pruebas de A3 (sin red ni modelo)
```bash
uv run pytest -q deploy/test_auth_deploy.py
uv run ruff check deploy/iniciar_puente.py deploy/test_auth_deploy.py
make check
```
