# progress.md — WorkBench → Bangla (source of truth)

Spec: `docs/superpowers/specs/2026-10-04-workbench-bangla-design.md` (re-read §0 on every resume).
Resume protocol: read this file → `git log --oneline -15` → continue from `## Current step`.

## Status

| Phase | State | Note |
|---|---|---|
| 0 Bootstrap (progress.md, .gitignore, spec) | ✅ | 2026-10-04 |
| 1 Setup & reconnaissance | 🔄 | starting 1.1 (uv install) |
| 2 Bangla translation | ⬜ | |
| 3 Pilot run | ⬜ | blocked on STOP (a), STOP (b), and empty OLLAMA_API_KEY |
| 4 Extensions | ⬜ | owner instruction only |

## Current step

Phase 1.1 — install `uv`, ensure Python 3.12. Next action: `brew install uv`.

## Decisions log

- 2026-10-04 — Superpowers 6.4.1 is installed. The owner's brief is treated as the approved written spec (saved verbatim-condensed to `docs/superpowers/specs/`). Interactive brainstorming Q&A was skipped because the owner explicitly asked for autonomy between stop points (user instructions override skill defaults).

## Blockers / needs-human

- **B1 (2026-10-04): `.env` contains key name `OLLAMA_API_KEY` but its value is EMPTY (0 chars).** This blocks the Ollama Cloud probe (Phase 1.6) and all Phase 3 runs. Action for owner: paste the key into `.env`. Work not needing API calls continues.

## Verified facts about the repo

(none yet)

## Request budget

| Provider | Observed cap | Used today | Projected next step |
|---|---|---|---|
| ollama_cloud | unknown (unpublished) | 0 | 0 (key empty) |
