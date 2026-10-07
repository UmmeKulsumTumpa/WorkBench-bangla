# Trace notes: gpt-oss:20b (`ollama-gpt-oss-20b`), C0 (English) vs C6 (Bangla), 90-task pilot

Annotator: A1. Rules: `results/failure_pipeline/annotation_rules.md`. Labels: `labels.csv` in this folder.
Counts (verified against `task_table.csv`): EN-pass/BN-fail 15, EN-fail/BN-fail 27, EN-fail/BN-pass 10, EN-pass/BN-pass 38.

Conventions used throughout:
- Step 2 of the decision tree is always "N/A (no user simulator)".
- An invented `<name>@example.com` address used without (or despite) a `company_directory` lookup is first failure point "Entity or slot grounding", failure type "Wrong tool argument".
- A dropped filter constraint is "Task constraint preservation"; the type is "Wrong tool argument" when the constraint is missing from a search call, "Wrong tool/action" when the agent acts on records whose returned fields visibly violate it.
- S7 is `fail` only when the agent stopped before a required write; it is `ok` when all writes were made (even if wrong) and `na` when the trace is lost.
- Errored rows: the harness keeps 0 steps on an exception. Call counts come from the logs `c0_2026-10-05_22-53-07`, `c6_2026-10-05_23-57-37` and `c6_2026-10-07_05-53-19`, where per-task HTTP counts match the step counts for every non-errored task. The first c0 log (`c0_2026-10-05_21-50-28`) was buffered and its HTTP lines do not line up with tasks, so no call counts are taken from it.
- All translation judgments are provisional until the owner's native-speaker review.
- Adjudicated: the conventions in `annotation_rules.md` (C1–C12) replace three of the A1 conventions above. An invented address is Tool-argument construction (C8). A filter missing from the first search is typed Understanding failure (C1 sub-rule). S7 is never `na`: it is `fail` when a crash leaves required writes missing (C3, C12). The final labels are in `labels_final.csv`, and the reasons in `adjudication.csv`.

---

## EN-pass / BN-fail (15 cases)

### workbench:email:51 (email)
- **Task goal:** forward the latest email about 'Update on Client Appreciation Gala' to santiago.
- **English:** search_emails → find_email_address("Santiago") → forward_email(00000206, santiago.martinez@atlas.com). Pass.
- **Bangla:** search_emails found 00000206, then forward_email(00000206, recipient="santiago@example.com") with no directory lookup. Fail.
- **First divergence:** step 1. Bangla skips `find_email_address` and invents an address.
- **Final failed action:** forward_email to the wrong recipient.
- **Failure type:** Wrong tool argument (first failure point: Entity or slot grounding).
- **Root cause:** the recipient name was not grounded to its directory address.
- **Confound:** General model weakness present in both English and Bangla. The same mechanism fails C0 email:21 and email:75. The name is Latin-script in both tasks, and the translation is faithful.
- **Evidence:** `email.forward_email {'email_id': '00000206', 'recipient': 'santiago@example.com'}`.
- **Decision tree:** S1 ok · S2 N/A (no user simulator) · S3 ok · S4 ok · S5 fail · S6 ok · S7 ok.
- **Adjudicated:** first failure point Tool-argument construction (C8: the address was fabricated, not misread); the failure type, confound and tree are unchanged.

### workbench:email:66 (email)
- **Task goal:** forward my most recent email from leila to fatima.
- **English:** search "Leila" → find_email_address("Fatima") → forward_email(00000052, fatima.khan@atlas.com). Pass.
- **Bangla:** search "leila" → forward_email(00000052, "fatima@example.com"). Fail.
- **First divergence:** step 1, no directory lookup.
- **Final failed action:** forward_email to the invented address.
- **Failure type:** Wrong tool argument (Entity or slot grounding).
- **Root cause:** ungrounded recipient name.
- **Confound:** General model weakness. Same mechanism in C0 email:41 ("nadia@example.com").
- **Evidence:** `recipient='fatima@example.com'`.
- **Decision tree:** S1 ok · S2 N/A (no user simulator) · S3 ok · S4 ok · S5 fail · S6 ok · S7 ok.
- **Adjudicated:** first failure point Tool-argument construction (C8: the address was fabricated, not misread); the failure type, confound and tree are unchanged.

