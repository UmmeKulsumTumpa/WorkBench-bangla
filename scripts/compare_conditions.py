#!/usr/bin/env python3
"""Score two WorkBench runs with WorkBench's own scorer and compare them, paired by task (docs/data/schema.md).

A comparison is always *reference* vs *treatment*, e.g. C0 vs C3 (language effect) or C0 vs C0-rep2 (noise
floor). Paths are resolved from the condition, so the usual call is just:

    source env.sh && uv run --project WorkBench --frozen python scripts/compare_conditions.py \
        --ref c0 --treat c3 --model ollama-gemma4-31b --subset pilot [--treat_label rep2]

Resolution (override any of it with the explicit --{ref,treat}_{results,tasks,traces} flags):
- results: newest  WorkBench/data/results/<cond>[-<label>]/<subset>_<task_lang>/<model>_all_<ts>.csv
- traces:  the same path with _traces.json (optional; gives LLM-request counts)
- tasks:   data_bn/<subset>/<subset>_<task_lang>_tasks_and_outcomes.csv ; index: data_bn/<subset>/<subset>_index.csv

Scoring: `load_and_score_results(results, tasks)`, i.e. exactly what `workbench-evaluate` does (predictions merged
with the tasks file on exact task text, `is_correct` / `has_side_effects`). The task_uid comes from the tasks file's
`source_file,row_idx` columns; fallbacks: a full `<domain>[_bn]_tasks_and_outcomes.csv` gives
`workbench:<domain>:<row>`, otherwise the tasks file is joined to --index by row position.

Outputs in results/comparisons/<subset>_<model>_<treat>_vs_<ref>/: per_task_ref.csv, per_task_treat.csv,
paired.csv, metrics.csv, run_meta_ref.json, run_meta_treat.json. Afterwards results/summary.csv is rebuilt from
every comparison's metrics.csv (one row per comparison).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WB = ROOT / "WorkBench"
TEMPLATES_EN = ROOT / "data_bn" / "templates_en.csv"
GT_DIR = WB / "data" / "processed" / "tasks_and_outcomes"
RAW_RESULTS = WB / "data" / "results"
COMPARISONS = ROOT / "results" / "comparisons"
SUMMARY = ROOT / "results" / "summary.csv"
DOMAINS = ["email", "calendar", "analytics", "project_management", "customer_relationship_manager", "multi_domain"]
BENCHMARK = "workbench"
SEED = 20261004
N_BOOT = 10_000
SIDES = ("ref", "treat")

PER_TASK_COLUMNS = [
    "benchmark",
    "run_id",
    "model_key",
    "model_id",
    "provider",
    "language",
    "condition",
    "task_uid",
    "domain",
    "template_id",
    "correct",
    "side_effect",
    "error",
    "n_llm_requests",
    "n_tool_calls",
    "run_date",
]
PAIRED_COLUMNS = [
    "task_uid",
    "domain",
    "template_id",
    "correct_ref",
    "correct_treat",
    "side_effect_ref",
    "side_effect_treat",
    "pair_class",
]
METRICS_COLUMNS = ["benchmark", "model_key", "model_id", "ref_condition", "condition", "scope", "metric", "value", "n"]
META_KEYS = [
    "benchmark",
    "run_id",
    "model_key",
    "model_id",
    "provider",
    "base_url",
    "temperature",
    "language",
    "condition",
    "run_label",
    "condition_spec",
    "condition_assets",
    "system_prompt_sent",
    "subset",
    "n_tasks",
    "tasks_file",
    "tasks_file_sha256",
    "results_file",
    "tool_selection",
    "structured_outputs",
    "act_without_confirmation",
    "harness_commit",
    "harness_dirty",
    "started_at",
    "finished_at",
    "total_llm_requests",
    "notes",
]
SUMMARY_METRICS = [
    "completion_rate_ref",
    "completion_rate_treat",
    "delta_completion",
    "delta_completion_ci95_low",
    "delta_completion_ci95_high",
    "mcnemar_p",
    "n_ref_only",
    "n_treat_only",
    "side_effect_rate_ref",
    "side_effect_rate_treat",
    "delta_side_effect",
]
FULL_FILE_RE = re.compile(r"^(?P<domain>[a-z_]+?)(?:_bn)?_tasks_and_outcomes\.csv$")
RESULTS_RE = re.compile(r"_all_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.csv$")


# ---------------------------------------------------------------- statistics


def mcnemar_exact(b: int, c: int) -> float:
    """Exact two-sided McNemar test: binomial(b+c, 0.5) on the discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def paired_bootstrap_ci(ref, treat, n_boot: int = N_BOOT, seed: int = SEED, alpha: float = 0.05) -> tuple[float, float]:
    """Percentile CI of mean(treat) - mean(ref), resampling tasks (pairs) with replacement."""
    diff = np.asarray(treat, dtype=float) - np.asarray(ref, dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(diff), size=(n_boot, len(diff)))
    means = diff[idx].mean(axis=1)
    low, high = np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(low), float(high)


