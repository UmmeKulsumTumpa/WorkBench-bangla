# progress.md — WorkBench → Bangla (source of truth)

Spec: `docs/superpowers/specs/2026-10-04-workbench-bangla-design.md` (re-read §0 on every resume).
Resume protocol: read this file → `git log --oneline -15` → continue from `## Current step`.

## Status

| Phase | State | Note |
|---|---|---|
| 0 Bootstrap (progress.md, .gitignore, spec) | ✅ | 2026-10-04 |
| 1 Setup & reconnaissance | 🔄 | 1.1, 1.2, 1.5 done; 1.3 partial (domains-only); 1.4 + Ollama doc research running in subagents |
| 2 Bangla translation | ⬜ | |
| 3 Pilot run | ⬜ | blocked on STOP (a), STOP (b), and empty OLLAMA_API_KEY |
| 4 Extensions | ⬜ | owner instruction only |

## Current step

Phase 1.3/1.4 — waiting for the repo-map subagent; after it finishes: (1) delete the global uv artifacts I created (see Decisions 2026-10-04 #3), (2) rebuild `WorkBench/.venv` with the project-local Python (`source env.sh && cd WorkBench && uv sync --frozen`), (3) re-run `uv run workbench-evaluate --all_tools` and compare it to the README and `retro/data/model_results.json`.

## Decisions log

- 2026-10-04 — Superpowers 6.4.1 is installed. The owner's brief is treated as the approved written spec (saved verbatim-condensed to `docs/superpowers/specs/`). Interactive brainstorming Q&A was skipped because the owner explicitly asked for autonomy between stop points (user instructions override skill defaults).

- 2026-10-04 #2 — `brew install uv` failed verbatim: `Error: You have not agreed to the Xcode license. Please resolve this by running: sudo xcodebuild -license accept`. Used the official astral installer instead.
- 2026-10-04 #3 — **Owner rule (strict): nothing global; everything inside this folder.** The first uv install went into `~/.local/bin` and Python into `~/.local/share/uv`, `~/.cache/uv`, and `~/.config/uv` (all created 2026-10-04 09:14 by me; no shell profiles were edited). I relocated these to `.tools/` (gitignored); `env.sh` sets UV_CACHE_DIR, UV_PYTHON_INSTALL_DIR, OLLAMA_MODELS, and related variables to point inside the project. **Always `source env.sh` first.** The global artifacts are removed once the subagents finish.
- 2026-10-04 #4 — `WorkBench/` keeps its own `.git` (upstream pinned at 49c7dfd, 2026-08-18) on local branch `bangla-eval`. The outer repo ignores `WorkBench/`. Our patches to WorkBench are committed on `bangla-eval` and also exported as `patches/*.patch` in the outer repo, so collaborators can apply them. Rationale: keeps a clean diff against upstream and avoids a 70 MB vendored copy.
- 2026-10-04 #5 — **Translation unit = 204 `chosen_template` variants (grouped under 69 base templates), not just the 69 bases.** The task text is chosen_template + slots, and 66 bases have 3 rewordings (3 have 2). Translating only the bases would collapse the paraphrase variety present in EN → confound. Owner reviews all 204 (grouped by base) at STOP (a).
- 2026-10-04 #6 — Slot values are of two kinds: entity values that must stay byte-identical (names like `nadia` — lowercase in tasks!, emails, subjects, event_name, task_name, board, body) and natural-language values the agent interprets (natural_language_metric, natural_language_date, more_or_less, day_of_week, natural_language_time, …). The second kind gets translated through the glossary. This is to be specified in translation_policy.md and confirmed at STOP (a). (Inference: grading only checks DB state, so translating interpretive slots doesn't affect the grader.)

## Blockers / needs-human

- **B1 (2026-10-04): `.env` contains key name `OLLAMA_API_KEY` but its value is EMPTY (0 chars).** This blocks the Ollama Cloud probe (Phase 1.6) and all Phase 3 runs. Action for owner: paste the key into `.env`. Work not needing API calls continues.

## Verified facts about the repo

- Upstream commit 49c7dfd (2026-08-18). `requires-python >=3.12`; uv 0.12.23; CPython 3.12.15. `uv sync --frozen` OK.
- Console scripts (pyproject): `workbench-inference = src.cli:inference`, `workbench-evaluate = src.cli:evaluate`, `workbench-generate-data = src.cli:generate_data`.
- Task CSV dirs: `data/processed/tasks_and_outcomes/` has the top-level files plus `v1/`, `v2026-05-17/`, `v2026-05-19/`. 690 rows: email 90, calendar 110, crm 80, analytics 120, pm 80, multi_domain 210. 69 base templates × 10 tasks each; no base appears in two files.
- `chosen_template` ≠ `base_template` in 453/690 rows; there are 204 distinct chosen_templates, each with the same slot set as its base. `task` = chosen_template with slots filled. Anchored regex recovery works on 690/690 rows (680 unique parses, 10 ambiguous, all analytics `{natural_language_metric} {more_or_less}`; fix by restricting more_or_less to more|less). 46 distinct slot names. Script: `scripts/extract_templates.py` → `data_bn/templates_en.csv`.
- `workbench-evaluate` with no args uses `all_tools=False` → only `*_domains_*` result files (src/cli.py, `get_latest_results_path` in src/evals/metrics.py). Ground truth is selected per results file from its `_meta.json`; if there is no sidecar, v1 is used. No-arg run: 7 models; counts match `data/results/item_level_results.csv.gz` exactly; it writes no files. The README headline numbers are `_all_` runs → need `--all_tools` to compare.

## Request budget

| Provider | Observed cap | Used today | Projected next step |
|---|---|---|---|
| ollama_cloud | unknown (unpublished) | 0 | 0 (key empty) |