### workbench:email:69 (email)
- **Task goal:** forward my most recent email from olga to raj.
- **English:** search "Olga" → find_email_address("Raj") → forward_email(00000206, raj.patel@atlas.com). Pass.
- **Bangla:** search "olga" → forward_email(00000206, "raj@example.com"). Fail.
- **First divergence:** step 1, no lookup.
- **Final failed action:** forward_email to the invented address.
- **Failure type:** Wrong tool argument (Entity or slot grounding).
- **Root cause:** ungrounded recipient name.
- **Confound:** General model weakness. Same mechanism in C0 email:75.
- **Evidence:** `recipient='raj@example.com'`. The final answer names the wrong person ("রজকে").
- **Decision tree:** S1 ok · S2 N/A (no user simulator) · S3 ok · S4 ok · S5 fail · S6 ok · S7 ok.
- **Adjudicated:** first failure point Tool-argument construction (C8: the address was fabricated, not misread); the failure type, confound and tree are unchanged.

### workbench:email:74 (email)
- **Task goal:** forward the last 'Update on Team Building Retreat' email to lena and aisha.
- **English:** search → find_email_address(Lena), find_email_address(Aisha) → two forwards of 00000262 to the @atlas.com addresses. Pass.
- **Bangla:** search → forwards of 00000262 to "lena@example.com" and "aisha@example.com". Fail.
- **First divergence:** step 1, no lookups.
- **Final failed action:** both forward_email calls have invented recipients.
- **Failure type:** Wrong tool argument (Entity or slot grounding).
- **Root cause:** ungrounded recipient names.
- **Confound:** General model weakness. C0 email:75 is the same two-recipient forward with invented addresses.
- **Evidence:** `recipient='lena@example.com'`, `recipient='aisha@example.com'`.
- **Decision tree:** S1 ok · S2 N/A (no user simulator) · S3 ok · S4 ok · S5 fail · S6 ok · S7 ok.
- **Adjudicated:** first failure point Tool-argument construction (C8: the address was fabricated, not misread); the failure type, confound and tree are unchanged.

### workbench:calendar:20 (calendar)
- **Task goal:** move my first meeting with kofi on December 4 by 1.5 hours (GT: event 00000109 starts 12:00).
- **English:** search(query "Kofi", 2023-12-04..2023-12-04) → []; search("", same window) → []; widened to 00:00:00–23:59:59 and found 00000109 → update_event(..., "2023-12-04 12:00:00"). Pass.
- **Bangla:** search("kofi", 2023-12-04..2023-12-04) → []; search("kofi@example.com", same window) → []; final answer asked the user for the event ID. Fail.
- **First divergence:** step 1. English widened the window, while Bangla queried an invented address and then gave up.
- **Final failed action:** update_event was never called.
- **Failure type:** Premature abandonment (Premature termination).
- **Root cause:** the agent stopped after empty searches instead of recovering. The zero-width first search is the same in the passing English run, so it is not decisive.
- **Confound:** General model weakness. Giving up and asking the user for IDs also fails C0 project_management:60 and multi_domain:6. The Bangla date was resolved correctly.
- **Evidence:** "দয়া করে ওই মিটিংটির ইভেন্ট আইডি (Event ID) আমাকে জানাবেন কি?"
- **Decision tree:** S1 ok · S2 N/A (no user simulator) · S3 ok · S4 ok · S5 ok · S6 ok · S7 fail.
- **Adjudicated:** first failure point Tool-argument construction, failure type Wrong tool argument, tree S5 fail and S7 fail (first fail S5). Under C2 the first failure is the uncorrected zero-width window at step 0, which the passing English run widened; Premature termination needs every step before the stop to be correct. Confound General, now citing C0 project_management:60 and :42 (malformed search, then no recovery).

