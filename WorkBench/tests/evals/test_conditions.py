import json
import os
import re
import tempfile
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.data_generation.data_generation_utils import HARDCODED_CURRENT_TIME
from src.evals.agent import ACT_WITHOUT_CONFIRMATION_SUFFIX, AgentResult, Route, build_structured_system_prompt
from src.evals.conditions import (
    CONDITIONS,
    Condition,
    act_without_confirmation_text,
    build_datetime_prefix,
    check_task_language,
    extra_instructions,
    get_condition,
    load_tool_descriptions,
    localize_tools,
)
from src.evals.inference import generate_results
from src.tools.tool import Tool, tool_to_openai_schema
from src.tools.toolkits import all_tools

_FAKE_ROUTE = Route("openai/gpt-4", "https://openrouter.ai/api/v1", "fake-key", "openrouter", True)
_BENGALI_DIGITS = re.compile(r"[০-৯]")

# Exact system prompt of the 2026-10-04 pilot runs (C0 and C1), from their _meta.json and agent.py.
PILOT_DATETIME_PREFIX = (
    "Today's date is Thursday, 2023-11-30 and the current time is 00:00:00. "
    "Remember the current date and time when completing tasks. Meetings must not start before 9am or end after 6pm."
)
PILOT_SYSTEM_PROMPT = PILOT_DATETIME_PREFIX + " " + ACT_WITHOUT_CONFIRMATION_SUFFIX.strip()


def test_registry_ids_and_references():
    assert list(CONDITIONS) == ["c0", "c1", "c2", "c3", "c4", "c5", "c6"]
    for c in CONDITIONS.values():
        assert c.reference is None or c.reference in CONDITIONS
    with pytest.raises(ValueError):
        get_condition("c9")


def test_english_prompt_reproduces_pilot_byte_for_byte():
    prefix = build_datetime_prefix(HARDCODED_CURRENT_TIME, "en")
    assert prefix == PILOT_DATETIME_PREFIX
    for cid in ("c0", "c1"):
        c = get_condition(cid)
        prompt = build_structured_system_prompt(
            build_datetime_prefix(HARDCODED_CURRENT_TIME, c.system_lang),
            True,
            act_without_confirmation_text(c.system_lang),
            extra_instructions(c),
        )
        assert prompt == PILOT_SYSTEM_PROMPT


def test_bangla_system_prompt():
    prefix = build_datetime_prefix(HARDCODED_CURRENT_TIME, "bn")
    assert "বৃহস্পতিবার" in prefix and "2023-11-30" in prefix and "00:00:00" in prefix
    text = prefix + act_without_confirmation_text("bn")
    assert not _BENGALI_DIGITS.search(text)
    assert not re.search(r"[A-Za-z]{4,}", text), "no English words left in the Bangla system prompt"


def test_output_language_lines():
    assert extra_instructions(get_condition("c0")) == ()
    assert extra_instructions(get_condition("c4")) == (
        "Always write your replies to the user in English, regardless of the language of the task.",
    )
    assert extra_instructions(get_condition("c5")) == (
        "Always write your replies to the user in Bangla, regardless of the language of the task.",
    )
    # c6: the output line is written in the system-prompt language (Bangla)
    assert extra_instructions(get_condition("c6")) == ("টাস্ক যে ভাষাতেই লেখা হোক না কেন, ইউজারকে সবসময় বাংলায় উত্তর দিও।",)


def _structured_prompt(c: Condition) -> str:
    return build_structured_system_prompt(
        build_datetime_prefix(HARDCODED_CURRENT_TIME, c.system_lang),
        True,
        act_without_confirmation_text(c.system_lang),
        extra_instructions(c),
    )


def test_c6_differs_from_c2_only_by_the_output_line():
    c2, c6 = get_condition("c2"), get_condition("c6")
    assert (c2.task_lang, c2.system_lang, c2.tool_desc_lang) == (c6.task_lang, c6.system_lang, c6.tool_desc_lang)
    assert _structured_prompt(c6) == _structured_prompt(c2) + " " + extra_instructions(c6)[0]


def test_bangla_tool_descriptions_cover_all_tools_and_keep_identifiers():
    bn = load_tool_descriptions("bn")
    assert set(bn) == {t.name for t in all_tools}
    localized = localize_tools(all_tools, "bn")
    for en_t, bn_t in zip(all_tools, localized):
        assert bn_t.name == en_t.name
        assert bn_t.args_schema == en_t.args_schema
        assert bn_t.signature_str == en_t.signature_str
        assert bn_t.func is en_t.func
        assert not _BENGALI_DIGITS.search(bn_t.description)
        en_s, bn_s = tool_to_openai_schema(en_t), tool_to_openai_schema(bn_t)
        assert en_s["function"]["parameters"] == bn_s["function"]["parameters"]
        assert bn_s["function"]["description"] == bn[en_t.name]
    assert localize_tools(all_tools, "en") is all_tools
    assert all_tools[0].description != localized[0].description, "originals must not be mutated"


