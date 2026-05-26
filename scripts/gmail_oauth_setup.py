#!/usr/bin/env python3
"""
CoBa's Daughter — Gmail OAuth Setup Helper
───────────────────────────────────────────
Run this ONCE on your local machine to generate the GMAIL_TOKEN_JSON
environment variable that daily_brief.py needs to read + send emails.

Usage:
    python3 scripts/gmail_oauth_setup.py --credentials /path/to/client_secret.json

What it does:
    1. Opens a browser window for you to authorise access to meline.nguyen@lixibox.com
    2. Captures the OAuth token
    3. Prints the base64-encoded token string you paste into your .env (or server secret)

Requirements:
    pip install google-auth-oauthlib google-auth google-api-python-client
"""

import argparse
import base64
import json
import os
import sys

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",   # read brand inbox
    "https://www.googleapis.com/auth/gmail.send",       # send daily brief
    "https://www.googleapis.com/auth/gmail.compose",    # create drafts
]

TARGET_ACCOUNT = "meline.nguyen@lixibox.com"


def run_oauth_flow(credentials_file: str) -> dict:
    """Run the OAuth flow and return the token as a dict."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("\n❌  Missing package. Run:")
        print("    pip install google-auth-oauthlib google-auth google-api-python-client\n")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)

    print(f"\n{'─'*60}")
    print("  A browser window will open.")
    print(f"  Sign in as:  {TARGET_ACCOUNT}")
    print(f"  Grant access to: Gmail (read + send)")
    print(f"{'─'*60}\n")

    # run_local_server opens the browser and handles the redirect automatically
    creds = flow.run_local_server(
        port=0,
        prompt="consent",           # always show consent screen so refresh_token is issued
        access_type="offline",      # required for refresh_token
    )

    token_data = {
        "token":         creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri":     creds.token_uri,
        "client_id":     creds.client_id,
        "client_secret": creds.client_secret,
        "scopes":        list(creds.scopes),
    }

    if not token_data.get("refresh_token"):
        print("\n⚠️  No refresh_token received.")
        print("   This usually means this Google account already authorised this app before.")
        print("   Fix: Go to https://myaccount.google.com/permissions, revoke the app, then re-run.\n")
        sys.exit(1)

    return token_data


def verify_token(token_data: dict):
    """Quick smoke-test: list labels to confirm the token works."""
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds   = Credentials.from_authorized_user_info(token_data)
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        print(f"\n✅  Token works. Connected as: {profile.get('emailAddress')}")
        return True
    except Exception as e:
        print(f"\n❌  Token verification failed: {e}")
        return False


def save_token_file(token_data: dict, output_path: str):
    """Save raw token JSON to a local file (for reference / Docker secrets)."""
    with open(output_path, "w") as f:
        json.dump(token_data, f, indent=2)
    print(f"   Raw token saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate GMAIL_TOKEN_JSON for CoBa's Daughter daily brief"
    )
    parser.add_argument(
        "--credentials",
        required=True,
        metavar="PATH",
        help="Path to the client_secret_*.json downloaded from Google Cloud Console",
    )
    parser.add_argument(
        "--save-token",
        metavar="PATH",
        default="",
        help="(Optional) also save the raw token JSON to this file path",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.credentials):
        print(f"\n❌  File not found: {args.credentials}\n")
        sys.exit(1)

    # ── Step 1: Run OAuth flow ───────────────────────────────────────────────
    token_data = run_oauth_flow(args.credentials)

    # ── Step 2: Verify ──────────────────────────────────────────────────────
    verify_token(token_data)

    # ── Step 3: Encode ──────────────────────────────────────────────────────
    token_json_str  = json.dumps(token_data)
    token_b64       = base64.b64encode(token_json_str.encode()).decode()

    # ── Step 4: Output ──────────────────────────────────────────────────────
    print(f"\n{'═'*60}")
    print("  ✦  YOUR GMAIL_TOKEN_JSON VALUE  ✦")
    print(f"{'═'*60}")
    print()
    print(token_b64)
    print()
    print(f"{'═'*60}")
    print()
    print("  Add this to your environment in ONE of these ways:")
    print()
    print("  Option A — .env file (local / Docker):")
    print(f"    GMAIL_TOKEN_JSON={token_b64}")
    print()
    print("  Option B — GitHub Actions secret:")
    print("    Name:  GMAIL_TOKEN_JSON")
    print(f"    Value: {token_b64[:40]}...  (paste the full string above)")
    print()
    print("  Option C — export in your shell (temporary test):")
    print(f"    export GMAIL_TOKEN_JSON='{token_b64}'")
    print(f"    python3 scripts/daily_brief.py")
    print(f"{'─'*60}\n")

    if args.save_token:
        save_token_file(token_data, args.save_token)

    print("  Done. The scheduler will now send emails automatically every day at 9AM GMT+7.\n")


if __name__ == "__main__":
    main()