def pair_class(correct_ref: int, correct_treat: int) -> str:
    return {(1, 1): "both_correct", (1, 0): "ref_only", (0, 1): "treat_only", (0, 0): "both_wrong"}[
        (int(correct_ref), int(correct_treat))
    ]


def _rate(x: float) -> str:
    return f"{x:.4f}"


def compute_comparison_metrics(
    paired: pd.DataFrame,
    benchmark: str,
    model_key: str,
    model_id: str,
    ref_condition: str,
    condition: str,
    weights: dict[str, float],
) -> pd.DataFrame:
    """Long-format metrics. Overall: rates, deltas (treat - ref), McNemar, bootstrap CIs, domain-reweighted
    completion. Per domain: descriptive rates/deltas/discordant counts only (pilot_design §5: no per-domain tests)."""
    rows = []

    def add(scope, metric, value, n):
        rows.append([benchmark, model_key, model_id, ref_condition, condition, scope, metric, value, n])

    def describe(scope, df):
        n = len(df)
        cr, ct = df.correct_ref.astype(int), df.correct_treat.astype(int)
        sr, st = df.side_effect_ref.astype(int), df.side_effect_treat.astype(int)
        add(scope, "completion_rate_ref", _rate(cr.mean()), n)
        add(scope, "completion_rate_treat", _rate(ct.mean()), n)
        add(scope, "delta_completion", _rate(ct.mean() - cr.mean()), n)
        add(scope, "side_effect_rate_ref", _rate(sr.mean()), n)
        add(scope, "side_effect_rate_treat", _rate(st.mean()), n)
        add(scope, "delta_side_effect", _rate(st.mean() - sr.mean()), n)
        b, c = int(((cr == 1) & (ct == 0)).sum()), int(((cr == 0) & (ct == 1)).sum())
        add(scope, "n_ref_only", str(b), n)
        add(scope, "n_treat_only", str(c), n)
        return cr, ct, sr, st, b, c

    n = len(paired)
    cr, ct, sr, st, b, c = describe("overall", paired)
    add("overall", "mcnemar_p", f"{mcnemar_exact(b, c):.4f}", n)
    lo, hi = paired_bootstrap_ci(cr, ct)
    add("overall", "delta_completion_ci95_low", _rate(lo), n)
    add("overall", "delta_completion_ci95_high", _rate(hi), n)
    lo, hi = paired_bootstrap_ci(sr, st)
    add("overall", "delta_side_effect_ci95_low", _rate(lo), n)
    add("overall", "delta_side_effect_ci95_high", _rate(hi), n)
    by_dom = paired.groupby("domain")
    present = [d for d in weights if d in by_dom.groups]
    if present:
        wsum = sum(weights[d] for d in present)
        for side in SIDES:
            val = sum(weights[d] * by_dom.get_group(d)[f"correct_{side}"].astype(int).mean() for d in present) / wsum
            add("overall", f"completion_rate_{side}_weighted", _rate(val), n)
    order = [d for d in DOMAINS if d in by_dom.groups] + sorted(set(by_dom.groups) - set(DOMAINS))
    for d in order:
        describe(f"domain:{d}", by_dom.get_group(d))
    return pd.DataFrame(rows, columns=METRICS_COLUMNS)


