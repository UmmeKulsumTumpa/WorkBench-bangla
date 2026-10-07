#!/usr/bin/env python3
"""Failure-analysis pipeline helpers (instructions/failure_analysis_pipeline.md; rules in
results/failure_pipeline/annotation_rules.md): task table, paired statistics, label counts.

English = condition c0, Bangla = condition c6, 90-task pilot, one folder per model:
results/failure_pipeline/pilot_<model>_c6_vs_c0/. No model or API calls; reads existing runs only.

    source env.sh && uv run --project WorkBench --frozen python scripts/failure_pipeline.py table --model ollama-gemma4-31b
    ... stats --all [--labels labels_final.csv]      # both models, Holm across the two McNemar p-values
    ... stats --model <M> [--labels labels_final.csv]
    ... counts --all --labels labels_final.csv       # pipeline section 10 distributions, merged into stats.json
    ... validate --model <M> --labels labels.csv     # check a label file against the vocabularies and the task table

`table` re-scores each run with compare_conditions.score_run (WorkBench's own scorer) and asserts the result against
the existing comparison folder (per_task_ref/treat.csv `correct`, paired.csv `pair_class`). `stats` reads
task_table.csv. Statistics reuse compare_conditions.mcnemar_exact / paired_bootstrap_ci (seed 20261004).
Without --labels, `stats` runs and the label-dependent sensitivity rows are null.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
from pathlib import Path

import numpy as np

csv.field_size_limit(sys.maxsize)

ROOT = Path(__file__).resolve().parents[1]
WB = ROOT / "WorkBench"
sys.path.insert(0, str(Path(__file__).resolve().parent))

import compare_conditions as cc  # noqa: E402  (sibling script; reuse its statistics and run loading)

MODELS = ["ollama-gemma4-31b", "ollama-gpt-oss-20b"]
SUBSET = "pilot"
REF, TREAT = "c0", "c6"  # English, Bangla
DATASET = "WorkBench"
OUT_ROOT = ROOT / "results" / "failure_pipeline"

TABLE_COLUMNS = [
    "dataset",
    "model",
    "task_uid",
    "domain",
    "run_id_en",
    "run_id_bn",
    "en_pass",
    "bn_pass",
    "pair_class",
    "en_trajectory",
    "bn_trajectory",
    "en_final_state",
    "bn_final_state",
    "gt_state",
    "en_error",
    "bn_error",
]
LABEL_COLUMNS = [
    "task_uid",
    "domain",
    "pair_class",
    "side",
    "first_failure_point",
    "failure_type",
    "confound",
    "decision_tree",
    "evidence",
    "not_general_reason",
    "annotator",
]
ANNOTATORS = ("A1", "A2", "ADJ")

# Controlled vocabularies, in the order and wording of pipeline sections 5, 6 and 7 (label text only).
FIRST_FAILURE_POINTS = [
    "Instruction understanding",
    "Entity or slot grounding",
    "Task constraint preservation",
    "Planning",
    "Tool selection",
    "Tool-argument construction",
    "Tool execution",
    "Result verification",
    "Premature termination",
    "Final response only",
    "Unclear",
]
FAILURE_TYPES = [
    "Understanding failure",
    "Planning failure",
    "Wrong tool/action",
    "Wrong tool argument",
    "Execution/environment failure",
    "Verification failure",
    "Premature abandonment",
    "Dialogue-state failure",
    "Unclear",
]
CONFOUNDS = [
    "Genuine Bangla-related agent failure",
    "Bangla user-simulator error",
    "Translation/localization error",
    "Tool/environment failure",
    "Benchmark/task ambiguity",
    "General model weakness present in both English and Bangla",
    "Unclear",
]
GENUINE = CONFOUNDS[0]
USER_SIM = CONFOUNDS[1]
TRANSLATION = CONFOUNDS[2]
TOOL_ENV = CONFOUNDS[3]
VOCAB = {"first_failure_point": FIRST_FAILURE_POINTS, "failure_type": FAILURE_TYPES, "confound": CONFOUNDS}

PAIR_CLASSES = ("both_correct", "ref_only", "treat_only", "both_wrong")  # ref = EN (c0), treat = BN (c6)
DECISION_TREE_RE = re.compile(r"^S1=(ok|fail|na);S2=(ok|fail|na);S3=(ok|fail|na);S4=(ok|fail|na);S5=(ok|fail|na);"
                              r"S6=(ok|fail|na);S7=(ok|fail|na)$")
Z95 = 1.959963984540054


# ---------------------------------------------------------------- statistics


def wilson_ci(k: int, n: int, z: float = Z95) -> tuple[float, float] | None:
    """Wilson score interval for a proportion k/n; None when n = 0."""
    if n == 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def holm_adjust(pvals: dict[str, float]) -> dict[str, float]:
    """Holm-Bonferroni adjusted p-values (step-down, monotone, capped at 1)."""
    order = sorted(pvals, key=lambda k: pvals[k])
    m = len(order)
    out, running = {}, 0.0
    for i, key in enumerate(order):
        running = max(running, (m - i) * pvals[key])
        out[key] = min(1.0, running)
    return out


def _binom_tail_ge(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p)."""
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact (Clopper-Pearson) CI for a binomial proportion k/n, by bisection on the binomial tails."""
    if n <= 0:
        raise ValueError("n must be positive")

    def solve(f, target):  # f is increasing in p; find p with f(p) = target
        lo, hi = 0.0, 1.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if f(mid) < target:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    # P(X >= k) increases with p: the lower limit has P(X >= k) = alpha/2; the upper limit has P(X <= k) = alpha/2,
    # i.e. P(X >= k+1) = 1 - alpha/2.
    low = 0.0 if k == 0 else solve(lambda p: _binom_tail_ge(k, n, p), alpha / 2)
    high = 1.0 if k == n else solve(lambda p: _binom_tail_ge(k + 1, n, p), 1 - alpha / 2)
    return low, high


def _odds(p: float) -> float | None:
    return None if p >= 1.0 else p / (1.0 - p)


def paired_odds_ratio(b: int, c: int, alpha: float = 0.05) -> dict:
    """Discordant-pair odds ratio b/c (b = EN-pass/BN-fail, c = EN-fail/BN-pass) with the exact conditional CI:
    Clopper-Pearson on p = b/(b+c), transformed to OR = p/(1-p). Infinite values are null with an *_is_infinite flag."""
    out = {
        "b": b,
        "c": c,
        "point": None,
        "point_is_infinite": False,
        "ci95_low": None,
        "ci95_high": None,
        "ci95_high_is_infinite": False,
        "method": "exact conditional (Clopper-Pearson on b/(b+c), OR = p/(1-p))",
    }
    n = b + c
    if n == 0:
        return out  # no discordant pairs: OR undefined
    if c == 0:
        out["point_is_infinite"] = True
    else:
        out["point"] = b / c
    low_p, high_p = clopper_pearson(b, n, alpha)
    out["ci95_low"] = _odds(low_p) if low_p > 0 else 0.0
    high = _odds(high_p)
    if high is None:
        out["ci95_high_is_infinite"] = True
    else:
        out["ci95_high"] = high
    return out


def bootstrap_indices(n: int, n_boot: int = cc.N_BOOT, seed: int = cc.SEED) -> np.ndarray:
    """The resample indices used by compare_conditions.paired_bootstrap_ci (same seed, same call order)."""
    rng = np.random.default_rng(seed)
    return rng.integers(0, n, size=(n_boot, n))


def bootstrap_gap_melr(en, bn) -> dict:
    """95% percentile CIs for the gap (EN - BN) and MELR = (EN - BN) / EN from the *same* resamples.

    The gap CI is compare_conditions.paired_bootstrap_ci (treat = EN, ref = BN, so mean(EN) - mean(BN)); the
    MELR CI uses identical resample indices. A resample with EN rate 0 has no MELR and is excluded (counted)."""
    en, bn = np.asarray(en, dtype=float), np.asarray(bn, dtype=float)
    n = len(en)
    if n == 0:
        return {"gap_ci95": None, "melr_ci95": None, "melr_undefined_resamples": None, "n_boot": cc.N_BOOT}
    gap_lo, gap_hi = cc.paired_bootstrap_ci(bn, en)
    idx = bootstrap_indices(n)
    en_m, bn_m = en[idx].mean(axis=1), bn[idx].mean(axis=1)
    own = np.percentile(en_m - bn_m, [2.5, 97.5])
    if not np.allclose(own, [gap_lo, gap_hi]):  # guard: the shared-resample claim must hold
        raise AssertionError("bootstrap resamples differ from compare_conditions.paired_bootstrap_ci")
    valid = en_m > 0
    melr_ci = None
    if valid.any():
        lo, hi = np.percentile((en_m[valid] - bn_m[valid]) / en_m[valid], [2.5, 97.5])
        melr_ci = [float(lo), float(hi)]
    return {
        "gap_ci95": [gap_lo, gap_hi],
        "melr_ci95": melr_ci,
        "melr_undefined_resamples": int((~valid).sum()),
        "n_boot": cc.N_BOOT,
    }


def paired_metrics(pairs: list[dict], inference: bool = True) -> dict:
    """All pipeline section 2 / 11 statistics for one set of pairs (each pair: en, bn in {0,1}).

    inference=False (per-domain, n = 15) keeps rates, Wilson CIs, gap, MELR and counts but no p-value, bootstrap
    CI or odds ratio: domain numbers are descriptive only."""
    n = len(pairs)
    en = [int(p["en"]) for p in pairs]
    bn = [int(p["bn"]) for p in pairs]
    a = sum(1 for e, b_ in zip(en, bn) if e and b_)
    b = sum(1 for e, b_ in zip(en, bn) if e and not b_)
    c = sum(1 for e, b_ in zip(en, bn) if not e and b_)
    d = sum(1 for e, b_ in zip(en, bn) if not e and not b_)
    en_k, bn_k = a + b, a + c
    en_rate = en_k / n if n else None
    bn_rate = bn_k / n if n else None
    gap = en_rate - bn_rate if n else None
    melr = (gap / en_rate) if n and en_rate else None  # undefined if EN = 0
    out = {
        "n": n,
        "en_pass": en_k,
        "bn_pass": bn_k,
        "en_rate": en_rate,
        "en_rate_ci95_wilson": wilson_ci(en_k, n),
        "bn_rate": bn_rate,
        "bn_rate_ci95_wilson": wilson_ci(bn_k, n),
        "gap": gap,
        "risk_difference": gap,
        "melr": melr,
        "melr_note": None if melr is not None else "undefined: EN success rate is 0 (or n = 0)",
        "pair_counts": {
            "en_pass_bn_pass": a,
            "en_pass_bn_fail": b,
            "en_fail_bn_pass": c,
            "en_fail_bn_fail": d,
        },
    }
    if inference:
        out["gap_ci95_paired_bootstrap"] = None
        out["melr_ci95_paired_bootstrap"] = None
        boot = bootstrap_gap_melr(en, bn)
        out["gap_ci95_paired_bootstrap"] = boot["gap_ci95"]
        out["melr_ci95_paired_bootstrap"] = boot["melr_ci95"]
        out["melr_undefined_resamples"] = boot["melr_undefined_resamples"]
        out["n_boot"] = boot["n_boot"]
        out["bootstrap_seed"] = cc.SEED
        out["mcnemar_exact_p"] = cc.mcnemar_exact(b, c)
        out["paired_odds_ratio"] = paired_odds_ratio(b, c)
    return out


# ---------------------------------------------------------------- labels


def _canon(value: str, vocab: list[str]) -> str | None:
    key = value.strip().rstrip(".").casefold()
    for label in vocab:
        if label.casefold() == key:
            return label
    return None


def read_csv_rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_labels(path: Path, annotator: str | None = None) -> list[dict]:
    """Read a labels CSV, check its columns, optionally keep one annotator's rows."""
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        rows = list(reader)
    if cols != LABEL_COLUMNS:
        raise ValueError(f"{path}: columns must be exactly {LABEL_COLUMNS}, got {cols}")
    if annotator:
        rows = [r for r in rows if r["annotator"] == annotator]
    return rows


