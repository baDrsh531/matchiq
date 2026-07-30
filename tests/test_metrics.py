"""Tests du monitoring LLM (métriques FinOps)."""
import pytest

from llm import metrics


@pytest.fixture
def store(tmp_path, monkeypatch):
    # Isole le fichier de métriques dans un dossier temporaire.
    monkeypatch.setattr(metrics, "METRICS_PATH", tmp_path / "llm_metrics.jsonl")
    return metrics


def test_empty_summary(store):
    s = store.summary()
    assert s["calls"] == 0 and s["cost_usd"] == 0.0 and s["by_model"] == []


def test_records_and_aggregates(store):
    store.record_call("gemini", "gemini-3.5-flash", 1000, 500, 800.0, ok=True)
    store.record_call("gemini", "gemini-3.5-flash", 2000, 1000, 1200.0, ok=True)
    s = store.summary()
    assert s["calls"] == 2 and s["ok"] == 2 and s["failed"] == 0
    assert s["total_tokens"] == 4500
    assert s["success_rate"] == 1.0
    assert s["avg_latency_ms"] == 1000.0
    assert len(s["by_model"]) == 1 and s["by_model"][0]["calls"] == 2


def test_cost_uses_pricing_grid(store):
    # 1M tokens d'entrée + 1M de sortie à (0.075, 0.30) $/M -> 0.375 $.
    store.record_call("gemini", "gemini-3.5-flash", 1_000_000, 1_000_000, 100.0, ok=True)
    assert abs(store.summary()["cost_usd"] - 0.375) < 1e-6


def test_local_model_is_free(store):
    store.record_call("openai", "qwen-local", 5000, 2000, 300.0, ok=True)
    assert store.summary()["cost_usd"] == 0.0     # modèle absent de la grille -> 0


def test_failed_call_counted(store):
    store.record_call("gemini", "gemini-3.5-flash", 100, 0, 50.0, ok=False, error="429")
    s = store.summary()
    assert s["failed"] == 1 and s["ok"] == 0 and s["success_rate"] == 0.0


def test_recent_is_most_recent_first(store):
    for i in range(5):
        store.record_call("openai", "qwen-local", i, i, 10.0, ok=True)
    recent = store.summary(recent=3)["recent"]
    assert len(recent) == 3
    assert recent[0]["prompt_tokens"] == 4      # dernier enregistré en tête