def full_domain_weights() -> dict[str, float]:
    """Domain shares of the full 690-task WorkBench set (current ground truth files)."""
    counts = {d: len(pd.read_csv(GT_DIR / f"{d}_tasks_and_outcomes.csv", dtype=str)) for d in DOMAINS}
    total = sum(counts.values())
    return {d: k / total for d, k in counts.items()}


# ---------------------------------------------------------------- task identity


def attach_task_uid(tasks: pd.DataFrame, tasks_path: str, index: pd.DataFrame | None) -> pd.DataFrame:
    """Return tasks with `task_uid`, `domain` (= source file) columns added."""
    tasks = tasks.copy()
    if {"source_file", "row_idx"} <= set(tasks.columns):
        pass
    elif (m := FULL_FILE_RE.match(os.path.basename(tasks_path))) and m["domain"] in DOMAINS:
        tasks["source_file"] = m["domain"]
        tasks["row_idx"] = [str(i) for i in range(len(tasks))]
    elif index is not None and len(index) == len(tasks):
        tasks["source_file"] = index["source_file"].astype(str).values
        tasks["row_idx"] = index["row_idx"].astype(str).values
    else:
        raise ValueError(
            f"{tasks_path}: no source_file,row_idx columns, not a <domain>_tasks_and_outcomes.csv file, "
            "and no --index of equal length to join by position"
        )
    tasks["task_uid"] = BENCHMARK + ":" + tasks["source_file"].astype(str) + ":" + tasks["row_idx"].astype(str)
    tasks["domain"] = tasks["source_file"].astype(str)
    if index is not None and len(index) != len(tasks):
        tasks = tasks[tasks.task_uid.isin(set(index.task_uid))].reset_index(drop=True)
    return tasks


def template_ids(tasks: pd.DataFrame, index: pd.DataFrame | None) -> list[str]:
    lookup = {}
    if TEMPLATES_EN.exists():
        t = pd.read_csv(TEMPLATES_EN, dtype=str)
        lookup = {(s, b): tid for s, b, tid in zip(t.source_file, t.base_template, t.template_id)}
    by_uid = dict(zip(index.task_uid, index.template_id)) if index is not None and "template_id" in index else {}
    out = []
    for r in tasks.itertuples():
        tid = by_uid.get(r.task_uid) or lookup.get((r.source_file, getattr(r, "base_template", None))) or ""
        out.append(tid)
    return out


def load_trace_counts(path: str) -> dict[str, int]:
    """task text -> number of trace steps (one per successful LLM call) from a WorkBench `_traces.json`."""
    with open(path, encoding="utf-8") as f:
        entries = json.load(f)
    return {e["task"]: len(e.get("steps") or []) for e in entries}


def run_dir_name(condition: str, label: str | None) -> str:
    return condition + (f"-{label}" if label else "")


def make_run_id(subset: str, condition: str, label: str | None, model_key: str) -> str:
    return f"{BENCHMARK}_{subset}_{run_dir_name(condition, label)}_{model_key}"


def make_comparison_id(subset: str, model_key: str, *, ref: str, treat: str) -> str:
    return f"{subset}_{model_key}_{treat}_vs_{ref}"


# ---------------------------------------------------------------- path resolution


def task_lang(condition: str) -> str:
    from src.evals.conditions import get_condition  # noqa: PLC0415  (WorkBench venv)

    return get_condition(condition).task_lang


def latest_results(condition: str, label: str | None, subset: str, model_key: str) -> Path:
    d = RAW_RESULTS / run_dir_name(condition, label) / f"{subset}_{task_lang(condition)}"
    files = sorted(p for p in d.glob(f"{model_key}_all_*.csv") if RESULTS_RE.search(p.name))
    if not files:
        raise SystemExit(f"no results for {model_key} in {d}")
    return files[-1]


def resolve_side(args, side: str) -> dict:
    cond, label = getattr(args, side), getattr(args, f"{side}_label")
    results = getattr(args, f"{side}_results")
    results = Path(results).resolve() if results else latest_results(cond, label, args.subset, args.model)
    traces = getattr(args, f"{side}_traces")
    if traces is None:
        guess = results.with_name(results.name.replace(".csv", "_traces.json"))
        traces = guess if guess.exists() else None
    tasks = getattr(args, f"{side}_tasks")
    tasks = (
        Path(tasks).resolve()
        if tasks
        else ROOT / "data_bn" / args.subset / f"{args.subset}_{task_lang(cond)}_tasks_and_outcomes.csv"
    )
    return {"condition": cond, "label": label, "results": results, "tasks": tasks, "traces": traces}


