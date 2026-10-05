# CLAUDE.md: WorkBench → Bangla (project)

On every new session, read these in order before acting:
1. `.claude/HANDOFF.md`: current state, hard rules, next action, gotchas.
2. `progress.md`: the source of truth for status, decisions and the request budget.
3. `git log --oneline -15` and `gh issue list`.

Non-negotiables (details in HANDOFF §2):
- Free model tiers only, with the owner's approval of the projected requests before any run.
- Project-local tooling only: `source env.sh`, then `uv run --project WorkBench --frozen ...`.
- Issue → feature branch → PR (`Closes #N`) → merge. Never commit on `main`.
- Conditions are selected with `--condition`; each model and condition has its own folders.
- A finished run is final; repeats use `--run_label`. Never edit dated `progress.md` decision entries.
- Execute plans subagent-driven, with a review per task.

Entry points: `README.md` (overview and folder map) and `docs/README.md` (documentation index). Plans live in `docs/design/plans/`.
