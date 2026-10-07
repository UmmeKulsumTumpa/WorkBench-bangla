# Annotation rules and statistics definitions: WorkBench failure analysis (C0 vs C6)

Binding for every annotator, second reviewer and adjudicator. It maps the owner's pipeline (`instructions/failure_analysis_pipeline.md`) onto WorkBench. English = condition C0 (all English). Bangla = condition C6 (Bangla task and system prompt, English tool descriptions, replies forced to Bangla). There is no C7. Models: `ollama-gemma4-31b` and `ollama-gpt-oss-20b`, on the 90-task pilot. One run per side; no repeats.

## Inputs and conventions

- **Task table:** `results/failure_pipeline/pilot_<M>_c6_vs_c0/task_table.csv` (written by `scripts/failure_pipeline.py table`), one row per task: `dataset, model, task_uid, domain, run_id_en, run_id_bn, en_pass, bn_pass, pair_class, en_trajectory, bn_trajectory, en_final_state, bn_final_state, gt_state, en_error, bn_error`. `pair_class` values: `both_correct`, `ref_only` (= EN-pass/BN-fail), `treat_only` (= EN-fail/BN-pass), `both_wrong`.
- **Pass/fail** equals `correct` in `results/comparisons/pilot_<M>_c6_vs_c0/per_task_ref.csv` (EN) and `per_task_treat.csv` (BN); the table command asserts this, and the `pair_class` equality with `paired.csv`, for all 90 rows.
- **Trajectory path** = `<traces json path>#<index>`: the path is relative to the project root and the index is the 0-based position in that JSON list (each entry has `task` and `steps[]` with `llm_input`, `llm_output`, `action`, `action_input`, `observation`). The index is found by matching the task text, not by row order. **The `*_traces.json` files are git-ignored** (`WorkBench/data/results/**/traces*`): they exist only in the working copy, so reports quote short excerpts only and never commit them. An errored gpt-oss row has an entry with zero steps (trace lost).
- **State-changing vs read-only tools:** WorkBench's own definition is `tools_with_side_effects` in `WorkBench/src/tools/toolkits.py:4-19` (calendar create/delete/update_event, email send/delete/forward/reply, analytics.create_plot, project_management create/delete/update_task, customer_relationship_manager update/add/delete_customer), used by the scorer in `WorkBench/src/evals/evaluation.py:118` (`is_exact_match`). Every other tool in `all_tools` (`toolkits.py:21-35`) is read-only. A call to a name that is not in `all_tools` is recorded as `unrecognised`: the executor rejects it (`WorkBench/src/evals/actions.py`) and it changes nothing.
- **`en_final_state` / `bn_final_state` / `gt_state`** are JSON objects `{"state_changing": [...], "read_only": [...], "unrecognised": [...]}` listing the calls in the order executed (from the run CSV `function_calls`; for `gt_state`, the ground-truth `outcome` calls). `correct` means the final database state equals that of the ground-truth calls, so the same state can be reached by different call lists.
- **Errors:** the full error text of an errored row is in `en_error` / `bn_error`.
- **Controlled-vocabulary values in `labels.csv`** are the label text of the numbered lists below, without the number, without the trailing period and, for the failure types, without the explanation after the colon (for example `Wrong tool argument`). `scripts/failure_pipeline.py validate` checks this.

## Annotation rules (WorkBench mapping of the pipeline; Task 1 writes these into `annotation_rules.md` verbatim, then annotators follow them)

- **Unit:** a task pair (same `task_uid` in C0 and C6). Pass = WorkBench `correct` (final database state equals the ground truth). Dataset = WorkBench (single dataset); domain = `source_file`; run ID = run CSV stem.
- **Final state:** summarised as the state-changing calls the run executed versus the ground-truth `outcome` calls (read-only calls listed separately). An errored row whose trace is lost: final state from the CSV `function_calls`, and "trace lost; N model calls preceded the failure (from the log)".
- **Cases (pipeline §3):**
  - all EN-pass/BN-fail pairs get a full trace note (§4 fields) and full labels;
  - **all** EN-fail/BN-fail pairs get labels for both failures (first failure point, failure type, confound, one evidence line each) — the comparison "sample" is the full set, for accuracy;
  - all EN-fail/BN-pass pairs get the same short labels for the English failure, so tool/environment confounds can be filtered symmetrically, plus a one-line "interesting?" note;
  - EN-pass/BN-pass: not analysed (pipeline: "if needed"; not needed).
