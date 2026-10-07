# Failure-analysis report: gpt-oss:20b, English (C0) vs Bangla (C6), WorkBench 90-task pilot

This report applies the owner's pipeline ([`instructions/failure_analysis_pipeline.md`](../../../instructions/failure_analysis_pipeline.md), sections §1–§14) to one model. The companion report for gemma4:31b is [`../pilot_ollama-gemma4-31b_c6_vs_c0/report.md`](../pilot_ollama-gemma4-31b_c6_vs_c0/report.md).

- **English** = condition C0: everything in English. Run `ollama-gpt-oss-20b_all_2026-10-05_21-50-29`.
- **Bangla** = condition C6: Bangla task and system prompt, English tool descriptions, replies forced to Bangla. Run `ollama-gpt-oss-20b_all_2026-10-05_23-57-38`. There is no C7.
- **Dataset:** WorkBench only. 90 tasks (15 per domain), one run per side, no repeats. Pass = WorkBench `correct`: the final database state equals the ground truth.
- **Where the numbers come from:**
  - [`stats.json`](stats.json): statistics and §10 counts, written by `scripts/failure_pipeline.py stats --all` and `counts --all` on `labels_final.csv`.
  - [`labels_final.csv`](labels_final.csv): the only source for label counts.
  - [`agreement.json`](agreement.json): inter-annotator agreement.
  - The comparison-set distributions (EN-fail/BN-fail and the English side) are counted directly from `labels_final.csv`.
  - Where [`trace_notes.md`](trace_notes.md) still has an older summary line, this report uses `labels_final.csv` and the "Adjudicated" lines, never the superseded summary.
- **Gap direction:** gap = EN rate − BN rate, so a positive gap means Bangla is worse. MELR = (EN − BN) / EN.
- **Model annotators:** all labels come from Claude models, not humans: first annotator A1, blind second reviewer A2 and adjudicator ADJ. The owner's native-speaker review of the Bangla translations has not happened yet.
- **Lost traces:** 13 label rows (11 tasks) belong to runs that ended on an exception. The harness kept 0 steps for these. Their labels rest on the CSV error string, `function_calls` and the per-task call count in the log (convention C12).

**Headline.**
- English 73.3%? No: English 53/90 = 58.9%, Bangla 48/90 = 53.3%.
- Gap +5.6 pp (95% CI −5.6 to +16.7); MELR +9.4% (−9.8% to +25.9%).
- McNemar exact p = 0.4244 (Holm 0.8487); paired OR b/c = 15/10 = 1.5 (0.630–3.734).
- Bangla is 5.6 points lower, but the interval includes 0 and also allows a moderate drop.
- Of the 15 EN-pass/BN-fail cases, 14 are general model weaknesses that also occur in English. 11 of the 15 begin at tool-argument construction, 6 of those with invented `<name>@example.com` addresses. 1 case is Genuine Bangla-related (fragile). 0 are translation or tool/environment.

---

## §1–§2. Basic outcome

### Overall (n = 90 pairs)

| measure | value | 95% CI |
|---|---|---|
| English success | 53/90 = 58.9% | 48.6–68.5% (Wilson) |
| Bangla success | 48/90 = 53.3% | 43.1–63.3% (Wilson) |
| Absolute gap EN − BN | +5.6 pp (5/90) | −5.6 to +16.7 pp (paired bootstrap, 10,000 resamples, seed 20261004) |
| MELR (EN − BN) / EN | +9.4% | −9.8% to +25.9% (same resamples; resamples with EN = 0 are excluded, **0 of 10,000** here) |

### Paired outcomes (n = 90)

| | Bangla pass | Bangla fail | total |
|---|---|---|---|
| **English pass** | EN-pass/BN-pass **38** | **EN-pass/BN-fail 15** ← most important group | 53 |
| **English fail** | EN-fail/BN-pass **10** | EN-fail/BN-fail **27** | 37 |
| total | 48 | 42 | 90 |

**EN-pass/BN-fail is the cleanest group for Bangla-specific degradation (15 of 90 pairs, 16.7%).** In these pairs the same task succeeded in English and failed in Bangla. 10 pairs go the other way (EN-fail/BN-pass), and 27 pairs fail in both languages.

### Per domain (n = 15 each; descriptive only)

