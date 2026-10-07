# Pilot failure analysis: WorkBench, gpt-oss:20b, C6 (BN task text and system prompt, EN tools, replies forced to Bangla) vs C0 (all English)

90 paired tasks (15 per domain). C0 53/90 correct, C6 48/90. 25 discordant pairs (15 ref_only = c0 right and c6 wrong, 10 treat_only = c6 right and c0 wrong; McNemar p = 0.4244) and 27 both_wrong. Every failed run in those 52 pairs was labelled: 37 C0 rows and 42 C6 rows, in `failure_labels.csv` in this folder. Annotator: `model:claude-opus-5-5` (single annotator, not yet human-checked). The BN task translations and the BN system prompt have not yet been reviewed by the owner.

Runs: C0 `ollama-gpt-oss-20b_all_2026-10-05_21-50-29.csv` (2026-10-05, harness `dcb6c76`). C6 `ollama-gpt-oss-20b_all_2026-10-05_23-57-38.csv` (67 rows on 2026-10-05/06, the last 23 on 2026-10-07 after a resume with a new API key; harness `a8447a3`). The harness code is the same in both commits (progress.md #36, #37). Both `run_meta_*.json` files carry these commits.

C6 prompt (`system_prompt_sent` in the C6 meta, identical to the gemma C6 run): the Bangla date/time and meeting-hours prefix, then "do not ask for confirmation; act immediately; do not stop after a search step", then "টাস্ক যে ভাষাতেই লেখা হোক না কেন, ইউজারকে সবসময় বাংলায় উত্তর দিও" (always answer the user in Bangla, whatever the task language). Tool schemas are English.

**Labels** (schema.md §4, adapted from BabelArena):
- *outcome*: right process, wrong value written.
- *reasoning*: wrong inference about the task or data.
- *planning*: missing, extra or misordered steps.
- *tool_use*: wrong tool, or wrong or malformed arguments.
- *control_flow*: stopped early, looped, hit the step limit, asked for confirmation, or ended on an empty answer.
- *memory*: lost information obtained earlier in the trace.
- *multilingual*: the failure is attributable to the instruction language. Subtypes: wrong_language_output, language_mixing, numeral_script_error, language_induced_tool_misuse.
- *infrastructure* (new for this model; not in the gemma analyses): the provider caused the failure and the trace shows no model fault.

**Lost traces.** When a run ends on any exception (a provider error or a bad kwarg), the harness records `Steps: 0` and an empty trace, so the model's earlier calls, and any writes they made, are lost. They did happen: counting the HTTP 200 lines in each task's segment of the run log (between the previous task's `### Steps` line and this task's), every one of the 13 errored rows made 1–7 model calls first. The notes in `failure_labels.csv` give the count for each row, and the per-row list is under "Errored rows" below.

**Infrastructure rule.** A run is labelled `infrastructure` when the event that ended it came from the provider: an HTTP 5xx after the harness's 10 retries, a read timeout (`APITimeoutError` after retries), or the time/iteration limit reached while the trace shows no model fault (a stall). For the 5xx and timeout rows the earlier calls cannot be inspected because the trace is lost, so a model fault before the provider error cannot be ruled out. The label says who ended the run, not that the model made no mistake. Everything else is a model failure:
- A bad tool kwarg (`new?`, `newvalue`, `field`, `value_to_plot`) is a **model** error. The harness raises `TypeError` and ends the run, the trace is lost, and the evidence is the error text. The last logged model call is the one that produced the bad kwarg.
- C0 project_management:57 hit the limit after 20 steps in 56.4 s, moving every Carlos task (including Completed ones) to Backlog. Its trace is intact. That is a model loop, so it is labelled `reasoning`, not infrastructure.
- Infrastructure rows: C0 3 (project_management:35 and multi_domain:130, HTTP 500; project_management:64, timeout after 880.7 s). C6 3 (project_management:35, customer_relationship_manager:46 and multi_domain:84, all HTTP 500). These 6 rows span 5 pairs.
- **Weakest infrastructure label: C6 customer_relationship_manager:46.** The recorded re-run made 7 model calls and then hit a 500. The first attempt (at `a8447a3`) also made 7 calls and then failed on a bad kwarg (`newvalue`), a model error. The label is kept because the recorded run was ended by the provider, but this row is at least as likely a model failure. The pair is both_wrong, so S1 does not change Δ.

**Errored rows: model calls before the failure** (HTTP 200 lines in the final attempt's log segment; command in the Task 4 report):

| row | cause | calls | log |
|---|---|---|---|
| C0 project_management:28 | bad kwarg `new?` | 6 | c0_2026-10-05_22-53-07, line 38 |
| C0 multi_domain:200 | bad kwarg `value_to_plot` | 1 | c0_2026-10-05_22-53-07, line 560 |
| C0 project_management:35 | HTTP 500 ×10 | 3 | c0_2026-10-05_22-53-07, line 141 |
| C0 project_management:64 | timeout ×9 retries, then terminal timeout | 2 | c0_2026-10-05_22-53-07, line 331 |
| C0 multi_domain:130 | 9 timeouts, then HTTP 500 | 3 | c0_2026-10-05_22-53-07, line 512 |
| C6 analytics:43 | bad kwarg `field` | 1 | c6_2026-10-07_05-53-19, line 145 |
| C6 customer_relationship_manager:53 | bad kwarg `new?` | 4 (+2 retried 500s) | c6_2026-10-07_05-53-19, line 107 |
| C6 customer_relationship_manager:57 | bad kwarg `newvalue` | 5 | c6_2026-10-07_05-53-19, line 128 |
| C6 project_management:30 | bad kwarg `new?` | 5 | c6_2026-10-07_05-53-19, line 172 |
| C6 multi_domain:130 | bad kwarg `value_to_plot` | 1 | c6_2026-10-07_05-53-19, line 442 |
| C6 project_management:35 | HTTP 500 ×10 | 5 | c6_2026-10-07_05-53-19, line 252 |
| C6 customer_relationship_manager:46 | HTTP 500 ×10 | 7 | c6_2026-10-07_05-53-19, line 83 |
| C6 multi_domain:84 | HTTP 500 ×10 | 6 | c6_2026-10-07_05-53-19, line 401 |

The line numbers point to each task's `### Steps` line.

## 0. Headline numbers and sensitivity

| | C0 | C6 | Δ (C6 − C0) | 95% CI | McNemar p | ref_only / treat_only |
|---|---|---|---|---|---|---|
| Main (recorded runs, n = 90) | 53/90 = 58.9% | 48/90 = 53.3% | −5.6 pp | −16.7 to +5.6 pp | 0.4244 | 15 / 10 |
| S1: pairs with no infrastructure error (n = 85) | 53/85 = 62.4% | 47/85 = 55.3% | −7.1 pp | −17.6 to +4.7 pp | 0.3075 | 15 / 9 |
| S2: recovered re-runs counted as failures (n = 90) | 51/90 = 56.7% | 46/90 = 51.1% | −5.6 pp | −16.7 to +5.6 pp | 0.4244 | 15 / 10 |

- Side effects: C0 25.6%, C6 24.4% (Δ −1.1 pp, 95% CI −11.1 to +8.9 pp). Domain-reweighted completion: C0 54.2%, C6 49.0%.
- Main row: copied from `metrics.csv`. S1 and S2 were computed from `paired.csv` with the comparison script's own `mcnemar_exact` and `paired_bootstrap_ci` (same seed and 10,000 resamples); the same code reproduces the main row exactly.
- **S1** drops the 5 pairs in which either side has an infrastructure row (project_management:35, project_management:64, multi_domain:130, customer_relationship_manager:46, multi_domain:84). Four are both_wrong; project_management:64 is treat_only (C0 timed out, C6 correct). C6 customer_relationship_manager:46 is the weakest infrastructure label (see above).
- **S2** counts every re-run row that recovered on its second attempt as a failure in its condition. Resuming an unfinished run drops its errored rows and re-runs them, so these rows got a second try. Verified from the CSVs (C0 first attempts from `c0_2026-10-05_21-50-28.log`, C6 first attempts from the 76-row CSV at `a8447a3`):
  - C0 idx 0 = email:5 (first attempt: time/iteration limit after 1 step, 672 s) and idx 58 = analytics:105 (first attempt: kwarg `traffic_source?`). Both are now correct, so both flip.
  - C6 idx 65 = project_management:28 (first attempt: kwarg `new_task_name`) and idx 69 = project_management:49 (first attempt: kwarg `new?`). Both are now correct, so both flip. idx 71 = project_management:60 (first attempt: time/iteration limit) has no error now but is still wrong, so it does not change.
  - Two flips per side cancel: Δ, p and the discordant counts are unchanged; both rates fall by 2.2 pp.
- **Requests:** distinct `llm_input` per task (decision #32): C0 381, C6 346 (`total_llm_requests` in the run metas; the per-task sums agree). These cover only each row's final attempt. **Provider attempts**, a separate figure from the 5 pilot logs: HTTP 200 840, HTTP 5xx 71, HTTP 429 1 (the monthly-limit stop on 2026-10-06), timeout retry lines 54.

## 1. Discordant pairs

"Invented address" below means a recipient or assignee such as `yuki@example.com`, made up instead of calling `company_directory.find_email_address`.

| task_uid | EN task (short) / BN wording at issue | Failed side: what went wrong | Label (secondary) |
|---|---|---|---|
| email:51 | forward latest 'Client Appreciation Gala' email to santiago | **C6.** Invented address santiago@example.com; right email id. | tool_use (planning) |
| email:66 | forward latest email from leila to fatima | **C6.** Invented fatima@example.com. | tool_use (planning) |
| email:69 | forward latest email from olga to raj | **C6.** Invented raj@example.com. | tool_use (planning) |
| email:74 | forward 'Team Building Retreat' email to lena and aisha | **C6.** Invented lena@/aisha@example.com. | tool_use (planning) |
| calendar:20 | move first meeting with kofi on Dec 4 by 1.5 h | **C6.** Zero-width window (12-04 to 12-04) returned nothing twice; asked the user for the event ID. C0 made the same first call, then retried with full-day times. | control_flow (tool_use) |
| analytics:42 | bar charts "since 2023-11-10" / "2023-11-10 থেকে" | **C6.** Both plots for the single day 11-10. The same bare "থেকে" gave full ranges in analytics:0 and :32. | reasoning (multilingual) |
| analytics:43 | bar charts since 2023-09-24 | **C6.** Bad kwarg `field` ended the run; trace lost (1 model call, from the log). | tool_use |
| analytics:54 | line chart if visits < 3 in the last week (condition false) | **C6.** Said the condition was not met, then plotted anyway. | planning (reasoning) |
| analytics:105 | line plot of the most popular traffic source | **C6.** Queried 2 of 4 sources, then an empty answer. | control_flow |
| pm:2 | move yuki's In Progress tasks to In Review | **C6.** Looked up yuki.tanaka@atlas.com, then kept searching with yuki@example.com. | memory (tool_use) |
| pm:72 | reassign nia's most urgent task to olga | **C6.** 11 searches with invented nia@example.com; asked the user. | tool_use (control_flow) |
| crm:22 | add lead Jordan Moore for Akira | **C6.** Passed every optional field as "", so the row differs from GT. C0 passed only the 3 GT arguments. Close to a scoring artefact. | tool_use |
| crm:38 | move Taylor Jackson to Raj | **C6.** Correct update, but step 0 called the non-existent `crm_search_customers`; the scorer rejects disallowed tool names. | tool_use |
| crm:53 | move Sofia's Training Qualified/Proposal customers to Nadia | **C6.** Bad kwarg `new?` ended the run; trace lost (4 model calls before it, from the log). | tool_use |
| crm:77 | software proposals with no reply for 6 weeks → Lost (none qualify) | **C6.** No status=Proposal filter; moved 5 customers (some Won) to Lost. | reasoning |
| email:21 | send email to jinsoo | **C0.** Invented jinsoo@example.com. | tool_use (planning) |
| email:36 | reply to lena with '…tomorrow. Can you send the reply for me? | **C0.** The body also carries "Can you send the reply for me?" (the task's quote is never closed). | outcome |
| email:75 | forward last 'Board of Directors Conclave' email to akira and yuki | **C0.** Invented akira@/yuki@example.com. | tool_use (planning) |
| calendar:38 | cancel the next Quarterly Sales Review | **C0.** Deleted the right event and also a past one (2023-08-03). | planning |
| calendar:105 | 30-min event with yuki on Dec 20 at 10 | **C0.** Invented yuki@example.com. | tool_use (planning) |
| pm:28 | move nia's overdue backlog tasks (none) | **C0.** Bad kwarg `new?` ended the run; trace lost (6 model calls before it, from the log). | tool_use |
| pm:42 | reassign yuki's In Progress tasks to carlos | **C0.** Invented yuki@example.com; found nothing. | tool_use (planning) |
| pm:64 | give yuki carlos's overdue unstarted tasks (none) | **C0.** Request timed out after retries (880.7 s); trace lost, 2 model calls preceded it (from the log). | infrastructure |
| crm:60 | delete Sofia's Won/Services customers | **C0.** Dropped the Sofia filter; deleted 5 other reps' customers. | reasoning |
| crm:74 | hardware proposals with no reply for 6 weeks → Lost | **C0.** Correct updates, but step 0 called `crm_search_customers`, which the scorer rejects. | tool_use |

## 2. Failure mix, C0 vs C6

| label | C0, discordant (n=10) | C6, discordant (n=15) | C0, all failures (n=37) | C6, all failures (n=42) |
|---|---|---|---|---|
| tool_use | 6 | 9 | 14 | 16 |
| reasoning | 1 | 2 | 14 | 15 |
| planning | 1 | 1 | 3 | 4 |
| control_flow | 0 | 2 | 2 | 3 |
| outcome | 1 | 0 | 1 | 0 |
| memory | 0 | 1 | 0 | 1 |
| infrastructure | 1 | 0 | 3 | 3 |
| multilingual (primary) | – | 0 | – | 0 |
| multilingual (secondary) | – | 1 | – | 2 |
| *non-infrastructure failures* | *9* | *15* | *34* | *39* |

**What tool_use is made of** (counts from `failure_labels.csv`):

| tool_use subtype | C0 (14) | C6 (16) |
|---|---|---|
| invented address (`@example.com`) | 10 | 5 |
| bad kwarg → run ended, trace lost | 2 | 5 |
| invalid tool name rejected by the scorer | 1 | 1 |
| invented or empty optional fields in `add_customer` | 0 | 3 |
| plot type (bar for "distribution") | 1 | 1 |
| wrong search field | 0 | 1 |

- An invented address is the decisive error in 10 C0 and 6 C6 failures (the C6 count includes pm:2, labelled memory). It hits different tasks on each side: 4 of the 15 C6-only failures are the four C6 email failures, and 4 of the 10 C0-only failures are this same error.
- Bad kwargs on any attempt (final runs plus the first attempts of re-run rows): C0 3 tasks (pm:28, md:200, and analytics:105, whose first attempt used `traffic_source?`); C6 8 tasks (analytics:43, crm:46, crm:53, crm:57, pm:28, pm:30, pm:49, md:130). The corrupted names (`new?`, `newvalue`, `traffic_source?`) look like a decoding glitch rather than a language effect: the schema is English in both conditions, and the same `new?` occurs in C0. The same `?` corruption appears in argument values on both sides (C0 crm:42 "lara?", crm:57 "akira.sate?"; C6 pm:60 "aisha.??").

**What the one-sided failures are about.**
- C6-only (15): 9 are tool_use (4 invented addresses in email, 1 more in pm:72, 2 bad kwargs, 1 invalid tool name, 1 empty optional fields). The others: 2 control_flow (calendar:20 asks the user, analytics:105 empty answer), 1 memory (pm:2), 1 planning (analytics:54 plotted despite a false condition), and 2 reasoning (analytics:42 single day, crm:77 missing status filter).
- C0-only (10): 6 tool_use (4 invented addresses, 1 bad kwarg, 1 invalid tool name), 1 outcome (email:36), 1 planning (calendar:38), 1 reasoning (crm:60) and 1 infrastructure (pm:64).
- Only analytics:42 has a plausible language reading (bare "থেকে"). The other 14 C6-only failures are error types that C0 also shows on other tasks. This grouping was made after reading the traces (post hoc), and n is small.

**both_wrong pairs (27).**
- Same primary label in 13/27: analytics:20, analytics:98, analytics:119, calendar:63, calendar:79, calendar:84, crm:20, crm:42, md:102, md:120, md:169, pm:57, and pm:35 (infrastructure on both sides). In 4 of them the two sides made the same write calls (analytics:20, calendar:63 with no write, md:120, md:169).
  - calendar:63: both counted today's 09:30 meeting with Fatima (not yet held at 00:00) as "already met" and booked nothing.
  - calendar:79: both resolved "Wednesday"/"বুধবার" to the past Wednesday 11-29. Both gemma runs made the same error.
  - md:120 and md:169: both resolved "next Friday"/"আগামী শুক্রবার" to 12-01 (GT 12-08).
- Different on each side (14). The pattern repeats: one side uses an invented address or a bad kwarg, and the other makes a reasoning or planning error (email:41, crm:46, crm:57, md:18, md:76, md:149, md:182, md:200, pm:30, pm:60). Other differences: analytics:69 (C0 wrong window, C6 asked to clarify), md:6 (C0 asked for the user's email, C6 booked 09:00 unchecked), md:84 and md:130 (an infrastructure row on one side).

**Shared weak spots (both conditions).**
- **"next Friday"**: 0 of 5 runs that created the task got 12-08 (C0 md:120, md:169; C6 md:120, md:169, md:200). Unlike gemma, gpt-oss makes this error in English too.
- **First free slot tomorrow (GT 13:00)**: no run on either side booked 13:00. 4 runs booked 09:00 without checking the user's own calendar (C0 md:84; C6 md:6, md:102, md:200).
- **Dropped filters** in CRM/PM searches (status=Lead, owner, status=Proposal): C0 crm:42, crm:60, md:182, pm:30; C6 crm:42, crm:77.

**Empty answers.** C0 3/90 (crm:42, crm:57, pm:30), C6 2/90 (analytics:105, pm:60). Unlike gemma, empty answers are not C6-specific here.

**Side effects.** 20/42 C6 failures and 14/37 C0 failures leave no side effect: no write, extra plots or asks, or an errored run. An errored run's trace is lost, so it scores no side effect even if one of its 1–7 earlier calls wrote something (C0 5 such rows, C6 8).

## 3. Language-behaviour scan (all 90 C6 runs)

Method: the same script logic as the gemma C6 scan, run over the C6 trace file. Final answer = `action_input` of the last `Final Answer` step. Tool calls = all non-`Final Answer` trace steps (264, matching the sum of `n_tool_calls` in `per_task_treat.csv`). Bengali script = U+0980–U+09FF; Bengali digits = U+09E6–U+09EF; ASCII digits = `[0-9]`. C0 counts come from the same script on the C0 trace (297 tool calls). The 8 errored C6 rows (3 × 5xx, 5 × bad kwarg) lost their traces (each made 1–7 model calls first, from the log), so 82 C6 runs have steps.

**Final-answer language.**
- 80 of 82 C6 runs with steps produced a non-empty final answer. 2 answers are empty (analytics:105, pm:60). 0 runs hit the iteration limit.
- All 80 answers (100%) contain Bengali script. None is in English (0 answers with zero Bengali letters).
- **English mixing.**
  - 29/80 answers contain Latin letters outside quoted strings, email addresses, plot paths and 8-digit IDs. In 27 of them every Latin word also appears in the run's own task text or tool inputs/outputs (names, titles, status values, "CRM"). The other 2 add an English gloss in brackets: email:41 "(email_id)" and calendar:20 "(Event ID)".
  - 6/80 answers contain an English function word outside quotes (calendar:104, pm:17, pm:18, md:6, md:25, md:94). In all 6 it sits inside an unquoted English title or name (e.g. "Board of Directors Conclave", "Update on Jamie Anderson") or, in md:94, a verbatim copy of the English email body the model sent. So there are 0 clause-level switches.
  - The letter-share heuristic (Bengali letters against ASCII letters, < 80%) flags 28/80 answers. It overcounts because of the English titles and names above.
- C0: all 81 non-empty final answers are English and contain no Bengali characters. 3 answers are empty, 1 run (pm:57) hit the iteration limit, and 5 errored runs have no trace.

**Numerals.**
- 32/80 C6 answers use Bengali digits (০–৯), 365 digits in total. 16 answers write ISO-style dates in Bengali digits (e.g. "২০২৩‑১১‑৩০").
- After removing quoted strings, emails, plot paths and 8-digit IDs, 8 answers still contain ASCII digits:
  - 3 use them only for Markdown list numbers (calendar:65, analytics:21, md:200);
  - 1 is the copied email body (md:94);
  - 4 write a date or quantity in ASCII digits (analytics:32 "28 অক্টোবর থেকে 29 নভেম্বর", analytics:119 a table of ASCII dates and counts, pm:17 "2023‑12‑05", md:182 "21‑এর").
  
  So digit script in prose is mostly, but not always, Bengali (gemma C6: 0 ASCII digits in prose). No answer misreads a number because of its script.
- The BN task texts use ASCII digits (38/90 tasks; 0 use Bengali digits).

**Tool arguments.**
- None of the 264 C6 tool calls has an argument containing Bengali script, so there are also 0 Bengali digits in arguments and 0 numeral_script_error cases.
- 64 BN task texts carry 117 tokens of the form Latin word + hyphen + Bangla suffix (`-এর` 58, `-এ` 40, `-কে` 18, `-গুলো` 1). 0 leaked into arguments: no argument contains Bengali script or a hyphenated `<word>-` form. Names were passed bare or as looked-up addresses.

**Invalid tool names.**
- C6: 3 in 264 calls: crm:38 `crm_search_customers` (step 0), pm:57 `projectmanagement_update_task` (step 11), pm:72 a garbled `project____…We` name (step 6). The tool returned "Tool … not found".
- C0: 2 in 297 calls: crm:74 `crm_search_customers` (step 0), pm:30 a garbled `functions____…We` name (step 8).
- The scorer rejects disallowed tool names ("Rejected disallowed tool name: crm_search_customers.func" etc. in the `compare_conditions.py` output). That alone fails crm:38 (C6) and crm:74 (C0), whose remaining calls matched GT.
- The same invented prefix `crm_` and the same garbling occur in both languages, so they do not suggest a language cause.

## 4. Compared with gemma4:31b

Descriptive only. Sources: the two `metrics.csv` files and the two `failure_labels.csv` files (gemma: `results/comparisons/pilot_ollama-gemma4-31b_c6_vs_c0/`). The two models ran on different days and the gemma analysis has no infrastructure label, so gpt-oss is shown both overall and without infrastructure rows.

| | gemma4:31b | gpt-oss:20b |
|---|---|---|
| C0 completion | 73/90 = 81.1% | 53/90 = 58.9% |
| C6 completion | 74/90 = 82.2% | 48/90 = 53.3% |
| Δ (95% CI), McNemar p | +1.1 pp (−7.8, +10.0), p = 1.0 | −5.6 pp (−16.7, +5.6), p = 0.4244 |
| ref_only / treat_only / both_wrong | 7 / 8 / 9 | 15 / 10 / 27 |
| Side effects C0 / C6 | 16.7% / 8.9% | 25.6% / 24.4% |
| Analytics domain Δ | −20.0 pp (3 / 0) | −26.7 pp (4 / 0) |
| Labelled failures C0 / C6 | 17 / 16 | 37 / 42 (non-infrastructure 34 / 39) |

Failure mix, all labelled failures (share of the column):

| label | gemma C0 (17) | gemma C6 (16) | gpt-oss C0 (37) | gpt-oss C6 (42) | gpt-oss C0, non-infra (34) | gpt-oss C6, non-infra (39) |
|---|---|---|---|---|---|---|
| reasoning | 11 (65%) | 10 (63%) | 14 (38%) | 15 (36%) | 14 (41%) | 15 (38%) |
| tool_use | 1 (6%) | 2 (13%) | 14 (38%) | 16 (38%) | 14 (41%) | 16 (41%) |
| planning | 4 (24%) | 2 (13%) | 3 (8%) | 4 (10%) | 3 (9%) | 4 (10%) |
| control_flow | 1 (6%) | 2 (13%) | 2 (5%) | 3 (7%) | 2 (6%) | 3 (8%) |
| outcome / memory | 0 | 0 | 1 / 0 | 0 / 1 | 1 / 0 | 0 / 1 |
| infrastructure | – | – | 3 (8%) | 3 (7%) | – | – |
| multilingual primary / secondary | 0 / 0 | 0 / 3 | 0 / 0 | 0 / 2 | 0 / 0 | 0 / 2 |

- gemma's failures are mostly reasoning (about two thirds on both sides). gpt-oss's non-infrastructure failures split about evenly between reasoning and tool_use on both sides. Most of that tool_use comes from invented addresses and corrupted kwargs. Neither causes a gemma failure: gemma has 1 run per side with an `@example.com` argument and 0 bad-kwarg errors.
- Within each model, the C0 and C6 mixes are close. Neither model has a failure labelled primarily multilingual.
- Tasks failed in some form by both models: calendar:79 (all 4 runs, past Wednesday), crm:42 (gemma C0, both gpt-oss), md:120 (gemma C6, both gpt-oss; "next Friday" → 12-01), analytics:119 (gemma C6, both gpt-oss; the 4-week window), md:149 (the 5-result search cap in gemma C0 and gpt-oss C6), md:182 (all 4 runs), and email:41.
  - email:41: both models' C6 runs read "গত সপ্তাহে" as the past 7 days (11-23..11-29). Both C0 runs used a calendar week; gpt-oss C0 still failed, on an invented address.
- Both models lose most in the analytics domain under C6, with 0 treat_only analytics pairs in each. The failed tasks differ (gemma: analytics:20, :98, :119; gpt-oss: analytics:42, :43, :54, :105). At 15 tasks per domain this is a hypothesis, not a finding.

## 5. Conclusions (preliminary: n = 90, one model, one run per side; see Threats)

- **No C6 failure is clearly language-induced. Primary label `multilingual`: 0/42** (0/39 excluding infrastructure). 13 of the 27 both_wrong pairs have the same primary label on both sides. The 15 C6-only failures are the same error types (invented addresses, bad kwargs, invalid tool names, dropped filters, asks and empty answers) that C0 shows on other tasks.
- **Two C6 failures carry `multilingual` as a weak secondary label:**
  - analytics:42: "2023-11-10 থেকে" was read as one day. This is weak, because the same construction gave full ranges in analytics:0 and :32 in this run.
  - email:41: "গত সপ্তাহে" was read as the past 7 days. gemma's C6 run did the same, which makes it the most consistent BN-specific reading across the two models. It is still weak, because English "last week" is also ambiguous. *Action: the owner should review the BN wording (e.g. "গত সপ্তাহে" → "আগের সপ্তাহে (সোম–রবি)").*
- **Completion:** C6 is 5.6 pp lower (53.3% vs 58.9%), but the 95% CI (−16.7 to +5.6 pp) includes 0 and p = 0.4244. Excluding infrastructure pairs (S1) gives −7.1 pp (CI −17.6 to +4.7, p = 0.3075). Counting recovered re-runs as failures (S2) leaves Δ at −5.6 pp. At this n, a gap of 5–10 points cannot be detected or ruled out.
- **The C6 deficit is concentrated in tool_use** (9 of 15 C6-only failures vs 6 of 10 C0-only).
  - Its biggest parts, invented addresses (10 C0 vs 6 C6 failures overall) and corrupted kwargs (3 vs 8 tasks on any attempt), occur in both languages and land on different tasks in each run. This looks like run-to-run variability of gpt-oss.
  - The bad-kwarg excess in C6 (8 vs 3 tasks) is the one pattern worth testing with repeated runs (k ≥ 3).
- **Side effects are about equal:** 24.4% vs 25.6% (Δ −1.1 pp, CI −11.1 to +8.9). C6 failures more often leave no side effect (20/42 vs 14/37), partly because 8 C6 errored runs (5 bad kwargs, 3 × 5xx) lost their traces after 1–7 model calls, so any writes they made are not recorded (C0: 5 such runs).
- **Forced-Bangla output works at the surface level:**
  - 80/80 non-empty answers are in Bangla, with English only as borrowed names and titles (plus 2 bracketed glosses).
  - No Bangla text or case marker reaches a tool argument.
  - Prose digits are mostly Bengali (4 answers keep some ASCII numbers).
  - Invalid tool names are as rare as in C0 (3/264 vs 2/297).
- **Shared weaknesses dominate both conditions:** "next Friday" (0/5 correct, English too), the first free slot (0 runs booked 13:00), past-vs-upcoming weekdays, and dropped search filters.

## Threats to validity

- **Different days.** C0 ran on 2026-10-05. C6 ran 2026-10-05/06 (67 rows). The last row was saved at about 00:28 on 2026-10-06, and the free-tier monthly limit (HTTP 429) stopped the run at about 03:52 the same day. About one day later, the last 23 rows ran from 05:53 on 2026-10-07 with a new API key (same model and tier). Provider-side drift between and within runs cannot be excluded. `run_date` in `per_task_treat.csv` shows 2026-10-07 for all 90 rows because it comes from the finishing invocation's `started_at`.
- **Both runs were resumed after interruptions.** A resume re-runs errored rows, so some rows got a second attempt (C0 2, C6 9). S2 brackets this; the first attempts' requests are not in 381/346.
- **Provider failures:** 6 infrastructure rows (3 per side) plus 71 HTTP 5xx and 54 timeout retries absorbed by the harness. S1 brackets the rows, not any latency effect on the rest.
- **Single LLM annotator** (`model:claude-opus-5-5`), not yet human-checked. The label boundaries (tool_use vs planning for invented addresses; infrastructure vs model for stalls) are judgement calls, documented above and in `notes`.
- **Unreviewed Bangla prompt and task translations.**
- **n = 90, one run per side, one model.** No repeated runs, so there is no measured noise floor. The many one-sided invented-address and bad-kwarg failures suggest that run-to-run variability for gpt-oss:20b is large compared with the observed Δ.