- **First failure point (§5):** exactly one of the 11 labels, the earliest upstream point after which the correct final state became unreachable — not the last visible error.
- **Failure type (§6):** exactly one of the 9 types.
  - "Dialogue-state failure" applies only if the agent loses or contradicts task state across its own steps (no user turns exist).
  - "Premature abandonment" includes stopping after partial completion of a compound task.
- **Confound (§7):** exactly one of the 7.
  - **Bangla user-simulator error: structurally impossible in WorkBench** (single-turn tasks, no simulator). Never used; decision-tree Step 2 is recorded as "N/A (no user simulator)".
  - **Translation/localization error:** the Bangla task is not faithful to the English one, a protected token (name, email, subject, list/board/status enum) changed, an executable value is wrong, or a Bangla phrasing is ambiguous in a way the English is not, and that difference caused the failure. Compare the two task texts row by row. These judgments are provisional, because the owner's native-speaker review of the translations is still pending.
  - **Tool/environment failure:** the provider or the tool failed despite a reasonable agent action (HTTP 5xx after harness retries, read timeout, connection error, a stall to the time/iteration limit with no model fault visible). A malformed argument (for example a bad keyword argument) is a model error, not tool/environment.
  - **General model weakness present in both English and Bangla:** the failure mechanism has no plausible link to the Bangla input, and the same mechanism class occurs in C0 failures (cite the C0 task_uid).
  - **Genuine Bangla-related agent failure:** the first failure point is linked to reading or acting on the Bangla input (a misread Bangla date/time/quantity phrase, a lost Bangla-stated constraint, a mis-grounded entity from Bangla text, a Bangla-script value leaking into an argument), and the translation is faithful.
  - **Unclear:** no link to the Bangla input and no C0 analogue (possibly run-to-run variance; there are no repeats). Also used when evidence is missing.
