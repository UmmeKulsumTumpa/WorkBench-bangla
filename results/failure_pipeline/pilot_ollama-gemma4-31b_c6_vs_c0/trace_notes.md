# Trace notes: gemma4:31b, C6 (Bangla) vs C0 (English), WorkBench 90-task pilot

Annotator: **A1**. Rules: `results/failure_pipeline/annotation_rules.md`. Inputs: `task_table.csv` and the local, git-ignored traces
(`WorkBench/data/results/c0/pilot_en/ollama-gemma4-31b/*_traces.json` and `.../c6/pilot_bn/...`). The EN and BN traces were read side by side for every case.
"Today" = Thu 2023-11-30 00:00. Translation judgments are **provisional** until the owner's native-speaker review.

Pair counts (verified from `task_table.csv`): both_correct 66, **ref_only (EN-pass/BN-fail) 7**, **both_wrong 9**, **treat_only (EN-fail/BN-pass) 8**.

Facts about the harness used below:
- calendar, CRM and email searches return at most 5 rows (`DEFAULT_SEARCH_RESULT_LIMIT = 5`, `WorkBench/src/tools/_utils.py`).
- `is_correct` returns False for any errored row (`WorkBench/src/evals/evaluation.py`).
- States are compared as full tables, so an auto-incremented event ID counts as part of the state.
- Tomorrow's (2023-12-01) calendar has events at 09:00-10:00, 10:00-12:00, 12:00-13:00, 13:30-14:00 and 14:30-15:00. The earliest free 30-minute slot is therefore **13:00**.

Decision-tree step key (pipeline §8): S1 translated task valid · S2 user simulator (N/A, no user simulator) · S3 agent understood the Bangla user · S4 right tool/action · S5 correct arguments · S6 tool/environment executed correctly · S7 completion verified. `fail` means that step's problem applies.

---

## EN-pass / BN-fail (full §4 notes)

### 1. workbench:email:41 (email)
- **Task goal:** forward every email that anaya sent last week with subject 'Update on Board of Directors Conclave' to nadia. Ground truth forwards 00000346 and 00000120, sent 11-20 and 11-21. The ground-truth logic uses the calendar week 2023-11-20..26.
- **English:** looked up both addresses, then `search_emails(query=subject, date_min=2023-11-19, date_max=2023-11-26)` returned both emails. It forwarded both. Pass.
- **Bangla:** "গত সপ্তাহে anaya '…' নিয়ে যে ইমেইলগুলো পাঠিয়েছিল, সবগুলো nadia-কে ফরোয়ার্ড করে দিতে পারবে". It looked up both addresses correctly, then searched `date_min=2023-11-23, date_max=2023-11-29` and got [] twice (steps 2 and 3, subject queries); a third search in that window by anaya's address (step 4) returned only other emails (00000166, 00000456). An undated search (step 5) returned both target emails, but the agent rejected them as outside last week. Its final answer: "গত সপ্তাহে (২৩ নভেম্বর থেকে ২৯ নভেম্বর) … কোনো ইমেইল খুঁজে পাওয়া যায়নি … আপনি কি অন্য কোনো তারিখ … চেক করতে চান?"
- **First divergence:** step 2. "গত সপ্তাহে" was grounded as the rolling 7 days 11-23..11-29, where English used the calendar week.
- **Final failed/missing action:** the two `forward_email` calls were never made.
- **Failure type:** Wrong tool argument (first failure point: Entity or slot grounding).
- **Root cause:** a Bangla relative-date phrase was mis-grounded to the wrong date window. The wrong window then justified abandoning the task even after the correct emails had been found.
- **Confound decision:** Genuine Bangla-related agent failure (provisional).
  - Translation (T05.v2) is faithful: subject and names are byte-identical, and "গত সপ্তাহে" is the standard rendering of "last week".
  - No C0 failure mis-grounds a "last week / last N weeks" window.
  - The owner has listed "গত সপ্তাহে" for the native-speaker review. If the review finds that it leans to "the past 7 days", this label becomes Translation/localization error.
