# Failure-analysis report: gemma4:31b, English (C0) vs Bangla (C6), WorkBench 90-task pilot

This report applies the owner's pipeline ([`instructions/failure_analysis_pipeline.md`](../../../instructions/failure_analysis_pipeline.md), sections §1–§14) to one model. The companion report for gpt-oss:20b is [`../pilot_ollama-gpt-oss-20b_c6_vs_c0/report.md`](../pilot_ollama-gpt-oss-20b_c6_vs_c0/report.md).

- **English** = condition C0: everything in English. Run `ollama-gemma4-31b_all_2026-10-04_11-42-18`.
- **Bangla** = condition C6: Bangla task and system prompt, English tool descriptions, replies forced to Bangla. Run `ollama-gemma4-31b_all_2026-10-05_16-12-03`. There is no C7.
- **Dataset:** WorkBench only, 90 tasks (15 per domain), one run per side, no repeats. Pass = WorkBench `correct` (the final database state equals the ground truth).
- **Where every number comes from:**
  - [`stats.json`](stats.json): the statistics and §10 counts, written by `scripts/failure_pipeline.py stats --all` and `counts --all` on `labels_final.csv`;
  - [`labels_final.csv`](labels_final.csv): the only source for label counts;
  - [`agreement.json`](agreement.json): inter-annotator agreement.
  - The comparison-set distributions (EN-fail/BN-fail and the English side) are counted directly from `labels_final.csv`.
- **Gap direction:** gap = EN rate − BN rate, so a positive gap means Bangla is worse. MELR = (EN − BN) / EN.
- **Model annotators:** every label comes from a Claude model, not a human: the first annotator A1, the blind second reviewer A2 and the adjudicator ADJ. The owner has not yet done the native-speaker review of the Bangla translations.

**Headline.** English 73/90 = 81.1%, Bangla 74/90 = 82.2%. The gap is −1.1 pp (95% CI −10.0 to +7.8) and MELR is −1.4% (−12.5% to +8.6%). McNemar exact p = 1.0 (Holm 1.0), and the paired OR b/c = 7/8 = 0.875 (0.270–2.761). There is no detectable language gap. Of the 7 EN-pass/BN-fail cases:
- 3 are general model weaknesses that also occur in English;
- 2 are Genuine Bangla-related (both fragile);
- 1 is a translation error;
- 1 is benchmark ambiguity.

---

## §1–§2. Basic outcome

### Overall (n = 90 pairs)

| measure | value | 95% CI |
|---|---|---|
| English success | 73/90 = 81.1% | 71.8–87.9% (Wilson) |
| Bangla success | 74/90 = 82.2% | 73.1–88.8% (Wilson) |
| Absolute gap EN − BN | −1.1 pp (−1/90) | −10.0 to +7.8 pp (paired bootstrap, 10,000 resamples, seed 20261004) |
| MELR (EN − BN) / EN | −1.4% | −12.5% to +8.6% (same resamples). Resamples with EN = 0 are excluded; there were **0 of 10,000** here. |

### Paired outcomes (n = 90)

| | Bangla pass | Bangla fail | total |
|---|---|---|---|
| **English pass** | EN-pass/BN-pass **66** | **EN-pass/BN-fail 7** ← the most important group | 73 |
| **English fail** | EN-fail/BN-pass **8** | EN-fail/BN-fail **9** | 17 |
| total | 74 | 16 | 90 |

**EN-pass/BN-fail (7 of 90 pairs, 7.8%) is the cleanest group for Bangla-specific degradation:** the same task succeeded in English and failed in Bangla. It is balanced by 8 pairs in the opposite direction (EN-fail/BN-pass).

### Per domain (n = 15 each; descriptive only)

`stats.json` gives Wilson CIs for the per-domain rates. By design (plan, "Statistics"), it gives no interval or p-value for the per-domain gap or MELR, so those are point values only.

| domain | n | English | Bangla | gap EN − BN | MELR | EN-pass/BN-pass | **EN-pass/BN-fail** | EN-fail/BN-pass | EN-fail/BN-fail |
|---|---|---|---|---|---|---|---|---|---|
| email | 15 | 15/15 = 100.0% (79.6–100.0) | 14/15 = 93.3% (70.2–98.8) | +6.7 pp | +6.7% | 14 | **1** | 0 | 0 |
| calendar | 15 | 13/15 = 86.7% (62.1–96.3) | 14/15 = 93.3% (70.2–98.8) | −6.7 pp | −7.7% | 13 | **0** | 1 | 1 |
| analytics | 15 | 13/15 = 86.7% (62.1–96.3) | 10/15 = 66.7% (41.7–84.8) | +20.0 pp | +23.1% | 10 | **3** | 0 | 2 |
| project_management | 15 | 13/15 = 86.7% (62.1–96.3) | 14/15 = 93.3% (70.2–98.8) | −6.7 pp | −7.7% | 13 | **0** | 1 | 1 |
| customer_relationship_manager | 15 | 11/15 = 73.3% (48.0–89.1) | 13/15 = 86.7% (62.1–96.3) | −13.3 pp | −18.2% | 10 | **1** | 3 | 1 |
| multi_domain | 15 | 8/15 = 53.3% (30.1–75.2) | 9/15 = 60.0% (35.7–80.2) | −6.7 pp | −12.5% | 6 | **2** | 3 | 4 |
| **overall** | 90 | 73/90 = 81.1% | 74/90 = 82.2% | −1.1 pp | −1.4% | 66 | **7** | 8 | 9 |

Analytics is the only domain with a visible one-way gap: 3 EN-pass/BN-fail pairs against 0 EN-fail/BN-pass. At n = 15 this is descriptive only, and the 3 cases have three different confounds (§10.10).

---

## §3. Case selection: what was analysed

| pair class | pairs | what was done | label rows |
|---|---|---|---|
| EN-pass/BN-fail | 7 | **Every case.** A full §4 trace note (EN and BN traces read side by side), full labels, the §8 decision tree and §9 evidence. All 7 also got a blind second review (A2) and adjudication. | 7 (BN side) |
| EN-fail/BN-fail | 9 | **The full set, not a sample.** This is more accurate than the pipeline's "smaller comparison sample". **Both** failures get a first failure point, failure type, confound and one evidence line. | 18 (EN + BN) |
| EN-fail/BN-pass | 8 | The same short labels for the English failure, so that tool/environment confounds can be filtered on both sides, plus a one-line "interesting?" note for each. | 8 (EN side) |
| EN-pass/BN-pass | 66 | **Not analysed.** Pipeline §3 asks for it only "if needed", and no listed output needs a stable-success contrast. | 0 |
| **total** | 90 | | **33** |

EN-fail/BN-pass short labels (all 8, from `labels_final.csv`; the notes are in [`trace_notes.md`](trace_notes.md)):

