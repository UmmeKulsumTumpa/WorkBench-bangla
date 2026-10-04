# Bangla translation policy (WorkBench) — DRAFT for owner review at STOP (a)

Principle: **translate the instruction side, keep the environment English** (MAPS, Hofman et al., EACL 2026 Findings). Field typing follows BabelFlow (Peng et al., 2026, arXiv 2609.23490): every piece of a task is **preserve**, **translate**, or **canonical**.

## 1. Unit of translation
- WorkBench tasks are `chosen_template` with its `{slot}`s filled in. There are **204 chosen templates**, which are rewordings of 69 base templates (66 bases have 3 variants, 3 have 2).
- We translate all 204. Each BN variant should reword its base the way the EN variant does, so the BN data keeps the EN paraphrase variety.
- Worklist: `data_bn/variants_en.csv`. Output: `data_bn/templates_bn.csv`.
- Every task is then rendered by `scripts/make_bn_tasks.py`. Only the `task` and `chosen_template` columns change; `outcome`, `base_template` and `domains` are byte-identical to EN.

## 2. Preserve (byte-identical, Latin script)
- **Person first names** exactly as in the task, including their case (`nadia`, `Raj`).
- **Customer names**, email addresses, IDs, URLs.
- Email **subjects** and **bodies**, **event names**, **task names**, **board names** (`Front end`, `Design`, `Back end`).
- **ASCII digits, numbers and percentages** (`3`, `10%`, `1.5`), ISO dates (`2023-11-17`), clock times (`11:30`, `2`).
- Tool names, argument names, JSON keys (they never appear in task text).
- **Any text inside quotation marks that reaches a tool argument.** For example, in "create a task called 'Improve {natural_language_metric}'", the whole quoted string stays English, including the slot value. This is checked automatically: every string literal in a row's `outcome` that appears verbatim in the EN task must also appear verbatim in the BN task.
- **Never use Bengali numerals (০–৯).**

## 3. Translate
- All other natural-language instruction text: natural, polite-but-direct workplace Bangla (the register of a Dhaka office Slack message), not word-for-word.
- Interpretive slot values, which the agent has to understand but never copies into a tool call. These go through `data_bn/glossary.csv`:
  - **Dates:** `November 21` → `21 নভেম্বর` (ASCII day + Bangla Gregorian month name, Bangla day-month order; the year stays implicit as in EN).
  - **Weekdays:** `Monday`/`monday` → `সোমবার`.
  - **Comparators:**
    - `more`/`higher` → `বেশি`
    - `less`/`lower` → `কম`
    - `most` → `সবচেয়ে বেশি`
    - `before` → `আগে`
    - `after` → `পরে`
  - **Durations:** `30 minute` → `30 মিনিট`; `1.5 hour` → `1.5 ঘণ্টা`. A bare day count stays a number.
  - **Analytics metrics** (when not inside quotes):
    - `total visits` → `মোট ভিজিট`
    - `engaged users` → `এনগেজড ইউজার`
    - `average session duration` → `গড় সেশনের সময়কাল`

## 4. Canonical (decided once, applied everywhere)
- **DB/tool enum values stay in Latin script, unquoted, with the same case as in the EN task.** They are not quoted unless the EN task quotes them. This covers project list names (`Backlog`, `In Progress`, `In Review`, `Completed`), whether they appear as slots or as template text. It also covers the enum slot values listed below.
- **Values whose English surface form is the DB/tool enum value** stay in **Latin script**: CRM status (`qualified`, `won`, `lost`, `proposal`, `lead`), product interest (`hardware`, `software`, …), traffic source (`direct`, `referral`, `search engine`, `social media`), plot type (`bar`, `line`, `scatter`, `histogram`). This is how Bangla professionals type CRM/analytics jargon, and it keeps the environment vocabulary English (MAPS).
- **Case markers on Latin-script entities** use a hyphen: `{name}-কে`, `{name}-এর`, `{name}-কে ইমেইল করো`. This is standard Bangla orthography for Latin words. It also exposes a realistic failure mode: an agent passing `nadia-কে` to a tool is labelled `language_induced_tool_misuse`.
- **Fixed workplace loanwords**, used the same way in every template:
  - email → ইমেইল
  - meeting → মিটিং
  - event → ইভেন্ট
  - calendar → ক্যালেন্ডার
  - task → টাস্ক
  - board → বোর্ড
  - customer → কাস্টমার
  - CRM → CRM
  - plot/chart → চার্ট
  - inbox → ইনবক্স
  - reply → রিপ্লাই
  - forward → ফরোয়ার্ড
  - deadline/due date → ডেডলাইন
  - status → স্ট্যাটাস
  - subject/title → সাবজেক্ট
  - backlog → `Backlog` (enum, Latin)
  - CRM statuses → Latin (`lead`, `won`, …)
- **Bangla suffixes attach directly to Bangla-script slot values** (`{natural_language_metric}ের` → মোট ভিজিটের; `{natural_language_date} তারিখে`). They take a hyphen after Latin-script values (`{name}-এর`, `CRM-এ`, `In Progress-এ`).

## 5. Template slot syntax in `templates_bn.csv`
- `{slot}` renders the glossary Bangla value if `(slot, value)` is in `glossary.csv`; otherwise it renders the raw value (preserve).
- `{slot!en}` always renders the raw English value. Use it inside quoted literals that reach a tool argument.
- Every slot of the EN variant must appear at least once in the BN variant. Slots may be reordered for Bangla word order (SOV).

## 6. Conditions
- **C1 (primary):** BN task text, with the system prompt, tool descriptions and environment in English.
- **C2 (secondary, later):** as C1, plus a Bangla `PREFIX`/`SUFFIX`/`ACT_WITHOUT_CONFIRMATION_SUFFIX`. Only the instruction prose of the system prompt is translated; JSON keys and `"Final Answer"` keywords stay English.

## 7. Owner decisions requested (defaults shown)
1. **Month names translated** (`21 নভেম্বর`), not kept English (`November 21`)? Default: translated.
2. **Metrics translated** (`মোট ভিজিট`), while CRM/analytics enum values stay Latin? Default: yes.
3. Loanword choices in §4: ইমেইল/মিটিং/টাস্ক etc., vs. native terms (বৈঠক, কাজ). Default: loanwords, as in real office usage.
4. Hyphenated case markers on Latin names (`nadia-কে`). Default: yes.
5. `natural_language_time` (e.g. `2`, `11:30`) has no am/pm in EN. We keep it bare (`2টায়`) and don't add দুপুর/বিকেল, which would add information EN doesn't have. Default: keep bare.