def expected_sides(pair_class: str) -> tuple[str, ...]:
    """Which sides carry labels: EN-pass/BN-fail -> BN; both fail -> EN and BN; EN-fail/BN-pass -> EN."""
    return {"both_correct": (), "ref_only": ("BN",), "treat_only": ("EN",), "both_wrong": ("EN", "BN")}[pair_class]


def validate_labels(rows: list[dict], table: list[dict], require_complete: bool = True) -> list[dict]:
    """Return the rows with vocabulary values canonicalised; raise ValueError listing every problem."""
    by_uid = {t["task_uid"]: t for t in table}
    problems, seen, out = [], set(), []
    for i, r in enumerate(rows, start=2):  # line numbers as in the file (header = 1)
        where = f"line {i} ({r.get('task_uid')}, {r.get('side')})"
        r = dict(r)
        t = by_uid.get(r["task_uid"])
        if t is None:
            problems.append(f"{where}: task_uid not in task table")
            continue
        if r["side"] not in ("EN", "BN"):
            problems.append(f"{where}: side must be EN or BN")
            continue
        if r["domain"] != t["domain"] or r["pair_class"] != t["pair_class"]:
            problems.append(f"{where}: domain/pair_class do not match the task table")
        if r["side"] not in expected_sides(t["pair_class"]):
            problems.append(f"{where}: no {r['side']} label is expected for pair_class {t['pair_class']}")
        key = (r["task_uid"], r["side"])
        if key in seen:
            problems.append(f"{where}: duplicate (task_uid, side)")
        seen.add(key)
        for col, vocab in VOCAB.items():
            canon = _canon(r[col], vocab)
            if canon is None:
                problems.append(f"{where}: {col}={r[col]!r} is not in the controlled vocabulary")
            r[col] = canon or r[col]
        if r["confound"] == USER_SIM:
            problems.append(f"{where}: {USER_SIM!r} is structurally impossible in WorkBench and must not be used")
        if r["annotator"] not in ANNOTATORS:
            problems.append(f"{where}: annotator must be one of {ANNOTATORS}")
        if not r["evidence"].strip():
            problems.append(f"{where}: evidence is empty")
        if t["pair_class"] == "ref_only":
            if not DECISION_TREE_RE.match(r["decision_tree"]):
                problems.append(f"{where}: decision_tree must look like S1=ok;S2=na;...;S7=ok")
            if not r["not_general_reason"].strip():
                problems.append(f"{where}: not_general_reason is required for EN-pass/BN-fail")
        elif r["decision_tree"].strip():
            problems.append(f"{where}: decision_tree is only for EN-pass/BN-fail rows")
        out.append(r)
    if require_complete:
        for t in table:
            for side in expected_sides(t["pair_class"]):
                if (t["task_uid"], side) not in seen:
                    problems.append(f"missing label row: {t['task_uid']} side {side} ({t['pair_class']})")
    if problems:
        raise ValueError("label file problems:\n  " + "\n  ".join(problems))
    return out