`stats.json` gives Wilson CIs for the per-domain rates. By design (see the plan's "Statistics" section), it gives no interval or p-value for the per-domain gap or MELR, so those are point values only.

| domain | n | English | Bangla | gap EN − BN | MELR | EN-pass/BN-pass | **EN-pass/BN-fail** | EN-fail/BN-pass | EN-fail/BN-fail |
|---|---|---|---|---|---|---|---|---|---|
| email | 15 | 11/15 = 73.3% (48.0–89.1) | 10/15 = 66.7% (41.7–84.8) | +6.7 pp | +9.1% | 7 | **4** | 3 | 1 |
| calendar | 15 | 10/15 = 66.7% (41.7–84.8) | 11/15 = 73.3% (48.0–89.1) | −6.7 pp | −10.0% | 9 | **1** | 2 | 3 |
| analytics | 15 | 11/15 = 73.3% (48.0–89.1) | 7/15 = 46.7% (24.8–69.9) | +26.7 pp | +36.4% | 7 | **4** | 0 | 4 |
| project_management | 15 | 8/15 = 53.3% (30.1–75.2) | 9/15 = 60.0% (35.7–80.2) | −6.7 pp | −12.5% | 6 | **2** | 3 | 4 |
| customer_relationship_manager | 15 | 9/15 = 60.0% (35.7–80.2) | 7/15 = 46.7% (24.8–69.9) | +13.3 pp | +22.2% | 5 | **4** | 2 | 4 |
| multi_domain | 15 | 4/15 = 26.7% (10.9–52.0) | 4/15 = 26.7% (10.9–52.0) | +0.0 pp | 0.0% | 4 | **0** | 0 | 11 |
| **overall** | 90 | 53/90 = 58.9% | 48/90 = 53.3% | +5.6 pp | +9.4% | 38 | **15** | 10 | 27 |

Analytics has the largest one-way split: 4 EN-pass/BN-fail against 0 EN-fail/BN-pass. Its 4 cases have three different first failure points and two different confounds (§10.10). Multi_domain fails in both languages for 11 of 15 pairs. At n = 15 these figures are descriptive only.

---

## §3. Case selection: what was analysed

| pair class | pairs | what was done | label rows |
|---|---|---|---|
| EN-pass/BN-fail | 15 | **Every case.** Full §4 trace note (EN and BN traces read side by side), full labels, the §8 decision tree and §9 evidence. A2 gave a blind second review of all 15, followed by adjudication. | 15 (BN side) |
| EN-fail/BN-fail | 27 | **The full set, not a sample.** For **both** failures: first failure point, failure type, confound and one evidence line. | 54 (EN + BN) |
| EN-fail/BN-pass | 10 | The same short labels for the English failure, so that tool/environment confounds can be filtered on both sides. Each also gets a one-line "interesting?" note. | 10 (EN side) |
| EN-pass/BN-pass | 38 | **Not analysed.** Pipeline §3 asks for it only "if needed", and no listed output needs a stable-success contrast. | 0 |
| **total** | 90 | | **79** |

The EN-fail/BN-pass short labels, all 10, are from `labels_final.csv`. The notes are in [`trace_notes.md`](trace_notes.md).

| task | first failure point (EN) | confound | note |
|---|---|---|---|
| email:21 | Tool-argument construction | General | EN sent to the invented "jinsoo@example.com"; BN looked the address up |
| email:36 | Tool-argument construction | Benchmark/task ambiguity | the EN template never closes the reply quote, so EN copied "Can you send the reply for me?" into the body |
| email:75 | Tool-argument construction | General | EN forwarded to the invented "akira@example.com" and "yuki@example.com" |
| calendar:38 | Task constraint preservation (Wrong tool/action) | General | EN also deleted a past event |
| calendar:105 | Tool-argument construction | General | EN invited the invented "yuki@example.com" |
| crm:60 | Tool-argument construction | General | EN's search left out Sofia's owner filter and deleted 5 customers of other owners |
| crm:74 | Tool selection | General | EN called the nonexistent `crm_search_customers`; the final state was otherwise correct |
| project_management:28 | Task constraint preservation (Wrong tool/action) | General | lost trace; error `update_task() … 'new?'`. Ground truth is no change, so any update is a write that should not exist (C10) |
| project_management:42 | Tool-argument construction | General | EN searched with "yuki@example.com" and found nothing |
| project_management:64 | Tool execution | **Tool/environment** | lost trace; "Request timed out." after 9 harness retries |

4 of these 10 English failures (email:21, email:75, calendar:105, pm:42) are invented addresses: the mirror image of the dominant Bangla-only mechanism (§12, Finding 1).

---

## §4–§9. Method summary

The full rules are in [`../annotation_rules.md`](../annotation_rules.md) and the per-case notes in [`trace_notes.md`](trace_notes.md). Where a note has an "Adjudicated" line, that line and `labels_final.csv` are final. Several older summary lines in this folder's `trace_notes.md` were superseded in fix round 1: the md:120 and md:169 confounds, and the crm:60, pm:57 and md:182 types. They are not used here.

- **§4 Trace note.** Each EN-pass/BN-fail case has a note with every §4 field:
  - task goal;
  - what happened in English and in Bangla;
  - first divergence;
  - final failed or missing action;
  - failure type, root cause and confound decision;
  - evidence (tool-call quotes).
- **§5 First failure point.** Exactly one of the 11 labels. It is the earliest upstream point after which the correct final state became unreachable, not the last visible error. Convention C2 judges "unreachable" on the trajectory the agent actually followed.
- **§6 Failure type.** Exactly one of the 9 types. Under convention C1 the type names the failure *at* the first failure point. The two fields are therefore one judgment, and their distributions are **not independent**.
  - C8 adds that a value invented instead of looked up is Tool-argument construction / Wrong tool argument. Examples: an `@example.com` address, a calendar slot, a count.
  - Entity or slot grounding is reserved for reading errors.
- **§7 Confound.** Exactly one of the 7.
  - **"Bangla user-simulator error" is structurally N/A.** WorkBench tasks are single-turn and there is no user simulator, so this confound is never used and decision-tree Step 2 is always `na`.
  - **Translation** needs a reading that the Bangla introduced and that this failure used, and the paired English run must not have taken the same reading (C5, C5(3)).
  - **General** needs the same mechanism class in a C0 failure, cited by task ID. English rows cite a C6 analogue instead (C7).
  - **Tool/environment** means the provider or tool failed despite a reasonable action. Examples: HTTP 5xx after the harness retries, or a read timeout. A malformed keyword is a model error.
- **§8 Decision tree.** Seven one-word outcomes per EN-pass/BN-fail case:
  - S1: translation valid;
  - S2: user simulator, always N/A;
  - S3: understood;
  - S4: right tool/action;
  - S5: correct arguments;
  - S6: tool/environment executed;
  - S7: completion verified.

  The first `fail` sets the root cause, and later steps are descriptive (C3). S7 is never `na`. For lost traces, a step is `na` only when the surviving evidence says nothing about it (C12).
- **§9 Evidence.** Every label row carries:
  - the English and Bangla outcomes;
  - the tool call, message or error string that proves the failure;
  - the first failure point;
  - for EN-pass/BN-fail, why the case is or is not just a general model failure.
- **Conventions.**
  - C1–C7 come from the gemma4:31b adjudication.
  - C8–C12 come from this model's adjudication: fabricated lookup values, transliterated protected tokens, wrong-tool-plus-bad-keyword calls, "English admits a reading that the Bangla favours", and lost traces.
  - The fix-round-1 review amendments are C5(3), the C11 note, the C6 clarification, the C1 tie-break and the C2 amendment.
  - All of them are applied to every row of both models.

---

## §10. Counts for EN-pass/BN-fail (n = 15 cases of 90 pairs; BN-side labels)

### Case list

| task | domain | first failure point | failure type | confound | tree (first fail) |
|---|---|---|---|---|---|
| email:51 | email | Tool-argument construction | Wrong tool argument | General | S5 |
| email:66 | email | Tool-argument construction | Wrong tool argument | General | S5 |
| email:69 | email | Tool-argument construction | Wrong tool argument | General | S5 |
| email:74 | email | Tool-argument construction | Wrong tool argument | General | S5 |
| calendar:20 | calendar | Tool-argument construction | Wrong tool argument | General | S5 |
| customer_relationship_manager:22 | CRM | Tool-argument construction | Wrong tool argument | General | S5 |
| customer_relationship_manager:38 | CRM | Tool selection | Wrong tool/action | General | S4 |
| customer_relationship_manager:53 | CRM | Tool-argument construction | Wrong tool argument | General (lost trace) | S5 |
| customer_relationship_manager:77 | CRM | Tool-argument construction | Wrong tool argument | General | S5 |
| analytics:42 | analytics | Entity or slot grounding | Understanding failure | **Genuine Bangla-related** | S3 |
| analytics:43 | analytics | Tool-argument construction | Wrong tool argument | General (lost trace) | S5 |
| analytics:54 | analytics | Task constraint preservation | Wrong tool/action | General | S4 |
| analytics:105 | analytics | Premature termination | Premature abandonment | General | S7 |
| project_management:2 | project_management | Tool-argument construction | Wrong tool argument | General | S5 |
| project_management:72 | project_management | Tool-argument construction | Wrong tool argument | General | S5 |

The evidence column shows what the 11 Tool-argument-construction cases have in common. This grouping comes from the `evidence` field and is not a controlled label:
- invented `<name>@example.com` addresses: 6 (email:51, :66, :69, :74, pm:2, pm:72);
- malformed keyword arguments that crashed the run: 2 (crm:53 `'new?'`, analytics:43 `'field'`; both lost traces);
- unrequested empty-string optional fields: 1 (crm:22);
- a zero-width search window that was never widened: 1 (calendar:20);
- a missing status filter in the first search: 1 (crm:77).

### 10.1 Failure type distribution (denominator 15)

| failure type | n | % of 15 |
|---|---|---|
| Wrong tool argument | 11 | 73.3% |
| Wrong tool/action | 2 | 13.3% |
| Understanding failure | 1 | 6.7% |
| Premature abandonment | 1 | 6.7% |
| Planning failure | 0 | 0.0% |
| Execution/environment failure | 0 | 0.0% |
| Verification failure | 0 | 0.0% |
| Dialogue-state failure | 0 | 0.0% |
| Unclear | 0 | 0.0% |

### 10.2 First failure point distribution (denominator 15)

| first failure point | n | % of 15 |
|---|---|---|
| Tool-argument construction | 11 | 73.3% |
| Entity or slot grounding | 1 | 6.7% |
| Task constraint preservation | 1 | 6.7% |
| Tool selection | 1 | 6.7% |
| Premature termination | 1 | 6.7% |
| Instruction understanding, Planning, Tool execution, Result verification, Final response only, Unclear | 0 each | 0.0% |

### 10.3 Confound distribution (denominator 15)

| confound | n | % of 15 | tasks |
|---|---|---|---|
| General model weakness present in both English and Bangla | 14 | 93.3% | all except analytics:42 |
| Genuine Bangla-related agent failure | 1 | 6.7% | analytics:42 |
| Translation/localization error | 0 | 0.0% | (crm:77 was Translation for both A1 and A2; adjudicated General, see §10.6) |
| Bangla user-simulator error | 0 | 0.0% | structurally N/A |
| Tool/environment failure | 0 | 0.0% | |
| Benchmark/task ambiguity | 0 | 0.0% | |
| Unclear | 0 | 0.0% | |

### 10.4 Genuine Bangla-related cases after filtering

The filter removes the user-simulator, translation and tool/environment confounds. It removes **0 of 15**, so **15 remain**. Of these, **1 is Genuine Bangla-related: analytics:42 (6.7% of 15)**. The other 14 are General.

### 10.5 User-simulator-caused cases

**0 of 15.** This is structurally N/A, because WorkBench has no user simulator.

### 10.6 Translation-caused cases

**0 of 15.**
- **crm:77 BN.** The Bangla template renders the CRM status "proposal" in Bangla script ("প্রপোজালে"), which breaks translation policy §4. A1 and A2 both labelled the case Translation, and the adjudicator overrode both to General (C9, C5(1)). The reasons:
  - the word keeps its English meaning;
  - the English "a proposal" admits the same omission;
  - the agent's own final answer restates the constraint;
  - the same model mapped the identical word correctly in C6 crm:74.

  The deviation stays flagged for the native-speaker review.
- **The two Translation labels in this model fall outside EN-pass/BN-fail.** Both are BN rows of EN-fail/BN-fail pairs, and both carry the C5(3) no-counterfactual note:
  - **multi_domain:76 BN.** "Overdue" was rendered as "ডেডলাইন পেরিয়ে গেছে" ("the deadline has passed"). BN then sent "Overdue tasks" citing completed tasks. The paired English run never observed carlos's tasks: every search used the invented carlos@example.com and returned `[]`. So there is no English counterfactual for the "overdue" reading.
  - **multi_domain:200 BN.** "আগামী শুক্রবার" was read as 2023-12-01; the ground truth is 2023-12-08. The paired English run crashed at its first call (`total_visits_count(value_to_plot=…)`), so it never reached the phrase. This is the weaker of the two, because the same model read "next Friday" as 12-01 in English on md:120 and md:169.
- **multi_domain:120 and multi_domain:169 are Benchmark/task ambiguity on both sides, not Translation (C5(3), C6(a)).** The paired English run made the identical `create_task(… due_date="2023-12-01")` call for "next Friday". md:169 EN even glossed it "next Friday (2023-12-01)". On Thursday 2023-11-30 the English task itself admits that reading, so the Bangla wording did not cause the failure. S1 = ok on both sides.

### 10.7 Tool/environment-caused cases

**0 of 15.** Tool/environment labels exist on **5 pairs**, none of them EN-pass/BN-fail. All 5 are lost traces.

| pair | class | side(s) labelled | evidence (from `labels_final.csv`) |
|---|---|---|---|
| customer_relationship_manager:46 | EN-fail/BN-fail | BN | HTTP 500 after 9 harness retries; 7 model calls before it. The first attempt had failed on a model error (`'newvalue'`), so this is the weakest such label. |
| multi_domain:84 | EN-fail/BN-fail | BN | HTTP 500 after 9 harness retries; 6 model calls before it |
| project_management:35 | EN-fail/BN-fail | EN and BN | HTTP 500 after 9 harness retries on both sides (EN after 3 model calls, BN after 5) |
| multi_domain:130 | EN-fail/BN-fail | EN | HTTP 500 after read timeouts and 9 harness retries; 3 model calls before it |
| project_management:64 | EN-fail/BN-pass | EN | "Request timed out." after 9 harness retries; 2 model calls before it |

### 10.8 Dataset-wise distribution

WorkBench is the only dataset: 90 pairs and 15 cases. The distributions are the same as 10.1–10.3.

### 10.9 Model-wise distribution (EN-pass/BN-fail; this model next to gemma4:31b)

| | gpt-oss:20b (n = 15 of 90) | gemma4:31b (n = 7 of 90) |
|---|---|---|
| **Failure type** | | |
| Understanding failure | 1 (6.7%) | 3 (42.9%) |
| Planning failure | 0 | 1 (14.3%) |
| Wrong tool/action | 2 (13.3%) | 1 (14.3%) |
| Wrong tool argument | 11 (73.3%) | 2 (28.6%) |
| Premature abandonment | 1 (6.7%) | 0 |
| others | 0 | 0 |
| **First failure point** | | |
| Instruction understanding | 0 | 1 (14.3%) |
| Entity or slot grounding | 1 (6.7%) | 2 (28.6%) |
| Task constraint preservation | 1 (6.7%) | 1 (14.3%) |
| Planning | 0 | 1 (14.3%) |
| Tool selection | 1 (6.7%) | 0 |
| Tool-argument construction | 11 (73.3%) | 2 (28.6%) |
| Premature termination | 1 (6.7%) | 0 |
| others | 0 | 0 |
| **Confound** | | |
| Genuine Bangla-related | 1 (6.7%) | 2 (28.6%) |
| Translation/localization | 0 | 1 (14.3%) |
| Benchmark/task ambiguity | 0 | 1 (14.3%) |
| General model weakness | 14 (93.3%) | 3 (42.9%) |
| User simulator / Tool/environment / Unclear | 0 / 0 / 0 | 0 / 0 / 0 |

gpt-oss has twice as many EN-pass/BN-fail cases as gemma (15 vs 7), and they are concentrated at tool-argument construction. gemma's few cases are spread over reading and reasoning points, and more of them are Bangla-linked.

### 10.10 Domain-wise distribution (EN-pass/BN-fail cases per domain)

| domain | cases / 15 pairs | first failure point | failure type | confound |
|---|---|---|---|---|
| email | 4 | Tool-argument construction 4 | Wrong tool argument 4 | General 4 |
| calendar | 1 | Tool-argument construction 1 | Wrong tool argument 1 | General 1 |
| analytics | 4 | Entity or slot grounding 1, Task constraint preservation 1, Tool-argument construction 1, Premature termination 1 | Understanding 1, Wrong tool/action 1, Wrong tool argument 1, Premature abandonment 1 | Genuine 1, General 3 |
| project_management | 2 | Tool-argument construction 2 | Wrong tool argument 2 | General 2 |
| customer_relationship_manager | 4 | Tool selection 1, Tool-argument construction 3 | Wrong tool/action 1, Wrong tool argument 3 | General 4 |
| multi_domain | 0 | — | — | — |

### 10.11 Comparison sets: EN-fail/BN-fail and the English side

The same three distributions follow for the other failures, so that a general weakness can be told apart from a Bangla-only one. All counts are from `labels_final.csv`.

| failure type | EN-pass/BN-fail, BN (n = 15) | EN-fail/BN-fail, BN (n = 27) | EN-fail/BN-fail, EN (n = 27) | EN-fail/BN-pass, EN (n = 10) | all English failures (n = 37) |
|---|---|---|---|---|---|
| Understanding failure | 1 | 10 | 8 | 0 | 8 |
| Wrong tool/action | 2 | 2 | 2 | 3 | 5 |
| Wrong tool argument | 11 | 10 | 13 | 6 | 19 |
| Execution/environment failure | 0 | 3 | 2 | 1 | 3 |
| Verification failure | 0 | 1 | 0 | 0 | 0 |
| Premature abandonment | 1 | 1 | 2 | 0 | 2 |
| Planning, Dialogue-state, Unclear | 0 | 0 | 0 | 0 | 0 |

| first failure point | EN-pass/BN-fail, BN (15) | EN-fail/BN-fail, BN (27) | EN-fail/BN-fail, EN (27) | EN-fail/BN-pass, EN (10) | all English (37) |
|---|---|---|---|---|---|
| Instruction understanding | 0 | 1 | 2 | 0 | 2 |
| Entity or slot grounding | 1 | 5 | 3 | 0 | 3 |
| Task constraint preservation | 1 | 6 | 5 | 2 | 7 |
| Tool selection | 1 | 0 | 0 | 1 | 1 |
| Tool-argument construction | 11 | 10 | 13 | 6 | 19 |
| Tool execution | 0 | 3 | 2 | 1 | 3 |
| Result verification | 0 | 1 | 0 | 0 | 0 |
| Premature termination | 1 | 1 | 2 | 0 | 2 |
| Planning, Final response only, Unclear | 0 | 0 | 0 | 0 | 0 |

| confound | EN-pass/BN-fail, BN (15) | EN-fail/BN-fail, BN (27) | EN-fail/BN-fail, EN (27) | EN-fail/BN-pass, EN (10) | all English (37) |
|---|---|---|---|---|---|
| Genuine Bangla-related | 1 | 1 (email:41) | 0 | 0 | 0 |
| Translation/localization | 0 | 2 (md:76, md:200) | 0 | 0 | 0 |
| Tool/environment | 0 | 3 (crm:46, md:84, pm:35) | 2 (md:130, pm:35) | 1 (pm:64) | 3 |
| Benchmark/task ambiguity | 0 | 3 (calendar:79, md:120, md:169) | 3 (calendar:79, md:120, md:169) | 1 (email:36) | 4 |
| General model weakness | 14 | 18 | 21 | 8 | 29 |
| Unclear | 0 | 0 | 1 (analytics:69) | 0 | 1 |

What these tables show:
- **General dominates every set:** 14/15 EN-pass/BN-fail (93.3%), 18/27 both-fail BN (66.7%) and 29/37 English failures (78.4%).
- **Tool-argument construction is the most common first failure point everywhere.** Its share is higher among EN-pass/BN-fail (11/15, 73.3%) than among all English failures (19/37, 51.4%) or both-fail BN failures (10/27, 37.0%). That difference is descriptive. It cannot be separated from run-to-run noise with one run per side.
- **Bangla-linked labels outside EN-pass/BN-fail:**
  - Genuine email:41 BN: "গত সপ্তাহে" read as the rolling 11-23..29 window, the same mechanism as gemma email:41.
  - The two Translation rows.
  - All three are both-fail, so they do not change b or c.
- **Group the due-today/today-boundary mechanism by first failure point, not by type:**
  - project_management:60 BN: a task due today was moved as overdue.
  - project_management:28 EN: inferred from a lost trace.
  - calendar:63 EN and BN: a meeting later today was counted as already held.

  All four share the first failure point Task constraint preservation. Their types split under the C1 sub-rule: Wrong tool/action for pm:60 and pm:28, Understanding failure for calendar:63. None of them is EN-pass/BN-fail.

---

## §11. Statistical analysis

| statistic | value |
|---|---|
| McNemar exact p (b = 15, c = 10) | **0.4244** |
| Holm-adjusted p (family: the 2 model comparisons; gemma raw p = 1.0) | **0.8487** |
| Risk difference (= gap EN − BN) | +5.6 pp, 95% CI −5.6 to +16.7 (paired bootstrap) |
| Paired odds ratio b/c | 15/10 = **1.5**, exact conditional 95% CI **0.630–3.734** (Clopper–Pearson on b/(b+c)) |
| MELR | +9.4%, 95% CI −9.8% to +25.9% (0 resamples with EN = 0 excluded) |
| English rate | 58.9% (48.6–68.5) |
| Bangla rate | 53.3% (43.1–63.3) |

**Effect size and uncertainty, not only p:**
- The point estimate is a 5.6-point Bangla deficit, a 9.4% relative loss.
- Discordant pairs favour English 15 to 10.
- The interval runs from Bangla 5.6 points *better* to 16.7 points *worse*.
- The odds-ratio interval (0.63–3.73) includes no effect and a near-fourfold excess of Bangla-only failures.
- At n = 90, a gap of 5–10 points can be neither detected nor ruled out.

### Sensitivity analysis

Each row is a filtered paired analysis. The p-values are raw McNemar p; Holm applies only to the "all" row.

| analysis | n pairs | English | Bangla | gap EN − BN (95% CI) | MELR (95% CI) | paired counts (pp/pf/fp/ff) | McNemar p | OR b/c (95% CI) |
|---|---|---|---|---|---|---|---|---|
| all pairs | 90 | 53/90 = 58.9% (48.6–68.5) | 48/90 = 53.3% (43.1–63.3) | +5.6 pp (−5.6, +16.7) | +9.4% (−9.8, +25.9) | 38/15/10/27 | 0.4244 | 1.500 (0.630–3.734) |
| translation removed (md:76, md:200) | 88 | 53/88 = 60.2% (49.8–69.8) | 48/88 = 54.5% (44.2–64.5) | +5.7 pp (−4.5, +17.0) | +9.4% (−9.4, +26.2) | 38/15/10/25 | 0.4244 | 1.500 (0.630–3.734) |
| user simulator removed | 90 | 53/90 = 58.9% | 48/90 = 53.3% | +5.6 pp (−5.6, +16.7) | +9.4% (−9.8, +25.9) | 38/15/10/27 | 0.4244 | 1.500 (0.630–3.734) |
| tool/environment removed (crm:46, md:84, md:130, pm:35, pm:64) | 85 | 53/85 = 62.4% (51.7–71.9) | 47/85 = 55.3% (44.7–65.4) | +7.1 pp (−3.5, +17.7) | +11.3% (−6.8, +27.4) | 38/15/9/23 | 0.3075 | 1.667 (0.683–4.319) |

- **"User simulator removed" is identical to "all" by construction.** WorkBench has no user simulator, so 0 pairs are removed.
- **"Translation removed" drops two EN-fail/BN-fail pairs,** so b and c are unchanged. Only the rates and the gap shift slightly.
- **"Tool/environment removed" drops 5 pairs: 4 EN-fail/BN-fail and 1 EN-fail/BN-pass (pm:64).** c falls from 10 to 9 while b stays 15, so the gap widens to +7.1 pp and p falls to 0.3075. The CI still includes 0, and no conclusion changes.
- In every row, 0 bootstrap resamples had EN = 0.

---

## §12. Findings

Each finding follows Observation → Evidence → Root cause → Boundary. "Filtering" means removing the translation, user-simulator and tool/environment confounds (§10.4); for this model's EN-pass/BN-fail set it removes nothing. With 15 cases and one run per side, every finding describes this pilot only.

### Finding 1: Bangla-only failures are dominated by fabricated or malformed tool arguments, which the model also produces in English

> We find that **fabricated or malformed tool arguments** account for **11 of 15 (73.3%)** EN-pass/BN-fail cases. Invented `<name>@example.com` addresses alone account for **6 of 15 (40.0%)**. Manual trajectory analysis shows that these failures usually begin at **tool-argument construction**, at the first lookup or search call. After filtering translation, user-simulator and tool/environment confounds, **15 of 15** cases remain. All 11 in this pattern are General with a cited C0 analogue. This suggests that these Bangla-only failures are the model's general argument unreliability landing on the Bangla run, not a Bangla effect.

- **Evidence.**
  - email:51: EN called `find_email_address(name="Santiago")` and forwarded to `santiago.martinez@atlas.com`. BN skipped the lookup and forwarded to `recipient="santiago@example.com"`. The C0 analogues are email:21 and email:75.
  - project_management:2: BN searched with `assigned_to_email="yuki@example.com"`. It looked up "yuki" and got `yuki.tanaka@atlas.com`, but kept searching with the invented address and concluded there were no tasks. The C0 analogues are pm:30, :42 and :60.
  - crm:53 and analytics:43: crashes on invented keywords (`'new?'`, `'field'`). The C0 analogues are pm:28 and md:200.
  - **The mirror image:** 4 of the 10 EN-fail/BN-pass cases are English invented addresses where Bangla did the lookup (email:21, email:75, calendar:105, pm:42).
- **Root cause.** Lookups are skipped, or their results ignored, and values are invented instead (C8). Keyword names are corrupted. Recipient and assignee names are Latin-script and identical in both tasks, and the translations are faithful.
- **Boundary.**
  - The share of tool-argument construction is higher among Bangla-only failures (11/15, 73.3%) than among all English failures (19/37, 51.4%).
  - The crm:53 evidence records malformed-keyword errors on 8 C6 tasks against 3 C0 tasks, including first attempts.
  - Each single case has a C0 analogue, so none is labelled Bangla-related. But an aggregate excess like this cannot be tested with labels. It needs repeated runs.

### Finding 2: one fragile Bangla-linked case, a range phrase read as a single day

> We find that **misreading a Bangla date-range phrase** accounts for **1 of 15 (6.7%)** EN-pass/BN-fail cases (analytics:42, "2023-11-10 থেকে", "since 2023-11-10"). Manual trajectory analysis shows that this failure begins at **entity or slot grounding**. After filtering translation, user-simulator and tool/environment confounds, **1 of 15 (6.7%)** remains Genuine Bangla-related. This suggests at most a weak, isolated Bangla effect for this model, pending the native-speaker review.

- **Evidence.**
  - EN called `create_plot(time_min="2023-11-10", time_max="2023-11-30", plot_type="bar")` for both metrics.
  - BN called `create_plot(time_min="2023-11-10", time_max="2023-11-10")` twice and described the charts as "২০২৩‑১১‑১০ তারিখের" ("for the date 2023-11-10").
  - No C0 failure collapses "since <date>" to one day.
- **Root cause.** The bare Bangla phrase "<date> থেকে" was read as a single day. The translation is a faithful rendering of "since", but unlike other BN templates it leaves out "এখন পর্যন্ত" ("until now").
- **Boundary.** The same model read the same bare "<date> থেকে" as an open range in C6 analytics:0 and analytics:32, both of which passed. So this looks like a one-off misreading. Run-to-run variance cannot be excluded, and the phrase needs a native-speaker check.

### Finding 3: the remaining Bangla-only failures are gate, termination and tool-name errors with English analogues

> We find that **gate, termination and tool-name errors** account for **3 of 15 (20.0%)** EN-pass/BN-fail cases. Each begins at a different first failure point: analytics:54 at task constraint preservation, analytics:105 at premature termination, crm:38 at tool selection. After filtering, **15 of 15** remain, and all 3 are General. This suggests that they reflect general control-flow weaknesses rather than Bangla input.

- **Evidence.**
  - **analytics:54.** BN wrote "কখনও ৩‑এর নিচে ছিল না" ("it was never below 3") and still called `create_plot` "as requested". The C0 analogue is analytics:98 EN.
  - **analytics:105.** BN made 2 read calls and then returned an empty final answer. The C0 analogues are crm:57 and crm:42.
  - **crm:38.** BN's first call was the nonexistent `crm_search_customers`. The final state was otherwise correct. C0 crm:74 EN called the same invented name and failed the same way.
- **Root cause.** A condition was evaluated correctly but ignored at the write; the agent stopped mid-task; a tool name was hallucinated.
- **Boundary.** crm:38, together with crm:22 (empty-string optional fields), fails on WorkBench's strict scoring with an otherwise near-correct state. Both are model errors under C2 and C6, but the paper should state the scorer property.

### Finding 4: the overall gap is not detectable, and removing tool/environment pairs does not change that

- **Observation.** Bangla is 5.6 points lower: 48/90 vs 53/90.
- **Evidence.**
  - Gap +5.6 pp (−5.6, +16.7); MELR +9.4% (−9.8, +25.9).
  - OR 1.5 (0.630–3.734); McNemar p = 0.4244, Holm 0.8487.
  - Removing the 5 tool/environment pairs: +7.1 pp (−3.5, +17.7), p = 0.3075, OR 1.667 (0.683–4.319).
- **Root cause.** The discordant pairs favour English 15 to 10. By the confound labels, 14 of the 15 Bangla-only failures are general weaknesses (Finding 1).
- **Boundary.** n = 90, one run per side, different run days, and resumed runs. The CI allows anything from a small Bangla advantage to a moderate drop.

---

## §13. Paper outputs

### 13.1 Overall English vs Bangla success table

| model | n | English (C0) | Bangla (C6) | gap EN − BN (95% CI) | McNemar p | Holm p |
|---|---|---|---|---|---|---|
| gpt-oss:20b | 90 | 53/90 = 58.9% (48.6–68.5) | 48/90 = 53.3% (43.1–63.3) | +5.6 pp (−5.6, +16.7) | 0.4244 | 0.8487 |
| gemma4:31b | 90 | 73/90 = 81.1% (71.8–87.9) | 74/90 = 82.2% (73.1–88.8) | −1.1 pp (−10.0, +7.8) | 1.0000 | 1.0000 |

### 13.2 MELR by dataset and model (WorkBench only)

| dataset | model | MELR (95% CI, paired bootstrap) | resamples with EN = 0 excluded |
|---|---|---|---|
| WorkBench | gpt-oss:20b | +9.4% (−9.8%, +25.9%) | 0 of 10,000 |
| WorkBench | gemma4:31b | −1.4% (−12.5%, +8.6%) | 0 of 10,000 |

### 13.3 Paired outcome table

| model | EN-pass/BN-pass | **EN-pass/BN-fail** | EN-fail/BN-pass | EN-fail/BN-fail | n |
|---|---|---|---|---|---|
| gpt-oss:20b | 38 | **15** | 10 | 27 | 90 |
| gemma4:31b | 66 | **7** | 8 | 9 | 90 |

### 13.4 Failure type distribution for EN-pass/BN-fail

See §10.1 for this model and §10.9 for both models.

### 13.5 First failure point distribution

See §10.2 for this model and §10.9 for both models.

### 13.6 Confound filtering table

| confound | EN-pass/BN-fail cases (of 15) | removed by the §10.4 filter? | pairs removed in the §11 sensitivity row (all pair classes) |
|---|---|---|---|
| Genuine Bangla-related | 1 (analytics:42) | no (this is the signal) | — |
| Bangla user-simulator error | 0 | yes (N/A) | 0 |
| Translation/localization error | 0 | yes | 2 (md:76, md:200; both EN-fail/BN-fail) |
| Tool/environment failure | 0 | yes | 5 (crm:46, md:84, md:130, pm:35, pm:64) |
| Benchmark/task ambiguity | 0 | no (not part of the plan's filter) | — |
| General model weakness | 14 | no | — |
| Unclear | 0 | no | — |

### 13.7 Before/after confound-filtered results

| | before (all) | after translation removed | after user simulator removed | after tool/environment removed |
|---|---|---|---|---|
| n pairs | 90 | 88 | 90 | 85 |
| EN-pass/BN-fail | 15 | 15 | 15 | 15 |
| EN-fail/BN-pass | 10 | 10 | 10 | 9 |
| gap EN − BN | +5.6 pp (−5.6, +16.7) | +5.7 pp (−4.5, +17.0) | +5.6 pp | +7.1 pp (−3.5, +17.7) |
| McNemar p | 0.4244 | 0.4244 | 0.4244 | 0.3075 |
| OR b/c | 1.500 (0.630–3.734) | 1.500 (0.630–3.734) | 1.500 | 1.667 (0.683–4.319) |
| Genuine among EN-pass/BN-fail | 1 of 15 | 1 of 15 | 1 of 15 | 1 of 15 |

### 13.8 Case studies

These three cases match the quantitative pattern:
- two cases from the dominant mechanism, invented addresses (6 of 15 cases, inside the 11 tool-argument-construction cases);
- the only Genuine Bangla-related case.

The excerpts are short; longer step lists are in the appendix.

**Case 1: email:51 (General, tool-argument construction).** The task: *santiago needs the latest email about 'Update on Client Appreciation Gala'. Can you forward it?*
- Both runs found email 00000206 with the same `search_emails` call.
- English then called `find_email_address(name="Santiago")` and forwarded to `santiago.martinez@atlas.com`.
- Bangla went straight to `forward_email(email_id="00000206", recipient="santiago@example.com")`, then answered "ইমেইলটি সফলভাবে সান্টিয়াগোকে ফরোয়ার্ড করা হয়েছে" ("the email was forwarded to Santiago successfully").
- The name "santiago" is Latin-script and identical in both tasks. C0 email:21 and email:75 fail by the same invented-address mechanism, and 4 EN-fail/BN-pass cases show it in English only. Labelled Tool-argument construction / Wrong tool argument / General.

**Case 2: project_management:2 (General, tool-argument construction).** The task: *Move all of yuki's tasks that are in progress to in review.*
- English looked up `yuki.tanaka@atlas.com`, searched In Progress and called `update_task(00000091, list_name, "In Review")`.
- Bangla first searched with `assigned_to_email="yuki@example.com"` and got `[]`. It then looked up "yuki" and got `["yuki.tanaka@atlas.com"]`, but ran three more searches with `yuki@example.com`. It concluded that yuki had no In Progress tasks, so `update_task` was never called.
- The invented value persisted despite a correct lookup (C8). C0 pm:30, :42 and :60 search with invented `<name>@example.com` assignees.

**Case 3: analytics:42 (Genuine, entity or slot grounding).** The task: *I need bar charts of total visits and engaged users since 2023-11-10.*
- English plotted `time_min="2023-11-10", time_max="2023-11-30"`.
- Bangla's task reads "2023-11-10 থেকে মোট ভিজিট আর এনগেজড ইউজারের bar চার্ট লাগবে" ("I need bar charts of total visits and engaged users from 2023-11-10"). It plotted `time_min="2023-11-10", time_max="2023-11-10"` for both metrics and described them as "২০২৩‑১১‑১০ তারিখের" ("for the date 2023-11-10").
- The translation is faithful, and no C0 failure collapses "since" to one day, so the label is Genuine.
- The label is fragile: analytics:0 and analytics:32 BN read the same bare "থেকে" as an open range.

### 13.9 Appendix

See the Appendix at the end of this report: annotation rules, file links, and longer trace excerpts for the three case studies.

---

## §14. Quality-control checklist

| | item | evidence |
|---|---|---|
| ☑ | Every task ID is aligned between English and Bangla | `task_table.csv` has 90 rows and 90 distinct `task_uid`s. The `table` command asserts the alignment. It also asserts that EN/BN pass/fail and `pair_class` match the existing comparison folder for all 90 rows ([`../annotation_rules.md`](../annotation_rules.md), "Inputs and conventions"). One EN run ID and one BN run ID cover all rows. |
| ☑ | Every metric has a denominator | Rates are given as k/n, shares as n of 15 (or of the stated set), and each sensitivity row states its number of pairs. |
| ☑ | EN-pass/BN-fail is separated from both-fail | §10 counts only the 15 EN-pass/BN-fail BN rows (`stats.json` `counts.population`). Both-fail (27 pairs, 54 rows) is reported separately in §10.11. |
| ☑ | Translation errors are not counted as genuine Bangla agent failures | §10.6: 0 EN-pass/BN-fail Translation. The 2 Translation rows (md:76 BN, md:200 BN) are kept out of Genuine and removed in the sensitivity row. |
| ☑ | User-simulator errors are counted separately | §10.5: 0, structurally N/A. The sensitivity row is identical to "all", and the report says so. |
| ☑ | Tool/environment failures are counted separately | §10.7: 0 of 15 EN-pass/BN-fail. 5 pairs carry the label in other classes and are listed. The sensitivity row (n = 85) is reported. |
| ☑ | At least one second reviewer checks a subset of labels | A2 labelled **all 15** EN-pass/BN-fail cases blind to A1 (`second_review.csv`). **All three annotators (A1, A2, ADJ) are Claude models, not humans.** An owner review of a subset is recommended, starting with crm:77, analytics:42, analytics:54, calendar:20, md:76, md:200 and md:120/169. |
| ☑ | Disagreements are adjudicated | `adjudication.csv` has **147 decision rows**, each with a written reason: 10 A1–A2 disagreement rows (1 of them also a task-review item), 5 task-review rows, 4 task-review + convention rows, 6 A2-ambiguity rows, 92 convention rows and 30 fix-round-1 rows. In `labels_final.csv`, 54 of 79 rows are marked `ADJ`. |
| ☑ | Case studies match the quantitative patterns | §13.8 covers the dominant mechanism (invented addresses: email:51, pm:2) and the only Genuine case (analytics:42). |
| ☑ | Strong claims are made only after confound filtering | No strong claim is made. The Bangla-linked share is stated after filtering (1 of 15), and the general-weakness reading is qualified by the single run (§12). |

---

## Inter-annotator agreement (A1 vs blind A2, EN-pass/BN-fail, n = 15)

From [`agreement.json`](agreement.json). **κ was measured BEFORE adjudication**, at the stage "A1 (labels.csv) vs A2 (second_review.csv), before adjudication".

| field | agree / n | raw agreement | expected agreement | Cohen's κ |
|---|---|---|---|---|
| first failure point | 14/15 | 93.3% | 0.2667 | 0.909 |
| failure type | 13/15 | 86.7% | 0.4400 | 0.762 |
| confound | 14/15 | 93.3% | 0.7067 | 0.773 |
| decision-tree first-fail step | 14/15 | 93.3% | 0.4000 | 0.889 |

- **κ is not the reliability of the final labels.** The adjudication conventions changed **11 fields that both annotators had agreed on**:
  - the first failure point of email:51, :66, :69, :74, pm:2 and pm:72 (C8: invented address → Tool-argument construction);
  - the first failure point, type and tree of calendar:20 (C2);
  - the first failure point and the confound of crm:77 (Translation → General, overriding both annotators).

  For gemma4:31b the equivalent number was 2 fields.
- **First failure point and failure type are not independent.** Under C1 the type follows from the first failure point.
- **agreement.json reports only the tree's first-fail step.** Whole-tree exact agreement (all seven steps identical) was **11 of 15** (2 of 7 for gemma).
- The confound κ is held down by prevalence: one category dominates (expected agreement 0.7067).
- With n = 15, all κ values are imprecise and should be read as descriptive.
- The disagreements were:
  - analytics:42: first failure point;
  - analytics:54: type, confound and first-fail step;
  - crm:77: type.

  Each was adjudicated against the raw traces.

---

## Limitations

- **Sample and runs.** n = 90 (15 per domain), one run per side and no repeats, so run-to-run noise is unmeasured. The 4 invented-address mirror cases in EN-fail/BN-pass show how much this model varies between runs.
- **Model annotators.** A1, A2 and ADJ are all Claude models. No human has checked the labels. An owner review of a subset is recommended (§14).
- **Native-speaker review still pending.** The owner has not yet reviewed the Bangla templates, so every Translation and Genuine judgment is provisional. This applies especially to "থেকে" (analytics:42), "প্রপোজালে" (crm:77), "ডেডলাইন পেরিয়ে গেছে" (md:76), "আগামী শুক্রবার" (md:120, :169, :200) and "গত সপ্তাহে" (email:41 BN). If the wording changes, C6 must be re-run.
- **Lost traces.** 13 label rows across 11 tasks ended on an exception and kept 0 steps (C12): crm:46 BN, crm:53 BN, crm:57 BN, analytics:43 BN, pm:28 EN, pm:30 BN, pm:35 EN and BN, pm:64 EN, md:84 BN, md:130 EN and BN, and md:200 EN. Their labels rest on the error string, `function_calls` and the log call count. Two of them are EN-pass/BN-fail cases (crm:53, analytics:43); crm:53 keeps S3 = `na`.
- **Different days and resumed runs.** C0 ran on 2026-10-05. C6 ran on 2026-10-05/06 and was resumed on 2026-10-07. Both runs were resumed, and errored rows were re-run on resume, so some pass/fail outcomes are from a recorded re-run (for example analytics:105 EN). By contrast, gemma C0 ran on 2026-10-04 and C6 on 2026-10-05.
- **Specific weak labels:**
  - gemma analytics:98 BN, Benchmark/task ambiguity: General is equally defensible.
  - **gpt-oss analytics:42 BN, Genuine:** reading "থেকে" as a single day needs a native-speaker check. The same model read it as an open range in analytics:0 and :32.
  - **gpt-oss project_management:28 EN:** inferred from a lost trace. Because the ground truth is no change, any `update_task` call is treated as a gate error (C10).
  - **gpt-oss multi_domain:200 BN and multi_domain:76 BN:** both stay Translation under the C5(3) no-counterfactual clause (`labels_final.csv`).
    - md:200: the English run crashed at its first call.
    - md:76: the English run never observed carlos's tasks.

    md:200 is the weaker of the two, because this model read "next Friday" as 12-01 in English on md:120 and md:169.
  - **gpt-oss crm:46 BN, Tool/environment:** the recorded run ended in an HTTP 500, but the first attempt had failed on a model error (`'newvalue'`).
- **md:120 differs by model.** gpt-oss md:120 BN is Benchmark; gemma md:120 BN is Translation. Under C5(3), the paired English run decides:
  - gpt-oss's English run made the identical 12-01 call, so the defect is in the English task, not the translation.
  - gemma's English run read 12-08 and passed, so for gemma the Bangla reading caused the failure.

  The task is the same; the English runs differed.
- **Group mechanisms by first failure point, not type.** The due-today/today-boundary mechanism appears in pm:60 BN, pm:28 EN and calendar:63 EN/BN here, and in pm:64 EN/BN and pm:28 EN for gemma. All of these share Task constraint preservation, but under the C1 sub-rule their type splits between Wrong tool/action and Understanding failure.
- **Scorer strictness.** WorkBench fails a run on any unrecognised tool call (crm:38 BN, crm:74 EN) and compares full tables, so empty strings differ from nulls (crm:22 BN). Under the C2 amendment, a validation-error string returned by a tool does not fail the run: analytics:42 EN and analytics:105 EN passed despite "Value to plot must be one of …". These cases are model errors under C2 and C6, but the paper should state the scoring properties.
- **Aggregate signal not captured per case.** Malformed-keyword errors occur on more C6 tasks than C0 tasks (8 vs 3, including first attempts; crm:53 evidence). Every single case has a C0 analogue and is labelled General, so this excess appears only in aggregate and needs repeated runs.
- **Small-n statistics.** Domain figures are descriptive. The odds-ratio CI is wide because only 25 pairs are discordant.

---

## Appendix

### A.1 Rules and files

- Annotation rules, controlled vocabularies, the `labels.csv` contract, statistics definitions, adjudication conventions C1–C12 and the review amendments: [`../annotation_rules.md`](../annotation_rules.md).
- Trace notes: [`trace_notes.md`](trace_notes.md). It has all §4 fields for the 15 EN-pass/BN-fail cases, "interesting?" notes for the 10 EN-fail/BN-pass cases, and adjudication notes for the EN-fail rows. Use the "Adjudicated" lines; the older summary lines are superseded.
- Label and result files:
  - first labels: [`labels.csv`](labels.csv) (A1);
  - blind second labels: [`second_review.csv`](second_review.csv) (A2);
  - decisions: [`adjudication.csv`](adjudication.csv);
  - final labels: [`labels_final.csv`](labels_final.csv);
  - agreement: [`agreement.json`](agreement.json);
  - statistics: [`stats.json`](stats.json);
  - task table: [`task_table.csv`](task_table.csv).
- Raw traces are git-ignored and exist only in the working copy:
  - `WorkBench/data/results/c0/pilot_en/ollama-gpt-oss-20b/ollama-gpt-oss-20b_all_2026-10-05_21-50-29_traces.json`
  - `WorkBench/data/results/c6/pilot_bn/ollama-gpt-oss-20b/ollama-gpt-oss-20b_all_2026-10-05_23-57-38_traces.json`

  The index after `#` in `task_table.csv` gives each task's position.
- Pipeline: [`../../../instructions/failure_analysis_pipeline.md`](../../../instructions/failure_analysis_pipeline.md). Plan: [`../../../docs/design/plans/2026-10-07-failure-pipeline.md`](../../../docs/design/plans/2026-10-07-failure-pipeline.md).

### A.2 Longer trace excerpts for the case studies

Each step is listed as tool, arguments and observation. Observations are truncated, and email bodies are cut.

**email:51** (trace index #9 on both sides)

English (pass):
```
[0] email.search_emails {"query": "Update on Client Appreciation Gala", "date_min": "2023-01-01", "date_max": "2023-12-31"} -> [{"email_id": "00000206", "sender/recipient": "olga.petrova@atlas.com", "subject": "Update on Client Appreciation Gala", "sent_datetime": "2023-11-30 14:46:03", ...}]
[1] company_directory.find_email_address {"name": "Santiago"} -> ["santiago.martinez@atlas.com"]
[2] email.forward_email {"email_id": "00000206", "recipient": "santiago.martinez@atlas.com"} -> Email forwarded successfully.
[3] Final Answer "The latest email about “Update on Client Appreciation Gala” has been forwarded to Santiago at santiago.martinez@atlas.com."
```
Bangla (fail):
```
[0] email.search_emails {"query": "Update on Client Appreciation Gala", "date_min": "2023-01-01", "date_max": "2023-12-31"} -> (same as English)
[1] email.forward_email {"email_id": "00000206", "recipient": "santiago@example.com"} -> Email forwarded successfully.
[2] Final Answer "ইমেইলটি সফলভাবে সান্টিয়াগোকে ফরোয়ার্ড করা হয়েছে।"
```

**project_management:2** (trace index #60 on both sides)

English (pass):
```
[0] company_directory.find_email_address {"name": "Yuki"} -> ["yuki.tanaka@atlas.com"]
[1] project_management.search_tasks {"assigned_to_email": "yuki.tanaka@atlas.com", "board": "", "due_date": "", "list_name": "In Progress", "task_name": ""} -> [{"task_id": "00000091", "task_name": "Add authentication for third-party login", "list_name": "In Progress", ...}]
[2] project_management.update_task {"task_id": "00000091", "field": "list_name", "new_value": "In Review"} -> Task updated successfully.
[3] Final Answer "All of Yuki’s tasks that were in the “In Progress” list have been moved to “In Review.”"
```
Bangla (fail):
```
[0] project_management.search_tasks {"assigned_to_email": "yuki@example.com", "board": "", "due_date": "", "list_name": "", "task_name": ""} -> []
[1] company_directory.find_email_address {"name": "yuki"} -> ["yuki.tanaka@atlas.com"]
[2] project_management.search_tasks {"assigned_to_email": "yuki@example.com", ..., "list_name": "In Progress", ...} -> []
[3] project_management.search_tasks {"assigned_to_email": "yuki@example.com", "board": "Back end", ..., "list_name": "In Progress", ...} -> []
[4] project_management.search_tasks {"assigned_to_email": "yuki@example.com", "board": "Front end", ..., "list_name": "In Progress", ...} -> []
[5] Final Answer "দুঃখিত, বর্তমানে **yuki**-এর জন্য “In Progress” তালিকায় কোনো টাস্ক নেই, তাই এগুলোকে “In Review” এ সরানোর প্রয়োজন নেই।"
```

**analytics:42** (trace index #50 on both sides)

English (pass):
```
[0] analytics.create_plot {"plot_type": "bar", "time_min": "2023-11-10", "time_max": "2023-11-30", "value_to_plot": "total_visits"} -> plots/2023-11-10_2023-11-30_total_visits_bar.png
[1] analytics.create_plot {"plot_type": "bar", "time_max": "2023-11-30", "time_min": "2023-11-10", "value_to_plot": "engaged_users"} -> Value to plot must be one of 'total_visits', 'session_duration_seconds', 'user_engaged', ...
[2] analytics.create_plot {"plot_type": "bar", "time_max": "2023-11-30", "time_min": "2023-11-10", "value_to_plot": "user_engaged"} -> plots/2023-11-10_2023-11-30_user_engaged_bar.png
[3] Final Answer "... Both charts cover the period from 2023‑11‑10 to 2023‑11‑30."
```
Bangla (fail):
```
[0] analytics.create_plot {"time_min": "2023-11-10", "time_max": "2023-11-10", "value_to_plot": "total_visits", "plot_type": "bar"} -> plots/2023-11-10_2023-11-10_total_visits_bar.png
[1] analytics.create_plot {"plot_type": "bar", "time_max": "2023-11-10", "time_min": "2023-11-10", "value_to_plot": "user_engaged"} -> plots/2023-11-10_2023-11-10_user_engaged_bar.png
[2] Final Answer "নিম্নে ২০২৩‑১১‑১০ তারিখের মোট ভিজিট ও এনগেজড ইউজারের বার চার্টের লিঙ্ক দেওয়া হলো: ..."
```

The English step [1] shows the C2 amendment at work: the validation-error string did not fail the run, and English passed.