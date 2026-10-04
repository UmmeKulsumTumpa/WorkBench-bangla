#!/usr/bin/env python3
"""Build a self-contained HTML report for one EN-vs-BN comparison.

Reads results/<comparison_id>/{metrics.csv, paired.csv, per_task_*.csv, run_meta_*.json,
failure_labels.csv (optional), report_notes.json (optional)} and the pilot task files, and writes
results/<comparison_id>/report.html. Stdlib only.

  python3 scripts/build_pilot_html.py --comparison_id workbench_pilot_ollama-gemma4-31b_c1
"""
import argparse
import csv
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
csv.field_size_limit(sys.maxsize)
DOMAINS = ["email", "calendar", "analytics", "project_management", "customer_relationship_manager", "multi_domain"]
DOMAIN_LABEL = {"email": "Email", "calendar": "Calendar", "analytics": "Analytics",
                "project_management": "Project mgmt", "customer_relationship_manager": "CRM",
                "multi_domain": "Multi-domain"}


def read_csv(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--comparison_id", required=True)
    ap.add_argument("--en_tasks", default="data_bn/pilot/pilot_en_tasks_and_outcomes.csv")
    ap.add_argument("--bn_tasks", default="data_bn/pilot/pilot_bn_tasks_and_outcomes.csv")
    a = ap.parse_args()
    d = ROOT / "results" / a.comparison_id

    metrics = {}
    for r in read_csv(d / "metrics.csv"):
        metrics.setdefault(r["scope"], {})[r["metric"]] = float(r["value"])
    meta_en = json.loads((d / "run_meta_en.json").read_text(encoding="utf-8"))
    meta_bn = json.loads((d / "run_meta_bn.json").read_text(encoding="utf-8"))

    def uid(r):
        return f"workbench:{r['source_file']}:{r['row_idx']}"
    en_t = {uid(r): r for r in read_csv(ROOT / a.en_tasks)}
    bn_t = {uid(r): r for r in read_csv(ROOT / a.bn_tasks)}
    per = {L: {r["task_uid"]: r for r in read_csv(d / f"per_task_{L}.csv")} for L in ("en", "bn")}

    labels = {}
    lp = d / "failure_labels.csv"
    if lp.exists():
        for r in read_csv(lp):
            labels[(r["task_uid"], r["language"])] = {
                "label": r["failure_label"], "sub": r.get("multilingual_subtype", ""),
                "evidence": r.get("evidence", ""), "notes": r.get("notes", "")}

    rows = []
    for r in read_csv(d / "paired.csv"):
        u = r["task_uid"]
        rows.append({
            "uid": u, "domain": r["domain"], "template": r["template_id"], "pair": r["pair_class"],
            "en": en_t[u]["task"], "bn": bn_t[u]["task"],
            "c_en": int(r["correct_en"]), "c_bn": int(r["correct_bn"]),
            "se_en": int(r["side_effect_en"]), "se_bn": int(r["side_effect_bn"]),
            "req_en": int(per["en"][u]["n_llm_requests"] or 0), "req_bn": int(per["bn"][u]["n_llm_requests"] or 0),
            "lab_en": labels.get((u, "en")), "lab_bn": labels.get((u, "bn")),
        })

    notes_p = d / "report_notes.json"
    notes = json.loads(notes_p.read_text(encoding="utf-8")) if notes_p.exists() else {}
    data = {"metrics": metrics, "rows": rows, "notes": notes,
            "domains": [{"key": k, "label": DOMAIN_LABEL[k]} for k in DOMAINS],
            "meta": {"model_id": meta_en["model_id"], "provider": meta_en["provider"],
                     "en_started": meta_en.get("started_at", ""), "bn_started": meta_bn.get("started_at", ""),
                     "req_en": meta_en.get("total_llm_requests"), "req_bn": meta_bn.get("total_llm_requests"),
                     "harness_commit": meta_en.get("harness_commit", "")[:7],
                     "tool_selection": meta_en.get("tool_selection"), "comparison_id": a.comparison_id}}
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    tpl = (ROOT / "scripts" / "pilot_report_template.html").read_text(encoding="utf-8")
    out = tpl.replace("/*__DATA__*/null", payload).replace("__TITLE__", html.escape(notes.get("title", "WorkBench Bangla Pilot")))
    # report_fragment.html: body-only page for claude.ai Artifact publishing (the publisher adds the skeleton).
    # report.html: complete standalone document for opening locally in any browser.
    (d / "report_fragment.html").write_text(out, encoding="utf-8")
    head_end = out.index("</style>") + len("</style>")
    full = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + out[:head_end] + "\n</head>\n<body>\n" + out[head_end:] + "\n</body>\n</html>\n")
    (d / "report.html").write_text(full, encoding="utf-8")
    print(f"wrote {d / 'report.html'} + report_fragment.html ({len(full) // 1024} KB, {len(rows)} tasks, {len(labels)} labels)")


if __name__ == "__main__":
    main()