# ---------------------------------------------------------------- stats


def pairs_from_table(table: list[dict]) -> list[dict]:
    return [
        {"task_uid": t["task_uid"], "domain": t["domain"], "en": int(t["en_pass"]), "bn": int(t["bn_pass"])}
        for t in table
    ]


def drop_by_confound(pairs: list[dict], labels: list[dict], confound: str) -> tuple[list[dict], list[str]]:
    """Remove every pair in which any labelled failure (EN or BN side) has the given confound."""
    drop = {r["task_uid"] for r in labels if r["confound"] == confound}
    return [p for p in pairs if p["task_uid"] not in drop], sorted(drop & {p["task_uid"] for p in pairs})


def sensitivity(pairs: list[dict], labels: list[dict] | None) -> dict:
    out = {"all": {"description": "all pairs", **paired_metrics(pairs)}}
    specs = [
        ("no_translation", TRANSLATION, "pairs with a labelled failure confounded by translation removed"),
        (
            "no_user_simulator",
            USER_SIM,
            "pairs with a user-simulator confound removed; identical to 'all' (WorkBench has no user simulator)",
        ),
        ("no_tool_environment", TOOL_ENV, "pairs with a labelled tool/environment failure removed"),
    ]
    for key, confound, desc in specs:
        if labels is None:
            out[key] = None
            continue
        kept, removed = drop_by_confound(pairs, labels, confound)
        out[key] = {
            "description": desc,
            "confound": confound,
            "n_removed": len(removed),
            "removed_task_uids": removed,
            **paired_metrics(kept),
        }
    return out


