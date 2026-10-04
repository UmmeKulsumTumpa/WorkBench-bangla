# Review cycle 1: EN→BN templates (204 rows)

Reviewer: independent senior reviewer. Inputs: `templates_bn.csv` (=`review_sheet.csv` template_bn), `glossary.csv`, `docs/translation_policy.md`.
Outputs: `review_cycle1.csv` (99 rows flagged), `templates_bn_cycle1_candidate.csv`. The candidate **passes** `make_bn_tasks.py --partial`: 204/204 templates OK, 690 tasks render, GT literals survive, no duplicate tasks, no Bengali digits. No two variants of the same template are identical.

## Counts
| Severity (per row, highest wins) | Rows |
|---|---|
| critical | 18 |
| major | 63 |
| minor | 18 |
| **total** | **99** / 204 |

Issue instances by category (a row can have more than one): B-enum 60, C-consistency 38, B-policy 4, A-meaning 3, C-register 1.

- **critical (18):** DB enum values transliterated into Bangla script: ইন প্রোগ্রেস, ইন রিভিউ, কমপ্লিটেড, ব্যাকলগ (T42–T46) and লিড (T50). The agent would have to turn these back into a tool argument value, and the other batches keep these values in Latin script. T50 also had `CRM এ` without the hyphen.
- **major (63):** enum values put in quotes although EN doesn't quote them: `'lead'`, `'qualified'`, `'proposal'`, `'lost'` (T23–T28), `'line'`, `'bar'`, `'histogram'` (T30–T40), `'in progress'`, `'in review'` (T41). Also `'status'` in quotes (T21), transliterated লাইন (T38.v1/v2), টাইটেল (T52–T56), and ওভারডিউ (T57, T64).
- **minor (18):** bare কাল for "tomorrow" (batch 5), দয়া করে (T03.v3, T12.v3), `{subject!en}` outside quotes (T51.v1), honorific উনি/ওনাকে (T23.v3), and plural তাদের/তারা for one customer (T49).

No meaning errors found in quantifiers, step order, cancel vs delete, reply vs forward, or assign vs reassign. Every batch keeps these distinctions.

## Cross-batch decisions standardised
| Concept | Chosen rendering | Was |
|---|---|---|
| list names / CRM status / plot type | Latin, unquoted, EN case + hyphenated suffix: `in progress-এ`, `in review-এ`, `completed-এ`, `backlog-এ`, `lead`, `lost-এ`, `line চার্ট` | ইন প্রোগ্রেসে, ব্যাকলগে, লিড, `'lead'`, `'line'` |
| suffix on Latin `in review` | `-এ` (not `-তে`) | `'in review'-তে` |
| CRM field "status" (unquoted in EN) | স্ট্যাটাস | `'status'` (outdated checker workaround; `field=` names are now exempt) |
| email title/subject | সাবজেক্ট | টাইটেল (T52–T56) |
| overdue | ডেডলাইন পেরিয়ে যাওয়া (9 rows already; uses §4 ডেডলাইন; T64 extends T56) | ওভারডিউ (T57, T64) |
| tomorrow | আগামীকাল | কাল |
| please | প্লিজ | দয়া করে |
| CRM locative | `CRM-এ` (hyphen) | `CRM এ` |

These were already consistent and are kept: delete→ডিলিট, cancel→বাতিল, reply→রিপ্লাই, forward→ফরোয়ার্ড, schedule→শিডিউল, book→বুক (each follows the EN word), assign/reassign→অ্যাসাইন/রিঅ্যাসাইন, chart/plot→চার্ট (চার্ট বানাও / চার্টে দেখাও), and the তুমি register.

## Questions for the owner
1. **`front-end board` → ফ্রন্ট-এন্ড বোর্ড (21 rows, T60–T69).** §2 says board names stay Latin, but the checker rejects bare `front-end`, and the EN surface form is not the DB value `Front end` anyway. Keep the transliteration, or allowlist `front-end` in the checker and use Latin? I did not change these rows.
2. **Missing `?` on casual EN questions** (batch 1: T05.v2, T06.v2, T07.v2, T08.v2, T09.v3, T10.v3, T11.v2, T13.v2, T14.v3). These copy EN, but in Bangla `…করে দিতে পারবে` without `?` reads like a statement ("you will be able to…"). I recommend adding `?`. Not changed.
3. **Lowercase enum values** (`in progress`, `completed`, `backlog`, `lead`) follow "same case as EN", but the DB values are capitalised (`In Progress`). Please confirm this is intended.
4. **Curly quotes** (`‘…’`, `“…”`) in T54 and T64 work around apostrophes inside bodies (`haven't`, `let's`). The literals survive, so this is acceptable. A sturdier quote regex in the checker would let these rows use straight quotes like the rest.
5. **CRM locative.** Batch T15–T28 uses CRM সিস্টেমে / CRM রেকর্ডে (a workaround for the old checker) and batch T57–T69 uses `CRM-এ`. Both read naturally, so I left them. Decide whether to standardise.
6. **Stale translator notes.** Notes on T21, T23, T26, T28, T30–T40 and T50 cite checker limits that commit a5b58d4 removed. The notes column should be refreshed when the edits are merged.
