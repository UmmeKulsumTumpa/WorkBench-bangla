"""Experimental conditions for the EN/BN cross-lingual study.

A condition fixes which parts of the agent's input are in Bangla. It is selected with
``workbench-inference --condition <id>`` and is recorded in every run's ``_meta.json``.
Full documentation: ``../docs/conditions/README.md`` (project root).

Layers a condition controls:

- ``task_lang``: language of the task text. The tasks CSV must already be in that language;
  the harness only checks it (see :func:`check_task_language`).
- ``system_lang``: language of the system prompt (date line, act-without-confirmation line,
  output-language line).
- ``tool_desc_lang``: language of the tool descriptions sent in the ``tools=`` schema. Tool
  names, argument names and JSON keys always stay English.
- ``output_lang``: if set, one instruction line forces the language of the agent's replies.

Tool observations (environment data) are English in every condition: grading compares the
final sandbox state byte for byte.

To add a condition: add one entry to ``CONDITIONS``. To add a language: add
``data/conditions/<lang>/system_prompt.json`` and ``tool_descriptions.json`` and a
``LANGUAGE_NAMES`` entry.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

from src.evals.agent import ACT_WITHOUT_CONFIRMATION_SUFFIX
from src.tools.tool import Tool

WORKBENCH_ROOT = Path(__file__).resolve().parents[2]
CONDITIONS_DIR = WORKBENCH_ROOT / "data" / "conditions"

LANGUAGE_NAMES = {"en": "English", "bn": "Bangla"}

# English texts are the upstream strings, byte-identical (C0 and C1 must reproduce the pilot prompt).
_EN_PACK = {
    "datetime_prefix": (
        "Today's date is {weekday}, {date} and the current time is {time}. "
        "Remember the current date and time when completing tasks. "
        "Meetings must not start before 9am or end after 6pm."
    ),
    "weekdays": {d: d for d in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")},
    "act_without_confirmation": ACT_WITHOUT_CONFIRMATION_SUFFIX.strip(),
    "output_language_instruction": "Always write your replies to the user in {language}, regardless of the language of the task.",
    "language_names": dict(LANGUAGE_NAMES),
}

_BENGALI = re.compile(r"[ঀ-৿]")


@dataclass(frozen=True)
class Condition:
    id: str
    description: str
    task_lang: str
    system_lang: str
    tool_desc_lang: str
    output_lang: str | None
    reference: str | None  # condition this one is compared against by default

    @property
    def needs_structured_outputs(self) -> bool:
        # The ReAct prompt (PREFIX / FORMAT_INSTRUCTIONS / SUFFIX) is not translated.
        return self.system_lang != "en" or self.tool_desc_lang != "en"


CONDITIONS: dict[str, Condition] = {
    c.id: c
    for c in [
        Condition("c0", "English baseline", "en", "en", "en", None, None),
        Condition("c1", "Bangla task; English system prompt and tools", "bn", "en", "en", None, "c0"),
        Condition("c2", "Bangla task and system prompt; English tool descriptions", "bn", "bn", "en", None, "c0"),
        Condition("c3", "Fully Bangla interface: task, system prompt, tool descriptions", "bn", "bn", "bn", None, "c0"),
        Condition(
            "c4",
            "Bangla task; English system prompt and tools; replies forced to English",
            "bn",
            "en",
            "en",
            "en",
            "c0",
        ),
        Condition(
            "c5", "English task, system prompt and tools; replies forced to Bangla", "en", "en", "en", "bn", "c0"
        ),
        Condition(
            "c6",
            "Bangla task and system prompt; English tool descriptions; replies forced to Bangla",
            "bn",
            "bn",
            "en",
            "bn",
            "c0",
        ),
    ]
}


def get_condition(condition_id: str) -> Condition:
    try:
        return CONDITIONS[condition_id]
    except KeyError:
        raise ValueError(f"Unknown condition '{condition_id}'. Must be one of {', '.join(CONDITIONS)}") from None


def _pack_path(lang: str, name: str) -> Path:
    return CONDITIONS_DIR / lang / name


@lru_cache
def load_system_pack(lang: str) -> dict:
    """System-prompt texts for ``lang`` (English from code, other languages from JSON)."""
    if lang == "en":
        return _EN_PACK
    with open(_pack_path(lang, "system_prompt.json"), encoding="utf-8") as f:
        pack = json.load(f)
    missing = set(_EN_PACK) - set(pack)
    if missing:
        raise ValueError(f"{_pack_path(lang, 'system_prompt.json')}: missing keys {sorted(missing)}")
    return pack


@lru_cache
def load_tool_descriptions(lang: str) -> dict[str, str] | None:
    """Tool name -> description for ``lang``; ``None`` for English (use the docstrings)."""
    if lang == "en":
        return None
    with open(_pack_path(lang, "tool_descriptions.json"), encoding="utf-8") as f:
        return json.load(f)


def build_datetime_prefix(now: pd.Timestamp, lang: str = "en") -> str:
    pack = load_system_pack(lang)
    return pack["datetime_prefix"].format(
        weekday=pack["weekdays"][now.strftime("%A")], date=now.date(), time=now.time()
    )


def act_without_confirmation_text(lang: str = "en") -> str:
    return load_system_pack(lang)["act_without_confirmation"]


def extra_instructions(condition: Condition) -> tuple[str, ...]:
    """System-prompt lines appended after the act-without-confirmation line."""
    if condition.output_lang is None:
        return ()
    pack = load_system_pack(condition.system_lang)
    return (pack["output_language_instruction"].format(language=pack["language_names"][condition.output_lang]),)


def localize_tools(tools: list[Tool], lang: str) -> list[Tool]:
    """Copies of ``tools`` with descriptions in ``lang``. Names, signatures and arg schemas are unchanged."""
    descriptions = load_tool_descriptions(lang)
    if descriptions is None:
        return tools
    missing = [t.name for t in tools if t.name not in descriptions]
    if missing:
        raise ValueError(f"No '{lang}' description for tools: {', '.join(missing)}")
    return [dataclasses.replace(t, description=descriptions[t.name]) for t in tools]


def check_task_language(tasks: list[str], lang: str) -> None:
    """Fail fast when the tasks file does not match the condition's task language."""
    has_bn = [bool(_BENGALI.search(t)) for t in tasks]
    if lang == "bn" and not all(has_bn):
        raise ValueError(
            f"Condition expects Bangla tasks, but {has_bn.count(False)}/{len(tasks)} tasks have no Bengali script"
        )
    if lang == "en" and any(has_bn):
        raise ValueError(
            f"Condition expects English tasks, but {sum(has_bn)}/{len(tasks)} tasks contain Bengali script"
        )


def asset_fingerprints(condition: Condition) -> dict[str, str]:
    """sha256 of every asset file the condition reads, for ``_meta.json``."""
    files = set()
    for lang, name in (
        (condition.system_lang, "system_prompt.json"),
        (condition.tool_desc_lang, "tool_descriptions.json"),
    ):
        if lang != "en":
            files.add(_pack_path(lang, name))
    return {str(p.relative_to(WORKBENCH_ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}


def condition_metadata(condition: Condition) -> dict:
    return {
        "condition": condition.id,
        "condition_spec": dataclasses.asdict(condition),
        "condition_assets": asset_fingerprints(condition),
    }
