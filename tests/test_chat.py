"""Tests de la conversation multi-tours (contexte mocké, sans LLM ni réseau)."""
import pytest

from llm import report_generator
from llm.prompt_templates import match_chat_prompt


def test_chat_prompt_includes_history_and_context():
    ctx = {"goals": {"home": 2, "away": 1}, "man_of_the_match": "X"}
    history = [
        {"role": "user", "content": "Qui est l'homme du match ?"},
        {"role": "assistant", "content": "C'est X."},
        {"role": "user", "content": "Et pourquoi lui ?"},
    ]
    prompt = match_chat_prompt(history, ctx)
    assert "Et pourquoi lui ?" in prompt
    assert "C'est X." in prompt
    assert "man_of_the_match" in prompt
    assert "UNIQUEMENT" in prompt          # discipline anti-hallucination conservée


def test_chat_match_calls_llm_with_context(monkeypatch):
    monkeypatch.setattr(report_generator, "_match_qa_context",
                        lambda fid: {"man_of_the_match": "X", "players": []})
    captured = {}

    def fake_generate(prompt, lang="fr"):
        captured["prompt"] = prompt
        captured["lang"] = lang
        return "Réponse ancrée."

    monkeypatch.setattr(report_generator, "generate_report", fake_generate)

    res = report_generator.chat_match(
        99, [{"role": "user", "content": "Qui a le mieux joué ?"}], lang="en"
    )
    assert res["answer"] == "Réponse ancrée."
    assert captured["lang"] == "en"
    assert "Qui a le mieux joué ?" in captured["prompt"]


def test_chat_match_rejects_when_last_not_user(monkeypatch):
    monkeypatch.setattr(report_generator, "_match_qa_context", lambda fid: {})
    with pytest.raises(ValueError):
        report_generator.chat_match(1, [{"role": "assistant", "content": "hello"}])


def test_chat_match_windows_long_history(monkeypatch):
    monkeypatch.setattr(report_generator, "_match_qa_context", lambda fid: {})
    seen = {}

    def fake_generate(prompt, lang="fr"):
        seen["prompt"] = prompt
        return "ok"

    monkeypatch.setattr(report_generator, "generate_report", fake_generate)
    # 12 tours user : la fenêtre glissante ne doit garder que les 8 derniers.
    msgs = [{"role": "user", "content": f"question {i}"} for i in range(12)]
    report_generator.chat_match(1, msgs)
    assert "question 11" in seen["prompt"]
    assert "question 0" not in seen["prompt"]
