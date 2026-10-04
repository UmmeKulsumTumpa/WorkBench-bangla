#!/usr/bin/env python3
"""Build data_bn/slot_inventory.csv and data_bn/glossary_candidates.csv.

Input: data_bn/slot_values_en.csv (from recover_slots.py) + WorkBench sandbox DB CSVs.
Slot value provenance (where natural-language values come from):
  - WorkBench/src/tools/analytics.py: METRICS <-> METRIC_NAMES, VALID_PLOT_TYPES, VALID_VALUES_TO_PLOT
  - WorkBench/src/data_generation/data_generation_utils.py: get_natural_language_date ("%B %-d"),
    get_natural_language_time ("%-I[:%M]", no am/pm), format_event_duration ("N minute"/"N hour"),
    get_first_name (lowercase first token of email)
  - WorkBench/scripts/data_generation/task_outcome_generation/generate_*_task_and_outcome.py
    (status .lower(), product_interest .lower(), more/less, higher/lower, before/after, traffic sources)

Stdlib only.
"""
import argparse
import csv
import os
import re
import sys
from collections import Counter, OrderedDict, defaultdict
from datetime import datetime

DB_FILES = ["analytics_data", "calendar_events", "customer_relationship_manager_data", "emails", "project_tasks"]

P, T, C = "preserve", "translate", "canonical"
# slot -> (proposed_type, rationale). BORDERLINE marks cases to review.
DECISIONS = {
    # --- people / entities
    "name": (P, "lowercase first name = get_first_name(email); agent must resolve to email via company_directory. Keep Latin script (lowercase as in source)."),
    "name_1": (P, "lowercase first name from email (project_management)."),
    "name_2": (P, "lowercase first name from email (project_management)."),
    "sender_name": (P, "lowercase first name from email; also embedded in quoted tool-arg event name 'Catch up with {sender_name}'."),
    "recipient_name": (P, "lowercase first name from email."),
    "recipient_name1": (P, "lowercase first name from email."),
    "recipient_name2": (P, "lowercase first name from email."),
    "assigned_to_first_name": (P, "Capitalised first name (CRM templates) vs lowercase elsewhere; resolves to assigned_to_email."),
    "new_assigned_to_first_name": (P, "Capitalised first name; resolves to assigned_to_email."),
    "sender": (P, "Full email address; passed verbatim to send_email."),
    "current_customer_name": (P, "Exact CRM customer_name; also embedded in quoted event name 'Update on {current_customer_name}'."),
    "new_customer_name": (P, "New CRM customer_name passed verbatim to add_customer."),
    "subject": (P, "Email subject; matched against emails.subject and/or used as quoted tool arg (send_email subject, event_name in T51)."),
    "body": (P, "Email body passed verbatim to send_email (contains newlines and lowercase names). BORDERLINE: kept English even inside a Bangla instruction."),
    "event_name": (P, "Calendar event name; matched against DB or passed to create/update_event verbatim."),
    "new_event_name": (P, "New event name passed verbatim to update_event."),
    "task_name": (P, "Project task name passed verbatim to create_task."),
    "board": (P, "Board name = project_tasks.board exact value (3 values). BORDERLINE: closed-class, could be canonical, but it is an entity name passed verbatim -> preserve."),
    # --- numbers / ISO
    "threshold": (P, "Integer threshold."),
    "days": (P, "Integer day count."),
    "weeks": (P, "Integer week count."),
    "n_weeks": (P, "Integer week count."),
    "past_n_weeks": (P, "Integer week count."),
    "date_min": (P, "ISO date (YYYY-MM-DD) = analytics_data.date_of_visit; passed as time_min."),
    "natural_language_growth_threshold": (P, "Percentage string 'N%' (2/3/5/10%). BORDERLINE: numeric -> preserve; digits could be rendered in Bangla numerals if numerals policy says so."),
    # --- natural-language: translate
    "natural_language_metric": (T, "One of METRIC_NAMES (analytics.py) -> METRICS column. BORDERLINE/RISK: in multi_domain templates it is also embedded inside quoted tool-arg strings ('Improve {m}', 'Discuss {m}', email titles/bodies) whose expected outcome is English."),
    "natural_language_metric_2": (T, "One of METRIC_NAMES. Same quoted-literal risk as natural_language_metric ('Improve {natural_language_metric_2}')."),
    "natural_language_date": (T, "'Month D' (get_natural_language_date), no year (2023 implied); agent converts to ISO."),
    "natural_language_date_max": (T, "'Month D'; agent converts to ISO time_max."),
    "natural_language_due_date": (T, "'Month D'; agent converts to ISO due_date."),
    "natural_language_email_date": (T, "'Month D'; agent matches emails.sent_datetime date."),
    "natural_language_event_date": (T, "'Month D'; agent converts to ISO event_start date."),
    "natural_language_time": (T, "Bare 12h clock without am/pm ('2', '11:30'; get_natural_language_time). BORDERLINE: Bangla rendering may add a period-of-day word (e.g. দুপুর) which disambiguates more than the English does."),
    "natural_language_duration": (T, "'N minute'/'N hour' (format_event_duration) -> minutes."),
    "duration": (T, "BORDERLINE: slot name reused with two meanings: '30 minute'/'1.5 hour' (calendar create/push-back; push-back template appends 's') vs bare integer day count in 'last {duration} days' (numbers -> preserve). Treat per template."),
    "more_or_less": (T, "Comparator {more, less}."),
    "higher_or_lower": (T, "Comparator {higher, lower}."),
    "most_or_least": (T, "Superlative {most, least} (only 'most' occurs)."),
    "before_or_after": (T, "Temporal comparator {before, after}."),
    # --- closed-class labels: canonical
    "new_status_natural_language": (C, "status.lower() of CRM status {Qualified, Won, Lost, Lead, Proposal}; tool arg is the capitalised DB value."),
    "natural_language_product_interest": (C, "product_interest.lower() of CRM product_interest; tool filter uses the capitalised DB value."),
    "traffic_source_1": (C, "analytics_data.traffic_source exact value; plot value_to_plot = visits_<source with _>."),
    "traffic_source_2": (C, "analytics_data.traffic_source exact value."),
    "plot_type": (C, "VALID_PLOT_TYPES value passed verbatim as plot_type."),
    "day_of_week": (C, "Weekday name, mixed case (Title in analytics, lowercase in some variants; .day_name()/.lower()); agent resolves to date relative to 2023-11-30."),
    "next_day": (C, "Weekday name (Title case); agent resolves to the next such date."),
}