def model_stats(model: str, table: list[dict], labels: list[dict] | None, labels_file: str | None = None) -> dict:
    pairs = pairs_from_table(table)
    overall = paired_metrics(pairs)
    domains = {}
    for dom in sorted({p["domain"] for p in pairs}, key=lambda d: (cc.DOMAINS.index(d) if d in cc.DOMAINS else 99, d)):
        domains[dom] = paired_metrics([p for p in pairs if p["domain"] == dom], inference=False)
    return {
        "model": model,
        "dataset": DATASET,
        "comparison": f"{TREAT}_vs_{REF}",
        "en_condition": REF,
        "bn_condition": TREAT,
        "n_pairs": len(pairs),
        "labels_provided": labels is not None,
        "labels_file": labels_file,
        "overall": overall,
        "holm": None,
        "domains": domains,
        "domains_note": "descriptive only (n = 15 per domain): no p-values or intervals",
        "sensitivity": sensitivity(pairs, labels),
    }


def apply_holm(stats_by_model: dict[str, dict]) -> None:
    """Holm across the McNemar p-values of the given model comparisons (the primary 'all pairs' analysis)."""
    raw = {m: s["overall"]["mcnemar_exact_p"] for m, s in stats_by_model.items()}
    adj = holm_adjust(raw)
    for m, s in stats_by_model.items():
        s["holm"] = {
            "family": list(raw),
            "p_raw": raw[m],
            "p_holm": adj[m],
            "family_p_raw": raw,
            "family_p_holm": adj,
            "method": "Holm-Bonferroni across the McNemar p-values of the model comparisons",
        }
        s["overall"]["mcnemar_p_holm"] = adj[m]


