"""Tests for scripts/compare_en_bn.py.

Run from the WorkBench checkout (the script imports WorkBench's own scorer):
    cd WorkBench && uv run --frozen python -m pytest ../tests -q
"""

import csv
import importlib.util
import json
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
WB = ROOT / "WorkBench"
SCRIPT = ROOT / "scripts" / "compare_en_bn.py"
PILOT_EN = ROOT / "data_bn" / "pilot" / "pilot_en_tasks_and_outcomes.csv"
PILOT_INDEX = ROOT / "data_bn" / "pilot" / "pilot_index.csv"
DOMAINS = ["email", "calendar", "customer_relationship_manager", "analytics", "project_management", "multi_domain"]


def _load():
    spec = importlib.util.spec_from_file_location("compare_en_bn", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cmp = _load()
csv.field_size_limit(sys.maxsize)


# ---------------------------------------------------------------- statistics


@pytest.mark.parametrize(
    "b,c,expected",
    [
        (0, 5, 0.0625),
        (5, 0, 0.0625),
        (0, 0, 1.0),
        (3, 3, 1.0),
        (1, 9, 2 * (1 + 10) / 1024),
        (2, 3, 1.0),
    ],
)
def test_mcnemar_exact(b, c, expected):
    assert cmp.mcnemar_exact(b, c) == pytest.approx(expected)


def test_bootstrap_is_deterministic_and_brackets_point_estimate():
    en = [1, 0, 1, 1, 0, 1, 0, 0, 1, 1] * 3
    bn = [1, 0, 0, 1, 0, 0, 0, 1, 1, 0] * 3
    a = cmp.paired_bootstrap_ci(en, bn)
    b = cmp.paired_bootstrap_ci(en, bn)
    assert a == b
    delta = (sum(bn) - sum(en)) / len(en)
    assert a[0] <= delta <= a[1]
    assert a[0] < a[1]
    assert cmp.SEED == 20261004 and cmp.N_BOOT == 10_000


def test_bootstrap_no_variation_gives_zero_width():
    assert cmp.paired_bootstrap_ci([1, 0, 1], [1, 0, 1]) == (0.0, 0.0)


def test_pair_class():
    assert cmp.pair_class(1, 1) == "both_correct"
    assert cmp.pair_class(1, 0) == "en_only"
    assert cmp.pair_class(0, 1) == "bn_only"
    assert cmp.pair_class(0, 0) == "both_wrong"


def test_metrics_long_format():
    paired = pd.DataFrame(
        {
            "task_uid": [f"workbench:email:{i}" for i in range(4)] + [f"workbench:calendar:{i}" for i in range(2)],
            "domain": ["email"] * 4 + ["calendar"] * 2,
            "template_id": ["T01"] * 6,
            "correct_en": [1, 1, 0, 1, 1, 0],
            "correct_bn": [1, 0, 0, 0, 1, 1],
            "side_effect_en": [0, 0, 1, 0, 0, 0],
            "side_effect_bn": [0, 1, 1, 0, 0, 0],
        }
    )
    paired["pair_class"] = [cmp.pair_class(e, b) for e, b in zip(paired.correct_en, paired.correct_bn)]
    weights = {"email": 0.5, "calendar": 0.5}
    m = cmp.compute_comparison_metrics(paired, "workbench", "k", "id", "c1", weights)
    assert list(m.columns) == ["benchmark", "model_key", "model_id", "condition", "scope", "metric", "value", "n"]
    get = lambda scope, metric: m[(m.scope == scope) & (m.metric == metric)].iloc[0]  # noqa: E731
    assert get("overall", "completion_rate_en").value == "0.6667"
    assert get("overall", "completion_rate_bn").value == "0.5000"
    assert get("overall", "delta_completion").value == "-0.1667"
    assert get("overall", "side_effect_rate_bn").value == "0.3333"
    assert get("overall", "n_en_only").value == "2"
    assert get("overall", "n_bn_only").value == "1"
    assert get("overall", "mcnemar_p").value == "1.0000"
    assert set(m[m.scope == "overall"].n) == {6}
    # weighted: email 0.75/0.25, calendar 0.5/1.0 at equal weights
    assert get("overall", "completion_rate_en_weighted").value == "0.6250"
    assert get("overall", "completion_rate_bn_weighted").value == "0.6250"
    for name in ("delta_completion_ci95_low", "delta_completion_ci95_high",
                 "delta_side_effect_ci95_low", "delta_side_effect_ci95_high"):
        assert len(m[(m.scope == "overall") & (m.metric == name)]) == 1
    # domain scopes are descriptive only
    dom = m[m.scope == "domain:email"]
    assert set(dom.n) == {4}
    assert "mcnemar_p" not in set(dom.metric)
    assert get("domain:calendar", "delta_completion").value == "0.5000"


# ---------------------------------------------------------------- task_uid assignment


def test_uid_from_columns():
    tasks = pd.DataFrame({"task": ["a", "b"], "source_file": ["email", "email"], "row_idx": ["5", "6"]})
    out = cmp.attach_task_uid(tasks, "pilot_en_tasks_and_outcomes.csv", None)
    assert list(out.task_uid) == ["workbench:email:5", "workbench:email:6"]
    assert list(out.domain) == ["email", "email"]


def test_uid_fallback_full_domain_file():
    tasks = pd.DataFrame({"task": ["a", "b", "c"]})
    out = cmp.attach_task_uid(tasks, "/x/email_bn_tasks_and_outcomes.csv", None)
    assert list(out.task_uid) == ["workbench:email:0", "workbench:email:1", "workbench:email:2"]
    index = pd.DataFrame({"task_uid": ["workbench:email:2"], "source_file": ["email"], "row_idx": ["2"]})
    out = cmp.attach_task_uid(tasks, "/x/email_bn_tasks_and_outcomes.csv", index)
    assert list(out.task) == ["c"]


def test_uid_fallback_positional_index():
    tasks = pd.DataFrame({"task": ["a", "b"]})
    index = pd.DataFrame(
        {"task_uid": ["workbench:email:5", "workbench:calendar:1"], "source_file": ["email", "calendar"], "row_idx": ["5", "1"]}
    )
    out = cmp.attach_task_uid(tasks, "/x/whatever.csv", index)
    assert list(out.task_uid) == ["workbench:email:5", "workbench:calendar:1"]
    with pytest.raises(ValueError):
        cmp.attach_task_uid(tasks, "/x/whatever.csv", None)


def test_trace_counts(tmp_path):
    p = tmp_path / "t_traces.json"
    p.write_text(json.dumps([{"task": "a", "steps": [{}, {}, {}]}, {"task": "b", "steps": []}]))
    assert cmp.load_trace_counts(str(p)) == {"a": 3, "b": 0}


def test_run_id():
    assert cmp.make_run_id("pilot", "en", "m", "en") == "workbench_pilot_en_m"
    assert cmp.make_run_id("pilot", "bn", "m", "c1") == "workbench_pilot_bn_m_c1"


# ---------------------------------------------------------------- end-to-end on committed results


def _latest(domain, model):
    files = sorted(f for f in os.listdir(WB / "data/results" / domain)
                   if f.startswith(f"{model}_all_") and f.endswith((".csv", ".csv.gz")))
    return WB / "data/results" / domain / files[-1]


def build_standin(model: str, out_path: Path) -> list[Path]:
    """Concatenate the model's 6 domain `all` results, filtered to the pilot tasks of each domain."""
    pilot = pd.read_csv(PILOT_EN, dtype=str)
    frames, sources = [], []
    for d in DOMAINS:
        src = _latest(d, model)
        sources.append(src)
        r = pd.read_csv(src, dtype=str, engine="python")
        frames.append(r[r.task.isin(set(pilot[pilot.source_file == d].task))])
    out = pd.concat(frames, ignore_index=True)
    assert len(out) == len(pilot) and out.task.is_unique
    out.to_csv(out_path, index=False, quoting=csv.QUOTE_ALL)
    return sources


@pytest.fixture(scope="module")
def e2e(tmp_path_factory):
    d = tmp_path_factory.mktemp("cmp")
    en, bn = d / "en.csv", d / "bn.csv"
    en_src = build_standin("qwen-3.5-flash", en)
    bn_src = build_standin("deepseek-v4-pro", bn)
    out = d / "out"
    cmp.main([
        "--en_results", str(en), "--bn_results", str(bn),
        "--en_tasks", str(PILOT_EN), "--bn_tasks", str(PILOT_EN), "--index", str(PILOT_INDEX),
        "--model_key", "standin", "--model_id", "standin/model", "--provider", "openrouter",
        "--condition", "c1", "--comparison_id", "workbench_pilot_standin_c1", "--out_dir", str(out),
    ])
    return out, en_src, bn_src


def _item_level(sources):
    il = pd.read_csv(WB / "data/results/item_level_results.csv.gz", dtype=str)
    rel = {p.relative_to(WB).as_posix() for p in sources}
    il = il[il.results_file.isin(rel)]
    return il


@pytest.mark.parametrize("lang,src_idx", [("en", 1), ("bn", 2)])
def test_e2e_matches_item_level(e2e, lang, src_idx):
    out = e2e[0]
    per = pd.read_csv(out / f"per_task_{lang}.csv", dtype=str, keep_default_na=False)
    assert len(per) == 90 and per.task_uid.is_unique
    pilot = pd.read_csv(PILOT_EN, dtype=str)
    uid_task = dict(zip("workbench:" + pilot.source_file + ":" + pilot.row_idx, pilot.task))
    il = _item_level(e2e[src_idx])
    il = il[il.task.isin(set(pilot.task))]
    assert len(il) == 90
    ref = {(t, dom): (c == "True", s == "True") for t, dom, c, s in
           zip(il.task, il.domain, il.correct, il.unwanted_side_effects)}
    for r in per.itertuples():
        exp = ref[(uid_task[r.task_uid], r.domain)]
        assert (r.correct == "1", r.side_effect == "1") == exp, r.task_uid
    assert (per.correct == "1").sum() == sum(v[0] for v in ref.values())
    assert (per.side_effect == "1").sum() == sum(v[1] for v in ref.values())


def test_e2e_outputs_follow_schema(e2e):
    out = e2e[0]
    per = pd.read_csv(out / "per_task_bn.csv", dtype=str, keep_default_na=False)
    assert list(per.columns) == cmp.PER_TASK_COLUMNS
    assert set(per.language) == {"bn"} and set(per.condition) == {"c1"}
    assert set(per.run_id) == {"workbench_pilot_bn_standin_c1"}
    assert set(per.template_id) <= {f"T{i:02d}" for i in range(1, 70)} and "" not in set(per.template_id)
    paired = pd.read_csv(out / "paired.csv", dtype=str)
    assert list(paired.columns) == cmp.PAIRED_COLUMNS and len(paired) == 90
    m = pd.read_csv(out / "metrics.csv", dtype=str)
    assert set(m.scope) == {"overall"} | {f"domain:{d}" for d in DOMAINS}
    overall = m[m.scope == "overall"].set_index("metric")
    n_en_only = int(overall.loc["n_en_only", "value"])
    n_bn_only = int(overall.loc["n_bn_only", "value"])
    assert (paired.pair_class == "en_only").sum() == n_en_only
    assert (paired.pair_class == "bn_only").sum() == n_bn_only
    meta = json.loads((out / "run_meta_bn.json").read_text(encoding="utf-8"))
    for k in ["benchmark", "run_id", "model_key", "model_id", "provider", "base_url", "temperature", "language",
              "condition", "subset", "n_tasks", "tasks_file", "tasks_file_sha256", "tool_selection",
              "structured_outputs", "act_without_confirmation", "harness_commit", "patch_files", "started_at",
              "finished_at", "total_llm_requests", "notes"]:
        assert k in meta
    assert len(meta["harness_commit"]) == 40 and len(meta["tasks_file_sha256"]) == 64
    assert meta["n_tasks"] == 90
