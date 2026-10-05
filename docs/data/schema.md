# Shared result formats (EN↔BN agent evaluation)

Version 2.0 — 2026-10-05. Used by WorkBench (this repo), OfficeBench and τ²-bench collaborators, so results can be concatenated with no conversion step.

**Changes from 1.0** (2026-10-04):
- A comparison is now *reference* vs *treatment*, not EN vs BN. Columns and metrics use `_ref`/`_treat` instead of `_en`/`_bn`. Reason: c5 has an English task on both sides, and repeat runs compare one condition with itself.
- `condition` ids are `c0`–`c5`; c0 replaces `en`.
- Paths moved under `results/comparisons/`, and `results/summary.csv` was added.
- `failure_labels.csv` is keyed by `condition`, the side that failed.
- `run_meta` gains `run_label`, `condition_spec`, `condition_assets`, `system_prompt_sent`, `results_file` and `harness_dirty`, and drops `patch_files`.

The C1 pilot outputs were regenerated in v2: all values are identical, only the names changed.

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
| `condition` | `c0` … `c5`, defined in `docs/conditions/README.md`; a repeated run appends `-<label>`, e.g. `c0-rep2` (in `run_id`, `ref_condition`/`condition` of metrics) |
| `provider` | as registered in the run, e.g. `ollama_cloud`, `ollama_local`, `groq`, `openrouter`, `google` |
| `failure_label` | `outcome`, `reasoning`, `planning`, `tool_use`, `control_flow`, `memory`, `multilingual` |
| `multilingual_subtype` (only when `failure_label=multilingual`) | `wrong_language_output`, `language_mixing`, `numeral_script_error`, `language_induced_tool_misuse` |
| `pair_class` | `both_correct`, `ref_only`, `treat_only`, `both_wrong` |

`task_uid` is stable across languages: `<benchmark>:<split_or_file>:<row_index>` (0-based row in the original EN file), e.g. `workbench:email:17`. The EN and BN versions of a task share the same `task_uid`; this is the pairing key. Never pair by task text.

## 1. Per-task results — `results/comparisons/<comparison_id>/per_task_{ref,treat}.csv`

`run_id` = `<benchmark>_<subset>_<condition>[-<label>]_<model_key>`, e.g. `workbench_pilot_c3_ollama-gemma4-31b`, `workbench_pilot_c0-rep2_ollama-gemma4-31b`.

| column | type | meaning |
|---|---|---|
| benchmark | str | vocabulary above |
| run_id | str | |
| model_key | str | registry key used to launch the run |
| model_id | str | exact provider model ID (pinned) |
| provider | str | |
| language | str | language of the task text: `en` / `bn` |
| condition | str | `c0` … `c5` |
| task_uid | str | pairing key |
| domain | str | benchmark-native domain (WorkBench: `email`, `calendar`, `analytics`, `project_management`, `customer_relationship_manager`, `multi_domain`) |
| template_id | str | benchmark-native template/scenario ID if one exists (WorkBench: `T01`–`T69`), else empty |
| correct | 0/1 | benchmark's own success criterion (WorkBench: final DB state == ground truth) |
| side_effect | 0/1 | incorrect AND changed environment state (WorkBench definition). Benchmarks without a notion of side effects leave this empty |
| error | str | runtime error message (truncated to 300 chars) or empty |
| n_llm_requests | int | LLM calls made for this task (empty if unknown) |
| n_tool_calls | int | tool calls the agent made |
| run_date | date | date the task ran |

## 2. Paired table — `results/comparisons/<comparison_id>/paired.csv`

One row per `task_uid` present in both runs: `task_uid, domain, template_id, correct_ref, correct_treat, side_effect_ref, side_effect_treat, pair_class`. `comparison_id` = `<subset>_<model_key>_<treat>_vs_<ref>`, e.g. `pilot_ollama-gemma4-31b_c3_vs_c0`.

## 3. Metrics — `results/comparisons/<comparison_id>/metrics.csv` (long format)

Columns: `benchmark, model_key, model_id, ref_condition, condition, scope, metric, value, n` (`condition` = the treatment).
- `scope`: `overall` or `domain:<domain>`.
- `metric` ∈
  - `completion_rate_ref`, `completion_rate_treat`, `delta_completion` (treat − ref)
  - `side_effect_rate_ref`, `side_effect_rate_treat`, `delta_side_effect`
  - `mcnemar_p` (exact binomial McNemar on discordant pairs)
  - `delta_completion_ci95_low`, `delta_completion_ci95_high` (paired bootstrap over tasks, 10,000 resamples, seed 20261004)
  - `n_ref_only`, `n_treat_only` (discordant counts)
- `n` is the number of paired tasks in that scope.
- Extra metrics (WorkBench, `scripts/compare_conditions.py`): scope `overall` also carries `delta_side_effect_ci95_low`/`_high` (same bootstrap, percentile CIs) and `completion_rate_ref_weighted`/`completion_rate_treat_weighted` = Σ_d w_d·completion_rate_d with w_d = domain share of the full 690-task set (email 90, calendar 110, analytics 120, project_management 80, customer_relationship_manager 80, multi_domain 210), correcting the pilot's equal 15-per-domain mix; `domain:<d>` scopes are descriptive only (no `mcnemar_p`/CIs).

## 4. Failure labels — `results/comparisons/<comparison_id>/failure_labels.csv`

Each row labels one failed run of one task (usually: tasks whose outcome differs between reference and treatment).

| column | meaning |
|---|---|
| benchmark, model_key, condition, task_uid, language | as above; `condition` and `language` are those of the run that failed |
| failure_label | primary label (vocabulary) |
| multilingual_subtype | required iff `failure_label=multilingual` |
| secondary_labels | `|`-joined extra labels, may be empty |
| step_index | 0-based trace step where the failure manifests, or empty |
| evidence | ≤200-char quote from the trace |
| annotator | `model:<model_id>` or `human:<initials>` |
| notes | free text |

Label definitions (adapted from BabelArena; written fully in `results/comparisons/pilot_ollama-gemma4-31b_c1_vs_c0/failure_analysis.md`): **outcome** — right process, wrong final state (wrong value written); **reasoning** — wrong inference about the task or data; **planning** — missing or extra steps, wrong order; **tool_use** — wrong tool, wrong or malformed arguments; **control_flow** — stopped early, looped, hit the step limit, asked for confirmation; **memory** — lost information obtained earlier in the trace; **multilingual** — the failure is attributable to the language of the instruction (subtypes above).

## 5. Run metadata — `results/comparisons/<comparison_id>/run_meta_{ref,treat}.json`

`{benchmark, run_id, model_key, model_id, provider, base_url, temperature, language, condition, run_label, condition_spec, condition_assets, system_prompt_sent, subset, n_tasks, tasks_file, tasks_file_sha256, results_file, tool_selection, structured_outputs, act_without_confirmation, harness_commit, harness_dirty, started_at, finished_at, total_llm_requests, notes}`. For WorkBench this is derived from the run's `_meta.json` plus our fields. `harness_commit` is the commit the run executed on, recorded at run time; for runs before 2026-10-05, the commit at comparison time, with a note.

## 6. Summary — `results/summary.csv`

One row per comparison folder: `comparison_id, model_key, ref_condition, condition, n, completion_rate_ref, completion_rate_treat, delta_completion, delta_completion_ci95_low, delta_completion_ci95_high, mcnemar_p, n_ref_only, n_treat_only, side_effect_rate_ref, side_effect_rate_treat, delta_side_effect` (overall scope). Rebuilt by `scripts/compare_conditions.py`.
