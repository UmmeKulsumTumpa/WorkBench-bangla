#!/usr/bin/env python3
"""Score an EN and a BN WorkBench run with WorkBench's own scorer and compare them (docs/schema.md formats).

Must run with the WorkBench venv (imports `src.evals.metrics`); the script chdirs into WorkBench/ before
scoring because the sandbox loads its data from relative paths. Relative input paths are resolved against the
cwd you launch from; a relative --out_dir is resolved against the project root (never inside WorkBench/).

    source env.sh && cd WorkBench && uv run --frozen python ../scripts/compare_en_bn.py \
        --en_results data/results/pilot_en/<model>_all_<ts>.csv \
        --bn_results data/results/pilot_bn/<model>_all_<ts>.csv \
        --en_tasks ../data_bn/pilot/pilot_en_tasks_and_outcomes.csv \
        --bn_tasks ../data_bn/pilot/pilot_bn_tasks_and_outcomes.csv \
        --model_key <key> --model_id <id> --provider <provider> --condition c1 \
        --comparison_id workbench_pilot_<key>_c1 [--en_traces ... --bn_traces ...]

Scoring: `load_and_score_results(results, tasks)` -> `compute_metrics`, i.e. exactly what `workbench-evaluate`
does (predictions merged with the tasks file on exact task text, `is_correct` / `has_side_effects`). The
task_uid is then attached from the tasks file's `source_file,row_idx` columns. Fallbacks when those columns
are absent: a full file named `<domain>[_bn]_tasks_and_outcomes.csv` gives `workbench:<domain>:<row>`
(optionally restricted to the --index task_uids); otherwise the tasks file is joined to --index by row position.

Outputs in --out_dir: per_task_en.csv, per_task_bn.csv (§1), paired.csv (§2), metrics.csv (§3),
run_meta_en.json, run_meta_bn.json (§5).
"""

from __future__ import annotations

import argparse
import csv
import glob
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
DOMAINS = ["email", "calendar", "analytics", "project_management", "customer_relationship_manager", "multi_domain"]
BENCHMARK = "workbench"
SEED = 20261004
N_BOOT = 10_000

PER_TASK_COLUMNS = [
    "benchmark", "run_id", "model_key", "model_id", "provider", "language", "condition", "task_uid", "domain",
    "template_id", "correct", "side_effect", "error", "n_llm_requests", "n_tool_calls", "run_date",
]
PAIRED_COLUMNS = [
    "task_uid", "domain", "template_id", "correct_en", "correct_bn", "side_effect_en", "side_effect_bn", "pair_class",
]
METRICS_COLUMNS = ["benchmark", "model_key", "model_id", "condition", "scope", "metric", "value", "n"]
META_KEYS = [
    "benchmark", "run_id", "model_key", "model_id", "provider", "base_url", "temperature", "language", "condition",
    "subset", "n_tasks", "tasks_file", "tasks_file_sha256", "tool_selection", "structured_outputs",
    "act_without_confirmation", "harness_commit", "patch_files", "started_at", "finished_at", "total_llm_requests",
    "notes",
]
FULL_FILE_RE = re.compile(r"^(?P<domain>[a-z_]+?)(?:_bn)?_tasks_and_outcomes\.csv$")


# ---------------------------------------------------------------- statistics


