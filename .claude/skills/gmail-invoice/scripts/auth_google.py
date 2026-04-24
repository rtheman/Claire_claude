#!/usr/bin/env python3
"""
One-time Google OAuth setup for Claire.

Run this once to authorise Claire to access Gmail.
It will open a browser window, ask you to sign in with kleung.hkg@gmail.com,
and save a refresh token to auth/token.json.

After this, tools/gmail_invoice_fetch.py will authenticate silently.

Usage:
    cd "/Users/richleung/Library/CloudStorage/GoogleDrive-kleung.hkg@gmail.com/My Drive/Projects/Claire_claude"
    .venv/bin/python scripts/auth_google.py
"""

from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

PROJECT_ROOT = Path(__file__).parent.parent
CREDENTIALS_FILE = PROJECT_ROOT / "auth" / "credentials.json"
TOKEN_FILE = PROJECT_ROOT / "auth" / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive",
]

def main():
    if not CREDENTIALS_FILE.exists():
        print(f"ERROR: {CREDENTIALS_FILE} not found.")
        print("Place your Google OAuth client secret at auth/credentials.json and retry.")
        return

    print("Opening browser for Google sign-in...")
    print(f"Sign in with: kleung.hkg@gmail.com")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_FILE.write_text(creds.to_json())
    print(f"\nSuccess! Token saved to: {TOKEN_FILE}")
    print("Claire can now access Gmail without further prompts.")

if __name__ == "__main__":
    main()
