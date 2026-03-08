# City Family Events Curator - Design Document

**Date:** 2026-03-07
**Status:** Approved

## Overview

An application that discovers events in Austin, TX relevant to a family, synthesizes and ranks them with AI, and sends curated email digests twice per week. Architected so Austin is configuration, not code -- new cities can be added later.

## Stack

| Layer | Choice | Rationale |
|---|---|---|
| Language | Python 3.12 | Best scraping/ML ecosystem |
| Web framework | FastAPI | Async-native, auto OpenAPI docs |
| ORM | SQLAlchemy 2.0 + Alembic | Async support, mature migrations |
| Database | PostgreSQL 16 | Relational, full-text search, JSONB for raw payloads |
| Scheduler | APScheduler 3.x | In-process cron, no extra infra |
| Scraping | Playwright + httpx + BeautifulSoup4 | Playwright for JS-rendered, httpx+BS4 for static |
| LLM | Anthropic SDK (Haiku) via thin abstraction | Cheapest Claude model, provider-swappable |
| Email | Resend SDK + Jinja2 templates | Simple API, Jinja for HTML templating |
| Validation | Pydantic v2 | Data models, config, API schemas |
| Containerization | Docker + docker-compose | Single-command deployment |

## Architecture

Pipeline-oriented monolith. Single FastAPI process with APScheduler for background jobs.

```
Sources -> Ingest -> Normalize -> Dedupe -> Store
                                              |
Schedule trigger -> Rank -> LLM Enrich -> Generate Digest -> Send Email
```

Two containers total: app (FastAPI + APScheduler) and Postgres.

## Folder Structure

```
austin-event-tracker/
  src/
    config/           # City configs, app settings, env loading
    sources/          # Source adapter implementations
      base.py         # Abstract source adapter interface
      eventbrite.py
      do512.py
      austin_chronicle.py
      bandsintown.py
      instagram.py    # Stub
    ingestion/        # Ingestion pipeline orchestration
    models/           # SQLAlchemy models
    schemas/          # Pydantic schemas
    dedupe/           # Deduplication engine
    ranking/          # Scoring + personalization
    llm/              # LLM abstraction + synthesis
    digest/           # Digest generation + email rendering
    notifications/    # Notification dispatch (email now, push later)
    api/              # FastAPI routes (admin, feedback, web view)
    jobs/             # APScheduler job definitions
    templates/        # Jinja2 email + web templates
  tests/
  migrations/         # Alembic
  docker-compose.yml
  Dockerfile
  .env.example
```

## Data Model

### events

The normalized event record after ingestion and dedupe.

| Column | Type | Notes |
|---|---|---|
| id | UUID, PK | |
| title | text, not null | |
| description | text | |
| category | enum | music, arts, festivals, theatre, kids, outdoor, seasonal, community |
| subcategory | text, nullable | |
| start_datetime | timestamptz, not null | |
| end_datetime | timestamptz, nullable | |
| timezone | text | default 'America/Chicago' |
| venue_name | text | |
| address | text | |
| neighborhood | text, nullable | |
| city | text, not null | |
| latitude | float, nullable | |
| longitude | float, nullable | |
| price_min | decimal, nullable | |
| price_max | decimal, nullable | |
| currency | text | default 'USD' |
| age_suitability | text, nullable | e.g. "all ages", "5+", "21+" |
| family_score | float, nullable | 0-1, LLM-inferred |
| image_url | text, nullable | |
| tags | text[], nullable | |
| confidence | float | default 0.5 |
| dedupe_group_id | UUID, nullable | links duplicate events |
| canonical_event_url | text | |
| editorial_summary | text, nullable | LLM-generated |
| relevance_explanation | text, nullable | LLM-generated "why this is for you" |
| created_at | timestamptz | |
| updated_at | timestamptz | |

### event_sources

Raw source records preserving provenance. Many-to-one with events.

| Column | Type | Notes |
|---|---|---|
| id | UUID, PK | |
| event_id | UUID, FK -> events, nullable | linked after dedupe |
| source_name | text, not null | 'eventbrite', 'do512', etc. |
| source_type | enum | api, feed, scraper |
| source_url | text | |
| raw_payload | jsonb | full original data |
| title | text | |
| start_datetime | timestamptz | |
| venue_name | text | |
| ingested_at | timestamptz | |

### user_profiles

Single user for MVP, multi-user ready.

| Column | Type | Notes |
|---|---|---|
| id | UUID, PK | |
| email | text, not null | |
| city | text | default 'austin' |
| adults | jsonb | [{age: 35}] |
| children | jsonb | [{age: 5}, {age: 8}] |
| preferred_neighborhoods | text[] | |
| max_distance_miles | int | default 30 |
| preferred_days | text[] | ['saturday', 'sunday'] |
| preferred_times | text[] | ['morning', 'afternoon'] |
| budget | enum | free, low, moderate, any |
| interests | text[] | ['music', 'outdoor', 'festivals'] |
| dislikes | text[] | |
| max_events_per_digest | int | default 15 |
| crowd_sensitivity | enum | low, medium, high |
| created_at | timestamptz | |
| updated_at | timestamptz | |

### feedback

| Column | Type | Notes |
|---|---|---|
| id | UUID, PK | |
| user_id | UUID, FK -> user_profiles | |
| event_id | UUID, FK -> events | |
| feedback_type | enum | thumbs_up, thumbs_down, more_like_this, less_like_this, too_far, too_expensive, wrong_age, already_knew |
| created_at | timestamptz | |