| task | first failure point (EN) | confound | note |
|---|---|---|---|
| calendar:63 | Tool-argument construction | General | EN booked 11:00, overlapping 10:00–12:00; BN found 13:00 |
| crm:42 | Task constraint preservation (Dialogue-state failure) | Unclear | EN applied status=Lead, then dropped it after an empty result |
| crm:46 | Tool-argument construction | Unclear | EN searched without status='Lead' |
| crm:57 | Instruction understanding | Unclear | EN read "Give Akira … customers" as "email Akira a list" |
| project_management:28 | Task constraint preservation | General | EN moved a task due today as if it were overdue |
| multi_domain:6 | Tool-argument construction | General | EN booked a conflicting slot, then self-corrected; the shifted event ID fails the strict state comparison |
| multi_domain:102 | Tool-argument construction | General | EN chose 15:00, the same wrong slot as BN multi_domain:84 |
| multi_domain:130 | Task constraint preservation | General | EN created the task before evaluating its condition |

None of the 8 English failures is Tool/environment, so the tool/environment filter removes nothing on either side (§11).

---

## §4–§9. Method summary

The full rules are in [`../annotation_rules.md`](../annotation_rules.md), and the per-case notes are in [`trace_notes.md`](trace_notes.md). Where a note has an "Adjudicated" line, that line and `labels_final.csv` are final.

- **§4 Trace note.** Each EN-pass/BN-fail case has a note with every §4 field:
  - the task goal;
  - what happened in English, and what happened in Bangla;
  - the first divergence;
  - the final failed or missing action;
  - the failure type, root cause and confound decision;
  - the evidence (tool-call quotes).
- **§5 First failure point.** Exactly one of the 11 labels. It is the earliest upstream point after which the correct final state became unreachable, not the last visible error. Convention C2 judges "unreachable" on the trajectory the agent actually followed.
- **§6 Failure type.** Exactly one of the 9 types. Under convention C1 the type names the failure *at* the first failure point. The two fields are therefore one judgment, and their distributions are **not independent**: for example, Entity or slot grounding always maps to Understanding failure.
- **§7 Confound.** Exactly one of the 7.
  - **"Bangla user-simulator error" is structurally N/A.** WorkBench tasks are single-turn and there is no user simulator, so this confound is never used and decision-tree Step 2 is always `na`.
  - Translation needs a reading that the Bangla introduced and that this failure used. The paired English run must not have taken the same reading (C5, C5(3)).
  - General needs the same class of mechanism in a C0 failure, cited by task ID.
  - Benchmark/task ambiguity has its own WorkBench definition (C6).
- **§8 Decision tree.** Each EN-pass/BN-fail case gets seven one-word outcomes:
  - S1: the translation is valid;
  - S2: user simulator (always N/A);
  - S3: the agent understood the request;
  - S4: right tool or action;
  - S5: correct arguments;
  - S6: the tool or environment executed;
  - S7: completion was verified.

  The first `fail` sets the root cause; later steps are descriptive only (C3).
- **§9 Evidence.** Every label row carries:
  - the English outcome and the Bangla outcome;
  - the tool call or message that proves the failure;
  - the first failure point;
  - for EN-pass/BN-fail, why the case is or is not just a general model failure.
- **Conventions.** C1–C7 were written during the gemma adjudication, and C8–C12 during the gpt-oss adjudication. The review amendments came in fix round 1: C5(3), the C11 note, the C6 clarification, the C1 tie-break and the C2 amendment. All of them are applied to every row of both models.

---

## §10. Counts for EN-pass/BN-fail (n = 7 cases out of 90 pairs; BN-side labels)

### Case list

| task | domain | first failure point | failure type | confound | tree (first fail) |
|---|---|---|---|---|---|
| email:41 | email | Entity or slot grounding | Understanding failure | **Genuine Bangla-related** | S3 |
| customer_relationship_manager:77 | CRM | Task constraint preservation | Wrong tool/action | General model weakness | S4 |
| analytics:20 | analytics | Instruction understanding | Understanding failure | **Genuine Bangla-related** | S3 |
| analytics:98 | analytics | Planning | Planning failure | Benchmark/task ambiguity | S4 |
| analytics:119 | analytics | Tool-argument construction | Wrong tool argument | General model weakness | S5 |
| multi_domain:84 | multi_domain | Tool-argument construction | Wrong tool argument | General model weakness | S5 |
| multi_domain:120 | multi_domain | Entity or slot grounding | Understanding failure | Translation/localization | S1 |

### 10.1 Failure type distribution (denominator 7)

| failure type | n | % of 7 |
|---|---|---|
| Understanding failure | 3 | 42.9% |
| Wrong tool argument | 2 | 28.6% |
| Planning failure | 1 | 14.3% |
| Wrong tool/action | 1 | 14.3% |
| Execution/environment failure | 0 | 0.0% |
| Verification failure | 0 | 0.0% |
| Premature abandonment | 0 | 0.0% |
| Dialogue-state failure | 0 | 0.0% |
| Unclear | 0 | 0.0% |

### 10.2 First failure point distribution (denominator 7)

| first failure point | n | % of 7 |
|---|---|---|
| Entity or slot grounding | 2 | 28.6% |
| Tool-argument construction | 2 | 28.6% |
| Instruction understanding | 1 | 14.3% |
| Task constraint preservation | 1 | 14.3% |
| Planning | 1 | 14.3% |
| Tool selection, Tool execution, Result verification, Premature termination, Final response only, Unclear | 0 each | 0.0% |

### 10.3 Confound distribution (denominator 7)

| confound | n | % of 7 | tasks |
|---|---|---|---|
| General model weakness present in both English and Bangla | 3 | 42.9% | crm:77, analytics:119, md:84 |
| Genuine Bangla-related agent failure | 2 | 28.6% | email:41, analytics:20 |
| Translation/localization error | 1 | 14.3% | md:120 |
| Benchmark/task ambiguity | 1 | 14.3% | analytics:98 |
| Bangla user-simulator error | 0 | 0.0% | structurally N/A |
| Tool/environment failure | 0 | 0.0% | |
| Unclear | 0 | 0.0% | |

### 10.4 Genuine Bangla-related cases after filtering

The filter removes the user-simulator, translation and tool/environment confounds. It removes **1 of the 7 cases** (md:120, Translation), so **6 remain**. Of those 6, **2 are Genuine Bangla-related: email:41 and analytics:20** (33.3% of the remaining 6, or 28.6% of all 7). The other 4 are General (3) and Benchmark (1).

### 10.5 User-simulator-caused cases

**0 of 7.** This is structurally N/A, because WorkBench has no user simulator.

### 10.6 Translation-caused cases

**1 of 7: md:120.** "আগামী শুক্রবার" was read as the coming Friday, 2023-12-01; the ground truth is 2023-12-08. The label is provisional until the native-speaker review. Across all 33 label rows, md:120 BN is the only Translation label.

