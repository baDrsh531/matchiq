from types import SimpleNamespace

import pytest

from llm import llm_client


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
    assert fake_interactions.last_kwargs["system_instruction"] == llm_client.SYSTEM_PROMPT
    assert fake_interactions.last_kwargs["input"] == "Analyse ce joueur."


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
