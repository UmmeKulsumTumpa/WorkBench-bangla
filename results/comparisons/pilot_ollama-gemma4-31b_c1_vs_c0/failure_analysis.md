# Pilot failure analysis: WorkBench, gemma4:31b, C1 (BN task text, EN system prompt and tools)

90 paired tasks (15 per domain). EN 73/90 correct, BN 74/90. 13 discordant pairs (6 en_only, 7 bn_only, McNemar p = 1.0) and 10 both_wrong. Every failed run in those 23 pairs was labelled: 17 EN rows and 16 BN rows, in `workbench_pilot_ollama-gemma4-31b_c1/failure_labels.csv`. Annotator: `model:claude-opus-5-5` (single annotator, not yet human-checked). The BN translations have not yet been reviewed by the owner.

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
| email:41 | forward Anaya's "last week" emails to Nadia / "গত সপ্তাহে" | **BN.** Read "last week" as 11-23..11-29 (EN read it as 11-19..11-26), got `[]`, then repeated the identical search 19 times until the iteration limit. | control_flow (reasoning) |
| analytics:20 | "plot the distribution of" engaged users and visits / "ডিস্ট্রিবিউশন … চার্টে দেখিয়ে দাও" | **BN.** Used `plot_type="line"` instead of histogram. The same BN wording in analytics:15 gave a histogram. | tool_use |
| crm:38 | "moving Taylor Jackson to Raj" / "Taylor Jackson-এর দায়িত্ব … Raj-কে" | **BN.** Treated the customer as an employee, looked them up in the directory, then gave up and asked the user. EN *and* BN made the same misreading on sibling crm:32, which scored correct only because its ground truth is a no-op. | reasoning (control_flow) |
| crm:77 | move software proposals with no reply for 6 weeks to Lost (none qualify) | **BN.** Moved 00000147 (last contact 4.5 weeks ago) to Lost: "প্রায় ৪ সপ্তাহ, তবে আপনার নির্দেশ অনুযায়ী…" ("about 4 weeks, but as you instructed…"). EN made the same update and then reverted it. Also called a non-existent tool `customer_relationship_manager_update_task`. | reasoning (tool_use) |
| md:84 | Olga overdue → meeting at earliest free slot tomorrow | **BN.** Booked 15:00 although 13:00 was free. | reasoning |
| md:169 | task due "next Friday" / "আগামী শুক্রবার" | **BN.** Set the deadline to 12-01 (tomorrow); ground truth is 12-08. In Bangla, "আগামী শুক্রবার" idiomatically means *the coming* Friday, but the model resolved the same phrase to 12-08 in 3 other BN tasks. | reasoning (multilingual) |
| calendar:63 | catch-up with Fatima at first free slot | **EN.** Booked 11:00, inside a 10:00–12:00 event. | reasoning |
| pm:28 | move Nia's overdue backlog tasks | **EN.** Treated a task due today as overdue; the final answer contradicts itself. | reasoning |
| crm:42 | reassign Nadia's training *leads* to Lena (none exist) | **EN.** Dropped the status=Lead filter and reassigned 5 Won/Lost/Proposal customers. | reasoning |
| crm:46 | reassign Lena's hardware *leads* to Akira | **EN.** Ignored "leads" (moved a Lost and a Won customer). The unfiltered search hit the 5-result cap, so one lead was never retrieved. | reasoning (planning) |
| crm:57 | "Give Akira all of Nadia's … customers in the crm" | **EN.** Emailed Akira a list instead of reassigning the customers. | reasoning (tool_use) |
| md:102 | meeting at earliest free slot tomorrow | **EN.** Booked a busy 12:00 slot, deleted it, then rebooked 15:00, skipping the free 13:00 slot. | reasoning (planning) |
| md:200 | task + meeting at earliest free slot | **EN.** Booked 11:00 (busy). The BN run self-corrected to 13:00. | reasoning |

## 2. Failure mix, EN vs BN

| label | EN, discordant (n=7) | BN, discordant (n=6) | EN, all failures (n=17) | BN, all failures (n=16) |
|---|---|---|---|---|
| reasoning | 7 | 4 | 11 | 9 |
| planning | 0 | 0 | 4 | 3 |
| tool_use | 0 | 1 | 1 | 2 |
| control_flow | 0 | 1 | 1 | 2 |
| outcome / memory | 0 | 0 | 0 | 0 |
| multilingual (primary) | – | 0 | – | 0 |
| multilingual (secondary) | – | 1 | – | 1 |

In 9 of the 10 both_wrong pairs, the two sides have the same primary label. In 7 of them, the two sides made exactly the same wrong calls or ran the same loop.
- **Recurring patterns:**
  - "Wednesday" resolved to the past Wednesday instead of the coming one (calendar:79).
  - A plot date range off by one day (analytics:69).
  - Looping until the step limit (analytics:76).
  - A task due today treated as overdue (pm:64).
  - Miscounting the person with the fewest tasks (md:18).
  - A conditional action executed before its condition was checked (md:130).
  - Missing records beyond the 5-result search cap (md:149, md:182).
