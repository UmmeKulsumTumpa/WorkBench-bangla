# progress.md — WorkBench → Bangla (source of truth)

Spec: `docs/superpowers/specs/2026-10-04-workbench-bangla-design.md` (re-read §0 on every resume).
Resume protocol: read this file → `git log --oneline -15` → continue from `## Current step

Phase 1.6 — the provider patch and `scripts/probe_provider.py` are being written by a subagent (TDD, commit on WorkBench branch `bangla-eval`, export to `patches/0001-providers.patch`). Next: (1) verify that patch's tests yourself, (2) run `cd WorkBench && uv run python ../scripts/probe_provider.py --dry_run` and then the real probe (≤14 requests, already authorized), (3) write `docs/schema.md`, (4) do 1.7 `docs/pilot_design.md`. In parallel: the glossary-inputs subagent is producing `scripts/recover_slots.py`, `data_bn/slot_inventory.csv`, and `data_bn/glossary_candidates.csv` (Phase 2.1 input).

## Decisions log

- 2026-10-04 — Superpowers 6.4.1 is installed. The owner's brief is treated as the approved written spec (saved verbatim-condensed to `docs/superpowers/specs/`). Interactive brainstorming Q&A was skipped because the owner explicitly asked for autonomy between stop points (user instructions override skill defaults).

- 2026-10-04 #2 — `brew install uv` failed verbatim: `Error: You have not agreed to the Xcode license. Please resolve this by running: sudo xcodebuild -license accept`. Used the official astral installer instead.
- 2026-10-04 #3 — **Owner rule (strict): nothing global; everything inside this folder.** The first uv install went into `~/.local/bin` and Python into `~/.local/share/uv`, `~/.cache/uv`, and `~/.config/uv` (all created 2026-10-04 09:14 by me; no shell profiles were edited). I relocated these to `.tools/` (gitignored); `env.sh` sets UV_CACHE_DIR, UV_PYTHON_INSTALL_DIR, OLLAMA_MODELS, and related variables to point inside the project. **Always `source env.sh` first.** The global artifacts are removed once the subagents finish.
- 2026-10-04 #4 — `WorkBench/` keeps its own `.git` (upstream pinned at 49c7dfd, 2026-08-18) on local branch `bangla-eval`. The outer repo ignores `WorkBench/`. Our patches to WorkBench are committed on `bangla-eval` and also exported as `patches/*.patch` in the outer repo, so collaborators can apply them. Rationale: keeps a clean diff against upstream and avoids a 70 MB vendored copy.
- 2026-10-04 #5 — **Translation unit = 204 `chosen_template` variants (grouped under 69 base templates), not just the 69 bases.** The task text is chosen_template + slots, and 66 bases have 3 rewordings (3 have 2). Translating only the bases would collapse the paraphrase variety present in EN → confound. Owner reviews all 204 (grouped by base) at STOP (a).
- 2026-10-04 #6 — Slot values are of two kinds: entity values that must stay byte-identical (names like `nadia` — lowercase in tasks!, emails, subjects, event_name, task_name, board, body) and natural-language values the agent interprets (natural_language_metric, natural_language_date, more_or_less, day_of_week, natural_language_time, …). The second kind gets translated through the glossary. This is to be specified in translation_policy.md and confirmed at STOP (a). (Inference: grading only checks DB state, so translating interpretive slots doesn't affect the grader.)

- 2026-10-04 #7 — Global uv artifacts removed (`~/.local/bin/{uv,uvx,python3.12}`, `~/.local/share/uv`, `~/.cache/uv`, `~/.config/uv`, all created by me today). `WorkBench/.venv` rebuilt on `.tools/python/cpython-3.12.15`.
- 2026-10-04 #8 — **BN file naming:** use `{stem}_bn_tasks_and_outcomes.csv`, not `{domain}_tasks_and_outcomes_bn.csv`. Reason (code-verified): `workbench-evaluate` finds GT as `data/processed/tasks_and_outcomes/{results_dir}_tasks_and_outcomes.csv`, and the results dir = tasks-file stem minus `_tasks_and_outcomes`. The spec's name would produce no GT match. Canonical copies are kept in `data_bn/` and copied into `WorkBench/data/processed/tasks_and_outcomes/` for runs. Pilot subsets: `pilot_en_tasks_and_outcomes.csv` / `pilot_bn_tasks_and_outcomes.csv` → results dirs `data/results/pilot_en/`, `pilot_bn/`. Fallback: `scripts/evals/calculate_metrics_for_single_file.py --ground_truth_path`.
- 2026-10-04 #9 — **Upstream bug (verified, `src/evals/inference.py:43`):** `_TOOLKIT_MAP` has no `"crm"` key, but 50 multi_domain tasks list `'crm'`, so with `--tool_selection domains` their CRM tools are silently dropped. Proposal: the pilot uses `--tool_selection all` (27 tools; same setting as README / Revisited headline runs; avoids the bug) instead of the spec's `domains`. To be confirmed by the owner at STOP (b). Not patched upstream (keeps comparability).
- 2026-10-04 #10 — Ollama Cloud (docs, 2026-10-04; see `docs/notes_ollama_cloud.md`): base `https://ollama.com/v1` (`api.ollama.com` 301-redirects to it), Bearer auth; the free tier is now **monthly credits** with **1 concurrent request**; `tools` and `temperature` supported; `tool_choice` and `response_format` structured outputs NOT supported. WorkBench `--structured_outputs` = native `tools=` (not response_format), so it is compatible. The 17 live models from the unauthenticated `/api/tags` include gpt-oss:20b/120b, gemma4:31b, nemotron-3-nano:30b, glm-5.3-flash, deepseek-v4.1-flash, minimax-m2.7 (no qwen3 on cloud).
- 2026-10-04 #11 — The owner pasted OLLAMA_API_KEY (57 chars) and said "You can use it while processing" → treated as rule-6 confirmation for the **Phase 1.6 probe only**: 7 models × 2 requests = 14 requests. The pilot still needs STOP (b).

## Blockers / needs-human

- ~~B1: OLLAMA_API_KEY empty~~ — resolved 2026-10-04 (owner pasted the key).
- Ollama Cloud: which models count as free "starter" models (vs credit-heavy) is unpublished — the probe and credit usage page will tell. Owner may need to check the credit balance at ollama.com/settings after the probe.

## Verified facts about the repo

- Upstream commit 49c7dfd (2026-08-18). `requires-python >=3.12`; uv 0.12.23; CPython 3.12.15. `uv sync --frozen` OK.
- Console scripts (pyproject): `workbench-inference = src.cli:inference`, `workbench-evaluate = src.cli:evaluate`, `workbench-generate-data = src.cli:generate_data`.
- Task CSV dirs: `data/processed/tasks_and_outcomes/` has the top-level files plus `v1/`, `v2026-05-17/`, `v2026-05-19/`. 690 rows: email 90, calendar 110, crm 80, analytics 120, pm 80, multi_domain 210. 69 base templates × 10 tasks each; no base appears in two files.
- `chosen_template` ≠ `base_template` in 453/690 rows; there are 204 distinct chosen_templates, each with the same slot set as its base. `task` = chosen_template with slots filled. Anchored regex recovery works on 690/690 rows (680 unique parses, 10 ambiguous, all analytics `{natural_language_metric} {more_or_less}`; fix by restricting more_or_less to more|less). 46 distinct slot names. Script: `scripts/extract_templates.py` → `data_bn/templates_en.csv`.
- `workbench-evaluate` with no args uses `all_tools=False` → only `*_domains_*` result files (src/cli.py, `get_latest_results_path` in src/evals/metrics.py). Ground truth is selected per results file from its `_meta.json`; if there is no sidecar, v1 is used. No-arg run: 7 models; counts match `data/results/item_level_results.csv.gz` exactly; it writes no files. The README headline numbers are `_all_` runs → need `--all_tools` to compare.

## Request budget

| Provider | Observed cap | Used today | Projected next step |
|---|---|---|---|
| ollama_cloud | monthly credits, 1 concurrent (exact cap unpublished) | 0 | probe: 14 requests (7 models × 2) |