# ---------------------------------------------------------------- counts (pipeline section 10)


def distribution(values: list[str], vocab: list[str]) -> dict:
    n = len(values)
    unknown = sorted(set(values) - set(vocab))
    if unknown:
        raise ValueError(f"values outside the vocabulary: {unknown}")
    return {
        "denominator": n,
        "counts": {label: {"n": values.count(label), "share": (values.count(label) / n if n else None)} for label in vocab},
    }


def breakdown(rows: list[dict]) -> dict:
    """The three label distributions for a set of EN-pass/BN-fail labels."""
    return {
        "n_cases": len(rows),
        "failure_type": distribution([r["failure_type"] for r in rows], FAILURE_TYPES),
        "first_failure_point": distribution([r["first_failure_point"] for r in rows], FIRST_FAILURE_POINTS),
        "confound": distribution([r["confound"] for r in rows], CONFOUNDS),
    }


def ef_bf_cases(labels: list[dict], table: list[dict]) -> list[dict]:
    """BN-side labels of the EN-pass/BN-fail pairs (the cleanest Bangla-degradation group)."""
    cls = {t["task_uid"]: t["pair_class"] for t in table}
    return [r for r in labels if r["side"] == "BN" and cls.get(r["task_uid"]) == "ref_only"]


def model_counts(table: list[dict], labels: list[dict]) -> dict:
    """Items 1-7 and the dataset-wise / domain-wise cuts (items 8, 10) for one model; model-wise is added by
    `all_counts`. Cases = EN-pass/BN-fail pairs, labelled on the BN side."""
    cases = ef_bf_cases(labels, table)
    n_pairs = len(table)
    removed = {c: sum(1 for r in cases if r["confound"] == c) for c in (USER_SIM, TRANSLATION, TOOL_ENV)}
    remaining = [r for r in cases if r["confound"] not in removed]
    genuine = sum(1 for r in remaining if r["confound"] == GENUINE)
    base = breakdown(cases)
    domains = {}
    for dom in sorted({t["domain"] for t in table}, key=lambda d: (cc.DOMAINS.index(d) if d in cc.DOMAINS else 99, d)):
        domains[dom] = {
            "n_pairs": sum(1 for t in table if t["domain"] == dom),
            **breakdown([r for r in cases if r["domain"] == dom]),
        }
    return {
        "population": "EN-pass/BN-fail pairs, BN-side labels",
        "n_pairs": n_pairs,
        "n_cases": len(cases),
        "item_1_failure_type": base["failure_type"],
        "item_2_first_failure_point": base["first_failure_point"],
        "item_3_confound": base["confound"],
        "item_4_genuine_after_filtering": {
            "n_cases": len(cases),
            "filter_removes": [USER_SIM, TRANSLATION, TOOL_ENV],
            "n_removed_by_filter": len(cases) - len(remaining),
            "n_remaining": len(remaining),
            "n_genuine_bangla_related": genuine,
            "genuine_share_of_remaining": genuine / len(remaining) if remaining else None,
            "genuine_share_of_cases": genuine / len(cases) if cases else None,
        },
        "item_5_user_simulator_caused": {"n": removed[USER_SIM], "n_cases": len(cases)},
        "item_6_translation_caused": {"n": removed[TRANSLATION], "n_cases": len(cases)},
        "item_7_tool_environment_caused": {"n": removed[TOOL_ENV], "n_cases": len(cases)},
        "item_8_dataset_wise": {DATASET: {"n_pairs": n_pairs, **base}},
        "item_10_domain_wise": domains,
    }