### workbench:customer_relationship_manager:22 (CRM)
- **Task goal:** add Jordan Moore as a new lead assigned to Akira.
- **English:** find_email_address(Akira) → add_customer(customer_name, assigned_to_email, status="Lead"). Pass.
- **Bangla:** the same lookup, then add_customer with the same three values plus customer_email="", customer_phone="", last_contact_date="", product_interest="", notes="", follow_up_by="". Fail, because empty strings differ from nulls in the final state.
- **First divergence:** step 1, the argument list of add_customer.
- **Final failed action:** add_customer with unrequested empty fields.
- **Failure type:** Wrong tool argument (Tool-argument construction).
- **Root cause:** the agent fills optional parameters that the task does not mention.
- **Confound:** General model weakness. C0 customer_relationship_manager:20 invented optional values and multi_domain:18 used empty strings.
- **Evidence:** `customer_email='', customer_phone='', ..., follow_up_by=''`.
- **Decision tree:** S1 ok · S2 N/A (no user simulator) · S3 ok · S4 ok · S5 fail · S6 ok · S7 ok.

### workbench:customer_relationship_manager:38 (CRM)
- **Task goal:** reassign Taylor Jackson to Raj.
- **English:** search_customers → find_email_address(Raj) → update_customer(00000189, assigned_to_email, raj.patel@atlas.com). Pass.
- **Bangla:** step 0 called the non-existent `crm_search_customers`, which was rejected. The rest is identical to English, so the final DB state is correct, but WorkBench fails any run that contains an unrecognised call. Fail.
- **First divergence:** step 0, tool name.
- **Final failed action:** none in the state. The failure is the scored unrecognised call.
- **Failure type:** Wrong tool/action (Tool selection).
- **Root cause:** a hallucinated tool name.
- **Confound:** General model weakness. C0 customer_relationship_manager:74 called the same `crm_search_customers` and failed the same way.
- **Evidence:** "Tool 'crm_search_customers' not found."
- **Decision tree:** S1 ok · S2 N/A (no user simulator) · S3 ok · S4 fail · S5 ok · S6 ok · S7 ok.

### workbench:customer_relationship_manager:53 (CRM)
- **Task goal:** give Nadia all of Sofia's training customers that are qualified or in proposal (3 updates).
- **English:** two lookups, two filtered searches, three update_customer calls. Pass.
- **Bangla:** errored with `update_customer() got an unexpected keyword argument 'new?'`. Trace lost; 4 model calls preceded the failure (from the log `c6_2026-10-07_05-53-19`; 2 HTTP 500s were retried successfully). The first attempt (`c6_2026-10-05_23-57-37`) failed with the same `'new?'` after 6 calls.
- **First divergence:** the update_customer call, with a malformed keyword.
- **Final failed action:** no update was executed.
- **Failure type:** Wrong tool argument (Tool-argument construction).
- **Root cause:** a malformed keyword name (`new?` instead of `new_value`).
- **Confound:** General model weakness. C0 project_management:28 has the same `'new?'`. Caveat: this error class is more frequent in C6 (see the report).
- **Evidence:** the CSV error string, plus the log.
- **Decision tree:** S1 ok · S2 N/A (no user simulator) · S3 na (trace lost) · S4 ok · S5 fail · S6 ok · S7 na.
- **Adjudicated:** tree S7 fail (C3: never `na`; the required writes are missing). S3 stays `na` (C12: the lost trace says nothing about it).

### workbench:customer_relationship_manager:77 (CRM)
- **Task goal:** move customers who haven't responded to a software proposal in 6 weeks to lost (GT: no change; there are none).
- **English:** search_customers(product_interest="Software", status="Proposal", last_contact_date_max="2023-10-19") → [], so it changed nothing. Pass.
- **Bangla:** search_customers(product_interest="Software", last_contact_date_max="2023-10-19"), with no status filter, then set 5 customers with status Won/Qualified/Lead to Lost. Fail.
- **First divergence:** step 0, the status filter is missing.
- **Final failed action:** five spurious update_customer(..., status, "Lost") calls.
- **Failure type:** Wrong tool argument (Task constraint preservation).
- **Root cause:** the "proposal" status constraint was dropped.
- **Confound:** Translation/localization error (provisional). The BN template renders the status enum "proposal" in Bangla script ("প্রপোজালে"). Policy §4 says CRM status values stay in Latin script, and this is exactly the constraint that was lost. Counter-evidence: C6 customer_relationship_manager:74 uses the same rendering and was mapped correctly, and C0 customer_relationship_manager:42 drops a status filter in English. Flagged for the native-speaker review.
- **Evidence:** `search_customers {'product_interest': 'Software', 'last_contact_date_max': '2023-10-19'}`, followed by 5 updates to Lost.
- **Decision tree:** S1 fail · S2 N/A (no user simulator) · S3 ok · S4 ok · S5 fail · S6 ok · S7 ok.
- **Adjudicated:** failure type Understanding failure; confound General model weakness; tree S1 ok · S3 fail · S4 fail · S5 na · S7 ok. The transliteration keeps the word's meaning, and the English 'a proposal' admits the same drop (C9, C5(1)). The same model mapped the same 'প্রপোজালে' correctly in crm:74 BN. A status filter missing from the first search also fails C0 crm:42 EN and md:182 EN. The policy deviation remains flagged for the native-speaker review.

