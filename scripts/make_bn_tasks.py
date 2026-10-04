#!/usr/bin/env python3
"""Render Bangla WorkBench task files from translated chosen_templates.

Inputs
  data_bn/templates_bn.csv  (variant_id, template_id, source_file, template_en, template_bn, notes)
  data_bn/glossary.csv      (slot, value_en, value_bn, kind, rule, n_occurrences)
  WorkBench/data/processed/tasks_and_outcomes/{src}_tasks_and_outcomes.csv (top-level = v2 GT)

Outputs
  data_bn/{src}_bn_tasks_and_outcomes.csv  — same rows/columns/order as EN; only `task` and
  `chosen_template` differ. Named so that workbench-evaluate finds GT for results dir `{src}_bn`.

Template syntax (docs/translation_policy.md §5): `{slot}` -> glossary BN value if present else raw;
`{slot!en}` -> raw English value always.

Modes
  python3 scripts/make_bn_tasks.py --check_templates [--templates FILE]   # validate translations only
  python3 scripts/make_bn_tasks.py                                         # validate + render + assert

Stdlib only.
"""
import argparse
import ast
import csv
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recover_slots import recover_slots  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_DIR = os.path.join(ROOT, "WorkBench", "data", "processed", "tasks_and_outcomes")
SOURCES = ["email", "calendar", "customer_relationship_manager", "analytics",
           "project_management", "multi_domain"]
EN_SLOT_RE = re.compile(r"\{([A-Za-z0-9_]+)\}")
BN_SLOT_RE = re.compile(r"\{([A-Za-z0-9_]+)(!en)?\}")
BENGALI_DIGIT_RE = re.compile("[০-৯]")
BENGALI_CHAR_RE = re.compile("[ঀ-৿]")
# Quoted segments may keep English literal text (they reach tool arguments).
QUOTED_RE = re.compile(r"'[^']*'|\"[^\"]*\"|‘[^’]*’|“[^”]*”")
LATIN_ALLOWLIST = {"CRM"}
# DB/tool enum values are kept in Latin script, unquoted (policy §4). Words compared case-insensitively.
# project_tasks.list_name, crm status / product_interest, analytics traffic_source, plot types.
ENUM_PHRASES = ["Backlog", "In Progress", "In Review", "Completed",
                "Lead", "Lost", "Proposal", "Qualified", "Won",
                "Consulting", "Hardware", "Services", "Software", "Training",
                "direct", "referral", "search engine", "social media",
                "bar", "line", "scatter", "histogram",
                # project board names (DB enum; owner decision review cycle 2: Latin, EN surface form)
                "Front end", "Back end", "Design", "front-end", "back-end"]
ENUM_WORDS = {w.lower() for ph in ENUM_PHRASES for w in ph.split()}


def nfc(s):
    return unicodedata.normalize("NFC", s)


