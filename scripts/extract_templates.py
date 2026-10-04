#!/usr/bin/env python3
"""Extract the base templates of the WorkBench tasks to templates_en.csv.

Reads the 6 top-level tasks_and_outcomes CSVs (not v1/ or dated subdirs),
writes one row per distinct base_template, and prints verification stats
including whether slot values can be recovered from `task` via `chosen_template`.

Stdlib only.
"""
import argparse
import csv
import os
import re
import sys
from collections import Counter, OrderedDict

SOURCES = [
    "email",
    "calendar",
    "customer_relationship_manager",
    "analytics",
    "project_management",
    "multi_domain",
]
SLOT_RE = re.compile(r"\{([^{}]+)\}")
OUT_COLS = [
    "template_id", "source_file", "domains", "base_template", "n_tasks",
    "n_chosen_templates", "example_chosen_template", "example_task", "placeholders",
]


def slots(template):
    return SLOT_RE.findall(template)


def segments(template):
    """Split into [('lit', text) | ('slot', name)]."""
    out, pos = [], 0
    for m in SLOT_RE.finditer(template):
        if m.start() > pos:
            out.append(("lit", template[pos:m.start()]))
        out.append(("slot", m.group(1)))
        pos = m.end()
    if pos < len(template):
        out.append(("lit", template[pos:]))
    return out


def template_regex(template):
    """Anchored regex: literal text escaped, each slot -> non-greedy capture group."""
    parts = []
    for kind, val in segments(template):
        parts.append(re.escape(val) if kind == "lit" else "(.+?)")
    return re.compile("^" + "".join(parts) + "$", re.DOTALL)