### workbench:analytics:42 (analytics)
- **Task goal:** bar charts of total visits and engaged users since 2023-11-10.
- **English:** create_plot(2023-11-10..2023-11-30) for total_visits and user_engaged. Pass, since an end of 11-30 is accepted.
- **Bangla:** create_plot(time_min="2023-11-10", time_max="2023-11-10") for both metrics. The final answer says the charts are "২০২৩‑১১‑১০ তারিখের" (for the date 2023-11-10). Fail.
- **First divergence:** step 0, time_max.
- **Final failed action:** both plots cover a single day.
- **Failure type:** Understanding failure (Instruction understanding).
- **Root cause:** "2023-11-10 থেকে" (from/since 2023-11-10) was read as that one day.
- **Confound:** Genuine Bangla-related agent failure (provisional). The error is tied to a Bangla range phrase, and no C0 failure collapses "since" to one day. The translation is the standard rendering of "since", but unlike other BN templates it omits "এখন পর্যন্ত" (until now). Weakening evidence: the same bare "<date> থেকে" was read as an open range in C6 analytics:0 and analytics:32 (both passed), so this looks like a one-off misreading of Bangla input rather than a systematic one.
- **Evidence:** `analytics.create_plot {'time_min': '2023-11-10', 'time_max': '2023-11-10', ...}`.
- **Decision tree:** S1 ok · S2 N/A (no user simulator) · S3 fail · S4 ok · S5 fail · S6 ok · S7 ok.
- **Adjudicated:** first failure point Entity or slot grounding (C1: the date phrase was resolved to a different referent, the single day). Type, confound (Genuine, with the analytics:0/:32 caveat) and tree unchanged.

### workbench:analytics:43 (analytics)
- **Task goal:** bar charts of engaged users and average session duration since 2023-09-24.
- **English:** two create_plot calls. Pass.
- **Bangla:** errored with `engaged_users_count() got an unexpected keyword argument 'field'`. Trace lost; 1 model call preceded the failure (from the log). The first attempt failed the same way, with `'traffic_source'`.
- **First divergence:** the first tool call.
- **Final failed action:** no plots.
- **Failure type:** Wrong tool argument (Tool-argument construction).
- **Root cause:** an invented keyword on an analytics count tool.
- **Confound:** General model weakness. C0 multi_domain:200 errored on its first call with `total_visits_count(value_to_plot=...)`.
- **Evidence:** the CSV error string, plus the log.
- **Decision tree:** S1 ok · S2 N/A (no user simulator) · S3 na (trace lost) · S4 ok · S5 fail · S6 ok · S7 na.
- **Adjudicated:** tree S3 ok (the crashing call names the requested metric, C12) and S7 fail (C3).

### workbench:analytics:54 (analytics)
- **Task goal:** if total visits was below 3 at any time in the last week, plot it (GT: no change).
- **English:** total_visits_count(11-23..11-29), lowest 6, so no plot. Pass.
- **Bangla:** the same query. It wrote that visits never fell below 3 but still called create_plot(11-23..11-29, total_visits, line) "as requested". Fail.
- **First divergence:** step 1, an unnecessary create_plot.
- **Final failed action:** the spurious create_plot.
- **Failure type:** Wrong tool/action (Task constraint preservation).
- **Root cause:** the conditional ("if so") was ignored after being evaluated correctly.
- **Confound:** General model weakness. C0 analytics:98 also plotted and then concluded "no plot is generated".
- **Evidence:** "কখনও ৩‑এর নিচে ছিল না। ... তবে আপনার অনুরোধ অনুযায়ী লাইন চার্ট তৈরি করেছি".
- **Decision tree:** S1 ok · S2 N/A (no user simulator) · S3 ok · S4 fail · S5 ok · S6 ok · S7 ok.
- **Adjudicated:** labels kept (Task constraint preservation / Wrong tool/action / General, citing C0 analytics:98 EN); tree S5 na (C3: the only write should not exist). Verification failure was rejected: the agent checked the condition and acted against it.