### 10.7 Tool/environment-caused cases

**0 of 7.** No row of any pair class has this confound for gemma4:31b (0 of 33).

### 10.8 Dataset-wise distribution

WorkBench is the only dataset: 90 pairs, 7 cases. The distributions are the same as 10.1–10.3.

### 10.9 Model-wise distribution (EN-pass/BN-fail; this model next to gpt-oss:20b)

| | gemma4:31b (n = 7 of 90) | gpt-oss:20b (n = 15 of 90) |
|---|---|---|
| **Failure type** | | |
| Understanding failure | 3 (42.9%) | 1 (6.7%) |
| Planning failure | 1 (14.3%) | 0 |
| Wrong tool/action | 1 (14.3%) | 2 (13.3%) |
| Wrong tool argument | 2 (28.6%) | 11 (73.3%) |
| Premature abandonment | 0 | 1 (6.7%) |
| others | 0 | 0 |
| **First failure point** | | |
| Instruction understanding | 1 (14.3%) | 0 |
| Entity or slot grounding | 2 (28.6%) | 1 (6.7%) |
| Task constraint preservation | 1 (14.3%) | 1 (6.7%) |
| Planning | 1 (14.3%) | 0 |
| Tool selection | 0 | 1 (6.7%) |
| Tool-argument construction | 2 (28.6%) | 11 (73.3%) |
| Premature termination | 0 | 1 (6.7%) |
| others | 0 | 0 |
| **Confound** | | |
| Genuine Bangla-related | 2 (28.6%) | 1 (6.7%) |
| Translation/localization | 1 (14.3%) | 0 |
| Benchmark/task ambiguity | 1 (14.3%) | 0 |
| General model weakness | 3 (42.9%) | 14 (93.3%) |
| User simulator / Tool/environment / Unclear | 0 / 0 / 0 | 0 / 0 / 0 |

gemma's EN-pass/BN-fail cases are spread across reading and reasoning points. gpt-oss's are concentrated at tool-argument construction: invented addresses and malformed keywords.

### 10.10 Domain-wise distribution (EN-pass/BN-fail cases per domain)

| domain | cases / 15 pairs | first failure point | failure type | confound |
|---|---|---|---|---|
| email | 1 | Entity or slot grounding 1 | Understanding 1 | Genuine 1 |
| calendar | 0 | — | — | — |
| analytics | 3 | Instruction understanding 1, Planning 1, Tool-argument construction 1 | Understanding 1, Planning 1, Wrong tool argument 1 | Genuine 1, Benchmark 1, General 1 |
| project_management | 0 | — | — | — |
| customer_relationship_manager | 1 | Task constraint preservation 1 | Wrong tool/action 1 | General 1 |
| multi_domain | 2 | Entity or slot grounding 1, Tool-argument construction 1 | Understanding 1, Wrong tool argument 1 | Translation 1, General 1 |

### 10.11 Comparison sets: EN-fail/BN-fail and the English side

These tables give the same three distributions for the failures that are not EN-pass/BN-fail. They help separate a general weakness from a Bangla-only one. They are counted from `labels_final.csv`.

| failure type | EN-pass/BN-fail, BN (n = 7) | EN-fail/BN-fail, BN (n = 9) | EN-fail/BN-fail, EN (n = 9) | EN-fail/BN-pass, EN (n = 8) | all English failures (n = 17) |
|---|---|---|---|---|---|
| Understanding failure | 3 | 3 | 3 | 1 | 4 |
| Planning failure | 1 | 0 | 1 | 0 | 1 |
| Wrong tool/action | 1 | 1 | 0 | 2 | 2 |
| Wrong tool argument | 2 | 2 | 3 | 4 | 7 |
| Verification failure | 0 | 1 | 2 | 0 | 2 |
| Premature abandonment | 0 | 2 | 0 | 0 | 0 |
| Dialogue-state failure | 0 | 0 | 0 | 1 | 1 |
| Execution/environment, Unclear | 0 | 0 | 0 | 0 | 0 |

| first failure point | EN-pass/BN-fail, BN (7) | EN-fail/BN-fail, BN (9) | EN-fail/BN-fail, EN (9) | EN-fail/BN-pass, EN (8) | all English (17) |
|---|---|---|---|---|---|
| Instruction understanding | 1 | 0 | 0 | 1 | 1 |
| Entity or slot grounding | 2 | 2 | 2 | 0 | 2 |
| Task constraint preservation | 1 | 2 | 2 | 3 | 5 |
| Planning | 1 | 0 | 1 | 0 | 1 |
| Tool-argument construction | 2 | 2 | 2 | 4 | 6 |
| Result verification | 0 | 1 | 2 | 0 | 2 |
| Premature termination | 0 | 2 | 0 | 0 | 0 |
| others | 0 | 0 | 0 | 0 | 0 |

| confound | EN-pass/BN-fail, BN (7) | EN-fail/BN-fail, BN (9) | EN-fail/BN-fail, EN (9) | EN-fail/BN-pass, EN (8) | all English (17) |
|---|---|---|---|---|---|
| Genuine Bangla-related | 2 | 0 | 0 | 0 | 0 |
| Translation/localization | 1 | 0 | 0 | 0 | 0 |
| Tool/environment | 0 | 0 | 0 | 0 | 0 |
| Benchmark/task ambiguity | 1 | 1 (calendar:79) | 1 (calendar:79) | 0 | 1 |
| General model weakness | 3 | 6 | 7 | 5 | 12 |
| Unclear | 0 | 2 (crm:74, md:149: empty model responses) | 1 (analytics:76) | 3 (crm:42, :46, :57) | 4 |

What these tables show:
- **General is the largest confound in every set:** 3/7 EN-pass/BN-fail, 6/9 both-fail BN, 12/17 English failures.
- **The Bangla-linked labels appear only in EN-pass/BN-fail.** The 2 Genuine labels and the 1 Translation label occur nowhere else.
- **The reasoning errors behind the General cases are the model's usual ones.** Tool-argument construction and Task constraint preservation together account for 11 of the 17 English failures (64.7%) and 3 of the 7 EN-pass/BN-fail cases.
- **Group the "due today counted as overdue" mechanism by first failure point, not by type.** It appears in project_management:64 (EN and BN) and project_management:28 (EN). All three share the first failure point Task constraint preservation, but under the C1 sub-rule their types differ (Understanding failure on pm:64, Wrong tool/action on pm:28). Grouping by type would split one mechanism. None of these is EN-pass/BN-fail. gpt-oss:20b shows the same mechanism in pm:60 BN and pm:28 EN (the latter inferred from a lost trace), both Task constraint preservation / Wrong tool/action. Its calendar:63 EN/BN (a meeting later today counted as already held) is a related today-boundary error and is kept separate.

### 10.12 §6 watch items in WorkBench

