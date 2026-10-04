# Pilot design — WorkBench EN vs BN (condition C1)

Status: draft, 2026-10-04. Model choice, settings and budget need owner confirmation at STOP (b).

## 1. Question for the pilot
Before spending the free quota on 690 × 2 tasks, find out whether a free open model shows a measurable EN→BN drop in task completion on WorkBench, and get early failure categories. We also check that the pipeline works end to end with Bangla text (UTF-8 through prompts, traces, CSVs, and the evaluator).

## 2. Sample
- `scripts/make_pilot.py`, seed `20261004`. It takes **15 tasks from each of the 6 task files = 90 tasks**.
- Templates are drawn round-robin in a seeded order, preferring an unused rewording each time. All templates are covered in email (9), calendar (11), CRM (8), analytics (12) and project management (8); multi_domain covers 15 of its 21.
- The same 90 rows go into both languages. Files:
  - `data_bn/pilot/pilot_en_tasks_and_outcomes.csv`
  - `data_bn/pilot/pilot_bn_tasks_and_outcomes.csv`
  - `data_bn/pilot/pilot_index.csv` (`task_uid` = `workbench:<file>:<row>`)
- For runs, both task files are copied into `WorkBench/data/processed/tasks_and_outcomes/`. Results land in `data/results/pilot_en/` and `pilot_bn/`. `workbench-evaluate --tools pilot_en pilot_bn --all_tools` then scores each run against its own file, with the identical `outcome` column. Matching is by task text, which is why the BN run needs its own GT file (`docs/repo_map.md` §3).
- Limitation: multi_domain is under-sampled relative to the full set (15 of 210 vs 15 of 80–120 elsewhere). Overall rates are therefore reported both unweighted and re-weighted to the full 690-task domain mix.

## 3. Model shortlist (Ollama Cloud free tier, probe 2026-10-04)
| key | model_id | why |
|---|---|---|
| **`ollama-gemma4-31b`** (recommended primary) | `gemma4:31b` | Google open model, heavily multilingual (Bangla in training mix, inferred from model family). Mid-size, so likely below ceiling in EN and the gap stays measurable. |
| `ollama-gpt-oss-20b` (recommended second) | `gpt-oss:20b` | Popular open reasoning model, weaker multilingual (inferred). Contrasts with gemma. |
| `ollama-gpt-oss-120b` | `gpt-oss:120b` | Stronger; may be near ceiling in EN. Run later if budget allows. |
| `ollama-nemotron-3-nano-30b` | `nemotron-3-nano:30b` | Small MoE; possible floor effects. |
| local fallback `ollama-local-qwen3-8b` | `qwen3:8b` | Only if the cloud quota runs out. Needs local Ollama; weights go to `.tools/ollama-models` (project-local rule). |

Not free (HTTP 402): glm-5.3-flash, deepseek-v4.1-flash, minimax-m2.7. They are removed from the registry.

## 4. Run settings (identical for EN and BN)
`workbench-inference --model_name <key> --tasks_path data/processed/tasks_and_outcomes/pilot_{en,bn}_tasks_and_outcomes.csv --structured_outputs --act_without_confirmation --tool_selection all --workers 1 --log_traces --resume`
- `--structured_outputs`: native `tools=` calling. The probe showed it works on Ollama Cloud. (Ollama does not support `response_format`, and WorkBench doesn't use it.)
- `--act_without_confirmation`: same as the 2026 Revisited runs. Without it, agents often stop to ask for confirmation, which shows up as a control-flow failure in both languages and masks the language effect.
- `--tool_selection all` **(deviation from the spec's `domains`)**: the upstream `domains` mode drops CRM tools for 50 multi_domain tasks (`"crm"` is missing from `_TOOLKIT_MAP`). `all` (27 tools) is also the setting of every headline result.
- Temperature is 0 (hard-coded in WorkBench). `--workers 1`, because the free tier allows one concurrent request. Retries are WorkBench's built-in exponential backoff on 429/5xx (×10, max 90 s). 402 is not retried.
- Order: EN first, then BN, on the same day if possible (provider-side model updates are a validity threat).

## 5. Analysis (`scripts/compare_en_bn.py` → formats in `docs/schema.md`)
- **Per task:** `correct`, `side_effect` for EN and BN, paired by `task_uid`.
- **Completion rate** EN and BN, and Δ = BN − EN.
  - **Exact McNemar test** on discordant pairs (binomial, two-sided).
  - **Paired bootstrap 95% CI** of Δ (10,000 resamples over tasks, seed 20261004).
- **Side-effect rate** EN and BN, and Δ (same CI method).
- **Per-domain** table: descriptive only (n = 15 per domain; no per-domain tests).
- **Power (inference):** with 90 pairs, only large gaps are detectable, roughly ≥ 12–15 pp with typical discordance. The pilot estimates the effect size and failure mix; the full 690 run is the confirmatory test.
- **Failure analysis:** every task whose outcome differs between EN and BN, plus all BN failures with a non-empty error, is labelled with the `docs/schema.md` taxonomy. Primary labels: outcome / reasoning / planning / tool_use / control_flow / memory / multilingual. Multilingual subtypes: wrong-language output, language mixing, numeral/script error, language-induced tool misuse (e.g. `nadia-কে` passed as a name).

## 6. Request budget
- 1 LLM request per agent step. Committed runs average 2.5–4.1 tool calls per task, so expect **≈ 4 requests per task**; the hard cap is 20 per task.
- **Dry run (Phase 3.1):** 2 EN + 2 BN tasks on the primary model, ≈ 16 requests (cap 80). This measures the real requests per task.
- **Pilot, one model:** 180 tasks × ~4 ≈ **720 requests** (worst case 3,600).
- **Two models:** ≈ 1,440.
- **Pacing:** 1 concurrent request at ~2–5 s each ≈ 10–20 min of wall-clock per 100 tasks. Ollama's free tier is metered in monthly credits with an unpublished cap and sends no rate-limit headers. We watch for 429/402 and stop on the first quota signal. `--resume` lets a run continue on a later day.
- **Fallback:** if the quota cannot carry one model's pilot within ~3 days, record a blocker recommending a Groq or Gemini free key, and prepare local `qwen3:8b`.