### workbench:analytics:105 (analytics)
- **Task goal:** line plot of the most popular traffic source since November 24 (GT: visits_direct).
- **English (re-run):** three traffic_source_count calls, then a rejected create_plot(value_to_plot="traffic_source", line) ("Value to plot must be one of ..."), then create_plot(visits_direct, line). Pass (the rejection is returned as a message, so the run still executed). The first EN attempt errored with `traffic_source_count() ... 'traffic_source?'`; its call count cannot be recovered from the buffered log.
- **Bangla:** traffic_source_count for direct and referral, then an empty final answer. Fail.
- **First divergence:** step 2. Bangla stops where English continues to search engine and create_plot.
- **Final failed action:** create_plot was never called.
- **Failure type:** Premature abandonment (Premature termination).
- **Root cause:** the agent stopped mid-task with an empty answer.
- **Confound:** General model weakness. C0 customer_relationship_manager:57 and :42 also end with an empty answer before the required writes. The English pass here was itself fragile.
- **Evidence:** BN final answer `''` after 2 read-only calls.
- **Decision tree:** S1 ok · S2 N/A (no user simulator) · S3 ok · S4 ok · S5 ok · S6 ok · S7 fail.

### workbench:project_management:2 (project_management)
- **Task goal:** move all of yuki's in-progress tasks to in review (00000091).
- **English:** find_email_address(Yuki) → search_tasks(yuki.tanaka@atlas.com, In Progress) → update_task(00000091, list_name, "In Review"). Pass.
- **Bangla:** search_tasks("yuki@example.com") → []. find_email_address("yuki") returned yuki.tanaka@atlas.com, but the agent kept searching with "yuki@example.com" (4 empty searches) and concluded there were no tasks. Fail.
- **First divergence:** step 0, the invented assignee address. The lookup result was ignored at step 2.
- **Final failed action:** update_task was never called.
- **Failure type:** Wrong tool argument (Entity or slot grounding).
- **Root cause:** an invented identifier that persisted despite a correct lookup.
- **Confound:** General model weakness. C0 project_management:30, :42 and :60 use invented "<name>@example.com" assignees.
- **Evidence:** the obs `["yuki.tanaka@atlas.com"]`, followed by `search_tasks {'assigned_to_email': 'yuki@example.com', ...}`.
- **Decision tree:** S1 ok · S2 N/A (no user simulator) · S3 ok · S4 ok · S5 fail · S6 ok · S7 fail.
- **Adjudicated:** first failure point Tool-argument construction (C8: the fabricated address was kept despite the correct lookup); the type, confound and tree are unchanged.

### workbench:project_management:72 (project_management)
- **Task goal:** reassign nia's most urgent task to olga (00000162).
- **English:** lookups for Nia and Olga, search_tasks, then update_task(00000162 → olga.petrova). Pass.
- **Bangla:** 11 search_tasks("nia@example.com") calls, all [], one garbled tool name ("project___...We"), then it asked the user for Nia's task list. Fail.
- **First divergence:** step 0, the invented address with no lookup.
- **Final failed action:** update_task was never called.
- **Failure type:** Wrong tool argument (Entity or slot grounding).
- **Root cause:** an ungrounded assignee identifier, followed by a degenerate retry loop.
- **Confound:** General model weakness. C0 project_management:30 shows the same loop with "luis@example.com" and a garbled "functions___...We" tool.
- **Evidence:** 11× `search_tasks {'assigned_to_email': 'nia@example.com'}` → `[]`.
- **Decision tree:** S1 ok · S2 N/A (no user simulator) · S3 ok · S4 ok · S5 fail · S6 ok · S7 fail.
- **Adjudicated:** first failure point Tool-argument construction (C8); the type, confound and tree are unchanged.

