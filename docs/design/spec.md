# PROJECT SPEC: WorkBench → Bangla cross-lingual agent evaluation

> Verbatim copy of the owner's brief (2026-10-04). This is the approved design; `progress.md` tracks execution.
> Personal research project; results will later be merged with two collaborators' OfficeBench and τ²-bench results.

## 0. Working rules (read first, re-read on every resume)

1. **progress.md is the source of truth.** Sections: `## Status` (phase table ✅/🔄/⬜ + note), `## Current step` (exact sub-step + exact next action), `## Decisions log` (dated, with rationale), `## Blockers / needs-human`, `## Verified facts about the repo`, `## Request budget` (per provider: observed daily cap, used today, projected next step). Update after EVERY completed sub-step and before stopping. `git commit` after each sub-step.
2. **On any new session:** read `progress.md`, then `git log --oneline -15`, then continue from `## Current step`. Do not redo completed phases.
3. **Use Superpowers** (brainstorming → writing-plans → executing-plans, subagent-driven development).
4. **Protect the main context.** Delegate bulky work to subagents (codebase reading, translation batches, translation review, data scripts, provider probes, literature notes). Main thread orchestrates, verifies, updates `progress.md`.
5. **Environment (hard):** macOS, Apple Silicon M1, 16 GB RAM. No Docker, no VMs, no background web servers. Pure Python via `uv` (Python 3.12+). If anything demands Docker → blocker.
6. **Free tiers only (hard).** Never select/call a paid model. If a run would exceed a free quota: slow down, wait, split across days — never switch to paid. Before the first API call of any phase, write projected request count + chosen models into `progress.md` and ask the owner to confirm.
7. **Secrets:** keys only from `.env`; never print/log/echo/commit. Missing/empty → blocker. Record key *names* only.
8. **Accuracy:** assert nothing about the repo not read. Label inferences. Record errors verbatim before fixing.
9. **Stop points (MUST wait):** (a) end of Phase 2 — owner reviews translation policy + 69 templates (native Bangla speaker); (b) before pilot run (rule 6 confirmation); (c) any blocker.

## 1. Research goal

RQ: do LLM agents complete the same realistic multi-step tasks less reliably when instructed in Bangla than in English, and how do failure types shift? Pipeline: WorkBench (English, COLM 2024) → Bangla task instructions → identical agents on EN and BN → compare task completion, harmful side effects, failure types.

Collaborators run the same design on OfficeBench and τ²-bench. All outputs (CSV schemas, metric names, failure-taxonomy labels, result tables) must be mergeable: plain CSV/JSON, formats documented in `docs/data/schema.md`. Correctness and reproducibility over speed.

Owner-stated facts (re-verify against code):
- Repo https://github.com/olly-styles/WorkBench (MIT). Paper Styles et al., COLM 2024 (openreview 4HNAwZFDcH; arXiv 2405.00823). 2026 follow-up "WorkBench Revisited" at `retro/main.pdf`.
- 690 tasks in `data/processed/tasks_and_outcomes/{email,calendar,customer_relationship_manager,analytics,project_management,multi_domain}_tasks_and_outcomes.csv`, columns `task, outcome, base_template, chosen_template, domains`. 69 unique base templates.
- Grading is outcome-centric (final sandbox DB state vs ground truth); entity values must stay byte-identical.
- Install `uv sync --frozen`. Console scripts: `workbench-evaluate`, `workbench-inference --model_name <name> --tasks_path <csv>`, `workbench-generate-data --force`. Flags: `--structured_outputs`, `--workers N`, `--log_traces`, `--resume`, `--tool_selection {all,domains}`.
- `MODEL_REGISTRY` in `src/evals/agent.py`: `ModelConfig(model_id, supports_temperature, provider)`, provider ∈ {openai, anthropic, google, openrouter}; OpenAI-compatible chat-completions. Prompt pieces: `PREFIX`, `SUFFIX`, `ACT_WITHOUT_CONFIRMATION_SUFFIX`, `build_system_prompt`.
- Ground truth versioned; use top-level (v2, 2026-corrected), not `v1/`.
- Frontier models near ceiling in EN (~98%); gap measurable on non-frontier/free models.

## 2. Translation policy (defaults — confirm at Stop Point (a))

"Translate the instruction side, keep the environment English" (MAPS, Hofman et al., EACL 2026 Findings) + preserve/translate/canonical field typing (BabelFlow, Peng et al., 2026, arXiv 2609.23490):
- **Preserve byte-identical:** tool names, argument names, JSON keys, IDs, emails, URLs, dates/times in original format, all ASCII digits. **Never Bengali numerals (০–৯).**
- **Translate:** natural-language instruction text of each template.
- **Canonical:** recurring nouns that must match a DB value (person/customer/project names, weekday words, status labels). Default: names in Latin script exactly as in DB; translate common nouns. Build `data_bn/glossary.csv`.
- Register: natural, polite-but-direct workplace Bangla.
- Conditions: **C1** BN task + EN system prompt/tools (primary, default). **C2** BN task + BN `PREFIX`/`SUFFIX` (secondary, later).
- Deliverable: parallel `<domain>_tasks_and_outcomes_bn.csv`, identical rows/columns, only `task` and `chosen_template` translated, `outcome` unchanged.

