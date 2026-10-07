# Pilot report — WorkBench EN vs BN, gpt-oss:20b, condition C6 vs C0

Date: 2026-10-07 · Interactive version: `results/comparisons/pilot_ollama-gpt-oss-20b_c6_vs_c0/report.html`.

## Setup
- **Data:** WorkBench (v2 ground truth). The same 90-task stratified pilot as the gemma runs: 15 per task file, seed 20261004, 63/69 templates covered.
- **Model:** gpt-oss:20b via the Ollama Cloud free tier, temperature 0.
- **Settings:** native tool calling, act-without-confirmation, all 27 tools, 1 worker, max 20 steps.
- **Reference C0:** all English (task, system prompt, tool descriptions). Ran 2026-10-05 (21:50 start; resumed 22:53); code: commit dcb6c76.
- **Condition C6:** Bangla task text and Bangla system prompt; English tool descriptions; replies forced to Bangla (the collaborators' setup). Started 2026-10-05 23:57. The first 67 rows ran on 2026-10-05/06; the free-tier monthly limit (HTTP 429) stopped the run, and the last 23 rows ran on 2026-10-07 (05:53–06:14) with a new API key (same model and tier). Code: commit a8447a3.
- **Requests** (two figures; see decision #32 and #37 in `progress.md`):
  - distinct `llm_input` per task, final attempts only: 381 C0 + 346 C6 = 727;
  - provider attempts across the 5 pilot logs: 840 HTTP 200, 71 HTTP 5xx, 1 HTTP 429 (the monthly-limit stop), 54 timeout retry lines.

## Results
| metric | C0 (EN) | C6 (BN) | Δ (C6−C0) | 95% CI |
|---|---|---|---|---|
| completion | 58.9% (53/90) | 53.3% (48/90) | -5.6 pp | [-16.7, +5.6] |
| harmful side effects | 25.6% | 24.4% | -1.1 pp | [-11.1, +8.9] |
| completion, domain-mix weighted | 54.2% | 49.0% | | |

Paired outcomes: 38 both correct, 27 both wrong, 15 only C0, 10 only C6. Exact McNemar p = 0.4244.

**Sensitivity** (computed from `paired.csv` with the comparison script's own McNemar and bootstrap code):

| | C0 | C6 | Δ | 95% CI | McNemar p | only C0 / only C6 |
|---|---|---|---|---|---|---|
| Main (recorded runs, n = 90) | 58.9% | 53.3% | -5.6 pp | [-16.7, +5.6] | 0.4244 | 15 / 10 |
| S1: the 85 pairs without an infrastructure error | 62.4% (53/85) | 55.3% (47/85) | -7.1 pp | [-17.6, +4.7] | 0.3075 | 15 / 9 |
| S2: recovered re-runs counted as failures (n = 90) | 56.7% (51/90) | 51.1% (46/90) | -5.6 pp | [-16.7, +5.6] | 0.4244 | 15 / 10 |

- **S1** drops 5 pairs in which either side has a row labelled infrastructure (pm:35, pm:64, md:130, crm:46, md:84).
- **S2:** a resumed run drops its errored rows and re-runs them. Two rows per side recovered on the second try (C0 email:5, analytics:105; C6 pm:28, pm:49). S2 counts them as failures. The flips cancel, so Δ, CI and p stay as in the main row.

| domain (n=15) | C0 | C6 | side effects C0 | side effects C6 |
|---|---|---|---|---|
| email | 73% | 67% | 27% | 27% |
| calendar | 67% | 73% | 27% | 13% |
| analytics | 73% | 47% | 0% | 0% |
| project_management | 53% | 60% | 13% | 13% |
| customer_relationship_manager | 60% | 47% | 40% | 33% |
| multi_domain | 27% | 27% | 47% | 60% |

## Failure analysis (details: `results/comparisons/pilot_ollama-gpt-oss-20b_c6_vs_c0/failure_analysis.md`, labels: `failure_labels.csv`)
- 79 failed runs are labelled (C0 37, C6 42): every failed run in the discordant and both-wrong pairs. Primary label `multilingual`: 0 of 42 C6 failures. 2 carry it as a weak secondary label: analytics:42 ("2023-11-10 থেকে" read as one day, although the same construction gave full ranges in analytics:0 and :32) and email:41 ("গত সপ্তাহে" read as the past 7 days; gemma's C6 run read it the same way).
- Failure mix (C0 / C6, all failures): tool_use 14 / 16, reasoning 14 / 15, planning 3 / 4, control_flow 2 / 3, outcome 1 / 0, memory 0 / 1, infrastructure 3 / 3.
- **tool_use is mostly invented addresses** (a recipient such as `yuki@example.com` made up instead of calling the directory: 10 C0 and 5 C6 tool_use failures) **and corrupted keyword arguments** (`new?`, `newvalue`; bad kwarg on any attempt: 3 tasks in C0, 8 in C6). Both occur in English as well and land on different tasks in each run, which looks like run-to-run variability, not a language effect. The bad-kwarg excess in C6 is the one pattern worth testing with k ≥ 3 repeats.
- **Infrastructure label (caveat).** The label says the provider ended the run (HTTP 5xx after 10 harness retries, a read timeout, or a stall), not that the model made no mistake.
  - **Lost traces:** when a run ends on any exception (a provider error or a bad kwarg), the harness records an empty trace. The model's earlier calls, and any writes they made, are lost. The run logs show 1–7 model calls before each of the 13 errored rows, so a model fault before the provider error cannot be ruled out.
  - Rows: C0 pm:35, pm:64, md:130; C6 pm:35, crm:46, md:84. These span 5 pairs (S1 drops them).
  - **crm:46 (C6) is the weakest label:** both attempts made 7 calls, and the first one failed on a model error (a bad kwarg). It stays infrastructure because the recorded re-run ended on a 500. It is a both-wrong pair, so S1 is not affected.
  - An errored run scores no side effect because its trace is lost (C0 5 rows, C6 8 rows). This can lower both side-effect rates, and C6 has more such rows.
  - c0 pm:57 (20 steps, moved every Carlos task to Backlog) is a model loop, not infrastructure.
- 80 of 80 non-empty C6 answers contain Bengali script; none switched to English. English appears only as borrowed names and titles (29 answers), plus 2 bracketed glosses. 2 answers are empty (analytics:105, pm:60); C0 had 3.
- 32 of 80 answers write numbers in Bengali digits (365 digits); 4 keep some ASCII numbers in prose. 0 of 264 tool calls passed Bangla script as an argument.
- Invalid tool names: C6 3 of 264 calls, C0 2 of 297 (the same invented `crm_search_customers` prefix and the same garbled names in both languages, so no language cause). The scorer rejects such a name, which alone fails crm:38 (C6) and crm:74 (C0).
- Shared weak spots: "next Friday" (0 of 5 runs that created the task got Dec 8; unlike gemma, gpt-oss errs on the English phrase too), the first free slot (no run booked 13:00), the past Wednesday, and dropped search filters.

## Findings
- **No detectable completion gap.** C6 is 5.6 pp lower (53.3% vs 58.9%), but the 95% CI (−16.7 to +5.6 pp) includes 0 and exact McNemar p = 0.4244. The CI also allows a moderate drop, so at this n a gap of 5–10 points can be neither detected nor ruled out (task sampling only; run-to-run noise not measured).
- **The sensitivity checks agree.** S1 (no infrastructure pairs): −7.1 pp, CI −17.6 to +4.7, p = 0.3075. S2 (recovered re-runs as failures): −5.6 pp, CI and p unchanged.
- **Side effects are about equal:** 25.6% vs 24.4% (−1.1 pp, CI −11.1 to +8.9).
- **No language cause visible in the failures:** 0 of 42 C6 failures are primarily multilingual (single model annotator). The 15 C6-only failures are error types that C0 also shows on other tasks (9 tool_use, 2 reasoning, 2 control_flow, 1 memory, 1 planning); 13 of the 27 both-wrong pairs have the same primary label on both sides. This grouping was made after reading the traces.
- **Analytics has the largest drop under C6** (73% vs 47%, −26.7 pp; 4 tasks only C0 solved, none only C6). C6 is lowest in multi-domain (27%), with analytics and CRM both at 47%. With 15 tasks per domain this is descriptive only.
- **Multi-domain tasks are still the hard part** (27% on both sides).
- **Compared with gemma4:31b (descriptive only).** The two models ran on different days with different failure types, so the comparison is a description, not a test.
  - Completion C0 / C6: gemma 81.1% / 82.2% (Δ +1.1 pp, p = 1.0); gpt-oss 58.9% / 53.3% (Δ −5.6 pp, p = 0.4244). Both CIs include 0.
  - gemma's failures are mostly reasoning (about two thirds on both sides). gpt-oss splits about evenly between reasoning and tool_use, and tool_use comes mostly from invented addresses and corrupted kwargs, which gemma barely shows (1 run per side with an `@example.com` argument, 0 bad kwargs).
  - Neither model has a failure labelled primarily multilingual. Both models have their largest C0-to-C6 drop in analytics (gemma −20.0 pp, gpt-oss −26.7 pp), with 0 only-C6 analytics pairs each, but on different tasks.

## Threats to validity
- **Different days.** C0 ran on 2026-10-05; C6 ran on 2026-10-05/06 (67 rows), was stopped by the monthly limit, and ran its last 23 tasks on 2026-10-07 with a new API key (same model and tier). Provider drift between and within runs cannot be excluded.
- **Both runs were resumed** after interruptions. A resume re-runs errored rows, so some rows got a second attempt (C0 2, C6 9). S2 brackets this; the first attempts' requests are not in 381 and 346.
- **`run_date` is the finishing invocation's date.** In `per_task_treat.csv` all 90 C6 rows show 2026-10-07, although 67 ran on 2026-10-05/06 (follow-up issue; the file is not edited by hand).
- **Provider failures:** 6 rows labelled infrastructure (3 per side), and the traces of 13 errored rows are lost. S1 drops the rows; it does not bracket any effect on the rest.
- **Single LLM annotator** (`model:claude-opus-5-5`), not yet human-checked. The label boundaries (tool_use vs planning for invented addresses; infrastructure vs model for stalls) are judgement calls.
- **Unreviewed Bangla prompt and task translations.** If they change, the C6 side must be re-run.
- **Small sample:** n = 90, 15 per domain. Per-domain differences are descriptive only.
- **One run per side, one model** at temperature 0 on a hosted free-tier endpoint. There is no measured noise floor, and the many one-sided invented-address and bad-kwarg failures suggest that run-to-run variability for gpt-oss:20b is large compared with the observed Δ.
- C6 changes the task, the system prompt and the reply language together, so a difference could not be assigned to one of them.

## Recommendations
1. **Owner review of the Bangla prompt wording** (`docs/conditions/translation_review.md`, `docs/translation/template_review.md`), including "আগামী শুক্রবার" and "গত সপ্তাহে" (for example "আগের সপ্তাহে (সোম–রবি)"). Re-run C6 if the wording changes.
2. **Measure the noise floor** with repeat runs (`--run_label rep2`): gemma c0-rep2 (about 342 requests) and, if the free-tier budget allows, gpt-oss repeats. The size of the gpt-oss C6 bad-kwarg excess (8 vs 3 tasks) cannot be read before then.
3. **Larger run (300 tasks) or another condition (C3) only if a gap shows up** in repeated runs. Each needs the owner's approval of the projected requests first.