def load_templates(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def check_template(en, bn):
    """Return a list of problems with one translated template (empty = OK)."""
    problems = []
    if not bn.strip():
        return ["empty template_bn"]
    en_slots = set(EN_SLOT_RE.findall(en))
    bn_slots = {m.group(1) for m in BN_SLOT_RE.finditer(bn)}
    if en_slots != bn_slots:
        problems.append(f"slot mismatch: missing={sorted(en_slots - bn_slots)} extra={sorted(bn_slots - en_slots)}")
    leftover = re.sub(BN_SLOT_RE, "", bn)
    if "{" in leftover or "}" in leftover:
        problems.append("malformed placeholder braces")
    if BENGALI_DIGIT_RE.search(bn):
        problems.append("Bengali numeral present")
    if not BENGALI_CHAR_RE.search(bn):
        problems.append("no Bangla script at all")
    stray = re.sub(QUOTED_RE, " ", leftover)
    latin = [w for w in (t.rstrip(".-") for t in re.findall(r"[A-Za-z][A-Za-z.\-]*", stray))
             if w not in LATIN_ALLOWLIST and w.lower() not in ENUM_WORDS]
    if latin:
        problems.append(f"stray Latin outside quotes/slots: {latin}")
    return problems


def check_all(rows):
    bad = 0
    for r in rows:
        p = check_template(r["template_en"], r.get("template_bn", ""))
        if p:
            bad += 1
            print(f"[{r.get('variant_id', '?')}] " + "; ".join(p))
    print(f"checked {len(rows)} templates: {len(rows) - bad} OK, {bad} with problems")
    return bad == 0


def load_glossary():
    with open(os.path.join(ROOT, "data_bn", "glossary.csv"), encoding="utf-8", newline="") as f:
        return {(r["slot"], r["value_en"]): r["value_bn"] for r in csv.DictReader(f)}


def render(template_bn, slots, glossary):
    def sub(m):
        slot, raw = m.group(1), m.group(2)
        value = slots[slot]
        return value if raw else glossary.get((slot, value), value)
    return nfc(BN_SLOT_RE.sub(sub, template_bn))


def outcome_literals(outcome):
    """String argument values in the outcome's calls (excluding `field=` names, which are schema, not task text)."""
    lits = []
    for call in ast.literal_eval(outcome):
        for node in ast.walk(ast.parse(call, mode="eval")):
            if not isinstance(node, ast.Call):
                continue
            vals = [a for a in node.args] + [k.value for k in node.keywords if k.arg != "field"]
            lits += [v.value for v in vals if isinstance(v, ast.Constant) and isinstance(v.value, str)]
    return lits


def build(templates, out_dir, partial=False):
    by_en = {r["template_en"]: r for r in templates}
    glossary = load_glossary()
    totals = {}
    for src in SOURCES:
        with open(os.path.join(TASKS_DIR, f"{src}_tasks_and_outcomes.csv"), encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames
            en_rows = list(reader)
        out_rows = []
        for i, row in enumerate(en_rows):
            ct = row["chosen_template"]
            if partial and ct not in by_en:
                continue
            assert ct in by_en, f"{src}:{i} no translation for chosen_template: {ct!r}"
            tbn = nfc(by_en[ct]["template_bn"])
            slots = recover_slots(ct, row["task"])
            task_bn = render(tbn, slots, glossary)
            # placeholders all filled
            assert not BN_SLOT_RE.search(task_bn), f"{src}:{i} unfilled placeholder: {task_bn!r}"
            assert not BENGALI_DIGIT_RE.search(task_bn), f"{src}:{i} Bengali numeral: {task_bn!r}"
            # literals that reach the ground truth survive verbatim
            for lit in outcome_literals(row["outcome"]):
                if lit and lit in row["task"]:
                    assert lit in task_bn, f"{src}:{i} GT literal {lit!r} lost in BN task: {task_bn!r}"
            new = dict(row)
            new["task"] = task_bn
            new["chosen_template"] = tbn
            out_rows.append(new)
        tasks = [r["task"] for r in out_rows]
        dups = {t for t in tasks if tasks.count(t) > 1}
        assert not dups, f"{src}: duplicate BN tasks (eval merges on task text): {sorted(dups)[:3]}"
        if partial:
            totals[src] = len(out_rows)
            for r in out_rows[:2]:
                print(f"  sample {src}: {r['task'][:160]!r}")
            continue
        # invariants vs EN
        assert len(out_rows) == len(en_rows)
        for a, b in zip(en_rows, out_rows):
            assert a["outcome"] == b["outcome"] and a["base_template"] == b["base_template"] and a["domains"] == b["domains"]
        path = os.path.join(out_dir, f"{src}_bn_tasks_and_outcomes.csv")
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL, lineterminator="\n")
            w.writeheader()
            w.writerows(out_rows)
        totals[src] = len(out_rows)
        print(f"wrote {path} ({len(out_rows)} rows)")
    print(f"total {sum(totals.values())} rows" + ("" if partial else " (expected 690)"))
    if partial:
        print("partial render OK (no files written)")
        return
    assert sum(totals.values()) == 690


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--templates", default=os.path.join(ROOT, "data_bn", "templates_bn.csv"))
    ap.add_argument("--check_templates", action="store_true")
    ap.add_argument("--partial", action="store_true",
                    help="render only rows whose template is present; run all assertions; write nothing")
    ap.add_argument("--out_dir", default=os.path.join(ROOT, "data_bn"))
    a = ap.parse_args()
    templates = load_templates(a.templates)
    ok = check_all(templates)
    if a.check_templates:
        sys.exit(0 if ok else 1)
    if not ok:
        sys.exit("template check failed; fix templates_bn.csv first")
    if a.partial:
        build(templates, a.out_dir, partial=True)
        return
    assert len(templates) == 204, f"expected 204 templates, got {len(templates)}"
    build(templates, a.out_dir)


if __name__ == "__main__":
    main()