- **Decision tree (§8):** record a one-word outcome for each of Steps 1–7 for every EN-pass/BN-fail case. The first step that fails sets the root cause.
- **Evidence (§9):** every labelled failure carries the minimum evidence. For EN-pass/BN-fail this includes "why this is not just a general model failure" (or why it is).
- **Second reviewer (§14):** an independent annotator labels every EN-pass/BN-fail case of both models blind to the first labels (same rules, same inputs). Agreement is reported per field (raw % and Cohen's κ). An adjudicator resolves every disagreement with a written reason; adjudicated labels are final. All three annotators are Claude models, not humans, so this is disclosed and an owner review of a subset is recommended.

## Controlled vocabularies (pipeline sections 5, 6 and 7, copied verbatim)

### First failure point (pipeline section 5)

Use these first-failure-point labels:

1. Instruction understanding.
2. Entity or slot grounding.
3. Task constraint preservation.
4. Planning.
5. Tool selection.
6. Tool-argument construction.
7. Tool execution.
8. Result verification.
9. Premature termination.
10. Final response only.
11. Unclear.

### Failure type (pipeline section 6)

Use this taxonomy:

1. Understanding failure: the agent misunderstood the Bangla request.
2. Planning failure: the agent understood the request but planned the wrong steps.
3. Wrong tool/action: the agent chose the wrong tool or action.
4. Wrong tool argument: the agent chose the right tool but filled incorrect parameters.
5. Execution/environment failure: the tool or environment failed despite a reasonable agent action.
6. Verification failure: the agent acted but did not check whether the goal was satisfied.
7. Premature abandonment: the interaction stopped before the required final action.
8. Dialogue-state failure: the conversation state changed, lost, or contradicted the task.
9. Unclear.

### Confound type (pipeline section 7)

Use this confound taxonomy:

1. Genuine Bangla-related agent failure.
2. Bangla user-simulator error.
3. Translation/localization error.
4. Tool/environment failure.
5. Benchmark/task ambiguity.
6. General model weakness present in both English and Bangla.
7. Unclear.

## `labels.csv` contract

Columns, in this order (UTF-8, comma-separated, `csv` quoting): `task_uid, domain, pair_class, side, first_failure_point, failure_type, confound, decision_tree, evidence, not_general_reason, annotator`.

- `task_uid`, `domain`, `pair_class`: copied from `task_table.csv`.
- `side`: `EN` or `BN`. Rows: EN-pass/BN-fail (`ref_only`) pairs get one `BN` row; EN-fail/BN-fail (`both_wrong`) pairs get an `EN` and a `BN` row; EN-fail/BN-pass (`treat_only`) pairs get one `EN` row; EN-pass/BN-pass pairs get none. One row per (`task_uid`, `side`).
- `first_failure_point`, `failure_type`, `confound`: exactly one label each from the lists above. `Bangla user-simulator error` is never used.
- `decision_tree`: EN-pass/BN-fail rows only (empty otherwise): seven one-word outcomes, exactly `S1=<o>;S2=<o>;S3=<o>;S4=<o>;S5=<o>;S6=<o>;S7=<o>` with `<o>` one of `ok`, `fail`, `na`. Steps follow pipeline section 8: S1 translated task valid, S2 user simulator (always `na`: no user simulator), S3 agent understood the Bangla user, S4 right tool/action, S5 correct arguments, S6 tool/environment executed correctly, S7 completion verified. `fail` means the step's problem applies (for S6, `fail` means the tool or environment did not execute correctly). The first `fail` sets the root cause.
- `evidence`: the section 9 minimum evidence in one or two sentences (English outcome, Bangla outcome, the tool call or message proving the failure, first failure point), with at most short quoted excerpts.
- `not_general_reason`: EN-pass/BN-fail rows only: why this is not just a general model failure (or why it is).
- `annotator`: `A1` (first annotator), `A2` (second reviewer, blind), `ADJ` (adjudicated final).

## Statistics (pipeline §2 and §11; per model, overall and per domain)

- EN rate and BN rate with 95% CIs (Wilson);
- absolute gap EN − BN, with a 95% paired-bootstrap CI;
- MELR = (EN − BN) / EN, with a 95% paired-bootstrap CI (same resamples);
- the four paired counts;
- exact McNemar p, with Holm correction across the two model comparisons;
- effect size: risk difference (the gap) and the paired odds ratio b/c (b = EN-pass/BN-fail, c = EN-fail/BN-pass), with an exact conditional 95% CI (Clopper–Pearson on b/(b+c));
- sensitivity, each a filtered paired analysis:
  - all pairs;
  - removing pairs where any labelled failure has confound "translation";
  - removing "user simulator" (identical to all; stated);
  - removing "tool/environment".

Domain-level numbers are descriptive only (n = 15).

## Adjudication conventions (applied 2026-10-07, after blind double annotation)

The adjudicator (ADJ) wrote these conventions to resolve the rule ambiguities that the second reviewer (A2) reported for gemma4:31b. They refine the rules above and do not replace any wording. They were applied to all 33 gemma4:31b label rows, not only the disputed ones, and they bind later adjudication. Decisions and reasons are in `pilot_<M>_c6_vs_c0/adjudication.csv`.

**C1. First failure point, failure type and decision-tree step are one judgment.** Pipeline §6 says "after finding the first failure point, assign one failure type", and §5 says "do not label only the final visible error". So the type names the failure *at* the first failure point, not the later symptom. For EN-pass/BN-fail rows, the first agent-level `fail` among S3–S7 must be the step that matches both labels:

| First failure point | Failure type | Tree step |
|---|---|---|
| Instruction understanding; Entity or slot grounding | Understanding failure | S3 |
| Task constraint preservation | see the sub-rule below | S3, S4 or S5 |
| Planning | Planning failure | S4 |
| Tool selection | Wrong tool/action | S4 |
| Tool-argument construction | Wrong tool argument | S5 |
| Tool execution | Execution/environment failure | S6 |
| Result verification | Verification failure | S7 |
| Premature termination | Premature abandonment | S7 |
| Unclear | Unclear | none |

- **Which first failure point (including date errors).** Choose by the role of the value and the kind of error.
  - Entity or slot grounding: a phrase is resolved to a different referent that is linguistically available ("last week" read as the past 7 days; "Wednesday" read as the past one; an exclusive "since").
  - Task constraint preservation: a condition, threshold, filter or gate that decides *whether* to act, or *on which entities*, is misread, dropped, or evaluated wrongly. This holds even when the error is arithmetic (a 6-week threshold).
  - Tool-argument construction: a value that was read correctly becomes a wrong argument through computation (date arithmetic, free-slot search, counting).
  - Instruction understanding: the request's action or meaning is misread.
  - Planning: the gate is applied correctly, but to inputs from a wrong plan of steps.
- **Task constraint preservation sub-rule.**
  - Understanding failure (S3): the agent's own words or first action give the constraint a wrong meaning.
  - Dialogue-state failure (S3, the rule's own definition): the agent applied the constraint in an earlier tool call and dropped or contradicted it in a later one.
  - Wrong tool/action (S4): the constraint was read correctly but not applied, or evaluated wrongly, at the write, and the write should not exist.
  - Wrong tool argument (S5): as for Wrong tool/action, but a write was due and it landed on the wrong targets or values.
- **Labels on English rows.** The type labels are used for English rows unchanged ("Understanding failure" = the request was misunderstood).
- **Translation rows.** When S1 fails, the root cause is Translation. The agent-level labels and S3–S7 describe where the shifted value entered, judged against the intended (English/ground-truth) task.

**C2. Reversible errors and "unreachable".** "The earliest upstream point after which the correct final state became unreachable" is judged on the trajectory the agent actually followed. A reversible error that the agent never corrected is the first failure point when it caused the failure; the point of no return is not moved to termination. The first failure point is Premature termination or Result verification only when everything before the stop was correct.

An error the agent corrected is not the first failure point unless it left an irreversible trace in the scored state:
- a call to a nonexistent tool, or any failed call (`is_correct` requires every call to execute);
- a create/send/forward/reply/delete side effect, because IDs and sent items cannot be restored.

**C3. Decision-tree steps after the first fail.** Each step is scored on its own §8 question as observed in the trace (§8 asks for an outcome for each step). This includes errors inherited from an earlier fail: a wrong date from S3 also fails S5's "correct date/time?". Only the first `fail` sets the root cause; later outcomes are descriptive. `na` is used only where a step has nothing to judge:
- S2 is always `na`.
- S5 is `na` when every write is one that should not exist and its arguments carry no error beyond that decision.
- S7 is never `na`. It is `fail` when a required write is missing at termination (premature, partial or abandoned), or when the agent skipped a check of its own write that the paired English run made and that corrected the state. Otherwise it is `ok`.

**C4. Genuine vs General when the Bangla value was read correctly but computed wrongly.** The test is the wrong value, not an echo of the phrase in the final answer.
- **Reading error.** Some reading of the Bangla phrase yields the wrong value, so the error is in reading or acting on the Bangla input. The rows link to the Bangla input: the confound is Genuine if the translation is faithful, and Translation if the Bangla wording created that reading (C5).
- **Computation error.** No reading yields it: the value was read correctly and then computed wrongly (arithmetic, comparison, or computation from observations). This step has "no plausible link to the Bangla input". The confound is General if a C0 failure shows the same computation class (cite the C0 uid), and Unclear otherwise.

**C5. Translation needs a Bangla-introduced reading that this failure used.** Translation/localization error requires two things:
1. The Bangla wording favours, or newly admits, a reading that its English source does not. The same ambiguity in both languages is not a translation error.
2. The observed wrong value is exactly what that reading yields in this trajectory.

It does not require the ambiguity to cause failure every time. If the same run reads the same phrase correctly elsewhere, confidence is lower and the case carries a caveat, but the label stays: labels describe this failure's cause, and there is one run per side. If (1) fails, a misreading of a faithful phrase is Genuine (C4). All translation judgments stay provisional until the owner's native-speaker review.

**C6. Benchmark/task ambiguity (WorkBench definition).** The English source task or its WorkBench ground truth, not the translation and not the agent, puts the ground-truth state out of reach for a reasonable agent. Either:
- (a) the English task admits two or more reasonable readings that lead to different final states, and the ground truth encodes one of them; or
- (b) the ground truth comes from generator logic that is degenerate on the data, so the task as worded has no well-defined answer (for example, growth "since" the last data day).

Two further conditions apply:
- The agent's failing action must follow a reasonable reading or handling of that defect.
- The defect must be present in English. If only the Bangla wording introduces it, the confound is Translation.

The following are not Benchmark:
- full-state comparison that counts a real side effect (an event created and then deleted shifts the ID sequence);
- the rule that errored or iteration-limited runs fail;
- the documented 5-result search cap.

The §8 tree has no benchmark step: it records the agent-level failure, and §7 sets the confound.

**C7. General on English rows.** "Present in both English and Bangla" applied to an English (C0) failure requires the same mechanism class in a C6 failure; the same task's BN side counts. Cite the C6 uid. BN rows cite a C0 failure. A mechanism shared only between English failures is not General: with no C6 analogue it is Unclear.
