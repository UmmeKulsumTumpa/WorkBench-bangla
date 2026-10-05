# Runbook: run, compare, report, reproduce

Every command runs from the project root after `source env.sh`. `uv run --project WorkBench --frozen` runs Python in the WorkBench environment (pinned by `WorkBench/uv.lock`). Nothing is installed globally.

## 0. Before any API spend

1. **Commit first.** The runner refuses to start if `WorkBench/src` or `WorkBench/data/conditions` has uncommitted changes, so every result maps to a commit.
2. **Dry run.** It prints the condition, the exact system prompt, the tasks file, tasks left, projected requests and the command. It makes no API call.
   ```bash
   uv run --project WorkBench --frozen python scripts/run_condition.py --condition c3 --model ollama-gemma4-31b --subset pilot --dry_run
   ```
3. **Record and approve the budget.** Write the projected requests in `progress.md` → `## Request budget` and get the owner's go-ahead (project rule). Measured cost: **≈ 4.9 requests per task**, so about 440 for the 90-task pilot.

## 1. Run a condition

```bash
uv run --project WorkBench --frozen python scripts/run_condition.py --condition c3 --model ollama-gemma4-31b --subset pilot
```

- **Fixed study settings** (`STUDY_FLAGS` in the script): native tool calling, act without confirmation, all 27 tools, 1 worker, traces, `--resume`.
- **Output:** `WorkBench/data/results/c3/pilot_bn/ollama-gemma4-31b_all_<timestamp>.csv`, plus `_meta.json` and `_traces.json`.
- **Logs:** the console output goes to `results/logs/pilot/c3_ollama-gemma4-31b_<timestamp>.log`, and a row is appended to `results/logs/run_log.csv`.
- **Interrupted?** Run the same command again. It resumes and only runs missing tasks.
- **Finished?** Running again does nothing. A finished run is final: its errored tasks (e.g. step limit) are real outcomes. `--retry_errors` exists but changes results; note it in `progress.md` if you use it.

## 2. Repeat a condition (noise floor)

```bash
uv run --project WorkBench --frozen python scripts/run_condition.py --condition c0 --run_label rep2 --model ollama-gemma4-31b
uv run --project WorkBench --frozen python scripts/compare_conditions.py --ref c0 --treat c0 --treat_label rep2 --model ollama-gemma4-31b
```

The second command writes `results/comparisons/pilot_ollama-gemma4-31b_c0-rep2_vs_c0/`. Its discordant pairs show how much two identical runs disagree; a language effect has to be larger than that.

## 3. Compare and report

```bash
uv run --project WorkBench --frozen python scripts/compare_conditions.py --ref c0 --treat c3 --model ollama-gemma4-31b --subset pilot
python3 scripts/build_report_html.py --comparison_id pilot_ollama-gemma4-31b_c3_vs_c0   # optional HTML
```

- **Output:** `results/comparisons/<subset>_<model>_<treat>_vs_<ref>/`, and `results/summary.csv` is rebuilt. Formats: [`docs/data/schema.md`](../data/schema.md).
- **Any pair works,** e.g. `--ref c1 --treat c2` gives the effect of the Bangla system prompt alone.
- **Failure analysis:** label every failed run in a discordant or both-wrong pair, in `failure_labels.csv` in the comparison folder (schema §4). Write `failure_analysis.md` next to it.
- **HTML report:** the template's wording assumes an English-task reference and a Bangla-task treatment, so it works for c1–c4 vs c0. For c5 the template must be generalized first; the builder refuses until then.

## 4. Switch between conditions

There is nothing to switch: every condition is a flag value, and results live in separate folders, so c3 and c1 can be run, re-compared or re-reported in any order. To inspect what a condition sends, use `--dry_run`. To inspect what a past run actually sent, open its `_meta.json` → `system_prompt_sent` and `condition_assets`.

## 5. Reproduce a past result

1. Open the comparison's `run_meta_{ref,treat}.json`. It has the `results_file`, `tasks_file` + sha256, `model_id`, `harness_commit` and `condition_assets` hashes.
2. **Re-score only (free):** re-run `compare_conditions.py` with the same arguments. The output must be identical; this was verified for the C1 pilot.
3. **Re-run inference:** `git checkout <harness_commit>`, then run with a new `--run_label`. Expect run-to-run noise even at temperature 0: hosted models are not bit-deterministic, and the provider can update a model silently.
4. **Runs before 2026-10-05** (the C0/C1 pilot) predate `--condition`. Their code is tag `run/pilot-c0c1-gemma4-31b`, and the C0/C1 prompt is asserted byte-identical in `WorkBench/tests/evals/test_conditions.py`.

## 6. Change a Bangla asset (prompt or tool text)

1. Edit `WorkBench/data/conditions/bn/*.json`.
2. Regenerate the review sheet with `uv run --project WorkBench --frozen python scripts/build_condition_review.py`.
3. Run the tests: `(cd WorkBench && uv run --frozen pytest -q tests/evals/test_conditions.py)`.
4. Commit through a PR.
5. Runs made before the edit no longer match the asset: their `condition_assets` hash differs. Re-run under a new label and record the change in `progress.md`.

## 7. Tests

```bash
(cd WorkBench && uv run --frozen pytest -q)                      # harness: 283 tests
uv run --project WorkBench --frozen python -m pytest tests -q    # project scripts: 19 tests
```

## 8. Git workflow

- Work on a feature branch, then open a PR to `main` and merge it (`gh pr create`, `gh pr merge --merge --delete-branch`). Don't commit on `main` directly.
- Tag a run you will cite: `git tag -a run/<subset>-<cond>-<model> <commit>`.
