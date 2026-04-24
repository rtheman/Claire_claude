#!/usr/bin/env python3
"""
Full invoice filing pipeline for Claire.

Fetches invoice PDFs from Gmail, parses metadata, files to Google Drive,
and archives the Gmail message. Outputs a JSON summary to stdout.

Usage:
    python tools/gmail_invoice_fetch.py [--days N] [--vendor KEY] [--dry-run]

    --days N      Look back N days (default: 35)
    --vendor KEY  Run only one vendor: premiumsim | telekom | googlefi
    --dry-run     Parse and report without uploading or archiving
"""

import argparse
import base64
import io
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import pdfplumber

# ---------------------------------------------------------------------------
# Paths & scopes
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
CREDENTIALS_FILE = PROJECT_ROOT / "auth" / "credentials.json"
TOKEN_FILE = PROJECT_ROOT / "auth" / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive",
]

# ---------------------------------------------------------------------------
# Vendor config
# ---------------------------------------------------------------------------

VENDORS = {
    "premiumsim": {
        "name": "PremiumSIM",
        "query": "from:no-reply@premiumsim.de has:attachment",
        "parse": "premiumsim",
        "phone_map": {"0493": "Rich", "0046": "Helena", "1254": "Henric", "1274": "Marko"},
        # Drive path: vendor_folder_name / invoices_folder_name / {YYYY} /
        "drive_vendor_folder": "Mobile Telephone (PremiumSim)",
        "drive_invoices_folder": "Invoices",
    },
    "telekom": {
        "name": "Telekom",
        "query": "from:rechnungonline@telekom.de has:attachment",
        "parse": "telekom",
        "drive_vendor_folder": "Internet (T-Mobile)",
        "drive_invoices_folder": "Invoices",
    },
    "googlefi": {
        "name": "Google Fi",
        "query": "from:payments-noreply@google.com has:attachment",
        "parse": "googlefi",
        "drive_vendor_folder": "Mobile Telephone (Google Fi)",
        "drive_invoices_folder": None,  # files go directly under vendor/{YYYY}/
    },
}

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def get_services():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
    gmail = build("gmail", "v1", credentials=creds)
    drive = build("drive", "v3", credentials=creds)
    return gmail, drive

# ---------------------------------------------------------------------------
# Gmail helpers
# ---------------------------------------------------------------------------

def search_messages(gmail, query: str, after_date: str) -> list:
    full_query = f"{query} after:{after_date}"
    result = gmail.users().messages().list(userId="me", q=full_query, maxResults=50).execute()
    return result.get("messages", [])


def get_message(gmail, msg_id: str) -> dict:
    return gmail.users().messages().get(userId="me", id=msg_id, format="full").execute()


def get_attachment(gmail, msg_id: str, att_id: str) -> bytes:
    data = gmail.users().messages().attachments().get(
        userId="me", messageId=msg_id, id=att_id
    ).execute()
    b64 = data["data"].replace("-", "+").replace("_", "/")
    return base64.b64decode(b64 + "==")


def archive_message(gmail, msg_id: str):
    gmail.users().messages().modify(
        userId="me", id=msg_id,
        body={"removeLabelIds": ["INBOX"]}
    ).execute()


def find_pdf_parts(parts: list) -> list:
    found = []
    for part in parts:
        if part.get("mimeType") == "application/pdf" and part.get("filename"):
            found.append(part)
        if part.get("parts"):
            found.extend(find_pdf_parts(part["parts"]))
    return found

# ---------------------------------------------------------------------------
# Drive helpers
# ---------------------------------------------------------------------------

def find_folder(drive, name: str, parent_id: str = None):
    """Return the Drive folder ID for a folder with the given name and optional parent."""
    q = f"mimeType='application/vnd.google-apps.folder' and name='{name}' and trashed=false"
    if parent_id:
        q += f" and '{parent_id}' in parents"
    result = drive.files().list(q=q, fields="files(id,name,parents)", spaces="drive").execute()
    files = result.get("files", [])
    return files[0]["id"] if files else None


def create_folder(drive, name: str, parent_id: str) -> str:
    """Create a Drive folder and return its ID."""
    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = drive.files().create(body=meta, fields="id").execute()
    return folder["id"]


def file_exists(drive, filename: str, parent_id: str) -> bool:
    """Check whether a file with this name already exists in the given folder."""
    q = f"name='{filename}' and '{parent_id}' in parents and trashed=false"
    result = drive.files().list(q=q, fields="files(id)", spaces="drive").execute()
    return len(result.get("files", [])) > 0