# ---------------------------------------------------------------- scoring one run


def _results_meta(results_path: Path) -> dict:
    path = results_path.with_name(results_path.name.replace(".csv", "_meta.json"))
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _run_date(results_path: Path, meta: dict) -> str:
    if meta.get("started_at"):
        return str(meta["started_at"])[:10]
    m = re.search(r"_(\d{4}-\d{2}-\d{2})_\d{2}-\d{2}-\d{2}\.csv", results_path.name)
    return m.group(1) if m else ""


def score_run(results_path: Path, tasks_path: Path, index: pd.DataFrame | None) -> pd.DataFrame:
    """WorkBench's own pipeline (merge on task text, is_correct / has_side_effects), plus task_uid."""
    from src.evals.metrics import load_and_score_results  # noqa: PLC0415  (needs WorkBench cwd + sys.path)

    raw = pd.read_csv(tasks_path, dtype=str)
    tasks = attach_task_uid(raw, str(tasks_path), index)
    if not tasks.task.is_unique:
        raise ValueError(f"{tasks_path}: task texts are not unique; cannot match predictions by text")
    tasks["template_id"] = template_ids(tasks, index)
    gt_path, tmp = str(tasks_path), None
    if len(tasks) != len(raw):  # index restricted the file: score against exactly those rows
        fd, tmp = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        tasks[list(raw.columns)].to_csv(tmp, index=False, quoting=csv.QUOTE_ALL)
        gt_path = tmp
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            df = load_and_score_results(str(results_path), gt_path)
    finally:
        if tmp:
            os.remove(tmp)
    df = df.merge(tasks[["task", "task_uid", "domain", "template_id"]], on="task", how="left", validate="1:1")
    assert df.task_uid.notna().all()
    return df


def per_task_frame(df, run_id, model_key, meta, language, condition, traces, run_date) -> pd.DataFrame:
    counts = load_trace_counts(traces) if traces else None
    out = pd.DataFrame(
        {
            "benchmark": BENCHMARK,
            "run_id": run_id,
            "model_key": model_key,
            "model_id": meta.get("model_id", ""),
            "provider": meta.get("provider", ""),
            "language": language,
            "condition": condition,
            "task_uid": df.task_uid,
            "domain": df.domain,
            "template_id": df.template_id,
            "correct": df.correct.astype(bool).astype(int),
            "side_effect": df.unwanted_side_effects.astype(bool).astype(int),
            "error": df.error.fillna("").astype(str).str.slice(0, 300),
            "n_llm_requests": [str(counts[t]) if counts and t in counts else "" for t in df.task],
            "n_tool_calls": df.prediction.apply(len),
            "run_date": run_date,
        }
    )
    order = {d: i for i, d in enumerate(DOMAINS)}
    out["_d"] = out.domain.map(order)
    out["_r"] = out.task_uid.str.rsplit(":", n=1).str[1].astype(int)
    return out.sort_values(["_d", "_r"]).drop(columns=["_d", "_r"]).reset_index(drop=True)[PER_TASK_COLUMNS]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def harness_state() -> tuple[str, bool]:
    """Commit of this repo and whether the harness code (WorkBench/src, data/conditions) has local changes."""
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    dirty = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--porcelain", "--", "WorkBench/src", "WorkBench/data/conditions"],
        capture_output=True,
        text=True,
        check=True,
    )
    return commit.stdout.strip(), bool(dirty.stdout.strip())


def rel(p) -> str:
    p = Path(p).resolve()
    return os.path.relpath(p, ROOT) if p.is_relative_to(ROOT) else str(p)


