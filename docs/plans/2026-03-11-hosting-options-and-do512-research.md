# Hosting Options and Do512 Research

**Date:** 2026-03-11
**Status:** Research note

## Executive Summary

The current repo is **not** a drop-in fit for Vercel Hobby as written. The design and code assume:

- a long-lived FastAPI process
- in-process APScheduler jobs
- a Postgres service reachable on the private network
- Playwright/Chromium for the Do512 source

That architecture fits a small VPS or always-on container much better than serverless hosting.

The best "no VPS" path for this repo is:

1. **Vercel for HTTP**
2. **Neon for Postgres**
3. **GitHub Actions for scheduled ingestion**
4. **Playwright only in GitHub Actions for Do512**
5. **A DB-backed digest job run from Vercel cron or GitHub Actions**

This keeps the browser-dependent scraping out of Vercel while preserving a mostly serverless stack.

## What The Current Repo Assumes

The design doc explicitly chooses in-process cron and a two-container deployment:

- [`docs/plans/2026-03-07-city-family-events-curator-design.md`](./2026-03-07-city-family-events-curator-design.md)
- [`docs/deployment.md`](../deployment.md)

The implementation matches that:

- [`src/main.py`](../../src/main.py) runs Alembic migrations, seeds data, and starts APScheduler on app startup.
- [`src/jobs/scheduler.py`](../../src/jobs/scheduler.py) schedules ingestion, digest generation, and cleanup inside the app process.
- [`docker-compose.yml`](../../docker-compose.yml) expects an `app` service and a `db` service.
- [`src/sources/do512.py`](../../src/sources/do512.py) launches Playwright Chromium to fetch Do512 before parsing it.
- [`Dockerfile`](../../Dockerfile) installs Chromium with Playwright.

There is one important nuance: the current implementation is still relatively batch-oriented and not fully DB-backed yet.

- [`src/jobs/ingest_job.py`](../../src/jobs/ingest_job.py) currently runs with `persist=False`.
- [`src/jobs/digest_job.py`](../../src/jobs/digest_job.py) currently re-runs ingestion directly instead of reading a durable event store.
- [`src/api/feedback.py`](../../src/api/feedback.py) still has TODO persistence for feedback.

That means the project is actually easier to move toward external cron + managed Postgres now than it would be after more stateful features are wired in.

## Current Platform Constraints

The following external constraints matter for this decision as of 2026-03-11.

| Platform | Relevant constraint | Why it matters here |
|---|---|---|
| Vercel Hobby | Up to 2 cron jobs | The current app schedules 3 jobs. Cleanup would need to be folded into another run or handled elsewhere. |
| Vercel Hobby | Python functions max duration 300 seconds | Any Do512 scrape + ranking + email path must finish well under 5 minutes if run on Vercel. |
| Vercel Hobby | Cron invocations may happen at any time within the scheduled hour and duplicate deliveries are possible | Jobs must be idempotent and should not assume exact delivery time. |
| GitHub Actions | Scheduled workflows can be delayed and some queued jobs may be dropped during high load, especially at the top of the hour | Fine for daily ingestion, not suitable for exact-time delivery guarantees. |
| GitHub Free | 2,000 Actions minutes per month for private repos; standard runners are free for public repos | Usually enough for daily scraping plus a few manual re-runs, but private-repo usage should be watched. |
| Neon Free | 0.5 GB storage and 190 compute hours per month | Reasonable fit for this MVP if data retention is controlled. |

## Do512 Findings

### 1. The repo uses Playwright for the fetch step, not the parse step

This is an important distinction.

- [`src/sources/do512.py`](../../src/sources/do512.py) uses Playwright only to obtain the rendered HTML.
- The parser itself is plain BeautifulSoup over `.ds-listing` nodes.
- [`tests/fixtures/do512_sample.html`](../../tests/fixtures/do512_sample.html) is already-rendered HTML, which is exactly what the adapter expects after the browser step.

So Playwright is not inherently required to parse Do512 markup. It is there because the adapter assumes a real browser is needed to obtain stable HTML from the live site.

### 2. I did not find a documented public Do512 API/feed

I did not find a documented public API, RSS feed, ICS feed, or stable machine contract for Do512 that I would want to build against.

The strongest official signal I found is Do512's own FAQ page, which says their events are drawn from band and venue websites plus user submissions. That sounds like a consumer-facing aggregation product, not a supported developer API.

### 3. A lightweight `httpx` Do512 fetch is possible in theory, but not plan-worthy yet

There may still be an undocumented non-browser path, for example:

- server-rendered HTML that only needs request/header tuning
- preloaded JSON in the page HTML
- an internal XHR endpoint the web app calls

But I did not verify any of those as a stable contract. Given the current evidence, I would not make the Vercel architecture depend on discovering one later.