---

## EN-fail / BN-pass: "interesting?" notes (10 cases)

### workbench:email:21
Interesting as a mirror case. EN invented "jinsoo@example.com", while BN looked up jinsoo.kim. Directory-skipping hits both languages, which suggests run-to-run variance rather than a language effect.

### workbench:email:36
Yes. This is a benchmark text defect. The EN chosen_template never closes the reply quote, so EN copied "Can you send the reply for me?" into the body. The BN template closes the quote. It inflates the EN failure count by one (Benchmark/task ambiguity).

### workbench:email:75
Mirror case: EN used invented addresses and BN did the lookups. Not language-related.

### workbench:calendar:38
Mild. EN also deleted a past event (2023-08-03), while BN deleted only the next one. The same temporal-constraint loss appears in both languages elsewhere (calendar:84).

### workbench:calendar:105
Mirror case: EN invented "yuki@example.com" and BN looked it up.

### workbench:customer_relationship_manager:60
Mirror of CRM:42 BN. EN dropped the owner (Sofia) filter and deleted 5 other customers, while BN kept it.

### workbench:customer_relationship_manager:74
Yes. This is the mirror of CRM:38. The same hallucinated `crm_search_customers` failed EN here and BN there, both times with an otherwise correct final state. WorkBench's unrecognised-call penalty hits both sides. The BN pass uses the same Bangla-script "প্রপোজালে" that CRM:77 BN dropped, which is counter-evidence to a translation cause there.

### workbench:project_management:28
Yes, as a fragile pass. EN errored on a malformed keyword `'new?'`. BN passed only on the re-run, and its first attempt errored with `'new_task_name'`. The GT is "no change", so the pass required only not writing.

### workbench:project_management:42
BN also started with "yuki@example.com" but recovered: it searched the substring "yuki", got "Assignee email not valid" for "carlos@example.com", then looked Carlos up. This is recovery, not a language effect.

### workbench:project_management:64
Not informative. The EN failure is a read timeout (Tool/environment failure). BN passed a "no change" task. This case drops out of the tool/environment sensitivity analysis.

---

## Adjudication: EN-fail rows (no per-row notes above)

These are the adjudicated label changes on EN-fail/BN-fail and EN-fail/BN-pass rows. Reasons are in `adjudication.csv`; final labels are in `labels_final.csv`.

- **Confound changes:**
  - email:41 BN: General → Genuine. 'গত সপ্তাহে' read as the rolling 11-23..29 window, as in gemma email:41.
  - calendar:79 EN/BN: General → Benchmark (C6(a), as in gemma calendar:79).
  - analytics:69 EN: Benchmark → Unclear; analytics:69 BN: Benchmark → General. The condition holds under every reading, so C6(a) does not apply.
  - multi_domain:120/169/200 BN: Benchmark → Translation (C5, C11, as in gemma md:120 BN). The English rows of md:120 and md:169 stay Benchmark.
- **First failure point → Tool-argument construction (C8):**
  - invented addresses: email:21/41/75 EN, calendar:105 EN, CRM:20/46 EN, PM:30/42/60 EN, md:76/149 EN;
  - an uncounted assignee: md:18 EN;
  - a 09:00 slot booked without reading the calendar: md:6 BN, md:84 EN, md:102 BN.
- **Type follows the first failure point (C1):**
  - Understanding failure: calendar:63 EN/BN (meeting later today counted as held → Task constraint preservation); calendar:79 EN/BN; analytics:20 EN/BN (→ Instruction understanding); md:120/169 EN/BN; md:200 BN.
  - Understanding failure, because the filter is missing from the first search: calendar:84 BN, CRM:42 EN/BN, CRM:60 EN, PM:57 EN/BN, md:182 EN.
  - Wrong tool/action, because the gate was evaluated wrongly at a write that should not exist: PM:60 BN (Result verification → Task constraint preservation); PM:28 EN (C10: Tool-argument construction → Task constraint preservation).
  - md:76 BN: first failure point Instruction understanding → Task constraint preservation.
- **Evidence only (C7):** C6 analogues were added to 15 EN General rows that cited only C0.
