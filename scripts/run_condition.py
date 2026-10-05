#!/usr/bin/env python3
"""Run one condition on one task subset with the fixed study settings (docs/runbook/README.md).

    source env.sh && uv run --project WorkBench --frozen python scripts/run_condition.py \
        --condition c3 --model ollama-gemma4-31b --subset pilot [--run_label rep2] [--dry_run]

What it does:
1. Resolves the tasks file from the condition's task language: data_bn/<subset>/<subset>_<lang>_tasks_and_outcomes.csv,
   and makes sure the identical file is in WorkBench/data/processed/tasks_and_outcomes/ (the scorer's GT folder).
2. Refuses to run if harness code or condition assets have uncommitted changes (results must map to a commit);
   --allow_dirty overrides for debugging only.
3. Prints the plan: condition spec, exact system prompt, tasks left, projected LLM requests. --dry_run stops here
   (no API call).
4. Runs `workbench-inference` with the study settings (STUDY_FLAGS) and --resume, so an interrupted run continues
   where it stopped and a finished run is a no-op. Output: WorkBench/data/results/<condition>[-<label>]/<subset>_<lang>/.
5. Writes the full console output to results/logs/<subset>/<condition>[-<label>]_<model>_<timestamp>.log and
   appends one row to results/logs/run_log.csv.
"""

from __future__ import annotations

import argparse
import csv
import filecmp
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WB = ROOT / "WorkBench"
sys.path.insert(0, str(WB))

from src.data_generation.data_generation_utils import HARDCODED_CURRENT_TIME  # noqa: E402
from src.evals.agent import MODEL_REGISTRY, build_structured_system_prompt  # noqa: E402
from src.evals.conditions import (  # noqa: E402
    CONDITIONS,
    act_without_confirmation_text,
    build_datetime_prefix,
    extra_instructions,
    get_condition,
)

STUDY_FLAGS = [
    "--structured_outputs",
    "--act_without_confirmation",
    "--tool_selection",
    "all",
    "--workers",
    "1",
    "--log_traces",
    "--resume",
]
REQUESTS_PER_TASK = 3.8  # measured on the 2026-10-04 pilot: 682 LLM requests / 180 tasks (c0 340 + c1 342)
GT_DIR = WB / "data" / "processed" / "tasks_and_outcomes"
LOG_DIR = ROOT / "results" / "logs"
RUN_LOG = LOG_DIR / "run_log.csv"
RUN_LOG_COLUMNS = [
    "started_at",
    "finished_at",
    "exit_code",
    "subset",
    "condition",
    "run_label",
    "model",
    "n_tasks",
    "n_run",
    "results_dir",
    "log_file",
    "harness_commit",
    "harness_dirty",
    "command",
]
csv.field_size_limit(sys.maxsize)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def harness_dirty() -> bool:
    return bool(
        git("status", "--porcelain", "--", "WorkBench/src", "WorkBench/data/conditions")
    )


def stage_tasks(subset: str, lang: str) -> Path:
    """Copy the subset's tasks file into the WorkBench GT folder (or verify the copy there is identical)."""
    name = f"{subset}_{lang}_tasks_and_outcomes.csv"
    src = ROOT / "data_bn" / subset / name
    if not src.exists():
        raise SystemExit(f"tasks file not found: {src.relative_to(ROOT)}")
    dst = GT_DIR / name
    if dst.exists() and not filecmp.cmp(src, dst, shallow=False):
        raise SystemExit(
            f"{dst.relative_to(ROOT)} differs from {src.relative_to(ROOT)}; resolve before running"
        )
    if not dst.exists():
        shutil.copyfile(src, dst)
    return dst


