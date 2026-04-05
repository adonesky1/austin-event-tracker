# Deployment Guide

This app runs as a single Docker Compose stack: a FastAPI process (with in-process APScheduler) plus a Postgres 16 database. Everything runs unattended — events are ingested daily at 6am CT, digests are emailed Tuesday and Friday at 8am CT.

---

## 1. What You Need Before Starting

### A VPS

Any cheap VPS works. Recommendations:

| Provider | Size | Cost | Notes |
|---|---|---|---|
| Hetzner Cloud | CX22 (2 vCPU, 4GB RAM) | ~€4/mo | Best price/perf, EU-hosted |
| DigitalOcean | Basic Droplet (2 vCPU, 2GB RAM) | $18/mo | Easy UI, US-hosted |
| Fly.io | shared-cpu-1x (256MB) | Free tier | Lowest cost, more complex setup |

**Minimum requirements:** 1 vCPU, 1GB RAM, 10GB disk. Ubuntu 22.04 LTS recommended.

Do **not** use a 512MB VPS for this stack. The first Docker build installs Chromium for Playwright, and 512MB instances commonly get killed by the kernel for running out of memory during that step.

### A Domain (Required for Email)

Resend requires a verified domain to send email. You cannot use a Gmail/Yahoo address as the sender. A cheap domain ($10-12/yr from Namecheap or Cloudflare) is sufficient. You'll add 2-3 DNS records.

### API Keys