- **Decision tree:** S1 ok · S2 N/A (no user simulator) · S3 fail · S4 ok · S5 fail · S6 ok · S7 fail.
- **Evidence (§9):** In email:41, English passed by calling `forward_email` for 00000120 and 00000346 after searching 11-19..11-26. In Bangla, the agent grounded "গত সপ্তাহে" as 11-23..11-29, found nothing, and refused the two emails its own undated search returned, so `forward_email` was never called. This is labelled an entity/slot-grounding failure of a Bangla date phrase: the translation is faithful and no C0 analogue exists.
- **Adjudicated (ADJ, 2026-10-07):** the failure type is now **Understanding failure**, because the type follows the first failure point (convention C1). The first failure point (Entity or slot grounding), the confound (Genuine, provisional; decided together with md:120 under C5) and the tree are unchanged. Factual fix: the Bangla bullet originally said the windowed searches returned [] "three times"; the trace shows twice (steps 2 and 3), corrected above.

### 2. workbench:customer_relationship_manager:77 (CRM)
- **Task goal:** move software-proposal customers who have not responded in 6 weeks to Lost. Ground truth: **no change**, because no candidate's last contact is before the 2023-10-19 cutoff.
- **English:** `search_customers(Software, Proposal)` returned 5 customers. It set 00000147 (last contact 2023-10-29) to Lost, then set it back to Proposal twice, and answered "no customers have been inactive for 6 weeks or more (cutoff date: 2023-10-19)". The net state is unchanged. Pass.
- **Bangla:** the same search. At step 1 it set 00000147 to Lost through a **nonexistent tool**, `customer_relationship_manager_update_task(task_id=00000147, …)`. The DB was unchanged, but the call stays in `function_calls`, `_parse_and_dispatch` rejects it, and `is_correct` requires every call to execute. **That alone makes the run fail.** It then called `update_customer(00000147, status, Lost)`, with the claim "৬ সপ্তাহ বা তার বেশি সময় ধরে কোনো যোগাযোগ হয়নি … (শেষ যোগাযোগ ছিল ২০২৩-১০-২৯)". There was no revert.
- **First divergence:** step 1. The wrong decision is the same as English's step 1, but Bangla expressed it through an invalid tool name. Bangla therefore could not recover by reverting, as English did; it also never tried to.
- **Final failed action:** the rejected `customer_relationship_manager_update_task` call, plus the kept `update_customer(00000147 → Lost)`.
- **Failure type:** Wrong tool/action (first failure point: Task constraint preservation).
- **Root cause:** the 6-week threshold was misapplied (32 days treated as ≥ 42). This decision is upstream of both bad calls. A secondary, independently fatal error is the invalid tool name. It is the only unrecognised call in either run (0/90 C0), and it shows no visible Bangla link, because tool descriptions are English in C6.
- **Confound decision:** General model weakness present in both English and Bangla.
  - The same threshold error appears in C0 **customer_relationship_manager:74**. There, EN moved 00000195 (10-25) and 00000058 (10-21) to Lost under a self-stated "since October 16th" cutoff.
  - The same error also appears in this task's own EN step 1.
  - The Bangla text is faithful, and the agent restated the constraint correctly.
- **Decision tree:** S1 ok · S2 N/A (no user simulator) · S3 ok · S4 fail · S5 na · S6 ok · S7 fail.
- **Evidence (§9):** In customer_relationship_manager:77, English passed because it reverted its mistaken `update_customer(00000147 → Lost)`. In Bangla, the agent made the same decision, first through the nonexistent `customer_relationship_manager_update_task` (scored as a failed call) and then through `update_customer`, which it kept, claiming a 2023-10-29 contact was over 6 weeks old. This is a constraint-preservation (date-threshold) error. It is a general model weakness, because C0 customer_relationship_manager:74 fails by the same mechanism.

### 3. workbench:analytics:20 (analytics)
- **Task goal:** plot the distribution of engaged users and total visits for Nov 5–21. Ground truth: two `create_plot(..., plot_type="histogram")` calls.
- **English:** two histogram `create_plot` calls with the correct dates. Pass.
- **Bangla:** "প্লিজ 5 নভেম্বর থেকে 21 নভেম্বর সময়ের মধ্যে এনগেজড ইউজার ও মোট ভিজিটের ডিস্ট্রিবিউশন আমাকে চার্টে দেখিয়ে দাও". It made two `create_plot(..., plot_type="line")` calls with the correct dates and metrics, and described them as "ডিস্ট্রিবিউশন চার্টগুলো".
- **First divergence:** step 0, the choice of plot_type.
- **Final failed action:** `create_plot` with `line` instead of `histogram`, twice.
- **Failure type:** Wrong tool argument (first failure point: Instruction understanding).
- **Root cause:** the Bangla request for a "distribution" chart over a date range was not mapped to a histogram.
- **Confound decision:** Genuine Bangla-related agent failure, provisional and weak.
  - T31.v3 is faithful under the policy: plot→চার্ট, and "distribution" is transliterated.
  - No C0 failure has a wrong plot_type.
  - Caveat: analytics:15 BN uses the same Bangla phrasing ("ডিস্ট্রিবিউশন চার্টে দেখাও") and correctly got histogram. With one run per side, run-to-run variance cannot be excluded.