def upload_pdf(drive, pdf_bytes: bytes, filename: str, parent_id: str) -> str:
    """Upload a PDF to Drive and return its file ID."""
    meta = {"name": filename, "parents": [parent_id]}
    media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype="application/pdf")
    f = drive.files().create(body=meta, media_body=media, fields="id").execute()
    return f["id"]


def get_or_create_year_folder(drive, config: dict, year: str, vendor_folder_id: str) -> str:
    """
    Return the ID of the year subfolder, creating it if needed.
    For vendors with an invoices_folder, the path is: vendor / invoices / year
    For Google Fi: vendor / year
    """
    invoices_folder_name = config["drive_invoices_folder"]

    if invoices_folder_name:
        invoices_id = find_folder(drive, invoices_folder_name, parent_id=vendor_folder_id)
        if not invoices_id:
            raise RuntimeError(f"'{invoices_folder_name}' folder not found under vendor folder")
        parent_id = invoices_id
    else:
        parent_id = vendor_folder_id

    year_id = find_folder(drive, year, parent_id=parent_id)
    if not year_id:
        print(f"  Creating year folder '{year}'...", file=sys.stderr)
        year_id = create_folder(drive, year, parent_id=parent_id)

    return year_id

# ---------------------------------------------------------------------------
# PDF parsing
# ---------------------------------------------------------------------------

def extract_text(pdf_bytes: bytes) -> str:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return "".join(page.extract_text() or "" for page in pdf.pages)


def parse_premiumsim(pdf_bytes: bytes, phone_map: dict) -> dict:
    text = extract_text(pdf_bytes)

    date_match = re.search(r"Datum\s+(\d{2})\.(\d{2})\.(\d{4})", text)
    if not date_match:
        return {"error": "Datum field not found"}
    day, month, year = date_match.groups()
    invoice_date = f"{year}-{month}-{day}"

    phone_match = re.search(r"Rufnummer\s+([\d\s]+)", text)
    if not phone_match:
        return {"error": "Rufnummer field not found"}
    phone = phone_match.group(1).replace(" ", "").strip()

    for suffix, person in phone_map.items():
        if phone.endswith(suffix):
            return {
                "date": invoice_date,
                "year": year,
                "filename": f"PremiumSIM - Invoice ({invoice_date}) - {person}.pdf",
            }
    return {"error": f"Unrecognised phone number: {phone}"}


def parse_telekom(pdf_bytes: bytes) -> dict:
    text = extract_text(pdf_bytes)

    MONTHS_DE = {
        "Januar": "01", "Februar": "02", "März": "03", "April": "04",
        "Mai": "05", "Juni": "06", "Juli": "07", "August": "08",
        "September": "09", "Oktober": "10", "November": "11", "Dezember": "12",
    }
    month_match = re.search(r"Festnetz-Rechnung\s+f[üu]r\s+(\w+)\s+(\d{4})", text)
    if not month_match:
        return {"error": "Billing month not found"}
    month_name, year = month_match.groups()
    month_num = MONTHS_DE.get(month_name)
    if not month_num:
        return {"error": f"Unrecognised German month: {month_name}"}
    billing_period = f"{year}-{month_num}"

    date_match = re.search(r"Datum\s+(\d{2})\.(\d{2})\.(\d{4})", text)
    if not date_match:
        return {"error": "Issue date not found"}
    day, mon, issue_year = date_match.groups()
    issue_date = f"{issue_year}-{mon}-{day}"

    return {
        "date": billing_period,
        "year": year,
        "filename": f"Telekom Deutschland - Bill - {billing_period} ({issue_date}).pdf",
    }


