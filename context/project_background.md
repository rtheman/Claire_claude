# Project Background

**Project:** Claire_claude
**Owner:** kleung.hkg@gmail.com
**Purpose:** Claire is a personal AI assistant built on Skills. Each Skill bundles its own instructions, context, and scripts — invoked via `/skill-name` or triggered on a schedule.

## What Claire Does

Claire executes Skills on demand or on a schedule, handling tasks across Gmail, Google Calendar, Google Drive, and more.

**On-Demand** — invoke directly with a slash command or natural language:
- "File my invoices" → `/gmail-invoice`
- "Find me a free slot next week for a 1-hour dentist appointment" → checks Google Calendar and proposes options
- "Reschedule my Thursday meeting to Friday afternoon" → finds availability, updates the event, notifies attendees

**Scheduled** — Skills run automatically on a fixed schedule (local cron or Claude Code `/schedule`).

## Skills

| Skill | Slash Command | Schedule | Location |
|-------|---------------|----------|----------|
| Gmail Invoice Filing | `/gmail-invoice` | Weekly, Monday | `.claude/skills/gmail-invoice/` |

## Planned Capability Areas

- **Email management** — filing, labelling, summarising, drafting replies
- **Calendar management** — finding open slots, scheduling, rescheduling, invites
- **Document management** — organising Drive files, generating summaries, creating reports
- **Personal finance** — filing invoices, tracking recurring bills, flagging anomalies

## Key Decisions

- **Skills-first:** Each capability is a self-contained Skill under `.claude/skills/`. Instructions, context, and scripts all live together.
- **Python scripts for execution:** Complex API work (Gmail attachments, Drive uploads) runs via bundled Python scripts — not MCPs, which lack raw attachment access and nested folder targeting.
- **Credentials:** Google OAuth artifacts in `auth/`. Never hardcoded.
- **Deliverables** go to cloud services (Google Drive, Sheets, Calendar); intermediates stay in `.tmp/`.
- **Virtual environment** is `.venv/` inside the project folder — fully isolated from global Python.
