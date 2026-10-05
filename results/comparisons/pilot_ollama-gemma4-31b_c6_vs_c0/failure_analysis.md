# Pilot failure analysis: WorkBench, gemma4:31b, C6 (BN task text and system prompt, EN tools, replies forced to Bangla) vs C0 (all English)

90 paired tasks (15 per domain). C0 73/90 correct, C6 74/90. 15 discordant pairs (8 treat_only = c6 right and c0 wrong, 7 ref_only = c0 right and c6 wrong; McNemar p = 1.0) and 9 both_wrong. Every failed run in those 24 pairs was labelled: 17 C0 rows and 16 C6 rows, in `failure_labels.csv` in this folder. Annotator: `model:claude-opus-5-5` (single annotator, not yet human-checked). The BN task translations and the BN system prompt have not yet been reviewed by the owner.

The C0 run is the same run (2026-10-04 11:42:18) used in the C1 comparison, so its 17 labels were reused after re-checking each against the trace. Changes: notes now describe the C6 side, three step indices were moved to the step the evidence quotes (crm:42 → 3, crm:46 → 2, md:102 → 5), and the analytics:69 note now says that only `time_min` fails (the scorer accepts `time_max` 2023-11-30). No primary or secondary label changed.

C6 prompt (`system_prompt_sent` in the C6 meta): the Bangla date/time and meeting-hours prefix, then "do not ask for confirmation; act immediately; do not stop after a search step", then "টাস্ক যে ভাষাতেই লেখা হোক না কেন, ইউজারকে সবসময় বাংলায় উত্তর দিও" (always answer the user in Bangla, whatever the task language). Tool schemas are English.

**Labels** (schema.md §4, adapted from BabelArena):
- *outcome*: right process, wrong value written.
- *reasoning*: wrong inference about the task or data.
- *planning*: missing, extra or misordered steps.
- *tool_use*: wrong tool, or wrong or malformed arguments.
- *control_flow*: stopped early, looped, hit the step limit, or asked for confirmation.
- *memory*: lost information obtained earlier in the trace.
- *multilingual*: the failure is attributable to the instruction language. Subtypes: wrong_language_output, language_mixing, numeral_script_error, language_induced_tool_misuse.

## 1. Discordant pairs

