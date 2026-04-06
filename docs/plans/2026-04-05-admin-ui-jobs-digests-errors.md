# Admin UI: Jobs, Digest History & Error Notifications

**Date:** 2026-04-05  
**Status:** Approved — ready to implement

---

## Overview

Extend the existing admin UI (Next.js on Vercel) and FastAPI backend with four new capabilities:

1. **Cron job controls** — view schedules, trigger jobs manually, edit schedule (persisted to DB)
2. **Digest history** — browse previously sent digests and read their full content
3. **Backend error notifications** — job-level failures posted to Telegram as a short summary
4. **Wire up existing stubs** — several admin endpoints are currently TODO stubs; this plan implements them

---

## Backend Changes

### 1. Error Notifier (`src/notifications/error_notifier.py`)

New utility module with a single async function:

```python
async def notify_job_failure(job_name: str, error: Exception) -> None
```

- Posts a short plain-text message to Telegram if `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set
- Message format: `"[Job Failure] {job_name}: {type(error).__name__}: {str(error)[:200]}"`
- Silently no-ops if Telegram is not configured (no crash)
- Called from each job's top-level except block

### 2. Wrap Jobs with Error Handling

Add `try/except` + `notify_job_failure` to:

- `src/jobs/digest_job.py` — `run_digest()`
- `src/jobs/ingest_job.py` — `run_ingestion()`
- `src/jobs/calendar_sync_job.py` — `run_google_calendar_sync()`

Pattern:
```python
async def run_digest():
    try:
        ...existing body...
    except Exception as exc:
        logger.error("digest_job_failed", error=str(exc))
        await notify_job_failure("digest", exc)
        raise
```

### 3. Save Digest Runs to DB

`digest_job.py` currently sends the digest but never persists it. Update to:

- Create a `Digest` row with `status=DRAFT` before sending
- Update to `status=SENT` + `sent_at=now()` after successful send
- Update to `status=FAILED` if send throws

Uses the existing `Digest` model and `digests` table (created in migration 0001). The `Digest` model has all necessary fields: `subject`, `html_content`, `plaintext_content`, `event_ids`, `sent_at`, `status`, `window_start`, `window_end`.

### 4. Migration 0004 — `job_schedules` Table

New table to persist scheduler overrides:

```sql
CREATE TABLE job_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id VARCHAR(100) NOT NULL UNIQUE,
    day_of_week VARCHAR(50),    -- e.g. "tue,fri" or NULL for daily
    hour INTEGER NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Defaults are not pre-seeded — absence of a row means "use the hardcoded default".

### 5. Scheduler Singleton + DB-Backed Schedule Loading

**`src/jobs/scheduler.py`** changes:

- Add a module-level `_scheduler: AsyncIOScheduler | None = None`
- Add `get_scheduler() -> AsyncIOScheduler` to expose it to admin routes
- `create_scheduler()` after adding all default jobs, queries `job_schedules` and reschedules any jobs that have a DB override
- New `reschedule_job(job_id, day_of_week, hour)` helper that updates both the live APScheduler job and the DB row

DB lookup uses a one-shot sync SQLAlchemy session (same pattern used in migrations) to avoid async startup complexity, or alternatively an async call via the existing `create_engine` / `create_session_factory` utilities.

**Scheduler access in admin routes:** import `get_scheduler()` from `src.jobs.scheduler`.

### 6. Admin API — Jobs Endpoints

New routes added to `src/api/admin.py`:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/jobs` | List all APScheduler jobs with schedule + next run time |
| `POST` | `/admin/jobs/{job_id}/trigger` | Run a job immediately (fire-and-forget via `asyncio.create_task`) |
| `PUT` | `/admin/jobs/{job_id}/schedule` | Update schedule, persist to `job_schedules`, reschedule live job |

`GET /admin/jobs` response shape:
```json
[
  {
    "id": "generate_and_send_digest",
    "name": "Generate and send digest",
    "day_of_week": "tue,fri",
    "hour": 8,
    "next_run": "2026-04-08T13:00:00Z",
    "enabled": true
  }
]
```

`PUT /admin/jobs/{job_id}/schedule` request body:
```json
{ "day_of_week": "mon,wed,fri", "hour": 9 }
```

### 7. Admin API — Digest History Endpoints

Implement the existing stubs in `src/api/admin.py`:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/digests` | List digests ordered by `sent_at DESC`, paginated |
| `GET` | `/admin/digests/{id}` | Full digest content (html + plaintext) |