- **Decision tree:** S1 ok · S2 N/A (no user simulator) · S3 fail · S4 ok · S5 fail · S6 ok · S7 ok.
- **Evidence (§9):** In analytics:20, English passed by calling `create_plot` with `plot_type="histogram"` for both metrics. In Bangla, the agent called `create_plot` with `plot_type="line"` for the same request, phrased "ডিস্ট্রিবিউশন … চার্টে দেখিয়ে দাও". This is labelled an instruction-understanding failure tied to the Bangla wording. It is not a general weakness (no C0 analogue), but the evidence is weak (analytics:15 BN succeeded).
- **Adjudicated (ADJ, 2026-10-07):** the failure type is now **Understanding failure**, because the type follows the first failure point (C1). A2's Tool-argument construction was rejected: 'line' is what a loose reading of "distribution over Nov 5–21" gives, and the agent calls its line charts distribution charts. That is a different meaning, not a mis-mapping of an understood value (C4). The first failure point (Instruction understanding), the confound (Genuine, weak) and the tree are unchanged.

### 4. workbench:analytics:98 (analytics)
- **Task goal:** "percent growth of average session duration since Wednesday; if it grew by more than total visits, plot both lines since then".
  - The ground-truth logic is `relative_growth_two_plots_logic`: growth = (last value − value on 2023-11-29) / value on 2023-11-29.
  - The data ends on 11-29, so both growths are 0. 0 > 0 is false, so ground truth is **no plot**.
- **English:** 24 read calls cycling over 11-29/11-30, then "I was unable to calculate the percent growth because there is no data available for today". No plot was made. This passed by abstention, not by computing the answer.
- **Bangla:** queried 11-29 (20.5 s, 10 visits) and then **11-28** (20.32 s, 19 visits). It computed session +0.9% against visits −47%, judged the condition true, and called `create_plot(line, time_min=2023-11-28)` for both metrics. Its answer correctly says "বুধবার (২০২৩-১১-২৯) থেকে".
- **First divergence:** step 2. To get a "growth on Wednesday", the agent invented a Tuesday baseline.
- **Final failed action:** two `create_plot` calls that should not exist.
- **Failure type:** Planning failure (first failure point: Planning).
- **Root cause:** the task is degenerate. "Growth since yesterday", with data only through yesterday, has no meaningful value, and the ground truth encodes "0 vs 0 → no action". Bangla resolved the ill-posed task one plausible way; English gave up.
- **Confound decision:** Benchmark/task ambiguity.
  - The translation is faithful, and Wednesday was grounded correctly.
  - The English "success" carries no evidence that the model handles this task in English.
  - The §8 tree has no benchmark step. The tree records the agent-level fail (S4), and §7 sets the confound.
- **Decision tree:** S1 ok · S2 N/A (no user simulator) · S3 ok · S4 fail · S5 fail · S6 ok · S7 ok.
- **Evidence (§9):** In analytics:98, English passed only by abstaining ("unable to calculate … no data available for today") after looping reads. In Bangla, the agent compared 11-28 with 11-29, declared the condition met, and called `create_plot(line)` twice. Ground truth needs no plot because growth since the last data day is 0 for both metrics. This is labelled a planning failure under benchmark/task ambiguity, not a Bangla effect.