| task_uid | EN task (short) / BN wording at issue | Failed side: what went wrong | Label (secondary) |
|---|---|---|---|
| email:41 | forward Anaya's "last week" emails to Nadia / "গত সপ্তাহে" | **C6.** Searched 11-23..11-29 (C0: calendar week 11-19..11-26). A later unfiltered search found both 11-20/11-21 emails, but the model ruled them "not last week" and asked the user what to do. | reasoning (control_flow, multilingual) |
| analytics:20 | "plot the distribution of" engaged users and visits / "ডিস্ট্রিবিউশন … চার্টে দেখিয়ে দাও" | **C6.** `plot_type="line"` instead of histogram (C0: histogram). The same BN wording in analytics:15 (one day) gave a histogram. | tool_use (multilingual) |
| analytics:98 | growth of session duration "since Wednesday"; plot if > visits (condition false) | **C6.** Measured growth from Tue 11-28 to Wed 11-29, read +0.9% duration vs −47% visits as "grew more" and plotted both. | reasoning |
| analytics:119 | bar charts "over the last 4 weeks" / "গত 4 সপ্তাহের" | **C6.** Used 10-26 as start (5 weeks; GT 11-02). The answer says "গত ৪ সপ্তাহের", so the number was read correctly; "গত 2 সপ্তাহ" and "গত 1 সপ্তাহে" were resolved correctly in this run. | reasoning |
| crm:77 | move software proposals with no reply for 6 weeks to Lost (none qualify) | **C6.** Moved 00000147 (last contact 10-29, ~4.5 weeks) to Lost, claiming ≥ 6 weeks. C0 made the same update, then reverted it. Also called the non-existent `customer_relationship_manager_update_task`. | reasoning (tool_use) |
| md:84 | Olga overdue → meeting at earliest free slot tomorrow | **C6.** Booked 15:00 although 13:00 was free ("আপনি দুপুর ৩টার পর ফ্রি আছেন"). C0 booked 13:00. | reasoning |
| md:120 | task due "next Friday" / "আগামী শুক্রবার" | **C6.** Due date 12-01 (tomorrow), stated as "আগামী শুক্রবার (১ ডিসেম্বর, ২০২৩)"; GT 12-08. The idiomatic Bangla reading is "the coming Friday". The same phrase gave 12-08 in md:169 and md:200 in this run. C0 gave 12-08 in 4/4 "next Friday" tasks. | reasoning (multilingual) |
| calendar:63 | catch-up with Fatima at first free slot | **C0.** Booked 11:00, inside a 10:00–12:00 event. | reasoning |
| pm:28 | move Nia's overdue backlog tasks | **C0.** Treated a task due today as overdue; the final answer contradicts itself. | reasoning |
| crm:42 | reassign Nadia's training *leads* to Lena (none exist) | **C0.** Dropped the status=Lead filter and reassigned 5 Won/Lost/Proposal customers. C6 ran the same unfiltered search but changed nothing. | reasoning |
| crm:46 | reassign Lena's hardware *leads* to Akira | **C0.** Ignored "leads" (moved a Lost and a Won customer). The unfiltered search hit the 5-result cap, so one lead was never retrieved. C6 searched with status=Lead. | reasoning (planning) |
| crm:57 | "Give Akira all of Nadia's … customers in the crm" | **C0.** Emailed Akira a list instead of reassigning the customers. | reasoning (tool_use) |
| md:6 | meeting at first free slot with Jamie Anderson's owner | **C0.** Booked busy 12:00, then created the correct 13:00 event before deleting the wrong one, so the event ID no longer matched (a scoring artefact). | planning (reasoning) |
| md:102 | meeting at earliest free slot tomorrow | **C0.** Booked a busy 12:00 slot, deleted it, then rebooked 15:00, skipping the free 13:00 slot. | reasoning (planning) |
| md:130 | conditional backlog task (condition false) | **C0.** Created the task before evaluating the condition. C6 checked first and did nothing. | planning (reasoning) |

## 2. Failure mix, C0 vs C6

| label | C0, discordant (n=8) | C6, discordant (n=7) | C0, all failures (n=17) | C6, all failures (n=16) |
|---|---|---|---|---|
| reasoning | 6 | 6 | 11 | 10 |
| planning | 2 | 0 | 4 | 2 |
| tool_use | 0 | 1 | 1 | 2 |
| control_flow | 0 | 0 | 1 | 2 |
| outcome / memory | 0 | 0 | 0 | 0 |
| multilingual (primary) | – | 0 | – | 0 |
| multilingual (secondary) | – | 3 | – | 3 |

**What the one-sided failures are about.**
- C6-only (7): 2–3 are relative-date resolution errors — "গত সপ্তাহে" (email:41), "গত 4 সপ্তাহের" (analytics:119), "আগামী শুক্রবার" (md:120). analytics:98 ("বুধবার থেকে") is not counted: it resolved the weekday correctly (11-29) and its error was the baseline day. The others are a plot type (analytics:20), a 6-week cutoff (crm:77) and a free-slot error (md:84), plus analytics:98.
- C0-only (8): none is a relative-time resolution error. 3 are CRM "leads" or reassignment misreadings (crm:42, crm:46, crm:57), 3 are free-slot errors (calendar:63, md:102, and md:6, which is a scoring artefact), 1 is due-today-as-overdue (pm:28) and 1 is a condition checked too late (md:130).
- This grouping was made after reading the traces (post hoc), and n is small. C0 resolved the same four phrases correctly in English. Within C6, the trace evidence cuts against a language cause in each case:
  - analytics:98 dated Wednesday correctly (11-29) and erred on the baseline day.
  - analytics:119 restated "৪ সপ্তাহ" and got the 1- and 2-week windows right.
  - md:120's phrase gave 12-08 in 2/2 other tasks.
  - email:41's "last week" is equally ambiguous in English.

