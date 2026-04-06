# Admin UI — Vercel Deployment

The `admin-ui/` directory is a standalone Next.js app deployed to Vercel. It acts as a thin authenticated proxy in front of the FastAPI backend on your VPS.

---

## Prerequisites

- A Vercel account (free tier is fine)
- The backend already running on your VPS at `http://178.156.194.155:8000`
- A Google Cloud project with an OAuth 2.0 client (same one used for Google Calendar, or a new one)

---

## Step 1 — Redeploy the VPS backend

Pull the latest code and rebuild. Migration `0004` (job_schedules table) runs automatically on startup.

```bash
# SSH into your VPS, then:
cd /path/to/austin-event-tracker
git pull
docker compose up -d --build
docker compose logs -f app
# Wait until you see "migrations_applied" and "scheduler_started"
```

To verify the migration ran:
```bash
docker compose exec db psql -U events -d events -c "\d job_schedules"
```

---

## Step 2 — Create the Vercel project

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your GitHub repo (`austin-event-tracker`)
3. Under **Root Directory**, set it to `admin-ui`
4. Framework Preset: **Next.js** (auto-detected)
5. Click **Deploy** — the first build will fail because env vars aren't set yet. That's fine.

---

## Step 3 — Set environment variables

In the Vercel dashboard → your project → **Settings → Environment Variables**, add all of the following for **Production**, **Preview**, and **Development**:

| Variable | Value | How to get it |
|---|---|---|
| `BACKEND_BASE_URL` | `http://178.156.194.155:8000` | Your VPS backend URL |
| `BACKEND_ADMIN_API_KEY` | (value of `ADMIN_API_KEY` from VPS `.env`) | Copy from `.env` on the VPS |
| `AUTH_SECRET` | random 32-char string | Run: `openssl rand -base64 32` |
| `AUTH_GOOGLE_ID` | OAuth client ID | From Google Cloud Console |
| `AUTH_GOOGLE_SECRET` | OAuth client secret | From Google Cloud Console |
| `ADMIN_ALLOWED_EMAILS` | `you@gmail.com` | Comma-separated list of allowed Google accounts |

---

## Step 4 — Add your Vercel URL to Google OAuth

After the project is created in step 2, note your assigned Vercel URL (e.g. `https://austin-admin.vercel.app`).

1. Go to [Google Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials)
2. Edit your OAuth 2.0 client
3. Under **Authorized redirect URIs**, add:
   ```
   https://<your-vercel-url>/api/auth/callback/google
   ```
4. Save

---

## Step 5 — Redeploy on Vercel

After setting env vars and updating the OAuth redirect URI:

1. In the Vercel dashboard → **Deployments**
2. Click **Redeploy** on the latest deployment
3. The build should succeed this time

---

## Step 6 — Verify sign-in

1. Open your Vercel app URL
2. You should be redirected to `/signin`
3. Click **Sign in with Google** and authenticate with one of the `ADMIN_ALLOWED_EMAILS` accounts
4. You should land on the Dashboard with **Jobs** and **Digests** in the nav

---

## Local development

```bash
cd admin-ui
cp .env.example .env.local
# Fill in .env.local with real values (use http://localhost:8000 for BACKEND_BASE_URL)
npm run dev
```
