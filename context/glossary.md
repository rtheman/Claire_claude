# Glossary

| Term | Definition |
|------|-----------|
| WAT | Workflows, Agents, Tools — the three-layer architecture this project runs on |
| Workflow | A markdown SOP in `workflows/` that Claude reads before executing a task |
| Tool | A deterministic Python script in `tools/` that does the actual execution |
| Skill | A named workflow exposed as a callable capability for Claude |
| Routine | A Skill scheduled to run automatically on a cron-like schedule via Claude.ai |
| Deliverable | Output meant for the user — stored in cloud services (Drive, Sheets, etc.) |
| Intermediate | Temporary processing file — stored in `.tmp/`, disposable |
