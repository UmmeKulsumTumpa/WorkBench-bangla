# WorkBench → Bangla: do LLM agents fail more when instructed in Bangla?

Research project: we run the same multi-step office tasks ([WorkBench](https://github.com/olly-styles/WorkBench), COLM 2024) on an LLM agent in English and in Bangla. We compare task completion, harmful side effects and failure types. Outputs use a shared schema so they can be merged with collaborators' OfficeBench and τ²-bench results.

**Status (2026-10-05):** C0, C1 and C6 pilots done (90 tasks, gemma4:31b). C2–C6 are implemented. **Next: owner review of the Bangla prompt wording, then optional repeat runs (c0-rep2, c6-rep2) to measure noise.** Details: [`progress.md`](progress.md).

## Conditions

All conditions run from the same code and are chosen with `--condition` ([details](docs/conditions/README.md)).

| id | task | system prompt | tool descriptions | replies | status |
|---|---|---|---|---|---|
| c0 | EN | EN | EN | free | ✅ pilot 90 |
| c1 | BN | EN | EN | free | ✅ pilot 90 |
| c2 | BN | BN | EN | free | ⬜ ready |
| c3 | BN | BN | BN | free | ⬜ ready |
| c4 | BN | EN | EN | forced EN | ⬜ ready |
| c5 | EN | EN | EN | forced BN | ⬜ ready |
| c6 | BN | BN | EN | forced BN | ✅ pilot 90 (teammates' setup) |
| c0-rep2/3 | repeats of c0 (noise floor) | | | | ⬜ optional (rep2) |

## Results so far

Full table: [`results/summary.csv`](results/summary.csv). Each row is one comparison against C0, on the same tasks.

| comparison | n | C0 | treatment | Δ (95% CI) | McNemar p | side effects C0 → treat |
|---|---|---|---|---|---|---|
| C1 vs C0, pilot, gemma4:31b | 90 | 81.1% | 82.2% | +1.1 pp (−6.7, +8.9) | 1.00 | 16.7% → 12.2% |
| C6 vs C0, pilot, gemma4:31b | 90 | 81.1% | 82.2% | +1.1 pp (−7.8, +10.0) | 1.00 | 16.7% → 8.9% |

**Reading:** no detectable language gap for C1 on this model. 0 of 16 Bangla failures were language-caused ([report](results/comparisons/pilot_ollama-gemma4-31b_c1_vs_c0/report.md), [failure analysis](results/comparisons/pilot_ollama-gemma4-31b_c1_vs_c0/failure_analysis.md)).

**Reading (C6):** no detectable gap for C6 either. 0 of 16 Bangla failures were primarily language-caused, and C0 ran a day earlier with no repeat yet, so noise is unmeasured ([report](results/comparisons/pilot_ollama-gemma4-31b_c6_vs_c0/report.md), [failure analysis](results/comparisons/pilot_ollama-gemma4-31b_c6_vs_c0/failure_analysis.md)).

## Where things are

```
README.md            ← you are here
progress.md          ← source of truth: status, current step, decisions log, request budget
env.sh               ← `source env.sh` before every command (keeps all tooling inside this folder)
docs/                ← all documentation, by topic (index: docs/README.md)
  design/              research spec, pilot design
  conditions/          C0–C6 definitions, assets, Bangla review sheet
  runbook/             how to run, compare, report, reproduce, switch conditions
  data/                result file formats (shared schema)
  translation/         translation policy, task-template review
  harness/             WorkBench internals, provider notes
data_bn/             ← Bangla task data: templates, glossary, translated task files, subsets
  pilot/               90-task pilot (EN + BN task files, index)
  smoke10/             10-task smoke subset
WorkBench/           ← the agent harness (upstream WorkBench + our changes: providers, --condition)
  data/conditions/bn/  Bangla system prompt + tool descriptions
  data/results/        RAW run outputs: <condition>[-<label>]/<subset>_<lang>/<model>_all_<ts>.csv (+ _meta.json)
scripts/             ← run_condition.py, compare_conditions.py, build_report_html.py, data/translation builders
tests/               ← tests for the project scripts (WorkBench has its own tests/)
results/             ← ANALYSED outputs
```

### Output folders

| path | what is in it | written by |
|---|---|---|
| `WorkBench/data/results/<cond>[-<label>]/<subset>_<lang>/` | raw run: `<model>_all_<ts>.csv` (one row per task), `_meta.json` (condition, exact prompt, asset hashes, git commit), `_traces.json` (full trajectories, git-ignored) | `run_condition.py` |
| `results/comparisons/<subset>_<model>_<treat>_vs_<ref>/` | one comparison: `paired.csv`, `metrics.csv`, `per_task_{ref,treat}.csv`, `run_meta_{ref,treat}.json`; optional `failure_labels.csv`, `report.md`, `report.html` | `compare_conditions.py`, `build_report_html.py` |
| `results/summary.csv` | one row per comparison (completion, Δ, CI, p, side effects) | `compare_conditions.py` (rebuilt each time) |
| `results/logs/` | `run_log.csv` (every run: time, condition, commit, exit code) and the console log of each run | `run_condition.py` |
| `results/probe/` | provider probe results | `probe_provider.py` |

## Quick start

```bash
source env.sh
# 1. see exactly what a run will send, at no API cost
uv run --project WorkBench --frozen python scripts/run_condition.py --condition c3 --model ollama-gemma4-31b --dry_run
# 2. run it (free tier, ~340 requests for 90 tasks; resumable)
uv run --project WorkBench --frozen python scripts/run_condition.py --condition c3 --model ollama-gemma4-31b
# 3. compare with the baseline
uv run --project WorkBench --frozen python scripts/compare_conditions.py --ref c0 --treat c3 --model ollama-gemma4-31b
```

Everything else (repeats, switching conditions, reports, reproducing a past result) is in the [runbook](docs/runbook/README.md).

## Rules of the project

- Free model tiers only. The projected request count is recorded and approved before every run.
- Results must map to a commit: the runner refuses uncommitted harness changes, and every run records its commit.
- A finished run is final. Use `--run_label` for repeats, never re-runs.
- Work happens on feature branches, merged by PR into `main`.
