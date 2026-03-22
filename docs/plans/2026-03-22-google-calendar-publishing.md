# Google Calendar Publishing for Curated Events

## Summary

- Save and implement an invite-only Google Calendar publisher for curated Austin events.
- Use the Google Calendar API from Python.
- Publish all curated events with final score >= 0.65 in the next 21 days.
- Keep the target calendar fully reconciled daily.
- Every published event must include a compact description with:
  - `What:`
  - `Why it fits:`
  - `Links:`

## Key implementation changes

### Config and defaults

- Add Google Calendar settings to `src/config/settings.py` with inline defaults where safe:
  - `google_calendar_enabled=False`
  - `google_calendar_min_score=0.65`
  - `google_calendar_horizon_days=21`
  - `google_calendar_fallback_duration_minutes=120`
  - `google_calendar_sync_hour=7`
  - `google_calendar_timezone="America/Chicago"`
  - `google_calendar_calendar_name="Austin Curated Events"`
- Mirror those defaults in `.env.example`.
- Validate required Google secrets/IDs only when calendar sync is enabled.

### Shared curation pipeline

- Extract a reusable `CurationService` from the digest path.
- Flow:
  - ingest
  - normalize
  - dedupe
  - enrich
  - rank
  - threshold/window filter
- Ensure all calendar-selected events receive enrichment.

### Google Calendar integration

- Replace `src/integrations/calendar.py` stub with a real Google Calendar implementation using:
  - `google-api-python-client`
  - `google-auth-httplib2`
  - `google-auth-oauthlib`
- Authenticate with a stored OAuth refresh token for the calendar owner.
- Add a local bootstrap helper that:
  - runs the one-time OAuth flow
  - creates or validates the target secondary calendar
  - prints the refresh token + calendar ID
- Use deterministic publication keys and Google event IDs.
- Store sync metadata in `extendedProperties.private`.

### Calendar event formatting

- Build plain-text descriptions with:
  - `What:`
  - `Why it fits:`
  - `Links:`
- Include canonical/source event URL and a Google Maps link when a location exists.
- If `end_datetime` is missing, fall back to `start + 120 minutes`, mark as unspecified where supported, and note that the source did not provide an end time.

### Sync, persistence, and admin

- Add `calendar_sync_runs` persistence with counts and error tracking.
- Add a daily `sync_google_calendar` job at 7:00 AM America/Chicago.
- Add admin endpoints for:
  - latest sync status
  - dry-run preview
  - manual sync trigger
- Keep sharing manual in Google Calendar for v1.

## Test plan

- Unit tests for:
  - publication key and Google event ID generation
  - description builder
  - fallback copy
  - map-link generation
  - settings defaults and enabled-only validation
- Sync tests for create/update/delete/no-op behavior.
- Integration tests for digest reuse, scheduler wiring, admin endpoints, and sync-run persistence.

## Assumptions and defaults

- The repo’s “plans folder” is `docs/plans/`.
- Defaults:
  - invite-only shared calendar
  - manual sharing outside the app
  - 21-day publish window
  - 0.65 minimum score
  - 7:00 AM CT daily sync
  - concise what/why/link descriptions
- Public calendar publishing, self-serve subscriber management, in-app invite management, and Apps Script deployment are out of scope for v1.