Pipeline §6 lists five items to watch. They were written for τ²-bench; WorkBench is single-turn, so they map as below. Counts are from `labels_final.csv`: "EN-pass/BN-fail" is the 7 BN rows, and "all failures" is all 33 label rows (16 BN, 17 EN). The decision tree (S1–S7) exists only for EN-pass/BN-fail.

| §6 watch item | WorkBench mapping | EN-pass/BN-fail (of 7) | all failures (of 33 rows) |
|---|---|---|---|
| premature STOP before the final tool call | first failure point Premature termination (all typed Premature abandonment) | 0 | 2, both BN (crm:74, md:149; the two empty responses, Unclear): 2 of 16 BN, 0 of 17 EN |
| compound task partially completed | the Premature termination rows above, plus decision-tree S7 (completion verified) = fail | S7 = fail in 2 (email:41, crm:77) | S7 not recorded outside EN-pass/BN-fail |
| changed budget or task constraint | first failure point Task constraint preservation | 1 (crm:77) | 8: 3 of 16 BN (crm:77, analytics:76, pm:64), 5 of 17 EN (crm:42, crm:74, pm:28, pm:64, md:130) |
| internal ID used as a natural-language name | searched in the label evidence | 0 | 0 |
| wrong or early user-simulator termination | N/A: WorkBench has no user simulator | N/A | N/A |

Neither S7 = fail case begins at Premature termination: email:41 BN stopped and asked the user after a grounding error, without forwarding, and crm:77 BN kept a wrong write. The constraint-change item is more common among English failures (5 of 17) than Bangla failures (3 of 16), and only 1 of the 7 EN-pass/BN-fail cases.

---

## §11. Statistical analysis

| statistic | value |
|---|---|
| McNemar exact p (b = 7, c = 8) | **1.0000** |
| Holm-adjusted p (family: the 2 model comparisons; gpt-oss raw p = 0.4244) | **1.0000** |
| Risk difference (= gap EN − BN) | −1.1 pp, 95% CI −10.0 to +7.8 (paired bootstrap) |
| Paired odds ratio b/c | 7/8 = **0.875**, exact conditional 95% CI **0.270–2.761** (Clopper–Pearson on b/(b+c)) |
| MELR | −1.4%, 95% CI −12.5% to +8.6% (0 resamples with EN = 0 excluded) |
| English rate | 81.1% (71.8–87.9) |
| Bangla rate | 82.2% (73.1–88.8) |

**Effect size and uncertainty, not only p:**
- The point estimate is a 1.1-point *advantage* for Bangla.
- The gap interval runs from Bangla 10.0 points better to 7.8 points worse.
- The odds-ratio interval (0.27–2.76) includes both a large Bangla advantage and a large Bangla disadvantage among discordant pairs.
- The pilot can rule out only large gaps (roughly beyond 8–10 points); it cannot detect a small one.

### Sensitivity analysis

Each row is a filtered paired analysis. The p-values are raw McNemar p; Holm applies to the "all" row.

| analysis | n pairs | English | Bangla | gap EN − BN (95% CI) | MELR (95% CI) | paired counts (pp/pf/fp/ff) | McNemar p | OR b/c (95% CI) |
|---|---|---|---|---|---|---|---|---|
| all pairs | 90 | 73/90 = 81.1% | 74/90 = 82.2% | −1.1 pp (−10.0, +7.8) | −1.4% (−12.5, +8.6) | 66/7/8/9 | 1.0000 | 0.875 (0.270–2.761) |
| translation removed (md:120) | 89 | 72/89 = 80.9% | 74/89 = 83.1% | −2.2 pp (−10.1, +5.6) | −2.8% (−14.1, +6.8) | 66/6/8/9 | 0.7905 | 0.750 (0.214–2.465) |
| user simulator removed | 90 | 73/90 = 81.1% | 74/90 = 82.2% | −1.1 pp (−10.0, +7.8) | −1.4% (−12.5, +8.6) | 66/7/8/9 | 1.0000 | 0.875 (0.270–2.761) |
| tool/environment removed (none labelled) | 90 | 73/90 = 81.1% | 74/90 = 82.2% | −1.1 pp (−10.0, +7.8) | −1.4% (−12.5, +8.6) | 66/7/8/9 | 1.0000 | 0.875 (0.270–2.761) |

- **"User simulator removed" is identical to "all" by construction.** WorkBench has no user simulator, so 0 pairs are removed.
- **"Tool/environment removed" is also identical to "all".** No gemma label row (0 of 33) has that confound.
- **"Translation removed" drops md:120,** an EN-pass/BN-fail pair. This moves the estimate further toward a Bangla advantage. No conclusion changes.
- In every row, 0 bootstrap resamples had EN = 0.

---

## §12. Findings

Each finding follows Observation → Evidence → Root cause → Boundary. "Filtering" means removing the translation, user-simulator and tool/environment confounds (§10.4). With 7 cases and one run per side, every finding describes this pilot only; none is a population claim.

### Finding 1: most Bangla-only failures are reasoning errors the model also makes in English

> We find that **general model weaknesses that also occur in English** account for **3 of 7 (42.9%)** EN-pass/BN-fail cases. Manual trajectory analysis shows that these failures usually begin at **tool-argument construction** (2 of 3: date arithmetic and free-slot computation); the third begins at task constraint preservation (a misapplied 6-week threshold). After filtering translation, user-simulator and tool/environment confounds, **6 of 7** cases remain, and 3 of those 6 (50%) are still General. This suggests that about half of the remaining Bangla-only failures are labelled General: a matching C0 failure exists, so they are not attributable case by case to the Bangla input. An aggregate Bangla excess cannot be excluded and needs repeat runs.

- **Evidence.**
  - multi_domain:84: BN called `create_event(… event_start="2023-12-01 15:00:00")` and said "আপনি দুপুর ৩টার পর ফ্রি আছেন" ("you are free after 3 pm"), although 13:00–13:30 was free. C0 multi_domain:102 EN chose the identical 15:00.
  - analytics:119: BN used `time_min="2023-10-26"` (35 days back) for "গত 4 সপ্তাহের" ("of the last 4 weeks"), while restating "৪ সপ্তাহ" ("4 weeks"). C0 crm:74 EN turned "6 weeks" into "since October 16th".
  - crm:77: BN kept `update_customer(00000147 → Lost)` for a customer last contacted on 2023-10-29 (32 days earlier; the 6-week cutoff is 2023-10-19). EN made the same wrong update at step 1 and reverted it.
- **Root cause.** Language-neutral computation on correctly read values (convention C4). Each case has a cited C0 analogue.
- **Boundary.** With one run per side, it cannot be told whether these errors land on the English or the Bangla run by chance. Among the 8 EN-fail/BN-pass pairs, the same mechanism classes appear in the other direction: slot errors in calendar:63, md:6 and md:102, and a gate error in pm:28.

