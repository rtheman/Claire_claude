# CLAUDE.md — Project

This file governs **this project specifically**. It extends the global `CLAUDE.md` (stored at `~/.claude/CLAUDE.md`). Rules here take precedence over global rules where they conflict.

---

## Architecture: Skills

This project is organised around **Skills** — self-contained units that bundle instructions, context, and execution scripts together. Each Skill lives in `.claude/skills/<skill-name>/` and is invoked via `/skill-name`.

**Skill structure:**
```
.claude/skills/<skill-name>/
├── SKILL.md       # Entrypoint — frontmatter + instructions (required)
├── context.md     # Reference material — vendor config, mappings, edge cases
└── scripts/       # Execution scripts called by the skill
```

**Separation of concerns:**
- `SKILL.md` — what to do and how to report it
- `context.md` — reference knowledge (loaded when needed)
- `scripts/` — deterministic Python/shell execution

**Why scripts instead of MCPs:** Gmail MCP cannot expose raw attachment bytes, and Drive MCP does not support `parents` in search queries. Direct API access via Python is required for reliable attachment download and nested folder targeting.

---

## Skill Inventory

| Skill | Slash Command | Schedule | Purpose |
|-------|---------------|----------|---------|
| [gmail-invoice](.claude/skills/gmail-invoice/SKILL.md) | `/gmail-invoice` | Weekly, Monday | File invoice PDFs from Gmail to Google Drive |

Before building a new Skill, check if one already exists or can be extended.

---

## Execution Rules

### Sequential vs. Parallel Tool Calls
- **Read-only operations** (fetching, listing, querying): may run in parallel.
- **Write operations** (Drive uploads, file overwrites): always run sequentially. Parallel writes risk race conditions and data loss.

### Skill Updates
- **Appending notes, gotchas, findings to `context.md`** → allowed without asking.
- **Rewriting `SKILL.md` instructions or changing the objective** → ask first, always.

---

## File Structure

```
CLAUDE.md                          # This file — project-level instructions
.env                               # Secrets (never commit)
.gitignore                         # Must include: .env, .tmp/, credentials.json, token.json
requirements.txt                   # Python dependencies for .venv

.claude/
  skills/
    gmail-invoice/
      SKILL.md                     # Skill entrypoint
      context.md                   # Vendor config, mappings, edge cases
      scripts/
        gmail_invoice_fetch.py     # Main pipeline script
        auth_google.py             # One-time OAuth setup
        setup.sh                   # Venv + dependency setup

auth/                              # Google OAuth artifacts
  credentials.json                 # gitignored
  token.json                       # gitignored

context/                           # Project-level background knowledge
  project_background.md
  glossary.md
  known_issues.md

.tmp/                              # Intermediate files — disposable, never commit
```

**Deliverables vs. intermediates:**
- **Deliverables** → cloud services (Google Drive, Sheets, Calendar).
- **Intermediates** → `.tmp/`, local, disposable, regenerable.

---

## Google Auth

`auth/credentials.json` and `auth/token.json` are Google OAuth artifacts. They are gitignored and must never be committed.

If they are missing or expired:
1. Flag this immediately — don't attempt to proceed with Google-dependent scripts.
2. Run the auth flow: `.venv/bin/python .claude/skills/gmail-invoice/scripts/auth_google.py`

---

## Self-Improvement Loop

When something breaks:
1. Read the full error and trace carefully.
2. Fix and retest. *If re-running costs API credits, check first.*
3. If two consecutive fix attempts fail on the same error, stop and escalate.
4. Once fixed, document the finding in the relevant `context.md`.

---

## Bottom Line

Read the Skill, run the scripts in the right order, recover from errors cleanly, and keep improving. Think before you act. Escalate when stuck.