### 5. workbench:analytics:119 (analytics)
- **Task goal:** if social media traffic exceeded search engine traffic over the last 4 weeks, make bar charts of both. Ground truth: `time_min=2023-11-02`.
- **English:** traffic counts from 11-02, then two bar `create_plot` calls with `time_min=2023-11-02`. Pass. EN's `time_max=11-30` is accepted by `accept_either_chart_end_date`.
- **Bangla:** "গত 4 সপ্তাহের social media আর search engine-এর bar চার্ট বানাও, …". Traffic counts and two bar plots, both with `time_min=2023-10-26`, which is 5 weeks.
- **First divergence:** step 0, the time_min of the very first read call.
- **Final failed action:** both `create_plot` calls with `time_min=2023-10-26`.
- **Failure type:** Wrong tool argument (first failure point: Entity or slot grounding).
- **Root cause:** the Bangla N-week window was mis-grounded, off by one week.
- **Confound decision:** Genuine Bangla-related agent failure.
  - The translation is faithful: ASCII 4, "bar" stays Latin, and the condition is preserved.
  - No C0 failure miscomputes an N-week window. C0 and C6 analytics:51 ("last 2 weeks") and analytics:54 ("last 1 weeks") both pass.
  - analytics:69 EN (an exclusive "since" boundary) was considered as an analogue and rejected as a different mechanism.
- **Decision tree:** S1 ok · S2 N/A (no user simulator) · S3 fail · S4 ok · S5 fail · S6 ok · S7 ok.
- **Evidence (§9):** In analytics:119, English passed by calling `create_plot(bar)` for both sources with `time_min=2023-11-02`. In Bangla, the agent grounded "গত 4 সপ্তাহের" to `time_min=2023-10-26`, so both plots cover 5 weeks. This is labelled a Bangla date/quantity grounding failure: the translation is faithful and no C0 analogue exists.
- **Adjudicated (ADJ, 2026-10-07):** first failure point is now **Tool-argument construction**, the confound is **General model weakness present in both English and Bangla**, and the tree has S3 ok, so the first fail is S5. The failure type (Wrong tool argument) is unchanged. Reason (C4):
  - 10-26 is exactly 35 days back, and no reading of "গত 4 সপ্তাহের" gives it.
  - The agent restates "৪ সপ্তাহ", and analytics:51 BN computed "গত 2 সপ্তাহ" correctly. So this is date arithmetic on a correctly read value.
  - C0 customer_relationship_manager:74 EN shows the same N-weeks-before-today arithmetic error: '6 weeks' became 'since October 16th'. That task is also the C0 analogue for crm:77.

### 6. workbench:multi_domain:84 (multi_domain)
- **Task goal:** if olga has overdue tasks, book a 30-minute 'Catch up on overdue tasks' meeting with her at the earliest free time tomorrow. Ground truth: 2023-12-01 13:00.
- **English:** found the overdue tasks, searched tomorrow 09:00–18:00, and booked 13:00. Pass.
- **Bangla:** the overdue check, email lookup and calendar search are identical to English. It booked **15:00**, stating "আপনি দুপুর ৩টার পর ফ্রি আছেন" and ignoring the free 13:00–13:30 gap.
- **First divergence:** step 3, the event_start computed from the calendar observation.
- **Final failed action:** `create_event(..., event_start=2023-12-01 15:00:00)`.
- **Failure type:** Wrong tool argument (first failure point: Tool-argument construction).
- **Root cause:** the earliest free slot was computed wrongly from the observed events. The agent treated "free" as "after the last meeting".
- **Confound decision:** General model weakness present in both English and Bangla.
  - C0 **multi_domain:102** EN ended at exactly this wrong 15:00 slot.
  - C0 multi_domain:200 EN and calendar:63 EN booked 11:00, which overlaps the 10:00–12:00 event.
  - T57.v2 is faithful.
- **Decision tree:** S1 ok · S2 N/A (no user simulator) · S3 ok · S4 ok · S5 fail · S6 ok · S7 ok.
- **Evidence (§9):** In multi_domain:84, English passed by calling `create_event` at 13:00. In Bangla, the agent read the same calendar and booked 15:00 ("দুপুর ৩টার পর ফ্রি"), skipping the free 13:00 slot. This is labelled a tool-argument (slot computation) failure and a general model weakness, because C0 multi_domain:102 picks the same wrong 15:00 slot.