### digests

| Column | Type | Notes |
|---|---|---|
| id | UUID, PK | |
| user_id | UUID, FK -> user_profiles | |
| subject | text | |
| html_content | text | |
| plaintext_content | text | |
| event_ids | UUID[] | |
| sent_at | timestamptz, nullable | |
| status | enum | draft, sent, failed |
| window_start | date | |
| window_end | date | |

### source_health

| Column | Type | Notes |
|---|---|---|
| id | UUID, PK | |
| source_name | text | |
| last_run_at | timestamptz | |
| last_success_at | timestamptz, nullable | |
| events_found | int | |
| errors | text, nullable | |
| status | enum | healthy, degraded, failing, disabled |

## Source Adapters

### Interface

```python
class SourceAdapter(ABC):
    name: str
    source_type: SourceType  # api, feed, scraper

    async def fetch_events(self, city_config: CityConfig) -> list[RawEvent]
    def is_enabled(self) -> bool
    def rate_limit_delay(self) -> float
```

### MVP Sources

| Source | Type | Method | Status |
|---|---|---|---|
| Eventbrite | API | httpx + REST API | Real adapter |
| Bandsintown | API | httpx + REST API | Real adapter |
| Do512 | Scraper | Playwright | Real adapter |
| Austin Chronicle | Scraper | httpx + BeautifulSoup | Real adapter |
| Instagram | Stub | Interface only | TODO |

## Deduplication

Three-pass strategy:

1. **Exact match** - Same canonical URL or same (title + venue + date). Catches ~60%.
2. **Fuzzy match** - For events in same date window (+-2hrs), weighted similarity of title (Levenshtein 0.85), venue name (0.8), datetime proximity. Auto-merge if combined score > 0.8.
3. **LLM tiebreaker** - For scores 0.6-0.8, ask Haiku "are these the same event?" with both records.

On merge: keep richest record, link all event_sources to surviving event, assign shared dedupe_group_id.

## Ranking & Personalization

Three-layer scoring, each producing 0-1:

**Layer 1: Rule-based** - Distance, time fit, budget fit, category match, age fit, recency boost. Combined into `rule_score`.

**Layer 2: Feedback adjustment** - Positive feedback on similar events boosts. Negative feedback ("too far", "too expensive") applies targeted penalties. Recent feedback weighted more. Produces `feedback_adjusted_score`.

**Layer 3: LLM synthesis** - Runs on top ~30 candidates only. Single Haiku batch call. Returns family_score, editorial_summary, relevance_explanation. Structured JSON via tool use. Cached in events table.

**Final:** `final_score = 0.5 * rule_score + 0.2 * feedback_adjusted_score + 0.3 * llm_family_score`

Weights configurable. Top ~15 go into digest.

### Guardrails

- LLM never invents dates, venues, prices
- LLM output is editorial text and scores only
- Source URLs always preserved
- Confidence metadata stored alongside LLM outputs

## Digest Design

### Sections

1. **Top Picks** (3-4 highest scored, any type)
2. **Kids & Family** (high family_score, age-appropriate for children)
3. **Date Night / Adults** (concerts, comedy, theatre, lower family_score)
4. **This Weekend** (events in next 3-4 days)
5. **Worth Planning Ahead** (best events 1-3 weeks out)
6. **Free & Cheap** (top-scored events at $10 or under)

Events appear in at most two sections.

### Email Design

- Clean, minimal, mobile-first
- System font stack
- Muted color palette
- Event cards: image, title, date/time, venue, neighborhood, price, editorial blurb, "why this is for you"
- Inline feedback buttons (thumbs up/down) via signed GET links
- "Details" links to canonical event URL
- Footer: web view link, preferences link
- Plaintext fallback

### Web View

Each digest viewable at `/digests/{id}`. Same content, server-rendered.

## Scheduling

| Job | Schedule | Purpose |
|---|---|---|
| ingest_all_sources | Daily 6am CT | Run adapters, normalize, dedupe |
| generate_and_send_digest | Tue + Fri 8am CT | Rank, synthesize, render, send |
| cleanup_old_events | Weekly Sunday | Archive events older than 60 days |
| source_health_check | Daily after ingestion | Update source_health table |

## Admin Controls

FastAPI endpoints behind API key auth:

- `POST /admin/ingest` - trigger ingestion now
- `POST /admin/digest/preview` - generate but don't send
- `POST /admin/digest/send` - send latest draft
- `POST /admin/digest/{id}/resend` - resend specific digest
- `GET /admin/sources` - view source health
- `POST /admin/sources/{name}/toggle` - enable/disable source
- `GET /admin/events` - browse events with filters

## Deployment

docker-compose with two services: app (FastAPI + APScheduler) and db (Postgres 16 Alpine). Environment variables via .env file.

## Future Extension Points (Stubs in MVP)

**Push notifications:** NotificationChannel ABC, EmailChannel implemented, PushChannel stubbed.

**Google Calendar:** CalendarIntegration interface stubbed with create_event, update_event, check_duplicate.

**Multi-city:** City config loaded from YAML. Adding a city = new YAML + local source adapters.

**Multi-user:** user_profiles table supports it. MVP seeds one user. Adding multi-user = auth layer + per-user scheduling.
