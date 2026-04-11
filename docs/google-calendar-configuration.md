# Google Calendar Publishing Configuration

This feature publishes curated Austin events into an invite-only Google Calendar using the Google Calendar API from the Python app.

## 1. Enable the Google Calendar API

1. Open the Google Cloud Console.
2. Create or choose a project for this app.
3. Enable **Google Calendar API** for that project.

Reference: <https://developers.google.com/workspace/calendar/api/guides/overview>

## 2. Create OAuth client credentials

1. In Google Cloud, configure the OAuth consent screen.
2. If you're using a personal Gmail account, choose an **External** app.
3. Leave the app in **Testing** for personal setup and add your own Google account under **Test users**.
4. Create an **OAuth client ID** for a desktop application.
5. Download the OAuth client JSON file.

Reference: <https://developers.google.com/workspace/calendar/api/quickstart/python>

## 3. Run the bootstrap helper

From the repo root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python scripts/google_calendar_bootstrap.py path/to/oauth-client.json
```

The helper will:

- run the one-time OAuth flow in your browser
- create a secondary calendar named **Austin Curated Events**
- print the env vars you should save

## 4. Environment variables

Add these to `.env`:

```env
GOOGLE_CALENDAR_ENABLED=true
GOOGLE_CALENDAR_CLIENT_ID=...
GOOGLE_CALENDAR_CLIENT_SECRET=...
GOOGLE_CALENDAR_REFRESH_TOKEN=...
GOOGLE_CALENDAR_ID=...
GOOGLE_CALENDAR_MIN_SCORE=0.65
GOOGLE_CALENDAR_HORIZON_DAYS=21
GOOGLE_CALENDAR_FALLBACK_DURATION_MINUTES=120
GOOGLE_CALENDAR_SYNC_HOUR=7
GOOGLE_CALENDAR_TIMEZONE=America/Chicago
GOOGLE_CALENDAR_CALENDAR_NAME=Austin Curated Events
```

### Defaults

- `GOOGLE_CALENDAR_ENABLED=false`
- `GOOGLE_CALENDAR_MIN_SCORE=0.65`
- `GOOGLE_CALENDAR_HORIZON_DAYS=21`
- `GOOGLE_CALENDAR_FALLBACK_DURATION_MINUTES=120`
- `GOOGLE_CALENDAR_SYNC_HOUR=7`
- `GOOGLE_CALENDAR_TIMEZONE=America/Chicago`
- `GOOGLE_CALENDAR_CALENDAR_NAME=Austin Curated Events`

The client ID, client secret, refresh token, and calendar ID default to blank strings and are only required when `GOOGLE_CALENDAR_ENABLED=true`.

## 5. Share the calendar

V1 does **not** manage invites in-app.

To share the calendar:

1. Open Google Calendar on a computer: <https://calendar.google.com/>.
2. In the left sidebar, find **My calendars**.
3. Locate the secondary calendar created by the bootstrap helper, usually **Austin Curated Events**.
4. Hover over that calendar, click the three-dot menu, then click **Settings and sharing**.
5. In the left-side settings menu, open **Share with specific people or groups**.
6. Click **Add people and groups**.
7. Add the Gmail address or Google Group for each reader.
8. Choose **See all event details** for read-only access.
9. Click **Send**.
10. Ask each recipient to accept the email invite so the calendar appears in their Google Calendar list.

This keeps the calendar invite-only.

Avoid turning on:

- **Make available to public**
- **Make available for your organization**, unless you explicitly want everyone in that workspace to see the calendar

## 6. Preview and manual sync

Protected admin endpoints:

- `GET /admin/calendar/status`
- `GET /admin/calendar/preview`
- `POST /admin/calendar/sync`

Use your existing admin API key:

```bash
curl -H "x-api-key: YOUR_ADMIN_API_KEY" http://localhost:8000/admin/calendar/status
curl -H "x-api-key: YOUR_ADMIN_API_KEY" http://localhost:8000/admin/calendar/preview
curl -X POST -H "x-api-key: YOUR_ADMIN_API_KEY" http://localhost:8000/admin/calendar/sync
```

## 7. Scheduler behavior

- The app runs a daily Google Calendar sync at **7:00 AM America/Chicago**
- It publishes curated events in the next **21 days**
- It creates, updates, and deletes events to keep the calendar in sync

## 8. Troubleshooting

### `Missing required Google Calendar settings`

Set all of:

- `GOOGLE_CALENDAR_CLIENT_ID`
- `GOOGLE_CALENDAR_CLIENT_SECRET`
- `GOOGLE_CALENDAR_REFRESH_TOKEN`
- `GOOGLE_CALENDAR_ID`

when `GOOGLE_CALENDAR_ENABLED=true`.

### OAuth completed but no refresh token was printed

Delete any previously granted app authorization for the OAuth client and rerun the bootstrap helper so Google prompts for consent again.

### `Error 403: access_denied` during Google sign-in

This usually means the OAuth app is still in **Testing** and the Google account you used is not listed under **Test users** on the OAuth consent screen. Add the account, wait a minute, and rerun the bootstrap helper.

### `RefreshError: invalid_grant`

This means Google rejected the stored refresh token. Common causes:

- the OAuth client was left in **Testing** and the refresh token expired
- the token was revoked from the Google account security settings
- the client ID / client secret no longer match the refresh token

Fix:

1. Re-run `python scripts/google_calendar_bootstrap.py path/to/oauth-client.json`
2. Copy the new `GOOGLE_CALENDAR_REFRESH_TOKEN`
3. Update the deployed env var and restart or redeploy the app

### Calendar sync runs but creates no events

Check:

- the curated event score threshold (`GOOGLE_CALENDAR_MIN_SCORE`)
- the publish window (`GOOGLE_CALENDAR_HORIZON_DAYS`)
- source ingestion results
- whether events are being filtered out before ranking

Use `GET /admin/calendar/preview` to inspect selection counts.

### Map links or source links are missing

Map links only appear when the event has venue/address data. Source links only appear when canonical/source URLs were captured during ingestion.

### Google auth/import errors at runtime

Make sure project dependencies are installed after pulling the latest code:

```bash
python3 -m pip install -e .
```

Relevant docs:

- <https://developers.google.com/workspace/calendar/api/guides/overview>
- <https://developers.google.com/workspace/calendar/api/v3/reference/events/insert>
- <https://developers.google.com/workspace/calendar/api/guides/extended-properties>
