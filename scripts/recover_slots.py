#!/usr/bin/env python3
"""Recover slot values from WorkBench tasks given their chosen_template.

`recover_slots(chosen_template, task)` returns the unique {slot: value} dict
that renders `task` from `chosen_template`, or raises SlotParseError if there
is no parse or more than one.

Closed-class slots are constrained to their generator vocabulary (see
WorkBench/scripts/data_generation/task_outcome_generation/*.py), which removes
the ambiguity of adjacent slots such as `{natural_language_metric} {more_or_less}`.

CLI: reads the 6 top-level tasks_and_outcomes CSVs, asserts a unique parse for
all 690 rows, writes data_bn/slot_values_en.csv (one row per task x slot name).

Stdlib only.
"""
import argparse
import csv
import os
import re
import sys

SOURCES = [
    "email",
    "calendar",
    "customer_relationship_manager",
    "analytics",
    "project_management",
    "multi_domain",
]
SLOT_RE = re.compile(r"\{([^{}]+)\}")

# Closed-class slots: value must be one of these (from the generator scripts).
CLOSED_CLASS = {
    "more_or_less": {"more", "less"},
    "higher_or_lower": {"higher", "lower"},
    "most_or_least": {"most", "least"},
    "before_or_after": {"before", "after"},
}

OUT_COLS = ["source_file", "row_idx", "base_template", "chosen_template", "slot", "value"]


class SlotParseError(ValueError):
    pass


def segments(template):
    """Split template into [('lit', text) | ('slot', name)]."""
    out, pos = [], 0
    for m in SLOT_RE.finditer(template):
        if m.start() > pos:
            out.append(("lit", template[pos:m.start()]))
        out.append(("slot", m.group(1)))
        pos = m.end()
    if pos < len(template):
        out.append(("lit", template[pos:]))
    return out


def all_parses(template, task, limit=2):
    """Enumerate up to `limit` distinct slot bindings (non-empty values) rendering task.

    Repeated slot names must bind the same value; closed-class slots must take
    a value from CLOSED_CLASS.
    """
    segs = segments(template)
    results = []

    def rec(i, pos, binding):
        if len(results) >= limit:
            return
        if i == len(segs):
            if pos == len(task):
                results.append(dict(binding))
            return
        kind, val = segs[i]
        if kind == "lit":
            if task.startswith(val, pos):
                rec(i + 1, pos + len(val), binding)
            return
        if val in binding:
            v = binding[val]
            if task.startswith(v, pos):
                rec(i + 1, pos + len(v), binding)
            return
        if val in CLOSED_CLASS:
            candidates = [pos + len(c) for c in sorted(CLOSED_CLASS[val]) if task.startswith(c, pos)]
        else:
            candidates = range(pos + 1, len(task) + 1)
        for end in candidates:
            binding[val] = task[pos:end]
            rec(i + 1, end, binding)
            del binding[val]
            if len(results) >= limit:
                return

    rec(0, 0, {})
    return results


def recover_slots(chosen_template, task):
    """Return the unique {slot: value} parse of `task` under `chosen_template`; raise otherwise."""
    parses = all_parses(chosen_template, task, limit=2)
    if not parses:
        raise SlotParseError(f"no parse: template={chosen_template!r} task={task!r}")
    if len(parses) > 1:
        raise SlotParseError(
            f"ambiguous parse: template={chosen_template!r} task={task!r} parses={parses}"
        )
    return parses[0]


def load_rows(wb_root):
    tdir = os.path.join(wb_root, "data", "processed", "tasks_and_outcomes")
    rows = []
    for src in SOURCES:
        path = os.path.join(tdir, f"{src}_tasks_and_outcomes.csv")
        with open(path, newline="", encoding="utf-8") as f:
            for idx, d in enumerate(csv.DictReader(f)):
                rows.append((src, idx, d))
    return rows


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wb_root", default=os.path.join(here, "..", "WorkBench"))
    ap.add_argument("--out", default=os.path.join(here, "..", "data_bn", "slot_values_en.csv"))
    args = ap.parse_args()

    rows = load_rows(args.wb_root)
    assert len(rows) == 690, f"expected 690 rows, got {len(rows)}"

    out, errors, slot_names = [], [], set()
    for src, idx, d in rows:
        ct = d["chosen_template"]
        try:
            vals = recover_slots(ct, d["task"])
        except SlotParseError as e:
            errors.append(f"[{src}:{idx}] {e}")
            continue
        # sanity: re-render must reproduce the task exactly
        rendered = SLOT_RE.sub(lambda m: vals[m.group(1)], ct)
        assert rendered == d["task"], (src, idx)
        # slots of chosen template must equal slots of base template
        assert set(SLOT_RE.findall(ct)) == set(SLOT_RE.findall(d["base_template"])), (src, idx)
        seen = []
        for name in SLOT_RE.findall(ct):
            if name not in seen:
                seen.append(name)
        for name in seen:
            slot_names.add(name)
            out.append({
                "source_file": src, "row_idx": idx, "base_template": d["base_template"],
                "chosen_template": ct, "slot": name, "value": vals[name],
            })

    for e in errors:
        print(e, file=sys.stderr)
    n_ok = len(rows) - len(errors)
    print(f"unique parse: {n_ok}/{len(rows)}; slot names: {len(slot_names)}; slot-value rows: {len(out)}")
    assert not errors, f"{len(errors)} rows without a unique parse"

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS)
        w.writeheader()
        w.writerows(out)
    print(f"wrote {os.path.abspath(args.out)}")


if __name__ == "__main__":
    sys.exit(main())
