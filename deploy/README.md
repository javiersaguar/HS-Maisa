# Demo pública (ADR-0023): pasos para Javier

La consola está en Vercel; el puente y el chat, en Render. Quien abra `https://albertitos.vercel.app` no necesita nada.

## Una vez (unos 15 minutos, casi todo esperando al build)
1. **Render:** entra con GitHub en https://render.com, luego *New → Blueprint*, elige `javiersaguar/HS-Maisa` (rama `main`).
   Lee `render.yaml` y propone dos servicios: `albertitos-puente` y `albertitos-chat`.
2. Te pedirá **`ALBERTITOS_LLM_API_KEY`** para el chat: pega la clave del gateway (la de tu `.env`). Es el único
   secreto; no va al repo.
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
