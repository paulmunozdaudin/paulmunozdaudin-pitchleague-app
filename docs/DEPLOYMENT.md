# Deployment

This is written for a small-scale production deploy (a handful of private
leagues) rather than an internet-scale one — matching where the product
actually is right now.

## Guía rápida: Vercel + Railway (recomendado)

Backend + base de datos en [Railway](https://railway.app) (tiene plan
gratuito con horas incluidas), frontend en [Vercel](https://vercel.com)
(gratis para proyectos personales). Unos 15 minutos, todo desde el
navegador, sin usar la terminal.

### 1. Backend + base de datos en Railway

1. Entra en [railway.app](https://railway.app) y conecta tu cuenta de GitHub.
2. **New Project → Deploy from GitHub repo** → elige
   `paulmunozdaudin/paulmunozdaudin-pitchleague-app`.
3. Railway crea un servicio para el repo. Ábrelo → **Settings**:
   - **Root Directory**: `backend`
   - **Start Command** (déjalo vacío la primera vez — el `Dockerfile` ya
     define el comando; solo cámbialo si Railway no detecta el Dockerfile)
4. En el mismo proyecto: **New → Database → Add PostgreSQL**. Railway crea
   un servicio "Postgres" con sus propias variables (`PGHOST`, `PGPORT`,
   `PGUSER`, `PGPASSWORD`, `PGDATABASE`).
5. Vuelve al servicio del backend → pestaña **Variables** → añade:

   ```
   DATABASE_URL=postgresql+psycopg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/${{Postgres.PGDATABASE}}
   AUTH_SHARED_SECRET=<genera uno con: openssl rand -hex 32>
   BACKEND_CORS_ORIGINS=https://TU-APP.vercel.app
   ODDS_PROVIDER=mock
   AI_INSIGHTS_PROVIDER=heuristic
   ENABLE_DEMO_LOGIN=true
   DEFAULT_GAMEWEEK_BUDGET=10000
   ```

   (El prefijo `+psycopg` en `DATABASE_URL` es importante — Railway te da
   `postgresql://`, pero esta app necesita `postgresql+psycopg://`.
   `BACKEND_CORS_ORIGINS` lo terminas de rellenar en el paso 3, cuando ya
   tengas la URL de Vercel.)

6. **Settings → Networking → Generate Domain** para el servicio backend —
   te da una URL pública tipo `https://pitchleague-backend-production.up.railway.app`.
   Guárdala, la necesitas para el frontend.
7. El primer despliegue ya deja la base de datos con el esquema aplicado
   (el `Dockerfile`/comando del backend corre `alembic upgrade head` antes
   de arrancar). Verifica visitando `https://TU-BACKEND.up.railway.app/health`
   → debe responder `{"status":"ok"}`.
8. **Opcional pero recomendado**: repite "New → GitHub repo" en el mismo
   proyecto para crear un segundo servicio con **Root Directory**: `backend`
   y **Start Command**: `python -m app.workers.scheduler` — es el proceso
   que liquida jornadas automáticamente (ver más abajo, "The worker
   process"). Sin él, todo funciona igual pero tendrás que pulsar
   "Liquidar jornada" a mano en el panel admin. Usa las mismas variables
   del paso 5.

### 2. Frontend en Vercel

1. Entra en [vercel.com](https://vercel.com) y conecta tu cuenta de GitHub.
2. **Add New → Project** → importa el mismo repo.
3. En "Configure Project": **Root Directory** → Edit → selecciona `frontend`.
4. En **Environment Variables** añade:

   ```
   NEXT_PUBLIC_API_URL=https://TU-BACKEND.up.railway.app
   NEXTAUTH_URL=https://TU-APP.vercel.app
   NEXTAUTH_SECRET=<el MISMO valor que AUTH_SHARED_SECRET del paso 1>
   ENABLE_DEMO_LOGIN=true
   NEXT_PUBLIC_ENABLE_DEMO_LOGIN=true
   ```

   (`NEXTAUTH_URL` no la sabrás hasta después del primer deploy — pon
   cualquier valor provisional, despliega, copia la URL real que Vercel te
   asigna, y vuelve a "Settings → Environment Variables" para corregirla;
   luego haz **Redeploy**.)
5. **Deploy**. Cuando termine, copia la URL (`https://tu-proyecto.vercel.app`)
   y actualiza `BACKEND_CORS_ORIGINS` en Railway (paso 1.5) y
   `NEXTAUTH_URL` aquí con esa URL real — luego vuelve a desplegar ambos
   (Railway y Vercel redepliegan solos al guardar variables, o hazlo
   manualmente desde su panel).

### 3. Ver la web

Abre `https://tu-proyecto.vercel.app` — verás la landing page. Pulsa
**"Crear liga"** → en el diálogo de inicio de sesión, usa **"Probar en
modo invitado (demo)"** (no necesitas Google ni Discord todavía) → escribe
tu nombre → ya estás dentro, creando tu primera liga.

### 4. Añadir Google/Discord real más adelante (opcional)

Cuando quieras sign-in real:
- Google: [console.cloud.google.com](https://console.cloud.google.com) →
  crear proyecto → "APIs & Services → Credentials → Create OAuth client
  ID" (tipo "Web application") → Authorized redirect URI:
  `https://tu-proyecto.vercel.app/api/auth/callback/google`.
- Discord: [discord.com/developers/applications](https://discord.com/developers/applications) →
  New Application → OAuth2 → añade el mismo tipo de redirect URI con
  `/api/auth/callback/discord`.

Pega los `Client ID`/`Client Secret` de cada uno como
`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` y
`DISCORD_CLIENT_ID`/`DISCORD_CLIENT_SECRET` en Vercel, y pon
`ENABLE_DEMO_LOGIN=false` / `NEXT_PUBLIC_ENABLE_DEMO_LOGIN=false` en ambos
sitios (Vercel y Railway) para retirar el modo invitado. Redeploy.

### Modo demo

`ENABLE_DEMO_LOGIN` (backend) + `NEXT_PUBLIC_ENABLE_DEMO_LOGIN` (frontend)
activan un inicio de sesión sin OAuth: el usuario solo escribe un nombre
(`frontend/src/lib/auth.ts`, provider `Credentials` con id `demo`). Pensado
para probar el producto antes de configurar Google/Discord — dos personas
que escriban el mismo nombre comparten la misma cuenta (no hay contraseña
ni verificación real), así que **no lo dejes activado si vas a compartir
la URL públicamente más allá de tu propia prueba**: apágalo (ambas
variables a `false`) en cuanto tengas OAuth real configurado.

## Recommended shape

| Component | Suggestion | Why |
|---|---|---|
| Frontend | [Vercel](https://vercel.com) | Native Next.js App Router support, zero-config |
| Backend + worker | Any container host (Fly.io, Railway, Render, a plain VM with Docker) | It's a standard Docker image (`backend/Dockerfile`); no platform lock-in |
| Database | Managed Postgres (Supabase, Neon, RDS, Railway) | Automated backups; Supabase also gives you Realtime/Storage for free if you later want to move off the in-process WebSocket manager |

## Environment variables

Copy `.env.example` to `.env` and fill in:

- `AUTH_SHARED_SECRET` **must equal** the frontend's `NEXTAUTH_SECRET` —
  this is the one value both apps need to agree on. Generate with
  `openssl rand -hex 32`.
- `DATABASE_URL` — production Postgres connection string
  (`postgresql+psycopg://...`).
- `BACKEND_CORS_ORIGINS` — the frontend's real origin(s), comma-separated.
- `ODDS_PROVIDER=the_odds_api` + `THE_ODDS_API_KEY` — switch off the mock
  provider once you have a key (see ARCHITECTURE.md#adr-001-odds-provider).
- `AI_INSIGHTS_PROVIDER=anthropic` + `ANTHROPIC_API_KEY` — optional, falls
  back to the free heuristic provider if unset or if a call fails.
- `GOOGLE_CLIENT_ID`/`SECRET`, `DISCORD_CLIENT_ID`/`SECRET` — OAuth app
  credentials. Redirect URI for each: `https://<your-domain>/api/auth/callback/<provider>`.

## Database migrations

```bash
cd backend
alembic upgrade head
```

Run this once against the production database before starting the API
(the Docker Compose `backend` service already does this on every start —
`alembic upgrade head` is idempotent/no-op once applied).

## The worker process

Settlement, odds refresh, and gameweek locking are **not** automatic
unless `app/workers/scheduler.py` is running as its own long-lived process
(`python -m app.workers.scheduler`, or the `worker` service in
`docker-compose.yml`). Without it, an admin can still trigger the same
actions manually from the admin panel (`Actualizar cuotas` /
`Liquidar jornada`), but production should run the worker.

## Checklist before going live

- [ ] Real `AUTH_SHARED_SECRET` (matching on both apps), not the dev default
- [ ] Real Postgres, migrations applied
- [ ] Google/Discord OAuth apps created with the production redirect URIs
- [ ] `THE_ODDS_API_KEY` set (or knowingly staying on the mock provider for a soft launch)
- [ ] Worker process running (odds/settlement won't happen automatically otherwise)
- [ ] `BACKEND_CORS_ORIGINS` set to the real frontend origin
- [ ] HTTPS on both frontend and backend (required for secure OAuth cookies)

## Scaling notes (not needed at current scale, documented for later)

- **Realtime** is a single in-process WebSocket manager
  (`services/realtime.py`) — fine for one backend instance. Running more
  than one API replica means league rooms would split across instances;
  swap in Supabase Realtime or Redis pub/sub behind the same
  `manager.broadcast()` call when that's actually needed.
- **Odds provider rate limits**: The Odds API's free tier is 500
  requests/month. Each `refresh-odds` call is one request per configured
  sport key (currently 4), so budget accordingly or raise
  `DEFAULT_GAMEWEEK_BUDGET`/reduce refresh frequency in the worker.
