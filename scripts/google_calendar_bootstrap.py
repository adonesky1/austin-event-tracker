"""Bootstrap Google Calendar publishing credentials.

Usage:
  python3 scripts/google_calendar_bootstrap.py path/to/oauth-client.json
"""

import json
import sys


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/google_calendar_bootstrap.py path/to/oauth-client.json")
        raise SystemExit(1)

    client_secret_path = sys.argv[1]

    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/calendar"]
    flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, scopes=scopes)
    creds = flow.run_local_server(port=0)

    with open(client_secret_path, "r", encoding="utf-8") as handle:
        client_config = json.load(handle)

    installed = client_config.get("installed") or client_config.get("web") or {}
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    calendar = service.calendars().insert(
        body={"summary": "Austin Curated Events", "timeZone": "America/Chicago"}
    ).execute()

    print("\nSave these values in your environment:\n")
    print(f"GOOGLE_CALENDAR_CLIENT_ID={installed.get('client_id', '')}")
    print(f"GOOGLE_CALENDAR_CLIENT_SECRET={installed.get('client_secret', '')}")
    print(f"GOOGLE_CALENDAR_REFRESH_TOKEN={creds.refresh_token or ''}")
    print(f"GOOGLE_CALENDAR_ID={calendar['id']}")
    print("GOOGLE_CALENDAR_ENABLED=true")


if __name__ == "__main__":
    main()
