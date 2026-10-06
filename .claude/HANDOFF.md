# Session handoff: WorkBench → Bangla (written 2026-10-05, end of session 2)

Read this file fully, then `progress.md` (source of truth) and `git log --oneline -15`. Then continue at **Next action**.

## 1. The project in 5 lines
- **Research question:** do LLM agents complete the same multi-step office tasks less reliably when instructed in Bangla than in English, and how do the failure types shift?
- **Benchmark:** WorkBench (simulated, offline company data in CSVs plus 27 Python tool functions; graded by final database state). "Today" is fixed at Thu 2023-11-30.
- **Merging:** collaborators run the same design on OfficeBench and τ²-bench. Outputs follow the shared schema `docs/data/schema.md` v2.
- **Owner:** Umme Kulsum Tumpa, a native Bangla speaker. Wants concise, direct answers and the answer first.
- **Repo:** private GitHub `UmmeKulsumTumpa/WorkBench-bangla`. Local path `/Users/cefalo/Desktop/academic/BARTA/workbench`.

## 2. Hard rules (owner)
1. **Free model tiers only** (Ollama Cloud). Record the projected requests in `progress.md` and get the owner's go before every new run. Stop on 402, 429 or a quota message.
2. **Everything project-local:** `source env.sh` first, in the same command as uv (the shell is zsh and the env does not persist). Python runs as `uv run --project WorkBench --frozen python ...`. No global installs or settings, and nothing written outside the project folder.
3. **Git workflow:** one GitHub issue per task. Work on a feature branch, open a PR with `Closes #N`, then `gh pr merge --merge --delete-branch`. Never commit on `main`. Cut releases or tags at milestones. No empty or artificially split commits. The owner wants GitHub activity (badges); do it with real work only.
4. **Conditions are a `--condition` flag, never branches.** Each model and condition gets its own folders (issue #12 makes the raw results per model).
5. **Subagent-driven execution** (`superpowers:subagent-driven-development`): an implementer and a task reviewer per task, a final review on the most capable model, rulings in the ledger, and an exhaustive list of rulings in the final message.
6. **Results must map to a commit.** The runner refuses a dirty harness, and a finished run is final: use `--run_label rep2` for repeats and never re-run.
7. **Do not edit dated entries** in the `progress.md` decisions log. Add a new numbered entry instead; the next is **#37**.

## 3. Done so far

| | gemma4:31b, 90-task pilot |
|---|---|
| C0 (all EN) | 73/90 = 81.1%, side effects 16.7%, 340 requests (2026-10-04) |
| C1 (BN task only) | 74/90 = 82.2%, p = 1.0 vs C0 |
| C6 (BN task + BN system prompt + EN tools + forced BN replies; **collaborators' setup**) | 74/90 = 82.2%, Δ +1.1 pp (CI −7.8, +10.0), p = 1.0; side effects 8.9%; 296 requests (2026-10-05) |

- **Reading:** no detectable language gap on gemma.
  - Failures are mostly reasoning (calendar free slots, date math, filters), shared by both languages.
  - 0 failures are labelled primarily multilingual (single model annotator).
  - Watch items:
    - 2–3 of 7 C6-only failures resolve Bangla relative dates; "আগামী শুক্রবার" needs the owner's review;
    - 2 empty answers occur only in C6;
    - more C6 failures change nothing in the database.
- **C6 HTML report:** https://claude.ai/artifact/RwtdFQ5pvZ4uVXdrQNuzGc (private). The C1 report is linked in `progress.md`.
- **Harness:** conditions c0–c6 (`WorkBench/src/evals/conditions.py`), Bangla assets in `WorkBench/data/conditions/bn/`, runner `scripts/run_condition.py`, comparison `scripts/compare_conditions.py`, HTML `scripts/build_report_html.py`. Tests: WorkBench 284, project 19.
- **Fixed:** request counts are distinct `llm_input` per task, not trace steps (#7/#8). The true rate is about 3.8 requests per task.
- **Tags:** `run/pilot-c0c1-gemma4-31b`, `run/pilot-c6-gemma4-31b`.
- **Merged PRs:** #1–#3, #5, #8, #10, #11.

## 4. Next action (updated 2026-10-06: PAUSED on the free-tier monthly limit)
**There is no C7.** On 2026-10-05 the owner confirmed the scope is **C0 vs C6**. Do not ask again.

**State:** branch `run/gpt-oss-20b` (not merged, issue #13 open).
- Task 1 is done (PR #15).
- Task 2 is done: smoke10 gate passed.
- Task 3: c0 pilot finished 90/90; c6 pilot stopped at 76/90 on HTTP 429 "monthly usage limit". Both are committed.
- The controller ledger is `.superpowers/sdd/2026-10-06-gpt-oss-20b-run/progress.md` (git-ignored). Its rulings, deferred minors and task reports are there; read it first.
- `progress.md` #36 has the details.

**Resume after the monthly reset**, with the owner's go:
1. Finish c6: `source env.sh && PYTHONUNBUFFERED=1 uv run --project WorkBench --frozen python scripts/run_condition.py --condition c6 --subset pilot --model ollama-gpt-oss-20b`. It also re-runs c6's errored rows.
2. Stop on 402, 429 or quota, or when 3 consecutive tasks end with a 5xx after the harness's 10 retries. Isolated 500s are fine. Keep a watchdog on the log.
3. Commit the run, review Task 3, then do Tasks 4–5. Task 4 must:
   - label 5xx, timeout and stall errors as infrastructure;
   - add a sensitivity line over pairs without such errors;
   - add a sensitivity line counting the 2 re-run c0 tasks (pilot idx 0 and idx 58) as failures.
4. Report requests both as distinct `llm_input` and as provider attempts.

Original plan, `docs/design/plans/2026-10-06-gpt-oss-20b-run.md`, subagent-driven:
1. **Task 1, issue #12:** per-model folders for raw results and logs. Move the gemma runs and regenerate the comparisons; the metrics must stay byte-identical.
2. **Task 2, issue #13:** smoke10 C0 and C6 on `ollama-gpt-oss-20b`, then the go/no-go gate (C0 ≥ 3/10, tool calls valid). If the gate fails, stop and ask the owner. The fallbacks are gpt-oss:120b or local qwen3:8b.
3. **Tasks 3–5:** 90-task C0 and C6, comparison and failure analysis (including a descriptive "compared with gemma" section), report, HTML, README, tags, a **new** artifact.

The budget for this plan is approved: about 765 requests. The owner's later options, not approved yet:
- gemma C0-rep2 (noise floor, about 342 requests);
- 300 tasks;
- C3;
- a native-speaker review of `docs/conditions/translation_review.md` and the task templates.

## 5. Gotchas, learned the hard way
- **zsh does not split `$VAR` into words:** write the commands out, or use Python `subprocess`.
- **Large CSV fields:** `csv.field_size_limit(sys.maxsize)`.
- **A single run takes about 6 min for 90 tasks.** Give each Bash call `timeout: 600000`. If a run is interrupted, the same command resumes it.
- **`compare_conditions.py` rebuilds `results/summary.csv`** and needs the WorkBench venv. `build_report_html.py` is stdlib only (`python3`).
- **The HTML template** labels the reference "English" and the treatment "Bangla". The builder refuses other pairs; fine for c6 vs c0. Give each report a distinct `report_notes.json` `title`.
- **Publishing a report:** publish `report_fragment.html` as a **new** artifact, never over an existing one. Before writing any artifact page, load the `artifact-design` skill.
- **Workers:** the free Ollama tier allows 1 concurrent request (`--workers 1` is built in). Logs show `HTTP/1.1 200 OK` per request.
- **Commit attribution:** a commit's `Co-Authored-By` names the model that wrote it (Sonnet or Opus).
- **Open follow-ups:** issue #9 (C1 report wording, provenance of the pre-flag runs, missing `llm_input`).

## 6. Owner's open questions (ask once, when relevant)
- Release `v0.2-c6-pilot` on GitHub? (offered, not answered)
- Permissions: move the strict global `ask` rules from `~/.claude/settings.json` to the EAGL project so this project runs without prompts? (offered, not answered)
- The owner may share the artifact links with teammates; they are private until shared from the Share menu.
