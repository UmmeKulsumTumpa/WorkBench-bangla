"""Tests for scripts/failure_pipeline.py (synthetic inputs only; no traces or run files needed).

Run with the WorkBench venv:
    source env.sh && uv run --project WorkBench --frozen python -m pytest tests -q
"""

import csv
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "failure_pipeline.py"
RULES = ROOT / "results" / "failure_pipeline" / "annotation_rules.md"


def _load():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("failure_pipeline", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["failure_pipeline"] = mod
    spec.loader.exec_module(mod)
    return mod


fp = _load()
cc = fp.cc


def make_pairs(a, b, c, d, domains=("email", "calendar")):
    """a both-pass, b EN-pass/BN-fail, c EN-fail/BN-pass, d both-fail; domains cycle."""
    kinds = [(1, 1)] * a + [(1, 0)] * b + [(0, 1)] * c + [(0, 0)] * d
    return [
        {"task_uid": f"workbench:{domains[i % len(domains)]}:{i}", "domain": domains[i % len(domains)], "en": e, "bn": bn}
        for i, (e, bn) in enumerate(kinds)
    ]


def make_table(pairs):
    cls = {(1, 1): "both_correct", (1, 0): "ref_only", (0, 1): "treat_only", (0, 0): "both_wrong"}
    return [
        {"task_uid": p["task_uid"], "domain": p["domain"], "en_pass": str(p["en"]), "bn_pass": str(p["bn"]),
         "pair_class": cls[(p["en"], p["bn"])]}
        for p in pairs
    ]


def label_row(table_row, side, **kw):
    row = {
        "task_uid": table_row["task_uid"], "domain": table_row["domain"], "pair_class": table_row["pair_class"],
        "side": side, "first_failure_point": "Planning", "failure_type": "Planning failure",
        "confound": "General model weakness present in both English and Bangla",
        "decision_tree": "S1=ok;S2=na;S3=ok;S4=ok;S5=ok;S6=ok;S7=fail" if table_row["pair_class"] == "ref_only" else "",
        "evidence": "e", "not_general_reason": "r" if table_row["pair_class"] == "ref_only" else "", "annotator": "A1",
    }
    row.update(kw)
    return row


def full_labels(table, **kw):
    out = []
    for t in table:
        for side in fp.expected_sides(t["pair_class"]):
            out.append(label_row(t, side, **kw))
    return out


# ---------------------------------------------------------------- Wilson


@pytest.mark.parametrize(
    "k,n,low,high",
    [(0, 10, 0.0, 0.2775), (10, 10, 0.7225, 1.0), (5, 10, 0.2366, 0.7634), (73, 90, 0.7182, 0.8786)],
)
def test_wilson_known_values(k, n, low, high):
    lo, hi = fp.wilson_ci(k, n)
    assert lo == pytest.approx(low, abs=5e-4)
    assert hi == pytest.approx(high, abs=5e-4)


def test_wilson_empty_is_none():
    assert fp.wilson_ci(0, 0) is None


# ---------------------------------------------------------------- Holm


def test_holm_known_values():
    adj = fp.holm_adjust({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adj == pytest.approx({"a": 0.03, "c": 0.06, "b": 0.06})


def test_holm_two_models_monotone_and_capped():
    adj = fp.holm_adjust({"gemma": 1.0, "gpt": 0.4244})
    assert adj["gpt"] == pytest.approx(0.8488)
    assert adj["gemma"] == 1.0  # capped
    assert fp.holm_adjust({"x": 0.3, "y": 0.2})["x"] >= fp.holm_adjust({"x": 0.3, "y": 0.2})["y"]  # monotone


def test_apply_holm_writes_family_and_adjusted_p():
    stats = {m: {"overall": {"mcnemar_exact_p": p}} for m, p in (("m1", 0.01), ("m2", 0.04))}
    fp.apply_holm(stats)
    assert stats["m1"]["holm"]["p_holm"] == pytest.approx(0.02)
    assert stats["m2"]["overall"]["mcnemar_p_holm"] == pytest.approx(0.04)
    assert stats["m1"]["holm"]["family"] == ["m1", "m2"]


# ---------------------------------------------------------------- odds ratio and its exact CI


def test_clopper_pearson_closed_forms():
    lo, hi = fp.clopper_pearson(0, 10)
    assert lo == 0.0 and hi == pytest.approx(1 - 0.025 ** (1 / 10), abs=1e-9)
    lo, hi = fp.clopper_pearson(10, 10)
    assert hi == 1.0 and lo == pytest.approx(0.025 ** (1 / 10), abs=1e-9)
    lo, hi = fp.clopper_pearson(7, 15)  # reference value 0.2127 .. 0.7341
    assert (lo, hi) == pytest.approx((0.2127, 0.7341), abs=5e-4)


def test_odds_ratio_basic():
    r = fp.paired_odds_ratio(15, 10)
    assert r["point"] == 1.5 and not r["point_is_infinite"]
    p_lo, p_hi = fp.clopper_pearson(15, 25)
    assert r["ci95_low"] == pytest.approx(p_lo / (1 - p_lo))
    assert r["ci95_high"] == pytest.approx(p_hi / (1 - p_hi))
    assert r["ci95_low"] < 1.5 < r["ci95_high"]


def test_odds_ratio_c_zero_gives_lower_bound_only():
    r = fp.paired_odds_ratio(6, 0)
    assert r["point"] is None and r["point_is_infinite"]
    assert r["ci95_high"] is None and r["ci95_high_is_infinite"]
    assert r["ci95_low"] == pytest.approx(0.025 ** (1 / 6) / (1 - 0.025 ** (1 / 6)))


def test_odds_ratio_b_zero():
    r = fp.paired_odds_ratio(0, 5)
    assert r["point"] == 0.0 and r["ci95_low"] == 0.0
    p_hi = 1 - 0.025 ** (1 / 5)  # closed-form Clopper-Pearson upper limit for 0/5
    assert r["ci95_high"] == pytest.approx(p_hi / (1 - p_hi), rel=1e-6)


def test_odds_ratio_no_discordant_pairs():
    r = fp.paired_odds_ratio(0, 0)
    assert r["point"] is None and r["ci95_low"] is None and r["ci95_high"] is None
    assert not r["point_is_infinite"] and not r["ci95_high_is_infinite"]


# ---------------------------------------------------------------- MELR and bootstrap


def test_melr_point_and_ci():
    m = fp.paired_metrics(make_pairs(40, 10, 5, 35))  # EN 50/90... n=90
    assert m["n"] == 90
    assert m["en_rate"] == pytest.approx(50 / 90) and m["bn_rate"] == pytest.approx(45 / 90)
    assert m["gap"] == pytest.approx(5 / 90)
    assert m["melr"] == pytest.approx((5 / 90) / (50 / 90))
    lo, hi = m["melr_ci95_paired_bootstrap"]
    assert lo < m["melr"] < hi
    assert m["pair_counts"] == {"en_pass_bn_pass": 40, "en_pass_bn_fail": 10, "en_fail_bn_pass": 5, "en_fail_bn_fail": 35}
    assert m["mcnemar_exact_p"] == pytest.approx(cc.mcnemar_exact(10, 5))


def test_gap_ci_is_compare_conditions_bootstrap_and_melr_shares_resamples():
    pairs = make_pairs(30, 8, 3, 9)
    en, bn = [p["en"] for p in pairs], [p["bn"] for p in pairs]
    boot = fp.bootstrap_gap_melr(en, bn)
    ref_lo, ref_hi = cc.paired_bootstrap_ci(bn, en)  # mean(EN) - mean(BN)
    assert boot["gap_ci95"] == pytest.approx([ref_lo, ref_hi])
    idx = fp.bootstrap_indices(len(en))
    e, b = np.array(en)[idx].mean(1), np.array(bn)[idx].mean(1)
    lo, hi = np.percentile((e - b) / e, [2.5, 97.5])  # no EN = 0 resample here
    assert boot["melr_ci95"] == pytest.approx([lo, hi])
    assert boot["melr_undefined_resamples"] == 0


def test_melr_undefined_when_en_is_zero():
    m = fp.paired_metrics(make_pairs(0, 0, 4, 6))
    assert m["en_rate"] == 0 and m["melr"] is None and "undefined" in m["melr_note"]
    assert m["melr_ci95_paired_bootstrap"] is None


def test_melr_ci_excludes_resamples_with_zero_en_rate():
    pairs = make_pairs(0, 1, 2, 1)  # only one EN pass in 4 pairs: some resamples have EN = 0
    boot = fp.bootstrap_gap_melr([p["en"] for p in pairs], [p["bn"] for p in pairs])
    assert boot["melr_undefined_resamples"] > 0
    assert boot["melr_ci95"] is not None and all(math.isfinite(x) for x in boot["melr_ci95"])


def test_domain_metrics_are_descriptive():
    m = fp.paired_metrics(make_pairs(3, 1, 1, 0), inference=False)
    assert "mcnemar_exact_p" not in m and "gap_ci95_paired_bootstrap" not in m and m["melr"] is not None


# ---------------------------------------------------------------- sensitivity


def test_sensitivity_without_labels_is_null_but_all_present():
    s = fp.sensitivity(make_pairs(5, 2, 1, 2), None)
    assert s["all"]["n"] == 10
    assert s["no_translation"] is None and s["no_user_simulator"] is None and s["no_tool_environment"] is None


def test_sensitivity_drops_pair_when_either_side_has_the_confound():
    pairs = make_pairs(4, 3, 2, 3)  # indices: 4-6 ref_only, 7-8 treat_only, 9-11 both_wrong
    table = make_table(pairs)
    labels = full_labels(table)
    by = {(r["task_uid"], r["side"]): r for r in labels}
    ref_only = [t for t in table if t["pair_class"] == "ref_only"]
    both_wrong = [t for t in table if t["pair_class"] == "both_wrong"]
    by[(ref_only[0]["task_uid"], "BN")]["confound"] = fp.TRANSLATION
    by[(both_wrong[0]["task_uid"], "EN")]["confound"] = fp.TRANSLATION  # EN side only: pair still dropped
    by[(both_wrong[1]["task_uid"], "BN")]["confound"] = fp.TOOL_ENV
    s = fp.sensitivity(pairs, labels)
    assert s["all"]["n"] == 12
    assert s["no_translation"]["n"] == 10 and s["no_translation"]["n_removed"] == 2
    assert set(s["no_translation"]["removed_task_uids"]) == {ref_only[0]["task_uid"], both_wrong[0]["task_uid"]}
    assert s["no_tool_environment"]["n"] == 11
    assert s["no_user_simulator"]["n"] == 12 and s["no_user_simulator"]["n_removed"] == 0
    assert s["no_user_simulator"]["pair_counts"] == s["all"]["pair_counts"]
    # the removed ref_only pair shrinks b
    assert s["no_translation"]["pair_counts"]["en_pass_bn_fail"] == 2


def test_model_stats_runs_without_labels():
    table = make_table(make_pairs(5, 2, 1, 2))
    s = fp.model_stats("m", table, None)
    assert s["labels_provided"] is False and s["holm"] is None
    assert set(s["domains"]) == {"email", "calendar"}
    json.dumps(s)  # serialisable


# ---------------------------------------------------------------- alignment


def test_alignment_accepts_identical_order():
    fp.check_alignment(["a", "b", "c"], ["a", "b", "c"], expected=["c", "b", "a"])


@pytest.mark.parametrize(
    "en,bn,msg",
    [
        (["a", "b"], ["a"], "length differs"),
        (["a", "b"], ["a", "c"], "sets differ"),
        (["a", "b"], ["b", "a"], "different order"),
        (["a", "a"], ["a", "a"], "duplicate"),
    ],
)
def test_alignment_fails_loudly(en, bn, msg):
    with pytest.raises(SystemExit, match=msg):
        fp.check_alignment(en, bn)


def test_alignment_fails_when_not_the_expected_index():
    with pytest.raises(SystemExit, match="expected"):
        fp.check_alignment(["a", "b"], ["a", "b"], expected=["a", "c"])


def test_trace_index_found_by_text_not_position():
    assert fp.find_trace_index("t2", ["t3", "t2", "t1"]) == 1
    with pytest.raises(SystemExit):
        fp.find_trace_index("missing", ["t1"])
    with pytest.raises(SystemExit):
        fp.find_trace_index("dup", ["dup", "dup"])


def test_split_calls_uses_given_tool_sets():
    name_of = lambda a: a.split("(")[0]  # noqa: E731
    out = fp.split_calls(["w.f(x)", "r.g(y)", "bogus.h(z)", "w.f(q)"], {"w.f"}, name_of, {"w.f", "r.g"})
    assert out == {"state_changing": ["w.f(x)", "w.f(q)"], "read_only": ["r.g(y)"], "unrecognised": ["bogus.h(z)"]}


def test_check_against_comparison(tmp_path):
    rows = [{"task_uid": "u1", "en_pass": 1, "bn_pass": 0, "pair_class": "ref_only"}]

    def write(name, header, body):
        (tmp_path / name).write_text(header + "\n" + body + "\n")

    write("per_task_ref.csv", "task_uid,correct", "u1,1")
    write("per_task_treat.csv", "task_uid,correct", "u1,0")
    write("paired.csv", "task_uid,pair_class", "u1,ref_only")
    assert fp.check_against_comparison(rows, tmp_path)["pair_class_identical"]
    write("paired.csv", "task_uid,pair_class", "u1,both_wrong")
    with pytest.raises(SystemExit, match="disagrees"):
        fp.check_against_comparison(rows, tmp_path)


# ---------------------------------------------------------------- labels, counts, CLI


def test_validate_labels_accepts_complete_set_and_canonicalises():
    table = make_table(make_pairs(2, 2, 1, 1))
    rows = full_labels(table, first_failure_point="planning.")
    out = fp.validate_labels(rows, table)
    assert {r["first_failure_point"] for r in out} == {"Planning"}


@pytest.mark.parametrize(
    "mutate,msg",
    [
        (lambda rows: rows.pop(), "missing label row"),
        (lambda rows: rows[0].update(confound="Bangla user-simulator error"), "structurally impossible"),
        (lambda rows: rows[0].update(failure_type="Made up"), "controlled vocabulary"),
        (lambda rows: rows.append(dict(rows[0])), "duplicate"),
        (lambda rows: rows[0].update(decision_tree="S1=ok"), "decision_tree"),
        (lambda rows: rows[0].update(annotator="bob"), "annotator"),
    ],
)
def test_validate_labels_rejects(mutate, msg):
    table = make_table(make_pairs(0, 2, 1, 1))
    rows = full_labels(table)
    mutate(rows)
    with pytest.raises(ValueError, match=msg):
        fp.validate_labels(rows, table)


def test_counts_distribution_and_filtering():
    pairs = make_pairs(2, 4, 1, 1)
    table = make_table(pairs)
    labels = full_labels(table)
    ref_only = [r for r in labels if r["pair_class"] == "ref_only"]
    ref_only[0].update(confound=fp.GENUINE)
    ref_only[1].update(confound=fp.TRANSLATION)
    ref_only[2].update(confound=fp.TOOL_ENV)
    c = fp.model_counts(table, labels)
    assert c["n_cases"] == 4
    assert c["item_3_confound"]["counts"][fp.GENUINE]["n"] == 1
    assert c["item_6_translation_caused"]["n"] == 1 and c["item_7_tool_environment_caused"]["n"] == 1
    assert c["item_5_user_simulator_caused"]["n"] == 0
    f = c["item_4_genuine_after_filtering"]
    assert (f["n_removed_by_filter"], f["n_remaining"], f["n_genuine_bangla_related"]) == (2, 2, 1)
    assert sum(v["n"] for v in c["item_1_failure_type"]["counts"].values()) == 4
    assert c["item_8_dataset_wise"]["WorkBench"]["n_cases"] == 4
    assert sum(d["n_cases"] for d in c["item_10_domain_wise"].values()) == 4
    both = fp.all_counts({"m1": (table, labels), "m2": (table, labels)})
    assert set(both["m1"]["item_9_model_wise"]) == {"m1", "m2"}


def test_distribution_rejects_unknown_label():
    with pytest.raises(ValueError):
        fp.distribution(["nope"], fp.FAILURE_TYPES)


def test_cli_stats_counts_end_to_end(tmp_path):
    out_root = tmp_path  # pytest basetemp is inside the project (tests/conftest.py)
    table = make_table(make_pairs(5, 3, 2, 2))
    full = [{**t, "dataset": "WorkBench", "model": "ollama-gemma4-31b"} for t in table]
    d = fp.model_dir("ollama-gemma4-31b", out_root)
    d.mkdir(parents=True)
    with open(d / "task_table.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fp.TABLE_COLUMNS, restval="", lineterminator="\n")
        w.writeheader()
        w.writerows(full)
    fp.main(["--out_root", str(out_root), "stats", "--model", "ollama-gemma4-31b"])
    s = json.loads((d / "stats.json").read_text())
    assert s["overall"]["n"] == 12 and s["labels_provided"] is False
    with open(d / "labels_final.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fp.LABEL_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(full_labels(table))
    fp.main(["--out_root", str(out_root), "stats", "--model", "ollama-gemma4-31b", "--labels", "labels_final.csv"])
    fp.main(["--out_root", str(out_root), "counts", "--model", "ollama-gemma4-31b", "--labels", "labels_final.csv"])
    s = json.loads((d / "stats.json").read_text())
    assert s["labels_provided"] and s["sensitivity"]["no_translation"]["n_removed"] == 0
    assert s["counts"]["n_cases"] == 3 and s["counts"]["item_9_model_wise"] is None
    with pytest.raises(SystemExit, match="outside the project"):
        fp.main(["--out_root", "/tmp/elsewhere", "stats", "--model", "ollama-gemma4-31b"])


# ---------------------------------------------------------------- the rules file carries the vocabularies


def test_annotation_rules_contain_every_label_and_the_contract():
    text = RULES.read_text(encoding="utf-8")
    for label in fp.FIRST_FAILURE_POINTS + fp.FAILURE_TYPES + fp.CONFOUNDS:
        assert label in text, label
    assert ", ".join(fp.LABEL_COLUMNS) in text
    assert "git-ignored" in text
