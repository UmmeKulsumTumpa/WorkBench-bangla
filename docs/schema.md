# Shared result formats (EN↔BN agent evaluation)

Version 1.0 — 2026-10-04. Used by WorkBench (this repo), OfficeBench and τ²-bench collaborators, so results can be concatenated with no conversion step.

General rules
- Plain **CSV** (UTF-8, no BOM, `\n` line endings, RFC-4180 quoting, header row) or **JSON** (UTF-8, `ensure_ascii=False`).
- Booleans are `0`/`1`. Missing values are an empty cell, not `NA`/`None`. Rates are fractions in [0,1] with 4 decimal places, not percentages.
- Dates are ISO-8601 (`2026-10-04`, `2026-10-04T13:05:00Z`).
- Identifiers are lowercase snake_case ASCII.

## Controlled vocabularies

| Field | Values |
|---|---|
| `benchmark` | `workbench`, `officebench`, `tau2bench` |
| `language` | `en`, `bn` |
| `condition` | `en` (English baseline); `c1` (BN task text, EN system prompt/tools); `c2` (BN task text, BN system prompt pieces) |
| `provider` | as registered in the run, e.g. `ollama_cloud`, `ollama_local`, `groq`, `openrouter`, `google` |
| `failure_label` | `outcome`, `reasoning`, `planning`, `tool_use`, `control_flow`, `memory`, `multilingual` |
| `multilingual_subtype` (only when `failure_label=multilingual`) | `wrong_language_output`, `language_mixing`, `numeral_script_error`, `language_induced_tool_misuse` |
| `pair_class` | `both_correct`, `en_only`, `bn_only`, `both_wrong` |

`task_uid` is stable across languages: `<benchmark>:<split_or_file>:<row_index>` (0-based row in the original EN file), e.g. `workbench:email:17`. The EN and BN versions of a task share the same `task_uid`; this is the pairing key. Never pair by task text.

## 1. Per-task results — `results/<run_id>/per_task.csv`

`run_id` = `<benchmark>_<subset>_<language>_<model_key>[_<condition>]`, e.g. `workbench_pilot_bn_ollama-gpt-oss-20b_c1`.

| column | type | meaning |
|---|---|---|
| benchmark | str | vocabulary above |
| run_id | str | |
| model_key | str | registry key used to launch the run |
| model_id | str | exact provider model ID (pinned) |
| provider | str | |
| language | str | `en` / `bn` |
| condition | str | `en` / `c1` / `c2` |
| task_uid | str | pairing key |
| domain | str | benchmark-native domain (WorkBench: `email`, `calendar`, `analytics`, `project_management`, `customer_relationship_manager`, `multi_domain`) |
| template_id | str | benchmark-native template/scenario ID if one exists (WorkBench: `T01`–`T69`), else empty |
| correct | 0/1 | benchmark's own success criterion (WorkBench: final DB state == ground truth) |
| side_effect | 0/1 | incorrect AND changed environment state (WorkBench definition). Benchmarks without a notion of side effects leave this empty |
| error | str | runtime error message (truncated to 300 chars) or empty |
| n_llm_requests | int | LLM calls made for this task (empty if unknown) |
| n_tool_calls | int | tool calls the agent made |
| run_date | date | date the task ran |

## 2. Paired table — `results/<comparison_id>/paired.csv`

One row per `task_uid` present in both runs: `task_uid, domain, template_id, correct_en, correct_bn, side_effect_en, side_effect_bn, pair_class`. `comparison_id` = `<benchmark>_<subset>_<model_key>_<condition>`.

## 3. Metrics — `results/<comparison_id>/metrics.csv` (long format)

Columns: `benchmark, model_key, model_id, condition, scope, metric, value, n`.
- `scope`: `overall` or `domain:<domain>`.
- `metric` ∈
  - `completion_rate_en`, `completion_rate_bn`, `delta_completion` (bn − en)
  - `side_effect_rate_en`, `side_effect_rate_bn`, `delta_side_effect`
  - `mcnemar_p` (exact binomial McNemar on discordant pairs)
  - `delta_completion_ci95_low`, `delta_completion_ci95_high` (paired bootstrap over tasks, 10,000 resamples, seed 20261004)
  - `n_en_only`, `n_bn_only` (discordant counts)
- `n` is the number of paired tasks in that scope.

## 4. Failure labels — `results/<comparison_id>/failure_labels.csv`

Each row labels one failed run of one task (usually: tasks whose outcome differs between EN and BN).

| column | meaning |
|---|---|
| benchmark, model_key, condition, task_uid, language | as above (`language` = the side that failed) |
| failure_label | primary label (vocabulary) |
| multilingual_subtype | required iff `failure_label=multilingual` |
| secondary_labels | `|`-joined extra labels, may be empty |
| step_index | 0-based trace step where the failure manifests, or empty |
| evidence | ≤200-char quote from the trace |
| annotator | `model:<model_id>` or `human:<initials>` |
| notes | free text |

Label definitions (adapted from BabelArena; written fully in `results/pilot_failure_analysis.md`): **outcome** — right process, wrong final state (wrong value written); **reasoning** — wrong inference about the task or data; **planning** — missing or extra steps, wrong order; **tool_use** — wrong tool, wrong or malformed arguments; **control_flow** — stopped early, looped, hit the step limit, asked for confirmation; **memory** — lost information obtained earlier in the trace; **multilingual** — the failure is attributable to the language of the instruction (subtypes above).

## 5. Run metadata — `results/<run_id>/run_meta.json`

`{benchmark, run_id, model_key, model_id, provider, base_url, temperature, language, condition, subset, n_tasks, tasks_file, tasks_file_sha256, tool_selection, structured_outputs, act_without_confirmation, harness_commit, patch_files, started_at, finished_at, total_llm_requests, notes}`. For WorkBench this is derived from upstream's `_meta.json` plus our fields.