def mcnemar_exact(b: int, c: int) -> float:
    """Exact two-sided McNemar test: binomial(b+c, 0.5) on the discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def paired_bootstrap_ci(en, bn, n_boot: int = N_BOOT, seed: int = SEED, alpha: float = 0.05) -> tuple[float, float]:
    """Percentile CI of mean(bn) - mean(en), resampling tasks (pairs) with replacement."""
    diff = np.asarray(bn, dtype=float) - np.asarray(en, dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(diff), size=(n_boot, len(diff)))
    means = diff[idx].mean(axis=1)
    low, high = np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(low), float(high)


def pair_class(correct_en: int, correct_bn: int) -> str:
    return {(1, 1): "both_correct", (1, 0): "en_only", (0, 1): "bn_only", (0, 0): "both_wrong"}[
        (int(correct_en), int(correct_bn))
    ]


def _rate(x: float) -> str:
    return f"{x:.4f}"


def compute_comparison_metrics(
    paired: pd.DataFrame, benchmark: str, model_key: str, model_id: str, condition: str, weights: dict[str, float]
) -> pd.DataFrame:
    """Long-format metrics. Overall: rates, deltas, McNemar, bootstrap CIs, domain-reweighted completion.
    Per domain: descriptive rates/deltas/discordant counts only (pilot_design §5: no per-domain tests)."""
    rows = []

    def add(scope, metric, value, n):
        rows.append([benchmark, model_key, model_id, condition, scope, metric, value, n])

    def describe(scope, df):
        n = len(df)
        ce, cb = df.correct_en.astype(int), df.correct_bn.astype(int)
        se, sb = df.side_effect_en.astype(int), df.side_effect_bn.astype(int)
        add(scope, "completion_rate_en", _rate(ce.mean()), n)
        add(scope, "completion_rate_bn", _rate(cb.mean()), n)
        add(scope, "delta_completion", _rate(cb.mean() - ce.mean()), n)
        add(scope, "side_effect_rate_en", _rate(se.mean()), n)
        add(scope, "side_effect_rate_bn", _rate(sb.mean()), n)
        add(scope, "delta_side_effect", _rate(sb.mean() - se.mean()), n)
        b, c = int(((ce == 1) & (cb == 0)).sum()), int(((ce == 0) & (cb == 1)).sum())
        add(scope, "n_en_only", str(b), n)
        add(scope, "n_bn_only", str(c), n)
        return ce, cb, se, sb, b, c

    n = len(paired)
    ce, cb, se, sb, b, c = describe("overall", paired)
    add("overall", "mcnemar_p", f"{mcnemar_exact(b, c):.4f}", n)
    lo, hi = paired_bootstrap_ci(ce, cb)
    add("overall", "delta_completion_ci95_low", _rate(lo), n)
    add("overall", "delta_completion_ci95_high", _rate(hi), n)
    lo, hi = paired_bootstrap_ci(se, sb)
    add("overall", "delta_side_effect_ci95_low", _rate(lo), n)
    add("overall", "delta_side_effect_ci95_high", _rate(hi), n)
    by_dom = paired.groupby("domain")
    present = [d for d in weights if d in by_dom.groups]
    if present:
        wsum = sum(weights[d] for d in present)
        for lang in ("en", "bn"):
            val = sum(weights[d] * by_dom.get_group(d)[f"correct_{lang}"].astype(int).mean() for d in present) / wsum
            add("overall", f"completion_rate_{lang}_weighted", _rate(val), n)
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


def make_run_id(subset: str, language: str, model_key: str, condition: str) -> str:
    run_id = f"{BENCHMARK}_{subset}_{language}_{model_key}"
    return run_id if condition == "en" else f"{run_id}_{condition}"


# ---------------------------------------------------------------- scoring one run


def _results_meta(results_path: str, override: str | None) -> dict:
    path = override
    if path is None:
        for suffix in (".csv.gz", ".csv"):
            if results_path.endswith(suffix):
                path = results_path[: -len(suffix)] + "_meta.json"
                break
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _run_date(results_path: str, meta: dict) -> str:
    if meta.get("started_at"):
        return str(meta["started_at"])[:10]
    m = re.search(r"_(\d{4}-\d{2}-\d{2})_\d{2}-\d{2}-\d{2}\.csv", os.path.basename(results_path))
    return m.group(1) if m else ""


def score_run(results_path: str, tasks_path: str, index: pd.DataFrame | None) -> pd.DataFrame:
    """WorkBench's own pipeline (merge on task text, is_correct / has_side_effects), plus task_uid."""
    from src.evals.metrics import load_and_score_results  # noqa: PLC0415  (needs WorkBench cwd + sys.path)

    raw = pd.read_csv(tasks_path, dtype=str)
    tasks = attach_task_uid(raw, tasks_path, index)
    if not tasks.task.is_unique:
        raise ValueError(f"{tasks_path}: task texts are not unique; cannot match predictions by text")
    tasks["template_id"] = template_ids(tasks, index)
    gt_path, tmp = tasks_path, None
    if len(tasks) != len(raw):  # index restricted the file: score against exactly those rows
        fd, tmp = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        tasks[list(raw.columns)].to_csv(tmp, index=False, quoting=csv.QUOTE_ALL)
        gt_path = tmp
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            df = load_and_score_results(results_path, gt_path)
    finally:
        if tmp:
            os.remove(tmp)
    df = df.merge(tasks[["task", "task_uid", "domain", "template_id"]], on="task", how="left", validate="1:1")
    assert df.task_uid.notna().all()
    return df