def run_meta(args, side: dict, run_id: str, language: str, meta: dict, per: pd.DataFrame) -> dict:
    if meta.get("harness_commit"):
        commit, dirty = meta["harness_commit"], meta.get("harness_dirty")
    else:
        commit, dirty = harness_state()
    total = int(per.n_llm_requests.astype(int).sum()) if side["traces"] else None
    meta_cond = meta.get("condition")
    notes = []
    if not meta:
        notes.append("no _meta.json sidecar found")
    elif meta_cond is None:
        notes.append(
            "run predates the --condition flag (2026-10-04 pilot): condition taken from the results folder; "
            "harness_commit is the commit at comparison time, the run's code is tag run/pilot-c0c1-gemma4-31b"
        )
    elif meta_cond != side["condition"]:
        raise SystemExit(f"{side['results']}: _meta.json condition {meta_cond} != requested {side['condition']}")
    info = {
        "benchmark": BENCHMARK,
        "run_id": run_id,
        "model_key": args.model,
        "model_id": meta.get("model_id"),
        "provider": meta.get("provider"),
        "base_url": meta.get("base_url"),
        "temperature": 0 if meta.get("supports_temperature") else None,  # harness hard-codes temperature=0
        "language": language,
        "condition": side["condition"],
        "run_label": side["label"],
        "condition_spec": meta.get("condition_spec"),
        "condition_assets": meta.get("condition_assets"),
        "system_prompt_sent": meta.get("system_prompt_sent"),
        "subset": args.subset,
        "n_tasks": len(per),
        "tasks_file": rel(side["tasks"]),
        "tasks_file_sha256": sha256(side["tasks"]),
        "results_file": rel(side["results"]),
        "tool_selection": meta.get("tool_selection"),
        "structured_outputs": meta.get("structured_outputs"),
        "act_without_confirmation": meta.get("act_without_confirmation"),
        "harness_commit": commit,
        "harness_dirty": dirty,
        "started_at": meta.get("started_at"),
        "finished_at": meta.get("finished_at"),
        "total_llm_requests": total,
        "notes": "; ".join(notes),
    }
    return {k: info[k] for k in META_KEYS}


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8", lineterminator="\n", quoting=csv.QUOTE_MINIMAL)


def rebuild_summary(comparisons_dir: Path = COMPARISONS, out: Path = SUMMARY) -> pd.DataFrame:
    """One row per comparison folder (overall metrics), sorted by id."""
    rows = []
    for metrics_path in sorted(comparisons_dir.glob("*/metrics.csv")):
        m = pd.read_csv(metrics_path, dtype=str)
        ov = m[m.scope == "overall"].set_index("metric")
        first = m.iloc[0]
        row = {
            "comparison_id": metrics_path.parent.name,
            "model_key": first.model_key,
            "ref_condition": first.ref_condition,
            "condition": first.condition,
            "n": ov.loc["completion_rate_ref", "n"],
        }
        row.update({k: ov.loc[k, "value"] if k in ov.index else "" for k in SUMMARY_METRICS})
        rows.append(row)
    df = pd.DataFrame(rows, columns=["comparison_id", "model_key", "ref_condition", "condition", "n", *SUMMARY_METRICS])
    out.parent.mkdir(parents=True, exist_ok=True)
    write_csv(df, out)
    return df


# ---------------------------------------------------------------- CLI


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ref", required=True, help="reference condition, e.g. c0")
    p.add_argument("--treat", required=True, help="treatment condition, e.g. c3")
    p.add_argument("--model", required=True, help="model key from MODEL_REGISTRY, e.g. ollama-gemma4-31b")
    p.add_argument("--subset", default="pilot", help="task subset folder under data_bn/ (pilot, smoke10, ...)")
    p.add_argument("--ref_label", default=None, help="run label of the reference run (e.g. rep2)")
    p.add_argument("--treat_label", default=None, help="run label of the treatment run (e.g. rep2)")
    for side in SIDES:
        p.add_argument(f"--{side}_results", default=None, help="override the resolved results CSV")
        p.add_argument(f"--{side}_tasks", default=None, help="override the resolved tasks CSV")
        p.add_argument(f"--{side}_traces", default=None, help="override the resolved _traces.json")
    p.add_argument("--index", default=None, help="task index (default data_bn/<subset>/<subset>_index.csv if present)")
    p.add_argument("--comparison_id", default=None, help="default <subset>_<model>_<treat>_vs_<ref>")
    p.add_argument(
        "--out_dir", default=None, help="default results/comparisons/<comparison_id> (relative = project root)"
    )
    p.add_argument("--no_summary", action="store_true", help="do not rebuild results/summary.csv")
    return p.parse_args(argv)