### 7. workbench:multi_domain:120 (multi_domain)
- **Task goal:** if average session duration exceeded 19 since Nov 27, create the backlog task 'Improve average session duration' on Front end for the person with the most completed front-end tasks, due **next Friday**. Ground truth: `due_date=2023-12-08`.
- **English:** checked the analytics and completed tasks (nia), then `create_task(..., due_date=2023-12-08)`. Pass.
- **Bangla:** "… ডেডলাইন আগামী শুক্রবার". The analytics, the assignee and the call are identical except `due_date=2023-12-01`. Its answer: "আগামী শুক্রবার (১ ডিসেম্বর, ২০২৩)".
- **First divergence:** step 2, the due_date.
- **Final failed action:** `create_task(..., due_date=2023-12-01)`.
- **Failure type:** Wrong tool argument (first failure point: Entity or slot grounding).
- **Root cause:** "আগামী শুক্রবার" was read as "the coming Friday", which is tomorrow on a Thursday. The benchmark means the Friday of next week (12-08).
- **Confound decision:** Translation/localization error (provisional).
  - The Bangla phrase naturally supports the 12-01 reading, which the benchmark's English "next Friday" (GT 12-08) does not intend, so the translation introduced the ambiguity that caused the error.
  - No C0 failure mis-grounds "next Friday": EN gives 12-08 in md:120, md:130, md:169 and md:200.
  - Caveat: the same Bangla phrase gave 12-08 in md:169 BN and md:200 BN, so the model is inconsistent rather than systematically misled.
  - The owner has this phrase on the native-speaker review list.
- **Decision tree:** S1 fail · S2 N/A (no user simulator) · S3 fail · S4 ok · S5 fail · S6 ok · S7 ok.
- **Evidence (§9):** In multi_domain:120, English passed by calling `create_task` with `due_date=2023-12-08`. In Bangla, the agent read "আগামী শুক্রবার" as 1 December and called `create_task` with `due_date=2023-12-01`. This is labelled a slot-grounding failure caused by a translation/localization ambiguity (provisional), not a general weakness, because no C0 analogue exists.
- **Adjudicated (ADJ, 2026-10-07):** the failure type is now **Understanding failure**, because the type follows the first failure point (C1). Translation stays the confound. Decided together with email:41 under C5:
  - Here the Bangla "আগামী শুক্রবার" adds the tomorrow reading, which the English source does not favour.
  - In email:41, "গত সপ্তাহে" carries the same ambiguity as "last week", so that case is Genuine.

### EN-pass/BN-fail summary (A1)
| task | first failure point | failure type | confound |
|---|---|---|---|
| email:41 | Entity or slot grounding | Wrong tool argument | Genuine Bangla-related agent failure |
| crm:77 | Task constraint preservation | Wrong tool/action | General model weakness present in both English and Bangla |
| analytics:20 | Instruction understanding | Wrong tool argument | Genuine Bangla-related agent failure |
| analytics:98 | Planning | Planning failure | Benchmark/task ambiguity |
| analytics:119 | Entity or slot grounding | Wrong tool argument | Genuine Bangla-related agent failure |
| multi_domain:84 | Tool-argument construction | Wrong tool argument | General model weakness present in both English and Bangla |
| multi_domain:120 | Entity or slot grounding | Wrong tool argument | Translation/localization error |

- **Adjudicated (ADJ, 2026-10-07):** final labels are in `labels_final.csv`; the reasons are in `adjudication.csv`.
  - email:41, analytics:20 and multi_domain:120: the failure type becomes Understanding failure.
  - analytics:119 becomes Tool-argument construction / Wrong tool argument / General.
  - Final confounds for the 7 cases: General 3, Genuine 2, Translation 1, Benchmark 1.
  - The pattern line below now covers 2 of the 7, not 3: email:41 and multi_domain:120 are relative-date phrases resolved to another referent. analytics:119 is reclassified as date arithmetic.

Pattern: 3 of the 7 cases (email:41, analytics:119, multi_domain:120) are mis-grounded **Bangla relative-date phrases**: "last week", "last 4 weeks" and "next Friday". In all 3 the tool syntax is fine. Bangla script never leaked into a tool argument.

---

## EN-fail / BN-pass: "interesting?" notes

### workbench:calendar:63
Interesting? Yes, mildly. EN booked 11:00, which collides with the 10:00–12:00 event, while BN found 13:00. Slot-finding is noisy on both sides (compare md:84, where BN fails it), so this is variance in the same weakness, not a Bangla advantage.