### Finding 2: a small, fragile Bangla-linked signal around time phrases and one chart request

> We find that **Bangla time-phrase grounding** (a relative date or range resolved to a different referent) accounts for **2 of 7 (28.6%)** EN-pass/BN-fail cases: email:41 ("গত সপ্তাহে", "last week") and md:120 ("আগামী শুক্রবার", "next Friday"). Manual trajectory analysis shows that these failures begin at **entity or slot grounding**. After filtering the translation confound (md:120), **1 of the 6** remaining cases follows this pattern (email:41). Adding analytics:20 (instruction understanding of "ডিস্ট্রিবিউশন … চার্টে", "distribution … in a chart"), **2 of 6 (33.3%)** remaining cases are Genuine Bangla-related. This suggests a candidate pattern to test with repeat runs and the native-speaker review, not a demonstrated Bangla effect.

- **Evidence.**
  - email:41: EN searched `date_min="2023-11-19", date_max="2023-11-26"` and forwarded both emails. BN searched `date_min="2023-11-23", date_max="2023-11-29"` and got `[]`. It then found both emails with an undated search, but still rejected them as "গত সপ্তাহের নয়" ("not from last week").
  - md:120: EN called `create_task(… due_date="2023-12-08")`; BN used `due_date="2023-12-01"` and wrote "আগামী শুক্রবার (১ ডিসেম্বর, ২০২৩)" ("next Friday (1 December 2023)").
  - analytics:20: EN used `plot_type="histogram"`; BN used `plot_type="line"` for both metrics.
  - No C0 failure mis-grounds a relative week, "next Friday" or a plot type. C0 does misread relative dates in other ways: calendar:79 EN grounded a bare relative weekday ("Wednesday") to the past day and is labelled Benchmark/task ambiguity, and analytics:69 EN used an exclusive "since" boundary (General).
- **Root cause.**
  - email:41 and analytics:20: a Bangla phrase was read with a different referent, and the translation is faithful, so the label is Genuine.
  - md:120: the Bangla wording itself favours the "tomorrow" reading and the English source does not, so the cause is the translation (C5).
- **Boundary.** All three labels are weak:
  - email:41 becomes Translation if the native-speaker review finds that "গত সপ্তাহে" leans toward "the past 7 days".
  - analytics:20: analytics:15 BN read the same phrasing correctly, as a histogram.
  - md:120: md:169 BN and md:200 BN read the same phrase as 12-08.
  - With one run per side, run-to-run variance cannot be ruled out for any of them.

### Finding 3: no case labelled Tool/environment, but three Bangla-only call anomalies

> We find that **tool/environment failures** account for **0 of 7 (0.0%)** EN-pass/BN-fail cases, and no case begins at tool execution. After filtering, **6 of 7** cases remain, none of them in this pattern. This suggests only that no case was labelled Tool/environment. It does not show that the Bangla input left tool calling unaffected, because three call anomalies occur on the Bangla side only (below).

- **Evidence.**
  - 0 of 33 label rows are Tool/environment.
  - **Bangla-script tool arguments: 0.** Checked in the raw traces: none of the 285 C6 tool calls and none of the 356 C0 tool calls (Final Answer steps excluded) has a Bangla-script character in its arguments.
  - **One hallucinated tool name, Bangla only.** crm:77 BN called the nonexistent `customer_relationship_manager_update_task`: 1 of 90 C6 runs vs 0 of 90 C0 runs have an unrecognised call (`task_table.csv`). It followed a General threshold error, and per its label it kept BN from reverting the update as EN did. The tool descriptions are in English in C6, so there is no visible Bangla link.
  - **Two empty model responses, Bangla only.** crm:74 BN (an empty first response, no tool call) and md:149 BN (empty after two read calls): 2 of 90 C6 runs vs 0 of 90 C0 runs. Both are EN-fail/BN-fail pairs labelled Premature termination / Premature abandonment / Unclear (`labels_final.csv`), so they do not enter the EN-pass/BN-fail counts.
- **Root cause.** Not established. No error was recorded for the empty responses, so they cannot be attributed to the provider or to Bangla. The invalid tool name has no C0 analogue but no visible Bangla link either.
- **Boundary.** These are 3 events in 90 Bangla runs against 0 in 90 English runs, with one run per side: too few to separate from chance. Repeat runs should count empty responses and unrecognised tool calls per condition.

### Finding 4: the overall gap is not detectable, within wide bounds

> We find that **EN-pass/BN-fail cases** account for **7 of 90 pairs (7.8%)**, against **8 of 90 (8.9%)** EN-fail/BN-pass pairs. Manual trajectory analysis shows that these failures begin at varied points (entity or slot grounding and tool-argument construction, 2 of 7 each; §10.2). After filtering translation, user-simulator and tool/environment confounds, **6 of 7** EN-pass/BN-fail cases remain (6 vs 8 discordant pairs over 89 pairs), suggesting no detectable overall gap, within bounds too wide to exclude a gap of about 8–10 points.

- **Observation.** The Bangla and English success rates are almost the same: 74/90 vs 73/90.
- **Evidence.** Gap −1.1 pp (−10.0, +7.8), MELR −1.4% (−12.5, +8.6), OR 0.875 (0.270–2.761), McNemar p = 1.0, Holm 1.0. Every sensitivity row keeps the CI around 0.
- **Root cause.** The discordant pairs are balanced: 7 EN-pass/BN-fail vs 8 EN-fail/BN-pass (6 vs 8 after the translation filter).
- **Boundary.** n = 90, one run per side, and the two sides ran on different days. Gaps smaller than about 8–10 points can be neither detected nor ruled out.

---

## §13. Paper outputs

### 13.1 Overall English vs Bangla success table

| model | n | English (C0) | Bangla (C6) | gap EN − BN (95% CI) | McNemar p | Holm p |
|---|---|---|---|---|---|---|
| gemma4:31b | 90 | 73/90 = 81.1% (71.8–87.9) | 74/90 = 82.2% (73.1–88.8) | −1.1 pp (−10.0, +7.8) | 1.0000 | 1.0000 |
| gpt-oss:20b | 90 | 53/90 = 58.9% (48.6–68.5) | 48/90 = 53.3% (43.1–63.3) | +5.6 pp (−5.6, +16.7) | 0.4244 | 0.8487 |

### 13.2 MELR by dataset and model (WorkBench only)

| dataset | model | MELR (95% CI, paired bootstrap) | resamples with EN = 0 excluded |
|---|---|---|---|
| WorkBench | gemma4:31b | −1.4% (−12.5%, +8.6%) | 0 of 10,000 |
| WorkBench | gpt-oss:20b | +9.4% (−9.8%, +25.9%) | 0 of 10,000 |

### 13.3 Paired outcome table