def main(argv=None) -> Path:
    args = parse_args(argv)
    if str(WB) not in sys.path:
        sys.path.insert(0, str(WB))
    ref_name, treat_name = run_dir_name(args.ref, args.ref_label), run_dir_name(args.treat, args.treat_label)
    if ref_name == treat_name and not (args.ref_results or args.treat_results):
        raise SystemExit("reference and treatment resolve to the same run; use --treat_label for a repeat")
    sides = {s: resolve_side(args, s) for s in SIDES}
    index_path = (
        Path(args.index).resolve() if args.index else ROOT / "data_bn" / args.subset / f"{args.subset}_index.csv"
    )
    index = pd.read_csv(index_path, dtype=str) if index_path.exists() else None
    cid = args.comparison_id or make_comparison_id(args.subset, args.model, ref=ref_name, treat=treat_name)
    out_dir = Path(args.out_dir) if args.out_dir else COMPARISONS / cid
    out_dir = (out_dir if out_dir.is_absolute() else ROOT / out_dir).resolve()
    if not out_dir.is_relative_to(ROOT.resolve()):
        raise SystemExit(f"refusing to write outside the project folder: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    os.chdir(WB)  # the sandbox loads its data from relative paths
    per, metas = {}, {}
    for s in SIDES:
        side = sides[s]
        meta = _results_meta(side["results"])
        language = task_lang(side["condition"])
        run_id = make_run_id(args.subset, side["condition"], side["label"], args.model)
        scored = score_run(side["results"], side["tasks"], index)
        per[s] = per_task_frame(
            scored,
            run_id,
            args.model,
            meta,
            language,
            side["condition"],
            str(side["traces"]) if side["traces"] else None,
            _run_date(side["results"], meta),
        )
        write_csv(per[s], out_dir / f"per_task_{s}.csv")
        metas[s] = run_meta(args, side, run_id, language, meta, per[s])
        with open(out_dir / f"run_meta_{s}.json", "w", encoding="utf-8") as f:
            json.dump(metas[s], f, ensure_ascii=False, indent=2)
            f.write("\n")
    if metas["ref"]["model_id"] != metas["treat"]["model_id"]:
        raise SystemExit(f"model_id differs: {metas['ref']['model_id']} vs {metas['treat']['model_id']}")

    r = per["ref"].set_index("task_uid")
    t = per["treat"].set_index("task_uid")
    common = [u for u in r.index if u in t.index]
    paired = pd.DataFrame(
        {
            "task_uid": common,
            "domain": r.loc[common, "domain"].values,
            "template_id": r.loc[common, "template_id"].values,
            "correct_ref": r.loc[common, "correct"].values,
            "correct_treat": t.loc[common, "correct"].values,
            "side_effect_ref": r.loc[common, "side_effect"].values,
            "side_effect_treat": t.loc[common, "side_effect"].values,
        }
    )
    paired["pair_class"] = [pair_class(a, b) for a, b in zip(paired.correct_ref, paired.correct_treat)]
    write_csv(paired[PAIRED_COLUMNS], out_dir / "paired.csv")
    metrics = compute_comparison_metrics(
        paired, BENCHMARK, args.model, metas["ref"]["model_id"] or "", ref_name, treat_name, full_domain_weights()
    )
    write_csv(metrics, out_dir / "metrics.csv")
    if not args.no_summary and out_dir.parent == COMPARISONS.resolve():
        rebuild_summary()

    ov = metrics[metrics.scope == "overall"].set_index("metric").value
    print(
        f"{cid}: paired n={len(paired)} | completion {ref_name}={ov['completion_rate_ref']} "
        f"{treat_name}={ov['completion_rate_treat']} delta={ov['delta_completion']} "
        f"[{ov['delta_completion_ci95_low']}, {ov['delta_completion_ci95_high']}] "
        f"mcnemar_p={ov['mcnemar_p']} (ref_only={ov['n_ref_only']}, treat_only={ov['n_treat_only']}) | "
        f"side effects {ref_name}={ov['side_effect_rate_ref']} {treat_name}={ov['side_effect_rate_treat']} -> {rel(out_dir)}"
    )
    return out_dir


if __name__ == "__main__":
    main()