**both_wrong pairs (9).**
- Same primary label in 6/9 (calendar:79, analytics:69, pm:64, md:18, md:182, md:200). In 4 of them the two sides made exactly the same write calls (analytics:69, pm:64, md:18, md:182).
  - calendar:79: both resolved "Wednesday"/"বুধবার" to the past Wednesday 11-29. C0 deleted one event, C6 deleted two.
  - md:200: both picked a busy slot (C0 11:00, C6 12:00). Both set the deadline correctly (12-08).
- Different on each side (3):
  - analytics:76: C0 looped to the iteration limit (control_flow). C6 found the condition false, said so, and plotted anyway (planning).
  - crm:74: C0 applied a wrong cutoff (reasoning). C6 returned an empty response on its first turn (control_flow).
  - md:149: C0 missed a lead beyond the 5-result cap (planning). C6 returned an empty response after two lookups (control_flow).

**Calendar free-slot reasoning remains the main shared weak spot:** 5 failed runs (C0 3: calendar:63, md:102, md:200; C6 2: md:84, md:200), plus the C0 md:6 ordering artefact.

**Empty responses are new in C6.** 2/90 C6 runs ended on an empty assistant message with no tool call (crm:74 at step 0, md:149 at step 2). C0 had 0/90. The trace shows no cause.

## 3. Language-behaviour scan (all 90 C6 runs)

Method: a script over the C6 trace file. Final answer = `action_input` of the last `Final Answer` step. Tool calls = all non-`Final Answer` trace steps (285, matching the sum of `n_tool_calls` in `per_task_treat.csv`). Bengali script = U+0980–U+09FF; Bengali digits = U+09E6–U+09EF; ASCII digits = `[0-9]`. C0 counts come from the same script on the C0 trace.

**Final-answer language.**
- 88 of 90 C6 runs produced a non-empty final answer. 2 answers are empty (crm:74, md:149). 0 runs hit the iteration limit.
- All 88 answers (100%) contain Bengali script. None is in English (0 answers with zero Bengali letters).
- **English mixing.**
  - 62/88 answers contain Latin letters outside quoted strings, email addresses and plot paths. Every one of those Latin words also appears as a token in the run's own task text or tool inputs/outputs: entity names, task and event titles, status values (`Lost`, `Backlog`), "CRM", "ID". So these are borrowings, not code-switching.
  - 5/88 answers contain an English function word outside quotes (pm:30, pm:49, pm:60, pm:64, md:84). In all 5 the word sits inside an unquoted English task or event title (for example "Fix bug in data storage module"), so there are 0 clause-level switches.
  - A letter-share heuristic (Bengali code points U+0981–U+09E3/U+09F0–U+09FE against ASCII letters, < 80%) would flag 61/88 answers as "mixed". It overcounts because of the long English titles and names above.
- Names are sometimes transliterated into Bangla script (e.g. pm:64 "কার্লোসের", "ইউকি-র"). This was not counted.
- C0: all 89 non-empty final answers are English and contain no Bengali characters. 1 run (analytics:76) hit the iteration limit with no final answer.

**Numerals.**
- 51/88 C6 answers use Bengali digits (০–৯), 366 digits in total.
- After removing quoted strings, emails, plot paths and 8-digit IDs, 0 ASCII digits remain in the prose. So every date, time and quantity in the prose is written in Bengali digits, including ISO-style dates (e.g. "২০২৩-১১-৩০", in 10 answers). IDs, paths and quoted strings stay ASCII, which is correct.
- The BN task texts use ASCII digits (38/90 tasks; 0 use Bengali digits). The model read them correctly. The one numeric slip (analytics:119, 4 weeks → 5) shows the number restated correctly as "৪".