def all_counts(per_model: dict[str, tuple[list[dict], list[dict]]]) -> dict[str, dict]:
    """Per-model counts, each with item 9 (model-wise: every model's breakdown side by side)."""
    counts = {m: model_counts(t, lab) for m, (t, lab) in per_model.items()}
    model_wise = {m: {"n_pairs": len(t), **breakdown(ef_bf_cases(lab, t))} for m, (t, lab) in per_model.items()}
    for m in counts:
        counts[m]["item_9_model_wise"] = model_wise
    return counts


# ---------------------------------------------------------------- task table


def check_alignment(en_uids: list[str], bn_uids: list[str], expected: list[str] | None = None) -> None:
    """EN and BN runs must cover the same task_uids, once each, in the same order (and the expected set)."""
    problems = []
    for name, uids in (("EN", en_uids), ("BN", bn_uids)):
        if len(uids) != len(set(uids)):
            problems.append(f"{name} has duplicate task_uids")
    if len(en_uids) != len(bn_uids):
        problems.append(f"length differs: EN {len(en_uids)} vs BN {len(bn_uids)}")
    if set(en_uids) != set(bn_uids):
        problems.append(f"task_uid sets differ: EN-only {sorted(set(en_uids) - set(bn_uids))[:5]}, "
                        f"BN-only {sorted(set(bn_uids) - set(en_uids))[:5]}")
    elif en_uids != bn_uids:
        pos = next(i for i, (x, y) in enumerate(zip(en_uids, bn_uids)) if x != y)
        problems.append(f"same task_uids but different order (first difference at position {pos}: "
                        f"EN {en_uids[pos]} vs BN {bn_uids[pos]})")
    if expected is not None and set(en_uids) != set(expected):
        problems.append("task_uids differ from the expected task index")
    if problems:
        raise SystemExit("task_uid alignment FAILED: " + "; ".join(problems))


def split_calls(calls: list[str], side_effect_names: set[str], name_of, all_names: set[str] | None = None) -> dict:
    """State-changing calls (WorkBench's tools_with_side_effects), read-only calls and, when `all_names` is given,
    unrecognised calls (a tool name WorkBench does not have: the executor rejects them, so they change nothing),
    each in call order."""
    known = all_names
    out = {"state_changing": [], "read_only": []}
    if known is not None:
        out["unrecognised"] = []
    for c in calls:
        name = name_of(c)
        if name in side_effect_names:
            out["state_changing"].append(c)
        elif known is None or name in known:
            out["read_only"].append(c)
        else:
            out["unrecognised"].append(c)
    return out


def find_trace_index(task: str, trace_tasks: list[str]) -> int:
    """Index of the trace entry whose task text equals `task` (exactly one required)."""
    hits = [i for i, t in enumerate(trace_tasks) if t == task]
    if len(hits) != 1:
        raise SystemExit(f"trace match failed: {len(hits)} entries for task text {task[:60]!r}")
    return hits[0]


def _json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _score_sides(model: str):
    """Score the EN and BN runs with compare_conditions' loaders (WorkBench cwd and sys.path, as cc.main does)."""
    if str(WB) not in sys.path:
        sys.path.insert(0, str(WB))
    index = cc.pd.read_csv(ROOT / "data_bn" / SUBSET / f"{SUBSET}_index.csv", dtype=str)
    ns = argparse.Namespace(
        subset=SUBSET, model=model, ref=REF, treat=TREAT, ref_label=None, treat_label=None,
        ref_results=None, treat_results=None, ref_tasks=None, treat_tasks=None, ref_traces=None, treat_traces=None,
    )
    cwd = os.getcwd()
    os.chdir(WB)
    try:
        sides = {s: cc.resolve_side(ns, s) for s in cc.SIDES}
        scored = {s: cc.score_run(sides[s]["results"], sides[s]["tasks"], index) for s in cc.SIDES}
        from src.evals.evaluation import get_function_name  # noqa: PLC0415
        from src.tools.toolkits import all_tools, tools_with_side_effects  # noqa: PLC0415
    finally:
        os.chdir(cwd)
    return sides, scored, index, ({t.name for t in tools_with_side_effects}, {t.name for t in all_tools}), get_function_name


