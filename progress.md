# progress.md — WorkBench → Bangla (source of truth)

Spec: `docs/superpowers/specs/2026-10-04-workbench-bangla-design.md` (re-read §0 on every resume).
Resume protocol: read this file → `git log --oneline -15` → continue from the "Current step" section. Always `source env.sh` first; use `uv run --frozen`.

## Status

| Phase | State | Note |
|---|---|---|
| 0 Bootstrap | ✅ | progress.md, .gitignore, spec, project-local toolchain (`env.sh`, `.tools/`) |
| 1 Setup & reconnaissance | ✅ | smoke test reproduces 24/24 Revisited; provider patch + probe (4 free models); schema.md; pilot_design.md draft |
| 2 Bangla translation | 🛑 | **STOP (a): waiting for owner review.** 204 variants translated + 2 independent review cycles (cycle 1: 99 rows, cycle 2: 42 rows); 690 BN tasks rendered, all checks pass |
| 3 Pilot run | ⬜ | waits for STOP (a) then STOP (b) |
| 4 Extensions | ⬜ | owner instruction only |

## Current step

**STOP (a): owner review of the Bangla translation.** Nothing runs until the owner replies.

What the owner should check (≈45–60 min):
1. **Policy:** `docs/translation_policy.md`. Decide each item in §7 plus these new questions:
   - (a) "তুমি" register everywhere.
   - (b) Dates written as `{date} তারিখে` (e.g. "6 ডিসেম্বর তারিখের").
   - (c) DB labels stay Latin and unquoted: list names `in progress`, `backlog`; CRM status `lead`, `won`; boards `front-end`; plot types `line`.
   - (d) Case marker after vowel-final Latin names: `Akira-এর` (current) or `Akira-র`?
   - (e) "delete … in the CRM" rendered `CRM থেকে … ডিলিট` (natural) rather than `CRM-এ`.
   - (f) Loanwords ইমেইল, মিটিং, টাস্ক, সাবজেক্ট, চার্ট, প্লিজ; "next Friday" → "আগামী শুক্রবার".
2. **Translations:** `docs/translation_review.md`. All 204 EN/BN variants are grouped under the 69 templates, each with one real rendered task. Check meaning first (quantifiers, conditions, step order), then naturalness, then consistency.
3. **Glossary:** `data_bn/glossary.csv`, column `value_bn` (months, weekdays, the 3 analytics metrics, comparators, durations).
4. Optional context: `data_bn/review/review_cycle1_summary.md` (what the reviewers changed and why).

How the owner gives corrections, either way:
- **Edit `data_bn/templates_bn.csv` directly**, column `template_bn`. Rules: keep each `{slot}` name exactly; inside quotes that are copied into a tool call, use `{slot!en}`; ASCII digits only. VS Code or Excel are both fine; BOM/CRLF is handled. For glossary values, edit `data_bn/glossary.csv` → `value_bn`.
- **Or** write corrections in chat as `T23.v2: <new Bangla>`, plus policy answers as 1(a)…(f).

After the owner's edits, I run:
1. `git diff data_bn/templates_bn.csv` → the reviewer subagent checks only the changed rows.
2. `python3 scripts/make_bn_tasks.py`, then `python3 scripts/make_pilot.py`, then `python3 scripts/build_translation_review.py`.
3. Commit.

Then Phase 3.1 (dry run, ~16 requests) → STOP (b).

Preview of the STOP (b) decisions (`docs/pilot_design.md`):
- Primary model `ollama-gemma4-31b` (gemma4:31b), second `ollama-gpt-oss-20b`.
- `--tool_selection all` instead of `domains` (upstream crm bug).
- `--act_without_confirmation`.
- About 720 requests per model for the pilot.

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