## 2.5 Models & providers — FREE TIERS ONLY

- Only key now: `OLLAMA_API_KEY` (Ollama Cloud). Later maybe `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`; adding a key must need only a registry entry. On "new key in .env" → re-run probe for it.
- Ollama Cloud: verify OpenAI-compatible base URL (`https://ollama.com/v1` vs `https://api.ollama.com/v1`) from docs.ollama.com; free tier "light usage", unpublished limits, likely 1 concurrent request. List live cloud models from API; pick tool-calling ones (candidates gpt-oss 120b/20b, qwen3.x, glm, kimi, deepseek-v4-flash — exact IDs from API).
- Patch `MODEL_REGISTRY` minimally: providers `ollama_cloud`, `ollama_local` (`http://localhost:11434/v1`, no key), `groq` (`https://api.groq.com/openai/v1`), configurable base_url + env-var name. One commit; document in `docs/harness/repo_map.md`.
- Probe `scripts/probe_provider.py`: one tiny chat + one tool-call test per candidate; record success, latency, 429/limit headers in progress.md.
- Quota discovery: dry run (3.1), watch 429/5xx, infer safe req/hour → `## Request budget`. If free quota can't sustain pilot in ~3 days → blocker recommending Groq/Gemini key; prepare local-Ollama fallback (`ollama pull qwen3:8b`, `--tool_selection domains`).
- Discipline: `--workers 1` on Ollama Cloud, exponential backoff on 429/5xx, always `--resume`, measure req/task in dry run, project totals before each run.
- Reproducibility: exact model ID, provider, temperature (0 where supported), run date in each `_meta.json`.

## 3. Phases

**Phase 1 — Setup & reconnaissance**
1. Install `uv`; Python 3.12+.
2. Clone into `./WorkBench` (plain subfolder); `uv sync --frozen`; record versions.
3. No-API smoke test: `uv run workbench-evaluate` on committed results; confirm it reproduces README numbers.
4. Subagent → `docs/harness/repo_map.md` (≤2 pages): template location/task generation, inference loop, evaluation & side effects, `--resume`/`_meta.json`, `MODEL_REGISTRY` + provider dispatch.
5. Subagent → `data_bn/templates_en.csv` (69 base templates + one example task + domain). Verify 69 and 690→exactly-one mapping.
6. Provider patch; Ollama Cloud probe; `docs/data/schema.md` (per-task result row, metrics file, failure-label file).
7. `docs/design/pilot_design.md`: ~90-task stratified pilot (15/CSV, fixed seed, max template coverage), model shortlist, paired evaluation (McNemar, bootstrap CI, side-effect rate, failure taxonomy), request-budget plan.

**Phase 2 — Bangla translation (no benchmark API spend)**
1. `docs/translation/policy.md` + `data_bn/glossary.csv` (scan DB CSVs in `data/processed/` for slot values).
2. Translate 69 templates → `data_bn/templates_bn.csv` (`template_en, template_bn, notes`); subagent per ~15; independent reviewer (placeholders intact, no Bengali numerals, no translated entity names, meaning, register). Max two fix cycles.
3. `scripts/make_bn_tasks.py`: render BN template with slot values recovered by aligning `chosen_template` vs `task`. Assert row count, identical outcome, placeholders filled, no stray English except preserved entities, no Bengali digits. Commit outputs to `data_bn/`.
4. `docs/translation/template_review.md`: side-by-side table of 69 EN/BN templates.
→ **STOP (a)** with instructions for owner review (owner edits `data_bn/templates_bn.csv`; then re-run reviewer on diff and regenerate).

**Phase 3 — Pilot (after approval of translations AND budget)**
1. Dry run: 2 EN + 2 BN tasks, `--log_traces --structured_outputs --tool_selection domains --workers 1`. Confirm UTF-8 end-to-end; measure req/task. → **STOP (b)**.
2. Pilot EN and BN, identical settings; `data/results/pilot_en_<model>`, `pilot_bn_<model>_c1`; `--resume`.
3. `workbench-evaluate` (v2 GT via `_meta.json`); `scripts/compare_conditions.py`: paired table, completion, side-effect rate, McNemar p, bootstrap 95% CI, per-domain — in `docs/data/schema.md` formats.
4. Failure analysis (BabelArena-adapted taxonomy: outcome / reasoning / planning / tool-use / control-flow / memory / multilingual [wrong-language output, language mixing, numeral/script error, language-induced tool misuse]) → `results/comparisons/pilot_ollama-gemma4-31b_c1_vs_c0/failure_analysis.md`, `results/failure_labels.csv`.
5. `results/comparisons/pilot_ollama-gemma4-31b_c1_vs_c0/report.md` (≤3 pages).

**Phase 4 — owner instruction only:** more models, full 690, C2, merged formats.
