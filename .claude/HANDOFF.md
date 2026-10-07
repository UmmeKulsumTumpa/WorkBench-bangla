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
7. **Do not edit dated entries** in the `progress.md` decisions log. Add a new numbered entry instead; the next is **#39**.

## 3. Done so far

| | gemma4:31b, 90-task pilot |
|---|---|
| C0 (all EN) | 73/90 = 81.1%, side effects 16.7%, 340 requests (2026-10-04) |
| C1 (BN task only) | 74/90 = 82.2%, p = 1.0 vs C0 |
| C6 (BN task + BN system prompt + EN tools + forced BN replies; **collaborators' setup**) | 74/90 = 82.2%, Δ +1.1 pp (CI −7.8, +10.0), p = 1.0; side effects 8.9%; 296 requests (2026-10-05) |

| | gpt-oss:20b, 90-task pilot (finished 2026-10-07) |
|---|---|
| C0 (all EN) | 53/90 = 58.9%, side effects 25.6%, 381 requests (2026-10-05) |
| C6 (collaborators' setup) | 48/90 = 53.3%, Δ −5.6 pp (CI −16.7, +5.6), p = 0.4244; side effects 24.4%; 346 requests (2026-10-05/06 and 2026-10-07) |
| S1 (85 pairs without an infrastructure error) | 62.4% vs 55.3%, Δ −7.1 pp (CI −17.6, +4.7), p = 0.3075 |
| S2 (recovered re-runs as failures) | 56.7% vs 51.1% |

- **Reading:** no detectable language gap on gemma.
  - Failures are mostly reasoning (calendar free slots, date math, filters), shared by both languages.
  - 0 failures are labelled primarily multilingual (single model annotator).
  - Watch items:
    - 2–3 of 7 C6-only failures resolve Bangla relative dates; "আগামী শুক্রবার" needs the owner's review;
    - 2 empty answers occur only in C6;
    - more C6 failures change nothing in the database.
- **gpt-oss reading:** no detectable gap (the CI includes 0 and also allows a moderate drop). 0 of 42 c6 failures are primarily multilingual (single model annotator). The model is weaker overall (c0 58.9% vs gemma 81.1%); its failures split between reasoning and tool_use (invented `@example.com` addresses, corrupted kwargs such as `new?`, which occur in English too). Bad kwargs on any attempt: 3 c0 tasks vs 8 c6 tasks, the one pattern worth repeats.
  - **Caveats:** the infrastructure label says who ended the run, not that the model was faultless; errored rows have lost traces (1-7 model calls before each). The runs were on different days and resumed; the last 23 c6 tasks ran on 2026-10-07 with a new key; `run_date` in the per-task files is the finishing invocation's date (issue #16).
  - **Report:** `results/comparisons/pilot_ollama-gpt-oss-20b_c6_vs_c0/` (`report.md`, `report.html`, `report_fragment.html`). Artifact: not published yet.
- **C6 HTML report:** https://claude.ai/artifact/RwtdFQ5pvZ4uVXdrQNuzGc (private). The C1 report is linked in `progress.md`.
- **Harness:** conditions c0–c6 (`WorkBench/src/evals/conditions.py`), Bangla assets in `WorkBench/data/conditions/bn/`, runner `scripts/run_condition.py`, comparison `scripts/compare_conditions.py`, HTML `scripts/build_report_html.py`. Tests: WorkBench 285, project 19.
- **Fixed:** request counts are distinct `llm_input` per task, not trace steps (#7/#8). The true rate is about 3.8 requests per task.
- **Tags:** `run/pilot-c0c1-gemma4-31b`, `run/pilot-c6-gemma4-31b`, `run/pilot-c0-gpt-oss-20b` (dcb6c76), `run/pilot-c6-gpt-oss-20b` (a8447a3).
- **Merged PRs:** #1–#3, #5, #8, #10, #11, #15. The PR for issue #13 (branch `run/gpt-oss-20b`, Tasks 2-5) is open, not merged.

## 4. Next action (updated 2026-10-07: gpt-oss:20b pilot analysed and reported)
**There is no C7.** On 2026-10-05 the owner confirmed the scope is **C0 vs C6**. Do not ask again.

**State:** branch `run/gpt-oss-20b`; Tasks 1-5 of `docs/design/plans/2026-10-06-gpt-oss-20b-run.md` are done and the PR (`Closes #13`) is open, **not merged**. No run is pending and no model calls are needed.
- Task 1 (PR #15) per-model folders; Task 2 smoke10 gate; Task 3 the c0 and c6 pilots (c6 resumed on 2026-10-07 with a new key); Task 4 comparison, failure analysis, S1 and S2 sensitivity, "compared with gemma"; Task 5 report, HTML, README, tags.
- `progress.md` #36, #37 and #38 have the details. The controller ledger is `.superpowers/sdd/2026-10-06-gpt-oss-20b-run/progress.md` (git-ignored).

**Next, in order:**
1. **Final review** of the branch (most capable model; rulings in the ledger).
2. **Merge the PR** with `gh pr merge --merge --delete-branch` once the review is clean.
3. **Publish `report_fragment.html`** (`results/comparisons/pilot_ollama-gpt-oss-20b_c6_vs_c0/`) as a **new** private artifact (icon `chart`; load `artifact-design` first), then record its URL in `progress.md` and in §3 here through a small PR.
4. **Follow-up:** issue #16 (`run_date` of resumed runs uses the finishing invocation's start), and issue #9.

**The owner's open options (not approved; each needs a request estimate and the owner's go first):**
- gemma C0-rep2 (noise floor, about 342 requests); repeats of gpt-oss would also help with its bad-kwarg excess in c6;
- 300 tasks (only if repeated runs show a finding);
- C3;
- a native-speaker review of `docs/conditions/translation_review.md` and the task templates, including "আগামী শুক্রবার" and "গত সপ্তাহে". If the wording changes, c6 must be re-run on both models.

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
