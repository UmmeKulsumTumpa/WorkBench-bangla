# Plan: failure-analysis pipeline reports for gemma4:31b and gpt-oss:20b (2026-10-07)

Spec: `instructions/failure_analysis_pipeline.md` (the owner's pipeline; binding). Every section of it is followed; this plan only maps it onto WorkBench. Issue: see `progress.md` #39.

Scope: two reports, one per model, each comparing **English = C0** (all English) with **Bangla = C6** (Bangla task, Bangla system prompt, English tool descriptions, replies forced to Bangla) on the 90-task pilot. There is no C7. The inputs are existing runs only: no model or API calls of any kind (no Ollama). Claude subagents do the annotation.

Inputs per model (`<M>` = `ollama-gemma4-31b` or `ollama-gpt-oss-20b`):
- Comparison: `results/comparisons/pilot_<M>_c6_vs_c0/` (`paired.csv`, `per_task_ref.csv`, `per_task_treat.csv`, `metrics.csv`, run metas, earlier `failure_analysis.md`/`failure_labels.csv`).
- Runs: `WorkBench/data/results/c0/pilot_en/<M>/*.csv` and `c6/pilot_bn/<M>/*.csv`, plus git-ignored `*_traces.json` (90 entries each, `task` + `steps[]` with `llm_input`, `llm_output`, `action`, `action_input`, `observation`).
- Tasks and ground truth: `WorkBench/data/processed/tasks_and_outcomes/pilot_{en,bn}_tasks_and_outcomes.csv` (`outcome` = ground-truth calls), index `data_bn/pilot/pilot_index.csv` (task_uid ↔ row).
- Logs (gpt-oss errored rows have lost traces): `results/logs/pilot/<M>/`.

Outputs: `results/failure_pipeline/annotation_rules.md` (shared) and, per model, `results/failure_pipeline/pilot_<M>_c6_vs_c0/` containing `task_table.csv`, `trace_notes.md`, `labels.csv`, `second_review.csv`, `adjudication.csv`, `stats.json`, `report.md`.

## Global Constraints

- No model/API calls. Project-local tooling only: `source env.sh && uv run --project WorkBench --frozen python ...` in one shell command (zsh). Install nothing.
- Git: issue → branch `analysis/failure-pipeline` → PR `Closes #N` → merge (controller merges). Never commit on `main`. Never edit dated `progress.md` decision entries; the next entry is **#39**.
- Never modify existing run files or existing `results/comparisons/*` files. Traces stay git-ignored; reports quote short excerpts only.
- Every number in a report comes from `stats.json` or the label CSVs (generated), with its denominator. Cautious claims: n = 90, one run per side, model annotators, unreviewed Bangla prompt.
- Large CSV fields: `csv.field_size_limit(sys.maxsize)`. Statistics reuse `scripts/compare_conditions.py`'s `mcnemar_exact` and `paired_bootstrap_ci` (seed 20261004).

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

## Task 1: Stats and task-table script, annotation rules (branch `analysis/failure-pipeline`)

1. Commit the spec `instructions/failure_analysis_pipeline.md` (owner's file, unchanged) and this plan.
2. Write `results/failure_pipeline/annotation_rules.md`: the Annotation rules section above, verbatim, plus the exact label vocabularies (§5, §6, §7 lists) and the `labels.csv` column contract (`task_uid, domain, pair_class, side (EN|BN), first_failure_point, failure_type, confound, decision_tree (EN-pass/BN-fail only: S1..S7 outcomes), evidence, not_general_reason, annotator`).
3. Write `scripts/failure_pipeline.py` with two subcommands:
   - `table --model <M>` writes `task_table.csv`, one row per task with the §1 fields: dataset, model, task_uid, domain, run_id_en, run_id_bn, en_pass, bn_pass, pair_class, en_trajectory (traces path + index), bn_trajectory, en_final_state, bn_final_state, gt_state, en_error, bn_error. Check that task_uid alignment between EN and BN is exact (90/90, same order), and fail loudly otherwise.
   - `stats --labels <labels.csv or adjudicated> --model <M>` writes `stats.json` with everything in "Statistics". Holm needs both models: `stats --all` runs both and applies Holm.
   - Also `counts`, which writes the §10 distributions (1–10) from the final labels into `stats.json`.
4. Tests in `tests/test_failure_pipeline.py`, covering MELR, Holm, the discordant-OR CI, the Wilson CI, sensitivity filtering, and the alignment check (small synthetic inputs). Run the project and WorkBench suites and `ruff check`.
5. Run `table` for both models and commit the outputs. Do not run `stats` with labels yet.

## Task 2: Annotation, gemma4:31b (writes files only; the controller commits)
Follow `annotation_rules.md`. Write `trace_notes.md` (one §4 note per EN-pass/BN-fail case) and `labels.csv` (all required rows) in `results/failure_pipeline/pilot_ollama-gemma4-31b_c6_vs_c0/`. Read the EN and BN trajectories side by side from the traces.

## Task 3: Annotation, gpt-oss:20b (as Task 2; can run in parallel with Task 2 because it writes a different folder)

## Task 4: Second review and adjudication (both models)
1. The blind second annotator writes `second_review.csv` per model for all EN-pass/BN-fail cases.
2. Compute agreement per field (raw % and κ).
3. The adjudicator writes `adjudication.csv`: every disagreement, both labels, the decision and its reason. It then produces `labels_final.csv`: first-annotator labels with the adjudicated values applied.

## Task 5: Statistics, counts and reports
1. Run `stats --all` and `counts` on `labels_final.csv`.
2. Write `report.md` per model, with all §13 outputs:
   - the overall success table;
   - MELR;
   - the paired table;
   - the failure type, first failure point and confound distributions for EN-pass/BN-fail;
   - the confound filtering table and the before/after filtered results;
   - 2–3 case studies matching the quantitative pattern;
   - an appendix with the annotation rules link and long trace excerpts.
   Each report also needs the §10 counts (including model-wise, next to the other model), the §11 statistics (effect sizes and uncertainty, not only p), the §12 findings in Observation / Evidence / Root cause / Boundary form using the template sentence, and the §14 QC checklist with each item ticked and its evidence.
3. Update `README.md` (link), `progress.md` (Current step, entry #39), `.claude/HANDOFF.md`. Commit and open the PR.

Final whole-branch review on the most capable model, then merge.