def per_task_frame(df, run_id, args, language, condition, traces, run_date) -> pd.DataFrame:
    counts = load_trace_counts(traces) if traces else None
    out = pd.DataFrame(
        {
            "benchmark": BENCHMARK,
            "run_id": run_id,
            "model_key": args.model_key,
            "model_id": args.model_id,
            "provider": args.provider,
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


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_meta(args, run_id, language, condition, tasks_path, results_path, meta, per, traces) -> dict:
    commit = subprocess.run(["git", "-C", str(WB), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    patches = sorted(os.path.relpath(p, ROOT) for p in glob.glob(str(ROOT / "patches" / "*.patch")))
    supports_t = meta.get("supports_temperature")
    total = int(per.n_llm_requests.astype(int).sum()) if traces else None
    rel = lambda p: os.path.relpath(p, ROOT) if Path(p).resolve().is_relative_to(ROOT) else str(p)  # noqa: E731
    info = {
        "benchmark": BENCHMARK,
        "run_id": run_id,
        "model_key": args.model_key,
        "model_id": args.model_id,
        "provider": args.provider,
        "base_url": meta.get("base_url"),
        "temperature": 0 if supports_t else None,  # harness hard-codes temperature=0 (inference.py)
        "language": language,
        "condition": condition,
        "subset": args.subset,
        "n_tasks": len(per),
        "tasks_file": rel(tasks_path),
        "tasks_file_sha256": sha256(tasks_path),
        "tool_selection": meta.get("tool_selection"),
        "structured_outputs": meta.get("structured_outputs"),
        "act_without_confirmation": meta.get("act_without_confirmation"),
        "harness_commit": commit.stdout.strip(),
        "patch_files": patches,
        "started_at": meta.get("started_at"),
        "finished_at": meta.get("finished_at"),
        "total_llm_requests": total,
        "notes": f"results_file={rel(results_path)}"
        + ("" if meta else "; no _meta.json sidecar found")
        + (f"; meta model_id={meta['model_id']}" if meta.get("model_id") and meta["model_id"] != args.model_id else ""),
    }
    return {k: info[k] for k in META_KEYS}


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8", lineterminator="\n", quoting=csv.QUOTE_MINIMAL)


# ---------------------------------------------------------------- CLI


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--en_results", required=True)
    p.add_argument("--bn_results", required=True)
    p.add_argument("--en_tasks", required=True)
    p.add_argument("--bn_tasks", required=True)
    p.add_argument("--index", default=None, help="task index (task_uid,source_file,row_idx[,template_id])")
    p.add_argument("--model_key", required=True)
    p.add_argument("--model_id", required=True)
    p.add_argument("--provider", required=True)
    p.add_argument("--condition", default="c1", choices=["c1", "c2"])
    p.add_argument("--comparison_id", required=True)
    p.add_argument("--subset", default="pilot")
    p.add_argument("--out_dir", default=None, help="default results/<comparison_id> (relative = project root)")
    p.add_argument("--en_traces", default=None)
    p.add_argument("--bn_traces", default=None)
    p.add_argument("--en_meta", default=None, help="override the results' _meta.json sidecar")
    p.add_argument("--bn_meta", default=None)
    return p.parse_args(argv)


def main(argv=None) -> Path:
    args = parse_args(argv)
    absp = lambda p: os.path.abspath(p) if p else p  # noqa: E731
    for k in ("en_results", "bn_results", "en_tasks", "bn_tasks", "index", "en_traces", "bn_traces", "en_meta", "bn_meta"):
        setattr(args, k, absp(getattr(args, k)))
    out_dir = Path(args.out_dir or f"results/{args.comparison_id}")
    out_dir = out_dir if out_dir.is_absolute() else ROOT / out_dir
    out_dir = out_dir.resolve()
    if not out_dir.is_relative_to(ROOT.resolve()):
        raise SystemExit(f"refusing to write outside the project folder: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    os.chdir(WB)
    if str(WB) not in sys.path:
        sys.path.insert(0, str(WB))

    index = pd.read_csv(args.index, dtype=str) if args.index else None
    per = {}
    for lang, cond in (("en", "en"), ("bn", args.condition)):
        results, tasks, traces = getattr(args, f"{lang}_results"), getattr(args, f"{lang}_tasks"), getattr(args, f"{lang}_traces")
        meta = _results_meta(results, getattr(args, f"{lang}_meta"))
        run_id = make_run_id(args.subset, lang, args.model_key, cond)
        scored = score_run(results, tasks, index)
        per[lang] = per_task_frame(scored, run_id, args, lang, cond, traces, _run_date(results, meta))
        write_csv(per[lang], out_dir / f"per_task_{lang}.csv")
        with open(out_dir / f"run_meta_{lang}.json", "w", encoding="utf-8") as f:
            json.dump(run_meta(args, run_id, lang, cond, tasks, results, meta, per[lang], traces), f, ensure_ascii=False, indent=2)
            f.write("\n")

    en = per["en"].set_index("task_uid")
    bn = per["bn"].set_index("task_uid")
    common = [u for u in en.index if u in bn.index]
    paired = pd.DataFrame(
        {
            "task_uid": common,
            "domain": en.loc[common, "domain"].values,
            "template_id": en.loc[common, "template_id"].values,
            "correct_en": en.loc[common, "correct"].values,
            "correct_bn": bn.loc[common, "correct"].values,
            "side_effect_en": en.loc[common, "side_effect"].values,
            "side_effect_bn": bn.loc[common, "side_effect"].values,
        }
    )
    paired["pair_class"] = [pair_class(e, b) for e, b in zip(paired.correct_en, paired.correct_bn)]
    write_csv(paired[PAIRED_COLUMNS], out_dir / "paired.csv")
    metrics = compute_comparison_metrics(paired, BENCHMARK, args.model_key, args.model_id, args.condition, full_domain_weights())
    write_csv(metrics, out_dir / "metrics.csv")

    ov = metrics[metrics.scope == "overall"].set_index("metric").value
    print(
        f"paired n={len(paired)} (en {len(en)}, bn {len(bn)}) | completion en={ov['completion_rate_en']} "
        f"bn={ov['completion_rate_bn']} delta={ov['delta_completion']} "
        f"[{ov['delta_completion_ci95_low']}, {ov['delta_completion_ci95_high']}] "
        f"mcnemar_p={ov['mcnemar_p']} (en_only={ov['n_en_only']}, bn_only={ov['n_bn_only']}) | "
        f"side effects en={ov['side_effect_rate_en']} bn={ov['side_effect_rate_bn']} -> {out_dir}"
    )
    return out_dir


if __name__ == "__main__":
    main()
