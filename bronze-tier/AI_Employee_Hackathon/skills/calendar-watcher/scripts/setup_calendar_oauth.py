#!/usr/bin/env python3
"""Setup OAuth for Google Calendar API.

This script performs the OAuth flow to obtain a refresh token for the Calendar watcher.
It uses the same credentials.json as Gmail (same OAuth client).

Usage:
    uv run python skills/calendar-watcher/scripts/setup_calendar_oauth.py

Prerequisites:
    - config/credentials.json must exist (from Gmail setup)
    - Google Calendar API must be enabled in Google Cloud Console
"""

import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

CREDENTIALS_PATH = Path("config/credentials.json")
TOKEN_PATH = Path("config/calendar_token.json")


def main() -> None:
    """Run OAuth flow and save token."""
    if not CREDENTIALS_PATH.exists():
        print(f"❌ Error: {CREDENTIALS_PATH} not found")
        print("\nPlease create OAuth credentials first:")
        print("1. Go to https://console.cloud.google.com/apis/credentials")
        print("2. Create OAuth 2.0 Client ID (Desktop app)")
        print("3. Download JSON and save as config/credentials.json")
        print("4. Enable Google Calendar API in the API Library")
        sys.exit(1)

    creds = None

    # Check if token already exists
    if TOKEN_PATH.exists():
        print(f"📄 Found existing token at {TOKEN_PATH}")
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    # If no valid credentials, run OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("🔐 Starting OAuth flow...")
            print("\nThis will open your browser to authorize Calendar access.")
            print("Please sign in and grant permissions.\n")

            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
        print(f"✅ Token saved to {TOKEN_PATH}")

    # Test the connection
    print("\n🧪 Testing Calendar API connection...")
    try:
        service = build("calendar", "v3", credentials=creds)
        calendar_list = service.calendarList().list(maxResults=1).execute()
        calendars = calendar_list.get("items", [])

        if calendars:
            print(f"✅ Successfully connected to Calendar API")
            print(f"   Primary calendar: {calendars[0].get('summary', 'Unknown')}")
        else:
            print("⚠️  Connected but no calendars found")

    except Exception as e:
        print(f"❌ Error testing Calendar API: {e}")
        sys.exit(1)

    print("\n✅ Setup complete!")
    print("\nNext steps:")
    print("1. Review config/calendar_config.json")
    print("2. Test the watcher: uv run python backend/watchers/calendar_watcher.py --once")
    print("3. Start continuous monitoring: uv run python backend/watchers/calendar_watcher.py")


if __name__ == "__main__":
    main()