### workbench:customer_relationship_manager:42
Interesting? Yes. Both sides got [] from the `status=Lead` search and then ran the same unfiltered fallback search. EN then dropped the "leads" constraint and reassigned 5 non-lead customers. BN kept the constraint ("কোনো 'Lead' স্ট্যাটাসের কাস্টমার পাওয়া যায়নি") and correctly did nothing. The Latin enum "lead" in the Bangla text may have anchored the constraint, but this is a single run.

### workbench:customer_relationship_manager:46
Interesting? Yes, same pattern as crm:42. EN searched without `status=Lead` and moved Won/Lost customers; BN filtered `status=Lead` and matched the ground truth.

### workbench:customer_relationship_manager:57
Interesting? Yes. EN read "Give Akira … customers in the crm" as "email Akira a list" (`send_email`), a pure English misreading. BN's "Akira-এর হাতে দিয়ে দাও" was correctly executed as reassignment.

### workbench:project_management:28
Interesting? Somewhat. EN counted a task due today as overdue; BN did not here, but did in pm:64. This is the same weakness surfacing on alternate sides: variance.

### workbench:multi_domain:6
Interesting? Yes, a scorer artifact. EN first booked a conflicting 12:00 slot, then self-corrected to 13:00 and deleted the first event. The final event therefore has ID 00000301 instead of 00000300, and the strict full-state comparison fails a semantically correct end state.

### workbench:multi_domain:102
Interesting? Yes. EN booked 12:00 (conflict), deleted it and rebooked 15:00, the identical wrong slot that BN chose in md:84. This is the C0 analogue that makes md:84 a general weakness.

### workbench:multi_domain:130
Interesting? Yes. EN called `create_task` (step 3) before evaluating the condition. Its final answer then computed that the condition was false ("the condition was not met … I have already created the task"): act-then-check, an ignored conditional gate mirrored by analytics:76 BN. BN evaluated first and got this one right.

---

## EN-fail / BN-fail: brief notes (labels in `labels.csv`)
- **calendar:79:** both sides read "Wednesday" as yesterday (11-29); the ground truth is the upcoming Wednesday, 12-06. Labelled Benchmark/task ambiguity (a bare weekday asked on Thursday) on both sides.
- **crm:74:**
  - EN: the 6-week threshold was misapplied, and the true targets were hidden beyond the 5-result cap.
  - BN: an **empty model response with no tool call** (llm_output '').
- **analytics:69:** both used `time_min=10-05` for "since [Oct 4]". This is the same exclusive-boundary error on both sides.
- **analytics:76:**
  - EN: looped 20 identical reads to the iteration limit and is scored a fail only because errored rows are incorrect; its state matched the ground truth (no change).
  - BN: plotted although its own reasoning said no plot was needed.
- **pm:64:** both sides counted a task due today as overdue.
- **md:18:** both sides miscounted 300 tasks and chose nia; the right person is yuki (16 tasks).
- **md:149:**
  - EN: deleted only the 5 capped search results.
  - BN: an **empty model response** after two read calls.
- **md:182:** both sides deleted only the 5 capped results and missed the sixth lead.
- **md:200:** both sides booked a conflicting slot: EN 11:00, BN 12:00.

Empty model responses (no content and no tool call) occur in **2/90 C6 runs** (crm:74, md:149) and **0/90 C0 runs**. Both are both_wrong pairs, so they do not affect the EN-pass/BN-fail set. They are labelled Unclear: no error was recorded, so this cannot be attributed to the provider.

---

## Adjudication of the EN-fail rows (ADJ, 2026-10-07)
The notes above do not state these labels, so they are left as written. Under convention C1 (in `annotation_rules.md`, applied to all 33 rows), the failure type changed on these rows:
- calendar:79 EN/BN, analytics:69 EN/BN, project_management:64 EN/BN, customer_relationship_manager:46 EN and :57 EN → Understanding failure.
- customer_relationship_manager:42 EN → Dialogue-state failure (status=Lead was applied at step 2 and dropped at step 3).

No first failure point or confound changed on these rows. Rulings that kept a label:
- multi_domain:6 EN stays General: the ID shift comes from a real created-then-deleted event, which C6 does not count as a benchmark artefact.
- crm:42 EN and crm:46 EN stay Unclear: there is no C6 analogue. crm:46 EN never applied the Lead filter; it did not drop it after an empty result.
- project_management:28 EN stays Wrong tool/action: it states 'No overdue tasks were found' and still moves the due-today task.

See `adjudication.csv`.
