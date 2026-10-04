#!/usr/bin/env python3
"""Build data_bn/glossary.csv and data_bn/variants_en.csv (translation worklist).

glossary.csv: one row per (slot, value_en) for every slot value that is NOT
rendered verbatim in Bangla tasks. Slots/values absent from the glossary are
preserved byte-identical (names, emails, subjects, numbers, ISO dates, ...).
Rules are deterministic and documented in docs/translation_policy.md.

variants_en.csv: the 204 distinct chosen_templates (translation units), each
with one example task + outcome, so translators can see which literals reach
the ground truth.

Stdlib only. Run from the project root: python3 scripts/build_glossary.py
"""
import csv
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_DIR = os.path.join(ROOT, "WorkBench", "data", "processed", "tasks_and_outcomes")
SOURCES = ["email", "calendar", "customer_relationship_manager", "analytics",
           "project_management", "multi_domain"]

MONTHS_BN = {
    "January": "জানুয়ারি", "February": "ফেব্রুয়ারি", "March": "মার্চ", "April": "এপ্রিল",
    "May": "মে", "June": "জুন", "July": "জুলাই", "August": "আগস্ট",
    "September": "সেপ্টেম্বর", "October": "অক্টোবর", "November": "নভেম্বর", "December": "ডিসেম্বর",
}
WEEKDAYS_BN = {
    "monday": "সোমবার", "tuesday": "মঙ্গলবার", "wednesday": "বুধবার", "thursday": "বৃহস্পতিবার",
    "friday": "শুক্রবার", "saturday": "শনিবার", "sunday": "রবিবার",
}
COMPARATORS_BN = {
    "more": "বেশি", "less": "কম", "higher": "বেশি", "lower": "কম",
    "most": "সবচেয়ে বেশি", "least": "সবচেয়ে কম", "before": "আগে", "after": "পরে",
}
METRICS_BN = {
    "total visits": "মোট ভিজিট",
    "engaged users": "এনগেজড ইউজার",
    "average session duration": "গড় সেশনের সময়কাল",
}
UNITS_BN = {"minute": "মিনিট", "hour": "ঘণ্টা"}

DATE_SLOTS = {"natural_language_date", "natural_language_date_max", "natural_language_due_date",
              "natural_language_email_date", "natural_language_event_date"}
WEEKDAY_SLOTS = {"day_of_week", "next_day"}
COMPARATOR_SLOTS = {"more_or_less", "higher_or_lower", "most_or_least", "before_or_after"}
METRIC_SLOTS = {"natural_language_metric", "natural_language_metric_2"}
DURATION_SLOTS = {"duration", "natural_language_duration"}
# Closed-class values identical (case-insensitively) to DB/tool enum values: kept in Latin script.
LATIN_ENUM_SLOTS = {"new_status_natural_language", "natural_language_product_interest",
                    "traffic_source_1", "traffic_source_2", "plot_type"}

DATE_RE = re.compile(r"^(January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2})$")
DUR_RE = re.compile(r"^(\d+(?:\.\d+)?) (minute|hour)$")


def render(slot, value):
    """Return (value_bn, kind, rule) or None if the value is preserved verbatim."""
    if slot in DATE_SLOTS:
        m = DATE_RE.match(value)
        assert m, (slot, value)
        return f"{m.group(2)} {MONTHS_BN[m.group(1)]}", "translate", "date: <day ASCII> <Bangla month>"
    if slot in WEEKDAY_SLOTS:
        return WEEKDAYS_BN[value.lower()], "translate", "weekday"
    if slot in COMPARATOR_SLOTS:
        return COMPARATORS_BN[value], "translate", "comparator"
    if slot in METRIC_SLOTS:
        return METRICS_BN[value], "translate", "analytics metric (use {slot!en} inside quoted literals)"
    if slot in DURATION_SLOTS:
        m = DUR_RE.match(value)
        if not m:  # bare day count, e.g. "last {duration} days"
            assert value.isdigit(), (slot, value)
            return None
        return f"{m.group(1)} {UNITS_BN[m.group(2)]}", "translate", "duration: <ASCII number> <Bangla unit>"
    if slot in LATIN_ENUM_SLOTS:
        return value, "canonical", "DB/tool enum value kept in Latin script"
    return None


def main():
    gloss = {}
    variants = {}
    from recover_slots import recover_slots  # noqa: E402  (same folder)
    for src in SOURCES:
        with open(os.path.join(TASKS_DIR, f"{src}_tasks_and_outcomes.csv"), encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        for i, row in enumerate(rows):
            ct = row["chosen_template"]
            if ct not in variants:
                variants[ct] = dict(source_file=src, base_template=row["base_template"], chosen_template=ct,
                                    example_task=row["task"], example_outcome=row["outcome"], n_tasks=0)
            variants[ct]["n_tasks"] += 1
            for slot, value in recover_slots(ct, row["task"]).items():
                r = render(slot, value)
                if r is None:
                    continue
                key = (slot, value)
                if key not in gloss:
                    gloss[key] = dict(slot=slot, value_en=value, value_bn=r[0], kind=r[1], rule=r[2], n_occurrences=0)
                gloss[key]["n_occurrences"] += 1

    # template ids from templates_en.csv
    with open(os.path.join(ROOT, "data_bn", "templates_en.csv"), encoding="utf-8") as f:
        tid = {r["base_template"]: r["template_id"] for r in csv.DictReader(f)}
    out = sorted(variants.values(), key=lambda v: (tid[v["base_template"]], v["chosen_template"] != v["base_template"], v["chosen_template"]))
    counter = {}
    for v in out:
        t = tid[v["base_template"]]
        counter[t] = counter.get(t, 0) + 1
        v["template_id"] = t
        v["variant_id"] = f"{t}.v{counter[t]}"
    cols = ["variant_id", "template_id", "source_file", "base_template", "chosen_template", "n_tasks",
            "example_task", "example_outcome"]
    with open(os.path.join(ROOT, "data_bn", "variants_en.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for v in out:
            w.writerow({c: v[c] for c in cols})

    gcols = ["slot", "value_en", "value_bn", "kind", "rule", "n_occurrences"]
    with open(os.path.join(ROOT, "data_bn", "glossary.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=gcols, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for k in sorted(gloss):
            w.writerow(gloss[k])

    bengali_digits = re.compile("[০-৯]")
    assert not any(bengali_digits.search(g["value_bn"]) for g in gloss.values())
    print(f"variants: {len(out)} (expected 204); glossary rows: {len(gloss)}; "
          f"translated: {sum(g['kind']=='translate' for g in gloss.values())}; "
          f"latin canonical: {sum(g['kind']=='canonical' for g in gloss.values())}")
    assert len(out) == 204


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