def parse_googlefi(pdf_bytes: bytes) -> dict:
    text = extract_text(pdf_bytes)

    MONTHS_EN = {
        "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
        "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
        "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
    }
    date_match = re.search(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(\d{1,2}),\s+(\d{4})", text
    )
    if not date_match:
        return {"error": "Statement date not found"}
    month_abbr, day, year = date_match.groups()
    date_str = f"{year}-{MONTHS_EN[month_abbr]}-{int(day):02d}"
    return {"date": date_str, "year": year, "filename": f"Google Fi-{date_str}.pdf"}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="File invoice PDFs from Gmail to Google Drive")
    parser.add_argument("--days", type=int, default=35)
    parser.add_argument("--vendor", help="Run only one vendor key")
    parser.add_argument("--dry-run", action="store_true", help="Parse only — no uploads or archiving")
    args = parser.parse_args()

    after_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y/%m/%d")

    try:
        gmail, drive = get_services()
    except Exception as e:
        print(json.dumps({"error": f"Auth failed: {e}"}))
        sys.exit(1)

    vendors = VENDORS
    if args.vendor:
        if args.vendor not in VENDORS:
            print(json.dumps({"error": f"Unknown vendor '{args.vendor}'. Available: {', '.join(VENDORS)}"}))
            sys.exit(1)
        vendors = {args.vendor: VENDORS[args.vendor]}

    summary = {}

    for vendor_key, config in vendors.items():
        name = config["name"]
        log = {"saved": [], "skipped": [], "errors": []}
        summary[name] = log

        print(f"\n[{name}] Searching Gmail...", file=sys.stderr)
        messages = search_messages(gmail, config["query"], after_date)
        print(f"[{name}] Found {len(messages)} message(s)", file=sys.stderr)

        # Find vendor Drive folder once per vendor
        if not args.dry_run:
            vendor_folder_id = find_folder(drive, config["drive_vendor_folder"])
            if not vendor_folder_id:
                err = f"Drive folder not found: '{config['drive_vendor_folder']}'"
                print(f"[{name}] ERROR: {err}", file=sys.stderr)
                log["errors"].append(err)
                continue

        for msg_ref in messages:
            msg_id = msg_ref["id"]
            try:
                message = get_message(gmail, msg_id)
            except Exception as e:
                err = f"Failed to fetch message {msg_id}: {e}"
                print(f"[{name}] ERROR: {err}", file=sys.stderr)
                log["errors"].append(err)
                continue

            pdf_parts = find_pdf_parts(message.get("payload", {}).get("parts", []))
            if not pdf_parts:
                continue

            for part in pdf_parts:
                att_id = part["body"].get("attachmentId")
                if not att_id:
                    continue

                try:
                    pdf_bytes = get_attachment(gmail, msg_id, att_id)
                except Exception as e:
                    err = f"Failed to download attachment: {e}"
                    print(f"[{name}] ERROR: {err}", file=sys.stderr)
                    log["errors"].append(err)
                    continue

                # Parse
                if config["parse"] == "premiumsim":
                    parsed = parse_premiumsim(pdf_bytes, config["phone_map"])
                elif config["parse"] == "telekom":
                    parsed = parse_telekom(pdf_bytes)
                else:
                    parsed = parse_googlefi(pdf_bytes)

                if "error" in parsed:
                    print(f"[{name}] PARSE ERROR: {parsed['error']}", file=sys.stderr)
                    log["errors"].append(parsed["error"])
                    continue

                filename = parsed["filename"]
                year = parsed["year"]
                print(f"[{name}] Parsed: {filename}", file=sys.stderr)

                if args.dry_run:
                    print(f"[{name}] DRY RUN — would file: {filename}", file=sys.stderr)
                    log["saved"].append({"file": filename, "dry_run": True})
                    continue

                # Find/create year folder
                try:
                    year_folder_id = get_or_create_year_folder(drive, config, year, vendor_folder_id)
                except Exception as e:
                    err = f"Could not resolve Drive folder for {filename}: {e}"
                    print(f"[{name}] ERROR: {err}", file=sys.stderr)
                    log["errors"].append(err)
                    continue

                # Duplicate check
                if file_exists(drive, filename, year_folder_id):
                    print(f"[{name}] EXISTS — skipping: {filename}", file=sys.stderr)
                    log["skipped"].append({"file": filename, "reason": "already_exists"})
                    continue

                # Upload
                try:
                    file_id = upload_pdf(drive, pdf_bytes, filename, year_folder_id)
                    print(f"[{name}] SAVED: {filename} (Drive ID: {file_id})", file=sys.stderr)
                    log["saved"].append({"file": filename, "drive_id": file_id})
                except Exception as e:
                    err = f"Upload failed for {filename}: {e}"
                    print(f"[{name}] ERROR: {err}", file=sys.stderr)
                    log["errors"].append(err)
                    continue

                # Archive Gmail message
                try:
                    archive_message(gmail, msg_id)
                    print(f"[{name}] ARCHIVED: {msg_id}", file=sys.stderr)
                except Exception as e:
                    print(f"[{name}] WARNING: Could not archive {msg_id}: {e}", file=sys.stderr)

    # Print summary JSON to stdout
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