| Key | Where to Get | Notes |
|---|---|---|
| **Anthropic** (`ANTHROPIC_API_KEY`) | [console.anthropic.com](https://console.anthropic.com) | Free tier: $5 credit. Uses Claude Haiku — very cheap (~$0.001 per digest). |
| **Resend** (`RESEND_API_KEY`) | [resend.com](https://resend.com) | Free tier: 3,000 emails/mo. Create account → API Keys → Create. |
| **Eventbrite** (`EVENTBRITE_API_KEY`) | [eventbrite.com/platform](https://www.eventbrite.com/platform/api) | Free. Create app → get private token. |
| **Bandsintown** (`BANDSINTOWN_APP_ID`) | [artists.bandsintown.com/support/api-installation](https://artists.bandsintown.com/support/api-installation) | Free. The "app_id" is just your app name (e.g. `austin-family-events`), no approval required. |
| **Google Calendar OAuth client** (`GOOGLE_CALENDAR_CLIENT_ID`, `GOOGLE_CALENDAR_CLIENT_SECRET`) | [Google Cloud Console](https://console.cloud.google.com/) | Optional. Only needed if you want curated events pushed to a shared Google Calendar. Create a desktop OAuth client and enable the Google Calendar API. |

Do512 and Austin Chronicle are scraped directly — no API key needed.

---

## 2. Configure Resend (Email Sending)

This is the most involved step. Do it before touching the VPS.

**Step 1: Add your domain to Resend**
- Log into [resend.com](https://resend.com) → Domains → Add Domain
- Enter your domain (e.g. `example.com`)

**Step 2: Add DNS records**
Resend shows you 3 DNS records to add (SPF, DKIM, DMARC). Add them in your domain registrar's DNS panel. Changes propagate in 5–30 minutes.

**Step 3: Choose your from address**
Once the domain is verified, your from address can be anything at that domain — e.g. `digest@example.com` or `events@yourdomain.com`. This goes in `FROM_EMAIL`.

**Step 4: The to address**
This single-user app sends the digest to the same address as `FROM_EMAIL`. If you want the digest delivered to a different inbox (e.g. your Gmail), set `FROM_EMAIL` to your sending address and add a separate `TO_EMAIL` env var — see note in [Customizing the Recipient](#customizing-the-recipient).

---

## 3. Set Up the VPS

SSH into your fresh VPS as root, then:

```bash
# Create a non-root user
useradd -m -s /bin/bash deploy
usermod -aG sudo deploy
# Copy your SSH key
mkdir -p /home/deploy/.ssh
cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh

# Switch to deploy user for the rest
su - deploy
```

**Install Docker:**

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in for group membership to take effect
exit
ssh deploy@your-vps-ip
```

Verify: `docker --version` and `docker compose version`

---

## 4. (Optional) Configure Google Calendar Publishing

Skip this section if you only want email digests.

Google Calendar publishing uses OAuth and is easiest to bootstrap from **your local machine**, not the VPS, because the first run opens a browser for consent.

### Step 1: Enable the Google Calendar API

In Google Cloud:

1. Create or select a project
2. Enable **Google Calendar API**
3. Configure the OAuth consent screen:
   - choose **External** if you're using a personal Gmail account
   - leave the app in **Testing** for personal setup
   - add your own Google account under **Test users** before running the bootstrap helper
4. Create a **Desktop app** OAuth client
5. Download the OAuth client JSON file

### Step 2: Run the bootstrap helper locally

From your local clone of the repo:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python scripts/google_calendar_bootstrap.py path/to/oauth-client.json
```

If Google Cloud won't let you download the OAuth client JSON, `clientId` alone is not enough for this step. The bootstrap script also needs the OAuth client secret and redirect metadata. In practice, the easiest fallback is to open the OAuth client details in Google Cloud and either:

- download the JSON from there if the option appears
- or create a fresh **Desktop app** OAuth client and use that client ID and client secret to assemble a small JSON file locally

Example shape:

```json
{
  "installed": {
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "redirect_uris": ["http://localhost"]
  }
}
```

This will:

- open the Google OAuth flow in your browser
- create a secondary calendar named **Austin Curated Events**
- print:
  - `GOOGLE_CALENDAR_CLIENT_ID`
  - `GOOGLE_CALENDAR_CLIENT_SECRET`
  - `GOOGLE_CALENDAR_REFRESH_TOKEN`
  - `GOOGLE_CALENDAR_ID`

Save those values — you'll paste them into the VPS `.env` file in the next section.

### Step 3: Share the calendar

This app does **not** manage subscriber invites yet.

To keep the calendar invite-only:

1. Open Google Calendar on a computer: <https://calendar.google.com/>
2. In the left sidebar, find **My calendars**.
3. Locate the secondary calendar created by the bootstrap helper, usually **Austin Curated Events**.
4. Hover over that calendar, click the three-dot menu, then click **Settings and sharing**.
5. In the left-side settings menu, open **Share with specific people or groups**.
6. Click **Add people and groups**.
7. Enter the Gmail address or Google Group for each person who should be able to read the calendar.
8. For a read-only shared calendar, choose **See all event details**.
9. Click **Send**. Google Calendar emails each person a sharing invite.
10. Ask each recipient to open the email and accept the invitation so the calendar appears in their Google Calendar list.

To keep the calendar private:

- Do **not** enable **Make available to public**
- Do **not** enable **Make available for your organization** unless you intentionally want everyone in your Google Workspace to see it
- If you need to remove someone later, return to **Settings and sharing** and use **Remove** next to their address under **Share with specific people or groups**

---

## 5. Deploy the App

**Clone the repo:**

```bash
git clone https://github.com/adonesky1/austin-event-tracker.git
cd austin-event-tracker
```

If you're deploying from your own fork, replace `adonesky1` with your GitHub username or org. Do **not** type the literal placeholder `you`.

If the repo is private, GitHub will not accept your account password for HTTPS clones. Use either:

- an SSH clone URL, e.g. `git clone git@github.com:your-user/austin-event-tracker.git`
- or a GitHub personal access token (PAT) instead of a password

**Create your `.env` file:**

```bash
cp .env.example .env
nano .env
```

Fill in every value:

```bash
# Database — leave this as-is, it points to the docker-compose postgres service
DATABASE_URL=postgresql+asyncpg://events:events@db:5432/events

# LLM
ANTHROPIC_API_KEY=sk-ant-...

# Email
RESEND_API_KEY=re_...
FROM_EMAIL=digest@yourdomain.com

# Event sources
EVENTBRITE_API_KEY=your_private_token
BANDSINTOWN_APP_ID=austin-family-events   # can be any descriptive string

# App security
ADMIN_API_KEY=change-this-to-a-random-string
FEEDBACK_SECRET=change-this-to-another-random-string

# App config
BASE_URL=http://your-vps-ip:8000   # or https://yourdomain.com if you add nginx
DEFAULT_CITY=austin
LOG_LEVEL=INFO

# Optional Google Calendar publishing
GOOGLE_CALENDAR_ENABLED=false
GOOGLE_CALENDAR_CLIENT_ID=
GOOGLE_CALENDAR_CLIENT_SECRET=
GOOGLE_CALENDAR_REFRESH_TOKEN=
GOOGLE_CALENDAR_ID=
GOOGLE_CALENDAR_MIN_SCORE=0.65
GOOGLE_CALENDAR_HORIZON_DAYS=21
GOOGLE_CALENDAR_FALLBACK_DURATION_MINUTES=120
GOOGLE_CALENDAR_SYNC_HOUR=7
GOOGLE_CALENDAR_TIMEZONE=America/Chicago
GOOGLE_CALENDAR_CALENDAR_NAME=Austin Curated Events
```

If you want Google Calendar publishing, change:

```bash
GOOGLE_CALENDAR_ENABLED=true
```

and fill in the client ID, client secret, refresh token, and calendar ID from the bootstrap step.

Generate secure random strings for `ADMIN_API_KEY` and `FEEDBACK_SECRET`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Build and start:**

```bash
docker compose up -d --build
```

This takes 3–5 minutes on first run (downloads images, installs Python deps, installs Chromium for Playwright).

---

## 6. Verify the Deployment

**Check containers are running:**

```bash
docker compose ps
```

Expected output:
```
NAME                        STATUS          PORTS
austin-event-tracker-app-1  Up (healthy)    0.0.0.0:8000->8000/tcp
austin-event-tracker-db-1   Up (healthy)    0.0.0.0:5432->5432/tcp
```

**Check app logs for startup errors:**

```bash
docker compose logs app --tail=50
```

You should see lines like:
```
migrations_applied
Seeded default user: digest@yourdomain.com
scheduler_started  jobs=['ingest_all_sources', 'generate_and_send_digest', 'sync_google_calendar', 'cleanup_old_events']
app_startup  version=0.1.0
```

**Hit the health endpoint:**

```bash
curl http://your-vps-ip:8000/health
# {"status":"ok","version":"0.1.0"}
```

**Check the API docs:**

Open `http://your-vps-ip:8000/docs` in a browser — you'll see the full Swagger UI.

---

## 7. Trigger a Test Digest

Don't wait until Tuesday to find out if email is working. Trigger it manually:

```bash
# From inside the app container
docker compose exec app python3 -c "
import asyncio
from src.jobs.digest_job import run_digest
asyncio.run(run_digest())
"
```

Watch the logs in another terminal:

```bash
docker compose logs app -f
```

A successful run looks like:
```
run_ingestion_start
source_fetch_complete  source=eventbrite events=47
source_fetch_complete  source=do512 events=31
...
ingest_complete  total=98 normalized=94 deduped=87
digest_job_complete  events=15 email_id=abc123
```

Check your inbox — the digest should arrive within a minute.

---

## 8. (Optional) Verify Google Calendar Publishing

If `GOOGLE_CALENDAR_ENABLED=true`, verify the calendar integration before waiting for the scheduled sync.

**Preview the next sync without writing to Google Calendar:**

```bash
curl -H "x-api-key: YOUR_ADMIN_API_KEY" \
  http://your-vps-ip:8000/admin/calendar/preview
```

You should get JSON with:

- `selected_count`
- `created_count`
- `updated_count`
- `deleted_count`

**Run a manual sync now:**

```bash
curl -X POST -H "x-api-key: YOUR_ADMIN_API_KEY" \
  http://your-vps-ip:8000/admin/calendar/sync
```

**Check current status:**

```bash
curl -H "x-api-key: YOUR_ADMIN_API_KEY" \
  http://your-vps-ip:8000/admin/calendar/status
```

Successful logs look like:

```text
google_calendar_sync_complete  selected=12 created=12 updated=0 deleted=0
```

Then open Google Calendar and confirm the target secondary calendar contains:

- concise `What:` and `Why it fits:` text
- event/source links
- a Google Maps link when location data exists

---

## 9. Routine Operations

**View logs:**

```bash
docker compose logs app -f          # follow live
docker compose logs app --tail=200  # last 200 lines
```

**Restart the app** (e.g. after config changes):

```bash
docker compose restart app
```

**Redeploy after a code update:**

```bash
git pull
docker compose up -d --build app
```

**Check scheduled job timing** (all times CT):

| Job | Schedule |
|---|---|
| Ingest all sources | Daily at 6:00 AM |
| Generate and send digest | Tuesday and Friday at 8:00 AM |
| Sync Google Calendar | Daily at 7:00 AM |
| Archive old events | Sunday at 3:00 AM |

**Manually trigger ingestion:**

```bash
docker compose exec app python3 -c "
import asyncio
from src.jobs.ingest_job import run_ingestion
asyncio.run(run_ingestion())
"
```

**Access the database:**

```bash
docker compose exec db psql -U events -d events
```

Useful queries:

```sql
-- Count events by category
SELECT category, count(*) FROM events GROUP BY category ORDER BY count DESC;

-- Most recent ingestion
SELECT source_name, max(ingested_at) FROM event_sources GROUP BY source_name;

-- Recent digests
SELECT id, status, sent_at, created_at FROM digests ORDER BY created_at DESC LIMIT 10;

-- Recent Google Calendar sync runs
SELECT trigger, status, started_at, selected_count, created_count, updated_count, deleted_count
FROM calendar_sync_runs
ORDER BY started_at DESC
LIMIT 10;

-- Feedback summary
SELECT feedback_type, count(*) FROM feedback GROUP BY feedback_type;
```

---

## 10. (Optional) Deploy the Admin UI on Vercel

If you want a proper operator UI for preferences, prompts, tracked items, source status, and calendar sync, deploy the separate **`admin-ui/`** app to Vercel and keep the FastAPI backend on the VPS.

### Architecture

- **VPS**: FastAPI API, APScheduler, Playwright scraping, Postgres
- **Vercel**: `admin-ui/` Next.js app only

Recommended domains:

- `api.yourdomain.com` -> VPS
- `admin.yourdomain.com` -> Vercel

### Why keep the split?

The backend is not just a stateless API. It runs in-process scheduled jobs and browser automation, so it still belongs on the VPS. The admin UI is a normal Next.js app and is a good fit for Vercel previews and fast frontend deploys.

### Vercel root directory

Create a separate Vercel project and set:

- **Root Directory** = `admin-ui`

### Admin UI environment variables

Set these in Vercel:

```bash
BACKEND_BASE_URL=https://api.yourdomain.com
BACKEND_ADMIN_API_KEY=the-same-value-as-ADMIN_API_KEY-on-the-vps
AUTH_SECRET=generate-a-long-random-string
AUTH_GOOGLE_ID=from-google-cloud-oauth-client
AUTH_GOOGLE_SECRET=from-google-cloud-oauth-client
ADMIN_ALLOWED_EMAILS=you@example.com,other-admin@example.com
```

Notes:

- `BACKEND_ADMIN_API_KEY` should match the VPS `ADMIN_API_KEY`
- this key stays **server-side in Vercel only**
- do **not** expose the backend admin key in browser-side code or public env vars
- `ADMIN_ALLOWED_EMAILS` controls which Google accounts may enter the admin UI

### Google auth setup

In Google Cloud:

1. Reuse or create an OAuth client for the admin UI
2. Add your Vercel callback URL, e.g.
   - `https://admin.yourdomain.com/api/auth/callback/google`
3. Copy the client ID and secret into `AUTH_GOOGLE_ID` and `AUTH_GOOGLE_SECRET`

### First deploy checklist

After deploying the UI:

1. sign in with an allowed Google account
2. verify the dashboard loads
3. save a preference change under **Preferences**
4. update and reset the synthesis prompt under **Prompts**
5. add a tracked item under **Tracked Items**
6. open **Calendar** and run a preview

If those succeed, the Vercel UI -> VPS API proxy path is working.

---

## 11. (Optional) Add HTTPS with Nginx

For a proper domain + TLS, install Nginx and Certbot on the VPS:

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

Create `/etc/nginx/sites-available/events`:

```nginx
server {
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and get a certificate:

```bash
sudo ln -s /etc/nginx/sites-available/events /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d yourdomain.com
```

Then update `BASE_URL=https://yourdomain.com` in `.env` and restart:

```bash
docker compose restart app
```

---

## 12. Customizing the Recipient

Currently the digest is sent from `FROM_EMAIL` to `FROM_EMAIL` (same address). To send to a different inbox, add a `TO_EMAIL` variable to `.env` and update [`src/jobs/digest_job.py`](../src/jobs/digest_job.py):

Find this line (around line 36):
```python
profile = DEFAULT_PROFILE.model_copy(update={"email": settings.from_email})
```

Change to:
```python
to_email = getattr(settings, "to_email", settings.from_email)
profile = DEFAULT_PROFILE.model_copy(update={"email": to_email})
```

Then add to `src/config/settings.py`:
```python
to_email: str = ""  # defaults to from_email if blank
```

---

## 13. Troubleshooting

**App won't start — `migration_failed`:**

```bash
docker compose logs app | grep migration
```

Usually means the database isn't ready yet. Check: `docker compose ps db` — the db container should be healthy before the app starts. If the db is healthy but migrations still fail, check `DATABASE_URL` in `.env` uses `db` as the hostname (not `localhost`).

**No events from Eventbrite:**

The Eventbrite free API tier has rate limits and may require a published app. Verify your key works:

```bash
curl "https://www.eventbriteapi.com/v3/events/search/?location.address=Austin,TX&token=YOUR_KEY"
```

**Playwright/Do512 scrape fails:**

Chromium inside Docker sometimes needs extra flags. Check logs for `BrowserType.launch`. If it fails with "executable not found", rebuild the image:

```bash
docker compose build --no-cache app
```

**`docker compose up -d --build` fails with `signal: killed`:**

This usually means the VPS ran out of RAM during the Docker build, most often while installing Chromium for Playwright. A `512MB` VPS is below the supported minimum for this project.

Best fix:

1. Resize the VPS to at least `1GB RAM` (`2GB` is more comfortable)
2. Reconnect and rerun:

```bash
docker compose up -d --build
```

Temporary workaround if you absolutely must try the current box:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
free -h
docker compose up -d --build
```

That can help the build finish, but a `512MB` server is still likely to be unstable for the long-running app + Postgres + Playwright combination.

**`docker compose up -d --build` fails with `no space left on device`:**

This means the VPS disk filled up during the Docker image build or image export. Failed build layers are often still cached under Docker, so the second attempt can run out of disk even if the first failure was caused by RAM.

On a fresh box with no important Docker data yet, free failed build artifacts and retry:

```bash
docker builder prune -af
docker image prune -af
df -h
docker compose up -d --build
```

If it still fails, the disk is too tight for this stack. Increase the VPS disk size or move to a plan with more storage.

**Email not arriving:**

1. Check Resend dashboard → Logs — did the API call succeed?
2. Verify the domain is verified in Resend (green checkmark)
3. Check spam folder
4. Confirm `FROM_EMAIL` exactly matches a verified domain in Resend

**Google Calendar sync is enabled but fails immediately:**

1. Check that all four required values are set in `.env`:
   - `GOOGLE_CALENDAR_CLIENT_ID`
   - `GOOGLE_CALENDAR_CLIENT_SECRET`
   - `GOOGLE_CALENDAR_REFRESH_TOKEN`
   - `GOOGLE_CALENDAR_ID`
2. Confirm `GOOGLE_CALENDAR_ENABLED=true`
3. Check app logs:

```bash
docker compose logs app | grep google_calendar
```

**Google Calendar preview works but sync creates zero events:**

The most common causes are:

- no curated events cleared `GOOGLE_CALENDAR_MIN_SCORE`
- the event start dates fell outside `GOOGLE_CALENDAR_HORIZON_DAYS`
- upstream ingestion returned sparse results that day

Use:

```bash
curl -H "x-api-key: YOUR_ADMIN_API_KEY" \
  http://your-vps-ip:8000/admin/calendar/preview
```

to inspect the selection counts before forcing a sync.

**Google OAuth completed once, but later you see auth errors:**

Your refresh token may be missing or revoked. Re-run:

```bash
python3 scripts/google_calendar_bootstrap.py path/to/oauth-client.json
```

then update the VPS `.env` values and restart the app:

```bash
docker compose restart app
```

**Calendar events appear but links are missing:**

- event/source links require a canonical or source URL from ingestion
- map links require venue/address data

Missing links usually mean the upstream source data was incomplete, not that sync failed.

**Out of disk space** (usually from Docker images):

```bash
docker system prune -f           # remove unused images and containers
docker volume prune -f           # ⚠️  only if you want to wipe the database
```

---

## Cost Estimate (monthly)

| Item | Cost |
|---|---|
| Hetzner CX22 VPS | ~€4 |
| Domain | ~$1 (amortized) |
| Anthropic API (2 digests/wk × Claude Haiku) | ~$0.05 |
| Resend (free tier, <100 emails/mo) | $0 |
| Eventbrite API (free tier) | $0 |
| **Total** | **~€5/mo** |
