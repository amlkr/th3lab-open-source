# TH3LAB Superinterface (Next.js)

Interfaz de chat minimalista/oscura para conversar con el MCP server TH3LAB en `localhost:3000`.

## Setup

```bash
cd th3lab-superinterface
cp .env.example .env.local
npm install
npm run dev
```

Abrir: `http://localhost:3001`

## Login privado

La app requiere sesión privada si configuras:

- `BASIC_AUTH_USER`
- `BASIC_AUTH_PASS`

Incluye:

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `middleware.ts` (protege todo excepto `/login` y `/api/auth/*`)

## Bridge MCP

Ruta: `app/api/th3lab/route.ts`

- Recibe payload estilo chat (`messages`, `message`, `input`)
- Traduce a llamada MCP para el tool `chat_con_agente_principal`
- Intenta primero JSON-RPC (`tools/call`) y si falla usa fallback REST (`/tools/chat_con_agente_principal`)

Variables:

- `TH3LAB_MCP_URL` (default `http://localhost:3000/mcp`)
- `TH3LAB_MCP_TOOL` (default `chat_con_agente_principal`)
- `TH3LAB_ASK_URL` (default `http://localhost:8090/mcp/world/ask`)
- `TH3LAB_WORLD_ID` (default `amniotic`)
- `TH3LAB_PROJECT_ID` (default `_admin`)

## Deploy en Vercel

1. Importa el repo en Vercel.
2. En el proyecto, configura `Root Directory` = `th3lab-superinterface`.
3. Agrega env vars:
   - `BASIC_AUTH_USER`
   - `BASIC_AUTH_PASS`
   - `TH3LAB_ASK_URL`
   - `TH3LAB_WORLD_ID`
   - `TH3LAB_PROJECT_ID`
4. Deploy.

Importante: `TH3LAB_ASK_URL` debe ser una URL publica (no `localhost`) para que funcione desde Vercel.

## Superinterface self-hosted

Se incluye `@superinterface/react` con wrapper en `components/SuperinterfacePanel.tsx`.
Si configuras:

- `NEXT_PUBLIC_SUPERINTERFACE_API_KEY`
- `NEXT_PUBLIC_SUPERINTERFACE_ASSISTANT_ID`

se activa el provider en modo oscuro.
