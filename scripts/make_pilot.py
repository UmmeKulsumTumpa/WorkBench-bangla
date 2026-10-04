#!/usr/bin/env python3
"""Stratified pilot subset: 15 tasks per task file (6 files -> 90), fixed seed, maximal template coverage.

Selection per file: templates are visited in a seeded random order, round-robin. Each visit takes
one not-yet-chosen row of that template, preferring a chosen_template variant not yet used for
that template. Stops at 15. Every template in a file with <=15 templates is therefore covered at
least once (multi_domain has 21 templates -> 15 covered).

Writes (rows in original file order, original columns + `source_file`, `row_idx`):
  data_bn/pilot/pilot_en_tasks_and_outcomes.csv
  data_bn/pilot/pilot_bn_tasks_and_outcomes.csv   (same rows, from data_bn/*_bn_tasks_and_outcomes.csv)
  data_bn/pilot/pilot_index.csv                   (task_uid, source_file, row_idx, template_id, variant)

The extra columns are ignored by WorkBench (it reads `task`, `outcome`, `domains` by name; verified in
src/evals/inference.py / metrics.py). Stdlib only.
"""
import csv
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_DIR = os.path.join(ROOT, "WorkBench", "data", "processed", "tasks_and_outcomes")
SOURCES = ["email", "calendar", "customer_relationship_manager", "analytics",
           "project_management", "multi_domain"]
SEED = 20261004
PER_FILE = 15


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)


def select(rows, rng):
    by_t = {}
    for i, r in enumerate(rows):
        by_t.setdefault(r["base_template"], []).append(i)
    order = sorted(by_t)
    rng.shuffle(order)
    for t in order:
        rng.shuffle(by_t[t])
    chosen, used_variants = [], {t: set() for t in order}
    while len(chosen) < PER_FILE:
        progressed = False
        for t in order:
            if len(chosen) == PER_FILE:
                break
            cands = [i for i in by_t[t] if i not in chosen]
            if not cands:
                continue
            fresh = [i for i in cands if rows[i]["chosen_template"] not in used_variants[t]]
            i = (fresh or cands)[0]
            chosen.append(i)
            used_variants[t].add(rows[i]["chosen_template"])
            progressed = True
        assert progressed
    return sorted(chosen)


def main():
    rng = random.Random(SEED)
    out_dir = os.path.join(ROOT, "data_bn", "pilot")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(ROOT, "data_bn", "templates_en.csv"), encoding="utf-8") as f:
        tid = {r["base_template"]: r["template_id"] for r in csv.DictReader(f)}
    en_out, bn_out, idx = [], [], []
    fields = None
    for src in SOURCES:
        fields, en_rows = read(os.path.join(TASKS_DIR, f"{src}_tasks_and_outcomes.csv"))
        _, bn_rows = read(os.path.join(ROOT, "data_bn", f"{src}_bn_tasks_and_outcomes.csv"))
        assert len(en_rows) == len(bn_rows)
        for i in select(en_rows, rng):
            assert en_rows[i]["outcome"] == bn_rows[i]["outcome"]
            extra = {"source_file": src, "row_idx": str(i)}
            en_out.append({**en_rows[i], **extra})
            bn_out.append({**bn_rows[i], **extra})
            idx.append({"task_uid": f"workbench:{src}:{i}", "source_file": src, "row_idx": i,
                        "template_id": tid[en_rows[i]["base_template"]],
                        "chosen_template_en": en_rows[i]["chosen_template"]})
    cols = fields + ["source_file", "row_idx"]
    for name, rows in (("pilot_en", en_out), ("pilot_bn", bn_out)):
        tasks = [r["task"] for r in rows]
        assert len(set(tasks)) == len(tasks), f"{name}: duplicate task text"
        with open(os.path.join(out_dir, f"{name}_tasks_and_outcomes.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, quoting=csv.QUOTE_ALL, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    with open(os.path.join(out_dir, "pilot_index.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(idx[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(idx)
    n_t = len({r["template_id"] for r in idx})
    n_v = len({r["chosen_template_en"] for r in idx})
    print(f"pilot: {len(idx)} tasks, {n_t}/69 templates, {n_v}/204 variants, seed {SEED}")


if __name__ == "__main__":
    main()