def build_table(model: str) -> list[dict]:
    sides, scored, index, (side_effect_names, all_names), name_of = _score_sides(model)
    en, bn = scored["ref"], scored["treat"]
    check_alignment(list(en.task_uid), list(bn.task_uid), expected=list(index.task_uid))
    traces = {}
    for s in cc.SIDES:
        if sides[s]["traces"] is None:
            raise SystemExit(f"no traces file next to {sides[s]['results']}")
        with open(sides[s]["traces"], encoding="utf-8") as f:
            traces[s] = [e["task"] for e in json.load(f)]
    rows = []
    for e, b in zip(en.itertuples(), bn.itertuples()):
        gt_en, gt_bn = list(e.ground_truth), list(b.ground_truth)
        if gt_en != gt_bn:
            raise SystemExit(f"{e.task_uid}: EN and BN ground-truth outcomes differ")
        cls = cc.pair_class(int(bool(e.correct)), int(bool(b.correct)))
        rows.append(
            {
                "dataset": DATASET,
                "model": model,
                "task_uid": e.task_uid,
                "domain": e.domain,
                "run_id_en": sides["ref"]["results"].stem,
                "run_id_bn": sides["treat"]["results"].stem,
                "en_pass": int(bool(e.correct)),
                "bn_pass": int(bool(b.correct)),
                "pair_class": cls,
                "en_trajectory": f"{cc.rel(sides['ref']['traces'])}#{find_trace_index(e.task, traces['ref'])}",
                "bn_trajectory": f"{cc.rel(sides['treat']['traces'])}#{find_trace_index(b.task, traces['treat'])}",
                "en_final_state": _json(split_calls(list(e.prediction), side_effect_names, name_of, all_names)),
                "bn_final_state": _json(split_calls(list(b.prediction), side_effect_names, name_of, all_names)),
                "gt_state": _json(split_calls(gt_en, side_effect_names, name_of, all_names)),
                "en_error": "" if e.error is None or e.error != e.error else str(e.error),
                "bn_error": "" if b.error is None or b.error != b.error else str(b.error),
            }
        )
    return rows


def check_against_comparison(rows: list[dict], comp_dir: Path) -> dict:
    """Pass/fail and pair_class must equal the existing comparison folder (per_task_*.csv, paired.csv)."""
    ref = {r["task_uid"]: int(r["correct"]) for r in read_csv_rows(comp_dir / "per_task_ref.csv")}
    treat = {r["task_uid"]: int(r["correct"]) for r in read_csv_rows(comp_dir / "per_task_treat.csv")}
    paired = {r["task_uid"]: r["pair_class"] for r in read_csv_rows(comp_dir / "paired.csv")}
    bad = []
    if not (len(ref) == len(treat) == len(paired) == len(rows)):
        bad.append(f"row counts: table {len(rows)}, ref {len(ref)}, treat {len(treat)}, paired {len(paired)}")
    for r in rows:
        u = r["task_uid"]
        if r["en_pass"] != ref.get(u) or r["bn_pass"] != treat.get(u) or r["pair_class"] != paired.get(u):
            bad.append(f"{u}: table ({r['en_pass']},{r['bn_pass']},{r['pair_class']}) vs comparison "
                       f"({ref.get(u)},{treat.get(u)},{paired.get(u)})")
    if bad:
        raise SystemExit("task table disagrees with " + str(comp_dir) + ":\n  " + "\n  ".join(bad[:10]))
    return {"rows_checked": len(rows), "pair_class_identical": True}


