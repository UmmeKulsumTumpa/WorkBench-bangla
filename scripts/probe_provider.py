"""Probe WorkBench model routes before a full inference run.

Run from the WorkBench repo root (its venv provides ``openai`` + ``python-dotenv``):

    cd WorkBench && uv run python ../scripts/probe_provider.py --models ollama-gpt-oss-20b ollama-gemma4-31b
    cd WorkBench && uv run python ../scripts/probe_provider.py --models ollama-gpt-oss-20b --dry_run

Each model is resolved with WorkBench's own ``resolve_route``, so the probe hits
exactly the endpoint / model id / key that inference would use. Per model it does
two requests, strictly one at a time with a 2s sleep in between:

1. a tiny chat ("Reply with the single word: OK"), and
2. a tool-call test with a single ``get_weather(city)`` tool.

It records HTTP status, latency, token usage and rate-limit-ish response headers
(never request/auth headers, never the API key). A 429 stops probing that model;
there are no retries. Results go to ``results/probe/<provider>_<YYYY-MM-DD>.json``
in the project root (appended across runs on the same day).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKBENCH_ROOT = PROJECT_ROOT / "WorkBench"
PROBE_DIR = PROJECT_ROOT / "results" / "probe"

if str(WORKBENCH_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKBENCH_ROOT))

from dotenv import load_dotenv  # noqa: E402

from src.evals import agent  # noqa: E402
from src.evals.agent import resolve_route  # noqa: E402

SLEEP_BETWEEN_REQUESTS_S = 2.0
CHAT_PROMPT = "Reply with the single word: OK"
TOOL_PROMPT = "What's the weather in Dhaka? Use the tool."
WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current weather for a city.",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "City name"}},
            "required": ["city"],
        },
    },
}

# Response headers worth keeping. Anything auth/cookie-like is dropped outright.
_HEADER_DENY = ("authorization", "cookie", "api-key", "apikey", "token", "secret")
_HEADER_LIMIT_HINTS = ("limit", "remaining", "reset")


def _load_env() -> None:
    """Load .env files without ever printing their values (no override)."""
    for path in (PROJECT_ROOT / ".env", Path.cwd() / ".env"):
        if path.is_file():
            load_dotenv(path, override=False)


def _interesting_headers(headers: Any) -> dict[str, str]:
    kept: dict[str, str] = {}
    if headers is None:
        return kept
    for name, value in headers.items():
        lower = name.lower()
        if any(d in lower for d in _HEADER_DENY):
            continue
        if (
            "ratelimit" in lower
            or "retry" in lower
            or (lower.startswith("x-") and any(h in lower for h in _HEADER_LIMIT_HINTS))
        ):
            kept[lower] = value
    return kept


def _usage(completion: Any) -> dict[str, int | None] | None:
    usage = getattr(completion, "usage", None)
    if usage is None:
        return None
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
    }


def _route_info(model_name: str) -> dict[str, Any]:
    """Resolve the route; return metadata that is safe to print/store (no key)."""
    config = agent.MODEL_REGISTRY.get(model_name)
    provider_cfg = agent._PROVIDERS.get(config.provider) if config else None
    info: dict[str, Any] = {
        "model_name": model_name,
        "registry_provider": config.provider if config else None,
        "api_key_env": provider_cfg.api_key_env if provider_cfg else None,
    }
    try:
        route = resolve_route(model_name)
    except (ValueError, OSError) as e:
        info["route_error"] = str(e)
        return info
    info.update(
        provider=route.provider,
        base_url=route.base_url,
        model_id=route.model_id,
        supports_temperature=route.supports_temperature,
        key_present=bool(route.api_key) if provider_cfg and provider_cfg.api_key_env else "n/a (keyless, dummy sent)",
        _route=route,  # stripped before printing/saving
    )
    return info


def _base_kwargs(info: dict[str, Any], max_tokens: int) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"model": info["model_id"], "max_tokens": max_tokens}
    if info["supports_temperature"]:
        kwargs["temperature"] = 0
    return kwargs


def _planned_requests(info: dict[str, Any], args: argparse.Namespace) -> list[tuple[str, dict[str, Any]]]:
    chat = _base_kwargs(info, args.chat_max_tokens)
    chat["messages"] = [{"role": "user", "content": CHAT_PROMPT}]
    tool = _base_kwargs(info, args.tool_max_tokens)
    tool["messages"] = [{"role": "user", "content": TOOL_PROMPT}]
    tool["tools"] = [WEATHER_TOOL]
    return [("chat", chat), ("tool", tool)]


def _send(client: Any, kind: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    import openai

    rec: dict[str, Any] = {"kind": kind}
    t0 = time.monotonic()
    try:
        raw = client.chat.completions.with_raw_response.create(**kwargs)
        rec["latency_s"] = round(time.monotonic() - t0, 2)
        rec["http_status"] = raw.status_code
        rec["headers"] = _interesting_headers(raw.headers)
        completion = raw.parse()
    except openai.APIStatusError as e:
        rec["latency_s"] = round(time.monotonic() - t0, 2)
        rec["http_status"] = e.status_code
        rec["headers"] = _interesting_headers(getattr(e.response, "headers", None))
        rec["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        rec["ok"] = False
        return rec
    except Exception as e:  # connection errors, timeouts, bad JSON, ...
        rec["latency_s"] = round(time.monotonic() - t0, 2)
        rec["http_status"] = None
        rec["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        rec["ok"] = False
        return rec

    choice = completion.choices[0] if completion.choices else None
    msg = choice.message if choice else None
    rec["finish_reason"] = choice.finish_reason if choice else None
    rec["usage"] = _usage(completion)
    content = (msg.content or "") if msg else ""
    rec["content"] = content[:200]

    if kind == "chat":
        rec["ok"] = "ok" in content.strip().lower()
        return rec

    calls = []
    tool_ok = False
    for tc in (msg.tool_calls or []) if msg else []:
        fn = getattr(tc, "function", None)
        entry: dict[str, Any] = {"name": getattr(fn, "name", None), "arguments_raw": getattr(fn, "arguments", None)}
        try:
            parsed = json.loads(entry["arguments_raw"] or "")
            entry["arguments_valid_json"] = True
            if entry["name"] == "get_weather" and "dhaka" in json.dumps(parsed, ensure_ascii=False).lower():
                tool_ok = True
        except (TypeError, ValueError):
            entry["arguments_valid_json"] = False
        calls.append(entry)
    rec["tool_calls"] = calls
    rec["ok"] = tool_ok
    return rec


def _public(info: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in info.items() if not k.startswith("_")}


def _print_table(rows: list[dict[str, Any]]) -> None:
    def cell(req: dict[str, Any] | None) -> str:
        if req is None:
            return "-"
        status = req.get("http_status")
        mark = "ok" if req.get("ok") else "FAIL"
        return f"{status} {req.get('latency_s', '?')}s {mark}"

    header = f"{'model':<30} {'provider':<13} {'chat':<18} {'tool':<18} notes"
    print(header)
    print("-" * len(header))
    for row in rows:
        reqs = {r["kind"]: r for r in row.get("requests", [])}
        notes = row.get("route_error") or row.get("stopped_reason") or ""
        if not notes:
            errs = [r.get("error") for r in reqs.values() if r.get("error")]
            notes = (errs[0] or "")[:60] if errs else ""
        print(
            f"{row['model_name']:<30} {str(row.get('provider')):<13} "
            f"{cell(reqs.get('chat')):<18} {cell(reqs.get('tool')):<18} {notes}"
        )


def _save(rows: list[dict[str, Any]], started_at: str) -> list[Path]:
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    by_provider: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_provider.setdefault(str(row.get("provider") or row.get("registry_provider") or "unknown"), []).append(row)
    written = []
    for provider, prow in by_provider.items():
        path = PROBE_DIR / f"{provider}_{today}.json"
        runs: list[dict[str, Any]] = []
        if path.is_file():
            try:
                runs = json.loads(path.read_text(encoding="utf-8")).get("runs", [])
            except (ValueError, AttributeError):
                runs = []
        runs.append({"started_at": started_at, "results": prow})
        path.write_text(json.dumps({"runs": runs}, indent=2, ensure_ascii=False), encoding="utf-8")
        written.append(path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", required=True, help="MODEL_REGISTRY keys")
    parser.add_argument("--dry_run", action="store_true", help="print planned requests; send nothing")
    parser.add_argument("--chat_max_tokens", type=int, default=64)
    parser.add_argument("--tool_max_tokens", type=int, default=512)
    args = parser.parse_args()

    _load_env()
    started_at = dt.datetime.now().isoformat(timespec="seconds")
    infos = [_route_info(m) for m in args.models]

    if args.dry_run:
        print(f"DRY RUN: no requests will be sent. Sleep between requests: {SLEEP_BETWEEN_REQUESTS_S}s.\n")
        for info in infos:
            pub = _public(info)
            if "route_error" in info:
                print(f"[{info['model_name']}] ROUTE ERROR: {info['route_error']}\n")
                continue
            print(
                f"[{pub['model_name']}] provider={pub['provider']} base_url={pub['base_url']} "
                f"model_id={pub['model_id']} key_env={pub['api_key_env']} key_present={pub['key_present']}"
            )
            for kind, kwargs in _planned_requests(info, args):
                shown = {k: v for k, v in kwargs.items() if k != "tools"}
                if "tools" in kwargs:
                    shown["tools"] = [t["function"]["name"] for t in kwargs["tools"]]
                print(f"  POST {pub['base_url']}/chat/completions ({kind}): {json.dumps(shown, ensure_ascii=False)}")
            print()
        today = dt.date.today().isoformat()
        targets = sorted(
            {f"{i.get('provider') or i.get('registry_provider') or 'unknown'}_{today}.json" for i in infos}
        )
        print(f"Would write: {', '.join(str(PROBE_DIR / t) for t in targets)}")
        return

    rows: list[dict[str, Any]] = []
    first_request = True
    for info in infos:
        row = _public(info)
        row["requests"] = []
        rows.append(row)
        if "route_error" in info:
            continue
        route = info["_route"]
        client = agent._get_openai_client(route.api_key, route.base_url)
        for kind, kwargs in _planned_requests(info, args):
            if not first_request:
                time.sleep(SLEEP_BETWEEN_REQUESTS_S)
            first_request = False
            rec = _send(client, kind, kwargs)
            row["requests"].append(rec)
            if rec.get("http_status") == 429:
                row["stopped_reason"] = f"429 on {kind}; stopped probing this model"
                break

    _print_table(rows)
    for path in _save(rows, started_at):
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
