---
name: gmail-invoice
description: File invoice PDFs from Gmail into Google Drive and archive the source emails. Use when asked to "file invoices", "process invoices", or "file my invoices". Runs weekly every Monday.
disable-model-invocation: true
allowed-tools: Bash
---

# gmail-invoice

File invoice PDFs from Gmail (PremiumSIM, Telekom, Google Fi) into Google Drive and archive the source emails.

## Execution

```bash
cd "/Users/richleung/Library/CloudStorage/GoogleDrive-kleung.hkg@gmail.com/My Drive/Projects/Claire_claude"
.venv/bin/python "${CLAUDE_SKILL_DIR}/scripts/gmail_invoice_fetch.py" --days 35
```

Optional flags:
- `--vendor premiumsim|telekom|googlefi` — run only one vendor
- `--days N` — override the look-back window (default: 35)
- `--dry-run` — parse and report without uploading or archiving

## Reporting

The tool prints a JSON summary to stdout. Report to the user in this format:

```
Invoice Filing Summary — {date}

PremiumSIM:   {N} saved, {N} skipped (already exist), {N} errors
Telekom:      {N} saved, {N} skipped (already exist), {N} errors
Google Fi:    {N} saved, {N} skipped (already exist), {N} errors

Files saved:
- PremiumSIM - Invoice (2026-03-31) - Rich.pdf
- ...

Errors (if any):
- ...
```

## Supporting files

- Vendor config, phone mappings, Drive paths, edge cases: [context.md](context.md)
- Execution script: [scripts/gmail_invoice_fetch.py](scripts/gmail_invoice_fetch.py)
- First-time auth setup: [scripts/auth_google.py](scripts/auth_google.py)
- Environment setup: [scripts/setup.sh](scripts/setup.sh)

## Auth failure

If the tool fails with an auth error, run:

```bash
cd "/Users/richleung/Library/CloudStorage/GoogleDrive-kleung.hkg@gmail.com/My Drive/Projects/Claire_claude"
.venv/bin/python "${CLAUDE_SKILL_DIR}/scripts/auth_google.py"
```

This opens a browser, asks you to sign in with kleung.hkg@gmail.com, and saves a refresh token to `auth/token.json`.