def all_parses(template, task, limit=5):
    """Enumerate distinct slot assignments (non-empty values) that render task.

    A slot name repeated in the template must take the same value each time.
    Returns up to `limit` parses as list of tuples of (name, value).
    """
    segs = segments(template)
    results = []

    def rec(i, pos, binding, seq):
        if len(results) >= limit:
            return
        if i == len(segs):
            if pos == len(task):
                results.append(tuple(seq))
            return
        kind, val = segs[i]
        if kind == "lit":
            if task.startswith(val, pos):
                rec(i + 1, pos + len(val), binding, seq)
            return
        if val in binding:
            v = binding[val]
            if task.startswith(v, pos):
                rec(i + 1, pos + len(v), binding, seq + [(val, v)])
            return
        for end in range(pos + 1, len(task) + 1):
            v = task[pos:end]
            binding[val] = v
            rec(i + 1, end, binding, seq + [(val, v)])
            del binding[val]
            if len(results) >= limit:
                return

    rec(0, 0, {}, [])
    return results


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wb_root", default=os.path.join(here, "..", "WorkBench"))
    ap.add_argument("--out", default=os.path.join(here, "..", "data_bn", "templates_en.csv"))
    args = ap.parse_args()

    tdir = os.path.join(args.wb_root, "data", "processed", "tasks_and_outcomes")
    rows = []  # (source, row dict)
    per_file = OrderedDict()
    for src in SOURCES:
        path = os.path.join(tdir, f"{src}_tasks_and_outcomes.csv")
        with open(path, newline="", encoding="utf-8") as f:
            r = list(csv.DictReader(f))
        per_file[src] = len(r)
        rows.extend((src, d) for d in r)

    # --- 1. row counts
    total = len(rows)
    print(f"[1] total rows: {total}")
    for src, n in per_file.items():
        print(f"    {src}: {n}")
    assert total == 690, f"expected 690 rows, got {total}"

    # --- 3. no empty base_template
    empty = [(s, d["task"]) for s, d in rows if not d["base_template"].strip()]
    print(f"[3] rows with empty base_template: {len(empty)}")
    assert not empty, empty[:5]

    # --- group by base_template
    groups = OrderedDict()
    base_sources = {}
    for src, d in rows:
        bt = d["base_template"]
        groups.setdefault(bt, []).append((src, d))
        base_sources.setdefault(bt, OrderedDict())[src] = True

    # --- 2. unique base templates
    print(f"[2] unique base_template: {len(groups)}")
    cross = {bt: list(s) for bt, s in base_sources.items() if len(s) > 1}
    print(f"    base_templates appearing in >1 source file: {len(cross)}")
    for bt, s in cross.items():
        print(f"      {bt!r} -> {s}")
    assert len(groups) == 69, f"expected 69 unique base_template, got {len(groups)}"

    # --- write CSV
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    out_rows = []
    for i, (bt, members) in enumerate(groups.items(), 1):
        src0, d0 = members[0]
        chosen = OrderedDict((d["chosen_template"], None) for _, d in members)
        out_rows.append({
            "template_id": f"T{i:02d}",
            "source_file": src0,
            "domains": d0["domains"],
            "base_template": bt,
            "n_tasks": len(members),
            "n_chosen_templates": len(chosen),
            "example_chosen_template": d0["chosen_template"],
            "example_task": d0["task"],
            "placeholders": "|".join(slots(bt)),
        })
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS)
        w.writeheader()
        w.writerows(out_rows)
    print(f"    wrote {len(out_rows)} rows -> {os.path.abspath(args.out)}")

    # --- base vs chosen relationship
    n_equal = sum(d["base_template"] == d["chosen_template"] for _, d in rows)
    distinct_chosen = {d["chosen_template"] for _, d in rows}
    chosen_with_slots = sum(bool(slots(c)) for c in distinct_chosen)
    same_slotset = sum(
        set(slots(d["chosen_template"])) == set(slots(d["base_template"])) for _, d in rows
    )
    multi_chosen = [r for r in out_rows if r["n_chosen_templates"] > 1]
    print("[base vs chosen]")
    print(f"    rows with chosen_template == base_template: {n_equal}/{total}")
    print(f"    distinct chosen_template: {len(distinct_chosen)}")
    print(f"    distinct chosen_templates containing {{slot}}: {chosen_with_slots}/{len(distinct_chosen)}")
    print(f"    rows where chosen slot-set == base slot-set: {same_slotset}/{total}")
    print(f"    base_templates with >1 chosen variant: {len(multi_chosen)}")
    shown = 0
    for bt, members in groups.items():
        variants = OrderedDict((d["chosen_template"], None) for _, d in members)
        if len(variants) > 1 and shown < 3:
            shown += 1
            print(f"      base: {bt!r}")
            for v in list(variants)[:4]:
                print(f"        chosen: {v!r}")

    # --- 4. regex recovery of slot values
    exact = ambiguous = failed = 0
    fails, ambs = [], []
    regex_ok = 0
    for src, d in rows:
        ct, task = d["chosen_template"], d["task"]
        if template_regex(ct).match(task):
            regex_ok += 1
        parses = all_parses(ct, task)
        if len(parses) == 1:
            exact += 1
        elif len(parses) == 0:
            failed += 1
            fails.append((src, ct, task))
        else:
            ambiguous += 1
            ambs.append((src, ct, task, parses[:2]))
    print("[4] task vs chosen_template slot recovery")
    print(f"    anchored non-greedy regex matches: {regex_ok}/{total}")
    print(f"    unique parse: {exact}  ambiguous: {ambiguous}  failed: {failed}")
    for src, ct, task in fails[:10]:
        print(f"      FAIL [{src}] template={ct!r}\n                  task={task!r}")
    for src, ct, task, ps in ambs[:10]:
        print(f"      AMBIG [{src}] template={ct!r}\n                   task={task!r}")
        for p in ps:
            print(f"                   parse={dict(p)}")
    assert exact + ambiguous + failed == total

    # --- 5. placeholder names
    ph = Counter()
    for bt in groups:
        ph.update(slots(bt))
    ph_rows = Counter()
    for _, d in rows:
        ph_rows.update(slots(d["base_template"]))
    print(f"[5] distinct placeholder names in base_templates: {len(ph)}")
    for name, n in ph.most_common():
        print(f"    {name}: {n} templates, {ph_rows[name]} task-rows")

    print("All assertions passed.")


if __name__ == "__main__":
    sys.exit(main())
