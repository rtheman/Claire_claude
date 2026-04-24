# gmail-invoice: Reference Context

## Vendors

| Vendor | Gmail sender | Drive destination (under My Drive) |
|--------|-------------|-------------------------------------|
| PremiumSIM | no-reply@premiumsim.de | `Housing 🏡/.../Mobile Telephone (PremiumSim)/Invoices/{YYYY}/` |
| Telekom | rechnungonline@telekom.de | `Housing 🏡/.../Internet (T-Mobile)/Invoices/{YYYY}/` |
| Google Fi | payments-noreply@google.com | `Housing 🏡/.../Mobile Telephone (Google Fi)/{YYYY}/` |

## Phone-to-name mapping (PremiumSIM only)

| Phone suffix | Person |
|-------------|--------|
| `0493` | Rich |
| `0046` | Helena |
| `1254` | Henric |
| `1274` | Marko |

## Filename conventions

| Vendor | Format | Example |
|--------|--------|---------|
| PremiumSIM | `PremiumSIM - Invoice (YYYY-MM-DD) - {Person}.pdf` | `PremiumSIM - Invoice (2026-03-31) - Rich.pdf` |
| Telekom | `Telekom Deutschland - Bill - YYYY-MM (YYYY-MM-DD).pdf` | `Telekom Deutschland - Bill - 2026-03 (2026-02-28).pdf` |
| Google Fi | `Google Fi-YYYY-MM-DD.pdf` | `Google Fi-2026-03-15.pdf` |

## Known behaviour

- **Idempotent:** Running multiple times will not create duplicates — duplicate check runs before every upload.
- **PremiumSIM:** Sends 4 separate emails per billing cycle (one per family member). Expect 4 files per run when a new cycle has occurred.
- **Telekom:** Sends the invoice for the *next* calendar month (e.g. April invoice arrives in late March). Filename uses billing month, not issue date.
- **Google Fi:** Attachment filename uses Gmail delivery date (1 day after statement date). Tool always derives date from PDF content.
- **Token refresh:** Happens automatically. Manual re-auth only needed if the token is revoked.

## Edge cases

| Situation | How the tool handles it |
|-----------|------------------------|
| `auth/token.json` missing or expired | Tool triggers browser auth flow automatically |
| PDF text cannot be read (scanned image) | Logged to stderr as a parse error; counted in `errors` |
| Phone suffix not in PremiumSIM map | Logged as parse error; counted in `errors` |
| German month name not recognised (Telekom) | Logged as parse error; counted in `errors` |
| Statement date not found (Google Fi) | Logged as parse error; counted in `errors` |
| Year subfolder doesn't exist in Drive | Created automatically before upload |
| File already exists in Drive | Skipped; counted in `skipped` — no overwrite |
| Upload fails | Logged as error; message is NOT archived |
| Gmail archive fails | Logged as warning — file was already saved, non-fatal |
| No invoices found for a vendor | Empty `saved` array; noted in report |
| Vendor Drive folder not found | Logged as error; vendor skipped entirely |

## Prerequisites

| Requirement | Location | Notes |
|-------------|----------|-------|
| Google OAuth client secret | `auth/credentials.json` | Copied from `~/.config/gws/client_secret.json` |
| Gmail + Drive refresh token | `auth/token.json` | Run `scripts/auth_google.py` once to generate |
| Python venv with dependencies | `.venv/` | Run `scripts/setup.sh` if missing |

## Adding a new vendor

1. Add an entry to `VENDORS` in `scripts/gmail_invoice_fetch.py`
2. Add a `parse_<vendor>` function returning `{"date", "year", "filename"}` or `{"error": "..."}`
3. Register the parser in the `if config["parse"] == ...` block in `main()`
4. Add the vendor row to the Vendors table above