| model | EN-pass/BN-pass | **EN-pass/BN-fail** | EN-fail/BN-pass | EN-fail/BN-fail | n |
|---|---|---|---|---|---|
| gemma4:31b | 66 | **7** | 8 | 9 | 90 |
| gpt-oss:20b | 38 | **15** | 10 | 27 | 90 |

### 13.4 Failure type distribution for EN-pass/BN-fail

See §10.1 (this model) and §10.9 (both models).

### 13.5 First failure point distribution

See §10.2 (this model) and §10.9 (both models).

### 13.6 Confound filtering table

| confound | EN-pass/BN-fail cases (of 7) | removed by the §10.4 filter? | pairs removed in the §11 sensitivity row (all pair classes) |
|---|---|---|---|
| Genuine Bangla-related | 2 | no (this is the signal) | — |
| Bangla user-simulator error | 0 | yes (N/A) | 0 |
| Translation/localization error | 1 (md:120) | yes | 1 (md:120) |
| Tool/environment failure | 0 | yes | 0 |
| Benchmark/task ambiguity | 1 (analytics:98) | no (not part of the plan's filter) | — |
| General model weakness | 3 | no | — |
| Unclear | 0 | no | — |

### 13.7 Before/after confound-filtered results

| | before (all) | after translation removed | after user simulator removed | after tool/environment removed |
|---|---|---|---|---|
| n pairs | 90 | 89 | 90 | 90 |
| EN-pass/BN-fail | 7 | 6 | 7 | 7 |
| EN-fail/BN-pass | 8 | 8 | 8 | 8 |
| gap EN − BN | −1.1 pp (−10.0, +7.8) | −2.2 pp (−10.1, +5.6) | −1.1 pp | −1.1 pp |
| McNemar p | 1.0000 | 0.7905 | 1.0000 | 1.0000 |
| OR b/c | 0.875 (0.270–2.761) | 0.750 (0.214–2.465) | 0.875 | 0.875 |
| Genuine among EN-pass/BN-fail | 2 of 7 | 2 of 6 | 2 of 7 | 2 of 7 |

### 13.8 Case studies

These three cases match the quantitative pattern:
- one General case, from the largest confound (3/7);
- the Genuine grounding case and the Translation grounding case, which together make up the 2/7 entity-or-slot-grounding cases.

The excerpts here are short; longer step lists are in the appendix.

**Case 1: multi_domain:84 (General, tool-argument construction).** *If olga has overdue tasks, book a 30-minute meeting with her at the earliest time I'm free tomorrow.*
- **Both runs:** the same three read calls, which saw the same calendar.
- **English:** booked `event_start="2023-12-01 13:00:00"`.
- **Bangla:** booked `event_start="2023-12-01 15:00:00"` and explained "আপনি দুপুর ৩টার পর ফ্রি আছেন" ("you are free after 3 pm"), skipping the free 13:00–13:30 gap.
- **Why General:** the Bangla phrase "আগামীকাল আমি সবচেয়ে আগে যখন ফ্রি থাকব" ("tomorrow, the earliest time I'm free") was read correctly. The error is in the slot computation, and C0 multi_domain:102 EN chose the identical 15:00 slot.
- **Labels:** Tool-argument construction / Wrong tool argument / General.

**Case 2: email:41 (Genuine, entity or slot grounding).** *Forward all the emails from anaya last week about 'Update on Board of Directors Conclave' to nadia.*
- **English:** searched the calendar week (`date_min="2023-11-19", date_max="2023-11-26"`) and forwarded 00000120 and 00000346.
- **Bangla:** grounded "গত সপ্তাহে" ("last week") as the rolling window `2023-11-23..2023-11-29` and got `[]`. An undated search at step 5 found both emails, but the agent still answered "… গত সপ্তাহের নয়। আপনি কি অন্য কোনো তারিখ … চেক করতে চান?" ("… not from last week. Do you want me to check another date …?"). It never called `forward_email`.
- **Why Genuine:** the translation is faithful, and no C0 failure mis-grounds a relative week. The label is provisional, because the phrase is on the native-speaker review list.

**Case 3: multi_domain:120 (Translation, entity or slot grounding).** *Create a backlog task … with a deadline of next Friday.*
- **Both runs:** the analytics read, the assignee search and the `create_task` call are identical, except for the deadline.
- **English:** used `due_date="2023-12-08"`.
- **Bangla:** used `due_date="2023-12-01"`, glossed as "আগামী শুক্রবার (১ ডিসেম্বর, ২০২৩)" ("next Friday (1 December 2023)").
- **Why Translation:** the task is set on Thursday 2023-11-30, and "আগামী শুক্রবার" ("the coming Friday") favours tomorrow. The English source does not favour that reading, and this model's English run read it as 12-08. Under C5 and C5(3), the Bangla wording therefore caused the failure.
- **Caveat:** the label is provisional; md:169 BN and md:200 BN read the same phrase as 12-08.

### 13.9 Appendix

See the Appendix at the end of this report: the annotation rules, file links, and longer trace excerpts for the three case studies.

---

## §14. Quality-control checklist

| | item | evidence |
|---|---|---|
| ☑ | Every task ID is aligned between English and Bangla | `task_table.csv` has 90 rows and 90 distinct `task_uid`s. The `table` command asserts the alignment. It also asserts that EN/BN pass/fail and `pair_class` match the existing comparison folder for all 90 rows ([`../annotation_rules.md`](../annotation_rules.md), "Inputs and conventions"). One EN run ID and one BN run ID cover all rows. |
| ☑ | Every metric has a denominator | Rates are given as k/n, shares as n of 7 (or of the stated set), and each sensitivity row gives its number of pairs. |
| ☑ | EN-pass/BN-fail is separated from both-fail | §10 counts only the 7 EN-pass/BN-fail BN rows (`stats.json` `counts.population`). Both-fail is reported separately in §10.11. |
| ☑ | Translation errors are not counted as genuine Bangla agent failures | md:120 is labelled Translation (§10.6). It is excluded from Genuine and removed both by the §10.4 filter and in the sensitivity row. |
| ☑ | User-simulator errors are counted separately | §10.5: 0, structurally N/A. The sensitivity row is identical to "all", and the report says so. |
| ☑ | Tool/environment failures are counted separately | §10.7: 0 of 7 (0 of 33 rows). The sensitivity row is stated. |
| ☑ | At least one second reviewer checks a subset of labels | A2 labelled **all 7** EN-pass/BN-fail cases blind to A1 (`second_review.csv`). **All three annotators (A1, A2, ADJ) are Claude models, not humans.** An owner review of a subset is recommended, starting with email:41, analytics:20, analytics:98 and md:120. |
| ☑ | Disagreements are adjudicated | `adjudication.csv` holds **54 decision rows**, each with a written reason: 17 A1–A2 disagreement rows (3 of them also task-review items), 12 task-review rows, 1 task-review + convention row, 12 convention rows and 12 fix-round-1 rows. 13 of the 33 rows in `labels_final.csv` are marked `ADJ`. |
| ☑ | Case studies match the quantitative patterns | §13.8 covers the largest confound (General, md:84) and the 2 entity-or-slot-grounding cases (email:41 Genuine, md:120 Translation). |
| ☑ | Strong claims are made only after confound filtering | No strong claim is made. The Bangla-linked share is stated after filtering (2 of 6) and called a candidate pattern (§12). |

---

## Inter-annotator agreement (A1 vs blind A2, EN-pass/BN-fail, n = 7)

The figures are from [`agreement.json`](agreement.json). **κ was measured BEFORE adjudication** (stage "A1 (labels.csv) vs A2 (second_review.csv), before adjudication").

| field | agree / n | raw agreement | expected agreement | Cohen's κ |
|---|---|---|---|---|
| first failure point | 4/7 | 57.1% | 0.2245 | 0.447 |
| failure type | 5/7 | 71.4% | 0.4490 | 0.481 |
| confound | 5/7 | 71.4% | 0.3061 | 0.588 |
| decision-tree first-fail step | 5/7 | 71.4% | 0.2245 | 0.632 |

- **κ is not the reliability of the final labels.** The adjudication conventions changed labels that both annotators had agreed on. For gemma this was 2 fields: the failure type of analytics:20 and of multi_domain:120, under C1. For gpt-oss:20b it was 11 fields.
- **First failure point and failure type are not independent.** Under C1 the type follows from the first failure point, so their κ values partly measure the same judgment.
- **agreement.json reports only the tree's first-fail step.** Whole-tree exact agreement (all seven steps identical) was **2 of 7** for gemma, and 11 of 15 for gpt-oss.
- With n = 7, κ is very imprecise; read it as descriptive only.
- **The disagreements:**
  - analytics:119: first failure point and confound;
  - analytics:20: first failure point;
  - analytics:98: first failure point, type and confound;
  - email:41: type.

  Each one was adjudicated against the raw traces.

---

## Limitations

- **Sample and runs.** n = 90 (15 per domain), with one run per side and no repeats, so run-to-run noise is unmeasured. Some labels have counter-examples within the same run (analytics:20, md:120).
- **Model annotators.** A1, A2 and ADJ are all Claude models, and no human has checked the labels. An owner review of a subset is recommended (§14).
- **Translations not yet reviewed.** The owner's native-speaker review of the Bangla templates is still pending. Every Translation and Genuine judgment is provisional, especially "গত সপ্তাহে" (email:41) and "আগামী শুক্রবার" (md:120). If the wording changes, C6 must be re-run.
- **Different days and resumed runs.** gemma C0 ran on 2026-10-04 and C6 on 2026-10-05, so provider drift is possible. Neither gemma run was resumed (`num_resumed_from_prior_run` = 0 in both run metas), so no gemma outcome comes from a re-run. For gpt-oss:20b, C0 ran on 2026-10-05 and C6 on 2026-10-05/06 and 2026-10-07, and both runs were resumed. Its comparison report's S2 sensitivity counts every recovered re-run as a failure (2 per side): both rates fall by 2.2 pp, and the gap (5.6 pp), McNemar p (0.4244) and discordant counts (15/10) are unchanged ([`failure_analysis.md`](../../comparisons/pilot_ollama-gpt-oss-20b_c6_vs_c0/failure_analysis.md), S2).
- **Lost traces (gpt-oss:20b).** Errored gpt-oss rows have 0 recorded steps. Their labels rest on the error string, `function_calls` and the per-task call count in the log (C12). This affects the model-wise comparison in §10.9, not gemma's own labels.
- **Specific weak labels:**
  - **gemma analytics:98 BN, Benchmark/task ambiguity.** General model weakness is equally defensible. English "passed" only by giving up after 24 looping read calls.
  - **gpt-oss analytics:42 BN, Genuine.** Reading "থেকে" ("since") as a single day needs a native-speaker check. The same model read it as an open range in analytics:0 and :32.
  - **gpt-oss project_management:28 EN.** This label is inferred from a lost trace (C10).
  - **gpt-oss multi_domain:200 BN and multi_domain:76 BN.** Both stay Translation under the no-counterfactual clause of C5(3) (`labels_final.csv`). md:200's English run crashed at its first call, and md:76's English run never observed carlos's tasks, so neither has an English counterfactual. md:200 is the weaker of the two, because the same model read "next Friday" as 12-01 in English on md:120 and md:169.
- **md:120 has a different confound for each model.** gemma md:120 BN is Translation, while gpt-oss md:120 BN is Benchmark. The task is the same; under C5(3), the paired English run decides:
  - gemma's English run read "next Friday" as 12-08 and passed, so the Bangla reading caused the failure.
  - gpt-oss's English run made the identical 12-01 call, so the defect is in the task, not in the translation.
- **Group mechanisms by first failure point, not by type.** The "due today counted as overdue" mechanism appears in pm:64 EN and BN and pm:28 EN here, and in pm:60 BN and pm:28 EN for gpt-oss. All share the first failure point Task constraint preservation, but under the C1 sub-rule the type splits between Understanding failure and Wrong tool/action. Aggregate this mechanism by first failure point.
- **Scorer strictness.** WorkBench compares full tables. md:6 EN fails only because a self-corrected event shifted the auto-incremented ID. It is kept as a real failure (C6 does not count real side effects as Benchmark), but the paper should state this strictness.
- **Small-n statistics.** The domain figures are descriptive only. The odds-ratio CI is wide because only 15 pairs are discordant.
- **The C1 tie-break ties the first failure point to the final answer's wording.** A filter missing from the first search is Tool-argument construction when the agent's own words restate the constraint, and Task constraint preservation when there are no words or the words also drop it. The rule applies to both models. For example, in gpt-oss:20b the same omission is Task constraint preservation in crm:42 EN (status='Lead' missing; empty final answer) but Tool-argument construction in crm:77 BN and md:182 EN (status missing) and crm:60 EN (owner missing), whose answers restate the constraint. The counts of these two first failure points therefore partly reflect what the answer text says.

---

## Appendix

### A.1 Rules and files

- **Annotation rules:** [`../annotation_rules.md`](../annotation_rules.md) holds the controlled vocabularies, the `labels.csv` contract, the statistics definitions, adjudication conventions C1–C12 and the review amendments.
- **Trace notes:** [`trace_notes.md`](trace_notes.md) holds all §4 fields for the 7 EN-pass/BN-fail cases, the "interesting?" notes for the 8 EN-fail/BN-pass cases, and brief both-fail notes.
- **Labels and statistics:**
  - [`labels.csv`](labels.csv): first labels (A1);
  - [`second_review.csv`](second_review.csv): blind second labels (A2);
  - [`adjudication.csv`](adjudication.csv): decisions;
  - [`labels_final.csv`](labels_final.csv): final labels;
  - [`agreement.json`](agreement.json): agreement;
  - [`stats.json`](stats.json): statistics;
  - [`task_table.csv`](task_table.csv): task table.
- **Raw traces** are git-ignored and exist only in the working copy:
  - `WorkBench/data/results/c0/pilot_en/ollama-gemma4-31b/ollama-gemma4-31b_all_2026-10-04_11-42-18_traces.json`;
  - `WorkBench/data/results/c6/pilot_bn/ollama-gemma4-31b/ollama-gemma4-31b_all_2026-10-05_16-12-03_traces.json`.

  In `task_table.csv`, the index after `#` gives each task's position in these files.
- **Pipeline:** [`../../../instructions/failure_analysis_pipeline.md`](../../../instructions/failure_analysis_pipeline.md). **Plan:** [`../../../docs/design/plans/2026-10-07-failure-pipeline.md`](../../../docs/design/plans/2026-10-07-failure-pipeline.md).

### A.2 Longer trace excerpts for the case studies

Each step is listed as tool, arguments and observation. Observations are truncated, and email bodies and event lists are cut.

**multi_domain:84** (trace index #81 on both sides)

English (pass):
```
[0] company_directory.find_email_address {"name": "olga"} -> ["olga.petrova@atlas.com"]
[1] project_management.search_tasks {"assigned_to_email": "olga.petrova@atlas.com"} -> [{"task_id": "00000258", "task_name": "Design logo for blog", ..., "list_name": "Backlog", "due_date": "2023-11-27", ...}, ...]
[2] calendar.search_events {"time_max": "2023-12-01 18:00:00", "time_min": "2023-12-01 09:00:00"} -> [{"event_id": "00000165", ..., "event_start": "2023-12-01 09:00:00", "duration": "60"}, ...]
[3] calendar.create_event {"duration": "30", "event_name": "Catch up on overdue tasks", "event_start": "2023-12-01 13:00:00", "participant_email": "olga.petrova@atlas.com"} -> 00000300
[4] Final Answer "... for tomorrow, December 1st, at 1:00 PM, which was the earliest time you were free."
```
Bangla (fail):
```
[0] company_directory.find_email_address {"name": "olga"} -> ["olga.petrova@atlas.com"]
[1] project_management.search_tasks {"assigned_to_email": "olga.petrova@atlas.com"} -> (same as English)
[2] calendar.search_events {"time_max": "2023-12-01 18:00:00", "time_min": "2023-12-01 09:00:00"} -> (same as English)
[3] calendar.create_event {"duration": "30", "event_name": "Catch up on overdue tasks", "event_start": "2023-12-01 15:00:00", "participant_email": "olga.petrova@atlas.com"} -> 00000300
[4] Final Answer "... আপনার আগামীকালকের (১ ডিসেম্বর) ক্যালেন্ডার চেক করে দেখলাম যে আপনি দুপুর ৩টার পর ফ্রি আছেন। তাই আমি আগামীকাল দুপুর ৩:০০ টায় ... মিটিং বুক করেছি।"
```

**email:41** (trace index #7 on both sides)

English (pass):
```
[0] company_directory.find_email_address {"name": "Anaya"} -> ["anaya.patel@atlas.com"]
[1] company_directory.find_email_address {"name": "Nadia"} -> ["nadia.moreau@atlas.com"]
[2] email.search_emails {"date_max": "2023-11-26", "date_min": "2023-11-19", "query": "Update on Board of Directors Conclave"} -> [{"email_id": "00000120", ..., "sent_datetime": "2023-11-21 13:26:29", ...}, ...]
[3] email.forward_email {"email_id": "00000120", "recipient": "nadia.moreau@atlas.com"} -> Email forwarded successfully.
[4] email.forward_email {"email_id": "00000346", "recipient": "nadia.moreau@atlas.com"} -> Email forwarded successfully.
[5] Final Answer "I've forwarded the two emails from Anaya ... from last week to Nadia."
```
Bangla (fail):
```
[0] company_directory.find_email_address {"name": "anaya"} -> ["anaya.patel@atlas.com"]
[1] company_directory.find_email_address {"name": "nadia"} -> ["nadia.moreau@atlas.com"]
[2] email.search_emails {"date_max": "2023-11-29", "date_min": "2023-11-23", "query": "Update on Board of Directors Conclave"} -> []
[3] email.search_emails {"date_max": "2023-11-29", "date_min": "2023-11-23", "query": "Board of Directors Conclave"} -> []
[4] email.search_emails {"date_max": "2023-11-29", "date_min": "2023-11-23", "query": "anaya.patel@atlas.com"} -> [{"email_id": "00000166", ..., "subject": "Task Update on Fix alignment issue in settings page", ...}, ...]
[5] email.search_emails {"query": "Update on Board of Directors Conclave"} -> [{"email_id": "00000120", ..., "sent_datetime": "2023-11-21 13:26:29", ...}, ...]
[6] Final Answer "দুঃখিত, গত সপ্তাহে (২৩ নভেম্বর থেকে ২৯ নভেম্বর) Anaya-র পাঠানো ... কোনো ইমেইল খুঁজে পাওয়া যায়নি। তবে এই শিরোনামে কিছু পুরনো ইমেইল পাওয়া গেছে, যা গত সপ্তাহের নয়। ..."
```

**multi_domain:120** (trace index #84 on both sides)

English (pass):
```
[0] analytics.get_average_session_duration {"time_min": "2023-11-27", "time_max": "2023-11-30"} -> {"2023-11-27": 22.33, "2023-11-28": 20.32, "2023-11-29": 20.5}
[1] project_management.search_tasks {"board": "Front end", "list_name": "Completed"} -> [{"task_id": "00000103", ..., "assigned_to_email": "nia.johnson@atlas.com", ...}, ...]
[2] project_management.create_task {"assigned_to_email": "nia.johnson@atlas.com", "board": "Front end", "due_date": "2023-12-08", "list_name": "Backlog", "task_name": "Improve average session duration"} -> 00000300
[3] Final Answer "... with a deadline of next Friday, December 8, 2023."
```
Bangla (fail):
```
[0] analytics.get_average_session_duration {"time_max": "2023-11-30", "time_min": "2023-11-27"} -> (same as English)
[1] project_management.search_tasks {"board": "Front end", "list_name": "Completed"} -> (same as English)
[2] project_management.create_task {"assigned_to_email": "nia.johnson@atlas.com", "board": "Front end", "due_date": "2023-12-01", "list_name": "Backlog", "task_name": "Improve average session duration"} -> 00000300
[3] Final Answer "... তাই তার জন্য আগামী শুক্রবার (১ ডিসেম্বর, ২০২৩) ডেডলাইনের সাথে 'Improve average session duration' নামে একটি Backlog টাস্ক তৈরি করা হয়েছে।"
```