METRIC_MAP = {"total visits": "total_visits", "average session duration": "session_duration_seconds",
              "engaged users": "user_engaged"}


def db_value_for(slot, v):
    """Known DB / tool value a translate/canonical slot value maps to ('' if none)."""
    if slot.startswith("natural_language_metric"):
        return f"metric/value_to_plot={METRIC_MAP[v]}"
    if slot.startswith("natural_language_date") or slot in (
            "natural_language_due_date", "natural_language_email_date", "natural_language_event_date"):
        return datetime.strptime(f"2023 {v}", "%Y %B %d").strftime("%Y-%m-%d")
    if slot == "natural_language_time":
        h, _, m = v.partition(":")
        h = int(h)
        h24 = h + 12 if h < 9 else h  # work hours 09:00-18:00
        return f"{h24:02d}:{m or '00'}:00 (12h->24h assuming work hours)"
    if slot in ("natural_language_duration", "duration"):
        mm = re.fullmatch(r"([\d.]+) (minute|hour)", v)
        if mm:
            n = float(mm.group(1)) * (60 if mm.group(2) == "hour" else 1)
            return f"duration_minutes={int(n)}"
        if v.isdigit():
            return f"{v} days (number; preserve)"
        return ""
    if slot == "new_status_natural_language":
        return f"customer_relationship_manager_data.status={v.capitalize()}"
    if slot == "natural_language_product_interest":
        return f"customer_relationship_manager_data.product_interest={v.capitalize()}"
    if slot.startswith("traffic_source"):
        return f"analytics_data.traffic_source={v}; value_to_plot=visits_{v.replace(' ', '_')}"
    if slot == "plot_type":
        return f"plot_type={v}"
    if slot in ("day_of_week", "next_day"):
        return f"weekday={v.capitalize()} (resolved to ISO date relative to 2023-11-30)"
    if slot in ("more_or_less", "higher_or_lower", "most_or_least", "before_or_after"):
        return {"more": ">", "less": "<", "higher": ">", "lower": "<", "most": "max", "least": "min",
                "before": "<", "after": ">"}[v] + " (comparator; no DB value)"
    return ""


