# Failure Analysis Pipeline for the Bangla Agent Paper

This file gives the step-by-step process for analyzing failures, finding root causes, and turning the analysis into paper findings.

The goal is simple: do not only say "Bangla performance is lower." Show **where the Bangla trajectory first breaks**, **why it breaks**, and **which failures remain after removing confounds**.

## 1. What You Need Before Analysis

Prepare these files or tables first:

1. English run results.
2. Bangla run results.
3. Full English trajectories.
4. Full Bangla trajectories.
5. Task metadata: dataset, domain, task ID, model, run ID.
6. Final pass/fail label for each run.
7. Tool calls, tool arguments, tool results, final answer, and final environment/database state.

Every task should have one row like this:

- dataset
- model
- task ID
- run ID
- English pass/fail
- Bangla pass/fail
- English trajectory path
- Bangla trajectory path
- English final state
- Bangla final state

## 2. First Compute the Basic Outcome

Start with simple quantitative results.

For each dataset, model, and overall setting, compute:

1. English success rate.
2. Bangla success rate.
3. Absolute English-Bangla gap.
4. MELR: English-to-Bangla relative loss.
5. Four paired outcome counts:
   - EN-pass / BN-pass
   - EN-pass / BN-fail
   - EN-fail / BN-pass
   - EN-fail / BN-fail

The most important group is:

**EN-pass / BN-fail**

This is the cleanest group for Bangla-specific degradation because the same task succeeded in English but failed in Bangla.

## 3. Choose Which Cases to Analyze

Analyze cases in this order:

1. All EN-pass / BN-fail cases.
2. A smaller comparison sample of EN-fail / BN-fail cases.
3. A smaller comparison sample of EN-pass / BN-pass cases if needed.
4. EN-fail / BN-pass cases only if they reveal something interesting.

Why this order:

- EN-pass / BN-fail tells you what Bangla may break.
- EN-fail / BN-fail tells you what is a general model or task difficulty problem.
- EN-pass / BN-pass tells you what stable success looks like.

## 4. Create a Trace Note for Each Failure

For each EN-pass / BN-fail case, read the English and Bangla trajectories side by side.

Write a short note with these fields:

- Task goal.
- What happened in English.
- What happened in Bangla.
- First point where Bangla diverged from English.
- Final failed action or missing action.
- Failure type.
- Root cause.
- Confound decision.
- Evidence quote or tool-call evidence.

Keep the note short. The goal is not to rewrite the whole trace; the goal is to capture the first meaningful failure.

## 5. Find the First Failure Point

Ask this question first:

**Where did the Bangla trajectory first become unable to reach the correct final state?**

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

Important rule:

Do not label only the final visible error. Find the earliest upstream point that caused the failure.

Example:

- If the agent called the wrong tool because the Bangla user simulator gave the wrong name, the root cause is not "wrong tool call." The root cause is **user-simulator entity-slot corruption**.

## 6. Assign the Failure Type

After finding the first failure point, assign one failure type.

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

For your current Gemma/tau2 evidence, keep special attention on:

- premature STOP before final tool call;
- internal ID used as natural-language name;
- changed budget or task constraint;
- compound task partially completed;
- wrong or early user-simulator termination.

## 7. Assign the Confound Type

Now ask:

**Is this really caused by Bangla agent behavior, or is it caused by another artifact?**

Use this confound taxonomy:

1. Genuine Bangla-related agent failure.
2. Bangla user-simulator error.
3. Translation/localization error.
4. Tool/environment failure.
5. Benchmark/task ambiguity.
6. General model weakness present in both English and Bangla.
7. Unclear.

This distinction is very important for the paper. Reviewers will not accept a strong Bangla claim if the real cause is broken simulation or translation.

## 8. Root Cause Decision Process

Use this simple decision tree for every EN-pass / BN-fail case.

### Step 1: Was the translated task valid?

Check:

- Was the Bangla instruction faithful to English?
- Were protected tokens preserved?
- Were executable values preserved or correctly mapped?
- Was the task still answerable?

If no, root cause is:

**Translation/localization error**

### Step 2: Did the Bangla user simulator behave correctly?

Check:

- Did it preserve the same task goal?
- Did it give correct names, IDs, dates, prices, addresses, or constraints?
- Did it stop only after the agent completed the required final action?
- Did it avoid adding new constraints not present in the task?

If no, root cause is:

**Bangla user-simulator error**

Example root causes:

- Premature STOP after confirmation but before final tool call.
- Internal ID surfaced as user name.
- Budget or decision constraint changed.
- Compound task ended after only one subtask.

### Step 3: Did the agent understand the Bangla user correctly?

Check:

- Did the agent restate or act according to the correct task?
- Did it identify the correct entity, slot, and constraint?
- Did it preserve the user's intent across turns?

If no, root cause is:

**Bangla understanding or grounding failure**

### Step 4: Did the agent choose the right tool/action?

Check:

- Was the required tool available?
- Did English choose the correct tool?
- Did Bangla choose a different or unnecessary tool?

If no, root cause is:

**Wrong tool/action**

### Step 5: Did the agent fill the correct arguments?

Check:

- Correct name?
- Correct ID?
- Correct date/time?
- Correct item/product?
- Correct amount/price?
- Correct source and destination?
- Correct enum/canonical value?