def count_rows(path: Path) -> int:
    with open(path, encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


def run_state(results_dir: Path, model: str) -> tuple[bool, int, int]:
    """(finished, rows without error, rows with error) of the newest results file in ``results_dir``.

    ``finished`` means the run reached its end (``finished_at`` in _meta.json). Its errored rows (e.g. the
    agent hit the step limit) are real outcomes, so a finished run is not resumed unless --retry_errors.
    """
    files = sorted(results_dir.glob(f"{model}_all_*-*-*_*-*-*.csv"))
    if not files:
        return False, 0, 0
    meta = files[-1].with_name(files[-1].name.replace(".csv", "_meta.json"))
    finished = meta.exists() and bool(
        json.loads(meta.read_text(encoding="utf-8")).get("finished_at")
    )
    with open(files[-1], encoding="utf-8", newline="") as f:
        errors = [bool(r.get("error")) for r in csv.DictReader(f)]
    return finished, errors.count(False), errors.count(True)


def append_run_log(row: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    new = not RUN_LOG.exists()
    with open(RUN_LOG, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RUN_LOG_COLUMNS, lineterminator="\n")
        if new:
            w.writeheader()
        w.writerow(row)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--condition", required=True, choices=sorted(CONDITIONS))
    p.add_argument(
        "--model", required=True, choices=sorted(MODEL_REGISTRY), metavar="MODEL"
    )
    p.add_argument(
        "--subset",
        default="pilot",
        help="task subset folder under data_bn/ (pilot, smoke10, ...)",
    )
    p.add_argument(
        "--run_label", default=None, help="label for a repeated run, e.g. rep2"
    )
    p.add_argument(
        "--dry_run", action="store_true", help="print the plan and exit (no API call)"
    )
    p.add_argument(
        "--allow_dirty",
        action="store_true",
        help="run with uncommitted harness changes (debug only)",
    )
    p.add_argument(
        "--retry_errors",
        action="store_true",
        help="re-run errored tasks of a FINISHED run (changes its results; default: a finished run is final)",
    )
    args = p.parse_args(argv)

    cond = get_condition(args.condition)
    tasks_rel = stage_tasks(args.subset, cond.task_lang).relative_to(WB)
    run_dir = cond.id + (f"-{args.run_label}" if args.run_label else "")
    results_dir = WB / "data" / "results" / run_dir / f"{args.subset}_{cond.task_lang}"
    n_tasks = count_rows(WB / tasks_rel)
    finished, n_ok, n_err = run_state(results_dir, args.model)
    n_run = 0 if finished and not args.retry_errors else n_tasks - n_ok
    prompt = build_structured_system_prompt(
        build_datetime_prefix(HARDCODED_CURRENT_TIME, cond.system_lang),
        True,
        act_without_confirmation_text(cond.system_lang),
        extra_instructions(cond),
    )
    cmd = [
        "workbench-inference",
        "--model_name",
        args.model,
        "--tasks_path",
        str(tasks_rel),
        "--condition",
        cond.id,
        *(["--run_label", args.run_label] if args.run_label else []),
        *STUDY_FLAGS,
    ]
    dirty = harness_dirty()

    print(f"condition   {cond.id}: {cond.description}")
    print(
        f"layers      task={cond.task_lang} system={cond.system_lang} tools={cond.tool_desc_lang} output={cond.output_lang or 'free'}"
    )
    print(f"model       {args.model} ({MODEL_REGISTRY[args.model].model_id})")
    status = (
        f"finished ({n_ok} ok, {n_err} errored)"
        if finished
        else f"{n_ok} done so far"
        if n_ok
        else "not started"
    )
    print(
        f"tasks       {WB.name}/{tasks_rel}: {n_tasks} tasks; run {status}; {n_run} to run now"
    )
    print(
        f"projected   ~{round(n_run * REQUESTS_PER_TASK)} LLM requests (cap {n_run * 20})"
    )
    print(f"results     {results_dir.relative_to(ROOT)}/")
    print(
        f"commit      {git('rev-parse', '--short', 'HEAD')}{' (harness has UNCOMMITTED changes)' if dirty else ''}"
    )
    print(f"prompt      {prompt}")
    print(f"command     (cd WorkBench && {' '.join(cmd)})")
    if args.dry_run:
        return 0
    if dirty and not args.allow_dirty:
        raise SystemExit(
            "harness code or condition assets have uncommitted changes; commit first (or --allow_dirty)"
        )
    if n_run == 0:
        print(
            "nothing to run: this run is finished (use --run_label for a repeat, --retry_errors to re-run errors)"
        )
        return 0

    started = datetime.now()
    log_file = (
        LOG_DIR
        / args.subset
        / f"{run_dir}_{args.model}_{started:%Y-%m-%d_%H-%M-%S}.log"
    )
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            cmd,
            cwd=WB,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
        )
        for line in proc.stdout:
            log.write(line)
            log.flush()
            if (
                line.startswith(("Progress:", "Resuming", "Routing", "Traces saved"))
                or "Error" in line[:40]
            ):
                print(line, end="", flush=True)
        code = proc.wait()
    append_run_log(
        {
            "started_at": started.isoformat(timespec="seconds"),
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "exit_code": code,
            "subset": args.subset,
            "condition": cond.id,
            "run_label": args.run_label or "",
            "model": args.model,
            "n_tasks": n_tasks,
            "n_run": n_run,
            "results_dir": str(results_dir.relative_to(ROOT)),
            "log_file": str(log_file.relative_to(ROOT)),
            "harness_commit": git("rev-parse", "HEAD"),
            "harness_dirty": dirty,
            "command": " ".join(cmd),
        }
    )
    print(f"exit {code}; log {log_file.relative_to(ROOT)}")
    return code


if __name__ == "__main__":
    sys.exit(main())
