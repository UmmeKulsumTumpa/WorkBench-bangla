# progress.md — WorkBench → Bangla (source of truth)

Spec: `docs/design/spec.md` (re-read §0 on every resume).
Resume protocol: read this file → `git log --oneline -15` → continue from the "Current step" section. Always `source env.sh` first; use `uv run --frozen`.

## Status

| Phase | State | Note |
|---|---|---|
| 0 Bootstrap | ✅ | progress.md, .gitignore, spec, project-local toolchain (`env.sh`, `.tools/`) |
| 1 Setup & reconnaissance | ✅ | smoke test reproduces 24/24 Revisited; provider patch + probe (4 free models); schema.md; pilot_design.md draft |
| 2 Bangla translation | 🛑 | **STOP (a): waiting for owner review.** 204 variants translated + 2 independent review cycles (cycle 1: 99 rows, cycle 2: 42 rows); 690 BN tasks rendered, all checks pass |
| 3 Pilot run | ✅ | gemma4:31b: EN 81.1% vs BN 82.2% (p=1.0); failure analysis + pilot_report.md + HTML report (artifact) done |
| 3b Conditions C2–C6 (owner, 2026-10-05) | 🔄 | `--condition` flag, BN assets, runner, generic comparison, docs: ✅ (PRs #1–#3). **C6 pilot run + report: ✅** (gemma4:31b, 74/90 vs C0 73/90, p=1.0). Other runs (c2–c5, repeats): ⬜ waiting for owner review of the BN prompt + budget approval |
| 4 Extensions | ⬜ | owner instruction only (300 tasks only if the 90-task runs show a finding) |

## Current step

C6 report published (private artifact): https://claude.ai/artifact/RwtdFQ5pvZ4uVXdrQNuzGc; regenerate with `python3 scripts/build_report_html.py --comparison_id pilot_ollama-gemma4-31b_c6_vs_c0` and republish `report_fragment.html`. C6 code: tag `run/pilot-c6-gemma4-31b` (0950e72). Follow-ups: issue #9.

Phase 3b: **C6 pilot is done** (296 requests, 2026-10-05) and compared with C0: `results/comparisons/pilot_ollama-gemma4-31b_c6_vs_c0/` (report.md, report.html, failure analysis). C2–C5 are built but not run.

Next, waiting for the owner:
- (1) **Review the Bangla prompt wording**, including "আগামী শুক্রবার" (md:120 read it as Dec 1; the same phrase gave Dec 8 in md:169): `docs/conditions/translation_review.md` for the system prompt and tool descriptions, `docs/translation/template_review.md` for the task templates (STOP (a)). Edits go to `WorkBench/data/conditions/bn/*.json` (runbook §6). If wording changes, C6 (and c1–c4) must be re-run.
- (2) **Optional repeat runs** `c0-rep2` and `c6-rep2` (about 342 requests each; `--run_label rep2`) to measure the noise floor. Needs owner approval first (rule 6).

To regenerate the C6 report: `python3 scripts/build_report_html.py --comparison_id pilot_ollama-gemma4-31b_c6_vs_c0`. To regenerate the C1 report, use the C1 id, then re-publish `report_fragment.html` to artifact https://claude.ai/artifact/6Nd3cAmYaD5sDRT5WsGa2q.

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
- 2026-10-04 #10 — Ollama Cloud (docs, 2026-10-04; see `docs/harness/ollama_cloud.md`): base `https://ollama.com/v1` (`api.ollama.com` 301-redirects to it), Bearer auth; the free tier is now **monthly credits** with **1 concurrent request**; `tools` and `temperature` supported; `tool_choice` and `response_format` structured outputs NOT supported. WorkBench `--structured_outputs` = native `tools=` (not response_format), so it is compatible. The 17 live models from the unauthenticated `/api/tags` include gpt-oss:20b/120b, gemma4:31b, nemotron-3-nano:30b, glm-5.3-flash, deepseek-v4.1-flash, minimax-m2.7 (no qwen3 on cloud).
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
- 2026-10-04 #22 — **STOP (b) passed by owner instruction:** "run the 90-task pilot on gemma4:31b and gimme a html report". Model `ollama-gemma4-31b` (gemma4:31b, Ollama Cloud free tier), C1, settings as `docs/design/pilot_design.md` §4 (`--tool_selection all`, `--act_without_confirmation`, `--structured_outputs`, `--workers 1`, `--log_traces`, `--resume`). Budget ≈640 requests. **STOP (a) is NOT completed:** the owner has not yet reviewed the BN translations (machine-translated + 2 independent model-review cycles). Recorded as a threat to validity; if the owner later edits translations, the BN side must be re-run.
- 2026-10-04 #23 — **Pilot result (gemma4:31b, C1, EN 11:42–11:47, BN 11:47–11:54 local):** completion EN 73/90 = 81.1%, BN 74/90 = 82.2%. Δ = +1.1 pp, 95% paired-bootstrap CI [−6.7, +8.9], exact McNemar p = 1.0 (6 EN-only, 7 BN-only). Side effects: EN 16.7%, BN 12.2% (Δ −4.4 pp, CI [−11.1, +2.2]). Domain-mix-weighted completion: EN 76.7%, BN 77.3%. Requests: EN 445 + BN 433 = 878 (4.9/task, above the 3.6 smoke10 estimate); no 429/402/5xx. Agent errors (step limit): EN 1, BN 2. Interpretation: no detectable EN–BN gap for this model on this sample (the pilot can only rule out large gaps, roughly > 9 pp).
- 2026-10-04 #24 — Failure analysis (model-labelled, 33 failed runs): 0/16 BN failures primarily `multilingual`. One secondary multilingual case: md:169, "আগামী শুক্রবার" read as Dec 1 instead of Dec 8. BN language behaviour: 88/88 answers in Bangla; Bengali digits used in prose but never in tool arguments; 0/345 tool arguments contained Bangla script; 1 invalid tool name (BN crm:77). The HTML report is published as a private artifact. `report.html` is a standalone document; `report_fragment.html` is the version used for artifact publishing. The first `report.html` was a bare fragment that the owner reported as showing nothing; fixed.

- 2026-10-05 #25 — **Single repo, conditions as a flag (owner decision).** The owner considered one git branch per condition (C0–C5); chose instead one codebase where a `--condition` flag selects prompt/tool-description/output-language variants, so EN/BN runs of every condition come from the same code and can be compared without branch switching. Short-lived feature branches only while building a condition; tag each run (`run/<scope>-<cond>-<model>`). Repo: the outer `workbench` project is now the only git repo and tracks `WorkBench/` as plain files (base upstream `49c7dfd` + our 4 commits up to `b3dd57b`). The old nested `WorkBench/.git` was moved to `.tools/WorkBench.git.bak` (not deleted). Remote: private `https://github.com/UmmeKulsumTumpa/WorkBench-bangla`. Branch renamed `master` → `main`.
- 2026-10-05 #26 — **Next plan (owner):** run C2–C5 on the same 90 pilot tasks (C0/C1 already done) and compare. Expand to 300 tasks only if a finding appears; the full 690 is not planned yet. Conditions: C2 BN task + BN system prompt; C3 = C2 + BN tool descriptions; C4 BN task + English output forced; C5 EN task + Bangla output forced. Plus 2 repeat runs of C0 to measure the noise floor. Estimate ≈ 440 requests per run, ≈ 2,650 in total. Claude Code does all prep (translation, code, analysis); the only external calls are inference on the free tier.

- 2026-10-05 #27 — **Condition flag built (PR #1).**
  - `--condition c0..c5` and `--run_label` are in the harness, with Bangla assets in `WorkBench/data/conditions/bn/`.
  - Structured mode sends only a short system prompt: the date line, the act line and, for c4/c5, an output-language line. So c2 translates exactly those lines, and c3 adds the 27 tool descriptions.
  - Argument descriptions (generated from the argument names) and tool observations stay English in every condition.
  - Owner-requested git workflow: feature branch → PR → merge into `main`.
- 2026-10-05 #28 — **Runner and generic comparison (PR #2).**
  - Comparisons are now reference vs treatment (`_ref`/`_treat`; schema v2), because `_en`/`_bn` would mislabel c5 and repeat runs.
  - The C1-vs-C0 pilot was regenerated with the new script: all 63 metrics and all per-task rows are identical.
  - Raw pilot runs moved to `WorkBench/data/results/c0/` and `c1/`.
  - Safety: a finished run is final. Its step-limit errors are real outcomes; before this change, an accidental `--resume` of c0 would have re-run 1 task and changed the baseline. `--retry_errors` is the explicit override.
  - Run metadata now records the run-time git commit and a dirty flag, and the runner refuses to start with uncommitted harness changes.
- 2026-10-05 #29 — **Docs restructured (PR #3).**
  - Root `README.md` is the entry point: conditions, results summary, folder map with output folders.
  - `docs/` is split by topic (design, conditions, runbook, data, translation, harness). The spec moved from `docs/superpowers/specs/` to `docs/design/spec.md`.
  - `patches/` was removed: it no longer covered the harness, and `git diff` against upstream `49c7dfd` shows every change.
  - Results moved to `results/comparisons/`, `results/logs/` and `results/summary.csv`.
  - Older log entries above keep their original paths as history.

- 2026-10-05 #30 — **C6 added (issue #4).** The owner's teammates ran the Bangla condition with a Bangla system prompt, English tool descriptions and the reply language *forced* to Bangla. C2 leaves the reply language free, so it would differ from their setup by one prompt line. C6 = C2 + the Bangla output-language line (asserted in a test). The owner's next runs are **C6 and C0 (repeat `rep2`)**, set up the same as the teammates'.

- 2026-10-05 #31 — **STOP (b) passed for C6 (owner):** "yes, match … start with the c6". The settings match the collaborators' (gemma4:31b, structured outputs, act without confirmation, all tools, temperature 0, 20 steps). Budget: about 441 requests, cap 1,800, Ollama Cloud free tier. C0-rep2 is deferred: the owner treats the 2026-10-04 C0 pilot as the all-English reference. Executed subagent-driven from the plan `docs/design/plans/2026-10-05-c6-pilot-run.md` (issue #6).
- 2026-10-05 #32 — **Request counts corrected (issue #7).** `n_llm_requests` / `total_llm_requests` were computed as the number of trace steps, but in native tool-calling mode one LLM response can carry several tool calls, each its own step with the same `llm_input`. The fix counts distinct `llm_input` per task, which matches the `HTTP/1.1 200 OK` lines in the run logs exactly. Pilot: c0 445 → 340, c1 433 → 342 (total 878 → 682; 4.9 → 3.8 requests/task). Smoke10: c0 37 → 34, c1 34 → 31 (71 → 65). C6 pilot: 296 (log count; the old method gave 375). Projections recomputed at 3.8/task: about 342 per 90-task run. `metrics.csv`, `paired.csv` and `summary.csv` are unchanged. The dated entries above keep the old numbers as history.
- 2026-10-05 #33 — **C6 pilot result (gemma4:31b, 90 tasks, 2026-10-05 16:12–16:18 local; C0 is the 2026-10-04 11:42 run).** Completion C0 73/90 = 81.1%, C6 74/90 = 82.2%. Δ = +1.1 pp, 95% paired-bootstrap CI [−7.8, +10.0], exact McNemar p = 1.0 (7 C0-only, 8 C6-only, 66 both correct, 9 both wrong). Side effects 16.7% → 8.9% (Δ −7.8 pp, CI [−15.6, +0.0]). Domain-mix-weighted completion 76.7% vs 77.8%. Requests: C0 340, C6 296; no 429/402/5xx.
  - Failure analysis (33 failed runs, model-labelled): 0/16 C6 failures primarily `multilingual`; 3 secondary (md:120, email:41, analytics:20). 88/88 non-empty answers in Bangla; Bengali digits in prose only; 0/285 tool arguments with Bangla script; 1 invalid tool name (crm:77).
  - Relative-date errors: 2–3 of 7 C6-only failures vs 0 of 8 C0-only (analytics:98 resolved the weekday correctly and erred on the baseline day, so it is not counted). Post hoc; a hypothesis for repeated runs.
  - md:120 "আগামী শুক্রবার" → Dec 1 stays reasoning-primary, but may be a translation-fidelity issue (the same phrase gave Dec 8 in md:169): for the native-speaker review.
  - New in C6: 2 empty final answers (crm:74, md:149), no visible cause; C0 had 0.
  - Analytics is lower in C6 (87% → 67%, 3 vs 0 discordant); descriptive only at n = 15.
  - Threats: C0 and C6 ran on different days (provider drift possible), no C0 repeat (noise unmeasured), unreviewed BN prompt, one model, n = 90.

## Blockers / needs-human

- ~~B1: OLLAMA_API_KEY empty~~ — resolved 2026-10-04 (owner pasted the key).
- Ollama Cloud: which models count as free "starter" models (vs credit-heavy) is unpublished — the probe and credit usage page will tell. Owner may need to check the credit balance at ollama.com/settings after the probe.

## Verified facts about the repo

- Our WorkBench changes (originally on the nested `bangla-eval` branch: fbfa4d3 providers, 8372c87 drop non-free models; since 2026-10-05 tracked in this repo, plus the condition flag). WorkBench tests: 283 pass; project tests: 19 pass. Free Ollama Cloud registry keys: `ollama-gpt-oss-20b`, `ollama-gpt-oss-120b`, `ollama-nemotron-3-nano-30b`, `ollama-gemma4-31b`; local: `ollama-local-qwen3-8b`.
- Upstream commit 49c7dfd (2026-08-18). `requires-python >=3.12`; uv 0.12.23; CPython 3.12.15. `uv sync --frozen` OK.
- Console scripts (pyproject): `workbench-inference = src.cli:inference`, `workbench-evaluate = src.cli:evaluate`, `workbench-generate-data = src.cli:generate_data`.
- Task CSV dirs: `data/processed/tasks_and_outcomes/` has the top-level files plus `v1/`, `v2026-05-17/`, `v2026-05-19/`. 690 rows: email 90, calendar 110, crm 80, analytics 120, pm 80, multi_domain 210. 69 base templates × 10 tasks each; no base appears in two files.
- `chosen_template` ≠ `base_template` in 453/690 rows; there are 204 distinct chosen_templates, each with the same slot set as its base. `task` = chosen_template with slots filled. Anchored regex recovery works on 690/690 rows (680 unique parses, 10 ambiguous, all analytics `{natural_language_metric} {more_or_less}`; fix by restricting more_or_less to more|less). 46 distinct slot names. Script: `scripts/extract_templates.py` → `data_bn/templates_en.csv`.
- `workbench-evaluate` with no args uses `all_tools=False` → only `*_domains_*` result files (src/cli.py, `get_latest_results_path` in src/evals/metrics.py). Ground truth is selected per results file from its `_meta.json`; if there is no sidecar, v1 is used. No-arg run: 7 models; counts match `data/results/item_level_results.csv.gz` exactly; it writes no files. The README headline numbers are `_all_` runs → need `--all_tools` to compare.

## Request budget

| Provider | Observed cap | Used today | Projected next step |
|---|---|---|---|
| ollama_cloud | free tier: only 'included' models (4 found); 1 concurrent; monthly-credit cap unpublished; no rate-limit headers | 761 total on 2026-10-04 (probe 14 + smoke10 65 + pilot 682); 296 on 2026-10-05 (c6 pilot) | pilot: 682 req (3.8/task); no limit errors. **Next (optional): c0-rep2 + c6-rep2 on gemma4:31b, about 342 req each (cap 1,800 each). Needs owner approval.** |