If no, root cause is:

**Wrong tool argument**

### Step 6: Did the tool/environment execute correctly?

Check:

- Did the tool return an error despite correct arguments?
- Was there a database or environment issue?
- Did the environment state differ unexpectedly?

If yes, root cause is:

**Tool/environment failure**

### Step 7: Did the agent verify completion?

Check:

- Did the agent check the final state?
- Did it stop after partial completion?
- Did it miss a required final write action?

If no, root cause is:

**Verification failure or premature abandonment**

## 9. Evidence Required for Each Root Cause

For every labeled failure, save evidence.

Minimum evidence:

1. English outcome.
2. Bangla outcome.
3. First failure point.
4. Tool call or message proving the failure.
5. Why this is not just a general model failure.
6. Confound label.

Good evidence sentence format:

> In task X, English passed by calling TOOL_A with ARG_Y. In Bangla, the user simulator emitted STOP immediately after confirmation, so the agent never called TOOL_A. Therefore the failure is labeled as premature termination caused by Bangla user-simulator error.

## 10. Convert Labels Into Counts

After labeling all EN-pass / BN-fail cases, count:

1. Failure type distribution.
2. First failure point distribution.
3. Confound type distribution.
4. Genuine Bangla-related cases after filtering.
5. User-simulator-caused cases.
6. Translation-caused cases.
7. Tool/environment-caused cases.
8. Dataset-wise distribution.
9. Model-wise distribution.
10. Domain-wise distribution.

These counts become your main paper tables/figures.

## 11. Statistical Analysis

Use paired statistics because English and Bangla are evaluated on the same tasks.

Run:

1. McNemar test for English vs Bangla pass/fail.
2. Holm correction for multiple dataset/model comparisons.
3. 95% confidence intervals for success rate, absolute gap, and MELR.
4. Effect size for the English-Bangla gap.
5. Sensitivity analysis:
   - all cases;
   - after removing translation confounds;
   - after removing user-simulator confounds;
   - after removing tool/environment confounds.

Do not rely only on p-values. Report the size of the effect and uncertainty.

## 12. How to Turn Analysis Into Findings

A finding should have this structure:

1. Observation.
2. Evidence.
3. Root cause.
4. Boundary or limitation.

Use this template:

> We find that [failure pattern] accounts for [N/%] of EN-pass / BN-fail cases. Manual trajectory analysis shows that these failures usually begin at [first failure point]. After filtering [confound type], [N/%] cases remain, suggesting [careful interpretation].

Good finding examples for your current evidence:

1. Bangla failures were driven less by malformed tool syntax and more by dialogue-state fidelity errors.
2. Some Bangla failures came from premature user-simulator STOP before the agent could execute the final tool call.
3. Entity-slot corruption caused authentication and lookup failures when internal IDs were surfaced as names.
4. Some Bangla trajectories changed task constraints, producing valid-looking conversations but wrong final database states.
5. Compound tasks were vulnerable to partial completion, where Bangla completed an early subtask but stopped before the final required write action.

## 13. Final Paper Outputs

The final paper should include these outputs:

1. Overall English vs Bangla success table.
2. MELR by dataset and model.
3. Paired outcome table: EN-pass/BN-pass, EN-pass/BN-fail, EN-fail/BN-pass, EN-fail/BN-fail.
4. Failure type distribution for EN-pass / BN-fail cases.
5. First failure point distribution.
6. Confound filtering table.
7. Before/after confound-filtered results.
8. Two or three short case studies.
9. Appendix with full annotation rules and long trajectories.

## 14. Quality Control Checklist

Before trusting the findings, check:

- Every task ID is aligned between English and Bangla.
- Every metric has a denominator.
- EN-pass / BN-fail is separated from both-fail.
- Translation errors are not counted as genuine Bangla agent failures.
- User-simulator errors are counted separately.
- Tool/environment failures are counted separately.
- At least one second reviewer checks a subset of labels.
- Disagreements are adjudicated.
- Case studies match the quantitative patterns.
- Strong claims are made only after confound filtering.

## 15. Sources Used to Shape This Pipeline

This pipeline follows your existing methodology and paper structures, plus common practices from recent evaluation/error-analysis work:

- Error-analysis pipelines recommend per-instance trace review, open notes, taxonomy creation, taxonomy validation, and category counts.
- Agent-evaluation guidance recommends trajectory-level analysis, tool-call sequence inspection, user-simulator validation, and checking whether failures come from the benchmark rather than the agent.
- Tool-use benchmark work emphasizes invalid calls, wrong arguments, ignored tool outputs, execution faults, and recovery failures.
- Paired evaluation guidance recommends McNemar testing for paired binary outcomes, confidence intervals, effect sizes, and multiple-comparison correction.

Relevant references to cite or inspect:

- Diagnosing Failures in Large Language Models' Answers: Integrating Error Attribution into Evaluation Framework.
- ErrorMap and ErrorAtlas: Charting the Failure Landscape of Large Language Models.
- TRAIL: Trace Reasoning and Agentic Issue Localization.
- ToolScan: A Benchmark for Characterizing Errors in Tool-Use LLMs.
- ToolMisuseBench: An Offline Deterministic Benchmark for Tool Misuse and Recovery in Agentic Systems.
- Agent Evaluation: A Detailed Guide.
