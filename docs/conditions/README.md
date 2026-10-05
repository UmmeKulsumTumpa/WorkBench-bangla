# Experimental conditions (C0–C5)

A **condition** fixes which parts of the agent's input are in Bangla. Every condition runs from the same code; you pick one with `--condition` (never a git branch). Defined in `WorkBench/src/evals/conditions.py`.

## The six conditions

| id | task text | system prompt | tool descriptions | replies | isolates |
|---|---|---|---|---|---|
| **c0** | EN | EN | EN | free | baseline |
| **c1** | BN | EN | EN | free | understanding a Bangla task |
| **c2** | BN | BN | EN | free | + Bangla system prompt |
| **c3** | BN | BN | BN | free | fully Bangla interface |
| **c4** | BN | EN | EN | forced EN | does *answering* in Bangla hurt? (with c1) |
| **c5** | EN | EN | EN | forced BN | output language alone (with c0) |

Two ways to read them:
- **Dose-response:** c0 → c1 → c2 → c3 adds Bangla one layer at a time.
- **2×2, input × output language:** c0 (EN→EN), c5 (EN→BN), c4 (BN→EN), c1 (BN→BN, which the model chooses itself).

The reference for every comparison is **c0** (`Condition.reference`). Repeated runs of the same condition (`--run_label rep2`) measure the run-to-run noise floor.

## What stays English in every condition

- Tool **names**, **argument names**, JSON keys, IDs, emails, dates, and all digits (ASCII only). These are identifiers the grader and the sandbox match byte for byte.
- Argument descriptions in the `tools=` schema. They are generated from the argument names (`Email Id`), so they are identifiers too.
- **Tool observations**, i.e. the environment data. Grading compares the final sandbox state, so translating it would change the answer key.
- The ReAct prompt (`PREFIX`, `FORMAT_INSTRUCTIONS`, `SUFFIX`) is not translated. That is why c2 and c3 require `--structured_outputs`, the study setting; the harness refuses otherwise.

In native tool-calling mode the **whole system prompt** is: date line + act-without-confirmation line + (c4/c5) output-language line. You can see it per run in `_meta.json` → `system_prompt_sent`, or before a run with `scripts/run_condition.py --dry_run`.

## Assets

| file | content | used by |
|---|---|---|
| `WorkBench/data/conditions/bn/system_prompt.json` | Bangla date line (with weekday names), act-without-confirmation line, output-language template | c2, c3 |
| `WorkBench/data/conditions/bn/tool_descriptions.json` | Bangla description for each of the 27 tools, keyed by tool name | c3 |
| English texts | upstream strings, kept in code (`conditions.py`, `agent.py`) | all |

- The texts follow `docs/translation/policy.md`: তুমি register, as in the task templates; ASCII digits; field values and status values (`Lead`, `Won`) left in English.
- Side-by-side review: [`translation_review.md`](translation_review.md). Regenerate it with `python3 scripts/build_condition_review.py`.
- Every run records the sha256 of the asset files it read (`_meta.json` → `condition_assets`). An edited asset therefore always shows up in the metadata, and `run_condition.py` refuses to run with uncommitted asset changes.
- **If an asset changes after a run,** that condition's results no longer match the asset. Re-run it under a new label, or move the old run aside, and note it in `progress.md`.

## Guarantees (tested in `WorkBench/tests/evals/test_conditions.py`)

- c0 and c1 send the pilot's system prompt **byte for byte**, so the 2026-10-04 pilot counts as the c0/c1 runs.
- Localized tools keep name, signature and argument schema identical. Only `description` changes.
- The tasks file must match the condition's task language. A Bangla condition fails fast on English tasks, and vice versa.
- Results go to `WorkBench/data/results/<condition>[-<label>]/<subset>_<lang>/`, so conditions can never overwrite each other.

## Adding a condition or a language

- **New condition:** add one `Condition(...)` line to `CONDITIONS` in `conditions.py`. Add a row to the table above and to the README, and add a test.
- **New language `xx`:** add `WorkBench/data/conditions/xx/system_prompt.json` (same keys as `bn`) and `tool_descriptions.json` (all 27 tools), plus a `LANGUAGE_NAMES` entry. Then add conditions that use it.
