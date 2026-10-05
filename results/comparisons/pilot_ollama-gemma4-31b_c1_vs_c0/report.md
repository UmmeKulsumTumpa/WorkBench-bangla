# Pilot report — WorkBench EN vs BN, gemma4:31b, condition C1

Date: 2026-10-04 · Interactive version: `results/workbench_pilot_ollama-gemma4-31b_c1/report.html` (claude.ai artifact 6Nd3cAmYaD5sDRT5WsGa2q, private).

## Setup
- **Data:** WorkBench (v2 ground truth). 90-task stratified pilot: 15 per task file, seed 20261004, 63/69 templates covered. The same tasks are run in EN and BN.
- **Model:** gemma4:31b via the Ollama Cloud free tier, temperature 0.
- **Settings:** native tool calling, act-without-confirmation, all 27 tools, 1 worker, max 20 steps.
- **Condition C1:** Bangla task text; English system prompt and tools.
- **Requests:** 445 EN + 433 BN = 878, with no rate-limit or quota errors.

## Results
| metric | EN | BN | Δ (BN−EN) | 95% CI |
|---|---|---|---|---|
| completion | 81.1% | 82.2% | +1.1 pp | [-6.7, +8.9] |
| harmful side effects | 16.7% | 12.2% | -4.4 pp | [-11.1, +2.2] |
| completion, domain-mix weighted | 76.7% | 77.3% | | |

Paired outcomes: 67 both correct, 10 both wrong, 6 only EN, 7 only BN. Exact McNemar p = 1.00.

| domain (n=15) | EN | BN | side effects EN | side effects BN |
|---|---|---|---|---|
| email | 100% | 93% | 0% | 0% |
| calendar | 87% | 93% | 13% | 7% |
| analytics | 87% | 80% | 0% | 0% |
| project_management | 87% | 93% | 13% | 7% |
| customer_relationship_manager | 73% | 80% | 27% | 13% |
| multi_domain | 53% | 53% | 47% | 47% |

## Failure analysis (details: `results/pilot_failure_analysis.md`, labels: `failure_labels.csv`)
- 88 of 88 completed Bangla runs answered in Bangla; none switched to English mid-answer. English appeared only for names and IDs.
- The agent wrote Bengali digits in its prose (346 digits across 52 answers) but used ASCII digits in every tool argument.
- 0 of 345 tool calls passed Bangla script as an argument. All 76 names written with a case marker in the task (e.g. nadia-কে) were sent to tools as the bare name.
- One invalid tool name in Bangla (crm:77, customer_relationship_manager_update_task), none in English.
- One possible language effect: আগামী শুক্রবার ("next Friday") was read as the coming Friday (Dec 1) in multi_domain:169, where the answer key expects Dec 8. The wording needs the native-speaker review.

## Findings
- No detectable completion gap: 81.1% English vs 82.2% Bangla, exact McNemar p = 1.00. With 90 pairs the pilot can rule out a drop larger than about 7 points for this model.
- Disagreements look like run-to-run noise: 6 tasks only English solved, 7 only Bangla solved, and the failed side was labelled reasoning in 11 of the 13.
- Harmful side effects were slightly lower in Bangla (12.2% vs 16.7%), with a CI that crosses zero (−11.1 to +2.2 points).
- Failure mix is nearly identical: reasoning 11 vs 9, planning 4 vs 3, tool use 1 vs 2, control flow 1 vs 2 (English vs Bangla). 0 of 16 Bangla failures have multilingual as the primary label.
- Multi-domain tasks are the hard part in both languages (53% completion each), so a language gap, if one exists, is more likely to show up there in the full 690-task run.

## Threats to validity
- The Bangla translations have not yet been reviewed by a native speaker (machine translation plus two independent model-review cycles). If they change, the Bangla side must be re-run.
- Small sample: 90 tasks, 15 per domain. Per-domain differences are descriptive only.
- One model (gemma4:31b, Gemma family, trained heavily on multilingual data). Models with weaker Bangla may behave differently.
- Condition C1 only: the system prompt and tool descriptions stay English. A fully Bangla interface (C2) is untested.
- Single run per task at temperature 0 on a hosted free-tier endpoint; the provider can update the model silently.
- Failure labels were assigned by a model, not by human annotators.

## Recommendations
1. **Finish STOP (a) first.** Have the native speaker review the translations, especially relative-date phrases like "আগামী শুক্রবার". Then re-run BN for any changed templates.
2. **Second model: `ollama-gpt-oss-20b`.** It is a smaller open reasoning model, likely weaker in Bangla, so it is a better place to look for a gap. Cost is about 880 requests on the free tier.
3. **Condition C2 (Bangla system prompt):** run it only after a model shows a C1 gap, or on gemma4:31b as a robustness check (about 880 requests).
4. **Full 690 run:** about 6,800 requests per model across both languages. Run it on the model with the largest pilot gap; multi-domain tasks carry most of the signal.
