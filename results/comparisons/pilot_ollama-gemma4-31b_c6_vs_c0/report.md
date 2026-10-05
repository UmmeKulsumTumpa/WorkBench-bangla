# Pilot report — WorkBench EN vs BN, gemma4:31b, condition C6 vs C0

Date: 2026-10-05 · Interactive version: `results/comparisons/pilot_ollama-gemma4-31b_c6_vs_c0/report.html`.

## Setup
- **Data:** WorkBench (v2 ground truth). Same 90-task stratified pilot as C0: 15 per task file, seed 20261004, 63/69 templates covered.
- **Model:** gemma4:31b via the Ollama Cloud free tier, temperature 0.
- **Settings:** native tool calling, act-without-confirmation, all 27 tools, 1 worker, max 20 steps.
- **Reference C0:** all English (task, system prompt, tool descriptions). Ran 2026-10-04 11:42.
- **Condition C6:** Bangla task text and Bangla system prompt; English tool descriptions; replies forced to Bangla (the collaborators' setup). Ran 2026-10-05 16:12, harness commit 0950e72.
- **Requests:** 340 C0 + 296 C6 = 636, with no rate-limit or quota errors.

## Results
| metric | C0 (EN) | C6 (BN) | Δ (C6−C0) | 95% CI |
|---|---|---|---|---|
| completion | 81.1% | 82.2% | +1.1 pp | [-7.8, +10.0] |
| harmful side effects | 16.7% | 8.9% | -7.8 pp | [-15.6, +0.0] |
| completion, domain-mix weighted | 76.7% | 77.8% | | |

Paired outcomes: 66 both correct, 9 both wrong, 7 only C0, 8 only C6. Exact McNemar p = 1.00.

| domain (n=15) | C0 | C6 | side effects C0 | side effects C6 |
|---|---|---|---|---|
| email | 100% | 93% | 0% | 0% |
| calendar | 87% | 93% | 13% | 7% |
| analytics | 87% | 67% | 0% | 0% |
| project_management | 87% | 93% | 13% | 7% |
| customer_relationship_manager | 73% | 87% | 27% | 7% |
| multi_domain | 53% | 60% | 47% | 33% |

## Failure analysis (details: `results/comparisons/pilot_ollama-gemma4-31b_c6_vs_c0/failure_analysis.md`, labels: `failure_labels.csv`)
- 88 of 88 non-empty C6 answers are in Bangla; none switched to English. English appears only as borrowed names, titles and status values.
- 51 of 88 answers write numbers in Bengali digits (366 digits); every tool argument uses ASCII digits. 0 of 285 tool calls passed Bangla script as an argument.
- One invalid tool name in C6 (crm:77, `customer_relationship_manager_update_task`), none in 356 C0 calls. It mixes the CRM prefix with a project-management tool, which does not point to a language cause.
- 0 of 16 C6 failures have `multilingual` as the primary label; 3 carry it as a secondary label (md:120, email:41, analytics:20), each with a non-language explanation in the trace.
- Relative-date phrases: 2–3 of the 7 C6-only failures are relative-date resolution errors (email:41, analytics:119, md:120), against 0 of 8 C0-only failures. analytics:98 is not counted: it resolved "বুধবার" correctly and erred on the baseline day. This grouping is post hoc and n is small, so it is a hypothesis for repeated runs.
- md:120: "আগামী শুক্রবার" ("next Friday") was read as the coming Friday (Dec 1); the key expects Dec 8. It stays labelled reasoning, but it may be a translation-fidelity issue, because the same phrase gave Dec 8 in md:169 (and md:200). It goes to the native-speaker review.
- Observation: 2 of 90 C6 runs (crm:74, md:149) ended with an empty final answer; C0 had 0. The traces show no cause.

## Findings
- No detectable completion gap: 81.1% English vs 82.2% Bangla, exact McNemar p = 1.00. With 90 pairs the pilot can rule out a drop larger than about 8 points for this model.
- The disagreements show no detectable difference and no clear language cause (no repeat runs yet, so noise is not measured): 7 tasks only C0 solved, 8 only C6 solved, and the failed side was labelled reasoning in 12 of the 15.
- Harmful side effects were lower in Bangla (8.9% vs 16.7%), but the CI reaches zero (−15.6 to +0.0 points). 8 of 16 C6 failures leave no side effect (wrong plots, empty answers, no action), against 2 of 17 C0 failures.
- Failure mix is similar: reasoning 11 vs 10, planning 4 vs 2, tool use 1 vs 2, control flow 1 vs 2 (C0 vs C6).
- Analytics is the one domain where C6 is lower (87% vs 67%; 3 tasks only C0 solved, none only C6). With 15 tasks per domain this is descriptive only.
- Multi-domain tasks are still the hard part (53% and 60%), with calendar free-slot errors as the main shared weak spot in both languages.

## Threats to validity
- C0 ran on 2026-10-04 and C6 on 2026-10-05, so provider drift is possible. There is no C0 repeat yet, so the noise floor is not measured.
- The Bangla system prompt translation, and the task translations, have not been reviewed by a native speaker. If they change, the C6 side must be re-run.
- One model (gemma4:31b, trained heavily on multilingual data). Models with weaker Bangla may behave differently.
- Small sample: n = 90, 15 per domain. Per-domain differences are descriptive only.
- C6 changes the task, the system prompt and the reply language together, so a difference could not be assigned to one of them.
- Single run per task at temperature 0 on a hosted free-tier endpoint.
- Failure labels were assigned by one model annotator, not by human annotators.

## Recommendations
1. **Owner review of the Bangla prompt wording**, including relative-date phrases such as "আগামী শুক্রবার" (for example "পরের সপ্তাহের শুক্রবার"). Re-run C6 if the wording changes.
2. **Measure the noise floor:** repeat runs c0-rep2 and c6-rep2 (about 342 requests each on the free tier). Differences such as analytics 87% vs 67% and the 2 empty answers cannot be interpreted before that.
3. **Second model:** `ollama-gpt-oss-20b`, a smaller model that is likely weaker in Bangla, is a better place to look for a gap (about 342 requests per condition).
4. **Larger run only if a gap shows up** in repeated or second-model runs; multi-domain tasks carry most of the signal.