def write_table(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TABLE_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def read_table(path: Path) -> list[dict]:
    rows = read_csv_rows(path)
    missing = set(TABLE_COLUMNS) - set(rows[0] if rows else [])
    if missing:
        raise ValueError(f"{path}: missing columns {sorted(missing)}")
    return rows


# ---------------------------------------------------------------- CLI


def model_dir(model: str, out_root: Path) -> Path:
    return out_root / f"{SUBSET}_{model}_{TREAT}_vs_{REF}"


def _json_default(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    raise TypeError(type(o))


def write_json(obj: dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=_json_default)
        f.write("\n")


def _models(args) -> list[str]:
    if args.all:
        return list(MODELS)
    if not args.model:
        raise SystemExit("give --model <M> or --all")
    return [args.model]


def _load_model(args, model: str, out_root: Path):
    d = model_dir(model, out_root)
    table = read_table(d / "task_table.csv")
    labels = None
    if args.labels:
        path = d / args.labels if args.all or not Path(args.labels).parent.parts else Path(args.labels)
        labels = validate_labels(read_labels(path, args.annotator), table, require_complete=not args.allow_partial)
    return d, table, labels


def cmd_table(args, out_root: Path) -> None:
    for model in _models(args):
        rows = build_table(model)
        comp = ROOT / "results" / "comparisons" / f"{SUBSET}_{model}_{TREAT}_vs_{REF}"
        check = check_against_comparison(rows, comp)
        write_table(rows, model_dir(model, out_root) / "task_table.csv")
        n = {c: sum(1 for r in rows if r["pair_class"] == c) for c in PAIR_CLASSES}
        errs = (sum(1 for r in rows if r["en_error"]), sum(1 for r in rows if r["bn_error"]))
        print(f"{model}: {len(rows)} rows, alignment exact, matches {comp.name} {check}; "
              f"pair_class {'/'.join(str(n[c]) for c in PAIR_CLASSES)} (both_correct/ref_only/treat_only/both_wrong); "
              f"errored rows EN {errs[0]}, BN {errs[1]}")


def cmd_stats(args, out_root: Path) -> None:
    results = {}
    for model in _models(args):
        d, table, labels = _load_model(args, model, out_root)
        results[model] = (d, model_stats(model, table, labels, args.labels))
    if args.all:
        apply_holm({m: s for m, (_, s) in results.items()})
    for model, (d, s) in results.items():
        path = d / "stats.json"
        if path.exists():  # keep a previously written `counts` block
            old = json.loads(path.read_text(encoding="utf-8"))
            if "counts" in old:
                s["counts"] = old["counts"]
        write_json(s, path)
        o = s["overall"]
        print(f"{model}: EN {o['en_pass']}/{o['n']}={o['en_rate']:.4f} BN {o['bn_pass']}/{o['n']}={o['bn_rate']:.4f} "
              f"gap={o['gap']:.4f} {o['gap_ci95_paired_bootstrap']} MELR={o['melr']} {o['melr_ci95_paired_bootstrap']} "
              f"counts={o['pair_counts']} McNemar p={o['mcnemar_exact_p']:.4f} "
              f"Holm={'-' if s['holm'] is None else round(s['holm']['p_holm'], 4)} OR={o['paired_odds_ratio']['point']} "
              f"-> {path}")


def cmd_counts(args, out_root: Path) -> None:
    if not args.labels:
        raise SystemExit("counts needs --labels")
    loaded = {m: _load_model(args, m, out_root) for m in _models(args)}
    counts = all_counts({m: (t, lab) for m, (_, t, lab) in loaded.items()})
    for m, (d, _, _) in loaded.items():
        path = d / "stats.json"
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"model": m}
        data["counts"] = counts[m]
        if not args.all:
            data["counts"]["item_9_model_wise"] = None
            data["counts"]["item_9_note"] = "model-wise needs both models: run counts --all"
        write_json(data, path)
        print(f"{m}: counts written ({counts[m]['n_cases']} EN-pass/BN-fail cases of {counts[m]['n_pairs']}) -> {path}")


def cmd_validate(args, out_root: Path) -> None:
    for model in _models(args):
        _, _, labels = _load_model(args, model, out_root)
        print(f"{model}: {len(labels)} label rows valid ({args.labels})")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out_root", default=None, help="default results/failure_pipeline (must be inside the project)")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("table", "stats", "counts", "validate"):
        s = sub.add_parser(name)
        s.add_argument("--model", choices=MODELS)
        s.add_argument("--all", action="store_true", help="both models")
        if name != "table":
            s.add_argument("--labels", default=None, help="labels CSV (with --all: file name inside each model folder)")
            s.add_argument("--annotator", default=None, choices=ANNOTATORS, help="keep only this annotator's rows")
            s.add_argument("--allow_partial", action="store_true", help="do not require every expected label row")
    return p.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    out_root = Path(args.out_root) if args.out_root else OUT_ROOT
    out_root = (out_root if out_root.is_absolute() else ROOT / out_root).resolve()
    if not out_root.is_relative_to(ROOT.resolve()):
        raise SystemExit(f"refusing to write outside the project folder: {out_root}")
    {"table": cmd_table, "stats": cmd_stats, "counts": cmd_counts, "validate": cmd_validate}[args.cmd](args, out_root)


if __name__ == "__main__":
    main()