`GET /admin/digests` response shape:
```json
{
  "digests": [
    {
      "id": "uuid",
      "subject": "Austin Events: Apr 1 – Apr 8",
      "sent_at": "2026-04-01T13:00:00Z",
      "status": "sent",
      "event_count": 12,
      "window_start": "2026-04-01",
      "window_end": "2026-04-08"
    }
  ],
  "total": 5
}
```

---

## Frontend Changes (admin-ui)

### 8. `lib/types.ts` — New Types

```typescript
export interface JobInfo {
  id: string;
  name: string;
  day_of_week: string | null;
  hour: number;
  next_run: string | null;
  enabled: boolean;
}

export interface JobScheduleUpdate {
  day_of_week: string | null;
  hour: number;
}

export interface DigestSummary {
  id: string;
  subject: string;
  sent_at: string;
  status: string;
  event_count: number;
  window_start: string;
  window_end: string;
}

export interface DigestDetail extends DigestSummary {
  html_content: string;
  plaintext_content: string;
}
```

### 9. `/jobs` Page (`app/jobs/page.tsx`)

Server component that fetches job list. Renders a table with:

- Job name
- Current schedule (human-readable: e.g. "Tue, Fri at 8:00 AM CT")
- Next run time (relative: "in 3 days")
- **Run Now** button — fires `POST /admin/jobs/{id}/trigger`, shows loading state
- **Edit** button — opens inline form to change `day_of_week` (checkboxes Mon–Sun) and `hour` (0–23 number input); saves with `PUT /admin/jobs/{id}/schedule`

Client interactivity extracted into `components/job-row.tsx`.

### 10. `/digests` Page (`app/digests/page.tsx`)

Server component listing digest history. Table columns:
- Date sent (formatted)
- Subject
- Status badge (sent / failed / draft)
- Event count
- Link to detail view

### 11. `/digests/[id]` Page (`app/digests/[id]/page.tsx`)

Shows full digest:
- Metadata header (subject, sent at, event count, window)
- Tab toggle: **Preview** (rendered HTML in `<iframe srcDoc={...}>`) / **Plain Text** (monospace `<pre>`)

### 12. Navigation Update

Add to `components/app-nav.tsx`:
- "Jobs" → `/jobs`
- "Digests" → `/digests`

---

## Deployment (Vercel)

The `admin-ui/` directory is a standalone Next.js app. Steps:

1. Create new Vercel project pointing at the `admin-ui/` subdirectory
2. Set environment variables:
   - `BACKEND_URL=http://178.156.194.155:8000`
   - `BACKEND_ADMIN_API_KEY=<value from VPS .env>`
   - `NEXTAUTH_SECRET=<random 32-char string>`
   - `NEXTAUTH_URL=<assigned .vercel.app URL>`
   - `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` (from existing Google OAuth app)
3. The admin-ui proxies all backend calls server-side so `BACKEND_ADMIN_API_KEY` is never exposed to the browser

---

## File Change Summary

| File | Change |
|------|--------|
| `src/notifications/error_notifier.py` | **New** — Telegram failure notifier |
| `src/jobs/digest_job.py` | Wrap in try/except, save to `digests` table |
| `src/jobs/ingest_job.py` | Wrap in try/except, call error notifier |
| `src/jobs/calendar_sync_job.py` | Wrap in try/except, call error notifier |
| `migrations/versions/0004_job_schedules.py` | **New** — `job_schedules` table |
| `src/models/job_schedule.py` | **New** — `JobSchedule` SQLAlchemy model |
| `src/jobs/scheduler.py` | Singleton, DB-backed schedule loading, `reschedule_job()` |
| `src/api/admin.py` | New jobs endpoints; implement digest list/get stubs |
| `admin-ui/lib/types.ts` | Add `JobInfo`, `JobScheduleUpdate`, `DigestSummary`, `DigestDetail` |
| `admin-ui/lib/api.ts` | Add job + digest API helpers |
| `admin-ui/components/app-nav.tsx` | Add Jobs + Digests nav links |
| `admin-ui/components/job-row.tsx` | **New** — interactive job table row |
| `admin-ui/app/jobs/page.tsx` | **New** — jobs management page |
| `admin-ui/app/digests/page.tsx` | **New** — digest history list page |
| `admin-ui/app/digests/[id]/page.tsx` | **New** — digest detail page |

---

## Implementation Order

1. Error notifier + job wrapping (quick, low risk, no migration needed)
2. Migration 0004 + `JobSchedule` model
3. Scheduler singleton + DB schedule loading
4. Admin API: jobs endpoints
5. `digest_job.py`: save to DB
6. Admin API: digest history endpoints
7. Frontend: types + api helpers
8. Frontend: Jobs page
9. Frontend: Digests pages
10. Frontend: Nav update
11. Deploy to Vercel