def load_db(proc_dir):
    """{'table.col': (set_of_lowercased_cells, list_of_lowercased_cells)}"""
    cols = OrderedDict()
    for t in DB_FILES:
        with open(os.path.join(proc_dir, f"{t}.csv"), newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                for k, v in r.items():
                    # emails.body stores newlines as literal '\n'
                    cell = (v or "").replace("\\n", "\n").lower()
                    cols.setdefault(f"{t}.{k}", []).append(cell)
    return OrderedDict((k, (set(v), v)) for k, v in cols.items())


def db_match(values, db, allow_substring=True):
    """Exact (case-insensitive) cell match per column; substring fallback only if allowed."""
    vals = [v for v in values if not re.fullmatch(r"[\d.:%]+", v)]
    if not vals:
        return "n/a (numeric values not matched)"
    exact, sub = Counter(), Counter()
    unmatched_exact = []
    for v in vals:
        lv = v.lower()
        hit = [c for c, (s, _) in db.items() if lv in s]
        exact.update(hit)
        if not hit:
            unmatched_exact.append(lv)
    for lv in unmatched_exact if allow_substring else []:
        if len(lv) < 3:
            continue
        hit = [c for c, (_, cells) in db.items() if any(lv in cell for cell in cells)]
        sub.update(hit)
    n = len(vals)
    parts = []
    if exact:
        parts.append("exact: " + ", ".join(f"{c} ({k}/{n})" for c, k in exact.most_common(3)))
    if sub:
        parts.append("substring: " + ", ".join(f"{c} ({k}/{n})" for c, k in sub.most_common(3)))
    if not parts and not allow_substring:
        return "none (exact only; substring hits in free text not meaningful for this type)"
    return "; ".join(parts) if parts else "none"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.join(here, "..")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slot_values", default=os.path.join(root, "data_bn", "slot_values_en.csv"))
    ap.add_argument("--db_dir", default=os.path.join(root, "WorkBench", "data", "processed"))
    ap.add_argument("--out_inventory", default=os.path.join(root, "data_bn", "slot_inventory.csv"))
    ap.add_argument("--out_glossary", default=os.path.join(root, "data_bn", "glossary_candidates.csv"))
    args = ap.parse_args()

    counts = defaultdict(Counter)  # slot -> value -> n
    with open(args.slot_values, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            counts[r["slot"]][r["value"]] += 1
    assert len(counts) == 46, len(counts)
    missing = set(counts) - set(DECISIONS)
    assert not missing, missing

    db = load_db(args.db_dir)
    inv = []
    for slot in sorted(counts, key=lambda s: (-sum(counts[s].values()), s)):
        c = counts[slot]
        typ, why = DECISIONS[slot]
        inv.append({
            "slot": slot, "n_occurrences": sum(c.values()), "n_distinct_values": len(c),
            "example_values": " | ".join(v.replace("\n", "\\n") for v, _ in c.most_common(8)),
            "db_match": db_match(list(c), db, allow_substring=(typ == P)), "proposed_type": typ, "rationale": why,
        })
    with open(args.out_inventory, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(inv[0]))
        w.writeheader()
        w.writerows(inv)

    glos = []
    for slot in sorted(counts):
        if DECISIONS[slot][0] not in (T, C):
            continue
        for v, n in sorted(counts[slot].items(), key=lambda kv: (-kv[1], kv[0])):
            glos.append({"slot": slot, "value_en": v, "n_occurrences": n,
                         "db_value_it_maps_to_if_known": db_value_for(slot, v)})
    with open(args.out_glossary, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(glos[0]))
        w.writeheader()
        w.writerows(glos)

    tc = Counter(r["proposed_type"] for r in inv)
    distinct_vals = {r["value_en"] for r in glos}
    print(f"inventory: {len(inv)} slots {dict(tc)} -> {os.path.abspath(args.out_inventory)}")
    print(f"glossary: {len(glos)} (slot,value) rows, {len(distinct_vals)} distinct value strings "
          f"-> {os.path.abspath(args.out_glossary)}")


if __name__ == "__main__":
    sys.exit(main())
