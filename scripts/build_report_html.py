#!/usr/bin/env python3
"""Build a self-contained HTML report for one comparison (results/comparisons/<comparison_id>/).

Reads metrics.csv, paired.csv, per_task_{ref,treat}.csv, run_meta_{ref,treat}.json, and optionally
failure_labels.csv (keyed by task_uid + condition) and report_notes.json (headline text). Task texts come from
the tasks files recorded in run_meta. Writes report.html (standalone) and report_fragment.html (for claude.ai
artifact publishing) into the same folder. Stdlib only.

  python3 scripts/build_report_html.py --comparison_id pilot_ollama-gemma4-31b_c1_vs_c0

Limitation: the template's wording says "English" for the reference and "Bangla" for the treatment, so the
builder only accepts comparisons with an English-task reference and a Bangla-task treatment (C1-C4 vs C0).
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
DOMAIN_LABEL = {
    "email": "Email",
    "calendar": "Calendar",
    "analytics": "Analytics",
    "project_management": "Project mgmt",
    "customer_relationship_manager": "CRM",
    "multi_domain": "Multi-domain",
}


def read_csv(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--comparison_id", required=True)
    a = ap.parse_args()
    d = ROOT / "results" / "comparisons" / a.comparison_id

    metrics = {}
    for r in read_csv(d / "metrics.csv"):
        name = r["metric"].replace("_ref", "_en").replace("_treat", "_bn")  # template keys
        metrics.setdefault(r["scope"], {})[name] = float(r["value"])
    meta_en = json.loads((d / "run_meta_ref.json").read_text(encoding="utf-8"))
    meta_bn = json.loads((d / "run_meta_treat.json").read_text(encoding="utf-8"))
    if (meta_en["language"], meta_bn["language"]) != ("en", "bn"):
        sys.exit(
            f"template wording assumes an English reference vs a Bangla treatment; got "
            f"{meta_en['language']} vs {meta_bn['language']}. Generalize scripts/report_template.html first."
        )

    def uid(r):
        return f"workbench:{r['source_file']}:{r['row_idx']}"

    en_t = {uid(r): r for r in read_csv(ROOT / meta_en["tasks_file"])}
    bn_t = {uid(r): r for r in read_csv(ROOT / meta_bn["tasks_file"])}
    per = {
        L: {r["task_uid"]: r for r in read_csv(d / f"per_task_{side}.csv")}
        for L, side in (("en", "ref"), ("bn", "treat"))
    }
    lang_of = {meta_en["condition"]: "en", meta_bn["condition"]: "bn"}

    labels = {}
    lp = d / "failure_labels.csv"
    if lp.exists():
        for r in read_csv(lp):
            if r["condition"] not in lang_of:
                continue
            labels[(r["task_uid"], lang_of[r["condition"]])] = {
                "label": r["failure_label"],
                "sub": r.get("multilingual_subtype", ""),
                "evidence": r.get("evidence", ""),
                "notes": r.get("notes", ""),
            }

    rows = []
    for r in read_csv(d / "paired.csv"):
        u = r["task_uid"]
        rows.append(
            {
                "uid": u,
                "domain": r["domain"],
                "template": r["template_id"],
                "pair": {"ref_only": "en_only", "treat_only": "bn_only"}.get(r["pair_class"], r["pair_class"]),
                "en": en_t[u]["task"],
                "bn": bn_t[u]["task"],
                "c_en": int(r["correct_ref"]),
                "c_bn": int(r["correct_treat"]),
                "se_en": int(r["side_effect_ref"]),
                "se_bn": int(r["side_effect_treat"]),
                "req_en": int(per["en"][u]["n_llm_requests"] or 0),
                "req_bn": int(per["bn"][u]["n_llm_requests"] or 0),
                "lab_en": labels.get((u, "en")),
                "lab_bn": labels.get((u, "bn")),
            }
        )

    notes_p = d / "report_notes.json"
    notes = json.loads(notes_p.read_text(encoding="utf-8")) if notes_p.exists() else {}
    data = {
        "metrics": metrics,
        "rows": rows,
        "notes": notes,
        "domains": [{"key": k, "label": DOMAIN_LABEL[k]} for k in DOMAINS],
        "meta": {
            "model_id": meta_en["model_id"],
            "provider": meta_en["provider"],
            "en_started": meta_en.get("started_at", ""),
            "bn_started": meta_bn.get("started_at", ""),
            "req_en": meta_en.get("total_llm_requests"),
            "req_bn": meta_bn.get("total_llm_requests"),
            "harness_commit": meta_en.get("harness_commit", "")[:7],
            "tool_selection": meta_en.get("tool_selection"),
            "comparison_id": a.comparison_id,
        },
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    tpl = (ROOT / "scripts" / "report_template.html").read_text(encoding="utf-8")
    out = tpl.replace("/*__DATA__*/null", payload).replace(
        "__TITLE__", html.escape(notes.get("title", "WorkBench Bangla Pilot"))
    )
    # report_fragment.html: body-only page for claude.ai Artifact publishing (the publisher adds the skeleton).
    # report.html: complete standalone document for opening locally in any browser.
    (d / "report_fragment.html").write_text(out, encoding="utf-8")
    head_end = out.index("</style>") + len("</style>")
    full = (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        + out[:head_end]
        + "\n</head>\n<body>\n"
        + out[head_end:]
        + "\n</body>\n</html>\n"
    )
    (d / "report.html").write_text(full, encoding="utf-8")
    print(
        f"wrote {d / 'report.html'} + report_fragment.html ({len(full) // 1024} KB, {len(rows)} tasks, {len(labels)} labels)"
    )


if __name__ == "__main__":
    main()