def test_check_task_language():
    check_task_language(["Delete my last email from Nadia"], "en")
    check_task_language(["nadia-এর শেষ ইমেইলটা ডিলিট করো"], "bn")
    with pytest.raises(ValueError):
        check_task_language(["nadia-এর শেষ ইমেইলটা ডিলিট করো"], "en")
    with pytest.raises(ValueError):
        check_task_language(["Delete my last email", "ইমেইলটা ডিলিট করো"], "bn")


def _run(tmpdir: str, tasks: list[str], model_name: str = "gpt-4", **kwargs: object) -> tuple[list[dict], str]:
    csv_path = os.path.join(tmpdir, "pilot_xx_tasks_and_outcomes.csv")
    pd.DataFrame({"task": tasks, "outcome": ["[]"] * len(tasks)}).to_csv(csv_path, index=False)
    calls: list[dict] = []

    def fake_agent(model_name: str, tools: list[Tool], task: str, datetime_prefix: str, **kw: object) -> AgentResult:
        calls.append({"tools": tools, "datetime_prefix": datetime_prefix, **kw})
        return AgentResult(output="ok", intermediate_steps=[])

    cwd = os.getcwd()
    os.chdir(tmpdir)
    try:
        with patch("src.evals.inference.run_agent_structured", side_effect=fake_agent):
            generate_results(csv_path, model_name, structured_outputs=True, act_without_confirmation=True, **kwargs)
    finally:
        os.chdir(cwd)
    return calls, csv_path


@patch("src.evals.inference.reset_state")
@patch("src.evals.inference.resolve_route", return_value=_FAKE_ROUTE)
def test_generate_results_c3_layout_prompt_and_meta(_route: MagicMock, _reset: MagicMock):
    with tempfile.TemporaryDirectory() as tmpdir:
        calls, _ = _run(tmpdir, ["ইমেইলটা ডিলিট করো"], condition="c3")
        (call,) = calls
        assert "বৃহস্পতিবার" in call["datetime_prefix"]
        assert call["act_text"] == act_without_confirmation_text("bn")
        assert call["tools"][0].description == load_tool_descriptions("bn")[call["tools"][0].name]

        out_dir = os.path.join(tmpdir, "data", "results", "c3", "pilot_xx", "gpt-4")
        (meta_file,) = [f for f in os.listdir(out_dir) if f.endswith("_meta.json")]
        with open(os.path.join(out_dir, meta_file), encoding="utf-8") as f:
            meta = json.load(f)
        assert meta["condition"] == "c3"
        assert meta["condition_spec"]["tool_desc_lang"] == "bn"
        assert set(meta["condition_assets"]) == {
            "data/conditions/bn/system_prompt.json",
            "data/conditions/bn/tool_descriptions.json",
        }
        assert meta["system_prompt_sent"].startswith(call["datetime_prefix"])
        assert meta["run_label"] is None
        assert len(meta["harness_commit"]) == 40 and isinstance(meta["harness_dirty"], bool)


@patch("src.evals.inference.reset_state")
@patch("src.evals.inference.resolve_route", return_value=_FAKE_ROUTE)
def test_generate_results_c0_repeat_label_and_unchanged_prompt(_route: MagicMock, _reset: MagicMock):
    with tempfile.TemporaryDirectory() as tmpdir:
        calls, _ = _run(tmpdir, ["Delete my last email"], condition="c0", run_label="rep2")
        assert calls[0]["datetime_prefix"] == PILOT_DATETIME_PREFIX
        en_by_name = {t.name: t.description for t in all_tools}
        assert all(t.description == en_by_name[t.name] for t in calls[0]["tools"])
        assert calls[0]["extra_instructions"] == ()
        assert calls[0]["act_text"] == ACT_WITHOUT_CONFIRMATION_SUFFIX.strip()
        assert os.path.isdir(os.path.join(tmpdir, "data", "results", "c0-rep2", "pilot_xx", "gpt-4"))


@patch("src.evals.inference.reset_state")
@patch("src.evals.inference.resolve_route", return_value=_FAKE_ROUTE)
def test_generate_results_models_never_share_a_folder(_route: MagicMock, _reset: MagicMock):
    with tempfile.TemporaryDirectory() as tmpdir:
        _run(tmpdir, ["Delete my last email"], condition="c0")
        _run(tmpdir, ["Delete my last email"], condition="c0", model_name="gpt-4o")
        base = os.path.join(tmpdir, "data", "results", "c0", "pilot_xx")
        assert sorted(os.listdir(base)) == ["gpt-4", "gpt-4o"]
        for model in ("gpt-4", "gpt-4o"):
            files = os.listdir(os.path.join(base, model))
            assert files and all(f.startswith(model + "_all_") for f in files)


@patch("src.evals.inference.reset_state")
@patch("src.evals.inference.resolve_route", return_value=_FAKE_ROUTE)
def test_generate_results_rejects_mismatches(_route: MagicMock, _reset: MagicMock):
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(ValueError, match="Bangla tasks"):
            _run(tmpdir, ["Delete my last email"], condition="c1")
        with pytest.raises(ValueError, match="run_label"):
            _run(tmpdir, ["Delete my last email"], run_label="rep2")
        with pytest.raises(ValueError, match="run_label"):
            _run(tmpdir, ["Delete my last email"], condition="c0", run_label="Rep 2")