- 2026-10-04 #12 — Smoke test (1.3) verified: `uv run workbench-evaluate --all_tools` reproduces `retro/data/model_results.json` **exactly for all 24 Revisited models** (correct/total/side_effects), incl. README headline Claude Fable 5 674/690 = 97.7% (README "98%"), SE 1.9%, and GPT-4 (v1 GT) 48.1% / 16.2% (README "48% / 16%"). The 2024 paper's 43%/26% came from the older, stricter evaluator (README says so).
- 2026-10-04 #13 — **Probe (1.6), 14 requests, 2026-10-04 09:46:** gpt-oss:20b, gpt-oss:120b, nemotron-3-nano:30b, gemma4:31b → chat 200 + native tool call 200 with valid JSON args (latency 0.7–1.9 s). glm-5.3-flash, deepseek-v4.1-flash, minimax-m2.7 → **HTTP 402 "this model is not included in your free usage"** → removed from MODEL_REGISTRY (commit 8372c87) so they can never be called. No rate-limit headers are returned. Results: `results/probe/ollama_cloud_2026-10-04.json`.
- 2026-10-04 #14 — `uv run` (without `--frozen`) rewrote `WorkBench/uv.lock` (revision 3→5). Reverted. **Always use `uv run --frozen`.** The patch subagent's pyright run made one unintended PyPI version-check request (no install). Don't run pyright again.
- 2026-10-04 #15 — Translation register: "তুমি"-form imperatives (চ্যাটে সহকর্মী/অ্যাসিস্ট্যান্টকে লেখার ধরন). Dates rendered as "{date} তারিখে" to avoid inflecting the month name. To be confirmed at STOP (a).
- 2026-10-04 #16 — Review cycle 1 (independent reviewer): 99/204 rows changed (18 critical: list names/status transliterated into Bangla script → Latin; 63 major: unneeded quotes on enums, cross-batch terminology; 18 minor fluency). No meaning errors were found. Cycle 2 rules: board references stay Latin (`front-end বোর্ডে`); `CRM সিস্টেমে` → `CRM-এ`; enums keep EN case; curly quotes are OK; casual questions mirror EN punctuation.
- 2026-10-04 #17 — Checker refinements: allow DB enum words (list_name, CRM status/product_interest, traffic_source, plot types) and `CRM-`; GT-literal survival check excludes `field=` argument names (schema, not task text).
- 2026-10-04 #18 — Pilot subset built: 90 tasks (15/file), 63/69 templates, 90/204 variants, seed 20261004 (`data_bn/pilot/`).
- 2026-10-04 #19 — **Owner instruction:** "first run 10 tasks for both bangla and english" → a 10-task EN+BN smoke run on `ollama-gemma4-31b`, before the STOP (a) review is finished (owner's choice; translations may still change, so this run is exploratory, not part of the pilot). Subset: `data_bn/smoke10/` = the first N pilot rows per file (email 2, calendar 2, crm 1, analytics 2, pm 1, multi 2). Settings: `--structured_outputs --act_without_confirmation --tool_selection all --workers 1 --log_traces`. Budget: 20 tasks × ~4 = ~80 requests (cap 400).
- 2026-10-04 #20 — **Smoke10 result (gemma4:31b, C1, 2026-10-04 11:32–11:34 local):** EN 8/10, BN 8/10, identical per task. Both failures are multi_domain in BOTH languages with side effects, the same reasoning errors (wrong first-free-slot: EN 11:00 / BN 15:00 vs GT 13:00; wrong "fewest tasks" person: nia vs yuki), so not language-induced. Requests: EN 37 + BN 34 = **71 for 20 tasks (≈3.6/task)**; no 429/402/5xx. Projection: the pilot (180 tasks) needs ≈640 requests per model. Observation: the model's Bangla prose replies use Bengali numerals ("২১ নভেম্বর") while tool arguments stay ASCII (ungraded; note for the failure taxonomy). Output: `results/workbench_smoke10_ollama-gemma4-31b_c1/`, raw runs in `WorkBench/data/results/smoke10_{en,bn}/`.
- 2026-10-04 #21 — Fixes made during smoke10:
  - (1) WorkBench loads `.env` from its cwd (`src/cli.py:21`), so the first attempt failed with `OSError: Missing required environment variable 'OLLAMA_API_KEY'` (0 API calls). Fix: symlink `WorkBench/.env -> ../.env`; WorkBench's `.gitignore` covers `.env`.
  - (2) I passed `--out_dir ../results/...`, which wrote **outside the project** (`BARTA/results/`, created 11:34 by me). Moved back and deleted. `compare_en_bn.py` now refuses any out_dir outside the project.
  - (3) `tests/conftest.py` keeps pytest temp dirs in `.tools/pytest-tmp`. Earlier test runs used the macOS system temp dir (`/private/var/folders/.../pytest-of-cefalo`, auto-cleaned by the OS).
  - (4) Results CSVs contain fields >128 KB, so readers need `csv.field_size_limit(sys.maxsize)`.

## Blockers / needs-human

- ~~B1: OLLAMA_API_KEY empty~~ — resolved 2026-10-04 (owner pasted the key).
- Ollama Cloud: which models count as free "starter" models (vs credit-heavy) is unpublished — the probe and credit usage page will tell. Owner may need to check the credit balance at ollama.com/settings after the probe.

## Verified facts about the repo

- Our WorkBench commits on `bangla-eval`: fbfa4d3 (providers), 8372c87 (drop non-free models). Exported to `patches/0001-*.patch`, `patches/0002-*.patch`. 274 tests pass. Free Ollama Cloud registry keys: `ollama-gpt-oss-20b`, `ollama-gpt-oss-120b`, `ollama-nemotron-3-nano-30b`, `ollama-gemma4-31b`; local: `ollama-local-qwen3-8b`.
- Upstream commit 49c7dfd (2026-08-18). `requires-python >=3.12`; uv 0.12.23; CPython 3.12.15. `uv sync --frozen` OK.
- Console scripts (pyproject): `workbench-inference = src.cli:inference`, `workbench-evaluate = src.cli:evaluate`, `workbench-generate-data = src.cli:generate_data`.
- Task CSV dirs: `data/processed/tasks_and_outcomes/` has the top-level files plus `v1/`, `v2026-05-17/`, `v2026-05-19/`. 690 rows: email 90, calendar 110, crm 80, analytics 120, pm 80, multi_domain 210. 69 base templates × 10 tasks each; no base appears in two files.
- `chosen_template` ≠ `base_template` in 453/690 rows; there are 204 distinct chosen_templates, each with the same slot set as its base. `task` = chosen_template with slots filled. Anchored regex recovery works on 690/690 rows (680 unique parses, 10 ambiguous, all analytics `{natural_language_metric} {more_or_less}`; fix by restricting more_or_less to more|less). 46 distinct slot names. Script: `scripts/extract_templates.py` → `data_bn/templates_en.csv`.
- `workbench-evaluate` with no args uses `all_tools=False` → only `*_domains_*` result files (src/cli.py, `get_latest_results_path` in src/evals/metrics.py). Ground truth is selected per results file from its `_meta.json`; if there is no sidecar, v1 is used. No-arg run: 7 models; counts match `data/results/item_level_results.csv.gz` exactly; it writes no files. The README headline numbers are `_all_` runs → need `--all_tools` to compare.

## Request budget

| Provider | Observed cap | Used today | Projected next step |
|---|---|---|---|
| ollama_cloud | free tier: only 'included' models (4 found); 1 concurrent; monthly-credit cap unpublished; no rate-limit headers | 85 total on 2026-10-04 (probe 14 + smoke10 71) | smoke10 done: 71 req (2026-10-04), no limit errors; pilot (after STOP b): ≈640 req per model (3.6 req/task measured) |
