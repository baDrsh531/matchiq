from types import SimpleNamespace

import pytest

from llm import llm_client
from llm.prompt_templates import system_prompt


class _FakeInteractions:
    def __init__(self):
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return SimpleNamespace(output_text="Rapport généré.")


def test_generate_report_returns_output_text(monkeypatch):
    fake_interactions = _FakeInteractions()
    fake_client = SimpleNamespace(interactions=fake_interactions)
    monkeypatch.setattr(llm_client, "_get_client", lambda: fake_client)

    result = llm_client.generate_report("Analyse ce joueur.")

    assert result == "Rapport généré."
    assert fake_interactions.last_kwargs["model"] == llm_client.DEFAULT_MODEL
    # par défaut : prompt système français
    assert fake_interactions.last_kwargs["system_instruction"] == system_prompt("fr")
    assert fake_interactions.last_kwargs["input"] == "Analyse ce joueur."


def test_generate_report_switches_system_prompt_language(monkeypatch):
    fake_interactions = _FakeInteractions()
    monkeypatch.setattr(
        llm_client, "_get_client", lambda: SimpleNamespace(interactions=fake_interactions)
    )

    llm_client.generate_report("prompt", lang="en")
    instruction = fake_interactions.last_kwargs["system_instruction"]
    assert instruction == system_prompt("en")
    assert "English" in instruction


def test_generate_report_uses_custom_model(monkeypatch):
    fake_interactions = _FakeInteractions()
    fake_client = SimpleNamespace(interactions=fake_interactions)
    monkeypatch.setattr(llm_client, "_get_client", lambda: fake_client)

    llm_client.generate_report("prompt", model="gemini-custom")

    assert fake_interactions.last_kwargs["model"] == "gemini-custom"


def test_generate_report_raises_quota_error_on_429(monkeypatch):
    class _FakeRateLimitError(Exception):
        status_code = 429

    class _FailingInteractions:
        def create(self, **kwargs):
            raise _FakeRateLimitError("quota exceeded")

    monkeypatch.setattr(
        llm_client, "_get_client", lambda: SimpleNamespace(interactions=_FailingInteractions())
    )

    with pytest.raises(llm_client.LLMQuotaError):
        llm_client.generate_report("prompt")


def test_generate_report_wraps_other_errors_as_runtime_error(monkeypatch):
    class _FakeServerError(Exception):
        status_code = 500

    class _FailingInteractions:
        def create(self, **kwargs):
            raise _FakeServerError("boom")

    monkeypatch.setattr(
        llm_client, "_get_client", lambda: SimpleNamespace(interactions=_FailingInteractions())
    )

    with pytest.raises(RuntimeError) as exc_info:
        llm_client.generate_report("prompt")
    assert not isinstance(exc_info.value, llm_client.LLMQuotaError)


# ── Backend interchangeable : provider OpenAI-compatible ────────────────────

def _use_openai(monkeypatch):
    monkeypatch.setattr(llm_client, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(llm_client, "OPENAI_BASE_URL", "http://local:30000/v1")
    monkeypatch.setattr(llm_client, "OPENAI_MODEL", "qwen-local")
    monkeypatch.setattr(llm_client, "OPENAI_API_KEY", "")
    monkeypatch.setattr(llm_client, "LLM_NO_THINK", True)


class _Resp:
    def __init__(self, status, payload=None, text=""):
        self.status_code = status
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def test_generate_report_uses_openai_endpoint(monkeypatch):
    _use_openai(monkeypatch)
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return _Resp(200, {"choices": [{"message": {"content": "Réponse locale."}}]})

    monkeypatch.setattr(llm_client.requests, "post", fake_post)

    out = llm_client.generate_report("prompt", lang="en")
    assert out == "Réponse locale."
    assert captured["url"].endswith("/chat/completions")
    # prompt système EN passé en message system, prompt métier en user
    assert captured["json"]["messages"][0]["content"] == system_prompt("en")
    assert captured["json"]["messages"][1]["content"] == "prompt"
    # la phase de réflexion est désactivée pour les modèles à raisonnement
    assert captured["json"]["chat_template_kwargs"] == {"enable_thinking": False}


def test_generate_report_openai_429_raises_quota(monkeypatch):
    _use_openai(monkeypatch)
    monkeypatch.setattr(llm_client.requests, "post", lambda *a, **k: _Resp(429, text="rate"))
    with pytest.raises(llm_client.LLMQuotaError):
        llm_client.generate_report("p")


def test_generate_report_openai_empty_content_raises(monkeypatch):
    _use_openai(monkeypatch)
    monkeypatch.setattr(
        llm_client.requests, "post",
        lambda *a, **k: _Resp(200, {"choices": [{"message": {"content": ""}}]}),
    )
    with pytest.raises(RuntimeError):
        llm_client.generate_report("p")


def test_generate_report_openai_missing_config_raises(monkeypatch):
    monkeypatch.setattr(llm_client, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(llm_client, "OPENAI_BASE_URL", "")
    monkeypatch.setattr(llm_client, "OPENAI_MODEL", "")
    with pytest.raises(RuntimeError, match="OPENAI_BASE_URL"):
        llm_client.generate_report("p")
