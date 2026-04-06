# Admin UI — Vercel Deployment

The `admin-ui/` directory is a standalone Next.js app deployed to Vercel. It acts as a thin authenticated proxy in front of the FastAPI backend on your VPS.

---

## Prerequisites

- A Vercel account (free tier is fine)
- The backend already running on your VPS at `http://178.156.194.155:8000`
- A Google Cloud project with an OAuth 2.0 client (same one used for Google Calendar, or a new one)

---

## Step 1 — Add your Vercel callback URL to Google OAuth

Before deploying, you need to know your Vercel app URL. Vercel assigns a URL in the format `https://<project-name>-<hash>.vercel.app` on first deploy, but you can also pick a custom project name.

**Option A — Deploy first, then update OAuth (recommended)**

1. Complete steps 2–4 below
2. After the first deployment, note your assigned URL (e.g. `https://austin-admin.vercel.app`)
3. Go to [Google Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials)
4. Edit your OAuth 2.0 client
5. Under **Authorized redirect URIs**, add:
   ```
   https://<your-vercel-url>/api/auth/callback/google
   ```
6. Save — the next sign-in attempt will work

**Option B — Use a custom Vercel domain you already know before deploying**

Skip to step 2 and add the redirect URI upfront.

---

## Step 2 — Create the Vercel project

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your GitHub repo (`austin-event-tracker`)
3. Under **Root Directory**, set it to `admin-ui`
4. Framework Preset: **Next.js** (auto-detected)
5. Click **Deploy** — it will fail on the first build because env vars aren't set yet. That's fine.

---

## Step 3 — Set environment variables

In the Vercel dashboard → your project → **Settings → Environment Variables**, add:

| Variable | Value | Notes |
|---|---|---|
| `BACKEND_BASE_URL` | `http://178.156.194.155:8000` | Your VPS backend URL |
| `BACKEND_ADMIN_API_KEY` | (value of `ADMIN_API_KEY` from VPS `.env`) | Kept server-side only |
| `AUTH_SECRET` | random 32-char string | Run: `openssl rand -base64 32` |
| `AUTH_GOOGLE_ID` | OAuth client ID | From Google Cloud Console |
| `AUTH_GOOGLE_SECRET` | OAuth client secret | From Google Cloud Console |
| `ADMIN_ALLOWED_EMAILS` | `you@gmail.com` | Comma-separated list of allowed Google accounts |

Set all variables for **Production**, **Preview**, and **Development** environments.

---

## Step 4 — Redeploy

After setting env vars, go to **Deployments** and click **Redeploy** on the latest deployment (or push a new commit). The build should succeed.

---

## Step 5 — Update Google OAuth redirect URI

Follow Option A from Step 1 above — add your final Vercel URL to the authorized redirect URIs in Google Cloud Console.

---

## Step 6 — Verify sign-in

1. Open your Vercel app URL
2. You should be redirected to `/signin`
3. Click **Sign in with Google** and authenticate with one of the `ADMIN_ALLOWED_EMAILS` accounts
4. You should land on the Dashboard

---

## Manual configuration after VPS redeployment

When you redeploy the backend on your VPS (`docker compose up -d --build`), the new migration `0004_job_schedules` will run automatically on startup. No manual DB steps are needed.

If you want to verify it ran:
```bash
# SSH into your VPS, then:
docker compose exec db psql -U events -d events -c "\d job_schedules"
```

---

## Local development

Copy the example env file and fill in values:
```bash
cd admin-ui
cp .env.example .env.local
# edit .env.local with real values
npm run dev
```

For local use, set `BACKEND_BASE_URL=http://localhost:8000` and run the backend stack with `docker compose up -d`.
