"""Routing for the OpenAI-compatible providers added on ``bangla-eval``:
``ollama_cloud``, ``ollama_local`` and ``groq``."""

import re

import pytest

from src.evals import agent
from src.evals.agent import MODEL_REGISTRY, ModelConfig, resolve_route

_ENV_KEYS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "OPENROUTER_API_KEY",
    "OLLAMA_API_KEY",
    "GROQ_API_KEY",
    "OLLAMA_CLOUD_BASE_URL",
    "OLLAMA_LOCAL_BASE_URL",
    "GROQ_BASE_URL",
)

OLLAMA_CLOUD_MODELS = {
    "ollama-gpt-oss-20b": "gpt-oss:20b",
    "ollama-gpt-oss-120b": "gpt-oss:120b",
    "ollama-nemotron-3-nano-30b": "nemotron-3-nano:30b",
    "ollama-gemma4-31b": "gemma4:31b",
}


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


@pytest.fixture
def groq_model(monkeypatch: pytest.MonkeyPatch) -> str:
    # Groq ids carry a vendor "/" that must NOT be stripped.
    monkeypatch.setitem(MODEL_REGISTRY, "test-groq-gpt-oss-120b", ModelConfig("openai/gpt-oss-120b", True, "groq"))
    return "test-groq-gpt-oss-120b"


# --- ollama_cloud ---------------------------------------------------------


def test_ollama_cloud_routes_direct(clean_env: pytest.MonkeyPatch):
    clean_env.setenv("OLLAMA_API_KEY", "ol-key")
    clean_env.setenv("OPENROUTER_API_KEY", "or-key")
    route = resolve_route("ollama-gpt-oss-20b")
    assert route.provider == "ollama_cloud"
    assert route.base_url == "https://ollama.com/v1"
    assert route.api_key == "ol-key"
    assert route.model_id == "gpt-oss:20b"
    assert route.supports_temperature is True


def test_ollama_cloud_base_url_env_override(clean_env: pytest.MonkeyPatch):
    clean_env.setenv("OLLAMA_API_KEY", "ol-key")
    clean_env.setenv("OLLAMA_CLOUD_BASE_URL", "https://proxy.example/v1")
    assert resolve_route("ollama-gpt-oss-20b").base_url == "https://proxy.example/v1"


def test_ollama_cloud_missing_key_raises_without_openrouter_fallback(clean_env: pytest.MonkeyPatch):
    clean_env.setenv("OPENROUTER_API_KEY", "or-key")
    with pytest.raises(OSError, match="OLLAMA_API_KEY"):
        resolve_route("ollama-gpt-oss-20b")


@pytest.mark.parametrize(("name", "model_id"), sorted(OLLAMA_CLOUD_MODELS.items()))
def test_ollama_cloud_registry_entries(clean_env: pytest.MonkeyPatch, name: str, model_id: str):
    config = MODEL_REGISTRY[name]
    assert config == ModelConfig(model_id, True, "ollama_cloud")
    clean_env.setenv("OLLAMA_API_KEY", "ol-key")
    assert resolve_route(name).model_id == model_id


# --- ollama_local ---------------------------------------------------------


def test_ollama_local_needs_no_key_and_sends_dummy(clean_env: pytest.MonkeyPatch):
    route = resolve_route("ollama-local-qwen3-8b")
    assert route.provider == "ollama_local"
    assert route.base_url == "http://localhost:11434/v1"
    assert route.api_key == "ollama"
    assert route.model_id == "qwen3:8b"


def test_ollama_local_base_url_env_override(clean_env: pytest.MonkeyPatch):
    clean_env.setenv("OLLAMA_LOCAL_BASE_URL", "http://gpu-box:11434/v1")
    assert resolve_route("ollama-local-qwen3-8b").base_url == "http://gpu-box:11434/v1"


# --- groq -----------------------------------------------------------------


def test_groq_routes_direct_without_slug_stripping(clean_env: pytest.MonkeyPatch, groq_model: str):
    clean_env.setenv("GROQ_API_KEY", "gq-key")
    route = resolve_route(groq_model)
    assert route.provider == "groq"
    assert route.base_url == "https://api.groq.com/openai/v1"
    assert route.api_key == "gq-key"
    assert route.model_id == "openai/gpt-oss-120b"


def test_groq_base_url_env_override(clean_env: pytest.MonkeyPatch, groq_model: str):
    clean_env.setenv("GROQ_API_KEY", "gq-key")
    clean_env.setenv("GROQ_BASE_URL", "https://groq-proxy.example/v1")
    assert resolve_route(groq_model).base_url == "https://groq-proxy.example/v1"


def test_groq_missing_key_raises_without_openrouter_fallback(clean_env: pytest.MonkeyPatch, groq_model: str):
    clean_env.setenv("OPENROUTER_API_KEY", "or-key")
    with pytest.raises(OSError, match="GROQ_API_KEY"):
        resolve_route(groq_model)


# --- registry / config invariants -----------------------------------------


def test_every_registry_provider_is_known():
    assert {c.provider for c in MODEL_REGISTRY.values()} <= set(agent._PROVIDERS)


def test_existing_providers_keep_original_config():
    pc = agent.ProviderConfig
    assert agent._PROVIDERS["openai"] == pc("https://api.openai.com/v1", "OPENAI_API_KEY")
    assert agent._PROVIDERS["anthropic"] == pc("https://api.anthropic.com/v1", "ANTHROPIC_API_KEY")
    assert agent._PROVIDERS["google"] == pc("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY")
    assert agent._PROVIDERS["openrouter"] == pc(agent._OPENROUTER_BASE_URL, "OPENROUTER_API_KEY")


def test_new_registry_keys_are_filename_safe():
    for name in [*OLLAMA_CLOUD_MODELS, "ollama-local-qwen3-8b"]:
        assert re.fullmatch(r"[a-z0-9.\-]+", name), name
        assert "_all_" not in name and "_domains_" not in name


# --- hard deadline --------------------------------------------------------


def test_hard_deadline_defaults_to_75(clean_env: pytest.MonkeyPatch):
    clean_env.delenv("WB_HARD_DEADLINE", raising=False)
    assert agent._hard_deadline_from_env() == 75.0


def test_hard_deadline_env_override(clean_env: pytest.MonkeyPatch):
    clean_env.setenv("WB_HARD_DEADLINE", "300")
    assert agent._hard_deadline_from_env() == 300.0
