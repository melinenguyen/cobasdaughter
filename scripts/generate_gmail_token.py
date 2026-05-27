#!/usr/bin/env python3
"""
Run this ONCE locally to generate the GMAIL_TOKEN_JSON GitHub secret.

Prerequisites:
  pip install google-auth google-auth-oauthlib google-api-python-client

Steps:
  1. Go to https://console.cloud.google.com
  2. Create a project (or select an existing one)
  3. APIs & Services → Library → search "Gmail API" → Enable
  4. APIs & Services → Credentials → + Create Credentials → OAuth 2.0 Client ID
       Application type: Desktop app   Name: CoBa Daily Brief (or anything)
  5. Click Download JSON → save as  scripts/client_secret.json
  6. Run:  python3 scripts/generate_gmail_token.py
  7. A browser tab opens — sign in as meline.nguyen@lixibox.com and allow access
  8. Copy the long base64 string printed at the end
  9. GitHub repo → Settings → Secrets → Actions → GMAIL_TOKEN_JSON → paste

NEVER commit client_secret.json or gmail_token.json — both are in .gitignore
"""

import os
import json
import base64
from pathlib import Path

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
]
SCRIPT_DIR       = Path(__file__).parent
CLIENT_SECRET    = SCRIPT_DIR / "client_secret.json"
TOKEN_FILE       = SCRIPT_DIR / "gmail_token.json"


def main():
    if not CLIENT_SECRET.exists():
        print(f"ERROR: {CLIENT_SECRET} not found.")
        print("Download it from Google Cloud Console → APIs & Services → Credentials")
        print("then save it as scripts/client_secret.json")
        return

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing existing token…")
            creds.refresh(Request())
        else:
            print("Opening browser for Gmail authorization…")
            print("Sign in as: meline.nguyen@lixibox.com")
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json())
        print(f"Token saved to {TOKEN_FILE}")

    # Verify the token works
    from googleapiclient.discovery import build
    svc     = build("gmail", "v1", credentials=creds)
    profile = svc.users().getProfile(userId="me").execute()
    print(f"\nConnected as: {profile['emailAddress']}")
    print(f"Total messages in mailbox: {profile.get('messagesTotal', '?')}")

    # Base64-encode for GitHub secret
    b64 = base64.b64encode(TOKEN_FILE.read_bytes()).decode()

    print("\n" + "=" * 64)
    print("Paste this entire string as your GMAIL_TOKEN_JSON GitHub secret:")
    print("=" * 64)
    print(b64)
    print("=" * 64)
    print("\nGitHub: Settings → Secrets and variables → Actions → GMAIL_TOKEN_JSON")
    print(f"\nDO NOT commit {TOKEN_FILE.name} or client_secret.json to git.")


if __name__ == "__main__":
    main()