- **Different on each side:**
  - crm:74: EN applied a wrong cutoff, while BN found the right candidates but applied no cutoff.
  - md:6: EN booked the right time, but created the new event before deleting the wrong one, so the event ID no longer matched (a scoring artefact). BN picked a busy slot.

The dominant shared weakness is calendar free-slot reasoning: 6 failed runs across both languages (EN 4, BN 2).

## 3. Language-behaviour scan (all 90 BN runs)

**Final-answer language.**
- 88 of 90 BN runs produced a final answer; 2 hit the iteration limit (email:41, analytics:76).
- All 88 answers (100%) are in Bangla. No answer is in English, and none switches language at the clause level: outside quotes and code there are zero English function words.
- 67/88 answers contain English tokens outside quotes. These are entity names, task and event titles, status values (`Lost`, `Lead`), "CRM" and IDs, so they are borrowings rather than language mixing. A letter-share heuristic (<80% Bengali letters) would flag 31/88 as "mixed"; on inspection, all 31 are Bangla sentences with embedded English names.
- Fatima's name was transliterated into Bangla script (ফাতিমা/ফাতেমা) in a few answers.
- All 89 EN final answers are English and contain no Bengali characters.

**Numerals.**
- 52/88 BN answers use Bengali digits (০–৯), 346 digits in total.
- Every date and quantity outside IDs, file paths, emails and quoted strings is written in Bengali digits: 0 ASCII exceptions.
- IDs and paths stay in ASCII, which is correct.
- The BN task texts use ASCII digits (38/90 tasks), and the model read them correctly.

**Tool arguments.**
- None of the 345 BN tool calls has an argument containing Bengali script (U+0980–U+09FF). There are also no Bengali digits in arguments, so there are 0 numeral_script_error cases.
- 60 BN task texts carry 76 Latin names with a Bangla case marker attached (`leila-এর`, `nadia-কে`, `Raj-কে`). Every one was passed to the tools as the bare name (`"nadia"`, `"Raj"`): 0 case-marker leaks.

**Invalid tool names.**
- There was exactly 1 invalid tool name in 180 runs (701 tool calls), in BN crm:77, step 1: `customer_relationship_manager_update_task(field="status", new_value="Lost", task_id="00000147")`.
- This is the source of `WARNING: Rejected disallowed tool name: customer_relationship_manager_update_task.func` (lines 693–694 of `results/logs/pilot/c1_ollama-gemma4-31b_2026-10-04.log`). It was rejected, and the model then made a valid `update_customer` call.
- The name combines the CRM prefix with project_management's `update_task` and `task_id`. That pattern does not suggest a language cause.
- The EN runs had 0 invalid tool names.

## 4. Conclusions (preliminary: n = 90, one model, one run per side, translations not yet reviewed by the owner, single LLM annotator)

- **No BN failure is clearly language-induced. Primary label `multilingual`: 0/16.** The BN-only failures are the same kinds of reasoning, tool and loop errors that the EN side shows elsewhere. The clearest example is crm:77, where EN made the identical wrong update and then undid it.
- **One BN failure is a plausible translation-level effect: md:169, "আগামী শুক্রবার" → 12-01.** The Bangla phrase idiomatically means "the coming Friday", so the BN run can be defended against the WorkBench convention (next week's Friday). It was coded `multilingual` as a secondary label only, because the model resolved the same phrase to 12-08 in 3/3 other BN tasks. *Action: the owner should review the BN wording for "next Friday" (for example "পরের সপ্তাহের শুক্রবার", "Friday of next week").*
- **Two other BN failures could be tied to wording but are contradicted within the pilot.**
  - analytics:20 ("চার্টে দেখিয়ে দাও" → line plot): the same wording produced a histogram in analytics:15.
  - crm:38 (genitive "-এর দায়িত্ব"): the same misreading happened in English on crm:32.
  - Both are worth flagging in the translation review. Neither should count as language-induced yet.
- **The failure mix is very similar across languages:** reasoning 11 EN vs 9 BN, planning 4 vs 3, tool_use 1 vs 2, control_flow 1 vs 2. BN is not worse on completion (Δ = +1.1 pp, 95% CI −6.7 to +8.9 pp). The discordant pairs look like run-to-run randomness around shared weak spots (free-slot finding, "overdue" vs due-today, the "leads" filter, the 5-result search cap), not a language effect. At this n, an effect of a few points cannot be detected or ruled out.
- **gemma4:31b behaves well in Bangla at the surface level.** It always answers in Bangla, writes numbers consistently in Bengali digits, never passes Bangla text or case markers into tool arguments, and made 1 invalid tool name in 345 BN calls. Repeated runs (k ≥ 3) and a C2 condition are needed before this can count as a robust result.
