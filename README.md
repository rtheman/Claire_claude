# Claire — Personal AI Automation Assistant

Claire is a personal automation system built on [Claude Code](https://claude.ai/code). It organises work into **Skills** — self-contained units that bundle instructions, reference context, and execution scripts together. Skills are invoked via slash commands (`/gmail-invoice`) or triggered automatically on a schedule.

> **Status:** Active — one skill in production, more planned.

---

## Table of Contents

- [Why Claire Exists](#why-claire-exists)
- [System Architecture](#system-architecture)
- [Skills](#skills)
  - [gmail-invoice](#gmail-invoice)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Security Model](#security-model)
- [Deploying to a VPS (Hostinger)](#deploying-to-a-vps-hostinger)
- [Planned Skills](#planned-skills)

---

## Why Claire Exists

Claude Code's MCP integrations (Gmail, Google Drive) are useful for reading data interactively, but they cannot:
- Extract raw PDF attachment bytes from Gmail
- Target nested Google Drive folders by path

Claire bypasses these limitations by running **Python scripts that call Google APIs directly** via OAuth. Claude handles orchestration and decision-making; Python handles deterministic execution.

---

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Claude Code (local / VPS)           │
│                                                     │
│  User: "/gmail-invoice"                             │
│         │                                           │
│         ▼                                           │
│  SKILL.md  ──reads──▶  context.md                  │
│         │                                           │
│         ▼                                           │
│  Bash: gmail_invoice_fetch.py                       │
│         │                                           │
│         ├──▶  Gmail API  (fetch PDFs)               │
│         ├──▶  pdfplumber  (parse metadata)          │
│         └──▶  Drive API  (upload + archive)         │
│                                                     │
│  Output: JSON summary → formatted report to user    │
└─────────────────────────────────────────────────────┘
```

**Separation of concerns:**

| Layer | File | Responsibility |
|-------|------|----------------|
| Orchestration | `SKILL.md` | What to do, how to report it |
| Knowledge | `context.md` | Vendor config, mappings, edge cases |
| Execution | `scripts/*.py` | Deterministic API calls |
| Secrets | `auth/`, `.env` | OAuth tokens — never in code |

**Key design decisions:**
- **Skills-first:** every capability lives in `.claude/skills/<name>/` — self-contained, testable, replaceable.
- **Python for execution:** avoids MCP limitations; direct API access is more reliable and supports binary data.
- **Deliverables go to the cloud** (Google Drive, Sheets, Calendar); intermediates stay in `.tmp/` and are never committed.
- **Idempotent by design:** running any skill twice produces the same result — no duplicates, no data loss.

---

## Skills

### gmail-invoice

**Command:** `/gmail-invoice`  
**Schedule:** Weekly, every Monday  
**Purpose:** Fetch invoice PDFs from Gmail, parse metadata from PDF content, file to the correct Google Drive folder, and archive the source email.

**Vendors supported:**

| Vendor | Gmail sender | Drive destination |
|--------|-------------|-------------------|
| PremiumSIM | `no-reply@premiumsim.de` | `Housing 🏡/.../Mobile Telephone (PremiumSim)/Invoices/{YYYY}/` |
| Telekom | `rechnungonline@telekom.de` | `Housing 🏡/.../Internet (T-Mobile)/Invoices/{YYYY}/` |
| Google Fi | `payments-noreply@google.com` | `Housing 🏡/.../Mobile Telephone (Google Fi)/{YYYY}/` |

**Pipeline:**
```
Gmail search → download PDF attachment → pdfplumber parse
  → derive filename + year → Drive duplicate check
  → upload to correct year folder → archive Gmail message
  → JSON summary to stdout
```

**Filename conventions:**
- PremiumSIM: `PremiumSIM - Invoice (YYYY-MM-DD) - {Person}.pdf`
- Telekom: `Telekom Deutschland - Bill - YYYY-MM (YYYY-MM-DD).pdf`
- Google Fi: `Google Fi-YYYY-MM-DD.pdf`

**Optional flags:**
```bash
--vendor premiumsim|telekom|googlefi   # run one vendor only
--days N                               # look-back window (default: 35)
--dry-run                              # parse only, no uploads or archiving
```

**Auth:** Google OAuth 2.0. Token refreshes automatically. Manual re-auth only needed if the token is revoked — run `auth_google.py` locally, then copy `auth/token.json` to the server.

---

## Project Structure

```
claire_claude/
│
├── CLAUDE.md                          # Project-level instructions for Claude Code
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── .env.example                       # Template — copy to .env and fill in values
├── .gitignore
│
├── .claude/
│   └── skills/
│       └── gmail-invoice/
│           ├── SKILL.md               # Skill entrypoint (instructions + reporting format)
│           ├── context.md             # Vendor config, mappings, edge cases
│           └── scripts/
│               ├── gmail_invoice_fetch.py   # Main pipeline
│               ├── auth_google.py           # One-time OAuth setup (run locally)
│               └── setup.sh                 # Venv + dependency bootstrap
│
├── auth/                              # !! gitignored — never commit !!
│   ├── credentials.json               # Google OAuth client secret
│   └── token.json                     # Google refresh token
│
├── context/                           # Project-level background knowledge
│   ├── project_background.md
│   ├── glossary.md
│   └── known_issues.md
│
└── .tmp/                              # Intermediates — gitignored, disposable
```

---

## Setup

### Prerequisites
- Python 3.10+
- A Google Cloud project with Gmail API and Drive API enabled
- An OAuth 2.0 client secret downloaded as `auth/credentials.json`

### First-time setup

```bash
# 1. Clone the repo
git clone https://github.com/richleung/claire_claude.git
cd claire_claude

# 2. Bootstrap the environment
bash .claude/skills/gmail-invoice/scripts/setup.sh

# 3. Copy env template
cp .env.example .env
# (edit .env if you need to override default paths)

# 4. Place your Google OAuth client secret
mkdir -p auth
cp /path/to/your/client_secret.json auth/credentials.json

# 5. Run the one-time OAuth flow (opens a browser)
.venv/bin/python .claude/skills/gmail-invoice/scripts/auth_google.py
```

After step 5, `auth/token.json` is created and the skill is ready to run.

### Running manually

```bash
# Dry run (no uploads, no archiving)
.venv/bin/python .claude/skills/gmail-invoice/scripts/gmail_invoice_fetch.py --dry-run

# Full run
.venv/bin/python .claude/skills/gmail-invoice/scripts/gmail_invoice_fetch.py --days 35

# Single vendor
.venv/bin/python .claude/skills/gmail-invoice/scripts/gmail_invoice_fetch.py --vendor premiumsim
```

---

## Security Model

| Asset | Protection |
|-------|-----------|
| `auth/credentials.json` | gitignored; `chmod 600` on server |
| `auth/token.json` | gitignored; `chmod 600` on server; grants full Gmail modify + Drive access — treat like a password |
| `.env` | gitignored |
| `.claude/settings.local.json` | gitignored (may contain local paths) |
| API trigger token (VPS) | stored in `.env` only; never logged |

**Rules:**
- Never commit any file in `auth/`
- Never hardcode credentials, email addresses, or phone mappings in code that gets logged
- On the VPS, run as a non-root user; restrict SSH to key-based auth only
- If a token is compromised: revoke it immediately in [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials

---

## Deploying to a VPS (Hostinger)

This section covers running Claire autonomously on a VPS so skills execute on schedule without your laptop being on.

### Why a VPS

- Claude Code Routines (cloud scheduling) cannot execute Python scripts or access local credentials
- A VPS gives you a persistent, always-on environment with full Python and direct Google API access
- No Claude Code required at runtime — the Python scripts run standalone

### What to use

- **Provider:** Hostinger (or any Ubuntu VPS)
- **Tier:** Smallest available (~$5–6/month) — the scripts are lightweight
- **OS:** Ubuntu 22.04 LTS

### Architecture on VPS

```
/opt/claire/                          ← project root (git clone)
├── .claude/skills/gmail-invoice/
│   └── scripts/gmail_invoice_fetch.py
├── auth/
│   ├── credentials.json              ← copied manually via scp
│   └── token.json                    ← copied manually via scp
├── .env                              ← copied manually via scp
├── requirements.txt
├── .venv/                            ← created on VPS via setup.sh
└── logs/                             ← execution logs (gitignored)

cron (system)
└── Every Monday 09:00 HKT → run gmail_invoice_fetch.py

(optional) FastAPI app
└── POST /run-invoice  →  triggers script on demand
```

### One-time VPS setup

```bash
# 1. SSH into your VPS
ssh claire@your-vps-ip

# 2. Install Python
sudo apt update && sudo apt install -y python3 python3-venv python3-pip git

# 3. Create a non-root user to run Claire (if not done)
sudo useradd -m -s /bin/bash claire
sudo su - claire

# 4. Clone the repo
git clone https://github.com/richleung/claire_claude.git /opt/claire
cd /opt/claire

# 5. Bootstrap
bash .claude/skills/gmail-invoice/scripts/setup.sh

# 6. Transfer secrets (run from your LOCAL machine)
scp auth/credentials.json claire@your-vps-ip:/opt/claire/auth/credentials.json
scp auth/token.json        claire@your-vps-ip:/opt/claire/auth/token.json
scp .env                   claire@your-vps-ip:/opt/claire/.env

# 7. Lock down secret files on VPS
chmod 600 /opt/claire/auth/credentials.json
chmod 600 /opt/claire/auth/token.json
chmod 600 /opt/claire/.env

# 8. Patch get_services() — disable browser OAuth flow on headless server
#    (see note below)

# 9. Test with dry run
cd /opt/claire
.venv/bin/python .claude/skills/gmail-invoice/scripts/gmail_invoice_fetch.py --dry-run
```

> **Important — headless OAuth patch:** The script's `get_services()` function calls
> `flow.run_local_server(port=0)` as a fallback when the token is missing or expired.
> This opens a browser, which doesn't work on a headless VPS. Before deploying,
> patch this to raise a clear error instead:
> ```python
> # On VPS: replace run_local_server with a hard error
> raise RuntimeError(
>     "Token missing or expired. Re-run auth_google.py locally, "
>     "then scp auth/token.json to the server."
> )
> ```
> Token refresh (not initial auth) still works automatically — this only affects
> the first-time or revoked-token scenario.

### Cron schedule

```bash
# Edit crontab as the claire user
crontab -e

# Run every Monday at 09:00 server time
0 9 * * 1  cd /opt/claire && .venv/bin/python .claude/skills/gmail-invoice/scripts/gmail_invoice_fetch.py --days 35 >> logs/gmail_invoice_$(date +\%F).log 2>&1
```

Create the logs directory first:
```bash
mkdir -p /opt/claire/logs
```

### Optional: API trigger (FastAPI)

To fire the skill via HTTP POST (e.g. from a phone shortcut or another service):

```python
# trigger_api.py  (add to project root)
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import subprocess, os

app = FastAPI()
bearer = HTTPBearer()

def verify_token(creds: HTTPAuthorizationCredentials = Security(bearer)):
    if creds.credentials != os.environ["API_SECRET_TOKEN"]:
        raise HTTPException(status_code=401, detail="Unauthorised")

@app.post("/run-invoice")
def run_invoice(token=Depends(verify_token)):
    result = subprocess.run(
        [".venv/bin/python", ".claude/skills/gmail-invoice/scripts/gmail_invoice_fetch.py", "--days", "35"],
        cwd="/opt/claire", capture_output=True, text=True
    )
    return {"stdout": result.stdout, "returncode": result.returncode}
```

Run with: `uvicorn trigger_api:app --host 0.0.0.0 --port 8000`

Protect with a reverse proxy (nginx + HTTPS) — never expose port 8000 directly.

### Updating skills after deployment

```bash
# On VPS — pull code changes (scripts, context, SKILL.md)
cd /opt/claire && git pull

# If dependencies changed
.venv/bin/pip install -r requirements.txt

# If token expired — from your LOCAL machine:
.venv/bin/python .claude/skills/gmail-invoice/scripts/auth_google.py
scp auth/token.json claire@your-vps-ip:/opt/claire/auth/token.json
```

### Maintenance checklist

| Task | Frequency | How |
|------|-----------|-----|
| Check logs for errors | Weekly (or after each run) | `tail -50 /opt/claire/logs/gmail_invoice_*.log` |
| Update OS packages | Monthly | `sudo apt update && sudo apt upgrade` |
| Update Python deps | On requirements.txt change | `.venv/bin/pip install -r requirements.txt` |
| Rotate API secret token | Quarterly (if using API trigger) | Update `.env` on VPS, restart FastAPI |
| Verify token still valid | If errors appear | Re-run auth locally, scp token.json |

### Security hardening checklist

- [ ] SSH key-only authentication (`PasswordAuthentication no` in `/etc/ssh/sshd_config`)
- [ ] Firewall: allow only SSH (22) and HTTPS (443) — `ufw allow 22 && ufw allow 443 && ufw enable`
- [ ] Run as non-root `claire` user — never as root
- [ ] `chmod 600` on all files in `auth/` and `.env`
- [ ] HTTPS on FastAPI endpoint via nginx reverse proxy (if using API trigger)
- [ ] Bearer token on API endpoint stored in `.env`, not in code
- [ ] `fail2ban` installed to block SSH brute-force attempts

---

## Planned Skills

| Skill | Purpose | Status |
|-------|---------|--------|
| `calendar-scheduling` | Find free slots, propose and book meetings | Planned |
| `email-triage` | Label, summarise, and draft replies for incoming email | Planned |
| `drive-organiser` | File and tag documents in Google Drive by content | Planned |
| `finance-tracker` | Track recurring bills, flag anomalies | Planned |