## Viable Architectures

### Option A: Small paid VPS or always-on container

**Operational fit:** Best  
**Cash cost:** Higher than the serverless options  
**Engineering cost:** Lowest

This is the best fit for the current repo as-is. It preserves:

- long-lived APScheduler
- in-process cron
- Playwright/Chromium in the same runtime
- the current Docker-oriented deployment story

Good if the priority is shipping quickly with minimal refactor.

### Option B: Vercel + Neon + GitHub Actions + Playwright for Do512

**Operational fit:** Best "no VPS" option  
**Cash cost:** Low  
**Engineering cost:** Moderate

This is the recommended path if the goal is to avoid a VPS.

Suggested split:

- Vercel serves HTTP routes only.
- Neon stores events, digests, source health, and feedback.
- GitHub Actions runs scheduled ingestion, especially the Do512 step.
- The Do512 step runs under Playwright inside GitHub Actions.
- Results are upserted into Neon.
- Vercel reads from Neon and serves feedback/preferences/admin HTTP endpoints.
- Digest generation should be refactored to read from Neon and then run either from a protected Vercel cron route or from a second GitHub Actions workflow.

Why this works:

- Playwright has CI guidance for GitHub Actions.
- GitHub Actions can run browser automation without dragging Chromium into Vercel functions.
- The scheduled scrape is not user-facing, so cron jitter is acceptable if jobs are idempotent.

Tradeoffs:

- Logs and secrets are split across GitHub, Vercel, and Neon.
- Scheduled workflows are not exact-time guarantees.
- You need DB-level dedupe/idempotency and probably a per-job lock.
- The current digest flow must be changed so it no longer calls ingestion inline.

### Option C: Vercel + Neon + remote browser service

**Operational fit:** Possible  
**Cash cost:** Usually higher than Option B over time  
**Engineering cost:** Moderate to high

Instead of running Playwright locally in the job, connect to a remote managed browser such as Browserbase or Browserless from the ingest job.

Why this can work:

- avoids bundling Chromium into Vercel
- keeps browser execution out-of-process
- can fit a serverless-first architecture better than local browser binaries

Why I would not start here:

- adds another vendor immediately
- still leaves Vercel duration limits in place
- still requires idempotent scheduled execution
- is harder to debug than just running Playwright in GitHub Actions

This is a good fallback if Do512 becomes too brittle on GitHub-hosted runners or if anti-bot behavior becomes a bigger issue.

### Option D: Drop Do512 from MVP

**Operational fit:** Very high  
**Cash cost:** Lowest  
**Engineering cost:** Lowest after Option A

This is the cleanest way to stay serverless-friendly.

Coverage would come from:

- Eventbrite
- Bandsintown
- Austin Chronicle
- hand-picked venue/organization calendars

This loses some discovery breadth, but it may be the correct MVP tradeoff if the goal is a very low-ops deployment.

## Recommendation

If the goal is **lowest engineering effort**, deploy the current app to a small VPS or always-on container.

If the goal is **no VPS and low cash cost**, choose **Option B**:

- Vercel for HTTP
- Neon for Postgres
- GitHub Actions for scheduled ingestion
- Playwright only in GitHub Actions for Do512
- a separate DB-backed digest/send job

That gives the best balance of:

- low infrastructure cost
- realistic Do512 support
- minimal exposure to Vercel function constraints
- minimal platform lock-in

## Concrete Changes Needed For Option B

1. Remove APScheduler from the request-serving app path.
2. Move migrations out of FastAPI startup.
3. Add a dedicated ingestion entrypoint that can run from GitHub Actions.
4. Upsert events into Neon instead of returning them only in-memory.
5. Refactor digest generation to read from stored events instead of calling ingestion inline.
6. Add a job lock and idempotency key for ingestion and digest generation.
7. Keep Do512 browser automation isolated so only the GitHub Actions path depends on Playwright.
8. Make Vercel routes read-only where possible and keep feedback writes small/simple.

## Sources

- Do512 FAQ: <https://2025.do512.com/p/about>
- Playwright CI docs: <https://playwright.dev/python/docs/ci>
- GitHub Actions billing: <https://docs.github.com/en/billing/concepts/product-billing/github-actions>
- GitHub scheduled workflow delays: <https://docs.github.com/en/actions/how-tos/troubleshoot-workflows>
- Vercel Hobby plan: <https://vercel.com/docs/plans/hobby>
- Vercel Functions limits: <https://vercel.com/docs/functions/limitations>
- Vercel cron behavior: <https://vercel.com/docs/cron-jobs/manage-cron-jobs>
- Neon pricing: <https://neon.com/pricing>
- Browserbase session docs: <https://docs.browserbase.com/fundamentals/using-browser-session>
- Browserless quick start: <https://docs.browserless.io/baas/quick-start>