**Tool arguments.**
- None of the 285 C6 tool calls has an argument containing Bengali script, so there are also 0 Bengali digits in arguments and 0 numeral_script_error cases.
- 64 BN task texts carry 117 tokens of the form Latin word + hyphen + Bangla suffix (`-এর` 58, `-এ` 40, `-কে` 18, `-গুলো` 1). They appear on names (`nadia-কে`, `Raj-এর`) and on English nouns (`CRM-এ`, `backlog-এ`, `lead-গুলো`). 0 leaked into arguments: no argument contains Bengali script or the hyphenated `<word>-` form. Names were passed bare (`"nadia"`, `"Sofia"`).

**Invalid tool names.**
- There was exactly 1 invalid tool name in 285 C6 calls, in crm:77 at step 1: `customer_relationship_manager_update_task(field="status", new_value="Lost", task_id="00000147")`.
  - The tool returned "Tool … not found". The model then made a valid `update_customer` call.
  - Scoring rejects it too: `WARNING: Rejected disallowed tool name: customer_relationship_manager_update_task.func` appears at lines 634–635 of `results/logs/pilot/c6_ollama-gemma4-31b_2026-10-05_16-12-02.log`.
- The name combines the CRM prefix with project_management's `update_task` and `task_id`. That pattern does not suggest a language cause.
- C0 had 0 invalid tool names in 356 calls.

## 4. Conclusions (preliminary: n = 90, one model, one run per side, C0 and C6 on different days, translations not yet reviewed by the owner, single LLM annotator)

- **No C6 failure is clearly language-induced. Primary label `multilingual`: 0/16.** Six of the 9 both_wrong pairs have the same primary label on both sides. Four of them have identical write calls. The C6-only failures are the same kinds of reasoning, tool and slot errors that C0 shows elsewhere.
- **Three C6 failures carry `multilingual` as a secondary label** (3/7 C6-only failures):
  - md:120, "আগামী শুক্রবার" → 12-01. This is the strongest case: the answer states the reading explicitly, and the Bangla phrase idiomatically means "the coming Friday". It is not primary because the same run resolved the phrase to 12-08 in 2/2 other tasks with a deadline. *Action: the owner should review the BN wording for "next Friday" (e.g. "পরের সপ্তাহের শুক্রবার").*
  - email:41, "গত সপ্তাহে" read as the past 7 days. This is plausible but weak, because English "last week" is equally ambiguous.
  - analytics:20, "ডিস্ট্রিবিউশন … চার্টে দেখিয়ে দাও" → line plot. This is weak, because the same wording gave a histogram in analytics:15.
- **The one C6-specific pattern is relative-time resolution:** 2–3 of 7 C6-only failures (email:41, analytics:119, md:120; analytics:98 is not counted, because it resolved the weekday correctly and its error was the baseline day) vs 0 of 8 C0-only failures. This grouping is post hoc and each case has a non-language explanation, so it is a hypothesis for repeated runs (k ≥ 3), not a finding.
- **Overall, the failure mix is very similar:** reasoning 11 C0 vs 10 C6, planning 4 vs 2, tool_use 1 vs 2, control_flow 1 vs 2.
  - No detectable difference in completion: Δ = +1.1 pp, 95% CI −7.8 to +10.0 pp.
  - C6 has fewer side effects: 8.9% vs 16.7% (Δ −7.8 pp, 95% CI −15.6 to +0.0 pp). 8/16 C6 failures leave no side effect (wrong or extra plots, empty responses, no action), against 2/17 C0 failures.
  - At this n, an effect of a few points cannot be detected or ruled out.
- **Forced-Bangla output works at the surface level:**
  - 88/88 non-empty answers are in Bangla, with English only as borrowed names and titles.
  - All prose numbers are in Bengali digits.
  - No Bangla text or case marker reaches a tool argument.
  - There is 1 invalid tool name in 285 calls.
- **The new C6 behaviour is 2 empty responses** (2/90 vs 0/90). Watch for it in repeated runs.
